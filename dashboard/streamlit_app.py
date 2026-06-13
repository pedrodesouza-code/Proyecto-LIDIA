from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import PG_CONFIG


@st.cache_data(ttl=300, show_spinner=False)
def run_query(statement: str, params=()) -> pd.DataFrame:
    with psycopg2.connect(**PG_CONFIG) as connection:
        with connection.cursor() as cursor:
            cursor.execute(statement, params)
            columns = [column.name for column in cursor.description]
            return pd.DataFrame(cursor.fetchall(), columns=columns)


def query(statement: str, params=()) -> pd.DataFrame:
    return run_query(statement, params)


def query_optional(statement: str, params=(), missing_message: str | None = None) -> pd.DataFrame:
    try:
        return run_query(statement, params)
    except psycopg2.Error as exc:
        if missing_message:
            st.info(missing_message)
        else:
            st.info(f"No se pudo consultar la vista o tabla solicitada: {exc.pgerror or exc}")
        return pd.DataFrame()


st.set_page_config(
    page_title="Proyecto LIDIA - EC3",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        :root {
            --navy: #0B1F33;
            --blue: #2563EB;
            --cyan: #22D3EE;
            --green: #34D399;
            --orange: #F59E0B;
            --bg: #F5F9FF;
            --panel: #FFFFFF;
            --text: #1E293B;
            --muted: #64748B;
            --line: #DDE6F3;
            --shadow: 0 12px 30px rgba(15, 23, 42, .08);
        }

        .stApp {
            background:
                radial-gradient(circle at 8% 3%, rgba(37, 99, 235, .15), transparent 32%),
                radial-gradient(circle at 93% 5%, rgba(34, 211, 238, .18), transparent 28%),
                linear-gradient(180deg, #F8FBFF 0%, #EEF6FF 100%);
        }

        .block-container {
            padding-top: 1.1rem;
            padding-bottom: 2.8rem;
            max-width: 1450px;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0B1F33 0%, #123C69 52%, #0E7490 125%);
        }

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] div {
            color: #F8FAFC;
        }

        h1, h2, h3 {
            color: var(--navy);
            letter-spacing: -.03em;
        }

        .hero {
            background: linear-gradient(120deg, #0B1F33 0%, #123C69 42%, #2563EB 72%, #22D3EE 125%);
            color: white;
            border-radius: 26px;
            padding: 1.8rem 2.1rem;
            box-shadow: var(--shadow);
            border: 1px solid rgba(255,255,255,.12);
            margin-bottom: 1.1rem;
        }

        .hero h1 {
            color: white;
            margin: .15rem 0 .65rem 0;
        }

        .hero p {
            color: rgba(255,255,255,.88);
            font-size: 1.02rem;
            line-height: 1.62;
            max-width: 980px;
            margin: 0;
        }

        .chips {
            display: flex;
            flex-wrap: wrap;
            gap: .55rem;
            margin-top: 1.15rem;
        }

        .chip {
            background: rgba(255,255,255,.13);
            border: 1px solid rgba(255,255,255,.22);
            border-radius: 999px;
            padding: .38rem .78rem;
            color: #FFFFFF;
            font-weight: 650;
            font-size: .82rem;
        }

        .side-card {
            border-radius: 16px;
            padding: .9rem .95rem;
            margin: .8rem 0 1rem 0;
            background: rgba(255,255,255,.08);
            border: 1px solid rgba(255,255,255,.17);
            line-height: 1.55;
            font-size: .86rem;
        }

        .section-note {
            background: rgba(255,255,255,.86);
            border: 1px solid var(--line);
            border-left: 5px solid var(--cyan);
            border-radius: 16px;
            padding: .92rem 1rem;
            color: var(--muted);
            line-height: 1.55;
            margin: .25rem 0 1rem 0;
            box-shadow: 0 4px 16px rgba(15, 23, 42, .04);
        }

        [data-testid="stMetric"] {
            background: rgba(255,255,255,.94);
            border: 1px solid var(--line);
            border-radius: 19px;
            padding: .9rem 1rem;
            box-shadow: var(--shadow);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

COLOR_PAIS = {
    "Uruguay": "#2563EB",
    "Argentina": "#22D3EE",
    "Brasil": "#34D399",
    "URY": "#2563EB",
    "ARG": "#22D3EE",
    "BRA": "#34D399",
}
COLOR_SEQUENCE = ["#2563EB", "#22D3EE", "#34D399", "#F59E0B", "#123C69", "#14B8A6"]
COLOR_SCALE_BLUE = ["#E0F2FE", "#BAE6FD", "#60A5FA", "#2563EB", "#123C69"]
PLOT_CONFIG = {"displaylogo": False, "responsive": True, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}

PREGUNTAS = [
    "1. Evolución temporal de focos de calor en Uruguay.",
    "2. Diferencias descriptivas entre Uruguay, Argentina y Brasil.",
    "3. Asociación entre temperatura media diaria y focos.",
    "4. Focos en períodos con baja humedad relativa.",
    "5. PM2.5 y PM10 en días de mayor actividad, si hay cobertura válida.",
    "6. Precipitación mensual CHIRPS y focos de calor.",
    "7. Cobertura vegetal MODIS asociada a zonas analizadas.",
    "8. Zonas geográficas de Uruguay con mayor concentración de focos.",
    "9. Cobertura porcentual de calidad del aire por período.",
    "10. Rechazos y problemas de calidad del proceso ETL.",
]

SECTION_OPTIONS = [
    "A. Resumen",
    "B-C. Temporal y región",
    "D-H. Ambiente",
    "I. Zonas Uruguay",
    "F-J. Calidad y ETL",
]


def fmt_int(value) -> str:
    if pd.isna(value):
        return "0"
    return f"{int(value):,}".replace(",", ".")


def fmt_float(value, decimals: int = 2) -> str:
    if pd.isna(value):
        return "0"
    return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def numeric_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def polish(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,.72)",
        font=dict(color="#1E293B"),
        margin=dict(l=12, r=12, t=42, b=18),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(148,163,184,.20)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148,163,184,.20)", zeroline=False)
    return fig


def add_question(label: str) -> None:
    st.markdown(f"### {label}")


countries = pd.DataFrame(
    [
        {"pais_codigo": "URY", "pais_nombre": "Uruguay"},
        {"pais_codigo": "ARG", "pais_nombre": "Argentina"},
        {"pais_codigo": "BRA", "pais_nombre": "Brasil"},
    ]
)

with st.sidebar:
    st.markdown(
        """
        <div class="side-card">
            <b>Proyecto LIDIA EC3</b><br>
            PostgreSQL Data Warehouse<br>
            Uruguay en foco; Argentina y Brasil como contexto.
        </div>
        """,
        unsafe_allow_html=True,
    )
    mode = st.radio(
        "Modo de lectura",
        ["Uruguay en foco", "Comparativo regional"],
        help="Uruguay es el foco principal. ARG/BRA se mantienen como comparación contextual.",
    )
    selected_manual = st.multiselect(
        "Países para consultas regionales",
        countries["pais_codigo"].tolist(),
        default=["URY"],
    )
    if not selected_manual:
        selected_manual = ["URY"]
    selected = ["URY"] if mode == "Uruguay en foco" else selected_manual
    regional_selected = ["URY", "ARG", "BRA"] if mode == "Uruguay en foco" else selected
    period = st.slider("Período", 2018, 2025, (2018, 2025))
    section = st.radio(
        "Sección analítica",
        SECTION_OPTIONS,
        help="Cada sección ejecuta solo sus consultas agregadas para reducir tiempos de carga.",
    )

regional_params = (regional_selected, period[0], period[1])

st.markdown(
    f"""
    <div class="hero">
        <h1>Proyecto LIDIA: incendios y variables ambientales</h1>
        <p>
            Dashboard analítico para responder las preguntas EC3 sobre focos FIRMS, clima Open-Meteo,
            precipitación CHIRPS, calidad del aire CAMS/Open-Meteo Air Quality, cobertura MODIS e INUMET.
            El brillo térmico FIRMS se trata como brillo satelital, no como temperatura del aire.
        </p>
        <div class="chips">
            <span class="chip">Modo: {mode}</span>
            <span class="chip">Países: {", ".join(regional_selected)}</span>
            <span class="chip">Período: {period[0]}–{period[1]}</span>
            <span class="chip">Sin departamentos inventados</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if section == "A. Resumen":
    country_summary = query(
        """SELECT pais_codigo, pais_nombre,
                  COALESCE(SUM(focos), 0)::bigint AS focos,
                  COALESCE(SUM(frp_total_mw), 0) AS frp_total_mw,
                  COALESCE(SUM(frp_total_mw) / NULLIF(SUM(focos), 0), 0) AS frp_promedio_mw,
                  COUNT(DISTINCT (anio, mes)) AS meses
           FROM dw.mv_dashboard_focos_pais_periodo
           WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s
           GROUP BY pais_codigo, pais_nombre
           ORDER BY pais_codigo""",
        regional_params,
    )
    country_summary = numeric_cols(country_summary, ["focos", "frp_total_mw", "frp_promedio_mw", "meses"])
    air_coverage_kpi = query_optional(
        """SELECT
                  ROUND(100.0 * COUNT(pm25) / NULLIF(COUNT(*), 0), 2) AS cobertura_pm25_pct,
                  ROUND(100.0 * COUNT(pm10) / NULLIF(COUNT(*), 0), 2) AS cobertura_pm10_pct
           FROM dw.v_calidad_aire_alta_actividad
           WHERE pais_codigo = 'URY'
             AND EXTRACT(YEAR FROM fecha) BETWEEN %s AND %s""",
        (period[0], period[1]),
    )
    air_coverage_kpi = numeric_cols(air_coverage_kpi, ["cobertura_pm25_pct", "cobertura_pm10_pct"])
    st.subheader("Sección A — Resumen ejecutivo")
    st.caption("KPIs agregados desde PostgreSQL; no se cargan tablas crudas.")
    kpi_cols = st.columns(6)
    for idx, country in enumerate(["URY", "ARG", "BRA"]):
        row = country_summary.loc[country_summary["pais_codigo"].eq(country)]
        value = row.iloc[0]["focos"] if not row.empty else 0
        kpi_cols[idx].metric(f"Focos {country}", fmt_int(value))
    uy_row = country_summary.loc[country_summary["pais_codigo"].eq("URY")]
    uy_frp = uy_row.iloc[0]["frp_promedio_mw"] if not uy_row.empty else 0
    uy_meses = uy_row.iloc[0]["meses"] if not uy_row.empty else 0
    pm25_cov = air_coverage_kpi.iloc[0]["cobertura_pm25_pct"] if not air_coverage_kpi.empty else 0
    kpi_cols[3].metric("FRP promedio URY", fmt_float(uy_frp, 2))
    kpi_cols[4].metric("Meses URY", fmt_int(uy_meses))
    kpi_cols[5].metric("Cobertura PM2.5 URY", f"{fmt_float(pm25_cov, 1)}%")
    st.markdown("#### Preguntas analíticas cubiertas")
    st.write("\n".join(f"- {item}" for item in PREGUNTAS))

elif section == "B-C. Temporal y región":
    monthly_regional = query(
        """SELECT pais_codigo, pais_nombre, anio, mes, focos, frp_promedio_mw, frp_total_mw
           FROM dw.mv_dashboard_focos_pais_periodo
           WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s
           ORDER BY anio, mes, pais_codigo""",
        regional_params,
    )
    monthly_regional = numeric_cols(monthly_regional, ["anio", "mes", "focos", "frp_promedio_mw", "frp_total_mw"])
    monthly_ury = monthly_regional.loc[monthly_regional["pais_codigo"].eq("URY")].copy()
    country_summary = query(
        """SELECT pais_codigo, pais_nombre,
                  COALESCE(SUM(focos), 0)::bigint AS focos,
                  COALESCE(SUM(frp_total_mw), 0) AS frp_total_mw,
                  COALESCE(SUM(frp_total_mw) / NULLIF(SUM(focos), 0), 0) AS frp_promedio_mw,
                  COUNT(DISTINCT (anio, mes)) AS meses
           FROM dw.mv_dashboard_focos_pais_periodo
           WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s
           GROUP BY pais_codigo, pais_nombre
           ORDER BY pais_codigo""",
        regional_params,
    )
    country_summary = numeric_cols(country_summary, ["focos", "frp_total_mw", "frp_promedio_mw", "meses"])
    add_question("1. ¿Qué evolución temporal presentan los focos de calor en Uruguay?")
    if not monthly_ury.empty:
        monthly_ury["periodo"] = pd.to_datetime(dict(year=monthly_ury["anio"], month=monthly_ury["mes"], day=1))
        fig = px.line(
            monthly_ury,
            x="periodo",
            y="focos",
            markers=True,
            labels={"periodo": "Mes", "focos": "Focos"},
            title="Uruguay: focos mensuales FIRMS",
        )
        fig.update_traces(line=dict(width=3, color=COLOR_PAIS["URY"]), marker=dict(color=COLOR_PAIS["URY"], size=7))
        st.plotly_chart(polish(fig, 410), use_container_width=True, config=PLOT_CONFIG)
    else:
        st.info("No hay focos mensuales de Uruguay para el período seleccionado.")

    add_question("2. ¿Qué diferencias descriptivas se observan entre Uruguay, Argentina y Brasil?")
    if not country_summary.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig_total = px.bar(
                country_summary.sort_values("focos", ascending=True),
                x="focos",
                y="pais_nombre",
                color="pais_nombre",
                orientation="h",
                color_discrete_map=COLOR_PAIS,
                labels={"focos": "Focos", "pais_nombre": "País"},
                title="Focos totales por país",
            )
            fig_total.update_xaxes(type="log", title="Focos (escala log para contexto regional)")
            fig_total.update_layout(showlegend=False)
            st.plotly_chart(polish(fig_total, 390), use_container_width=True, config=PLOT_CONFIG)
        with c2:
            yearly = monthly_regional.groupby(["pais_codigo", "pais_nombre", "anio"], as_index=False).agg(
                focos=("focos", "sum"),
                frp_promedio_mw=("frp_promedio_mw", "mean"),
            )
            fig_year = px.line(
                yearly,
                x="anio",
                y="focos",
                color="pais_nombre",
                markers=True,
                color_discrete_map=COLOR_PAIS,
                labels={"anio": "Año", "focos": "Focos", "pais_nombre": "País"},
                title="Evolución anual por país",
            )
            st.plotly_chart(polish(fig_year, 390), use_container_width=True, config=PLOT_CONFIG)
        st.dataframe(country_summary, width="stretch", hide_index=True)

elif section == "D-H. Ambiente":
    st.subheader("Secciones D-H — Ambiente e incendios")
    add_question("3. ¿Qué asociación se observa entre temperatura media diaria y cantidad de focos?")
    temp_daily = query(
        """SELECT pais_codigo, fecha, focos, frp_promedio_mw, temperatura_media_c, humedad_media_pct
           FROM dw.v_incendios_clima
           WHERE pais_codigo = 'URY'
             AND EXTRACT(YEAR FROM fecha) BETWEEN %s AND %s
             AND temperatura_media_c IS NOT NULL
           ORDER BY fecha""",
        (period[0], period[1]),
    )
    temp_daily = numeric_cols(temp_daily, ["focos", "frp_promedio_mw", "temperatura_media_c", "humedad_media_pct"])
    if not temp_daily.empty:
        fig_temp = px.scatter(
            temp_daily,
            x="temperatura_media_c",
            y="focos",
            size="frp_promedio_mw",
            color_discrete_sequence=[COLOR_PAIS["URY"]],
            labels={"temperatura_media_c": "Temperatura media diaria (°C)", "focos": "Focos"},
            title="Temperatura meteorológica real vs focos diarios",
            hover_data={"fecha": True, "humedad_media_pct": ":.1f"},
        )
        st.plotly_chart(polish(fig_temp, 410), use_container_width=True, config=PLOT_CONFIG)
    else:
        st.info("No hay temperatura meteorológica asociada a focos de Uruguay para el período seleccionado.")

    add_question("4. ¿Cómo varía la cantidad de focos en períodos con baja humedad relativa?")
    humidity = query(
        """WITH base AS (
              SELECT pais_codigo, focos, frp_promedio_mw,
                     CASE
                       WHEN humedad_media_pct < 40 THEN 'Baja (<40%%)'
                       WHEN humedad_media_pct <= 70 THEN 'Media (40%%-70%%)'
                       ELSE 'Alta (>70%%)'
                     END AS rango_humedad
              FROM dw.v_incendios_clima
              WHERE pais_codigo = ANY(%s)
                AND EXTRACT(YEAR FROM fecha) BETWEEN %s AND %s
                AND humedad_media_pct IS NOT NULL
           )
           SELECT pais_codigo, rango_humedad,
                  SUM(focos)::bigint AS cantidad_focos,
                  ROUND(AVG(frp_promedio_mw), 2) AS frp_promedio_mw
           FROM base
           GROUP BY pais_codigo, rango_humedad
           ORDER BY pais_codigo, rango_humedad""",
        regional_params,
    )
    humidity = numeric_cols(humidity, ["cantidad_focos", "frp_promedio_mw"])
    if not humidity.empty:
        fig_hum = px.bar(
            humidity,
            x="rango_humedad",
            y="cantidad_focos",
            color="pais_codigo",
            barmode="group",
            color_discrete_map=COLOR_PAIS,
            labels={"rango_humedad": "Rango de humedad", "cantidad_focos": "Focos"},
            title="Focos por rango de humedad relativa",
            hover_data={"frp_promedio_mw": ":.2f"},
        )
        st.plotly_chart(polish(fig_hum, 410), use_container_width=True, config=PLOT_CONFIG)
    else:
        st.info("No hay humedad relativa asociada para los filtros seleccionados.")

    add_question("6. ¿Qué patrones se observan entre precipitación mensual CHIRPS y focos?")
    rain = query(
        """SELECT pais_codigo, anio, mes, focos, precipitacion_mm_promedio
           FROM dw.mv_dashboard_incendios_precipitacion
           WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s
           ORDER BY anio, mes, pais_codigo""",
        regional_params,
    )
    rain = numeric_cols(rain, ["anio", "mes", "focos", "precipitacion_mm_promedio"])
    if not rain.empty:
        rain["periodo"] = pd.to_datetime(dict(year=rain["anio"], month=rain["mes"], day=1))
        rain_ury = rain.loc[rain["pais_codigo"].eq("URY")]
        fig_rain = go.Figure()
        fig_rain.add_trace(go.Bar(x=rain_ury["periodo"], y=rain_ury["focos"], name="Focos URY", marker_color=COLOR_PAIS["URY"]))
        fig_rain.add_trace(go.Scatter(
            x=rain_ury["periodo"],
            y=rain_ury["precipitacion_mm_promedio"],
            name="Precipitación promedio",
            yaxis="y2",
            mode="lines+markers",
            line=dict(color="#F59E0B", width=3),
        ))
        fig_rain.update_layout(
            title="Uruguay: focos y precipitación mensual",
            yaxis=dict(title="Focos"),
            yaxis2=dict(title="Precipitación mm", overlaying="y", side="right"),
        )
        st.plotly_chart(polish(fig_rain, 410), use_container_width=True, config=PLOT_CONFIG)
    else:
        st.info("No hay precipitación CHIRPS asociada para los filtros seleccionados.")

    add_question("7. ¿Qué tipos de cobertura vegetal aparecen asociados a las zonas analizadas?")
    cover = query(
        """SELECT pais_codigo, cobertura, focos, frp_promedio_mw
           FROM dw.v_incendios_cobertura
           WHERE pais_codigo = ANY(%s)
           ORDER BY focos DESC
           LIMIT 20""",
        (regional_selected,),
    )
    cover = numeric_cols(cover, ["focos", "frp_promedio_mw"])
    cover_valid = cover.loc[~cover["cobertura"].fillna("").str.contains("Sin dato", case=False, regex=False)]
    if not cover_valid.empty:
        fig_cover = px.bar(
            cover_valid.sort_values("focos", ascending=True),
            x="focos",
            y="cobertura",
            color="pais_codigo",
            orientation="h",
            color_discrete_map=COLOR_PAIS,
            labels={"focos": "Focos", "cobertura": "Cobertura vegetal"},
            title="Focos por cobertura vegetal MODIS",
            hover_data={"frp_promedio_mw": ":.2f"},
        )
        st.plotly_chart(polish(fig_cover, 430), use_container_width=True, config=PLOT_CONFIG)
    else:
        st.info("No hay cobertura vegetal MODIS asociada a los focos para los filtros seleccionados.")

elif section == "I. Zonas Uruguay":
    st.subheader("Zonas geográficas con mayor concentración de focos")
    add_question("8. ¿Qué zonas geográficas de Uruguay presentan mayor concentración de focos?")
    st.markdown(
        """
        <div class="section-note">
            Las celdas espaciales no representan departamentos administrativos. Son zonas derivadas
            de coordenadas FIRMS. El análisis departamental formal requiere una capa poligonal válida.
        </div>
        """,
        unsafe_allow_html=True,
    )
    zones = query_optional(
        """SELECT zona_espacial, latitud_grilla, longitud_grilla, cantidad_focos, frp_promedio_mw
           FROM dw.v_focos_zona_espacial_ury
           ORDER BY cantidad_focos DESC
           LIMIT 20""",
        missing_message="La vista dw.v_focos_zona_espacial_ury todavía no está aplicada en PostgreSQL.",
    )
    zones = numeric_cols(zones, ["latitud_grilla", "longitud_grilla", "cantidad_focos", "frp_promedio_mw"])
    if not zones.empty:
        left, right = st.columns([1.2, 1])
        with left:
            fig_zones = px.bar(
                zones.sort_values("cantidad_focos", ascending=True),
                x="cantidad_focos",
                y="zona_espacial",
                orientation="h",
                labels={"cantidad_focos": "Focos", "zona_espacial": "Zona geográfica"},
                title="Top 20 celdas espaciales FIRMS en Uruguay",
                hover_data={"frp_promedio_mw": ":.2f", "latitud_grilla": ":.1f", "longitud_grilla": ":.1f"},
            )
            fig_zones.update_traces(marker_color=COLOR_PAIS["URY"])
            st.plotly_chart(polish(fig_zones, 470), use_container_width=True, config=PLOT_CONFIG)
        with right:
            map_zones = zones.rename(columns={"latitud_grilla": "lat", "longitud_grilla": "lon"})
            fig_map = px.scatter_mapbox(
                map_zones,
                lat="lat",
                lon="lon",
                size="cantidad_focos",
                color="cantidad_focos",
                hover_name="zona_espacial",
                hover_data={"frp_promedio_mw": ":.2f"},
                color_continuous_scale=COLOR_SCALE_BLUE,
                zoom=5.4,
                height=470,
                title="Distribución visual de celdas, no departamentos",
            )
            fig_map.update_layout(mapbox_style="carto-positron", margin=dict(l=0, r=0, t=45, b=0))
            st.plotly_chart(fig_map, use_container_width=True, config=PLOT_CONFIG)
        st.dataframe(zones, width="stretch", hide_index=True)
    else:
        st.info("No hay celdas espaciales FIRMS disponibles para Uruguay.")

    real_departments = query(
        """SELECT NULLIF(TRIM(u.region), '') AS region,
                  COUNT(*)::bigint AS focos
           FROM dw.fact_incendio f
           JOIN dw.dim_ubicacion u ON f.ubicacion_id = u.ubicacion_id
           JOIN dw.dim_fecha d ON f.fecha_id = d.fecha_id
           WHERE u.pais_codigo = 'URY'
             AND d.anio BETWEEN %s AND %s
             AND u.region IS NOT NULL
             AND TRIM(u.region) <> ''
           GROUP BY NULLIF(TRIM(u.region), '')
           ORDER BY focos DESC""",
        (period[0], period[1]),
    )
    if real_departments.empty:
        st.info(
            "El análisis de focos FIRMS por departamento queda pendiente hasta cargar una capa Polygon/MultiPolygon "
            "válida. El dashboard no usa ubicación, puntos INUMET ni coordenadas como reemplazo de departamento."
        )
    else:
        st.subheader("Focos FIRMS por departamento")
        st.dataframe(real_departments, width="stretch", hide_index=True)

elif section == "F-J. Calidad y ETL":
    quality_summary = query_optional(
        """SELECT altas, modificaciones, descartes_auditoria, rechazos_detallados
           FROM dw.v_resumen_calidad_pipeline"""
    )
    quality_summary = numeric_cols(quality_summary, ["altas", "modificaciones", "descartes_auditoria", "rechazos_detallados"])
    st.subheader("Secciones F, I y J — Calidad del aire y calidad del pipeline")
    add_question("5. ¿Qué diferencias se observan en PM2.5 y PM10 durante mayor actividad de focos?")
    air_activity = query_optional(
        """WITH daily AS (
              SELECT u.pais_codigo, fe.fecha,
                     COUNT(*)::bigint AS focos,
                     AVG(a.pm25) AS pm25,
                     AVG(a.pm10) AS pm10
              FROM dw.fact_incendio f
              JOIN dw.dim_fecha fe ON f.fecha_id = fe.fecha_id
              JOIN dw.dim_ubicacion u ON f.ubicacion_id = u.ubicacion_id
              LEFT JOIN dw.dim_calidad_aire a ON a.calidad_aire_id = f.calidad_aire_id
              WHERE u.pais_codigo = ANY(%s)
                AND fe.anio BETWEEN %s AND %s
              GROUP BY u.pais_codigo, fe.fecha
           ),
           thresholds AS (
              SELECT pais_codigo, percentile_cont(0.75) WITHIN GROUP (ORDER BY focos) AS p75_focos
              FROM daily
              GROUP BY pais_codigo
           )
           SELECT d.pais_codigo,
                  CASE WHEN d.focos >= t.p75_focos THEN 'Alta actividad' ELSE 'Baja/media actividad' END AS actividad,
                  COUNT(*)::bigint AS dias,
                  COUNT(d.pm25)::bigint AS dias_pm25_validos,
                  COUNT(d.pm10)::bigint AS dias_pm10_validos,
                  ROUND(AVG(d.pm25)::numeric, 2) AS pm25_promedio,
                  ROUND(AVG(d.pm10)::numeric, 2) AS pm10_promedio
           FROM daily d
           JOIN thresholds t ON t.pais_codigo = d.pais_codigo
           GROUP BY d.pais_codigo, CASE WHEN d.focos >= t.p75_focos THEN 'Alta actividad' ELSE 'Baja/media actividad' END
           ORDER BY d.pais_codigo, actividad""",
        regional_params,
    )
    air_activity = numeric_cols(
        air_activity,
        ["dias", "dias_pm25_validos", "dias_pm10_validos", "pm25_promedio", "pm10_promedio"],
    )
    if not air_activity.empty and (air_activity["dias_pm25_validos"].sum() + air_activity["dias_pm10_validos"].sum()) > 0:
        air_long = air_activity.melt(
            id_vars=["pais_codigo", "actividad", "dias"],
            value_vars=["pm25_promedio", "pm10_promedio"],
            var_name="contaminante",
            value_name="valor_promedio",
        ).dropna(subset=["valor_promedio"])
        fig_air = px.bar(
            air_long,
            x="actividad",
            y="valor_promedio",
            color="contaminante",
            barmode="group",
            facet_col="pais_codigo",
            labels={"actividad": "Actividad de focos", "valor_promedio": "Promedio", "contaminante": "Variable"},
            title="PM2.5 y PM10 por nivel de actividad de focos",
        )
        st.plotly_chart(polish(fig_air, 430), use_container_width=True, config=PLOT_CONFIG)
        st.dataframe(air_activity, width="stretch", hide_index=True)
    else:
        st.info("No hay cobertura válida de PM2.5/PM10 para comparar alta y baja actividad sin imputar datos.")

    add_question("9. ¿Qué porcentaje de cobertura de datos tiene calidad del aire por período?")
    air_coverage = query_optional(
        """SELECT pais_codigo,
                  EXTRACT(YEAR FROM fecha)::int AS anio,
                  EXTRACT(MONTH FROM fecha)::int AS mes,
                  COUNT(*)::bigint AS registros_periodo,
                  COUNT(pm25)::bigint AS registros_pm25_validos,
                  COUNT(pm10)::bigint AS registros_pm10_validos,
                  ROUND(100.0 * COUNT(pm25) / NULLIF(COUNT(*), 0), 2) AS cobertura_pm25_pct,
                  ROUND(100.0 * COUNT(pm10) / NULLIF(COUNT(*), 0), 2) AS cobertura_pm10_pct
           FROM dw.v_calidad_aire_alta_actividad
           WHERE pais_codigo = ANY(%s)
             AND EXTRACT(YEAR FROM fecha) BETWEEN %s AND %s
           GROUP BY pais_codigo, EXTRACT(YEAR FROM fecha), EXTRACT(MONTH FROM fecha)
           ORDER BY anio, mes, pais_codigo""",
        regional_params,
    )
    air_coverage = numeric_cols(
        air_coverage,
        ["anio", "mes", "registros_periodo", "registros_pm25_validos", "registros_pm10_validos", "cobertura_pm25_pct", "cobertura_pm10_pct"],
    )
    if not air_coverage.empty:
        air_coverage["periodo"] = pd.to_datetime(dict(year=air_coverage["anio"], month=air_coverage["mes"], day=1))
        cov_long = air_coverage.melt(
            id_vars=["pais_codigo", "periodo"],
            value_vars=["cobertura_pm25_pct", "cobertura_pm10_pct"],
            var_name="variable",
            value_name="cobertura_pct",
        )
        fig_cov = px.line(
            cov_long,
            x="periodo",
            y="cobertura_pct",
            color="variable",
            line_dash="pais_codigo",
            markers=True,
            labels={"periodo": "Período", "cobertura_pct": "Cobertura %", "variable": "Variable"},
            title="Cobertura CAMS/Open-Meteo Air Quality por período",
        )
        fig_cov.update_yaxes(range=[0, 100])
        st.plotly_chart(polish(fig_cov, 410), use_container_width=True, config=PLOT_CONFIG)
    else:
        st.info("No hay períodos con calidad de aire disponible en la vista analítica.")

    add_question("10. ¿Qué registros deben ser rechazados o tratados por problemas de calidad ETL?")
    rejects = query_optional(
        """SELECT fuente, motivo, COUNT(*)::bigint AS rechazos,
                  MAX(rechazado_en) AS ultimo_rechazo
           FROM staging.rechazos_etl
           GROUP BY fuente, motivo
           ORDER BY rechazos DESC, fuente, motivo
           LIMIT 30""",
        missing_message="No existe la tabla staging.rechazos_etl en esta base.",
    )
    rejects = numeric_cols(rejects, ["rechazos"])
    if not rejects.empty:
        fig_rejects = px.bar(
            rejects,
            x="fuente",
            y="rechazos",
            color="motivo",
            color_discrete_sequence=COLOR_SEQUENCE,
            labels={"fuente": "Fuente", "rechazos": "Rechazos", "motivo": "Motivo"},
            title="Rechazos ETL por fuente y motivo",
        )
        st.plotly_chart(polish(fig_rejects, 410), use_container_width=True, config=PLOT_CONFIG)
        st.dataframe(rejects, width="stretch", hide_index=True)
    else:
        st.info("No hay rechazos ETL registrados para mostrar.")

    if not quality_summary.empty:
        q = quality_summary.iloc[0]
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Altas CDC", fmt_int(q.altas))
        q2.metric("Modificaciones CDC", fmt_int(q.modificaciones))
        q3.metric("Descartes auditoría", fmt_int(q.descartes_auditoria))
        q4.metric("Rechazos detallados", fmt_int(q.rechazos_detallados))
