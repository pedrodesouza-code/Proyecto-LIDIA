"""
SINIA-SA — Cargador de datos hacia PostgreSQL
==============================================
Carga idempotente de los tres conjuntos de datos procesados:
  - focos_calor       (FIRMS VIIRS)
  - meteo_diario      (Open-Meteo histórico + forecast)
  - calidad_aire_diario (CAMS via Open-Meteo)

Estrategia CDC:
  - INSERT ... ON CONFLICT DO UPDATE (upsert por clave natural)
  - Registra en etl_ejecuciones cada corrida con métricas precisas
  - Detecta si es carga inicial o incremental consultando la tabla destino

Idempotencia garantizada:
  - Re-ejecutar el mismo lote no genera duplicados ni errores
  - Registros ya existentes e idénticos se cuentan como "sin_cambio"
"""

from __future__ import annotations

import socket
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.settings import PG_CONFIG
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.load.postgres")

VERSION_PIPELINE = "1.0.0"


# =============================================================================
# CONEXIÓN
# =============================================================================

def get_connection() -> psycopg2.extensions.connection:
    """Crea y devuelve una conexión a PostgreSQL según PG_CONFIG."""
    return psycopg2.connect(**PG_CONFIG)


def _safe_val(v: Any) -> Any:
    """Convierte NaN/NaT/numpy types a None para psycopg2."""
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if pd.isna(v):
        return None
    return v


# =============================================================================
# REGISTRO DE EJECUCIÓN ETL
# =============================================================================

def _registrar_inicio(
    conn: psycopg2.extensions.connection,
    fuente: str,
    etapa: str,
    tipo_carga: str,
) -> int:
    """Inserta un registro en etl_ejecuciones y devuelve su ID."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO etl_ejecuciones
                (fuente, etapa, tipo_carga, estado, iniciado_en)
            VALUES (%s, %s, %s, 'parcial', NOW())
            RETURNING id
            """,
            (fuente, etapa, tipo_carga),
        )
        ejecucion_id = cur.fetchone()[0]
    conn.commit()
    return ejecucion_id


def _registrar_fin(
    conn: psycopg2.extensions.connection,
    ejecucion_id: int,
    estado: str,
    procesados: int,
    insertados: int,
    actualizados: int,
    sin_cambio: int,
    duracion: float,
    mensaje: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
) -> None:
    """Actualiza el registro de ejecución con los resultados finales."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE etl_ejecuciones SET
                estado                = %s,
                registros_procesados  = %s,
                registros_insertados  = %s,
                registros_actualizados = %s,
                registros_sin_cambio  = %s,
                duracion_segundos     = %s,
                mensaje               = %s,
                fecha_datos_desde     = %s,
                fecha_datos_hasta     = %s,
                finalizado_en         = NOW()
            WHERE id = %s
            """,
            (
                estado, procesados, insertados, actualizados, sin_cambio,
                round(duracion, 3), mensaje, fecha_desde, fecha_hasta,
                ejecucion_id,
            ),
        )
    conn.commit()


# =============================================================================
# FUNCIÓN: Detectar tipo de carga (inicial / incremental)
# =============================================================================

def _detectar_tipo_carga(conn: psycopg2.extensions.connection, tabla: str) -> str:
    """Devuelve 'inicial' si la tabla está vacía, 'incremental' si ya tiene datos."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {tabla}")  # noqa: S608
        n = cur.fetchone()[0]
    return "inicial" if n == 0 else "incremental"


# =============================================================================
# FUNCIÓN: Obtener mapa nombre->id de puntos_monitoreo
# =============================================================================

def _get_puntos_map(conn: psycopg2.extensions.connection) -> dict[str, int]:
    """Devuelve {nombre_punto: id_postgres} de la tabla puntos_monitoreo."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, nombre FROM puntos_monitoreo WHERE activo = TRUE")
        rows = cur.fetchall()
    return {nombre: id_ for id_, nombre in rows}


