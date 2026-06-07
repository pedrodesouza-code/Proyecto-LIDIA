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


@st.cache_data(ttl=120, show_spinner=False)
def query(statement: str, params=()) -> pd.DataFrame:
    with psycopg2.connect(**PG_CONFIG) as connection:
        with connection.cursor() as cursor:
            cursor.execute(statement, params)
            columns = [column.name for column in cursor.description]
            return pd.DataFrame(cursor.fetchall(), columns=columns)


def query_optional(statement: str, params=(), missing_message: str | None = None) -> pd.DataFrame:
    try:
        return query(statement, params)
    except psycopg2.Error as exc:
        if missing_message:
            st.info(missing_message)
        else:
            st.info(f"No se pudo consultar la vista o tabla solicitada: {exc.pgerror or exc}")
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# Configuración visual general
# ─────────────────────────────────────────────────────────────────────────────
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
            --navy-2: #123C69;
            --blue: #2563EB;
            --blue-soft: #60A5FA;
            --cyan: #22D3EE;
            --cyan-soft: #CFFAFE;
            --orange: #F59E0B;
            --green: #34D399;
            --green-soft: #D1FAE5;
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
                radial-gradient(circle at 60% 100%, rgba(52, 211, 153, .12), transparent 30%),
                linear-gradient(180deg, #F8FBFF 0%, #EEF6FF 100%);
        }

        .block-container {
            padding-top: 1.1rem;
            padding-bottom: 2.8rem;
            max-width: 1480px;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0B1F33 0%, #123C69 52%, #0E7490 125%);
            border-right: 1px solid rgba(255,255,255,.10);
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

        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] input {
            background-color: rgba(255,255,255,.08);
            border-color: rgba(255,255,255,.25);
            color: #FFFFFF;
        }

        h1, h2, h3 {
            color: var(--navy);
            letter-spacing: -.03em;
        }

        h1 {
            font-size: 2.35rem;
            line-height: 1.12;
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

        .hero-kicker {
            text-transform: uppercase;
            letter-spacing: .14em;
            font-size: .75rem;
            font-weight: 750;
            color: rgba(255,255,255,.78);
            margin-bottom: .45rem;
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

        .side-title {
            font-size: 1.2rem;
            font-weight: 780;
            margin-bottom: .28rem;
        }

        .side-subtitle {
            color: rgba(255,255,255,.78);
            font-size: .86rem;
            line-height: 1.45;
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

        [data-testid="stMetricLabel"] {
            color: var(--muted);
        }

        [data-testid="stMetricValue"] {
            color: var(--navy);
            font-weight: 780;
        }

        [data-testid="stTabs"] button {
            font-weight: 680;
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(15,23,42,.04);
        }


        /* Ajustes para evitar el rojo por defecto de Streamlit en filtros */
        [data-baseweb="tag"] {
            background-color: #2563EB !important;
            border-color: #60A5FA !important;
            color: #FFFFFF !important;
        }

        [data-baseweb="tag"] span {
            color: #FFFFFF !important;
        }

        [data-testid="stSlider"] [role="slider"] {
            background-color: #22D3EE !important;
            border-color: #22D3EE !important;
            box-shadow: 0 0 0 3px rgba(34, 211, 238, .22) !important;
        }

        [data-testid="stSlider"] div {
            accent-color: #22D3EE !important;
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
COLOR_SCALE_MIX = ["#E0F2FE", "#A7F3D0", "#22D3EE", "#2563EB", "#123C69"]

PLOT_CONFIG = {"displaylogo": False, "responsive": True, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def fmt_int(value) -> str:
    if pd.isna(value):
        return "0"
    return f"{int(value):,}".replace(",", ".")


def fmt_float(value, decimals: int = 2) -> str:
    if pd.isna(value):
        return "0"
    return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")




def numeric_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Convierte columnas numéricas que llegan desde PostgreSQL como Decimal/object.
    Esto evita errores de Plotly al usar size, color o ejes numéricos.
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# Datos y filtros
# ─────────────────────────────────────────────────────────────────────────────
countries = query(
    """SELECT DISTINCT pais_codigo, pais_nombre
       FROM dw.v_incendios_pais_periodo
       WHERE pais_codigo IN ('URY', 'ARG', 'BRA')
       ORDER BY pais_nombre"""
)

with st.sidebar:
    st.markdown(
        """
        <div class="side-title">Proyecto LIDIA · EC3</div>
        <div class="side-subtitle">Dashboard conectado al Data Warehouse PostgreSQL.</div>
        <div class="side-card">
            <b>Alcance visible</b><br>
            Uruguay, Argentina y Brasil<br><br>
            <b>Período disponible</b><br>
            2018–2025<br><br>
            <b>Tipo de análisis</b><br>
            Incendios y variables ambientales integradas.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Filtros")
    selected = st.multiselect(
        "Países", countries["pais_codigo"].tolist(), default=countries["pais_codigo"].tolist()
    )
    period = st.slider("Período", 2018, 2025, (2018, 2025))

params = (selected, period[0], period[1])

monthly = query(
    """SELECT pais_codigo, pais_nombre, anio, mes, focos, frp_promedio_mw, frp_total_mw
       FROM dw.v_incendios_pais_periodo
       WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s
       ORDER BY anio, mes, pais_codigo""",
    params,
)
monthly = numeric_cols(monthly, ["anio", "mes", "focos", "frp_promedio_mw", "frp_total_mw"])
summary = query(
    """SELECT COALESCE(SUM(focos), 0)::bigint AS focos,
              COALESCE(SUM(frp_total_mw), 0) AS frp_total,
              COALESCE(SUM(frp_total_mw) / NULLIF(SUM(focos), 0), 0) AS frp_promedio,
              COUNT(DISTINCT pais_codigo) AS paises,
              COUNT(DISTINCT (anio, mes)) AS meses
       FROM dw.v_incendios_pais_periodo
       WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s""",
    params,
)
summary = numeric_cols(summary, ["focos", "frp_total", "frp_promedio", "paises", "meses"]).iloc[0]
quality = query(
    """SELECT altas, modificaciones, descartes_auditoria, rechazos_detallados
       FROM dw.v_resumen_calidad_pipeline"""
)
quality = numeric_cols(quality, ["altas", "modificaciones", "descartes_auditoria", "rechazos_detallados"]).iloc[0]

# ─────────────────────────────────────────────────────────────────────────────
# Encabezado
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-kicker">Proyecto LIDIA · Ingeniería de Datos</div>
        <h1>Incendios y variables ambientales</h1>
        <p>
            Panel interactivo para explorar la actividad de focos FIRMS, la intensidad radiativa FRP
            y variables ambientales integradas en el Data Warehouse PostgreSQL. La vista mantiene el
            alcance definido para Uruguay, Argentina y Brasil dentro del período 2018–2025.
        </p>
        <div class="chips">
            <span class="chip">Países seleccionados: {", ".join(selected)}</span>
            <span class="chip">Período: {period[0]}–{period[1]}</span>
            <span class="chip">Data Warehouse PostgreSQL</span>
            <span class="chip">FIRMS · CHIRPS · MODIS · CAMS/Open-Meteo</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="section-note">
        <b>Lectura general:</b> el dashboard resume focos de calor, potencia radiativa, calidad del pipeline
        y cruces ambientales disponibles en las vistas del Data Warehouse. Los gráficos y mapas son una
        representación visual de los mismos datos consultados desde PostgreSQL.
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Focos FIRMS", fmt_int(summary.focos))
c2.metric("FRP total (MW)", fmt_float(summary.frp_total, 1))
c3.metric("FRP promedio (MW)", fmt_float(summary.frp_promedio, 2))
c4.metric("Países con datos", int(summary.paises))
c5, c6, c7, c8 = st.columns(4)
c5.metric("Meses cubiertos", int(summary.meses))
c6.metric("Altas CDC", fmt_int(quality.altas))
c7.metric("Modificaciones CDC", fmt_int(quality.modificaciones))
c8.metric("Rechazos detallados", fmt_int(quality.rechazos_detallados))

activity, environment, tracking = st.tabs(["Actividad", "Ambiente", "Calidad y CDC"])

# ─────────────────────────────────────────────────────────────────────────────
# Actividad
# ─────────────────────────────────────────────────────────────────────────────
with activity:
    st.subheader("Actividad mensual de focos por país")
    st.markdown(
        """
        <div class="section-note">
            Esta sección muestra la evolución temporal de los focos detectados y la distribución de la
            potencia radiativa acumulada. Permite comparar la actividad mensual entre los países seleccionados.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not monthly.empty:
        chart = monthly.assign(
            periodo=pd.to_datetime(dict(year=monthly["anio"], month=monthly["mes"], day=1))
        )

        left, right = st.columns([1.45, 1])
        with left:
            fig_line = px.line(
                chart,
                x="periodo",
                y="focos",
                color="pais_nombre",
                markers=True,
                color_discrete_map=COLOR_PAIS,
                labels={"periodo": "Período", "focos": "Focos", "pais_nombre": "País"},
                title="Evolución mensual de focos FIRMS",
            )
            fig_line.update_traces(line=dict(width=3), marker=dict(size=7))
            st.plotly_chart(polish(fig_line, 420), use_container_width=True, config=PLOT_CONFIG)

        with right:
            pais_total = monthly.groupby(["pais_codigo", "pais_nombre"], as_index=False).agg(
                focos=("focos", "sum"), frp_total_mw=("frp_total_mw", "sum")
            )
            pais_total = numeric_cols(pais_total, ["focos", "frp_total_mw"])
            fig_bar = px.bar(
                pais_total.sort_values("frp_total_mw", ascending=True),
                x="frp_total_mw",
                y="pais_nombre",
                orientation="h",
                color="pais_nombre",
                color_discrete_map=COLOR_PAIS,
                labels={"frp_total_mw": "FRP total (MW)", "pais_nombre": "País"},
                title="FRP total por país",
                hover_data={"focos": True, "pais_codigo": True},
            )
            fig_bar.update_layout(showlegend=False)
            st.plotly_chart(polish(fig_bar, 420), use_container_width=True, config=PLOT_CONFIG)

        map_left, map_right = st.columns([1.25, 1])
        with map_left:
            st.subheader("Mapa comparativo por país")
            st.caption("Mapa coroplético con polígonos reales de país. El color representa la cantidad total de focos para el período filtrado.")
            fig_map = px.choropleth(
                pais_total,
                locations="pais_codigo",
                locationmode="ISO-3",
                color="focos",
                hover_name="pais_nombre",
                hover_data={"focos": True, "frp_total_mw": ":.1f", "pais_codigo": False},
                color_continuous_scale=COLOR_SCALE_MIX,
                labels={"focos": "Focos"},
                scope="south america",
            )
            fig_map.update_geos(
                fitbounds="locations",
                visible=True,
                showcountries=True,
                countrycolor="#D8E7F5",
                showcoastlines=True,
                coastlinecolor="#B6CBE0",
                showland=True,
                landcolor="#F8FBFF",
                showocean=True,
                oceancolor="#DDF7FF",
                lakecolor="#DDF7FF",
                bgcolor="rgba(0,0,0,0)",
            )
            fig_map.update_layout(
                height=470,
                margin=dict(l=0, r=0, t=8, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                geo=dict(bgcolor="rgba(0,0,0,0)"),
                coloraxis_colorbar=dict(title="Focos"),
            )
            st.plotly_chart(fig_map, use_container_width=True, config=PLOT_CONFIG)

        with map_right:
            st.subheader("Distribución porcentual")
            st.caption("Participación de cada país seleccionado dentro del total de focos del filtro actual.")
            fig_donut = px.pie(
                pais_total,
                names="pais_nombre",
                values="focos",
                hole=.55,
                color="pais_nombre",
                color_discrete_map=COLOR_PAIS,
                title="Participación por país",
            )
            fig_donut.update_traces(textposition="inside", textinfo="percent+label")
            fig_donut.update_layout(
                height=470,
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=12, r=12, t=50, b=15),
                legend=dict(orientation="h", y=-.08),
            )
            st.plotly_chart(fig_donut, use_container_width=True, config=PLOT_CONFIG)

        st.subheader("Patrón mensual y anual")
        st.caption("Estas vistas usan la misma tabla mensual para observar diferencias por año, mes y país.")
        h1, h2 = st.columns([1.1, 1])
        with h1:
            yearly = chart.groupby(["anio", "pais_nombre"], as_index=False).agg(
                focos=("focos", "sum"),
                frp_total_mw=("frp_total_mw", "sum"),
            )
            fig_year = px.bar(
                yearly,
                x="anio",
                y="focos",
                color="pais_nombre",
                barmode="group",
                color_discrete_map=COLOR_PAIS,
                labels={"anio": "Año", "focos": "Focos", "pais_nombre": "País"},
                title="Focos por año y país",
                hover_data={"frp_total_mw": ":.1f"},
            )
            st.plotly_chart(polish(fig_year, 390), use_container_width=True, config=PLOT_CONFIG)

        with h2:
            heat = chart.groupby(["anio", "mes"], as_index=False).agg(focos=("focos", "sum"))
            if not heat.empty:
                heat_pivot = heat.pivot(index="anio", columns="mes", values="focos").fillna(0)
                fig_heat = px.imshow(
                    heat_pivot,
                    color_continuous_scale=COLOR_SCALE_BLUE,
                    labels=dict(x="Mes", y="Año", color="Focos"),
                    title="Intensidad mensual de focos",
                    aspect="auto",
                )
                st.plotly_chart(polish(fig_heat, 390), use_container_width=True, config=PLOT_CONFIG)

        st.subheader("Relación entre focos y FRP promedio")
        st.caption("Cada punto representa un registro mensual por país. El tamaño se basa en el FRP total mensual.")
        bubble = chart.dropna(subset=["focos", "frp_promedio_mw", "frp_total_mw"]).copy()
        if not bubble.empty:
            fig_bubble = px.scatter(
                bubble,
                x="focos",
                y="frp_promedio_mw",
                size="frp_total_mw",
                color="pais_nombre",
                color_discrete_map=COLOR_PAIS,
                hover_data={"anio": True, "mes": True, "frp_total_mw": ":.1f"},
                labels={"focos": "Focos mensuales", "frp_promedio_mw": "FRP promedio (MW)", "pais_nombre": "País"},
                title="Focos mensuales vs FRP promedio",
            )
            st.plotly_chart(polish(fig_bubble, 430), use_container_width=True, config=PLOT_CONFIG)
    else:
        st.info("No hay datos mensuales para los filtros seleccionados.")

    region = query(
        """SELECT pais_codigo, region, focos, frp_promedio_mw
           FROM dw.v_incendios_region
           WHERE pais_codigo = ANY(%s)
           ORDER BY focos DESC LIMIT 15""",
        (selected,),
    )
    region = numeric_cols(region, ["focos", "frp_promedio_mw"])
    st.subheader("Regiones con mayor actividad")
    st.caption("Ranking de regiones según cantidad de focos detectados, conservando los datos de la vista del Data Warehouse.")
    if not region.empty:
        fig_region = px.bar(
            region.sort_values("focos", ascending=True),
            x="focos",
            y="region",
            color="pais_codigo",
            orientation="h",
            color_discrete_map=COLOR_PAIS,
            labels={"focos": "Focos", "region": "Región", "pais_codigo": "País"},
            title="Top 15 regiones por focos",
            hover_data={"frp_promedio_mw": ":.2f"},
        )
        st.plotly_chart(polish(fig_region, 470), use_container_width=True, config=PLOT_CONFIG)
    st.dataframe(region, width="stretch", hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# Ambiente
# ─────────────────────────────────────────────────────────────────────────────
with environment:
    
    st.subheader("Cruces ambientales disponibles")
    
    st.markdown(
        """
        <div class="section-note">
            Esta sección presenta vistas que relacionan la actividad de incendios con variables climáticas,
            precipitación mensual y cobertura vegetal. Las tablas conservan los valores originales consultados.
        </div>
        """,
        unsafe_allow_html=True,
    )

    climate = query(
        """SELECT pais_codigo, fecha, focos, frp_promedio_mw, temperatura_media_c, humedad_media_pct
           FROM dw.v_incendios_clima
           WHERE pais_codigo = ANY(%s) AND EXTRACT(YEAR FROM fecha) BETWEEN %s AND %s
           ORDER BY fecha DESC LIMIT 90""",
        params,
    )
    rain = query(
        """SELECT pais_codigo, anio, mes, focos, precipitacion_mm_promedio
           FROM dw.v_incendios_precipitacion
           WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s
           ORDER BY anio, mes""",
        params,
    )
    cover = query(
        """SELECT pais_codigo, cobertura, focos, frp_promedio_mw
           FROM dw.v_incendios_cobertura
           WHERE pais_codigo = ANY(%s) ORDER BY focos DESC""",
        (selected,),
    )
    climate = numeric_cols(climate, ["focos", "frp_promedio_mw", "temperatura_media_c", "humedad_media_pct"])
    rain = numeric_cols(rain, ["anio", "mes", "focos", "precipitacion_mm_promedio"])
    cover = numeric_cols(cover, ["focos", "frp_promedio_mw"])

    left_env, right_env = st.columns([1.1, 1])
    with left_env:
        st.subheader("Actividad y precipitación mensual CHIRPS")
        st.caption("Comparación visual entre focos registrados y precipitación promedio mensual disponible.")
        if not rain.empty:
            rain_plot = rain.assign(periodo=pd.to_datetime(dict(year=rain["anio"], month=rain["mes"], day=1)))
            rain_agg = rain_plot.groupby("periodo", as_index=False).agg(
                focos=("focos", "sum"),
                precipitacion_mm_promedio=("precipitacion_mm_promedio", "mean"),
            )
            fig_rain = go.Figure()
            fig_rain.add_trace(go.Bar(
                x=rain_agg["periodo"], y=rain_agg["focos"], name="Focos", marker_color="#2563EB"
            ))
            fig_rain.add_trace(go.Scatter(
                x=rain_agg["periodo"], y=rain_agg["precipitacion_mm_promedio"], name="Precipitación promedio", yaxis="y2",
                mode="lines+markers", line=dict(color="#F59E0B", width=3), marker=dict(size=7, color="#F59E0B")
            ))
            fig_rain.update_layout(
                yaxis=dict(title="Focos"),
                yaxis2=dict(title="Precipitación mm", overlaying="y", side="right"),
                title="Focos y precipitación mensual",
            )
            st.plotly_chart(polish(fig_rain, 410), use_container_width=True, config=PLOT_CONFIG)
        else:
            st.info("No hay datos de precipitación para los filtros seleccionados.")

    with right_env:
        st.subheader("Focos por cobertura vegetal MODIS")
        st.caption("Distribución de focos según las categorías de cobertura vegetal disponibles en la vista.")
        if not cover.empty:
            fig_cover = px.bar(
                cover.sort_values("focos", ascending=True),
                x="focos",
                y="cobertura",
                color="pais_codigo",
                orientation="h",
                color_discrete_map=COLOR_PAIS,
                labels={"focos": "Focos", "cobertura": "Cobertura", "pais_codigo": "País"},
                title="Focos por cobertura vegetal",
                hover_data={"frp_promedio_mw": ":.2f"},
            )
            st.plotly_chart(polish(fig_cover, 410), use_container_width=True, config=PLOT_CONFIG)
        else:
            st.info("No hay datos de cobertura vegetal para los filtros seleccionados.")

    st.subheader("Focos, temperatura y humedad")
    st.caption("Últimos registros disponibles en la vista de incendios y clima para los filtros aplicados.")
    if not climate.empty:
        climate_plot = climate.copy()
        climate_plot["fecha"] = pd.to_datetime(climate_plot["fecha"])

        cc1, cc2 = st.columns([1.05, 1])
        with cc1:
            fig_climate = px.scatter(
                climate_plot,
                x="temperatura_media_c",
                y="humedad_media_pct",
                size="focos",
                color="pais_codigo",
                color_discrete_map=COLOR_PAIS,
                hover_data={"fecha": True, "focos": True, "frp_promedio_mw": ":.2f"},
                labels={
                    "temperatura_media_c": "Temperatura media (°C)",
                    "humedad_media_pct": "Humedad media (%)",
                    "pais_codigo": "País",
                    "focos": "Focos",
                },
                title="Temperatura, humedad y focos",
            )
            st.plotly_chart(polish(fig_climate, 420), use_container_width=True, config=PLOT_CONFIG)

        with cc2:
            climate_time = climate_plot.sort_values("fecha").groupby("fecha", as_index=False).agg(
                focos=("focos", "sum"),
                temperatura_media_c=("temperatura_media_c", "mean"),
                humedad_media_pct=("humedad_media_pct", "mean"),
            )
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(
                x=climate_time["fecha"],
                y=climate_time["temperatura_media_c"],
                mode="lines+markers",
                name="Temperatura media",
                line=dict(color="#F59E0B", width=3),
            ))
            fig_temp.add_trace(go.Scatter(
                x=climate_time["fecha"],
                y=climate_time["humedad_media_pct"],
                mode="lines+markers",
                name="Humedad media",
                yaxis="y2",
                line=dict(color="#22D3EE", width=3),
            ))
            fig_temp.update_layout(
                title="Variables climáticas en registros recientes",
                yaxis=dict(title="Temperatura media (°C)"),
                yaxis2=dict(title="Humedad media (%)", overlaying="y", side="right"),
            )
            st.plotly_chart(polish(fig_temp, 420), use_container_width=True, config=PLOT_CONFIG)
    st.subheader("Auditoría de asociación espacial ambiental")
    st.caption(
        "Trazabilidad de las asociaciones nearest neighbor entre focos FIRMS y variables ambientales, "
        "cuando el pipeline registra la corrida."
    )
    spatial_audit = query_optional(
        """SELECT variable, metodo, umbral_km, total_hechos, asociados, sin_asociar,
                  distancia_maxima_km, ejecutado_en
           FROM audit.asociacion_espacial_runs
           ORDER BY ejecutado_en DESC, variable""",
        missing_message="No existe auditoría de asociación espacial en esta base.",
    )
    spatial_audit = numeric_cols(
        spatial_audit,
        ["umbral_km", "total_hechos", "asociados", "sin_asociar", "distancia_maxima_km"],
    )
    if not spatial_audit.empty:
        spatial_audit["ejecutado_en"] = pd.to_datetime(spatial_audit["ejecutado_en"], errors="coerce")
        spatial_long = spatial_audit.melt(
            id_vars=["variable"],
            value_vars=["asociados", "sin_asociar"],
            var_name="estado",
            value_name="hechos",
        )
        fig_spatial = px.bar(
            spatial_long,
            x="variable",
            y="hechos",
            color="estado",
            barmode="group",
            color_discrete_sequence=COLOR_SEQUENCE,
            labels={"variable": "Variable ambiental", "hechos": "Hechos", "estado": "Estado"},
            title="Cobertura de asociación espacial",
        )
        st.plotly_chart(polish(fig_spatial, 390), use_container_width=True, config=PLOT_CONFIG)
        st.dataframe(spatial_audit, width="stretch", hide_index=True)
    else:
        st.info("No hay corridas de asociación espacial registradas para mostrar.")

    st.subheader("Disponibilidad de variables ambientales independientes")
    st.caption(
        "Resumen de registros ambientales cargados en tablas del DW, sin reemplazar nulos ni inferir datos ausentes."
    )
    env_inventory = query_optional(
        """SELECT 'clima' AS componente, fuente, COUNT(*)::bigint AS registros
             FROM dw.dim_clima GROUP BY fuente
           UNION ALL
           SELECT 'precipitacion' AS componente, fuente, COUNT(*)::bigint AS registros
             FROM dw.dim_precipitacion GROUP BY fuente
           UNION ALL
           SELECT 'cobertura_vegetal' AS componente, fuente, COUNT(*)::bigint AS registros
             FROM dw.dim_cobertura_vegetal GROUP BY fuente
           UNION ALL
           SELECT 'calidad_aire' AS componente, COALESCE(fuente, 'sin_fuente') AS fuente,
                  COUNT(*)::bigint AS registros
             FROM dw.dim_calidad_aire GROUP BY COALESCE(fuente, 'sin_fuente')
           ORDER BY componente, fuente""",
        missing_message="No existen las tablas ambientales esperadas en el DW.",
    )
    env_inventory = numeric_cols(env_inventory, ["registros"])
    if not env_inventory.empty:
        fig_env = px.bar(
            env_inventory,
            x="componente",
            y="registros",
            color="fuente",
            color_discrete_sequence=COLOR_SEQUENCE,
            labels={"componente": "Componente", "registros": "Registros", "fuente": "Fuente"},
            title="Registros ambientales disponibles por componente",
        )
        st.plotly_chart(polish(fig_env, 390), use_container_width=True, config=PLOT_CONFIG)
        st.dataframe(env_inventory, width="stretch", hide_index=True)
    else:
        st.info("No hay registros ambientales independientes cargados para mostrar.")

    st.dataframe(climate, width="stretch", hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# Calidad y CDC
# ─────────────────────────────────────────────────────────────────────────────
with tracking:
    
    st.subheader("Calidad del aire y trazabilidad del pipeline")
    
    st.markdown(
        """
        <div class="section-note">
            Esta sección muestra registros vinculados a calidad del aire en días de alta actividad y la
            trazabilidad operativa del pipeline ETL/CDC. Es una vista de control y evidencia del proceso.
        </div>
        """,
        unsafe_allow_html=True,
    )

    air = query(
        """SELECT pais_codigo, fecha, focos, pm25, pm10, estado_dato
           FROM dw.v_calidad_aire_alta_actividad
           WHERE pais_codigo = ANY(%s) ORDER BY fecha DESC LIMIT 30""",
        (selected,),
    )
    runs = query(
        """SELECT fuente, estado, iniciado_en, finalizado_en, duracion_segundos,
                  filas_leidas, filas_insertadas, filas_actualizadas, filas_rechazadas
           FROM dw.v_calidad_pipeline LIMIT 30"""
    )
    air = numeric_cols(air, ["focos", "pm25", "pm10"])
    runs = numeric_cols(runs, ["duracion_segundos", "filas_leidas", "filas_insertadas", "filas_actualizadas", "filas_rechazadas"])

    st.info(
        "Calidad del aire usa CAMS/Open-Meteo Air Quality cuando hay PM2.5/PM10 validado; "
        "queda nula si no existe dato compatible."
    )
    st.caption(
        f"Descartes/filtrados registrados en auditoría: {fmt_int(quality.descartes_auditoria)}. "
        "No equivalen a errores: incluyen filas fuera del alcance geográfico o temporal."
    )

    left_q, right_q = st.columns([1.15, 1])
    with left_q:
        st.subheader("Registros de calidad del aire")
        st.caption("Últimos registros disponibles de PM2.5 y PM10 asociados a días de alta actividad.")
        if not air.empty:
            fig_air = px.scatter(
                air,
                x="pm10",
                y="pm25",
                size="focos",
                color="pais_codigo",
                color_discrete_map=COLOR_PAIS,
                hover_data={"fecha": True, "estado_dato": True, "focos": True},
                labels={"pm10": "PM10", "pm25": "PM2.5", "pais_codigo": "País", "focos": "Focos"},
                title="PM10 y PM2.5 en registros disponibles",
            )
            st.plotly_chart(polish(fig_air, 390), use_container_width=True, config=PLOT_CONFIG)
        else:
            st.info("No hay registros de calidad del aire para los filtros seleccionados.")

    with right_q:
        st.subheader("Resultado del pipeline")
        st.caption("Resumen visual de filas leídas, insertadas, actualizadas y rechazadas por fuente.")
        if not runs.empty:
            run_plot = runs.groupby("fuente", as_index=False).agg(
                filas_leidas=("filas_leidas", "sum"),
                filas_insertadas=("filas_insertadas", "sum"),
                filas_actualizadas=("filas_actualizadas", "sum"),
                filas_rechazadas=("filas_rechazadas", "sum"),
            )
            run_long = run_plot.melt(id_vars="fuente", var_name="métrica", value_name="filas")
            fig_runs = px.bar(
                run_long,
                x="fuente",
                y="filas",
                color="métrica",
                barmode="group",
                color_discrete_sequence=["#2563EB", "#22D3EE", "#34D399", "#F59E0B"],
                labels={"fuente": "Fuente", "filas": "Filas", "métrica": "Métrica"},
                title="Trazabilidad ETL/CDC por fuente",
            )
            st.plotly_chart(polish(fig_runs, 390), use_container_width=True, config=PLOT_CONFIG)
        else:
            st.info("No hay registros del pipeline para mostrar.")

    st.subheader("Tabla de calidad del aire")
    st.dataframe(air, width="stretch", hide_index=True)

    st.subheader("Trazabilidad del pipeline")
    st.dataframe(runs, width="stretch", hide_index=True)

    st.subheader("Resumen de calidad del pipeline")
    st.caption("Detalle operativo de la vista de resumen de calidad usada por los KPIs superiores.")
    quality_summary = query_optional(
        "SELECT * FROM dw.v_resumen_calidad_pipeline",
        missing_message="La vista dw.v_resumen_calidad_pipeline no existe en esta base.",
    )
    quality_numeric = [
        "altas", "modificaciones", "descartes_auditoria", "rechazos_detallados",
        "filas_leidas", "filas_insertadas", "filas_actualizadas", "filas_rechazadas",
    ]
    quality_summary = numeric_cols(quality_summary, quality_numeric)
    if not quality_summary.empty:
        available_numeric = [col for col in quality_numeric if col in quality_summary.columns]
        if available_numeric:
            category = "fuente" if "fuente" in quality_summary.columns else quality_summary.columns[0]
            fig_quality = px.bar(
                quality_summary,
                x=category,
                y=available_numeric,
                barmode="group",
                color_discrete_sequence=COLOR_SEQUENCE,
                title="Resumen operativo por fuente",
            )
            st.plotly_chart(polish(fig_quality, 390), use_container_width=True, config=PLOT_CONFIG)
        st.dataframe(quality_summary, width="stretch", hide_index=True)
    else:
        st.info("La vista de resumen de calidad no tiene filas para mostrar.")

    st.subheader("Eventos CDC registrados")
    st.caption("Distingue altas, modificaciones, registros sin cambio y rechazos cuando existen eventos auditados.")
    cdc_events = query_optional(
        """SELECT fuente, tipo_evento, COUNT(*)::bigint AS eventos,
                  MAX(registrado_en) AS ultimo_evento
           FROM audit.cdc_eventos
           GROUP BY fuente, tipo_evento
           ORDER BY fuente, tipo_evento""",
        missing_message="No existe la tabla audit.cdc_eventos en esta base.",
    )
    cdc_events = numeric_cols(cdc_events, ["eventos"])
    if not cdc_events.empty:
        cdc_events["ultimo_evento"] = pd.to_datetime(cdc_events["ultimo_evento"], errors="coerce")
        fig_cdc = px.bar(
            cdc_events,
            x="fuente",
            y="eventos",
            color="tipo_evento",
            barmode="group",
            color_discrete_sequence=COLOR_SEQUENCE,
            labels={"fuente": "Fuente", "eventos": "Eventos", "tipo_evento": "Tipo de evento"},
            title="Eventos CDC por fuente",
        )
        st.plotly_chart(polish(fig_cdc, 390), use_container_width=True, config=PLOT_CONFIG)
        st.dataframe(cdc_events, width="stretch", hide_index=True)
    else:
        st.info("No hay eventos CDC registrados para mostrar.")

    st.subheader("Rechazos ETL detallados")
    st.caption("Registros aislados por reglas de calidad, conservando motivo y payload original.")
    rejects = query_optional(
        """SELECT fuente, motivo, COUNT(*)::bigint AS rechazos,
                  MAX(rechazado_en) AS ultimo_rechazo
           FROM staging.rechazos_etl
           GROUP BY fuente, motivo
           ORDER BY rechazos DESC, fuente, motivo""",
        missing_message="No existe la tabla staging.rechazos_etl en esta base.",
    )
    rejects = numeric_cols(rejects, ["rechazos"])
    if not rejects.empty:
        rejects["ultimo_rechazo"] = pd.to_datetime(rejects["ultimo_rechazo"], errors="coerce")
        fig_rejects = px.bar(
            rejects,
            x="fuente",
            y="rechazos",
            color="motivo",
            color_discrete_sequence=COLOR_SEQUENCE,
            labels={"fuente": "Fuente", "rechazos": "Rechazos", "motivo": "Motivo"},
            title="Rechazos ETL por fuente y motivo",
        )
        st.plotly_chart(polish(fig_rejects, 390), use_container_width=True, config=PLOT_CONFIG)
        st.dataframe(rejects, width="stretch", hide_index=True)
    else:
        st.info("No hay rechazos ETL registrados para mostrar.")


