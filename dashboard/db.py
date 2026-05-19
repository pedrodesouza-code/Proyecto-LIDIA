"""
SINIA-UY — Capa de acceso a datos del dashboard
================================================
Todas las consultas del dashboard pasan por este módulo.
Estrategia: PostgreSQL primero, fallback a Parquet si la BD no está disponible.
Esto garantiza que el dashboard funcione en desarrollo sin Docker.

Funciones públicas:
    cargar_focos()          → DataFrame de focos históricos
    cargar_meteo()          → DataFrame meteorológico con índice de riesgo
    cargar_cams()           → DataFrame de calidad del aire
    cargar_forecast()       → DataFrame de pronóstico 7 días
    cargar_focos_nrt()      → DataFrame de focos NRT (últimas 24h)
    cargar_resumen_puntos() → DataFrame de último estado por punto
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import PG_CONFIG, DIR_PROCESADO, PAISES_SA, PUNTOS_METEO_SA

PAISES_ALCANCE = tuple(sorted(PAISES_SA.keys()))
PUNTOS_ALCANCE = tuple(PUNTOS_METEO_SA.keys())
SQL_SCOPE_PAISES = ", ".join(f"'{pais}'" for pais in PAISES_ALCANCE)
MAX_FOCOS_MAPA = 25000


def _filtro_espacial_sql(ciudades: tuple[str, ...] | None, radio_km: int) -> tuple[str, list]:
    """Devuelve cláusula SQL/params para focos cercanos a puntos de monitoreo."""
    if not ciudades:
        return "", []
    partes = []
    params: list = []
    for ciudad in ciudades:
        info = PUNTOS_METEO_SA.get(ciudad)
        if not info:
            continue
        partes.append(
            """
            (
                6371 * 2 * asin(sqrt(
                    power(sin(radians(%s - latitud) / 2), 2)
                    + cos(radians(latitud)) * cos(radians(%s))
                    * power(sin(radians(%s - longitud) / 2), 2)
                ))
            ) <= %s
            """
        )
        params.extend([info["lat"], info["lat"], info["lon"], radio_km])
    if not partes:
        return "", []
    return "(" + " OR ".join(partes) + ")", params


def _filtrar_focos_cercanos_parquet(df: pd.DataFrame, ciudades: tuple[str, ...] | None, radio_km: int) -> pd.DataFrame:
    if df.empty or not ciudades or not {"latitud", "longitud"}.issubset(df.columns):
        return df
    import numpy as np

    mask = pd.Series(False, index=df.index)
    lat = df["latitud"].astype(float)
    lon = df["longitud"].astype(float)
    for ciudad in ciudades:
        info = PUNTOS_METEO_SA.get(ciudad)
        if not info:
            continue
        dlat = np.radians(info["lat"] - lat)
        dlon = np.radians(info["lon"] - lon)
        a = (
            np.sin(dlat / 2) ** 2
            + np.cos(np.radians(lat)) * np.cos(np.radians(info["lat"]))
            * np.sin(dlon / 2) ** 2
        )
        distancia = 6371 * 2 * np.arcsin(np.sqrt(a))
        mask = mask | (distancia <= radio_km)
    return df[mask].copy()

# ---------------------------------------------------------------------------
# CONEXION
# ---------------------------------------------------------------------------

def _pg_disponible() -> bool:
    """Verifica si PostgreSQL responde. Falla silenciosamente."""
    try:
        import psycopg2
        conn = psycopg2.connect(**PG_CONFIG, connect_timeout=3)
        conn.close()
        return True
    except Exception:
        return False


def _query_pg(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Ejecuta una query en PostgreSQL y devuelve un DataFrame."""
    import psycopg2
    conn = psycopg2.connect(**PG_CONFIG, connect_timeout=5)
    try:
        df = pd.read_sql_query(sql, conn, params=params)
        return df
    finally:
        conn.close()


def _filtrar_fechas(df: pd.DataFrame, fecha_inicio: str | None, fecha_fin: str | None, columna: str) -> pd.DataFrame:
    if df.empty or columna not in df.columns:
        return df
    if fecha_inicio:
        df = df[df[columna] >= pd.to_datetime(fecha_inicio)]
    if fecha_fin:
        df = df[df[columna] <= pd.to_datetime(fecha_fin)]
    return df