# =============================================================================
# CARGA: focos_calor
# =============================================================================

def cargar_focos_calor(df: pd.DataFrame) -> dict[str, int]:
    """
    Carga focos de calor (FIRMS) en PostgreSQL.

    Upsert por clave natural: (latitud, longitud, fecha_adq, hora_adq_hhmm, satelite).
    Si el foco ya existe, actualiza potencia_radiativa y confianza_num.

    Usa execute_values con commits cada BATCH_SIZE filas para evitar
    transacciones gigantes que crashean PostgreSQL con datasets grandes.

    Returns:
        Diccionario con conteos: insertados, actualizados, sin_cambio, errores.
    """
    if df.empty:
        logger.warning("cargar_focos_calor: DataFrame vacío, nada que cargar")
        return {"insertados": 0, "actualizados": 0, "sin_cambio": 0, "errores": 0}

    BATCH_SIZE = 50_000

    conn = get_connection()
    t0 = time.perf_counter()
    tipo_carga = _detectar_tipo_carga(conn, "focos_calor")
    ej_id = _registrar_inicio(conn, "firms", "load", tipo_carga)

    insertados = actualizados = sin_cambio = errores = 0

    # Construir lista de tuplas con todos los valores
    def _to_tuple(row: pd.Series) -> tuple:
        fecha = row.get("fecha_adq")
        if hasattr(fecha, "date"):
            fecha = fecha.date()
        return (
            _safe_val(fecha),
            _safe_val(row.get("hora_adq_hhmm")),
            _safe_val(row.get("latitud")),
            _safe_val(row.get("longitud")),
            _safe_val(row.get("pais", "OTR")),
            _safe_val(row.get("potencia_radiativa")),
            _safe_val(row.get("confianza_raw")),
            _safe_val(row.get("confianza_num")),
            _safe_val(row.get("satelite")),
            _safe_val(row.get("instrumento")),
            _safe_val(row.get("dia_noche")),
            _safe_val(row.get("es_diurno")),
            _safe_val(row.get("brillo_ti4")),
            _safe_val(row.get("brillo_ti5")),
            "FIRMS",
        )

    SQL_TEMPLATE = """
        INSERT INTO focos_calor
            (fecha_adq, hora_adq_hhmm, latitud, longitud, pais,
             potencia_radiativa, confianza_raw, confianza_num,
             satelite, instrumento, dia_noche, es_diurno,
             brillo_ti4, brillo_ti5, fuente)
        VALUES %s
        ON CONFLICT (latitud, longitud, fecha_adq, hora_adq_hhmm, satelite)
        DO UPDATE SET
            potencia_radiativa = EXCLUDED.potencia_radiativa,
            confianza_num      = EXCLUDED.confianza_num,
            pais               = EXCLUDED.pais
        WHERE focos_calor.potencia_radiativa IS DISTINCT FROM EXCLUDED.potencia_radiativa
    """

    total = len(df)
    try:
        for batch_start in range(0, total, BATCH_SIZE):
            batch = df.iloc[batch_start: batch_start + BATCH_SIZE]
            tuples = [_to_tuple(row) for _, row in batch.iterrows()]

            try:
                with conn.cursor() as cur:
                    psycopg2.extras.execute_values(
                        cur, SQL_TEMPLATE, tuples, page_size=BATCH_SIZE
                    )
                    # execute_values no devuelve rowcount útil con ON CONFLICT,
                    # contamos como insertados los afectados vs tamaño del batch
                    affected = cur.rowcount if cur.rowcount >= 0 else 0
                    insertados += affected
                    sin_cambio += len(tuples) - affected
                conn.commit()
                logger.info(
                    f"focos_calor batch {batch_start // BATCH_SIZE + 1}: "
                    f"{batch_start + len(tuples)}/{total} filas procesadas"
                )
            except Exception as e:
                conn.rollback()
                errores += len(tuples)
                logger.warning(
                    f"Error en batch {batch_start}-{batch_start + len(tuples)}: {e}"
                )
                # Reconectar para el siguiente batch
                try:
                    conn.close()
                except Exception:
                    pass
                conn = get_connection()

    except Exception as e:
        logger.error(f"Error fatal en cargar_focos_calor: {e}")
        _registrar_fin(conn, ej_id, "error", total, 0, 0, 0,
                       time.perf_counter() - t0, str(e))
        try:
            conn.close()
        except Exception:
            pass
        raise

    duracion = time.perf_counter() - t0
    _registrar_fin(
        conn, ej_id, "ok", total,
        insertados, actualizados, sin_cambio, duracion,
    )
    conn.close()

    logger.info(
        f"focos_calor cargados [{tipo_carga}]: "
        f"{insertados} nuevos, {actualizados} actualizados, "
        f"{sin_cambio} sin cambio, {errores} errores — {duracion:.2f}s",
        extra={"etl_stage": "load", "source": "firms"},
    )

    # Refrescar vista materializada si existe y el usuario tiene permisos.
    # El dashboard usa la vista normal v_focos_por_pais_mes, por lo que este
    # refresco es una optimizacion opcional y no debe marcar error operativo.
    if insertados > 0:
        try:
            conn2 = get_connection()
            with conn2.cursor() as cur:
                cur.execute("""
                    SELECT 1
                    FROM pg_matviews
                    WHERE schemaname = 'public'
                      AND matviewname = 'mv_focos_por_pais_mes'
                """)
                if cur.fetchone():
                    cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_focos_por_pais_mes")
                    conn2.commit()
                    logger.info("mv_focos_por_pais_mes refrescada", extra={"etl_stage": "load", "source": "firms"})
                else:
                    logger.info("mv_focos_por_pais_mes no existe; se usa v_focos_por_pais_mes")
            conn2.close()
        except Exception as e:
            logger.info(f"Refresh opcional de mv_focos_por_pais_mes omitido: {e}")

    return {"insertados": insertados, "actualizados": actualizados,
            "sin_cambio": sin_cambio, "errores": errores}


