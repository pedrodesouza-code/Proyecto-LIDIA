from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    for rel in (".env", "config/.env", "config/utec.env", "docker/.env"):
        path = ROOT / rel
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def pg_cfg() -> dict:
    env = load_env()
    return {
        "host": env.get("POSTGRES_HOST") or env.get("PG_HOST") or "localhost",
        "port": int(env.get("POSTGRES_PORT") or env.get("PG_PORT") or 5432),
        "database": env.get("POSTGRES_DB") or env.get("PG_DATABASE") or "grp03db",
        "user": env.get("POSTGRES_USER") or env.get("PG_USER") or "",
        "password": env.get("POSTGRES_PASSWORD") or env.get("PG_PASSWORD") or "",
    }


def mongo_cfg() -> dict:
    env = load_env()
    database = env.get("MONGO_DB") or env.get("MONGO_DATABASE") or "grp03db"
    return {
        "host": env.get("MONGO_HOST") or "localhost",
        "port": int(env.get("MONGO_PORT") or 27017),
        "database": database,
        "user": env.get("MONGO_USER") or "",
        "password": env.get("MONGO_PASSWORD") or "",
        "auth_source": env.get("MONGO_AUTH_SOURCE") or database,
    }


def data_roots() -> list[Path]:
    env = load_env()
    roots = [ROOT / "data"]
    external = env.get("DIR_DATOS_EXTERNOS")
    if external:
        roots.append(Path(external))
    roots.append(ROOT.parent / "data")
    out: list[Path] = []
    for root in roots:
        if root not in out:
            out.append(root)
    return out


@st.cache_data(ttl=180, show_spinner=False)
def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    import psycopg2

    with psycopg2.connect(**pg_cfg(), connect_timeout=5) as conn:
        return pd.read_sql_query(sql, conn, params=params)


@st.cache_data(ttl=300, show_spinner=False)
def date_bounds() -> tuple[pd.Timestamp, pd.Timestamp]:
    df = query("""
        SELECT MIN(d.fecha)::date AS min_fecha, MAX(d.fecha)::date AS max_fecha
        FROM dw.fact_incendio f
        JOIN dw.dim_fecha d ON d.fecha_id = f.fecha_id
    """)
    return pd.to_datetime(df.loc[0, "min_fecha"]), pd.to_datetime(df.loc[0, "max_fecha"])


@st.cache_data(ttl=300, show_spinner=False)
def countries() -> pd.DataFrame:
    return query("""
        SELECT u.pais_codigo, COALESCE(u.pais_nombre, u.pais_codigo) AS pais_nombre, COUNT(*) AS focos
        FROM dw.fact_incendio f
        JOIN dw.dim_ubicacion u ON u.ubicacion_id = f.ubicacion_id
        GROUP BY 1, 2
        ORDER BY focos DESC
    """)


def where_clause(fecha_inicio, fecha_fin, pais_codigo: str) -> tuple[str, tuple]:
    clauses = ["d.fecha BETWEEN %s AND %s"]
    params: list = [fecha_inicio, fecha_fin]
    if pais_codigo != "Todos":
        clauses.append("u.pais_codigo = %s")
        params.append(pais_codigo)
    return "WHERE " + " AND ".join(clauses), tuple(params)


@st.cache_data(ttl=180, show_spinner=False)
def kpis(fecha_inicio, fecha_fin, pais_codigo: str) -> pd.DataFrame:
    where, params = where_clause(fecha_inicio, fecha_fin, pais_codigo)
    return query(f"""
        SELECT
            COUNT(*)::bigint AS total_focos,
            COUNT(*) FILTER (WHERE f.confidence >= 80)::bigint AS alta_confianza,
            COUNT(*) FILTER (WHERE f.daynight = 'D')::bigint AS diurnos,
            COUNT(*) FILTER (WHERE f.daynight = 'N')::bigint AS nocturnos,
            AVG(f.frp_mw)::numeric(12,2) AS frp_promedio,
            MAX(f.frp_mw)::numeric(12,2) AS frp_maximo,
            COUNT(DISTINCT u.ubicacion_id)::bigint AS ubicaciones,
            COUNT(DISTINCT d.fecha)::bigint AS dias
        FROM dw.fact_incendio f
        JOIN dw.dim_fecha d ON d.fecha_id = f.fecha_id
        JOIN dw.dim_ubicacion u ON u.ubicacion_id = f.ubicacion_id
        {where}
    """, params)