# ---------------------------------------------------------------------------
# FOCOS DE CALOR - HISTORICO
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def obtener_rango_focos() -> dict[str, object]:
    """Rango temporal real de focos dentro del alcance ARG/BRA/URY/CHL."""
    if _pg_disponible():
        try:
            df = _query_pg(f"""
                SELECT MIN(fecha_adq) AS fecha_min, MAX(fecha_adq) AS fecha_max
                FROM focos_calor
                WHERE pais IN ({SQL_SCOPE_PAISES})
            """)
            if not df.empty and pd.notna(df.iloc[0]["fecha_min"]) and pd.notna(df.iloc[0]["fecha_max"]):
                fecha_min = pd.to_datetime(df.iloc[0]["fecha_min"]).date()
                fecha_max = pd.to_datetime(df.iloc[0]["fecha_max"]).date()
                return {
                    "fecha_min": fecha_min,
                    "fecha_max": fecha_max,
                    "anio_min": fecha_min.year,
                    "anio_max": fecha_max.year,
                    "fuente": "postgresql",
                }
        except Exception:
            pass

    p = DIR_PROCESADO / "firms_procesado.parquet"
    if p.exists():
        df = pd.read_parquet(p, columns=["fecha_adq", "pais"])
        df["fecha_adq"] = pd.to_datetime(df["fecha_adq"])
        df = df[df["pais"].isin(PAISES_ALCANCE)].copy()
        fecha_min = df["fecha_adq"].min().date()
        fecha_max = df["fecha_adq"].max().date()
        return {
            "fecha_min": fecha_min,
            "fecha_max": fecha_max,
            "anio_min": fecha_min.year,
            "anio_max": fecha_max.year,
            "fuente": "parquet",
        }

    hoy = pd.Timestamp.today().date()
    return {"fecha_min": hoy, "fecha_max": hoy, "anio_min": hoy.year, "anio_max": hoy.year, "fuente": "sin datos"}


@st.cache_data(ttl=300)
def contar_focos(fecha_inicio: str | None = None, fecha_fin: str | None = None, pais: str | None = None) -> int:
    """
    Cuenta real de focos para KPIs.
    cargar_focos() limita la muestra visual para mapas/graficos; esta
    funcion usa COUNT(*) para que las tarjetas muestren el total real.
    """
    if _pg_disponible():
        try:
            where_clauses = []
            params: list = []
            if fecha_inicio:
                where_clauses.append("fecha_adq >= %s")
                params.append(fecha_inicio)
            if fecha_fin:
                where_clauses.append("fecha_adq <= %s")
                params.append(fecha_fin)
            if pais:
                where_clauses.append("pais = %s")
                params.append(pais)

            df = _query_pg(f"""
                SELECT COUNT(*) AS total
                FROM focos_calor
                WHERE pais IN ({SQL_SCOPE_PAISES})
                {"AND " + " AND ".join(where_clauses) if where_clauses else ""}
            """, tuple(params))
            return int(df.iloc[0]["total"]) if not df.empty else 0
        except Exception:
            pass

    p = DIR_PROCESADO / "firms_procesado.parquet"
    if p.exists():
        df = pd.read_parquet(p, columns=["fecha_adq", "pais"])
        df["fecha_adq"] = pd.to_datetime(df["fecha_adq"])
        df = df[df["pais"].isin(PAISES_ALCANCE)].copy()
        if pais:
            df = df[df["pais"] == pais].copy()
        df = _filtrar_fechas(df, fecha_inicio, fecha_fin, "fecha_adq")
        return int(len(df))
    return 0


