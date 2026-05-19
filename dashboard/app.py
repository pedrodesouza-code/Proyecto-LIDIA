"""
SINIA-UY — Dashboard de Monitoreo de Incendios Forestales
Ejecutar con: streamlit run dashboard/app.py

Fuente de datos: PostgreSQL (primario) con fallback a Parquet.
Ver dashboard/db.py para la capa de acceso a datos.
"""
from pathlib import Path
import sys
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import PUNTOS_METEO_SA

st.set_page_config(
    page_title="SINIA-UY | Monitor de Incendios Regional",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

PROCESSED = PROJECT_ROOT / "data" / "processed"
RAW_METEO = PROJECT_ROOT / "data" / "raw" / "meteo"

from dashboard.db import (
    calcular_estadisticas_focos,
    contar_focos,
    cargar_focos,
    cargar_focos_por_dia,
    cargar_focos_nrt,
    cargar_meteo,
    cargar_forecast,
    cargar_cams,
    cargar_resumen_puntos,
    cargar_dias_criticos,
    cargar_riesgo_por_pais,
    cargar_focos_por_pais_mes,
    obtener_rango_focos,
    _pg_disponible,
)

COLORES_RIESGO = {
    "bajo":     "#2ecc71",
    "moderado": "#f39c12",
    "alto":     "#e67e22",
    "muy_alto": "#e74c3c",
}

UMBRAL_ALERTA_RIESGO = 0.65
UMBRAL_FOCOS_ALERTA  = 10

MAPA_FOCOS = {
    None: {"lat": -20.0, "lon": -58.0, "zoom": 3.0},
    "BRA": {"lat": -14.0, "lon": -52.0, "zoom": 3.2},
    "ARG": {"lat": -38.0, "lon": -64.0, "zoom": 3.5},
    "URY": {"lat": -32.7, "lon": -56.0, "zoom": 6.2},
    "CHL": {"lat": -38.8, "lon": -72.2, "zoom": 4.2},
}


def _render_mapa_focos(
    df: pd.DataFrame,
    pais: str | None,
    color_por_confianza: bool,
    height: int = 460,
    centro_override: dict[str, float] | None = None,
):
    """Mapa reutilizable para focos historicos y NRT."""
    df_map = df.dropna(subset=["latitud", "longitud"]) if not df.empty else df
    if df_map.empty:
        return None
    centro = centro_override or MAPA_FOCOS.get(pais, MAPA_FOCOS[None])
    columna_color = "confianza_num" if color_por_confianza and "confianza_num" in df_map.columns else "potencia_radiativa"
    fig = px.scatter_mapbox(
        df_map,
        lat="latitud",
        lon="longitud",
        color=columna_color if columna_color in df_map.columns else None,
        size="potencia_radiativa" if "potencia_radiativa" in df_map.columns else None,
        size_max=18,
        color_continuous_scale=["yellow", "orange", "red"],
        hover_data={
            "latitud": ":.4f",
            "longitud": ":.4f",
            "fecha_adq": True,
            "potencia_radiativa": ":.2f",
            "pais": True,
        },
        mapbox_style="carto-positron",
        center={"lat": centro["lat"], "lon": centro["lon"]},
        zoom=centro["zoom"],
        height=height,
    )
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar_title="Confianza" if columna_color == "confianza_num" else "FRP",
    )
    return fig


def _distancia_km(lat1: pd.Series, lon1: pd.Series, lat2: float, lon2: float) -> pd.Series:
    """Distancia haversine entre una serie de coordenadas y un punto."""
    import numpy as np

    radio_tierra = 6371.0
    lat1_rad = np.radians(lat1.astype(float))
    lon1_rad = np.radians(lon1.astype(float))
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    return 2 * radio_tierra * np.arcsin(np.sqrt(a))


def _filtrar_focos_por_ciudades(df: pd.DataFrame, ciudades: list[str], radio_km: int) -> pd.DataFrame:
    if df.empty or not ciudades or not {"latitud", "longitud"}.issubset(df.columns):
        return df
    masks = []
    for ciudad in ciudades:
        info = PUNTOS_METEO_SA.get(ciudad)
        if not info:
            continue
        masks.append(_distancia_km(df["latitud"], df["longitud"], info["lat"], info["lon"]) <= radio_km)
    if not masks:
        return df.iloc[0:0].copy()
    mask = masks[0]
    for extra in masks[1:]:
        mask = mask | extra
    return df[mask].copy()


def _centro_ciudades(ciudades: list[str], pais: str | None) -> dict[str, float] | None:
    infos = [PUNTOS_METEO_SA[c] for c in ciudades if c in PUNTOS_METEO_SA]
    if not infos:
        return None
    zoom = 7.0 if len(infos) == 1 else MAPA_FOCOS.get(pais, MAPA_FOCOS[None])["zoom"]
    return {
        "lat": sum(i["lat"] for i in infos) / len(infos),
        "lon": sum(i["lon"] for i in infos) / len(infos),
        "zoom": zoom,
    }

# ── Sidebar — filtros (se definen ANTES de cargar datos) ─────────────────────
st.sidebar.title("SINIA-UY")
st.sidebar.caption("Sistema de Monitoreo de Incendios Forestales · UY / BRA / ARG / CHL")
st.sidebar.caption("4 países · 36 puntos · Uruguay completo + Chile volcánico")
st.sidebar.caption("UTEC · Ingeniería de Datos · 2026")
st.sidebar.divider()

pagina = st.sidebar.radio(
    "Sección",
    [
        "Resumen General",
        "Focos de Calor",
        "Índice de Riesgo",
        "Calidad del Aire",
        "Análisis de Riesgo",
        "Comparativo por País",
        "Tiempo Real",
        "Fuentes y Datos Crudos",
    ],
)

# Filtro de período (determina qué datos se cargan desde PG)
st.sidebar.divider()
rango_focos = obtener_rango_focos()
opciones_periodo = ["Todo el período"] + list(range(int(rango_focos["anio_max"]), int(rango_focos["anio_min"]) - 1, -1))
periodo_sel = st.sidebar.selectbox(
    "Período",
    opciones_periodo,
    index=0,
    help="Seleccioná todo el rango real disponible o un año puntual. Los datos se cargan desde PostgreSQL.",
)
if periodo_sel == "Todo el período":
    fecha_inicio_sel = str(rango_focos["fecha_min"])
    fecha_fin_sel = str(rango_focos["fecha_max"])
    periodo_label = f"{rango_focos['fecha_min']} a {rango_focos['fecha_max']}"
else:
    anio_sel = int(periodo_sel)
    fecha_inicio_sel = f"{anio_sel}-01-01"
    fecha_fin_sel = f"{anio_sel}-12-31"
    periodo_label = str(anio_sel)

# Filtro de país
PAISES_DISP = {
    "Todos": None,
    "Chile (CHL)":     "CHL",
    "Uruguay (URY)":   "URY",
    "Brasil (BRA)":    "BRA",
    "Argentina (ARG)": "ARG",
}
pais_sel_label = st.sidebar.selectbox("País", list(PAISES_DISP.keys()))
pais_sel = PAISES_DISP[pais_sel_label]
alcance_nrt_label = "ARG/BRA/URY/CHL" if pais_sel is None else pais_sel

ciudades_disponibles = [
    nombre for nombre, info in PUNTOS_METEO_SA.items()
    if pais_sel is None or info["pais"] == pais_sel
]
ciudades_disponibles = sorted(ciudades_disponibles)
ciudades_sel = st.sidebar.multiselect(
    "Ciudades / puntos",
    ciudades_disponibles,
    default=[],
    help="Filtra meteorología, calidad del aire y focos cercanos a los puntos seleccionados.",
)
radio_focos_km = st.sidebar.slider(
    "Radio focos por ciudad (km)",
    min_value=25,
    max_value=300,
    value=100,
    step=25,
    help="Los focos FIRMS no vienen asociados a una ciudad; se muestran los que caen dentro de este radio.",
)
alcance_ciudades_label = ", ".join(ciudades_sel) if ciudades_sel else alcance_nrt_label
centro_ciudades = _centro_ciudades(ciudades_sel, pais_sel)

# ── Carga de datos (con filtros ya seleccionados) ─────────────────────────────
ciudades_tuple = tuple(ciudades_sel)
firms  = cargar_focos(fecha_inicio_sel, fecha_fin_sel, pais_sel, ciudades_tuple, radio_focos_km)
focos_diarios = cargar_focos_por_dia(fecha_inicio_sel, fecha_fin_sel, pais_sel)
total_focos_periodo = contar_focos(fecha_inicio_sel, fecha_fin_sel, pais_sel)
stats_focos = calcular_estadisticas_focos(fecha_inicio_sel, fecha_fin_sel, pais_sel)
nrt    = cargar_focos_nrt(ciudades_tuple, radio_focos_km)
meteo  = cargar_meteo("historico")
fc     = cargar_forecast()
cams   = cargar_cams()

# Filtro de fechas adicional dentro del período
if pagina != "Tiempo Real":
    st.sidebar.divider()
    fecha_min = pd.to_datetime(fecha_inicio_sel).date()
    fecha_max = pd.to_datetime(fecha_fin_sel).date()
    rango = st.sidebar.date_input(
        "Rango de fechas",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max,
    )
    if isinstance(rango, (list, tuple)) and len(rango) == 2:
        if not firms.empty:
            firms = firms[firms["fecha_adq"].dt.date.between(rango[0], rango[1])]
        focos_diarios = cargar_focos_por_dia(str(rango[0]), str(rango[1]), pais_sel)
        total_focos_periodo = contar_focos(str(rango[0]), str(rango[1]), pais_sel)
        stats_focos = calcular_estadisticas_focos(str(rango[0]), str(rango[1]), pais_sel)
        periodo_label = f"{rango[0]} a {rango[1]}"

# Aplicar filtro de país a meteo/forecast/cams (focos ya vienen filtrados de PG)
if pais_sel:
    if not firms.empty and "pais" in firms.columns:
        firms = firms[firms["pais"] == pais_sel]
    if not nrt.empty and "pais" in nrt.columns:
        nrt = nrt[nrt["pais"] == pais_sel]
    if not meteo.empty and "pais" in meteo.columns:
        meteo = meteo[meteo["pais"] == pais_sel]
    if not fc.empty and "pais" in fc.columns:
        fc = fc[fc["pais"] == pais_sel]
    if not cams.empty and "pais" in cams.columns:
        cams = cams[cams["pais"] == pais_sel]