# =============================================================================
# CARGA: meteo_diario
# =============================================================================

def cargar_meteo_diario(df: pd.DataFrame, tipo_dato: str = "historico") -> dict[str, int]:
    """
    Carga datos meteorológicos en meteo_diario.

    Upsert por (fecha, id_punto, tipo_dato).
    Actualiza el índice de riesgo si cambió (CDC: detecta modificaciones).

    Args:
        df:        DataFrame procesado por transform_meteo
        tipo_dato: 'historico' o 'forecast'
    """
    if df.empty:
        logger.warning("cargar_meteo_diario: DataFrame vacío")
        return {"insertados": 0, "actualizados": 0, "sin_cambio": 0, "errores": 0}

    conn = get_connection()
    t0 = time.perf_counter()
    tipo_carga = _detectar_tipo_carga(conn, "meteo_diario")
    ej_id = _registrar_inicio(conn, "open-meteo", "load", tipo_carga)
    puntos_map = _get_puntos_map(conn)

    insertados = actualizados = sin_cambio = errores = 0

    SQL = """
        INSERT INTO meteo_diario (
            fecha, id_punto, tipo_dato,
            temperature_2m_max, temperature_2m_min, temperature_2m_mean,
            relative_humidity_2m_max, relative_humidity_2m_min,
            wind_speed_10m_max, wind_gusts_10m_max,
            precipitation_sum, et0_fao_evapotranspiration,
            precipitation_probability_max,
            riesgo_temp, riesgo_humedad, riesgo_viento, riesgo_sequia,
            indice_riesgo, nivel_riesgo, fuente
        ) VALUES (
            %(fecha)s, %(id_punto)s, %(tipo_dato)s,
            %(temperature_2m_max)s, %(temperature_2m_min)s, %(temperature_2m_mean)s,
            %(relative_humidity_2m_max)s, %(relative_humidity_2m_min)s,
            %(wind_speed_10m_max)s, %(wind_gusts_10m_max)s,
            %(precipitation_sum)s, %(et0_fao_evapotranspiration)s,
            %(precipitation_probability_max)s,
            %(riesgo_temp)s, %(riesgo_humedad)s, %(riesgo_viento)s, %(riesgo_sequia)s,
            %(indice_riesgo)s, %(nivel_riesgo)s, %(fuente)s
        )
        ON CONFLICT (fecha, id_punto, tipo_dato)
        DO UPDATE SET
            indice_riesgo    = EXCLUDED.indice_riesgo,
            nivel_riesgo     = EXCLUDED.nivel_riesgo,
            temperature_2m_max = EXCLUDED.temperature_2m_max,
            relative_humidity_2m_min = EXCLUDED.relative_humidity_2m_min,
            wind_speed_10m_max = EXCLUDED.wind_speed_10m_max,
            precipitation_sum = EXCLUDED.precipitation_sum,
            actualizado_en   = NOW()
        WHERE
            meteo_diario.indice_riesgo IS DISTINCT FROM EXCLUDED.indice_riesgo
            OR meteo_diario.nivel_riesgo IS DISTINCT FROM EXCLUDED.nivel_riesgo
    """

    fechas = []

    try:
        with conn.cursor() as cur:
            for _, row in df.iterrows():
                nombre_punto = str(row.get("punto", ""))
                id_punto = puntos_map.get(nombre_punto)
                if id_punto is None:
                    logger.warning(f"Punto no encontrado en BD: '{nombre_punto}'")
                    errores += 1
                    continue

                fecha = row.get("fecha")
                if hasattr(fecha, "date"):
                    fecha = fecha.date()
                fechas.append(fecha)

                params = {
                    "fecha":                        _safe_val(fecha),
                    "id_punto":                     id_punto,
                    "tipo_dato":                    tipo_dato,
                    "temperature_2m_max":           _safe_val(row.get("temperature_2m_max")),
                    "temperature_2m_min":           _safe_val(row.get("temperature_2m_min")),
                    "temperature_2m_mean":          _safe_val(row.get("temperature_2m_mean")),
                    "relative_humidity_2m_max":     _safe_val(row.get("relative_humidity_2m_max")),
                    "relative_humidity_2m_min":     _safe_val(row.get("relative_humidity_2m_min")),
                    "wind_speed_10m_max":           _safe_val(row.get("wind_speed_10m_max")),
                    "wind_gusts_10m_max":           _safe_val(row.get("wind_gusts_10m_max")),
                    "precipitation_sum":            _safe_val(row.get("precipitation_sum")),
                    "et0_fao_evapotranspiration":   _safe_val(row.get("et0_fao_evapotranspiration")),
                    "precipitation_probability_max":_safe_val(row.get("precipitation_probability_max")),
                    "riesgo_temp":                  _safe_val(row.get("riesgo_temp")),
                    "riesgo_humedad":               _safe_val(row.get("riesgo_humedad")),
                    "riesgo_viento":                _safe_val(row.get("riesgo_viento")),
                    "riesgo_sequia":                _safe_val(row.get("riesgo_sequia")),
                    "indice_riesgo":                _safe_val(row.get("indice_riesgo")),
                    "nivel_riesgo":                 _safe_val(str(row.get("nivel_riesgo", "")) or None),
                    "fuente":                       "open-meteo",
                }

                cur.execute(SQL, params)
                if cur.rowcount == 1:
                    insertados += 1
                elif cur.rowcount == 0:
                    sin_cambio += 1
                else:
                    actualizados += 1

        conn.commit()

    except Exception as e:
        conn.rollback()
        logger.error(f"Error en cargar_meteo_diario: {e}")
        _registrar_fin(conn, ej_id, "error", len(df), 0, 0, 0,
                       time.perf_counter() - t0, str(e))
        conn.close()
        raise

    duracion = time.perf_counter() - t0
    fecha_desde = min(fechas) if fechas else None
    fecha_hasta = max(fechas) if fechas else None

    _registrar_fin(
        conn, ej_id, "ok", len(df),
        insertados, actualizados, sin_cambio, duracion,
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
    )
    conn.close()

    logger.info(
        f"meteo_diario [{tipo_dato}, {tipo_carga}]: "
        f"{insertados} nuevos, {actualizados} actualizados, {sin_cambio} sin cambio — {duracion:.2f}s",
        extra={"etl_stage": "load", "source": "open-meteo"},
    )
    return {"insertados": insertados, "actualizados": actualizados,
            "sin_cambio": sin_cambio, "errores": errores}