@st.cache_data(ttl=300)
def cargar_focos_por_dia(fecha_inicio: str | None = None, fecha_fin: str | None = None, pais: str | None = None) -> pd.DataFrame:
    """Serie diaria real de focos; usa agregacion para no depender de la muestra del mapa."""
    if _pg_disponible():
        try:
            where_clauses = []
            params: list = []
            if fecha_inicio:
                where_clauses.append("fecha_adq >= %s")
                params.append(fecha_inicio)
            if fecha_fin:
                where_clauses.append("fecha_adq <= %s")
                params.append(fecha_fin)
            if pais:
                where_clauses.append("pais = %s")
                params.append(pais)
            df = _query_pg(f"""
                SELECT fecha_adq::date AS fecha, COUNT(*) AS focos
                FROM focos_calor
                WHERE pais IN ({SQL_SCOPE_PAISES})
                {"AND " + " AND ".join(where_clauses) if where_clauses else ""}
                GROUP BY fecha_adq::date
                ORDER BY fecha
            """, tuple(params))
            df["fecha"] = pd.to_datetime(df["fecha"])
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception:
            pass

    p = DIR_PROCESADO / "firms_procesado.parquet"
    if p.exists():
        df = pd.read_parquet(p, columns=["fecha_adq", "pais"])
        df["fecha_adq"] = pd.to_datetime(df["fecha_adq"])
        df = df[df["pais"].isin(PAISES_ALCANCE)].copy()
        if pais:
            df = df[df["pais"] == pais].copy()
        df = _filtrar_fechas(df, fecha_inicio, fecha_fin, "fecha_adq")
        out = df.groupby(df["fecha_adq"].dt.date).size().reset_index(name="focos")
        out = out.rename(columns={"fecha_adq": "fecha"})
        out["fecha"] = pd.to_datetime(out["fecha"])
        out.attrs["fuente"] = "parquet"
        return out
    return pd.DataFrame()


@st.cache_data(ttl=300)
def calcular_estadisticas_focos(fecha_inicio: str | None = None, fecha_fin: str | None = None, pais: str | None = None) -> dict[str, object]:
    """Estadisticas reales de focos para KPIs, sin depender de la muestra visual."""
    if _pg_disponible():
        try:
            where_clauses = []
            params: list = []
            if fecha_inicio:
                where_clauses.append("fecha_adq >= %s")
                params.append(fecha_inicio)
            if fecha_fin:
                where_clauses.append("fecha_adq <= %s")
                params.append(fecha_fin)
            if pais:
                where_clauses.append("pais = %s")
                params.append(pais)

            df = _query_pg(f"""
                SELECT
                    COUNT(*) AS total,
                    AVG(potencia_radiativa) AS frp_promedio,
                    MAX(potencia_radiativa) AS frp_maximo
                FROM focos_calor
                WHERE pais IN ({SQL_SCOPE_PAISES})
                {"AND " + " AND ".join(where_clauses) if where_clauses else ""}
            """, tuple(params))
            if not df.empty:
                row = df.iloc[0]
                return {
                    "total": int(row["total"] or 0),
                    "frp_promedio": float(row["frp_promedio"] or 0),
                    "frp_maximo": float(row["frp_maximo"] or 0),
                    "fuente": "postgresql",
                }
        except Exception:
            pass

    p = DIR_PROCESADO / "firms_procesado.parquet"
    if p.exists():
        df = pd.read_parquet(p, columns=["fecha_adq", "pais", "potencia_radiativa"])
        df["fecha_adq"] = pd.to_datetime(df["fecha_adq"])
        df = df[df["pais"].isin(PAISES_ALCANCE)].copy()
        if pais:
            df = df[df["pais"] == pais].copy()
        df = _filtrar_fechas(df, fecha_inicio, fecha_fin, "fecha_adq")
        frp_promedio = df["potencia_radiativa"].mean() if not df.empty else 0
        frp_maximo = df["potencia_radiativa"].max() if not df.empty else 0
        return {
            "total": int(len(df)),
            "frp_promedio": float(frp_promedio) if pd.notna(frp_promedio) else 0.0,
            "frp_maximo": float(frp_maximo) if pd.notna(frp_maximo) else 0.0,
            "fuente": "parquet",
        }

    return {"total": 0, "frp_promedio": 0.0, "frp_maximo": 0.0, "fuente": "sin datos"}