if ciudades_sel:
    firms = _filtrar_focos_por_ciudades(firms, ciudades_sel, radio_focos_km)
    nrt = _filtrar_focos_por_ciudades(nrt, ciudades_sel, radio_focos_km)
    if not meteo.empty and "punto" in meteo.columns:
        meteo = meteo[meteo["punto"].isin(ciudades_sel)]
    if not fc.empty and "punto" in fc.columns:
        fc = fc[fc["punto"].isin(ciudades_sel)]
    if not cams.empty and "punto" in cams.columns:
        cams = cams[cams["punto"].isin(ciudades_sel)]

    total_focos_periodo = int(len(firms))
    if not firms.empty and "fecha_adq" in firms.columns:
        focos_diarios = (
            firms.groupby(firms["fecha_adq"].dt.date)
            .size()
            .reset_index(name="focos")
            .rename(columns={"fecha_adq": "fecha"})
        )
        focos_diarios["fecha"] = pd.to_datetime(focos_diarios["fecha"])
    else:
        focos_diarios = pd.DataFrame(columns=["fecha", "focos"])
    stats_focos = {
        "total": total_focos_periodo,
        "frp_promedio": float(firms["potencia_radiativa"].mean()) if not firms.empty and "potencia_radiativa" in firms.columns else 0,
        "frp_maximo": float(firms["potencia_radiativa"].max()) if not firms.empty and "potencia_radiativa" in firms.columns else 0,
    }

