from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import psycopg2
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import PG_CONFIG


@st.cache_data(ttl=120)
def query(statement: str, params=()) -> pd.DataFrame:
    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cursor:
            cursor.execute(statement, params)
            columns = [column.name for column in cursor.description]
            return pd.DataFrame(cursor.fetchall(), columns=columns)


def optional_query(statement: str, params=()) -> pd.DataFrame:
    try:
        return query(statement, params)
    except Exception as error:
        st.warning(f"Metrica opcional no disponible: {error}")
        return pd.DataFrame()


st.set_page_config(page_title="Proyecto LIDIA - EC3", layout="wide")
st.title("Proyecto LIDIA | Incendios y condiciones ambientales")
st.caption("Uruguay, Argentina y Brasil | 2018-2025 | Data Warehouse PostgreSQL")

try:
    countries = query(
        """SELECT DISTINCT pais_codigo, pais_nombre
           FROM dw.dim_ubicacion
           WHERE pais_codigo IN ('URY', 'ARG', 'BRA')
           ORDER BY pais_nombre"""
    )
except Exception as error:
    st.error(f"No fue posible consultar el Data Warehouse PostgreSQL: {error}")
    st.stop()

existing_dw = bool(
    query(
        """SELECT EXISTS (
               SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'dw' AND table_name = 'fact_incendio'
                 AND column_name = 'incendio_hash'
           ) AS presente"""
    ).iloc[0]["presente"]
)
climate_temperature = "temperatura_media_c" if existing_dw else "temperatura_c"
climate_humidity = "humedad_relativa_media_pct" if existing_dw else "humedad_pct"
rain_amount = "precipitacion_acumulada_mm" if existing_dw else "precipitacion_mm"
cover_fk = "cobertura_vegetal_id" if existing_dw else "cobertura_id"
cover_pk = "cobertura_vegetal_id" if existing_dw else "cobertura_id"
cover_label = "tipo_cobertura" if existing_dw else "descripcion_cobertura"
air_pm25 = "pm25_ug_m3" if existing_dw else "pm25"
air_pm10 = "pm10_ug_m3" if existing_dw else "pm10"

selected = st.sidebar.multiselect(
    "Paises", countries["pais_codigo"].tolist(), default=countries["pais_codigo"].tolist()
)
period = st.sidebar.slider("Periodo", 2018, 2025, (2018, 2025))
params = (selected, period[0], period[1])

if existing_dw:
    monthly = query(
        """SELECT pais_codigo, pais_nombre, anio, 1 AS mes,
                  total_incendios AS focos, frp_promedio_mw,
                  total_incendios * frp_promedio_mw AS frp_total_mw
           FROM dw.mv_kpi_frp_por_pais_anio
           WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s
           ORDER BY anio, pais_codigo""",
        params,
    )
    summary = query(
        """SELECT COALESCE(SUM(total_incendios), 0)::bigint AS focos,
                  COALESCE(SUM(total_incendios * frp_promedio_mw), 0) AS frp_total,
                  COALESCE(
                      SUM(total_incendios * frp_promedio_mw) / NULLIF(SUM(total_incendios), 0),
                      0
                  ) AS frp_promedio,
                  COUNT(DISTINCT pais_codigo) AS paises,
                  COUNT(DISTINCT anio) AS meses
           FROM dw.mv_kpi_frp_por_pais_anio
           WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s""",
        params,
    ).iloc[0]
else:
    monthly = query(
        """SELECT u.pais_codigo, u.pais_nombre, d.anio, d.mes,
                  COUNT(*)::bigint AS focos,
                  COALESCE(AVG(f.frp_mw), 0) AS frp_promedio_mw,
                  COALESCE(SUM(f.frp_mw), 0) AS frp_total_mw
           FROM dw.fact_incendio f
           JOIN dw.dim_fecha d ON d.fecha_id = f.fecha_id
           JOIN dw.dim_ubicacion u ON u.ubicacion_id = f.ubicacion_id
           WHERE u.pais_codigo = ANY(%s) AND d.anio BETWEEN %s AND %s
           GROUP BY u.pais_codigo, u.pais_nombre, d.anio, d.mes
           ORDER BY d.anio, d.mes, u.pais_codigo""",
        params,
    )
    summary = query(
        """SELECT COUNT(*)::bigint AS focos,
                  COALESCE(SUM(f.frp_mw), 0) AS frp_total,
                  COALESCE(AVG(f.frp_mw), 0) AS frp_promedio,
                  COUNT(DISTINCT u.pais_codigo) AS paises,
                  COUNT(DISTINCT (d.anio, d.mes)) AS meses
           FROM dw.fact_incendio f
           JOIN dw.dim_fecha d ON d.fecha_id = f.fecha_id
           JOIN dw.dim_ubicacion u ON u.ubicacion_id = f.ubicacion_id
           WHERE u.pais_codigo = ANY(%s) AND d.anio BETWEEN %s AND %s""",
        params,
    ).iloc[0]