@st.cache_data(ttl=300)
def cargar_focos(
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    pais: str | None = None,
    ciudades: tuple[str, ...] | None = None,
    radio_km: int = 100,
) -> pd.DataFrame:
    """
    Focos de calor históricos filtrados por fecha y/o país.
    Devuelve una muestra visual ordenada por FRP descendente (los mas intensos primero).
    Fuente: tabla focos_calor (PostgreSQL) o firms_procesado.parquet (fallback).
    """
    if _pg_disponible():
        try:
            where_clauses = []
            params: list = []
            if fecha_inicio:
                where_clauses.append("fecha_adq >= %s")
                params.append(fecha_inicio)
            if fecha_fin:
                where_clauses.append("fecha_adq <= %s")
                params.append(fecha_fin)
            if pais:
                where_clauses.append("pais = %s")
                params.append(pais)
            filtro_ciudades, params_ciudades = _filtro_espacial_sql(ciudades, radio_km)
            if filtro_ciudades:
                where_clauses.append(filtro_ciudades)
                params.extend(params_ciudades)

            df = _query_pg(f"""
                SELECT
                    fecha_adq,
                    latitud,
                    longitud,
                    potencia_radiativa,
                    confianza_raw,
                    confianza_num,
                    satelite,
                    dia_noche,
                    es_diurno,
                    pais
                FROM focos_calor
                WHERE pais IN ({SQL_SCOPE_PAISES})
                {"AND " + " AND ".join(where_clauses) if where_clauses else ""}
                ORDER BY potencia_radiativa DESC NULLS LAST
                LIMIT {MAX_FOCOS_MAPA}
            """, tuple(params))
            df["fecha_adq"] = pd.to_datetime(df["fecha_adq"])
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception as e:
            st.sidebar.warning(f"BD no disponible, usando parquet: {e}")

    # Fallback: parquet
    p = DIR_PROCESADO / "firms_procesado.parquet"
    if p.exists():
        df = pd.read_parquet(p)
        df["fecha_adq"] = pd.to_datetime(df["fecha_adq"])
        if "pais" in df.columns:
            df = df[df["pais"].isin(PAISES_ALCANCE)].copy()
        if pais and "pais" in df.columns:
            df = df[df["pais"] == pais].copy()
        df = _filtrar_fechas(df, fecha_inicio, fecha_fin, "fecha_adq")
        df = _filtrar_focos_cercanos_parquet(df, ciudades, radio_km)
        df = df.sort_values("potencia_radiativa", ascending=False, na_position="last").head(MAX_FOCOS_MAPA)
        df.attrs["fuente"] = "parquet"
        return df
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# FOCOS NRT
# ---------------------------------------------------------------------------

@st.cache_data(ttl=180)
def cargar_focos_nrt(ciudades: tuple[str, ...] | None = None, radio_km: int = 100) -> pd.DataFrame:
    if _pg_disponible():
        try:
            filtro_ciudades, params_ciudades = _filtro_espacial_sql(ciudades, radio_km)
            df = _query_pg(f"""
                SELECT
                    fecha_adq,
                    latitud,
                    longitud,
                    potencia_radiativa,
                    confianza_raw,
                    confianza_num,
                    satelite,
                    dia_noche,
                    es_diurno,
                    pais
                FROM focos_calor
                WHERE pais IN ({SQL_SCOPE_PAISES})
                  AND fecha_adq >= CURRENT_DATE - INTERVAL '1 day'
                  {"AND " + filtro_ciudades if filtro_ciudades else ""}
                ORDER BY fecha_adq DESC, potencia_radiativa DESC NULLS LAST
                LIMIT 5000
            """, tuple(params_ciudades))
            df["fecha_adq"] = pd.to_datetime(df["fecha_adq"])
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception:
            pass
    """Focos NRT de las últimas 24h. Solo parquet (datos muy recientes)."""
    p = DIR_PROCESADO / "firms_nrt_procesado.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    df["fecha_adq"] = pd.to_datetime(df["fecha_adq"])
    df = _filtrar_focos_cercanos_parquet(df, ciudades, radio_km)
    df.attrs["fuente"] = "parquet"
    return df