# Auto-refresh
st.sidebar.divider()
auto_refresh = st.sidebar.toggle("Auto-refresh (5 min)", value=False)
if auto_refresh:
    st.sidebar.caption(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")

st.sidebar.divider()

# Estado de la base de datos
fuente_bd = "PostgreSQL" if _pg_disponible() else "Parquet (sin BD)"
icono_bd  = "🟢" if _pg_disponible() else "🟡"
st.sidebar.caption(f"{icono_bd} Base de datos: **{fuente_bd}**")

def _estado(path: Path, label: str, max_h: float):
    if not path.exists():
        st.sidebar.caption(f"⬜ {label}: sin datos")
    else:
        horas = (datetime.now().timestamp() - path.stat().st_mtime) / 3600
        if horas < max_h:
            st.sidebar.caption(f"🟢 {label}: hace {int(horas*60)} min")
        else:
            st.sidebar.caption(f"🔴 {label}: hace {int(horas)}h")

_estado(PROCESSED / "firms_nrt_procesado.parquet",  "Focos NRT",   3)
_estado(PROCESSED / "forecast_riesgo.parquet",       "Pronóstico",  1)
_estado(PROCESSED / "cams_nrt_procesado.parquet",    "Calidad aire",1)

if auto_refresh:
    time.sleep(300)
    st.cache_data.clear()
    st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — Resumen General
# ════════════════════════════════════════════════════════════════════════════
if pagina == "Resumen General":

    st.title("SINIA-UY — Sistema de Monitoreo de Incendios Forestales")
    st.caption("Uruguay completo por departamentos + Brasil/Argentina estratégicos + Chile volcánico · 36 puntos · 2018–2025 · Fuentes: NASA FIRMS · Open-Meteo · CAMS · CHIRPS · MODIS")

    # ── Explicación del sistema ───────────────────────────────────────────────
    st.info(
        "**¿Qué hace este sistema?**  \n"
        "SINIA-UY integra cinco fuentes de datos satelitales y meteorológicas para responder "
        "una pregunta central: **¿cuándo, dónde y por qué ocurren incendios forestales y eventos atmosféricos "
        "transfronterizos que pueden afectar a Uruguay?**  \n\n"
        "El alcance regional se concentra en **Uruguay como país núcleo**, más **Brasil y Argentina** "
        "como fuentes principales de humo e incendios transfronterizos, y **Chile** como fuente de ceniza "
        "volcánica y aerosoles de eventos reales como Puyehue-Cordón Caulle y Calbuco. Cada fuente aporta una capa de "
        "información distinta. Combinadas, permiten detectar incendios activos, anticipar condiciones de "
        "riesgo, medir impacto en calidad del aire y correlacionar con precipitación y tipo de cobertura vegetal."
    )

    # ── Arquitectura: flujo de las 5 fuentes ─────────────────────────────────
    st.subheader("Cómo se integran las 5 fuentes de datos")

    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        st.markdown(
            """
            **NASA FIRMS**
            🛰️ *Detección satelital de incendios*

            El satélite VIIRS (Suomi NPP) monitorea el
            corredor regional Uruguay-Brasil-Argentina
            varias veces al día detectando puntos con temperatura
            anormalmente alta en la superficie.

            **Responde:** ¿Hubo un incendio? ¿Dónde? ¿Qué tan intenso?

            → *4 países analizados en el modelo final*
            """
        )

    with col_f2:
        st.markdown(
            """
            **Open-Meteo + CAMS**
            🌡️ *Clima y calidad del aire*

            API meteorológica open-source para 36 puntos de monitoreo.
            Temperatura, humedad, viento y sequía calculan el
            **Índice de Riesgo de Incendio**.

            CAMS mide PM10 y PM2.5 del humo. Límite OMS: 45 µg/m³.

            **Responde:** ¿Cuándo y dónde hay mayor riesgo?
            """
        )

    with col_f3:
        st.markdown(
            """
            **CHIRPS + MODIS MCD12Q1**
            🌧️ *Contexto ambiental profundo*

            CHIRPS: precipitación mensual desde 1981 (UCSB/NASA).
            Enriquece el análisis de sequía acumulada.

            MODIS: clasificación anual del tipo de cobertura vegetal
            (bosque, pastizal, cultivo) — el combustible potencial.

            **Responde:** ¿Por qué algunas zonas son más vulnerables?
            """
        )

    st.divider()

    # ── Alertas activas ───────────────────────────────────────────────────────
    alertas = []
    if not fc.empty and "indice_riesgo" in fc.columns:
        idx_max = fc["indice_riesgo"].max()
        punto_max = fc.loc[fc["indice_riesgo"].idxmax(), "punto"] if "punto" in fc.columns else ""
        if idx_max >= UMBRAL_ALERTA_RIESGO:
            alertas.append(f"Riesgo ALTO previsto en {punto_max} — índice {idx_max:.2f}")
    if not nrt.empty:
        focos_hoy = nrt[nrt["fecha_adq"].dt.date == datetime.now().date()] if "fecha_adq" in nrt.columns else nrt
        if len(focos_hoy) >= UMBRAL_FOCOS_ALERTA:
            alertas.append(f"{len(focos_hoy)} focos detectados HOY por satélite NRT en {alcance_nrt_label}")

    for alerta in alertas:
        st.error(f"ALERTA: {alerta}", icon="🚨")
    if not alertas and (not fc.empty or not nrt.empty):
        st.success("Sin alertas activas — condiciones normales.", icon="✅")

    # ── KPIs con explicación ──────────────────────────────────────────────────
    st.subheader(f"Indicadores principales del período analizado ({periodo_label})")

    c1, c2, c3, c4 = st.columns(4)

    total_focos = total_focos_periodo
    frp_max = stats_focos.get("frp_maximo", 0)
    dias_alto = meteo["nivel_riesgo"].isin(["alto", "muy_alto"]).sum() if not meteo.empty and "nivel_riesgo" in meteo.columns else 0
    nivel_actual = str(meteo.sort_values("fecha").iloc[-1]["nivel_riesgo"]).upper() \
        if not meteo.empty and "nivel_riesgo" in meteo.columns and "fecha" in meteo.columns else "N/D"

    c1.metric(
        "Focos de calor detectados",
        f"{total_focos:,}",
        help="Puntos donde el satélite VIIRS detectó temperatura anormalmente alta. "
             "Cada punto representa un posible foco de incendio. La tarjeta muestra el conteo real; "
             "mapas y graficos usan una muestra acotada por rendimiento visual.",
    )
    c2.metric(
        "FRP máximo registrado",
        f"{frp_max:.1f} MW",
        help="Fire Radiative Power: potencia radiativa del fuego en megawatts. "
             "Es la medida de la intensidad del incendio. Un incendio grande de bosque "
             "puede superar los 1000 MW.",
    )
    c3.metric(
        "Días de riesgo ALTO o MUY ALTO",
        f"{dias_alto}",
        help="Días en que el Índice de Riesgo superó 0.50. "
             "Se calculó combinando temperatura, humedad, viento y sequía de los 36 puntos del alcance regional.",
    )
    c4.metric(
        "Último nivel de riesgo registrado",
        nivel_actual,
        help="Nivel de riesgo del último día histórico disponible en los puntos SA.",
    )

    st.divider()

    # ── Mapa + gráficos ───────────────────────────────────────────────────────
    col_mapa, col_graf = st.columns([3, 2])

    with col_mapa:
        st.subheader("Distribución geográfica de focos")
        modo_mapa_resumen = st.radio(
            "Vista del mapa",
            ["Actuales (NRT últimas 24h)", "Período seleccionado"],
            horizontal=True,
            key="modo_mapa_resumen",
        )
        if modo_mapa_resumen.startswith("Actuales"):
            datos_mapa = nrt
            color_por_confianza = False
            st.caption(
                f"Focos recientes NRT de las últimas 24 horas en {alcance_ciudades_label}. "
                "Respeta el país y las ciudades seleccionadas en el sidebar."
            )
        else:
            datos_mapa = firms
            color_por_confianza = True
            st.caption(
                f"Focos del período {periodo_label} en {alcance_ciudades_label}. "
                "El mapa usa una muestra acotada para mantener la navegacion agil."
            )

        if not datos_mapa.empty and "latitud" in datos_mapa.columns:
            fig_map = _render_mapa_focos(
                datos_mapa,
                pais_sel,
                color_por_confianza,
                height=460,
                centro_override=centro_ciudades,
            )
            if fig_map is not None:
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.info("Sin coordenadas disponibles para la vista seleccionada.")
        else:
            st.info("Sin datos de focos para la vista seleccionada.")

    with col_graf:
        st.subheader("Focos por semana")
        st.caption("Evolución temporal de la actividad de incendios. Picos = semanas críticas.")
        if not focos_diarios.empty:
            semanal = (
                focos_diarios.set_index("fecha").resample("W")["focos"]
                .sum().reset_index()
                .rename(columns={"fecha": "semana"})
            )
            fig_sem = px.bar(
                semanal, x="semana", y="focos",
                color_discrete_sequence=["#e67e22"],
                labels={"semana": "Semana", "focos": "Cantidad de focos"},
                height=220,
            )
            fig_sem.update_layout(margin={"t": 10, "b": 10})
            st.plotly_chart(fig_sem, use_container_width=True)

        st.subheader("¿Cuántos días hubo riesgo alto?")
        st.caption(
            "Distribución del índice de riesgo calculado con datos meteorológicos de los 36 puntos del alcance regional."
        )
        if not meteo.empty and "nivel_riesgo" in meteo.columns:
            dist = meteo["nivel_riesgo"].value_counts().reset_index()
            dist.columns = ["nivel", "dias"]
            fig_pie = px.pie(
                dist, names="nivel", values="dias",
                color="nivel", color_discrete_map=COLORES_RIESGO,
                height=210,
            )
            fig_pie.update_layout(
                margin={"t": 10, "b": 10},
                legend=dict(orientation="h", y=-0.1),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # ── Conclusión de la página ───────────────────────────────────────────────
    st.divider()
    with st.expander("Conclusión del análisis integrado", expanded=True):
        st.markdown(
            """
            **¿Qué nos dicen estas 3 fuentes combinadas?**

            - La actividad de incendios se concentra en **Brasil** y en corredores críticos del
              **noreste y centro de Argentina**, mientras **Uruguay** funciona como país núcleo de análisis
              y receptor de parte del humo transfronterizo.
            - Los picos de focos y de riesgo suelen alinearse con los meses más secos y cálidos,
              especialmente cuando coinciden temperatura alta, humedad baja y viento fuerte.
            - Los días de **riesgo alto o muy alto** tienden a concentrar más focos que los días moderados,
              lo que vuelve útil al índice meteorológico como herramienta de alerta temprana.
            - La integración de CAMS permite verificar si los incendios **impactan la calidad del aire**
              y cruzar ese efecto con puntos de monitoreo concretos del alcance regional.

            Este sistema demuestra el valor de la **ingeniería de datos**: el dato individual no responde
            la pregunta. La respuesta emerge cuando integramos 5 fuentes heterogéneas en una sola vista.
            """
        )


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — Focos de Calor
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Focos de Calor":

    st.title("Focos de Calor — NASA FIRMS VIIRS")
    st.caption(f"Satélite: VIIRS Suomi NPP (Standard Processing) · Período: {periodo_label} · Uruguay, Brasil, Argentina y Chile")

    st.info(
        "**¿Qué es un foco de calor?**  \n"
        "El satélite VIIRS detecta la radiación infrarroja emitida por la superficie terrestre. "
        "Cuando un pixel tiene una temperatura anormalmente alta respecto a su entorno, "
        "se marca como foco de calor (*hotspot*). No todo foco es necesariamente un incendio forestal: "
        "puede ser quema de pasturas, industria o volcanes. Por eso cada foco tiene un nivel de "
        "**confianza** (Baja / Normal / Alta) que indica la probabilidad de que sea fuego real.  \n\n"
        "**FRP (Fire Radiative Power)**: mide la energía irradiada por el fuego en megawatts. "
        "Un valor alto indica un incendio de mayor envergadura."
    )

    st.divider()

    if firms.empty:
        st.warning("No hay datos de focos cargados.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Total de focos detectados",
            f"{total_focos_periodo:,}",
            help="Cantidad real de hotspots satelitales detectados en el período seleccionado.",
        )
        c2.metric(
            "FRP promedio",
            f"{stats_focos.get('frp_promedio', 0):.2f} MW",
            help="Intensidad promedio de los focos. Valores > 100 MW indican incendios grandes.",
        )
        c3.metric(
            "FRP máximo registrado",
            f"{stats_focos.get('frp_maximo', 0):.2f} MW",
            help="El foco más intenso del período. Representa el incendio de mayor envergadura.",
        )
        st.caption(
            "Totales, FRP y evolución temporal usan agregaciones reales de PostgreSQL. "
            "Mapa, tabla y graficos de detalle usan una muestra acotada para mantener el dashboard agil."
        )

        st.subheader("Mapa de focos")
        modo_mapa_focos = st.radio(
            "Vista del mapa",
            ["Actuales (NRT últimas 24h)", "Período seleccionado"],
            horizontal=True,
            key="modo_mapa_focos",
        )
        if modo_mapa_focos.startswith("Actuales"):
            datos_mapa = nrt
            color_por_confianza = False
            st.caption(
                f"Focos recientes NRT de las últimas 24 horas en {alcance_ciudades_label}. "
                "Cambia el país o las ciudades en el sidebar para ajustar el mapa."
            )
        else:
            datos_mapa = firms
            color_por_confianza = True
            st.caption(
                f"Focos del período {periodo_label} en {alcance_ciudades_label}. "
                "Para el periodo completo se visualiza una muestra priorizada por intensidad FRP."
            )

        if not datos_mapa.empty and "latitud" in datos_mapa.columns:
            fig_map_focos = _render_mapa_focos(
                datos_mapa,
                pais_sel,
                color_por_confianza,
                height=430,
                centro_override=centro_ciudades,
            )
            if fig_map_focos is not None:
                st.plotly_chart(fig_map_focos, use_container_width=True)
            else:
                st.info("Sin coordenadas disponibles para la vista seleccionada.")
        else:
            st.info("Sin focos disponibles para la vista seleccionada.")

        st.subheader("Evolución diaria de focos detectados")
        st.caption(
            "Cada barra es un día. Los picos corresponden a eventos de incendios activos. "
            "La tendencia muestra si la actividad aumenta o disminuye en el período."
        )
        diario = focos_diarios.copy()
        fig_line = px.line(
            diario, x="fecha", y="focos",
            labels={"fecha": "Fecha", "focos": "Focos detectados por día"},
            color_discrete_sequence=["#e74c3c"],
        )
        fig_line.update_traces(fill="tozeroy", fillcolor="rgba(231,76,60,0.15)")
        st.plotly_chart(fig_line, use_container_width=True)

        col_conf, col_frp = st.columns(2)

        with col_conf:
            st.subheader("Nivel de confianza del detector")
            st.caption(
                "**Alta (h):** el satélite tiene alta certeza de que es fuego real.  \n"
                "**Normal (n):** confianza estándar — la mayoría de los focos.  \n"
                "**Baja (l):** puede ser ruido, reflexión solar u otras fuentes de calor."
            )
            if "confianza_raw" in firms.columns:
                conf_map = {"l": "Baja", "n": "Normal", "h": "Alta"}
                conf_data = firms["confianza_raw"].map(conf_map).fillna(firms["confianza_raw"]).value_counts()
                fig_conf = px.bar(
                    x=conf_data.index, y=conf_data.values,
                    labels={"x": "Confianza", "y": "Cantidad de focos"},
                    color=conf_data.index,
                    color_discrete_map={"Baja": "#f1c40f", "Normal": "#e67e22", "Alta": "#e74c3c"},
                )
                st.plotly_chart(fig_conf, use_container_width=True)

        with col_frp:
            st.subheader("Distribución de intensidad (FRP)")
            st.caption(
                "La mayoría de los focos son de baja intensidad (< 50 MW). "
                "Los focos de alta intensidad (cola derecha) son los grandes incendios."
            )
            if "potencia_radiativa" in firms.columns:
                fig_frp = px.histogram(
                    firms, x="potencia_radiativa", nbins=40,
                    labels={"potencia_radiativa": "FRP (megawatts)"},
                    color_discrete_sequence=["#e67e22"],
                )
                st.plotly_chart(fig_frp, use_container_width=True)

        st.subheader("Tabla de focos detectados")
        st.caption("Ordenado por fecha más reciente. Se puede filtrar y exportar.")
        cols_t = [c for c in ["fecha_adq", "latitud", "longitud", "potencia_radiativa",
                               "confianza_raw", "satelite", "dia_noche"] if c in firms.columns]
        st.dataframe(
            firms[cols_t].sort_values("fecha_adq", ascending=False),
            use_container_width=True, height=300,
        )


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 3 — Índice de Riesgo
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Índice de Riesgo":

    st.title("Índice de Riesgo de Incendio")
    st.caption("Fuente meteorológica: Open-Meteo Archive API · Sin costo · Sin API key")

    st.info(
        "**¿Cómo se calcula el índice de riesgo?**  \n"
        "Cada día y cada punto de monitoreo recibe un índice entre **0 (sin riesgo) y 1 (riesgo máximo)**, "
        "calculado como la suma ponderada de 4 variables meteorológicas normalizadas:  \n\n"
        "| Variable | Peso | Lógica |\n"
        "|---|---|---|\n"
        "| Temperatura máxima (°C) | **25%** | Mayor calor → más riesgo |\n"
        "| Humedad mínima (%) | **30%** | Menos humedad → más riesgo (ambiente seco) |\n"
        "| Velocidad del viento (km/h) | **20%** | Más viento → incendio se propaga más rápido |\n"
        "| Evapotranspiración / sequía (mm/día) | **25%** | Mayor sequía acumulada → más riesgo |\n\n"
        "Cada componente se normaliza con umbrales regionales definidos para el alcance "
        "Uruguay-Brasil-Argentina (ej: temperatura de referencia máxima = 42°C)."
    )

    st.markdown(
        """
        **Niveles de riesgo:**
        🟢 **BAJO** (0.00–0.25) &nbsp;|&nbsp;
        🟡 **MODERADO** (0.25–0.50) &nbsp;|&nbsp;
        🟠 **ALTO** (0.50–0.75) &nbsp;|&nbsp;
        🔴 **MUY ALTO** (0.75–1.00)
        """
    )
    st.divider()

    tab_hist, tab_fc = st.tabs([f"Histórico ({periodo_label})", "Pronóstico 7 días"])

    with tab_hist:
        if meteo.empty:
            st.warning("No hay datos meteorológicos procesados.")
        else:
            puntos = sorted(meteo["punto"].unique()) if "punto" in meteo.columns else []
            punto_sel = st.selectbox("Seleccionar punto de monitoreo:", puntos, key="hist_punto") if puntos else None
            df_p = meteo[meteo["punto"] == punto_sel].copy() if punto_sel else meteo.copy()
            if "fecha" in df_p.columns:
                df_p = df_p.sort_values("fecha")

            c1, c2, c3 = st.columns(3)
            if "indice_riesgo" in df_p.columns:
                c1.metric(
                    "Índice promedio del período",
                    f"{df_p['indice_riesgo'].mean():.3f}",
                    help="Promedio del índice de riesgo diario. Un valor > 0.50 es preocupante.",
                )
                c2.metric(
                    "Peor día registrado",
                    f"{df_p['indice_riesgo'].max():.3f}",
                    help="El día de mayor riesgo en el período. Revisar qué condiciones lo causaron.",
                )
            if "nivel_riesgo" in df_p.columns:
                n_criticos = int(df_p["nivel_riesgo"].isin(["alto", "muy_alto"]).sum())
                c3.metric(
                    "Días en nivel ALTO o MUY ALTO",
                    n_criticos,
                    help=f"De {len(df_p)} días totales, {n_criticos} superaron el umbral de 0.50.",
                )

            st.subheader("Evolución diaria del índice de riesgo")
            st.caption(
                "Las bandas de color indican el nivel de riesgo. "
                "Cuando la línea entra en la zona naranja o roja, las condiciones son peligrosas."
            )
            if "fecha" in df_p.columns and "indice_riesgo" in df_p.columns:
                fig_idx = go.Figure()
                bandas = [
                    (0,   .25, "rgba(46,204,113,0.12)",  "BAJO"),
                    (.25, .5,  "rgba(243,156,18,0.12)",  "MODERADO"),
                    (.5,  .75, "rgba(230,126,34,0.20)",  "ALTO"),
                    (.75, 1,   "rgba(231,76,60,0.25)",   "MUY ALTO"),
                ]
                for y0, y1, color, label in bandas:
                    fig_idx.add_hrect(
                        y0=y0, y1=y1, fillcolor=color, line_width=0,
                        annotation_text=label, annotation_position="left",
                        annotation_font_size=11,
                    )
                fig_idx.add_trace(go.Scatter(
                    x=df_p["fecha"], y=df_p["indice_riesgo"],
                    mode="lines+markers", name="Índice de riesgo",
                    line=dict(color="#e74c3c", width=2), marker=dict(size=5),
                ))
                fig_idx.update_layout(
                    yaxis=dict(range=[0, 1], title="Índice de riesgo (0 = sin riesgo, 1 = máximo)"),
                    xaxis_title="Fecha", height=380, margin={"t": 20},
                )
                st.plotly_chart(fig_idx, use_container_width=True)

            comp_cols = [c for c in ["riesgo_temp", "riesgo_humedad", "riesgo_viento", "riesgo_sequia"]
                         if c in df_p.columns]
            if comp_cols:
                col_r, col_t = st.columns([1, 1])
                with col_r:
                    st.subheader("¿Qué factor contribuye más al riesgo?")
                    st.caption(
                        "Gráfico radar con el promedio de cada componente. "
                        "El área más grande indica mayor exposición histórica en ese factor."
                    )
                    labels = ["Temperatura", "Humedad", "Viento", "Sequía"][:len(comp_cols)]
                    valores = [df_p[c].mean() for c in comp_cols]
                    fig_radar = go.Figure(go.Scatterpolar(
                        r=valores + [valores[0]], theta=labels + [labels[0]],
                        fill="toself", fillcolor="rgba(231,76,60,0.25)", line_color="#e74c3c",
                    ))
                    fig_radar.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                        height=380, margin={"t": 30},
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)

                with col_t:
                    st.subheader("Variables meteorológicas del período")
                    st.caption("Cada mini-gráfico muestra la evolución de la variable a lo largo del período.")
                    for col_var, label, color in [
                        ("temperature_2m_max",       "Temperatura máx. diaria (°C)",    "#e74c3c"),
                        ("relative_humidity_2m_min", "Humedad mínima diaria (%)",        "#3498db"),
                        ("wind_speed_10m_max",        "Velocidad máxima del viento (km/h)", "#9b59b6"),
                        ("precipitation_sum",         "Precipitación diaria (mm)",        "#27ae60"),
                    ]:
                        if col_var in df_p.columns and "fecha" in df_p.columns:
                            fig_v = px.line(
                                df_p, x="fecha", y=col_var,
                                color_discrete_sequence=[color], height=120,
                            )
                            fig_v.update_layout(
                                margin={"t": 5, "b": 5, "l": 0, "r": 0},
                                showlegend=False, yaxis_title=label,
                                xaxis=dict(showticklabels=False),
                            )
                            st.plotly_chart(fig_v, use_container_width=True)

    with tab_fc:
        if fc.empty:
            st.info(
                "Sin pronóstico disponible todavía.  \n\n"
                "Corré el scheduler en una terminal para obtenerlo:\n"
                "```\npython etl/scheduler.py\n```"
            )
        else:
            st.caption(
                "El pronóstico se descarga diariamente de Open-Meteo y el índice de riesgo "
                "se calcula aplicando la misma fórmula que para datos históricos."
            )
            puntos_fc = sorted(fc["punto"].unique()) if "punto" in fc.columns else []
            punto_fc = st.selectbox("Punto:", puntos_fc, key="fc_punto") if puntos_fc else None
            df_fc = fc[fc["punto"] == punto_fc].sort_values("fecha") if punto_fc else fc.sort_values("fecha")

            fig_fc = go.Figure()
            for y0, y1, color, label in [(0,.25,"rgba(46,204,113,0.12)","BAJO"),
                                          (.25,.5,"rgba(243,156,18,0.12)","MODERADO"),
                                          (.5,.75,"rgba(230,126,34,0.2)","ALTO"),
                                          (.75,1,"rgba(231,76,60,0.25)","MUY ALTO")]:
                fig_fc.add_hrect(y0=y0, y1=y1, fillcolor=color, line_width=0,
                                 annotation_text=label, annotation_position="left",
                                 annotation_font_size=11)
            if "indice_riesgo" in df_fc.columns:
                fig_fc.add_trace(go.Scatter(
                    x=df_fc["fecha"], y=df_fc["indice_riesgo"],
                    mode="lines+markers+text",
                    line=dict(color="#e74c3c", width=2.5), marker=dict(size=9),
                    text=df_fc["indice_riesgo"].round(2), textposition="top center",
                ))
            hoy = pd.Timestamp(datetime.now().date())
            fig_fc.add_shape(
                type="line",
                x0=hoy,
                x1=hoy,
                y0=0,
                y1=1,
                yref="paper",
                line=dict(color="gray", dash="dash"),
            )
            fig_fc.add_annotation(
                x=hoy,
                y=1,
                yref="paper",
                text="Hoy",
                showarrow=False,
                yanchor="bottom",
                font=dict(color="gray", size=11),
            )
            fig_fc.update_layout(
                yaxis=dict(range=[0, 1.1], title="Índice de riesgo (0–1)"),
                xaxis_title="Fecha", height=400, margin={"t": 20},
            )
            st.plotly_chart(fig_fc, use_container_width=True)

            cols_fc = [c for c in ["fecha", "punto", "temperature_2m_max",
                                    "relative_humidity_2m_min", "wind_speed_10m_max",
                                    "precipitation_probability_max",
                                    "indice_riesgo", "nivel_riesgo"] if c in df_fc.columns]
            st.dataframe(df_fc[cols_fc], use_container_width=True, height=280)


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 4 — Calidad del Aire
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Calidad del Aire":

    st.title("Calidad del Aire — CAMS vía Open-Meteo")
    st.caption("Fuente: Copernicus Atmosphere Monitoring Service · Proxy Open-Meteo Air Quality API")

    st.info(
        "**¿Por qué medir la calidad del aire?**  \n"
        "Cuando hay incendios forestales, el humo eleva la concentración de partículas en el aire. "
        "Estas partículas son invisibles al ojo humano pero dañinas para la salud respiratoria.  \n\n"
        "**PM10**: partículas menores a 10 micrómetros. El límite OMS es **45 µg/m³/día**.  \n"
        "**PM2.5**: partículas aún más finas (< 2.5 µm), más peligrosas porque llegan a los pulmones.  \n"
        "**AQI europeo**: índice agregado de calidad del aire (0 = perfecto, >50 = malo para grupos sensibles, >100 = malo para todos).  \n\n"
        "Con esta fuente respondemos: **¿los incendios detectados por FIRMS afectaron la salud de la población?**"
    )

    st.divider()

    if cams.empty:
        st.warning("No hay datos CAMS disponibles.")
    else:
        c1, c2, c3 = st.columns(3)
        if "pm10_media" in cams.columns:
            c1.metric(
                "PM10 promedio del período",
                f"{cams['pm10_media'].mean():.2f} µg/m³",
                help="Promedio de partículas PM10. El límite OMS es 45 µg/m³. "
                     "Por encima de ese valor hay riesgo para la salud.",
            )
            c2.metric(
                "PM10 máximo registrado",
                f"{cams['pm10_max'].max():.2f} µg/m³",
                help="El peor día del período en términos de calidad del aire.",
            )
            dias_oms = int(cams["supera_oms_pm10"].sum()) if "supera_oms_pm10" in cams.columns else 0
            c3.metric(
                "Días que superaron el límite OMS",
                dias_oms,
                help="Días con PM10 > 45 µg/m³. Estos días la población estuvo expuesta "
                     "a niveles de contaminación por encima del estándar internacional de salud.",
            )

        st.subheader("Evolución diaria de PM10 con el límite OMS")
        st.caption(
            "La línea roja punteada marca el límite de la OMS (45 µg/m³). "
            "Los días en que las líneas superan ese umbral son días de riesgo para la salud."
        )
        if "fecha" in cams.columns and "pm10_media" in cams.columns:
            fig_pm = go.Figure()
            fig_pm.add_hrect(
                y0=45, y1=max(cams["pm10_max"].max() * 1.1, 50),
                fillcolor="rgba(231,76,60,0.1)", line_width=0,
                annotation_text="Zona de riesgo (sobre límite OMS)", annotation_position="top left",
            )
            fig_pm.add_hline(
                y=45, line_dash="dash", line_color="red",
                annotation_text="Límite OMS: 45 µg/m³",
            )
            for punto in (cams["punto"].unique() if "punto" in cams.columns else [""]):
                df_p = cams[cams["punto"] == punto].sort_values("fecha") \
                    if "punto" in cams.columns else cams
                fig_pm.add_trace(go.Scatter(
                    x=df_p["fecha"], y=df_p["pm10_media"],
                    name=punto, mode="lines+markers",
                ))
            fig_pm.update_layout(
                yaxis_title="PM10 (µg/m³)",
                xaxis_title="Fecha",
                height=380, margin={"t": 20},
            )
            st.plotly_chart(fig_pm, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Relación entre PM2.5 y PM10")
            st.caption(
                "Si ambos suben juntos, es señal de humo de incendio. "
                "La línea de tendencia muestra la correlación entre las dos partículas."
            )
            if "pm2_5_media" in cams.columns and "pm10_media" in cams.columns:
                fig_sc = px.scatter(
                    cams, x="pm10_media", y="pm2_5_media",
                    color="punto" if "punto" in cams.columns else None,
                    labels={"pm10_media": "PM10 (µg/m³)", "pm2_5_media": "PM2.5 (µg/m³)"},
                    trendline="ols", height=300,
                )
                st.plotly_chart(fig_sc, use_container_width=True)

        with col_b:
            st.subheader("Índice de Calidad del Aire (AQI europeo)")
            st.caption(
                "AQI < 20: bueno. AQI 20–40: aceptable. AQI > 50: malo para grupos sensibles. "
                "AQI > 100: malo para toda la población."
            )
            if "european_aqi_media" in cams.columns:
                fig_aqi = px.line(
                    cams.sort_values("fecha"), x="fecha", y="european_aqi_media",
                    color="punto" if "punto" in cams.columns else None,
                    labels={"fecha": "Fecha", "european_aqi_media": "AQI europeo"},
                    height=300,
                )
                st.plotly_chart(fig_aqi, use_container_width=True)

        st.subheader("Tabla de datos diarios de calidad del aire")
        cols_t = [c for c in ["fecha", "punto", "pm10_media", "pm10_max", "pm10_p95",
                               "pm2_5_media", "nivel_pm10", "supera_oms_pm10"] if c in cams.columns]
        st.dataframe(
            cams[cols_t].sort_values("fecha", ascending=False),
            use_container_width=True, height=300,
        )


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 5 — Tiempo Real
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Tiempo Real":

    st.title("Monitoreo en Tiempo Real")
    st.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    st.info(
        "**¿Cómo funciona el monitoreo en tiempo real?**  \n"
        "El scheduler (APScheduler) ejecuta el pipeline ETL automáticamente cada 1-3 horas:  \n"
        "1. Descarga focos NRT de NASA FIRMS (latencia ~3h desde el paso del satélite)  \n"
        "2. Descarga el pronóstico meteorológico de los próximos 7 días de Open-Meteo  \n"
        "3. Recalcula el índice de riesgo para cada punto con los datos frescos  \n"
        "4. Actualiza la base de datos y genera alertas si se supera el umbral de riesgo 0.65"
    )

    if st.button("Actualizar ahora"):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    alertas = []
    if not fc.empty and "indice_riesgo" in fc.columns:
        idx_max = fc["indice_riesgo"].max()
        punto_max = fc.loc[fc["indice_riesgo"].idxmax(), "punto"] if "punto" in fc.columns else ""
        if idx_max >= UMBRAL_ALERTA_RIESGO:
            alertas.append(f"Riesgo ALTO previsto en {punto_max} — índice {idx_max:.2f}")
    if not nrt.empty and "fecha_adq" in nrt.columns:
        focos_hoy = nrt[nrt["fecha_adq"].dt.date == datetime.now().date()]
        if len(focos_hoy) >= UMBRAL_FOCOS_ALERTA:
            alertas.append(f"{len(focos_hoy)} focos detectados HOY por satélite NRT en {alcance_nrt_label}")

    if alertas:
        for a in alertas:
            st.error(f"ALERTA: {a}", icon="🚨")
    else:
        st.success("Sin alertas activas — condiciones normales.", icon="✅")
        if fc.empty and nrt.empty:
            st.info(
                "Iniciá el scheduler para activar el monitoreo en tiempo real:\n"
                "```\npython etl/scheduler.py\n```"
            )

    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Focos NRT últimas 24h", len(nrt) if not nrt.empty else 0,
              help="Focos detectados por VIIRS NRT en las últimas 24 horas.")
    if not fc.empty and "indice_riesgo" in fc.columns and "fecha" in fc.columns:
        idx_hoy = fc[fc["fecha"].dt.date == datetime.now().date()]["indice_riesgo"].mean()
        c2.metric("Índice de riesgo HOY", f"{idx_hoy:.3f}" if not pd.isna(idx_hoy) else "N/D",
                  help="Índice de riesgo calculado con el pronóstico meteorológico de hoy.")
        c3.metric("Índice máximo próximos 7 días", f"{fc['indice_riesgo'].max():.3f}",
                  help="El día más peligroso del pronóstico de los próximos 7 días.")
    else:
        c2.metric("Índice de riesgo HOY", "—")
        c3.metric("Índice máximo próximos 7 días", "—")
    if not cams.empty and "pm10_media" in cams.columns and "fecha" in cams.columns:
        pm10_hoy = cams[cams["fecha"].dt.date == datetime.now().date()]["pm10_media"].mean()
        c4.metric("PM10 hoy", f"{pm10_hoy:.1f} µg/m³" if not pd.isna(pm10_hoy) else "N/D",
                  help="Calidad del aire hoy. Límite OMS: 45 µg/m³.")
    else:
        c4.metric("PM10 hoy", "—")

    st.subheader("Pronóstico de riesgo — próximos 7 días")
    if fc.empty:
        st.info("Sin datos de pronóstico. Iniciá el scheduler para obtenerlos.")
    else:
        puntos_fc = sorted(fc["punto"].unique()) if "punto" in fc.columns else []
        punto_sel = st.selectbox("Punto:", puntos_fc, key="tr_punto") if puntos_fc else None
        df_fc = fc[fc["punto"] == punto_sel].sort_values("fecha") if punto_sel else fc.sort_values("fecha")

        fig_fc = go.Figure()
        for y0, y1, color, label in [(0,.25,"rgba(46,204,113,0.12)","BAJO"),
                                      (.25,.5,"rgba(243,156,18,0.12)","MODERADO"),
                                      (.5,.75,"rgba(230,126,34,0.2)","ALTO"),
                                      (.75,1,"rgba(231,76,60,0.25)","MUY ALTO")]:
            fig_fc.add_hrect(y0=y0, y1=y1, fillcolor=color, line_width=0,
                             annotation_text=label, annotation_position="left",
                             annotation_font_size=11)
        if "indice_riesgo" in df_fc.columns:
            fig_fc.add_trace(go.Scatter(
                x=df_fc["fecha"], y=df_fc["indice_riesgo"],
                mode="lines+markers+text",
                line=dict(color="#e74c3c", width=2.5), marker=dict(size=9),
                text=df_fc["indice_riesgo"].round(2), textposition="top center",
            ))
        hoy = pd.Timestamp(datetime.now().date())
        fig_fc.add_shape(
            type="line",
            x0=hoy, x1=hoy,
            y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(color="gray", dash="dash"),
        )
        fig_fc.add_annotation(
            x=hoy, y=1,
            xref="x", yref="paper",
            text="Hoy",
            showarrow=False,
            yanchor="bottom",
        )
        fig_fc.update_layout(
            yaxis=dict(range=[0, 1.1], title="Índice de riesgo"),
            height=400, margin={"t": 20},
        )
        st.plotly_chart(fig_fc, use_container_width=True)

    st.subheader("Focos NRT — últimas 24 horas")
    if nrt.empty:
        st.info("Sin focos NRT disponibles. El scheduler los actualiza cada 3 horas.")
    else:
        st.caption(f"Vista NRT filtrada por país/ciudad: {alcance_ciudades_label}.")
        fig_nrt = _render_mapa_focos(
            nrt,
            pais_sel,
            color_por_confianza=False,
            height=400,
            centro_override=centro_ciudades,
        )
        if fig_nrt is not None:
            st.plotly_chart(fig_nrt, use_container_width=True)
        else:
            st.info("Sin coordenadas NRT disponibles para el país seleccionado.")


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 6 — Análisis de Riesgo
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Análisis de Riesgo":

    st.title("Análisis de Riesgo — Capa Analítica")
    st.caption("Estadística descriptiva · Detección de anomalías · Validación del modelo")

    st.info(
        "**¿Qué responde esta sección?**  \n"
        "Esta es la capa de valor analítico del proyecto. Con los datos ya integrados en PostgreSQL, "
        "respondemos preguntas que no pueden responderse mirando una sola fuente:  \n\n"
        "- **¿Qué punto del sistema tiene más riesgo histórico?** → Ranking de zonas  \n"
        "- **¿En qué época del año hay más incendios?** → Análisis estacional  \n"
        "- **¿Hubo días con condiciones excepcionalmente peligrosas?** → Detección de anomalías  \n"
        "- **¿El índice que calculamos realmente predice incendios?** → Correlación focos-riesgo  \n"
        "- **¿Cuáles fueron los días más críticos de la historia?** → Días críticos"
    )

    st.divider()

    try:
        from analytics.riesgo_analytics import (
            ranking_zonas, analisis_estacional,
            detectar_anomalias, correlacion_focos_riesgo,
        )
        _analytics_ok = True
    except ImportError:
        _analytics_ok = False

    tab_rank, tab_estac, tab_anom, tab_corr, tab_criticos = st.tabs([
        "Ranking de Zonas",
        "Estacionalidad",
        "Anomalías",
        "Correlación Focos-Riesgo",
        "Días Críticos",
    ])

    # ── Tab 1: Ranking de zonas ───────────────────────────────────────────────
    with tab_rank:
        st.subheader("¿Qué punto de monitoreo tiene mayor exposición histórica al riesgo?")
        st.caption(
            "**Cómo se calcula el score:** 50% índice de riesgo promedio del período "
            "+ 50% proporción de días en nivel ALTO o MUY ALTO.  \n"
            "**Uso práctico:** este ranking permite priorizar recursos de vigilancia — "
            "las brigadas de incendios deberían concentrarse en los puntos con mayor score."
        )
        if not meteo.empty and "indice_riesgo" in meteo.columns and "punto" in meteo.columns:
            if _analytics_ok:
                df_rank = ranking_zonas(meteo)
            else:
                df_rank = (
                    meteo.groupby("punto")
                    .agg(
                        indice_promedio=("indice_riesgo", "mean"),
                        dias_criticos=("nivel_riesgo", lambda x: x.isin(["alto","muy_alto"]).sum()),
                        indice_maximo=("indice_riesgo", "max"),
                        total_dias=("indice_riesgo", "count"),
                    )
                    .reset_index()
                )
                df_rank["score_riesgo"] = (
                    df_rank["indice_promedio"] * 0.5
                    + (df_rank["dias_criticos"] / df_rank["total_dias"].replace(0, 1)) * 0.5
                ).round(4)
                df_rank = df_rank.sort_values("score_riesgo", ascending=False)

            fig_rank = px.bar(
                df_rank, x="punto", y="score_riesgo",
                color="score_riesgo",
                color_continuous_scale=["#2ecc71", "#f39c12", "#e74c3c"],
                labels={"punto": "Punto de monitoreo", "score_riesgo": "Score de exposición al riesgo"},
                height=350,
                text="score_riesgo",
            )
            fig_rank.update_traces(texttemplate="%{text:.3f}", textposition="outside")
            fig_rank.update_layout(margin={"t": 40}, coloraxis_showscale=False)
            st.plotly_chart(fig_rank, use_container_width=True)

            cols_mostrar = [c for c in [
                "punto", "score_riesgo", "indice_promedio",
                "dias_criticos", "indice_maximo", "total_dias"
            ] if c in df_rank.columns]
            st.dataframe(df_rank[cols_mostrar], use_container_width=True)

            if not df_rank.empty:
                zona_top = df_rank.iloc[0]["punto"]
                score_top = df_rank.iloc[0]["score_riesgo"]
                st.success(
                    f"**Conclusión:** La zona con mayor exposición histórica al riesgo es **{zona_top}** "
                    f"con un score de {score_top:.3f}. Este punto debería tener prioridad "
                    "en los planes de prevención y vigilancia de incendios forestales."
                )
        else:
            st.warning("No hay datos meteorológicos suficientes.")

    # ── Tab 2: Análisis estacional ────────────────────────────────────────────
    with tab_estac:
        st.subheader("¿En qué época del año hay más riesgo de incendio?")
        st.caption(
            "Esta pregunta es clave para la gestión preventiva: si sabemos que el riesgo "
            "aumenta en los meses más cálidos del corredor regional, podemos activar planes de "
            "emergencia con anticipación."
        )
        if not meteo.empty and "indice_riesgo" in meteo.columns:
            df_m = meteo.copy()
            df_m["fecha"] = pd.to_datetime(df_m["fecha"])
            df_m["mes"] = df_m["fecha"].dt.month
            df_m["nombre_mes"] = df_m["fecha"].dt.strftime("%b")

            estacional = (
                df_m.groupby(["mes", "nombre_mes"])
                .agg(
                    riesgo_promedio=("indice_riesgo", "mean"),
                    dias_criticos=("nivel_riesgo", lambda x: x.isin(["alto","muy_alto"]).sum()),
                )
                .reset_index()
                .sort_values("mes")
            )

            fig_est = px.bar(
                estacional, x="nombre_mes", y="riesgo_promedio",
                color="riesgo_promedio",
                color_continuous_scale=["#2ecc71", "#f39c12", "#e74c3c"],
                labels={"nombre_mes": "Mes", "riesgo_promedio": "Índice de riesgo promedio"},
                height=320,
                text="riesgo_promedio",
            )
            fig_est.update_traces(texttemplate="%{text:.3f}", textposition="outside")
            fig_est.update_layout(margin={"t": 40}, coloraxis_showscale=False)
            st.plotly_chart(fig_est, use_container_width=True)

            col_m1, col_m2 = st.columns(2)
            mes_peor  = estacional.loc[estacional["riesgo_promedio"].idxmax()]
            mes_mejor = estacional.loc[estacional["riesgo_promedio"].idxmin()]

            col_m1.metric(
                "Mes de mayor riesgo histórico",
                mes_peor["nombre_mes"],
                f"Índice promedio: {mes_peor['riesgo_promedio']:.3f}",
            )
            col_m2.metric(
                "Mes de menor riesgo histórico",
                mes_mejor["nombre_mes"],
                f"Índice promedio: {mes_mejor['riesgo_promedio']:.3f}",
            )

            st.success(
                f"**Conclusión:** El mes de **{mes_peor['nombre_mes']}** concentra el mayor riesgo histórico. "
                "Este patrón estacional permite diseñar políticas de prevención anticipadas: "
                "activar brigadas, restringir quemas controladas y emitir alertas tempranas "
                "antes de que comience la temporada de riesgo."
            )
        else:
            st.warning("Sin datos para análisis estacional.")

    # ── Tab 3: Anomalías ──────────────────────────────────────────────────────
    with tab_anom:
        st.subheader("¿Hubo días con condiciones excepcionalmente peligrosas?")
        st.caption(
            "Se usa **Isolation Forest**, un algoritmo de Machine Learning no supervisado que "
            "detecta puntos de datos que se alejan del patrón habitual. En este caso, identifica "
            "días donde la combinación de temperatura alta + humedad baja + viento fuerte + sequía "
            "fue inusualmente extrema — aunque no necesariamente se haya producido un incendio ese día."
        )
        if not meteo.empty and _analytics_ok:
            df_anom = detectar_anomalias(meteo)
            if not df_anom.empty and "es_anomalia" in df_anom.columns:
                n_anom  = int(df_anom["es_anomalia"].sum())
                n_total = len(df_anom)
                col_a1, col_a2 = st.columns(2)
                col_a1.metric(
                    "Días anómalos detectados",
                    n_anom,
                    help="Días cuya combinación meteorológica fue inusualmente extrema.",
                )
                col_a2.metric(
                    "Proporción del período",
                    f"{n_anom/n_total*100:.1f}%",
                    help=f"{n_anom} de {n_total} días totales.",
                )

                df_plot = df_anom.copy()
                df_plot["tipo"] = df_plot["es_anomalia"].map({True: "Día anómalo", False: "Día normal"})
                if "fecha" in df_plot.columns and "indice_riesgo" in df_plot.columns:
                    fig_anom = px.scatter(
                        df_plot, x="fecha", y="indice_riesgo",
                        color="tipo",
                        color_discrete_map={"Día anómalo": "#e74c3c", "Día normal": "#95a5a6"},
                        hover_data=["punto"] if "punto" in df_plot.columns else None,
                        height=350,
                        labels={"fecha": "Fecha", "indice_riesgo": "Índice de riesgo", "tipo": "Tipo de día"},
                    )
                    st.plotly_chart(fig_anom, use_container_width=True)

                st.subheader("Detalle de días anómalos")
                cols_anom = [c for c in ["fecha", "punto", "indice_riesgo", "nivel_riesgo",
                                          "temperature_2m_max", "relative_humidity_2m_min"]
                             if c in df_anom.columns]
                st.dataframe(
                    df_anom[df_anom["es_anomalia"]][cols_anom]
                    .sort_values("indice_riesgo", ascending=False),
                    use_container_width=True, height=250,
                )

                st.warning(
                    "**Limitación importante:** el modelo fue entrenado con solo 91 días (Q1 2024). "
                    "Con más datos históricos (2+ años), la detección de anomalías sería más precisa. "
                    "Los días marcados como anómalos deben ser validados por un experto en incendios "
                    "antes de tomar decisiones operativas."
                )

        elif not meteo.empty:
            df_m = meteo.dropna(subset=["indice_riesgo"])
            p95 = df_m["indice_riesgo"].quantile(0.95)
            anom = df_m[df_m["indice_riesgo"] >= p95]
            st.metric("Días sobre el percentil 95 de riesgo", len(anom))
            cols_a = [c for c in ["fecha","punto","indice_riesgo","nivel_riesgo",
                                    "temperature_2m_max","relative_humidity_2m_min"]
                      if c in anom.columns]
            st.dataframe(
                anom[cols_a].sort_values("indice_riesgo", ascending=False),
                use_container_width=True, height=300,
            )
        else:
            st.warning("Sin datos para análisis de anomalías.")

    # ── Tab 4: Correlación focos-riesgo ───────────────────────────────────────
    with tab_corr:
        st.subheader("¿El índice de riesgo realmente predice la ocurrencia de incendios?")
        st.caption(
            "Esta es la **validación del modelo**: si el índice que calculamos es útil, "
            "debería haber más focos FIRMS los días de índice alto. "
            "Medimos esto con la **correlación de Pearson** (entre -1 y 1).  \n"
            "- Valor cercano a **1**: cuando el índice sube, suben los focos → el modelo funciona.  \n"
            "- Valor cercano a **0**: no hay relación → el modelo necesita mejoras.  \n"
            "- Valor negativo: relación inversa (muy poco probable en este caso)."
        )

        if not meteo.empty and not firms.empty:
            df_focos_diario = (
                firms.set_index("fecha_adq").resample("D")["latitud"]
                .count().reset_index()
                .rename(columns={"fecha_adq": "fecha", "latitud": "focos"})
            )
            df_focos_diario["fecha"] = pd.to_datetime(df_focos_diario["fecha"]).dt.normalize()

            df_meteo_avg = meteo.groupby("fecha")["indice_riesgo"].mean().reset_index()
            df_meteo_avg["fecha"] = pd.to_datetime(df_meteo_avg["fecha"]).dt.normalize()

            df_corr = df_meteo_avg.merge(df_focos_diario, on="fecha", how="left").fillna(0)

            if len(df_corr) > 5:
                r = df_corr["indice_riesgo"].corr(df_corr["focos"])

                col_r1, col_r2 = st.columns(2)
                col_r1.metric(
                    "Correlación de Pearson (riesgo vs focos)",
                    f"{r:.3f}",
                    help="0 = sin correlación, 1 = correlación perfecta positiva.",
                )
                interpretacion = (
                    "correlación fuerte — el índice es un buen predictor" if r > 0.6
                    else "correlación moderada — el índice tiene valor predictivo parcial" if r > 0.3
                    else "correlación débil — se necesitan más datos o ajustar el modelo"
                )
                col_r2.metric("Interpretación", interpretacion)

                fig_corr = px.scatter(
                    df_corr, x="indice_riesgo", y="focos",
                    trendline="ols",
                    labels={
                        "indice_riesgo": "Índice de riesgo meteorológico (calculado por nosotros)",
                        "focos": "Focos detectados por satélite FIRMS (dato externo)",
                    },
                    color_discrete_sequence=["#e67e22"],
                    height=380,
                )
                fig_corr.update_layout(
                    title="Cada punto = un día. La línea de tendencia muestra la correlación.",
                )
                st.plotly_chart(fig_corr, use_container_width=True)

                if r > 0.3:
                    st.success(
                        f"**Conclusión:** Con una correlación de {r:.3f}, el índice de riesgo calculado "
                        f"con datos de Open-Meteo **tiene valor predictivo real** sobre la actividad de "
                        "incendios detectada por satélite. Esto valida el diseño del modelo y justifica "
                        "su uso como herramienta de alerta temprana."
                    )
                else:
                    st.warning(
                        f"**Conclusión:** Con una correlación de {r:.3f}, el índice tiene capacidad "
                        "predictiva limitada con los datos disponibles. Se necesitan más puntos de "
                        "monitoreo o ajustar los pesos del modelo."
                    )
            else:
                st.info("Se necesitan más datos históricos para calcular la correlación.")
        else:
            st.warning("Se necesitan datos de focos y meteorología simultáneamente.")

    # ── Tab 5: Días críticos ──────────────────────────────────────────────────
    with tab_criticos:
        st.subheader("Días históricos con riesgo ALTO o MUY ALTO")
        st.caption(
            "Registro de todos los días en que al menos un punto de monitoreo superó el "
            "índice de riesgo 0.50. Esta tabla es el insumo para análisis post-evento "
            "y para correlacionar con datos de incendios reportados oficialmente."
        )
        df_crit = cargar_dias_criticos()
        if df_crit.empty:
            if not meteo.empty and "nivel_riesgo" in meteo.columns:
                df_crit = (
                    meteo[meteo["nivel_riesgo"].isin(["alto","muy_alto"])]
                    .groupby("fecha")
                    .agg(
                        puntos_en_alerta=("punto", "nunique"),
                        indice_maximo=("indice_riesgo", "max"),
                        puntos_afectados=("punto", lambda x: ", ".join(sorted(x.unique()))),
                    )
                    .reset_index()
                    .sort_values("fecha", ascending=False)
                )
        if not df_crit.empty:
            st.metric(
                "Total de días críticos registrados",
                len(df_crit),
                help="Días en que el índice de riesgo superó 0.50 en al menos un punto.",
            )
            cols_show = [c for c in [
                "fecha", "puntos_en_alerta", "indice_maximo", "puntos_afectados"
            ] if c in df_crit.columns]
            st.dataframe(df_crit[cols_show], use_container_width=True, height=400)

            st.info(
                "**Uso operativo:** estos días son candidatos para cruzar con reportes "
                "de incendios del MGAP/MIDES y validar la efectividad del sistema. "
                "Los días con `puntos_en_alerta > 1` son eventos de riesgo regional, "
                "no solo locales."
            )
        else:
            st.info("Sin días críticos registrados con los datos disponibles.")


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 6 — Comparativo por País
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Comparativo por País":

    st.title("Comparativo por País")
    st.caption("Análisis comparativo del índice de riesgo y actividad de incendios entre Uruguay, Brasil, Argentina y Chile")

    st.info(
        "**¿Para qué sirve esta página?**  \n"
        "Permite comparar la evolución del riesgo de incendio y la cantidad de focos detectados "
        "entre Uruguay, Brasil, Argentina y Chile.  \n"
        "Los datos se agregan mensualmente promediando los puntos de monitoreo de cada país. "
        "Esto permite identificar **qué países tienen mayor riesgo estacional** y en qué períodos.  \n\n"
        "Nota: esta vista requiere datos históricos cargados para los 36 puntos del alcance regional."
    )

    df_riesgo_pais  = cargar_riesgo_por_pais()
    df_focos_pais   = cargar_focos_por_pais_mes()

    tab_r, tab_f, tab_tabla = st.tabs([
        "Riesgo por país",
        "Focos por país",
        "Tabla comparativa",
    ])

    # ── Tab 1: Riesgo por país ────────────────────────────────────────────────
    with tab_r:
        st.subheader("Índice de riesgo mensual promedio por país")
        st.caption(
            "Promedio del Índice de Riesgo de Incendio (0–1) de todos los puntos de cada país, "
            "agrupado por mes. Permite ver qué países tienen mayor riesgo estacional."
        )
        if not df_riesgo_pais.empty:
            fig = px.line(
                df_riesgo_pais,
                x="mes", y="riesgo_promedio", color="pais",
                labels={"mes": "Mes", "riesgo_promedio": "Índice de Riesgo Promedio", "pais": "País"},
                title="Evolución mensual del riesgo por país",
                color_discrete_sequence=px.colors.qualitative.Set1,
            )
            fig.add_hline(y=0.5, line_dash="dot", line_color="red",
                          annotation_text="Umbral ALTO (0.50)")
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)

            # Ranking actual
            st.subheader("Ranking de riesgo promedio histórico")
            ranking = (
                df_riesgo_pais.groupby("pais")["riesgo_promedio"].mean()
                .sort_values(ascending=False).reset_index()
            )
            ranking.columns = ["País", "Riesgo Promedio"]
            ranking["Riesgo Promedio"] = ranking["Riesgo Promedio"].round(4)
            st.dataframe(ranking, use_container_width=True, height=260)
        else:
            st.warning(
                "Sin datos de riesgo por país disponibles. "
                "Ejecuta el ETL para los 36 puntos del alcance regional para ver esta comparación."
            )

    # ── Tab 2: Focos por país ─────────────────────────────────────────────────
    with tab_f:
        st.subheader("Total de focos de calor por país y mes")
        st.caption(
            "Cantidad de focos FIRMS detectados por mes en cada país. "
            "Brasil suele concentrar la mayor actividad y Argentina muestra estacionalidad más marcada en meses secos."
        )
        if not df_focos_pais.empty:
            fig_f = px.bar(
                df_focos_pais,
                x="mes", y="total_focos", color="pais", barmode="stack",
                labels={"mes": "Mes", "total_focos": "Focos detectados", "pais": "País"},
                title="Focos de calor mensuales por país",
                color_discrete_sequence=px.colors.qualitative.Set1,
            )
            fig_f.update_layout(height=420)
            st.plotly_chart(fig_f, use_container_width=True)

            # Tabla por país
            resumen_focos = (
                df_focos_pais.groupby("pais")
                .agg(
                    total_focos=("total_focos", "sum"),
                    frp_maximo=("frp_maximo", "max"),
                    meses_con_datos=("mes", "count"),
                )
                .sort_values("total_focos", ascending=False)
                .reset_index()
            )
            st.dataframe(resumen_focos, use_container_width=True, height=260)
        else:
            st.warning(
                "Sin datos de focos por país. "
                "Verificá que el ETL histórico haya corrido para los 36 puntos del alcance regional."
            )

    # ── Tab 3: Tabla comparativa ──────────────────────────────────────────────
    with tab_tabla:
        st.subheader("Comparativa directa entre países")
        st.caption(
            "Métricas agregadas históricas por país. "
            "Útil para presentar en la defensa como tabla comparativa."
        )
        if not df_riesgo_pais.empty and not df_focos_pais.empty:
            agg_r = df_riesgo_pais.groupby("pais").agg(
                riesgo_promedio=("riesgo_promedio", "mean"),
                riesgo_maximo=("riesgo_maximo", "max"),
                dias_criticos=("dias_criticos", "sum"),
            ).round(4).reset_index()

            agg_f = df_focos_pais.groupby("pais").agg(
                total_focos=("total_focos", "sum"),
                frp_maximo=("frp_maximo", "max"),
            ).reset_index()

            tabla = agg_r.merge(agg_f, on="pais", how="outer").fillna(0)
            tabla.columns = [
                "País", "Riesgo Promedio", "Riesgo Máximo",
                "Días Críticos", "Total Focos", "FRP Máximo (MW)"
            ]
            st.dataframe(tabla, use_container_width=True, height=320)

            st.info(
                "**Cómo leer esta tabla:**  \n"
                "- **Riesgo Promedio**: promedio histórico del Índice de Riesgo (0-1)  \n"
                "- **Días Críticos**: días con riesgo ALTO o MUY ALTO en al menos un punto  \n"
                "- **Total Focos**: focos de calor FIRMS detectados en el período  \n"
                "- **FRP Máximo**: máxima potencia radiativa registrada (mayor → incendio más intenso)"
            )
        elif not df_riesgo_pais.empty:
            st.dataframe(df_riesgo_pais, use_container_width=True)
        else:
            st.warning("Sin datos suficientes para la tabla comparativa.")