@st.cache_data(ttl=180, show_spinner=False)
def monthly(fecha_inicio, fecha_fin, pais_codigo: str) -> pd.DataFrame:
    where, params = where_clause(fecha_inicio, fecha_fin, pais_codigo)
    df = query(f"""
        SELECT
            DATE_TRUNC('month', d.fecha)::date AS mes,
            COUNT(*)::bigint AS focos,
            AVG(f.frp_mw)::numeric(12,2) AS frp_promedio,
            COUNT(*) FILTER (WHERE f.confidence >= 80)::bigint AS alta_confianza
        FROM dw.fact_incendio f
        JOIN dw.dim_fecha d ON d.fecha_id = f.fecha_id
        JOIN dw.dim_ubicacion u ON u.ubicacion_id = f.ubicacion_id
        {where}
        GROUP BY 1
        ORDER BY 1
    """, params)
    if not df.empty:
        df["mes"] = pd.to_datetime(df["mes"])
    return df


@st.cache_data(ttl=180, show_spinner=False)
def by_country(fecha_inicio, fecha_fin, pais_codigo: str) -> pd.DataFrame:
    where, params = where_clause(fecha_inicio, fecha_fin, pais_codigo)
    return query(f"""
        SELECT
            COALESCE(u.pais_nombre, u.pais_codigo) AS pais,
            COUNT(*)::bigint AS focos,
            AVG(f.frp_mw)::numeric(12,2) AS frp_promedio,
            MAX(f.frp_mw)::numeric(12,2) AS frp_maximo
        FROM dw.fact_incendio f
        JOIN dw.dim_fecha d ON d.fecha_id = f.fecha_id
        JOIN dw.dim_ubicacion u ON u.ubicacion_id = f.ubicacion_id
        {where}
        GROUP BY 1
        ORDER BY focos DESC
        LIMIT 15
    """, params)


@st.cache_data(ttl=180, show_spinner=False)
def by_satellite(fecha_inicio, fecha_fin, pais_codigo: str) -> pd.DataFrame:
    where, params = where_clause(fecha_inicio, fecha_fin, pais_codigo)
    return query(f"""
        SELECT
            COALESCE(f.satellite, 'SIN_DATO') AS satelite,
            COALESCE(f.instrument, 'SIN_DATO') AS instrumento,
            COUNT(*)::bigint AS focos
        FROM dw.fact_incendio f
        JOIN dw.dim_fecha d ON d.fecha_id = f.fecha_id
        JOIN dw.dim_ubicacion u ON u.ubicacion_id = f.ubicacion_id
        {where}
        GROUP BY 1, 2
        ORDER BY focos DESC
    """, params)


@st.cache_data(ttl=180, show_spinner=False)
def map_points(fecha_inicio, fecha_fin, pais_codigo: str, limit: int) -> pd.DataFrame:
    where, params = where_clause(fecha_inicio, fecha_fin, pais_codigo)
    return query(f"""
        SELECT
            f.latitud_original::float AS lat,
            f.longitud_original::float AS lon,
            f.frp_mw::float AS frp_mw,
            f.confidence,
            d.fecha,
            COALESCE(u.pais_nombre, u.pais_codigo) AS pais
        FROM dw.fact_incendio f
        JOIN dw.dim_fecha d ON d.fecha_id = f.fecha_id
        JOIN dw.dim_ubicacion u ON u.ubicacion_id = f.ubicacion_id
        {where}
        ORDER BY f.frp_mw DESC NULLS LAST
        LIMIT %s
    """, (*params, limit))


@st.cache_data(ttl=300, show_spinner=False)
def climate_summary() -> pd.DataFrame:
    return query("""
        SELECT
            COUNT(*)::bigint AS registros_meteo,
            MIN(fecha)::date AS desde,
            MAX(fecha)::date AS hasta,
            AVG(indice_riesgo)::numeric(10,2) AS riesgo_promedio,
            COUNT(*) FILTER (WHERE nivel_riesgo IN ('ALTO', 'EXTREMO', 'Muy Alto', 'Alto'))::bigint AS dias_criticos
        FROM public.v_riesgo_historico
        WHERE tipo_dato = 'historico'
    """)


