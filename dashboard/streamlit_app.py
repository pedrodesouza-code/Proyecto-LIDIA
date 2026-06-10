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
    mode = st.radio(
        "Modo de lectura",
        ["Uruguay en foco", "Comparativo regional"],
        help=(
            "Uruguay es el foco principal del proyecto. Argentina y Brasil se mantienen "
            "como contexto comparativo, sin ocultar ni alterar datos."
        ),
    )
    selected_manual = st.multiselect(
        "Países",
        countries["pais_codigo"].tolist(),
        default=["URY"],
        help=(
            "Por defecto se abre Uruguay. ARG y BRA quedan disponibles para comparar "
            "cuando se usa el modo Comparativo regional."
        ),
    )
    if not selected_manual:
        selected_manual = ["URY"]
    selected = ["URY"] if mode == "Uruguay en foco" else selected_manual
    regional_selected = ["URY", "ARG", "BRA"] if mode == "Uruguay en foco" else selected
    period = st.slider("Período", 2018, 2025, (2018, 2025))

params = (selected, period[0], period[1])
regional_params = (regional_selected, period[0], period[1])
uy_params = (["URY"], period[0], period[1])

monthly = query(
    """SELECT pais_codigo, pais_nombre, anio, mes, focos, frp_promedio_mw, frp_total_mw
       FROM dw.v_incendios_pais_periodo
       WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s
       ORDER BY anio, mes, pais_codigo""",
    params,
)
monthly = numeric_cols(monthly, ["anio", "mes", "focos", "frp_promedio_mw", "frp_total_mw"])
regional_monthly = query(
    """SELECT pais_codigo, pais_nombre, anio, mes, focos, frp_promedio_mw, frp_total_mw
       FROM dw.v_incendios_pais_periodo
       WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s
       ORDER BY anio, mes, pais_codigo""",
    regional_params,
)
regional_monthly = numeric_cols(regional_monthly, ["anio", "mes", "focos", "frp_promedio_mw", "frp_total_mw"])
uy_monthly = query(
    """SELECT pais_codigo, pais_nombre, anio, mes, focos, frp_promedio_mw, frp_total_mw
       FROM dw.v_incendios_pais_periodo
       WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s
       ORDER BY anio, mes""",
    uy_params,
)
uy_monthly = numeric_cols(uy_monthly, ["anio", "mes", "focos", "frp_promedio_mw", "frp_total_mw"])
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
uy_summary = query(
    """SELECT COALESCE(SUM(focos), 0)::bigint AS focos,
              COALESCE(SUM(frp_total_mw), 0) AS frp_total,
              COALESCE(SUM(frp_total_mw) / NULLIF(SUM(focos), 0), 0) AS frp_promedio,
              COUNT(DISTINCT (anio, mes)) AS meses
       FROM dw.v_incendios_pais_periodo
       WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s""",
    uy_params,
)
uy_summary = numeric_cols(uy_summary, ["focos", "frp_total", "frp_promedio", "meses"]).iloc[0]
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
            foco principal en Uruguay y conserva Argentina y Brasil como contexto comparativo dentro
            del período 2018–2025.
        </p>
        <div class="chips">
            <span class="chip">Modo: {mode}</span>
            <span class="chip">Consulta principal: {", ".join(selected)}</span>
            <span class="chip">Contexto regional: {", ".join(regional_selected)}</span>
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
        <b>Lectura general:</b> Uruguay es la lectura principal del tablero. Argentina y Brasil se usan como
        contexto comparativo regional. No se reemplazan, normalizan ni ocultan resultados: solo se cambia
        la forma visual de lectura sobre los mismos datos consultados desde PostgreSQL.
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
    st.subheader("Uruguay en foco")
    st.markdown(
        """
        <div class="section-note">
            Lectura principal del EC3: Uruguay se muestra primero para evitar que el volumen mayor de
            focos de Argentina y Brasil domine visualmente la interpretación. Los países vecinos quedan
            disponibles debajo como contexto comparativo.
        </div>
        """,
        unsafe_allow_html=True,
    )

    uy_k1, uy_k2, uy_k3, uy_k4 = st.columns(4)
    uy_k1.metric("Focos Uruguay", fmt_int(uy_summary.focos))
    uy_k2.metric("FRP total Uruguay (MW)", fmt_float(uy_summary.frp_total, 1))
    uy_k3.metric("FRP promedio Uruguay (MW)", fmt_float(uy_summary.frp_promedio, 2))
    uy_k4.metric("Meses cubiertos Uruguay", int(uy_summary.meses))

    if not uy_monthly.empty:
        uy_chart = uy_monthly.assign(
            periodo=pd.to_datetime(dict(year=uy_monthly["anio"], month=uy_monthly["mes"], day=1))
        )
        uy_left, uy_right = st.columns(2)
        with uy_left:
            fig_uy_focos = px.line(
                uy_chart,
                x="periodo",
                y="focos",
                markers=True,
                labels={"periodo": "Período", "focos": "Focos"},
                title="Uruguay: evolución mensual de focos",
            )
            fig_uy_focos.update_traces(line=dict(width=3, color=COLOR_PAIS["URY"]), marker=dict(size=7, color=COLOR_PAIS["URY"]))
            st.plotly_chart(polish(fig_uy_focos, 390), use_container_width=True, config=PLOT_CONFIG)
        with uy_right:
            fig_uy_frp = px.bar(
                uy_chart,
                x="periodo",
                y="frp_total_mw",
                labels={"periodo": "Período", "frp_total_mw": "FRP total (MW)"},
                title="Uruguay: FRP mensual",
            )
            fig_uy_frp.update_traces(marker_color=COLOR_PAIS["URY"])
            st.plotly_chart(polish(fig_uy_frp, 390), use_container_width=True, config=PLOT_CONFIG)
    else:
        st.info("No hay datos mensuales de Uruguay para el período seleccionado.")

    uy_region = query(
        """WITH base AS (
               SELECT pais_codigo,
                      NULLIF(TRIM(region), '') AS region,
                      SUM(focos)::bigint AS focos,
                      AVG(frp_promedio_mw) AS frp_promedio_mw
               FROM dw.v_incendios_region
               WHERE pais_codigo = 'URY'
               GROUP BY pais_codigo, NULLIF(TRIM(region), '')
           )
           SELECT pais_codigo, region, focos, frp_promedio_mw,
                  CASE
                      WHEN region IS NULL THEN FALSE
                      WHEN LOWER(region) IN ('sin region', 'sin región', 'sin_region', 'none', 'null') THEN FALSE
                      ELSE TRUE
                  END AS territorio_informado
           FROM base
           ORDER BY focos DESC
           LIMIT 12"""
    )
    uy_region = numeric_cols(uy_region, ["focos", "frp_promedio_mw"])
    uy_region_informada = uy_region.loc[uy_region.get("territorio_informado", False).eq(True)].copy() if not uy_region.empty else pd.DataFrame()
    if not uy_region_informada.empty:
        st.subheader("Uruguay: distribución territorial disponible")
        fig_uy_region = px.bar(
            uy_region_informada.sort_values("focos", ascending=True),
            x="focos",
            y="region",
            orientation="h",
            labels={"focos": "Focos", "region": "Territorio informado"},
            title="Uruguay: territorios informados en el DW",
            hover_data={"frp_promedio_mw": ":.2f"},
        )
        fig_uy_region.update_traces(marker_color=COLOR_PAIS["URY"])
        st.plotly_chart(polish(fig_uy_region, 430), use_container_width=True, config=PLOT_CONFIG)
    elif not uy_region.empty:
        st.warning(
            "No hay región/departamento asociado en el DW para Uruguay. "
            "El análisis territorial queda limitado a país hasta incorporar una asociación espacial administrativa válida."
        )
    if not uy_region.empty:
        st.caption("Tabla de respaldo: valores territoriales disponibles en la vista, sin asumir que sean departamentos reales.")
        st.dataframe(uy_region, width="stretch", hide_index=True)

    st.subheader("Comparación regional como contexto")
    st.markdown(
        """
        <div class="section-note">
            Esta sección conserva Uruguay, Argentina y Brasil como contexto. Para que los volúmenes de
            Argentina/Brasil no oculten la señal uruguaya, se priorizan participación porcentual, índice
            base 100 por país y FRP promedio además de valores absolutos.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not regional_monthly.empty:
        chart = regional_monthly.assign(
            periodo=pd.to_datetime(dict(year=regional_monthly["anio"], month=regional_monthly["mes"], day=1))
        )
        chart = chart.sort_values(["pais_codigo", "periodo"]).copy()
        first_by_country = chart.groupby("pais_codigo")["focos"].transform(
            lambda values: values[values > 0].iloc[0] if (values > 0).any() else 0
        )
        chart["indice_base_100"] = chart["focos"] / first_by_country.replace(0, pd.NA) * 100
        monthly_total = chart.groupby("periodo")["focos"].transform("sum")
        chart["participacion_pct"] = chart["focos"] / monthly_total.replace(0, pd.NA) * 100

        left, right = st.columns([1.45, 1])
        with left:
            fig_line = px.line(
                chart,
                x="periodo",
                y="indice_base_100",
                color="pais_nombre",
                markers=True,
                color_discrete_map=COLOR_PAIS,
                labels={"periodo": "Período", "indice_base_100": "Índice base 100", "pais_nombre": "País"},
                title="Evolución mensual comparada, índice base 100 por país",
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
            fig_bar.update_xaxes(type="log", title="FRP total (MW, escala log)")
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
                frp_promedio_mw=("frp_promedio_mw", "mean"),
            )
            fig_year = px.bar(
                yearly,
                x="anio",
                y="frp_promedio_mw",
                color="pais_nombre",
                barmode="group",
                color_discrete_map=COLOR_PAIS,
                labels={"anio": "Año", "frp_promedio_mw": "FRP promedio (MW)", "pais_nombre": "País"},
                title="FRP promedio por año y país",
                hover_data={"focos": True, "frp_total_mw": ":.1f"},
            )
            st.plotly_chart(polish(fig_year, 390), use_container_width=True, config=PLOT_CONFIG)

        with h2:
            heat = chart.groupby(["anio", "mes"], as_index=False).agg(participacion_pct=("participacion_pct", "mean"))
            if not heat.empty:
                heat_pivot = heat.pivot(index="anio", columns="mes", values="participacion_pct").fillna(0)
                fig_heat = px.imshow(
                    heat_pivot,
                    color_continuous_scale=COLOR_SCALE_BLUE,
                    labels=dict(x="Mes", y="Año", color="Participación %"),
                    title="Participación porcentual mensual promedio",
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
        """WITH base AS (
               SELECT pais_codigo,
                      NULLIF(TRIM(region), '') AS region,
                      SUM(focos)::bigint AS focos,
                      AVG(frp_promedio_mw) AS frp_promedio_mw
               FROM dw.v_incendios_region
               WHERE pais_codigo = ANY(%s)
               GROUP BY pais_codigo, NULLIF(TRIM(region), '')
           )
           SELECT pais_codigo, region, focos, frp_promedio_mw,
                  CASE
                      WHEN region IS NULL THEN FALSE
                      WHEN LOWER(region) IN ('sin region', 'sin región', 'sin_region', 'none', 'null') THEN FALSE
                      ELSE TRUE
                  END AS territorio_informado
           FROM base
           ORDER BY focos DESC
           LIMIT 15""",
        (regional_selected,),
    )
    region = numeric_cols(region, ["focos", "frp_promedio_mw"])
    if not region.empty:
        region["region_tabla"] = region["region"].fillna("No informado")
        region_informada = region.loc[region["territorio_informado"].eq(True)].copy()
    else:
        region_informada = pd.DataFrame()

    st.subheader("Distribución territorial disponible")
    st.caption(
        "Se grafican solo territorios informados por el DW. Valores como 'sin region', vacío, none o null "
        "se tratan como no informados y no se presentan como regiones reales."
    )
    if not region_informada.empty:
        fig_region = px.bar(
            region_informada.sort_values("focos", ascending=True),
            x="focos",
            y="region",
            color="pais_codigo",
            orientation="h",
            color_discrete_map=COLOR_PAIS,
            labels={"focos": "Focos", "region": "Territorio informado", "pais_codigo": "País"},
            title="Territorios informados por focos",
            hover_data={"frp_promedio_mw": ":.2f"},
        )
        st.plotly_chart(polish(fig_region, 470), use_container_width=True, config=PLOT_CONFIG)
    elif not region.empty:
        st.warning(
            "No hay región/departamento asociado en el DW. El análisis territorial queda limitado a país "
            "hasta incorporar una asociación espacial administrativa válida."
        )
    st.caption(
        "Tabla de respaldo con valores devueltos por la vista; no se interpretan valores no informados "
        "como departamentos reales."
    )
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
        regional_params,
    )
    rain = query(
        """SELECT pais_codigo, anio, mes, focos, precipitacion_mm_promedio
           FROM dw.v_incendios_precipitacion
           WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s
           ORDER BY anio, mes""",
        regional_params,
    )
    cover = query(
        """SELECT pais_codigo, cobertura, focos, frp_promedio_mw
           FROM dw.v_incendios_cobertura
           WHERE pais_codigo = ANY(%s) ORDER BY focos DESC""",
        (regional_selected,),
    )
    climate_uy = query(
        """SELECT pais_codigo, fecha, focos, frp_promedio_mw, temperatura_media_c, humedad_media_pct
           FROM dw.v_incendios_clima
           WHERE pais_codigo = 'URY' AND EXTRACT(YEAR FROM fecha) BETWEEN %s AND %s
           ORDER BY fecha DESC LIMIT 90""",
        (period[0], period[1]),
    )
    rain_uy = query(
        """SELECT pais_codigo, anio, mes, focos, precipitacion_mm_promedio
           FROM dw.v_incendios_precipitacion
           WHERE pais_codigo = 'URY' AND anio BETWEEN %s AND %s
           ORDER BY anio, mes""",
        (period[0], period[1]),
    )
    cover_uy = query(
        """SELECT pais_codigo, cobertura, focos, frp_promedio_mw
           FROM dw.v_incendios_cobertura
           WHERE pais_codigo = 'URY' ORDER BY focos DESC""",
    )
    air_uy = query(
        """SELECT pais_codigo, fecha, focos, pm25, pm10, estado_dato
           FROM dw.v_calidad_aire_alta_actividad
           WHERE pais_codigo = 'URY' ORDER BY fecha DESC LIMIT 30""",
    )
    climate = numeric_cols(climate, ["focos", "frp_promedio_mw", "temperatura_media_c", "humedad_media_pct"])
    rain = numeric_cols(rain, ["anio", "mes", "focos", "precipitacion_mm_promedio"])
    cover = numeric_cols(cover, ["focos", "frp_promedio_mw"])
    climate_uy = numeric_cols(climate_uy, ["focos", "frp_promedio_mw", "temperatura_media_c", "humedad_media_pct"])
    rain_uy = numeric_cols(rain_uy, ["anio", "mes", "focos", "precipitacion_mm_promedio"])
    cover_uy = numeric_cols(cover_uy, ["focos", "frp_promedio_mw"])
    air_uy = numeric_cols(air_uy, ["focos", "pm25", "pm10"])

    st.subheader("Uruguay: ambiente en foco")
    st.caption("Primera lectura de clima, precipitación, cobertura vegetal y calidad del aire para Uruguay.")
    uy_env_left, uy_env_right = st.columns(2)
    with uy_env_left:
        if not rain_uy.empty:
            rain_uy_plot = rain_uy.assign(periodo=pd.to_datetime(dict(year=rain_uy["anio"], month=rain_uy["mes"], day=1)))
            fig_rain_uy = go.Figure()
            fig_rain_uy.add_trace(go.Bar(x=rain_uy_plot["periodo"], y=rain_uy_plot["focos"], name="Focos", marker_color=COLOR_PAIS["URY"]))
            fig_rain_uy.add_trace(go.Scatter(
                x=rain_uy_plot["periodo"],
                y=rain_uy_plot["precipitacion_mm_promedio"],
                name="Precipitación promedio",
                yaxis="y2",
                mode="lines+markers",
                line=dict(color="#F59E0B", width=3),
            ))
            fig_rain_uy.update_layout(
                title="Uruguay: focos y precipitación mensual",
                yaxis=dict(title="Focos"),
                yaxis2=dict(title="Precipitación mm", overlaying="y", side="right"),
            )
            st.plotly_chart(polish(fig_rain_uy, 390), use_container_width=True, config=PLOT_CONFIG)
        else:
            st.info("No hay precipitación asociada para Uruguay en el período seleccionado.")
    with uy_env_right:
        if not climate_uy.empty:
            climate_uy_plot = climate_uy.copy()
            climate_uy_plot["fecha"] = pd.to_datetime(climate_uy_plot["fecha"])
            fig_climate_uy = px.scatter(
                climate_uy_plot,
                x="temperatura_media_c",
                y="humedad_media_pct",
                size="focos",
                color_discrete_sequence=[COLOR_PAIS["URY"]],
                hover_data={"fecha": True, "frp_promedio_mw": ":.2f"},
                labels={"temperatura_media_c": "Temperatura media (°C)", "humedad_media_pct": "Humedad media (%)"},
                title="Uruguay: temperatura, humedad y focos",
            )
            st.plotly_chart(polish(fig_climate_uy, 390), use_container_width=True, config=PLOT_CONFIG)
        else:
            st.info("No hay clima asociado para Uruguay en el período seleccionado.")

    uy_env_c1, uy_env_c2 = st.columns(2)
    with uy_env_c1:
        if not cover_uy.empty:
            fig_cover_uy = px.bar(
                cover_uy.sort_values("focos", ascending=True),
                x="focos",
                y="cobertura",
                orientation="h",
                labels={"focos": "Focos", "cobertura": "Cobertura"},
                title="Uruguay: focos por cobertura vegetal",
                hover_data={"frp_promedio_mw": ":.2f"},
            )
            fig_cover_uy.update_traces(marker_color=COLOR_PAIS["URY"])
            st.plotly_chart(polish(fig_cover_uy, 390), use_container_width=True, config=PLOT_CONFIG)
        else:
            st.info("No hay cobertura vegetal asociada para Uruguay.")
    with uy_env_c2:
        if not air_uy.empty:
            fig_air_uy = px.scatter(
                air_uy,
                x="pm10",
                y="pm25",
                size="focos",
                color_discrete_sequence=[COLOR_PAIS["URY"]],
                hover_data={"fecha": True, "estado_dato": True},
                labels={"pm10": "PM10", "pm25": "PM2.5"},
                title="Uruguay: calidad del aire en alta actividad",
            )
            st.plotly_chart(polish(fig_air_uy, 390), use_container_width=True, config=PLOT_CONFIG)
        else:
            st.info("No hay calidad de aire asociada para Uruguay en alta actividad.")

    st.subheader("Comparación ambiental regional")
    st.caption("Argentina y Brasil se muestran como contexto secundario, sin reemplazar la lectura principal uruguaya.")

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

    st.subheader("Focos por rango de humedad relativa")
    st.caption("Clasificación de humedad media: baja, media y alta, sin imputar valores faltantes.")
    humidity_ranges = query_optional(
        """WITH clasificado AS (
               SELECT pais_codigo, focos, frp_promedio_mw,
                      CASE
                          WHEN humedad_media_pct < 30 THEN 'Baja (<30%)'
                          WHEN humedad_media_pct >= 30 AND humedad_media_pct < 60 THEN 'Media (30%–59%)'
                          WHEN humedad_media_pct >= 60 THEN 'Alta (≥60%)'
                      END AS rango_humedad
               FROM dw.v_incendios_clima
               WHERE pais_codigo = ANY(%s)
                 AND EXTRACT(YEAR FROM fecha) BETWEEN %s AND %s
                 AND humedad_media_pct IS NOT NULL
           )
           SELECT pais_codigo, rango_humedad,
                  SUM(focos)::bigint AS focos,
                  AVG(frp_promedio_mw) AS frp_promedio_mw
           FROM clasificado
           GROUP BY pais_codigo, rango_humedad
           ORDER BY pais_codigo,
                    CASE rango_humedad
                        WHEN 'Baja (<30%)' THEN 1
                        WHEN 'Media (30%–59%)' THEN 2
                        WHEN 'Alta (≥60%)' THEN 3
                        ELSE 4
                    END""",
        params,
        missing_message="No existe la vista dw.v_incendios_clima para calcular rangos de humedad.",
    )
    humidity_ranges = numeric_cols(humidity_ranges, ["focos", "frp_promedio_mw"])
    if not humidity_ranges.empty:
        fig_humidity = px.bar(
            humidity_ranges,
            x="rango_humedad",
            y="focos",
            color="pais_codigo",
            barmode="group",
            color_discrete_map=COLOR_PAIS,
            labels={"rango_humedad": "Rango de humedad relativa", "focos": "Focos", "pais_codigo": "País"},
            title="Focos por rango de humedad relativa",
            hover_data={"frp_promedio_mw": ":.2f"},
        )
        st.plotly_chart(polish(fig_humidity, 410), use_container_width=True, config=PLOT_CONFIG)
        st.dataframe(humidity_ranges, width="stretch", hide_index=True)
    else:
        st.info("No hay datos de humedad relativa disponibles para los filtros seleccionados.")

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

    st.subheader("Cobertura de datos CAMS / Air Quality por período")
    st.caption(
        "Porcentaje de registros de alta actividad con PM2.5/PM10 disponible. "
        "Los valores nulos no se imputan ni se reemplazan por cero."
    )
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
           GROUP BY pais_codigo, anio, mes
           ORDER BY anio, mes, pais_codigo""",
        params,
        missing_message=(
            "No existe la vista dw.v_calidad_aire_alta_actividad para calcular cobertura CAMS/Air Quality."
        ),
    )
    air_coverage = numeric_cols(
        air_coverage,
        [
            "anio", "mes", "registros_periodo", "registros_pm25_validos",
            "registros_pm10_validos", "cobertura_pm25_pct", "cobertura_pm10_pct",
        ],
    )
    if not air_coverage.empty:
        air_coverage["periodo"] = pd.to_datetime(
            dict(year=air_coverage["anio"], month=air_coverage["mes"], day=1)
        )
        coverage_long = air_coverage.melt(
            id_vars=["pais_codigo", "anio", "mes", "periodo", "registros_periodo"],
            value_vars=["cobertura_pm25_pct", "cobertura_pm10_pct"],
            var_name="variable",
            value_name="cobertura_pct",
        )
        coverage_long["variable"] = coverage_long["variable"].map(
            {"cobertura_pm25_pct": "PM2.5", "cobertura_pm10_pct": "PM10"}
        )
        fig_coverage = px.line(
            coverage_long,
            x="periodo",
            y="cobertura_pct",
            color="variable",
            line_dash="pais_codigo",
            markers=True,
            labels={
                "periodo": "Período",
                "cobertura_pct": "Cobertura (%)",
                "variable": "Variable",
                "pais_codigo": "País",
            },
            title="Cobertura porcentual de PM2.5/PM10 por período",
            hover_data={"registros_periodo": True, "anio": True, "mes": True},
        )
        fig_coverage.update_yaxes(range=[0, 100])
        st.plotly_chart(polish(fig_coverage, 410), use_container_width=True, config=PLOT_CONFIG)
        st.dataframe(air_coverage, width="stretch", hide_index=True)
    else:
        st.info("No hay datos CAMS/Open-Meteo Air Quality para los filtros seleccionados.")

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