# ════════════════════════════════════════════════════════════════════════════
# PÁGINA: FUENTES Y DATOS CRUDOS
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Fuentes y Datos Crudos":
    import glob as _glob

    RAW = PROJECT_ROOT / "data" / "raw"

    st.title("Fuentes de Datos y Datos Crudos")
    st.markdown(
        "Esta sección muestra los datos **tal como llegan de cada fuente**, antes de cualquier transformación. "
        "Permite verificar que las APIs están siendo consumidas correctamente y que los datos son reales."
    )

    # ── FUENTE 1: NASA FIRMS ─────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("1. NASA FIRMS — Focos de Calor Satelitales")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
**Proveedor:** NASA / LANCE FIRMS
**Satélite:** VIIRS Suomi NPP (S-NPP) · Instrumento: VIIRS
**Acceso:** API REST gratuita (requiere clave, registro en NASA Earthdata)
**Granularidad:** Por foco individual detectado (~375m de resolución)
**Cobertura temporal:** 2018–2024 (histórico) + tiempo real (~3h latencia)
**Archivo ETL:** `etl/extract/extract_firms.py`
        """)
    with col2:
        firms_files = _glob.glob(str(RAW / "firms" / "*.csv"))
        total_firms = sum(1 for f in firms_files)
        st.metric("Archivos CSV descargados", total_firms)
        st.metric("Años cubiertos", "2018–2024")
        st.metric("Países cubiertos", "4")

    st.markdown("**Columnas del dato crudo:**")
    col_firms = {
        "latitude": "Latitud del foco (grados decimales)",
        "longitude": "Longitud del foco (grados decimales)",
        "bright_ti4": "Temperatura de brillo banda I4 (Kelvin) — detecta calor",
        "bright_ti5": "Temperatura de brillo banda I5 (Kelvin) — referencia",
        "scan": "Tamaño del pixel en dirección de escaneo (km)",
        "track": "Tamaño del pixel en dirección de avance (km)",
        "acq_date": "Fecha de adquisición (YYYY-MM-DD)",
        "acq_time": "Hora UTC de adquisición (HHMM)",
        "satellite": "Satélite (N = Suomi NPP)",
        "instrument": "Instrumento sensor (VIIRS)",
        "confidence": "Nivel de confianza de detección (n=nominal, h=high, l=low)",
        "version": "Versión del algoritmo de detección",
        "frp": "Fire Radiative Power — potencia del fuego en Megawatts (MW)",
        "daynight": "D=diurno, N=nocturno",
        "type": "Tipo de foco (0=vegetación, 1=volcán, 2=offshore, 3=otro)",
    }
    st.dataframe(
        pd.DataFrame(list(col_firms.items()), columns=["Columna", "Descripción"]),
        use_container_width=True, hide_index=True, height=300
    )

    firms_csv = RAW / "firms" / "firms_archive_VIIRS_SNPP_SP_2024-01-01_2024-03-31.csv"
    if firms_csv.exists():
        df_firms_raw = pd.read_csv(firms_csv)
        st.markdown(f"**Muestra de datos crudos** — `{firms_csv.name}` ({len(df_firms_raw):,} filas)")
        st.dataframe(df_firms_raw.head(10), use_container_width=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total filas (Q1 2024)", f"{len(df_firms_raw):,}")
        c2.metric("FRP máximo (MW)", f"{df_firms_raw['frp'].max():.1f}")
        c3.metric("FRP promedio (MW)", f"{df_firms_raw['frp'].mean():.2f}")
        c4.metric("Fechas", f"{df_firms_raw['acq_date'].min()} → {df_firms_raw['acq_date'].max()}")

    # ── FUENTE 2: OPEN-METEO (METEOROLOGÍA) ──────────────────────────────────
    st.markdown("---")
    st.subheader("2. Open-Meteo Archive — Meteorología Histórica Diaria")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
**Proveedor:** Open-Meteo (open-source, financiado por la comunidad)
**Modelo:** ERA5-Land (ECMWF) reanalysis + modelos regionales
**Acceso:** API REST completamente gratuita, sin clave
**Granularidad:** Diaria por punto geográfico
**Cobertura temporal:** Desde 1940 hasta ayer
**Puntos monitoreados:** 36 puntos: 19 departamentos de Uruguay + ciudades estratégicas de Brasil, Argentina y Chile + puntos volcánicos
**Archivo ETL:** `etl/extract/extract_meteo.py`
        """)
    with col2:
        meteo_files = _glob.glob(str(RAW / "meteo" / "*.csv"))
        st.metric("Archivos CSV descargados", len(meteo_files))
        st.metric("Ciudades/puntos", "36")
        st.metric("Años cubiertos", "2018–2024")

    st.markdown("**Columnas del dato crudo:**")
    col_meteo = {
        "fecha": "Fecha del registro (YYYY-MM-DD)",
        "temperature_2m_max": "Temperatura máxima diaria a 2m (°C)",
        "temperature_2m_min": "Temperatura mínima diaria a 2m (°C)",
        "relative_humidity_2m_max": "Humedad relativa máxima (%) — mayor → menor riesgo",
        "relative_humidity_2m_min": "Humedad relativa mínima (%) — menor → mayor riesgo",
        "wind_speed_10m_max": "Velocidad máxima del viento a 10m (km/h)",
        "wind_direction_10m_dominant": "Dirección dominante del viento (grados)",
        "precipitation_sum": "Precipitación acumulada diaria (mm)",
        "et0_fao_evapotranspiration": "Evapotranspiración FAO (mm/día) — indica sequía acumulada",
        "punto": "Nombre de la ciudad/punto de monitoreo",
        "latitud": "Latitud del punto (grados decimales)",
        "longitud": "Longitud del punto (grados decimales)",
    }
    st.dataframe(
        pd.DataFrame(list(col_meteo.items()), columns=["Columna", "Descripción"]),
        use_container_width=True, hide_index=True, height=250
    )

    meteo_csv = RAW / "meteo" / "meteo_rivera_daily_2024-01-01_2024-03-31.csv"
    if meteo_csv.exists():
        df_meteo_raw = pd.read_csv(meteo_csv)
        st.markdown(f"**Muestra de datos crudos** — `{meteo_csv.name}` ({len(df_meteo_raw):,} filas)")
        st.dataframe(df_meteo_raw.head(10), use_container_width=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total días", len(df_meteo_raw))
        c2.metric("Temp. máx. registrada", f"{df_meteo_raw['temperature_2m_max'].max():.1f} °C")
        c3.metric("Humedad mínima registrada", f"{df_meteo_raw['relative_humidity_2m_min'].min():.0f}%")

    # ── FUENTE 3: CAMS (CALIDAD DEL AIRE) ────────────────────────────────────
    st.markdown("---")
    st.subheader("3. CAMS vía Open-Meteo — Calidad del Aire")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
**Proveedor:** Copernicus Atmosphere Monitoring Service (CAMS) — Unión Europea
**Acceso:** Proxy gratuito vía Open-Meteo Air Quality API, sin clave
**Granularidad:** Horaria por punto (se agrega a diaria en ETL)
**Cobertura temporal:** 2018–2024
**Puntos monitoreados:** 36 puntos: Uruguay completo por departamentos + Brasil/Argentina estratégicos + Chile volcánico
**Archivo ETL:** `etl/extract/extract_cams.py`
        """)
    with col2:
        cams_files = _glob.glob(str(RAW / "cams" / "*.csv"))
        st.metric("Archivos CSV descargados", len(cams_files))
        st.metric("Granularidad original", "Horaria")
        st.metric("Granularidad en BD", "Diaria (promedio)")

    st.markdown("**Columnas del dato crudo:**")
    col_cams = {
        "fecha_hora": "Fecha y hora UTC del registro (ISO 8601)",
        "pm10": "Partículas en suspensión ≤10 µm (µg/m³) — límite OMS: 45",
        "pm2_5": "Partículas finas ≤2.5 µm (µg/m³) — límite OMS: 15",
        "aerosol_optical_depth": "Profundidad óptica de aerosoles (adimensional)",
        "dust": "Concentración de polvo en suspensión (µg/m³)",
        "european_aqi": "Índice europeo de calidad del aire (0-100, mayor=peor)",
        "european_aqi_pm10": "Sub-índice AQI para PM10",
        "european_aqi_pm2_5": "Sub-índice AQI para PM2.5",
        "punto": "Ciudad/punto de monitoreo",
        "latitud": "Latitud del punto",
        "longitud": "Longitud del punto",
        "fuente": "Identificador de la fuente (CAMS_via_OpenMeteo)",
    }
    st.dataframe(
        pd.DataFrame(list(col_cams.items()), columns=["Columna", "Descripción"]),
        use_container_width=True, hide_index=True, height=250
    )

    cams_csv = RAW / "cams" / "cams_rivera_hourly_2024-01-01_2024-01-31.csv"
    if cams_csv.exists():
        df_cams_raw = pd.read_csv(cams_csv)
        st.markdown(f"**Muestra de datos crudos** — `{cams_csv.name}` ({len(df_cams_raw):,} filas = horas)")
        st.dataframe(df_cams_raw.head(10), use_container_width=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total horas (enero 2024)", len(df_cams_raw))
        c2.metric("PM10 promedio (µg/m³)", f"{df_cams_raw['pm10'].mean():.2f}")
        c3.metric("Límite OMS PM10 (µg/m³)", "45.0")

    # ── FUENTE 4: CHIRPS (PRECIPITACIÓN SATELITAL) ───────────────────────────
    st.markdown("---")
    st.subheader("4. CHIRPS — Precipitación Mensual Satelital")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
**Proveedor:** Climate Hazards Group InfraRed Precipitation with Station data (UCSB)
**Acceso:** API gratuita vía ClimateSERV (NASA SERVIR)
**Granularidad:** Mensual por punto geográfico
**Cobertura temporal:** 1981–presente
**Puntos monitoreados:** 36 puntos: Uruguay completo por departamentos + Brasil/Argentina estratégicos + Chile volcánico
**Archivo ETL:** `etl/extract/extract_chirps.py`
        """)
    with col2:
        chirps_files = _glob.glob(str(RAW / "chirps" / "*.csv"))
        st.metric("Archivos CSV descargados", len(chirps_files))
        st.metric("Granularidad", "Mensual")
        st.metric("Variable principal", "Precipitación (mm)")

    chirps_csv = RAW / "chirps" / "chirps_asunción_2024_2024.csv"
    if chirps_csv.exists():
        df_chirps_raw = pd.read_csv(chirps_csv)
        st.markdown(f"**Muestra de datos crudos** — `{chirps_csv.name}`")
        st.dataframe(df_chirps_raw.head(10), use_container_width=True)

    # ── FUENTE 5: MODIS / NASA AppEEARS (COBERTURA VEGETAL) ─────────────────
    st.markdown("---")
    st.subheader("5. NASA MODIS — Cobertura Vegetal (NDVI)")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