@st.cache_data(ttl=300, show_spinner=False)
def current_risk() -> pd.DataFrame:
    return query("""
        SELECT punto, pais, fecha, indice_riesgo, nivel_riesgo, temp_max, humedad_min, viento_max, precipitacion
        FROM public.v_riesgo_actual
        ORDER BY indice_riesgo DESC NULLS LAST, punto
    """)


@st.cache_data(ttl=300, show_spinner=False)
def public_counts() -> pd.DataFrame:
    return query("""
        SELECT 'FIRMS historico en DW' AS capa, COUNT(*)::bigint AS registros FROM dw.fact_incendio
        UNION ALL SELECT 'FIRMS operativo', COUNT(*)::bigint FROM public.focos_calor
        UNION ALL SELECT 'Open-Meteo', COUNT(*)::bigint FROM public.meteo_diario
        UNION ALL SELECT 'Calidad de aire', COUNT(*)::bigint FROM public.calidad_aire_diario
        UNION ALL SELECT 'CHIRPS precipitacion', COUNT(*)::bigint FROM public.precipitacion_mensual
        UNION ALL SELECT 'MODIS cobertura', COUNT(*)::bigint FROM public.cobertura_vegetal
        ORDER BY registros DESC
    """)


@st.cache_data(ttl=300, show_spinner=False)
def postgres_coverage() -> pd.DataFrame:
    return query("""
        SELECT 'staging' AS capa, 'stg_firms_incendios' AS tabla, COUNT(*)::bigint AS registros FROM staging.stg_firms_incendios
        UNION ALL SELECT 'staging', 'stg_openmeteo_clima', COUNT(*)::bigint FROM staging.stg_openmeteo_clima
        UNION ALL SELECT 'staging', 'stg_chirps_precipitacion', COUNT(*)::bigint FROM staging.stg_chirps_precipitacion
        UNION ALL SELECT 'staging', 'stg_modis_cobertura', COUNT(*)::bigint FROM staging.stg_modis_cobertura
        UNION ALL SELECT 'staging', 'stg_calidad_aire', COUNT(*)::bigint FROM staging.stg_calidad_aire
        UNION ALL SELECT 'public', 'focos_calor', COUNT(*)::bigint FROM public.focos_calor
        UNION ALL SELECT 'public', 'meteo_diario', COUNT(*)::bigint FROM public.meteo_diario
        UNION ALL SELECT 'public', 'calidad_aire_diario', COUNT(*)::bigint FROM public.calidad_aire_diario
        UNION ALL SELECT 'public', 'precipitacion_mensual', COUNT(*)::bigint FROM public.precipitacion_mensual
        UNION ALL SELECT 'public', 'cobertura_vegetal', COUNT(*)::bigint FROM public.cobertura_vegetal
        UNION ALL SELECT 'dw', 'fact_incendio', COUNT(*)::bigint FROM dw.fact_incendio
        UNION ALL SELECT 'dw', 'dim_fecha', COUNT(*)::bigint FROM dw.dim_fecha
        UNION ALL SELECT 'dw', 'dim_ubicacion', COUNT(*)::bigint FROM dw.dim_ubicacion
        UNION ALL SELECT 'dw', 'dim_clima', COUNT(*)::bigint FROM dw.dim_clima
        UNION ALL SELECT 'dw', 'dim_precipitacion', COUNT(*)::bigint FROM dw.dim_precipitacion
        UNION ALL SELECT 'dw', 'dim_cobertura_vegetal', COUNT(*)::bigint FROM dw.dim_cobertura_vegetal
        UNION ALL SELECT 'dw', 'dim_calidad_aire', COUNT(*)::bigint FROM dw.dim_calidad_aire
        ORDER BY capa, registros DESC, tabla
    """)


@st.cache_data(ttl=300, show_spinner=False)
def fact_environment_links() -> pd.DataFrame:
    return query("""
        SELECT
            COUNT(*)::bigint AS total_focos_dw,
            COUNT(*) FILTER (WHERE clima_id IS NOT NULL)::bigint AS con_clima,
            COUNT(*) FILTER (WHERE calidad_aire_id IS NOT NULL)::bigint AS con_calidad_aire,
            COUNT(*) FILTER (WHERE precipitacion_id IS NOT NULL)::bigint AS con_precipitacion,
            COUNT(*) FILTER (WHERE cobertura_vegetal_id IS NOT NULL)::bigint AS con_cobertura
        FROM dw.fact_incendio
    """)