# ---------------------------------------------------------------------------
# METEOROLOGIA + INDICE DE RIESGO
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def cargar_meteo(tipo_dato: str = "historico") -> pd.DataFrame:
    """
    Datos meteorológicos con índice de riesgo.
    Fuente: vista v_riesgo_historico (PostgreSQL) o parquet (fallback).
    """
    if _pg_disponible():
        try:
            df = _query_pg(f"""
                SELECT
                    punto,
                    pais,
                    fecha,
                    tipo_dato,
                    indice_riesgo,
                    nivel_riesgo,
                    temperature_2m_max,
                    temperature_2m_min,
                    relative_humidity_2m_min,
                    wind_speed_10m_max,
                    precipitation_sum,
                    et0_fao_evapotranspiration
                FROM v_riesgo_historico
                WHERE tipo_dato = %s
                  AND pais IN ({SQL_SCOPE_PAISES})
                ORDER BY punto, fecha
            """, (tipo_dato,))
            df["fecha"] = pd.to_datetime(df["fecha"])
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception as e:
            st.sidebar.warning(f"BD no disponible, usando parquet: {e}")

    # Fallback: parquet
    frames = [pd.read_parquet(f) for f in DIR_PROCESADO.glob("meteo_procesado_*.parquet")]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["fecha"] = pd.to_datetime(df["fecha"])
    if "punto" in df.columns:
        df = df[df["punto"].isin(PUNTOS_ALCANCE)].copy()
    df.attrs["fuente"] = "parquet"
    return df


# ---------------------------------------------------------------------------
# FORECAST
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def cargar_forecast() -> pd.DataFrame:
    """
    Pronóstico de riesgo 7 días.
    Fuente: vista v_forecast_riesgo (PostgreSQL) o parquet (fallback).
    """
    if _pg_disponible():
        try:
            df = _query_pg(f"""
                SELECT
                    punto,
                    pais,
                    fecha,
                    indice_riesgo,
                    nivel_riesgo,
                    temperature_2m_max,
                    relative_humidity_2m_min,
                    wind_speed_10m_max,
                    precipitation_probability_max
                FROM v_forecast_riesgo
                WHERE pais IN ({SQL_SCOPE_PAISES})
                ORDER BY punto, fecha
            """)
            df["fecha"] = pd.to_datetime(df["fecha"])
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception as e:
            st.sidebar.warning(f"BD no disponible, usando parquet: {e}")

    p = DIR_PROCESADO / "forecast_riesgo.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    df["fecha"] = pd.to_datetime(df["fecha"])
    if "punto" in df.columns:
        df = df[df["punto"].isin(PUNTOS_ALCANCE)].copy()
    df.attrs["fuente"] = "parquet"
    return df


# ---------------------------------------------------------------------------
# CALIDAD DEL AIRE
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def cargar_cams() -> pd.DataFrame:
    """
    Datos diarios de calidad del aire.
    Fuente: tabla calidad_aire_diario (PostgreSQL) o parquet (fallback).
    """
    if _pg_disponible():
        try:
            df = _query_pg(f"""
                SELECT
                    p.nombre AS punto,
                    p.pais AS pais,
                    c.fecha,
                    c.pm10_media,
                    c.pm10_max,
                    c.pm10_p95,
                    c.pm2_5_media,
                    c.european_aqi_media,
                    c.supera_oms_pm10,
                    c.nivel_pm10,
                    c.horas_validas
                FROM calidad_aire_diario c
                JOIN puntos_monitoreo p ON p.id = c.id_punto
                WHERE p.pais IN ({SQL_SCOPE_PAISES})
                  AND p.activo = TRUE
                ORDER BY c.fecha DESC
            """)
            df["fecha"] = pd.to_datetime(df["fecha"])
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception as e:
            st.sidebar.warning(f"BD no disponible, usando parquet: {e}")

    frames = [pd.read_parquet(f) for f in DIR_PROCESADO.glob("cams_procesado_*.parquet")]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["fecha"] = pd.to_datetime(df["fecha"])
    if "punto" in df.columns:
        df = df[df["punto"].isin(PUNTOS_ALCANCE)].copy()
    df.attrs["fuente"] = "parquet"
    return df