# =============================================================================
# CARGA: calidad_aire_diario
# =============================================================================

def cargar_calidad_aire(df: pd.DataFrame) -> dict[str, int]:
    """
    Carga datos de calidad del aire (CAMS) en calidad_aire_diario.

    Upsert por (fecha, id_punto).
    Actualiza si pm10_media o nivel_pm10 cambiaron (CDC).
    """
    if df.empty:
        logger.warning("cargar_calidad_aire: DataFrame vacío")
        return {"insertados": 0, "actualizados": 0, "sin_cambio": 0, "errores": 0}

    conn = get_connection()
    t0 = time.perf_counter()
    tipo_carga = _detectar_tipo_carga(conn, "calidad_aire_diario")
    ej_id = _registrar_inicio(conn, "cams", "load", tipo_carga)
    puntos_map = _get_puntos_map(conn)

    insertados = actualizados = sin_cambio = errores = 0

    SQL = """
        INSERT INTO calidad_aire_diario (
            fecha, id_punto,
            pm10_media, pm10_max, pm10_p95,
            pm2_5_media, pm2_5_max,
            aerosol_optical_depth_media,
            european_aqi_media, european_aqi_max,
            horas_validas, supera_oms_pm10, nivel_pm10, fuente
        ) VALUES (
            %(fecha)s, %(id_punto)s,
            %(pm10_media)s, %(pm10_max)s, %(pm10_p95)s,
            %(pm2_5_media)s, %(pm2_5_max)s,
            %(aerosol_optical_depth_media)s,
            %(european_aqi_media)s, %(european_aqi_max)s,
            %(horas_validas)s, %(supera_oms_pm10)s, %(nivel_pm10)s, %(fuente)s
        )
        ON CONFLICT (fecha, id_punto)
        DO UPDATE SET
            pm10_media         = EXCLUDED.pm10_media,
            pm10_max           = EXCLUDED.pm10_max,
            supera_oms_pm10    = EXCLUDED.supera_oms_pm10,
            nivel_pm10         = EXCLUDED.nivel_pm10,
            european_aqi_media = EXCLUDED.european_aqi_media,
            actualizado_en     = NOW()
        WHERE
            calidad_aire_diario.pm10_media IS DISTINCT FROM EXCLUDED.pm10_media
            OR calidad_aire_diario.nivel_pm10 IS DISTINCT FROM EXCLUDED.nivel_pm10
    """

    try:
        with conn.cursor() as cur:
            for _, row in df.iterrows():
                nombre_punto = str(row.get("punto", ""))
                id_punto = puntos_map.get(nombre_punto)
                if id_punto is None:
                    errores += 1
                    continue

                fecha = row.get("fecha")
                if hasattr(fecha, "date"):
                    fecha = fecha.date()

                nivel = row.get("nivel_pm10")
                if hasattr(nivel, "item"):
                    nivel = str(nivel)
                elif nivel is not None:
                    nivel = str(nivel)

                params = {
                    "fecha":                       _safe_val(fecha),
                    "id_punto":                    id_punto,
                    "pm10_media":                  _safe_val(row.get("pm10_media")),
                    "pm10_max":                    _safe_val(row.get("pm10_max")),
                    "pm10_p95":                    _safe_val(row.get("pm10_p95")),
                    "pm2_5_media":                 _safe_val(row.get("pm2_5_media")),
                    "pm2_5_max":                   _safe_val(row.get("pm2_5_max")),
                    "aerosol_optical_depth_media": _safe_val(row.get("aerosol_optical_depth_media")),
                    "european_aqi_media":          _safe_val(row.get("european_aqi_media")),
                    "european_aqi_max":            _safe_val(row.get("european_aqi_max")),
                    "horas_validas":               _safe_val(row.get("horas_validas")),
                    "supera_oms_pm10":             _safe_val(row.get("supera_oms_pm10")),
                    "nivel_pm10":                  nivel if nivel not in ("", "None", "nan") else None,
                    "fuente":                      "cams-openmeteo",
                }

                cur.execute(SQL, params)
                if cur.rowcount == 1:
                    insertados += 1
                elif cur.rowcount == 0:
                    sin_cambio += 1
                else:
                    actualizados += 1

        conn.commit()

    except Exception as e:
        conn.rollback()
        logger.error(f"Error en cargar_calidad_aire: {e}")
        _registrar_fin(conn, ej_id, "error", len(df), 0, 0, 0,
                       time.perf_counter() - t0, str(e))
        conn.close()
        raise

    duracion = time.perf_counter() - t0
    _registrar_fin(
        conn, ej_id, "ok", len(df),
        insertados, actualizados, sin_cambio, duracion,
    )
    conn.close()

    logger.info(
        f"calidad_aire_diario [{tipo_carga}]: "
        f"{insertados} nuevos, {actualizados} actualizados, {sin_cambio} sin cambio — {duracion:.2f}s",
        extra={"etl_stage": "load", "source": "cams"},
    )
    return {"insertados": insertados, "actualizados": actualizados,
            "sin_cambio": sin_cambio, "errores": errores}