quality = optional_query(
    """SELECT COUNT(*)::bigint AS ejecuciones,
              COALESCE(SUM(records_loaded), 0)::bigint AS cargados,
              COALESCE(SUM(records_rejected), 0)::bigint AS rechazos
       FROM audit.etl_runs"""
    if existing_dw
    else """SELECT COUNT(*)::bigint AS ejecuciones,
                   COALESCE(SUM(filas_insertadas + filas_actualizadas), 0)::bigint AS cargados,
                   COALESCE(SUM(filas_rechazadas), 0)::bigint AS rechazos
            FROM audit.etl_runs"""
)
quality_row = quality.iloc[0] if not quality.empty else {"ejecuciones": 0, "cargados": 0, "rechazos": 0}

c1, c2, c3, c4 = st.columns(4)
c1.metric("Focos FIRMS", f"{int(summary.focos):,}")
c2.metric("FRP total (MW)", f"{float(summary.frp_total):,.1f}")
c3.metric("FRP promedio (MW)", f"{float(summary.frp_promedio):,.2f}")
c4.metric("Paises con datos", int(summary.paises))
c5, c6, c7, c8 = st.columns(4)
c5.metric("Anios cubiertos" if existing_dw else "Meses cubiertos", int(summary.meses))
c6.metric("Registros cargados ETL", f"{int(quality_row['cargados']):,}")
c7.metric("Ejecuciones ETL", int(quality_row["ejecuciones"]))
c8.metric("Rechazos ETL", int(quality_row["rechazos"]))

tab_activity, tab_environment, tab_quality = st.tabs(["Actividad", "Ambiente", "Calidad y CDC"])
with tab_activity:
    temporal_unit = "anio" if existing_dw else "mes"
    st.subheader(f"Pregunta: como evoluciona la actividad de incendios por {temporal_unit} y pais?")
    if not monthly.empty:
        chart = monthly.assign(
            periodo=pd.to_datetime(dict(year=monthly["anio"], month=monthly["mes"], day=1))
        )
        st.line_chart(chart.pivot_table(index="periodo", columns="pais_nombre", values="focos", aggfunc="sum"))
        st.subheader("Pregunta: que pais presenta mayor FRP total en el periodo?")
        st.bar_chart(monthly.groupby("pais_nombre")["frp_total_mw"].sum())
    st.subheader("Pregunta: que regiones concentran mas focos?")
    if existing_dw:
        st.info("Pendiente: materializar la agregacion regional para consultar la carga historica sin degradar la aplicacion.")
    else:
        region = query(
            """SELECT u.pais_codigo, COALESCE(u.region, 'Sin region') AS region,
                      COUNT(*)::bigint AS focos, COALESCE(AVG(f.frp_mw), 0) AS frp_promedio_mw
               FROM dw.fact_incendio f
               JOIN dw.dim_ubicacion u ON u.ubicacion_id = f.ubicacion_id
               WHERE u.pais_codigo = ANY(%s)
               GROUP BY u.pais_codigo, COALESCE(u.region, 'Sin region')
               ORDER BY focos DESC LIMIT 15""",
            (selected,),
        )
        st.dataframe(region, width="stretch", hide_index=True)

