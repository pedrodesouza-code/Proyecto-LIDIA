"""
SINIA-SA — Carga Histórica 2018-2023
=====================================
Script para cargar los datos históricos faltantes año a año.

Fuentes:
  - FIRMS VIIRS-SNPP archivo (focos de calor)
  - Open-Meteo histórico (meteorología diaria, 36 puntos)
  - CAMS via Open-Meteo (calidad del aire, SOLO desde 2022)
  - CHIRPS via ClimateSERV (precipitación mensual, 36 puntos)

Estrategia:
  - Procesa un año completo por iteración
  - Guarda progreso en data/carga_historica_progreso.json
  - Al relanzar, saltea los pares (año, fuente) ya completados
  - Idempotente: el load_postgres usa upsert, no hay duplicados

Uso:
  python etl/carga_historica.py              # carga 2018-2023 completo
  python etl/carga_historica.py 2021 2023    # carga solo 2021 al 2023
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Raíz del proyecto en el path para que funcionen los imports internos
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DIR_DATOS
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.carga_historica")

# Archivo de progreso — cada clave es "{año}_{fuente}" con valor True/False
ARCHIVO_PROGRESO = DIR_DATOS / "carga_historica_progreso.json"

# CAMS via Open-Meteo solo tiene datos desde 2022
CAMS_ANIO_MIN = 2022


# =============================================================================
# GESTIÓN DE PROGRESO
# =============================================================================

def _cargar_progreso() -> dict:
    if ARCHIVO_PROGRESO.exists():
        with open(ARCHIVO_PROGRESO, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _guardar_progreso(progreso: dict) -> None:
    ARCHIVO_PROGRESO.parent.mkdir(parents=True, exist_ok=True)
    with open(ARCHIVO_PROGRESO, "w", encoding="utf-8") as f:
        json.dump(progreso, f, indent=2, ensure_ascii=False)


def _clave(anio: int, fuente: str) -> str:
    return f"{anio}_{fuente}"


def _ya_completado(progreso: dict, anio: int, fuente: str) -> bool:
    return progreso.get(_clave(anio, fuente), False) is True


def _marcar_completado(progreso: dict, anio: int, fuente: str) -> None:
    progreso[_clave(anio, fuente)] = True
    _guardar_progreso(progreso)


# =============================================================================
# CARGA POR FUENTE
# =============================================================================

def _cargar_firms(anio: int) -> None:
    """FIRMS archivo VIIRS-SNPP: extrae → transforma → carga en PG."""
    from etl.extract.extract_firms import extraer_firms_archivo
    from etl.transform.transform_firms import transformar_firms
    from etl.load.load_postgres import cargar_focos_calor

    fecha_inicio = f"{anio}-01-01"
    fecha_fin    = f"{anio}-12-31"

    logger.info(f"[FIRMS] Extrayendo {fecha_inicio} -> {fecha_fin} ...")
    df_crudo = extraer_firms_archivo(
        sensor="VIIRS_SNPP_SP",
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        guardar=True,
    )
    if df_crudo.empty:
        logger.warning(f"[FIRMS] Sin datos para {anio}, se continúa.")
        return

    logger.info(f"[FIRMS] {len(df_crudo):,} focos crudos. Transformando...")
    df_proc = transformar_firms(df_crudo, guardar=True)
    if df_proc.empty:
        logger.warning(f"[FIRMS] DataFrame vacío tras transformación para {anio}.")
        return

    logger.info(f"[FIRMS] {len(df_proc):,} focos procesados. Cargando en PG...")
    metricas = cargar_focos_calor(df_proc)
    logger.info(
        f"[FIRMS] {anio} completado — "
        f"insertados={metricas['insertados']}, "
        f"actualizados={metricas['actualizados']}, "
        f"sin_cambio={metricas['sin_cambio']}"
    )


def _cargar_meteo(anio: int) -> None:
    """Meteo Open-Meteo histórico: extrae todos los puntos → transforma → carga."""
    from etl.extract.extract_meteo import extraer_meteo_todos_los_puntos
    from etl.transform.transform_meteo import transformar_meteo
    from etl.load.load_postgres import cargar_meteo_diario

    fecha_inicio = f"{anio}-01-01"
    fecha_fin    = f"{anio}-12-31"

    logger.info(f"[METEO] Extrayendo {fecha_inicio} -> {fecha_fin} (36 puntos)...")
    df_crudo = extraer_meteo_todos_los_puntos(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        granularidad="daily",
        pausa=0.5,
    )
    if df_crudo.empty:
        logger.warning(f"[METEO] Sin datos para {anio}, se continúa.")
        return

    logger.info(f"[METEO] {len(df_crudo):,} registros crudos. Transformando...")
    df_proc = transformar_meteo(df_crudo, guardar=True)
    if df_proc.empty:
        logger.warning(f"[METEO] DataFrame vacío tras transformación para {anio}.")
        return

    logger.info(f"[METEO] {len(df_proc):,} registros procesados. Cargando en PG...")
    metricas = cargar_meteo_diario(df_proc, tipo_dato="historico")
    logger.info(
        f"[METEO] {anio} completado — "
        f"insertados={metricas['insertados']}, "
        f"actualizados={metricas['actualizados']}, "
        f"sin_cambio={metricas['sin_cambio']}"
    )


def _cargar_cams(anio: int) -> None:
    """CAMS calidad del aire: extrae todos los puntos → transforma → carga."""
    from etl.extract.extract_cams import extraer_cams_todos_los_puntos
    from etl.transform.transform_cams import transformar_cams
    from etl.load.load_postgres import cargar_calidad_aire

    fecha_inicio = f"{anio}-01-01"
    fecha_fin    = f"{anio}-12-31"

    logger.info(f"[CAMS] Extrayendo {fecha_inicio} -> {fecha_fin} (36 puntos)...")
    df_crudo = extraer_cams_todos_los_puntos(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        pausa=0.5,
    )
    if df_crudo.empty:
        logger.warning(f"[CAMS] Sin datos para {anio}, se continúa.")
        return

    logger.info(f"[CAMS] {len(df_crudo):,} registros crudos. Transformando...")
    df_proc = transformar_cams(df_crudo, guardar=True)
    if df_proc.empty:
        logger.warning(f"[CAMS] DataFrame vacío tras transformación para {anio}.")
        return

    logger.info(f"[CAMS] {len(df_proc):,} registros procesados. Cargando en PG...")
    metricas = cargar_calidad_aire(df_proc)
    logger.info(
        f"[CAMS] {anio} completado — "
        f"insertados={metricas['insertados']}, "
        f"actualizados={metricas['actualizados']}, "
        f"sin_cambio={metricas['sin_cambio']}"
    )


def _cargar_chirps(anio: int) -> None:
    """CHIRPS precipitación mensual: extrae todos los puntos → transforma → carga."""
    from etl.extract.extract_chirps import extraer_chirps_todos_los_puntos
    from etl.transform.transform_chirps import transformar_chirps
    from etl.load.load_postgres import cargar_precipitacion

    logger.info(f"[CHIRPS] Extrayendo año {anio} (36 puntos)...")
    df_crudo = extraer_chirps_todos_los_puntos(
        anio_inicio=anio,
        anio_fin=anio,
        pausa=2.0,
    )
    if df_crudo.empty:
        logger.warning(f"[CHIRPS] Sin datos para {anio}, se continúa.")
        return

    logger.info(f"[CHIRPS] {len(df_crudo):,} registros crudos. Transformando...")
    df_proc = transformar_chirps(df_crudo, guardar=True)
    if df_proc.empty:
        logger.warning(f"[CHIRPS] DataFrame vacío tras transformación para {anio}.")
        return

    logger.info(f"[CHIRPS] {len(df_proc):,} registros procesados. Cargando en PG...")
    metricas = cargar_precipitacion(df_proc)
    logger.info(
        f"[CHIRPS] {anio} completado — "
        f"insertados={metricas['insertados']}, "
        f"actualizados={metricas['actualizados']}, "
        f"sin_cambio={metricas['sin_cambio']}"
    )


# =============================================================================
# TABLA DE FUENTES
# =============================================================================

# Cada entrada: (nombre, función, año_mínimo)
# CAMS solo disponible desde 2022; el resto desde 2018
FUENTES = [
    ("firms",  _cargar_firms,  2018),
    ("meteo",  _cargar_meteo,  2018),
    ("chirps", _cargar_chirps, 2018),
    ("cams",   _cargar_cams,   CAMS_ANIO_MIN),
]


# =============================================================================
# PIPELINE PRINCIPAL
# =============================================================================

def ejecutar_carga_historica(anio_inicio: int = 2018, anio_fin: int = 2023) -> None:
    """
    Carga datos históricos año a año para las 4 fuentes principales.

    Args:
        anio_inicio: Primer año a cargar (default 2018).
        anio_fin:    Último año a cargar inclusive (default 2023).
    """
    progreso = _cargar_progreso()
    anios = list(range(anio_inicio, anio_fin + 1))

    print(f"\n{'='*60}")
    print(f"SINIA-SA — Carga Histórica {anio_inicio}–{anio_fin}")
    print(f"{'='*60}")
    print(f"Años a procesar: {anios}")
    print(f"Archivo de progreso: {ARCHIVO_PROGRESO}\n")

    total_fuentes = sum(
        1
        for anio in anios
        for nombre, _, anio_min in FUENTES
        if anio >= anio_min
    )
    completadas = sum(
        1
        for anio in anios
        for nombre, _, anio_min in FUENTES
        if anio >= anio_min and _ya_completado(progreso, anio, nombre)
    )
    print(f"Progreso actual: {completadas}/{total_fuentes} combinaciones completadas.\n")

    for anio in anios:
        print(f"\n--- AÑO {anio} ---")
        for nombre, funcion, anio_min in FUENTES:
            if anio < anio_min:
                print(f"  [{nombre.upper()}] Saltado (disponible desde {anio_min})")
                continue

            if _ya_completado(progreso, anio, nombre):
                print(f"  [{nombre.upper()}] Ya completado, saltando.")
                continue

            print(f"  [{nombre.upper()}] Iniciando...")
            t0 = time.perf_counter()
            try:
                funcion(anio)
                duracion = time.perf_counter() - t0
                _marcar_completado(progreso, anio, nombre)
                print(f"  [{nombre.upper()}] OK ({duracion:.1f}s)")
            except Exception as err:
                duracion = time.perf_counter() - t0
                logger.error(
                    f"[{nombre.upper()}] Error en {anio}: {err}",
                    exc_info=True,
                )
                print(f"  [{nombre.upper()}] ERROR ({duracion:.1f}s): {err}")
                print(f"           El año {anio} para {nombre} NO se marcó como completado.")
                print(f"           Podés relanzar el script para reintentar.")

    print(f"\n{'='*60}")
    print("Carga histórica finalizada.")
    progreso_final = _cargar_progreso()
    completadas_final = sum(1 for v in progreso_final.values() if v is True)
    print(f"Total combinaciones completadas: {completadas_final}/{total_fuentes}")
    print(f"{'='*60}\n")


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    # Argumentos opcionales: anio_inicio anio_fin
    # Ejemplos:
    #   python etl/carga_historica.py           -> 2018-2023
    #   python etl/carga_historica.py 2021 2023 -> 2021-2023
    #   python etl/carga_historica.py 2018 2018 -> solo 2018

    args = sys.argv[1:]
    if len(args) == 2:
        anio_ini = int(args[0])
        anio_fin = int(args[1])
    elif len(args) == 1:
        anio_ini = int(args[0])
        anio_fin = int(args[0])
    else:
        anio_ini = 2018
        anio_fin = 2023

    ejecutar_carga_historica(anio_inicio=anio_ini, anio_fin=anio_fin)