**Proveedor:** NASA MODIS / AppEEARS (Application for Extracting and Exploring Analysis Ready Samples)
**Producto:** MCD12Q1 v6.1 — Land Cover Type (clasificación anual de uso del suelo)
**Acceso:** API gratuita vía NASA AppEEARS (requiere cuenta NASA Earthdata)
**Granularidad:** Anual por punto (resolución 500m)
**Cobertura temporal:** 2018–2024 (un valor por año por punto)
**Archivo ETL:** `etl/extract/extract_modis.py`
        """)
    with col2:
        modis_files = _glob.glob(str(RAW / "modis" / "*.csv"))
        st.metric("Archivos CSV descargados", len(modis_files))
        st.metric("Granularidad", "Anual")
        st.metric("Resolución espacial", "500m")

    modis_csv = list((RAW / "modis").glob("*.csv"))
    if modis_csv:
        df_modis_raw = pd.read_csv(modis_csv[0])
        st.markdown(f"**Muestra de datos crudos** — `{modis_csv[0].name}` ({len(df_modis_raw):,} filas)")
        st.dataframe(df_modis_raw.head(10), use_container_width=True)
        st.caption(
            "**LC_Type1**: tipo de cobertura IGBP. 1=Bosque perenne de agujas, 2=Bosque perenne de hojas, "
            "8=Sabana, 10=Pastizal, 12=Tierras de cultivo, 13=Urbano, 14=Mosaico cultivo/vegetación natural..."
        )

    # ── RESUMEN FINAL ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Resumen del volumen de datos crudos")

    resumen = []
    for fuente, carpeta, patron in [
        ("NASA FIRMS", "firms", "*.csv"),
        ("Open-Meteo Meteo", "meteo", "*.csv"),
        ("CAMS Calidad Aire", "cams", "*.csv"),
        ("CHIRPS Precipitación", "chirps", "*.csv"),
        ("MODIS Cobertura", "modis", "*.csv"),
    ]:
        archivos = _glob.glob(str(RAW / carpeta / patron))
        total_filas = 0
        for f in archivos:
            try:
                total_filas += sum(1 for _ in open(f, encoding="utf-8")) - 1
            except Exception:
                pass
        resumen.append({
            "Fuente": fuente,
            "Archivos CSV": len(archivos),
            "Filas totales (aprox)": f"{total_filas:,}",
            "Carpeta": f"data/raw/{carpeta}/",
        })

    st.dataframe(pd.DataFrame(resumen), use_container_width=True, hide_index=True)
    st.info(
        "Todos los datos crudos se guardan en `data/raw/` antes de ser procesados. "
        "Los datos transformados (limpios, normalizados) quedan en `data/processed/` como archivos Parquet. "
        "La base de datos PostgreSQL contiene la versión final consolidada."
    )