with tab_environment:
    if existing_dw:
        st.info(
            "Los cruces clima, CHIRPS y MODIS requieren vistas materializadas sobre el historico cargado; "
            "se omiten hasta generarlas para mantener tiempos de respuesta utilizables."
        )
        climate = pd.DataFrame()
        rain = pd.DataFrame()
        cover = pd.DataFrame()
    else:
        climate = query(
        f"""SELECT u.pais_codigo, d.fecha, COUNT(*)::bigint AS focos,
                  COALESCE(AVG(f.frp_mw), 0) AS frp_promedio_mw,
                  AVG(c.{climate_temperature}) AS temperatura_media_c,
                  AVG(c.{climate_humidity}) AS humedad_media_pct
           FROM dw.fact_incendio f
           JOIN dw.dim_fecha d ON d.fecha_id = f.fecha_id
           JOIN dw.dim_ubicacion u ON u.ubicacion_id = f.ubicacion_id
           LEFT JOIN dw.dim_clima c ON c.clima_id = f.clima_id
           WHERE u.pais_codigo = ANY(%s) AND d.anio BETWEEN %s AND %s
           GROUP BY u.pais_codigo, d.fecha ORDER BY d.fecha""",
        params,
    )
        rain = query(
        f"""SELECT u.pais_codigo, d.anio, d.mes, COUNT(*)::bigint AS focos,
                  AVG(p.{rain_amount}) AS precipitacion_mm_promedio
           FROM dw.fact_incendio f
           JOIN dw.dim_fecha d ON d.fecha_id = f.fecha_id
           JOIN dw.dim_ubicacion u ON u.ubicacion_id = f.ubicacion_id
           LEFT JOIN dw.dim_precipitacion p ON p.precipitacion_id = f.precipitacion_id
           WHERE u.pais_codigo = ANY(%s) AND d.anio BETWEEN %s AND %s
           GROUP BY u.pais_codigo, d.anio, d.mes ORDER BY d.anio, d.mes""",
        params,
    )
        cover = query(
        f"""SELECT u.pais_codigo, COALESCE(c.{cover_label}, 'Sin dato MODIS') AS cobertura,
                  COUNT(*)::bigint AS focos, COALESCE(AVG(f.frp_mw), 0) AS frp_promedio_mw
           FROM dw.fact_incendio f
           JOIN dw.dim_ubicacion u ON u.ubicacion_id = f.ubicacion_id
           LEFT JOIN dw.dim_cobertura_vegetal c
             ON c.{cover_pk} = f.{cover_fk}
           WHERE u.pais_codigo = ANY(%s)
           GROUP BY u.pais_codigo, COALESCE(c.{cover_label}, 'Sin dato MODIS')
           ORDER BY focos DESC""",
        (selected,),
    )
    st.subheader("Pregunta: como se relacionan focos, temperatura y humedad?")
    st.dataframe(climate.tail(30), width="stretch", hide_index=True)
    st.subheader("Pregunta: cambia la actividad con la precipitacion CHIRPS mensual?")
    if not rain.empty:
        rain_chart = rain.assign(
            periodo=pd.to_datetime(dict(year=rain["anio"], month=rain["mes"], day=1))
        ).set_index("periodo")
        st.line_chart(rain_chart[["focos", "precipitacion_mm_promedio"]])
    st.subheader("Pregunta: que coberturas MODIS se asocian a los focos?")
    st.bar_chart(cover.set_index("cobertura")["focos"] if not cover.empty else cover)

with tab_quality:
    air = (
        pd.DataFrame()
        if existing_dw
        else query(
        f"""SELECT u.pais_codigo, d.fecha, COUNT(*)::bigint AS focos,
                  AVG(a.{air_pm25}) AS pm25, AVG(a.{air_pm10}) AS pm10,
                  CASE WHEN COUNT(a.calidad_aire_id) = 0
                       THEN 'Pendiente de fuente validada' ELSE 'Disponible' END AS estado_dato
           FROM dw.fact_incendio f
           JOIN dw.dim_fecha d ON d.fecha_id = f.fecha_id
           JOIN dw.dim_ubicacion u ON u.ubicacion_id = f.ubicacion_id
           LEFT JOIN dw.dim_calidad_aire a ON a.calidad_aire_id = f.calidad_aire_id
           WHERE u.pais_codigo = ANY(%s)
           GROUP BY u.pais_codigo, d.fecha HAVING COUNT(*) >= 10
           ORDER BY d.fecha DESC LIMIT 30""",
            (selected,),
        )
    )
    runs = optional_query(
        """SELECT source_name AS fuente, status AS estado, started_at AS iniciado_en,
                  finished_at AS finalizado_en, duration_seconds AS duracion_segundos,
                  records_extracted AS filas_leidas, records_loaded AS filas_cargadas,
                  records_rejected AS filas_rechazadas
           FROM audit.etl_runs ORDER BY started_at DESC LIMIT 30"""
        if existing_dw
        else """SELECT fuente, estado, iniciado_en, finalizado_en, duracion_segundos,
                       filas_leidas, (filas_insertadas + filas_actualizadas) AS filas_cargadas,
                       filas_rechazadas
                FROM audit.etl_runs ORDER BY iniciado_en DESC LIMIT 30"""
    )
    cdc = optional_query(
        """SELECT source_name AS fuente, last_successful_run_at AS ultima_carga_exitosa,
                  last_processed_datetime AS ultima_fecha_procesada,
                  total_records_processed AS registros_procesados, last_status AS estado
           FROM audit.cdc_control ORDER BY source_name"""
        if existing_dw
        else """SELECT fuente, MAX(registrado_en) AS ultima_carga_exitosa,
                       COUNT(*) FILTER (WHERE tipo_evento = 'alta') AS altas,
                       COUNT(*) FILTER (WHERE tipo_evento = 'modificacion') AS modificaciones
                FROM audit.cdc_eventos GROUP BY fuente ORDER BY fuente"""
    )
    st.info(
        "Calidad del aire se muestra solo cuando hay datos validos cargados; "
        "en su ausencia queda documentada como pendiente."
    )
    if not air.empty:
        st.dataframe(air, width="stretch", hide_index=True)
    st.subheader("Trazabilidad y rechazos del pipeline")
    st.dataframe(runs, width="stretch", hide_index=True)
    st.subheader("Metadata CDC disponible")
    st.dataframe(cdc, width="stretch", hide_index=True)
    if existing_dw:
        st.caption(
            "El esquema activo conserva ultima fecha y hash de control; "
            "no expone un contador historico separado de modificaciones."
        )