# ---------------------------------------------------------------------------
# RESUMEN EJECUTIVO POR PUNTO (para KPIs del dashboard)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def cargar_resumen_puntos() -> pd.DataFrame:
    """
    Último estado de cada punto de monitoreo.
    Fuente: vista v_riesgo_actual (PostgreSQL) o agregación sobre parquet (fallback).
    """
    if _pg_disponible():
        try:
            df = _query_pg(
                f"SELECT * FROM v_riesgo_actual WHERE pais IN ({SQL_SCOPE_PAISES}) "
                "ORDER BY indice_riesgo DESC NULLS LAST"
            )
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception:
            pass

    # Fallback: parquet - replica v_riesgo_actual (ultima fecha historica por punto)
    frames = [pd.read_parquet(f) for f in DIR_PROCESADO.glob("meteo_procesado_*.parquet")]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df[(df.get("tipo_dato") == "historico") & df["pais"].isin(PAISES_ALCANCE)].copy()
    if df.empty:
        return pd.DataFrame()
    # Ultima fila por punto
    idx = df.groupby("punto")["fecha"].idxmax()
    df = df.loc[idx].copy()
    df = df.rename(columns={
        "temperature_2m_max": "temp_max",
        "relative_humidity_2m_min": "humedad_min",
        "wind_speed_10m_max": "viento_max",
        "precipitation_sum": "precipitacion",
    })
    cols = ["punto", "pais", "fecha", "indice_riesgo", "nivel_riesgo",
            "temp_max", "humedad_min", "viento_max", "precipitacion"]
    df = df[[c for c in cols if c in df.columns]].sort_values(
        "indice_riesgo", ascending=False, na_position="last"
    ).reset_index(drop=True)
    df.attrs["fuente"] = "parquet"
    return df


# ---------------------------------------------------------------------------
# DIAS CRITICOS
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def cargar_dias_criticos() -> pd.DataFrame:
    """Días históricos con riesgo ALTO o MUY ALTO en al menos un punto."""
    if _pg_disponible():
        try:
            df = _query_pg(f"""
                SELECT
                    fecha,
                    COUNT(DISTINCT punto) AS puntos_en_alerta,
                    COUNT(DISTINCT pais) AS paises_en_alerta,
                    MAX(indice_riesgo) AS indice_maximo,
                    STRING_AGG(DISTINCT pais, ', ' ORDER BY pais) AS paises_afectados,
                    STRING_AGG(DISTINCT punto, ', ' ORDER BY punto) AS puntos_afectados
                FROM v_riesgo_historico
                WHERE pais IN ({SQL_SCOPE_PAISES})
                  AND nivel_riesgo IN ('alto', 'muy_alto')
                GROUP BY fecha
                ORDER BY fecha DESC
            """)
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception:
            pass

    # Fallback: parquet - replica v_dias_criticos
    frames = [pd.read_parquet(f) for f in DIR_PROCESADO.glob("meteo_procesado_*.parquet")]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df[
        df["nivel_riesgo"].isin(["alto", "muy_alto"])
        & (df.get("tipo_dato") == "historico")
        & df["pais"].isin(PAISES_ALCANCE)
    ].copy()
    if df.empty:
        return pd.DataFrame()
    agg = df.groupby("fecha").agg(
        puntos_en_alerta=("punto", "nunique"),
        paises_en_alerta=("pais", "nunique"),
        indice_maximo=("indice_riesgo", "max"),
        paises_afectados=("pais", lambda s: ", ".join(sorted(s.unique()))),
        puntos_afectados=("punto", lambda s: ", ".join(sorted(s.unique()))),
    ).reset_index().sort_values("fecha", ascending=False).reset_index(drop=True)
    agg.attrs["fuente"] = "parquet"
    return agg