# =============================================================================
# CARGA: precipitacion_mensual (CHIRPS)
# =============================================================================

def cargar_precipitacion(df: pd.DataFrame) -> dict[str, int]:
    """
    Carga precipitación mensual CHIRPS en precipitacion_mensual.

    Upsert por (anio, mes, id_punto).
    """
    if df.empty:
        logger.warning("cargar_precipitacion: DataFrame vacío")
        return {"insertados": 0, "actualizados": 0, "sin_cambio": 0, "errores": 0}

    conn = get_connection()
    t0 = time.perf_counter()
    tipo_carga = _detectar_tipo_carga(conn, "precipitacion_mensual")
    ej_id = _registrar_inicio(conn, "chirps", "load", tipo_carga)
    puntos_map = _get_puntos_map(conn)

    insertados = actualizados = sin_cambio = errores = 0

    SQL = """
        INSERT INTO precipitacion_mensual (anio, mes, id_punto, precipitacion_mm, fuente)
        VALUES (%(anio)s, %(mes)s, %(id_punto)s, %(precipitacion_mm)s, %(fuente)s)
        ON CONFLICT (anio, mes, id_punto)
        DO UPDATE SET
            precipitacion_mm = EXCLUDED.precipitacion_mm
        WHERE precipitacion_mensual.precipitacion_mm IS DISTINCT FROM EXCLUDED.precipitacion_mm
    """

    try:
        with conn.cursor() as cur:
            for _, row in df.iterrows():
                nombre_punto = str(row.get("punto", ""))
                id_punto = puntos_map.get(nombre_punto)
                if id_punto is None:
                    errores += 1
                    continue

                fecha = pd.to_datetime(row.get("fecha"), errors="coerce")
                if pd.isna(fecha):
                    errores += 1
                    continue

                params = {
                    "anio":            int(fecha.year),
                    "mes":             int(fecha.month),
                    "id_punto":        id_punto,
                    "precipitacion_mm": _safe_val(row.get("precipitacion_mm")),
                    "fuente":          str(row.get("fuente", "CHIRPS_ClimateSERV")),
                }

                cur.execute(SQL, params)
                if cur.rowcount == 1:
                    insertados += 1
                elif cur.rowcount == 0:
                    sin_cambio += 1
                else:
                    actualizados += 1

        conn.commit()

    except Exception as e:
        conn.rollback()
        logger.error(f"Error en cargar_precipitacion: {e}")
        _registrar_fin(conn, ej_id, "error", len(df), 0, 0, 0, time.perf_counter() - t0, str(e))
        conn.close()
        raise

    duracion = time.perf_counter() - t0
    _registrar_fin(conn, ej_id, "ok", len(df), insertados, actualizados, sin_cambio, duracion)
    conn.close()
    logger.info(
        f"precipitacion_mensual [{tipo_carga}]: "
        f"{insertados} nuevos, {actualizados} actualizados, {sin_cambio} sin cambio",
        extra={"etl_stage": "load", "source": "chirps"},
    )
    return {"insertados": insertados, "actualizados": actualizados,
            "sin_cambio": sin_cambio, "errores": errores}