@st.cache_data(ttl=300, show_spinner=False)
def mongo_collection_counts() -> pd.DataFrame:
    from pymongo import MongoClient

    cfg = mongo_cfg()
    uri = (
        f"mongodb://{cfg['user']}:{cfg['password']}@"
        f"{cfg['host']}:{cfg['port']}/{cfg['database']}?authSource={cfg['auth_source']}"
    )
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        db = client[cfg["database"]]
        rows = []
        for name in sorted(db.list_collection_names()):
            rows.append({"collection": name, "documentos": db[name].estimated_document_count()})
        return pd.DataFrame(rows)
    finally:
        client.close()


@st.cache_data(ttl=120, show_spinner=False)
def etl_runs() -> pd.DataFrame:
    return query("""
        SELECT run_id, source, status, rows_extracted, rows_loaded, started_at, finished_at
        FROM audit.etl_runs
        ORDER BY started_at DESC NULLS LAST
        LIMIT 30
    """)


def inventory() -> pd.DataFrame:
    records = []
    wanted_suffixes = {".shp", ".dbf", ".shx", ".prj", ".cpg", ".csv", ".parquet", ".json"}
    for root in data_roots():
        if not root.exists():
            records.append({"ruta": str(root), "tipo": "missing", "tamano_mb": None})
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() in wanted_suffixes:
                records.append({
                    "ruta": str(path),
                    "tipo": path.suffix.lower().lstrip("."),
                    "tamano_mb": round(path.stat().st_size / 1024 / 1024, 2),
                })
    return pd.DataFrame(records)


def fmt_int(value) -> str:
    if pd.isna(value):
        return "0"
    return f"{int(value):,}".replace(",", ".")


def fmt_num(value, suffix: str = "") -> str:
    if pd.isna(value):
        return "s/d"
    return f"{float(value):,.2f}{suffix}".replace(",", "X").replace(".", ",").replace("X", ".")


st.set_page_config(page_title="SINIA-SA EC3", layout="wide")