# ---------------------------------------------------------------------------
# METRICAS DE RENDIMIENTO (para defensa)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def cargar_riesgo_por_pais() -> pd.DataFrame:
    """Riesgo mensual agregado por país — usa vista v_riesgo_por_pais."""
    if _pg_disponible():
        try:
            df = _query_pg(
                f"SELECT * FROM v_riesgo_por_pais WHERE pais IN ({SQL_SCOPE_PAISES}) ORDER BY pais, mes"
            )
            df["mes"] = pd.to_datetime(df["mes"])
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception:
            pass

    # Fallback: parquet - replica v_riesgo_por_pais
    frames = [pd.read_parquet(f) for f in DIR_PROCESADO.glob("meteo_procesado_*.parquet")]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df[(df.get("tipo_dato") == "historico") & df["pais"].isin(PAISES_ALCANCE)].copy()
    if df.empty:
        return pd.DataFrame()
    df["mes"] = df["fecha"].dt.to_period("M").dt.to_timestamp()
    agg = df.groupby(["pais", "mes"]).agg(
        riesgo_promedio=("indice_riesgo", lambda s: round(float(s.mean()), 4) if s.notna().any() else None),
        riesgo_maximo=("indice_riesgo", lambda s: round(float(s.max()), 4) if s.notna().any() else None),
        dias_criticos=("nivel_riesgo", lambda s: int(s.isin(["alto", "muy_alto"]).sum())),
        total_registros=("indice_riesgo", "size"),
    ).reset_index().sort_values(["pais", "mes"]).reset_index(drop=True)
    agg["mes"] = pd.to_datetime(agg["mes"])
    agg.attrs["fuente"] = "parquet"
    return agg


@st.cache_data(ttl=600)
def cargar_focos_por_pais_mes() -> pd.DataFrame:
    """Focos de calor mensuales por país — usa vista v_focos_por_pais_mes."""
    if _pg_disponible():
        try:
            df = _query_pg(
                f"SELECT * FROM v_focos_por_pais_mes WHERE pais IN ({SQL_SCOPE_PAISES}) ORDER BY pais, mes"
            )
            df["mes"] = pd.to_datetime(df["mes"])
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception:
            pass

    # Fallback: parquet - replica v_focos_por_pais_mes
    p = DIR_PROCESADO / "firms_procesado.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    df["fecha_adq"] = pd.to_datetime(df["fecha_adq"])
    df = df[df["pais"].isin(PAISES_ALCANCE)].copy()
    if df.empty:
        return pd.DataFrame()
    df["mes"] = df["fecha_adq"].dt.to_period("M").dt.to_timestamp()
    agg_dict = {
        "total_focos": ("fecha_adq", "size"),
        "frp_promedio": ("potencia_radiativa", lambda s: round(float(s.mean()), 2) if s.notna().any() else None),
        "frp_maximo": ("potencia_radiativa", lambda s: round(float(s.max()), 2) if s.notna().any() else None),
    }
    if "confianza_num" in df.columns:
        agg_dict["focos_alta_confianza"] = ("confianza_num", lambda s: int((s == 3).sum()))
    agg = df.groupby(["pais", "mes"]).agg(**agg_dict).reset_index().sort_values(["pais", "mes"]).reset_index(drop=True)
    agg["mes"] = pd.to_datetime(agg["mes"])
    agg.attrs["fuente"] = "parquet"
    return agg


def medir_tiempos_consultas() -> dict[str, float]:
    """
    Mide el tiempo de ejecución de consultas representativas.
    Retorna dict con tiempos en segundos.
    Usar en la sección de métricas del informe final.
    """
    import time
    if not _pg_disponible():
        return {}

    resultados = {}
    consultas = {
        "focos_por_mes":       "SELECT DATE_TRUNC('month', fecha_adq), COUNT(*) FROM focos_calor GROUP BY 1",
        "riesgo_promedio_punto": "SELECT punto, AVG(indice_riesgo) FROM v_riesgo_historico GROUP BY punto",
        "alertas_calidad_aire": "SELECT * FROM v_alertas_calidad_aire LIMIT 100",
        "dias_criticos":        "SELECT * FROM v_dias_criticos",
    }
    for nombre, sql in consultas.items():
        t0 = time.perf_counter()
        try:
            _query_pg(sql)
            resultados[nombre] = round(time.perf_counter() - t0, 4)
        except Exception as e:
            resultados[nombre] = f"error: {e}"

    return resultados