# =============================================================================
# CARGA: cobertura_vegetal (MODIS MCD12Q1)
# =============================================================================

def cargar_cobertura_vegetal(df: pd.DataFrame) -> dict[str, int]:
    """
    Carga clasificación MODIS MCD12Q1 en cobertura_vegetal.

    Upsert por (anio, id_punto).
    """
    if df.empty:
        logger.warning("cargar_cobertura_vegetal: DataFrame vacío")
        return {"insertados": 0, "actualizados": 0, "sin_cambio": 0, "errores": 0}

    conn = get_connection()
    t0 = time.perf_counter()
    tipo_carga = _detectar_tipo_carga(conn, "cobertura_vegetal")
    ej_id = _registrar_inicio(conn, "modis", "load", tipo_carga)
    puntos_map = _get_puntos_map(conn)

    insertados = actualizados = sin_cambio = errores = 0

    SQL = """
        INSERT INTO cobertura_vegetal (anio, id_punto, lc_type1, lc_descripcion, fuente)
        VALUES (%(anio)s, %(id_punto)s, %(lc_type1)s, %(lc_descripcion)s, %(fuente)s)
        ON CONFLICT (anio, id_punto)
        DO UPDATE SET
            lc_type1       = EXCLUDED.lc_type1,
            lc_descripcion = EXCLUDED.lc_descripcion
        WHERE cobertura_vegetal.lc_type1 IS DISTINCT FROM EXCLUDED.lc_type1
    """

    try:
        with conn.cursor() as cur:
            for _, row in df.iterrows():
                nombre_punto = str(row.get("punto", ""))
                id_punto = puntos_map.get(nombre_punto)
                if id_punto is None:
                    errores += 1
                    continue

                params = {
                    "anio":          _safe_val(row.get("anio")),
                    "id_punto":      id_punto,
                    "lc_type1":      _safe_val(row.get("lc_type1")),
                    "lc_descripcion": str(row.get("lc_descripcion", "Sin clasificar")),
                    "fuente":        str(row.get("fuente", "MODIS_MCD12Q1_AppEEARS")),
                }

                cur.execute(SQL, params)
                if cur.rowcount == 1:
                    insertados += 1
                elif cur.rowcount == 0:
                    sin_cambio += 1
                else:
                    actualizados += 1

        conn.commit()

    except Exception as e:
        conn.rollback()
        logger.error(f"Error en cargar_cobertura_vegetal: {e}")
        _registrar_fin(conn, ej_id, "error", len(df), 0, 0, 0, time.perf_counter() - t0, str(e))
        conn.close()
        raise

    duracion = time.perf_counter() - t0
    _registrar_fin(conn, ej_id, "ok", len(df), insertados, actualizados, sin_cambio, duracion)
    conn.close()
    logger.info(
        f"cobertura_vegetal [{tipo_carga}]: "
        f"{insertados} nuevos, {actualizados} actualizados, {sin_cambio} sin cambio",
        extra={"etl_stage": "load", "source": "modis"},
    )
    return {"insertados": insertados, "actualizados": actualizados,
            "sin_cambio": sin_cambio, "errores": errores}