st.markdown("""
<style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 0.75rem 0.85rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    h1, h2, h3 {letter-spacing: 0;}
    div[data-testid="stDataFrame"] {border: 1px solid #e5e7eb; border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

st.title("SINIA-SA | Incendios forestales y riesgo ambiental")
st.caption("Dashboard EC3 conectado a PostgreSQL UTEC, datasets FIRMS/Open-Meteo/CHIRPS/MODIS y trazabilidad de pipeline.")

try:
    min_fecha, max_fecha = date_bounds()
    paises = countries()
except Exception as exc:
    st.error("No se pudo conectar al Data Warehouse PostgreSQL.")
    st.exception(exc)
    st.stop()

with st.sidebar:
    st.header("Filtros")
    selected_range = st.date_input(
        "Periodo",
        value=(min_fecha.date(), max_fecha.date()),
        min_value=min_fecha.date(),
        max_value=max_fecha.date(),
    )
    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        fecha_inicio, fecha_fin = selected_range
    else:
        fecha_inicio = min_fecha.date()
        fecha_fin = max_fecha.date()

    pais_options = ["Todos"] + paises["pais_codigo"].dropna().astype(str).tolist()
    pais_codigo = st.selectbox("Pais", pais_options)
    map_limit = st.slider("Puntos en mapa", min_value=250, max_value=5000, value=1500, step=250)

    st.divider()
    st.caption("Estado")
    st.write(f"DW: `{pg_cfg()['host']}:{pg_cfg()['port']}`")
    st.write(f"Rango FIRMS: `{min_fecha.date()}` a `{max_fecha.date()}`")

tab_resumen, tab_mapa, tab_ambiente, tab_datos, tab_pipeline = st.tabs([
    "Resumen",
    "Mapa",
    "Ambiente",
    "Datos",
    "Pipeline",
])

with tab_resumen:
    kpi = kpis(fecha_inicio, fecha_fin, pais_codigo).iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Focos FIRMS", fmt_int(kpi["total_focos"]))
    c2.metric("Alta confianza", fmt_int(kpi["alta_confianza"]))
    c3.metric("FRP promedio", fmt_num(kpi["frp_promedio"], " MW"))
    c4.metric("FRP maximo", fmt_num(kpi["frp_maximo"], " MW"))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Ubicaciones", fmt_int(kpi["ubicaciones"]))
    c6.metric("Dias cubiertos", fmt_int(kpi["dias"]))
    c7.metric("Diurnos", fmt_int(kpi["diurnos"]))
    c8.metric("Nocturnos", fmt_int(kpi["nocturnos"]))

    serie = monthly(fecha_inicio, fecha_fin, pais_codigo)
    left, right = st.columns([1.55, 1])
    with left:
        st.subheader("Evolucion mensual")
        if serie.empty:
            st.info("No hay datos para el filtro seleccionado.")
        else:
            st.line_chart(serie.set_index("mes")[["focos", "alta_confianza"]])
    with right:
        st.subheader("Top paises")
        pais_df = by_country(fecha_inicio, fecha_fin, pais_codigo)
        if not pais_df.empty:
            st.bar_chart(pais_df.set_index("pais")["focos"])

    st.subheader("Satelite e instrumento")
    sat = by_satellite(fecha_inicio, fecha_fin, pais_codigo)
    st.dataframe(sat, use_container_width=True, hide_index=True)

with tab_mapa:
    st.subheader("Focos mas intensos por FRP")
    pts = map_points(fecha_inicio, fecha_fin, pais_codigo, map_limit)
    if pts.empty:
        st.info("No hay puntos para mostrar.")
    else:
        st.map(pts[["lat", "lon"]], size=10)
        st.dataframe(
            pts.assign(fecha=pd.to_datetime(pts["fecha"]).dt.date).head(300),
            use_container_width=True,
            hide_index=True,
        )

with tab_ambiente:
    st.subheader("Riesgo meteorologico y variables ambientales")
    try:
        clima = climate_summary().iloc[0]
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Registros Open-Meteo", fmt_int(clima["registros_meteo"]))
        a2.metric("Riesgo promedio", fmt_num(clima["riesgo_promedio"]))
        a3.metric("Dias criticos", fmt_int(clima["dias_criticos"]))
        a4.metric("Cobertura", f"{clima['desde']} a {clima['hasta']}")
        riesgo = current_risk()
        st.dataframe(riesgo, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.warning(f"No se pudo leer la capa ambiental: {type(exc).__name__}: {exc}")

with tab_datos:
    st.subheader("Cobertura real del proyecto")
    st.info(
        "Los archivos completos viven en Jupyter. PostgreSQL contiene el DW analitico y tablas operativas. "
        "MongoDB se usa para trazabilidad, snapshots y logs; no es la base principal para millones de focos."
    )

    st.subheader("PostgreSQL por capa")
    pg_cov = postgres_coverage()
    st.dataframe(pg_cov, use_container_width=True, hide_index=True)

    st.subheader("Integracion ambiental en la tabla de hechos")
    links = fact_environment_links()
    if not links.empty:
        row = links.iloc[0]
        l1, l2, l3, l4, l5 = st.columns(5)
        l1.metric("Focos DW", fmt_int(row["total_focos_dw"]))
        l2.metric("Con clima", fmt_int(row["con_clima"]))
        l3.metric("Con aire", fmt_int(row["con_calidad_aire"]))
        l4.metric("Con precipitacion", fmt_int(row["con_precipitacion"]))
        l5.metric("Con cobertura", fmt_int(row["con_cobertura"]))
        if int(row["con_clima"] or 0) == 0:
            st.warning(
                "Pendiente tecnico: las capas ambientales existen en tablas publicas, "
                "pero todavia no estan enlazadas como dimensiones del modelo estrella."
            )

    st.subheader("MongoDB")
    try:
        mongo_counts = mongo_collection_counts()
        st.dataframe(mongo_counts, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.warning(f"No se pudo consultar MongoDB: {type(exc).__name__}: {exc}")

    st.subheader("Resumen de capas operativas")
    st.dataframe(public_counts(), use_container_width=True, hide_index=True)

    st.subheader("Archivos disponibles en Jupyter")
    inv = inventory()
    if inv.empty:
        st.warning("No se encontraron archivos de datos en las rutas configuradas.")
    else:
        total_mb = inv["tamano_mb"].fillna(0).sum()
        st.metric("Peso visible en archivos", fmt_num(total_mb, " MB"))
        st.dataframe(inv.sort_values(["tipo", "ruta"]), use_container_width=True, hide_index=True)

with tab_pipeline:
    st.subheader("Ejecuciones ETL")
    try:
        st.dataframe(etl_runs(), use_container_width=True, hide_index=True)
    except Exception as exc:
        st.warning(f"No se pudo leer audit.etl_runs: {type(exc).__name__}: {exc}")