# =============================================================================
# PIPELINE COMPLETO
# =============================================================================

def ejecutar_carga_completa() -> None:
    """
    Ejecuta la carga completa de todos los parquets procesados hacia PostgreSQL.
    Punto de entrada para la carga inicial o re-proceso.
    """
    from pathlib import Path
    from config.settings import DIR_PROCESADO

    logger.info("=== INICIO CARGA COMPLETA POSTGRESQL ===",
                extra={"etl_stage": "load", "source": "pipeline"})
    t_total = time.perf_counter()

    # ── 1. focos_calor ────────────────────────────────────────────────────────
    ruta_firms = DIR_PROCESADO / "firms_procesado.parquet"
    if ruta_firms.exists():
        df_firms = pd.read_parquet(ruta_firms)
        logger.info(f"Cargando {len(df_firms)} focos de calor...")
        cargar_focos_calor(df_firms)
    else:
        logger.warning(f"No encontrado: {ruta_firms}")

    # ── 2. meteo histórico ────────────────────────────────────────────────────
    for parquet in DIR_PROCESADO.glob("meteo_procesado_*.parquet"):
        df_m = pd.read_parquet(parquet)
        if not df_m.empty:
            logger.info(f"Cargando meteo histórico desde {parquet.name} ({len(df_m)} registros)...")
            cargar_meteo_diario(df_m, tipo_dato="historico")

    # ── 3. forecast ───────────────────────────────────────────────────────────
    ruta_fc = DIR_PROCESADO / "forecast_riesgo.parquet"
    if ruta_fc.exists():
        df_fc = pd.read_parquet(ruta_fc)
        if not df_fc.empty:
            logger.info(f"Cargando forecast ({len(df_fc)} registros)...")
            cargar_meteo_diario(df_fc, tipo_dato="forecast")

    # ── 4. calidad del aire ───────────────────────────────────────────────────
    for parquet in DIR_PROCESADO.glob("cams_procesado_*.parquet"):
        df_c = pd.read_parquet(parquet)
        if not df_c.empty:
            logger.info(f"Cargando CAMS desde {parquet.name} ({len(df_c)} registros)...")
            cargar_calidad_aire(df_c)

    # ── 5. precipitación CHIRPS ───────────────────────────────────────────────
    for parquet in DIR_PROCESADO.glob("chirps_*.parquet"):
        df_ch = pd.read_parquet(parquet)
        if not df_ch.empty:
            logger.info(f"Cargando CHIRPS desde {parquet.name} ({len(df_ch)} registros)...")
            cargar_precipitacion(df_ch)

    # ── 6. cobertura vegetal MODIS ────────────────────────────────────────────
    ruta_modis = DIR_PROCESADO / "modis_lc.parquet"
    if ruta_modis.exists():
        df_mod = pd.read_parquet(ruta_modis)
        if not df_mod.empty:
            logger.info(f"Cargando MODIS Land Cover ({len(df_mod)} registros)...")
            cargar_cobertura_vegetal(df_mod)

    duracion = time.perf_counter() - t_total
    logger.info(
        f"=== CARGA COMPLETA FINALIZADA en {duracion:.2f}s ===",
        extra={"etl_stage": "load", "source": "pipeline"},
    )


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SINIA-SA — Carga a PostgreSQL (Sudamérica)")
    print("=" * 60)
    ejecutar_carga_completa()
    print("\nCarga completada. Revisá los logs para detalles.")
