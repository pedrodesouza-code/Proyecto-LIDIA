from __future__ import annotations

import argparse
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import PG_CONFIG, PAISES_SA, PUNTOS_METEO_SA


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_ROOTS = [
    ROOT / "data" / "raw",
    Path("/app/Proyecto-LIDIA/data/raw"),
    Path("/home/pepo/Datos completos"),
]

URUGUAY_DEPARTAMENTOS = {
    "Artigas": (-30.40, -56.47),
    "Canelones": (-34.52, -56.28),
    "Cerro Largo": (-32.37, -54.17),
    "Colonia": (-34.47, -57.84),
    "Durazno": (-33.41, -56.50),
    "Flores": (-33.54, -56.89),
    "Florida": (-34.10, -56.21),
    "Lavalleja": (-34.37, -55.23),
    "Maldonado": (-34.90, -54.95),
    "Montevideo": (-34.90, -56.16),
    "Paysandu": (-32.32, -58.08),
    "Paysandú": (-32.32, -58.08),
    "Rivera": (-30.90, -55.55),
    "Rocha": (-34.48, -54.33),
    "Rio Negro": (-33.12, -58.31),
    "Río Negro": (-33.12, -58.31),
    "Salto": (-31.38, -57.97),
    "San Jose": (-34.34, -56.71),
    "San José": (-34.34, -56.71),
    "Soriano": (-33.25, -58.03),
    "Tacuarembo": (-31.73, -55.98),
    "Tacuarembó": (-31.73, -55.98),
    "Treinta y Tres": (-33.23, -54.38),
}

IGBP_LABELS = {
    1: "Bosque siempreverde coniferas",
    2: "Bosque caducifolio coniferas",
    3: "Bosque siempreverde hoja ancha",
    4: "Bosque caducifolio hoja ancha",
    5: "Bosque mixto",
    6: "Arbustal cerrado",
    7: "Arbustal abierto",
    8: "Sabana arbolada",
    9: "Sabana",
    10: "Pastizal",
    11: "Humedal permanente",
    12: "Tierra de cultivo",
    13: "Zona urbana",
    14: "Cultivo/Vegetacion mosaico",
    15: "Nieve y hielo",
    16: "Suelo desnudo",
    17: "Cuerpo de agua",
    255: "Sin clasificar",
}

COMBUSTIBILIDAD = {
    1: "alta",
    2: "alta",
    3: "alta",
    4: "alta",
    5: "alta",
    6: "media",
    7: "media",
    8: "media",
    9: "alta",
    10: "alta",
    11: "baja",
    12: "media",
    13: "baja",
    14: "media",
    15: "baja",
    16: "baja",
    17: "baja",
    255: "no clasificada",
}


def _conn():
    return psycopg2.connect(**PG_CONFIG)


def _safe(v: Any) -> Any:
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except TypeError:
        pass
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    if hasattr(v, "to_pydatetime"):
        return v.to_pydatetime()
    return v


def _find_file(relatives: list[str]) -> Path:
    for root in DEFAULT_DATA_ROOTS:
        for rel in relatives:
            candidate = root / rel
            if candidate.exists():
                return candidate
    raise FileNotFoundError(f"No se encontro ninguno de: {relatives}")


def _pais_nombre(codigo: str | None) -> str | None:
    if not codigo:
        return None
    if codigo == "URY":
        return "Uruguay"
    return PAISES_SA.get(codigo, {}).get("nombre")


def _nearest_point(lat: float, lon: float) -> tuple[str | None, str | None]:
    known = [
        (-34.90, -56.20, "URY", "UY_Montevideo"),
        (-34.90, -56.16, "URY", "UY_Montevideo"),
        (-34.60, -58.40, "ARG", "Buenos_Aires"),
        (-23.50, -46.60, "BRA", "BR_Sao_Paulo"),
    ]
    for known_lat, known_lon, pais, name in known:
        if abs(lat - known_lat) <= 0.15 and abs(lon - known_lon) <= 0.15:
            return pais, name
    best_name = None
    best_dist = float("inf")
    for name, info in PUNTOS_METEO_SA.items():
        dist = (float(info["lat"]) - lat) ** 2 + (float(info["lon"]) - lon) ** 2
        if dist < best_dist:
            best_name = name
            best_dist = dist
    if best_name is None or best_dist > 1.0:
        return None, None
    codigo = PUNTOS_METEO_SA[best_name]["pais"]
    return codigo, best_name


def _location_country(location: str | None, lat: float | None = None, lon: float | None = None) -> tuple[str | None, str | None]:
    if location and "_" in location:
        prefix = location.split("_", 1)[0]
        code_map = {"UY": "URY", "AR": "ARG", "BR": "BRA", "BO": "BOL", "PY": "PRY", "CL": "CHL", "PE": "PER"}
        if prefix in code_map:
            return code_map[prefix], location
    if lat is not None and lon is not None:
        return _nearest_point(float(lat), float(lon))
    return None, None


def _hash_series(df: pd.DataFrame, cols: list[str], prefix: str) -> pd.Series:
    values = pd.util.hash_pandas_object(df[cols].astype("string"), index=False)
    return prefix + "_" + values.map(lambda x: f"{int(x):016x}").astype(str)


def _next_id(conn, table: str, id_col: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COALESCE(MAX({id_col}), 0) + 1 FROM {table}")  # noqa: S608
        return int(cur.fetchone()[0])


def _insert_values(conn, table: str, columns: list[str], rows: list[tuple], update_columns: list[str]) -> int:
    if not rows:
        return 0
    assignments = ", ".join(f"{col}=EXCLUDED.{col}" for col in update_columns)
    sql = f"""
        INSERT INTO {table} ({", ".join(columns)})
        VALUES %s
        ON CONFLICT (record_hash) DO UPDATE SET {assignments}
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, rows, page_size=5000)
    return len(rows)


def _write_audit(conn, run_id: str, source: str, rows: int, status: str, seconds: float, error: str | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(etl_run_id), 0) + 1 FROM audit.etl_runs")
        etl_run_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO audit.etl_runs (
                etl_run_id, run_id, source_name, pipeline_name, load_type, status,
                started_at, finished_at, duration_seconds,
                records_extracted, records_transformed, records_loaded, records_rejected,
                parameters, error_message
            )
            VALUES (
                %s, %s, %s, 'cargar_staging_ambiental', 'full', %s,
                NOW() - (%s || ' seconds')::interval, NOW(), %s,
                %s, %s, %s, 0, %s::jsonb, %s
            )
            ON CONFLICT (run_id) DO NOTHING
            """,
            (
                etl_run_id,
                run_id,
                source,
                status,
                seconds,
                round(seconds, 3),
                rows,
                rows,
                rows if status == "success" else 0,
                '{"target":"staging"}',
                error,
            ),
        )
        cur.execute("SELECT COALESCE(MAX(log_id), 0) + 1 FROM audit.pipeline_logs")
        log_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO audit.pipeline_logs (log_id, run_id, log_level, step_name, message, details)
            VALUES (%s, %s, %s, 'load_staging', %s, %s::jsonb)
            """,
            (
                log_id,
                run_id,
                "INFO" if status == "success" else "ERROR",
                f"{source}: {status}, rows={rows}",
                f'{{"source":"{source}","rows":{rows}}}',
            ),
        )


def load_openmeteo(conn, batch_id: str, chunk_size: int) -> int:
    path = _find_file(["Open_meteo/clima_completo.parquet", "clima_completo.parquet"])
    df = pd.read_parquet(path)
    df = df.rename(columns={
        "date": "fecha_hora",
        "lat": "latitude",
        "lon": "longitude",
        "temperature": "temperature_2m",
        "humidity": "relative_humidity_2m",
        "wind_speed": "wind_speed_10m",
        "wind_direction": "wind_direction_10m",
    })
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"], utc=True).dt.tz_localize(None)
    df["fecha"] = df["fecha_hora"].dt.date
    countries = df.apply(lambda r: _location_country(None, r["latitude"], r["longitude"]), axis=1)
    df["pais_codigo"] = [c[0] for c in countries]
    df["departamento"] = [c[1] for c in countries]
    df["pais_nombre"] = df["pais_codigo"].map(_pais_nombre)
    df["region"] = None
    df["record_hash"] = _hash_series(df, ["fecha_hora", "latitude", "longitude"], "openmeteo")
    df["source_file"] = str(path)
    df["batch_id"] = batch_id
    df["raw_payload"] = None
    start_id = _next_id(conn, "staging.stg_openmeteo_clima", "stg_clima_id")
    df.insert(0, "stg_clima_id", range(start_id, start_id + len(df)))
    columns = [
        "stg_clima_id", "batch_id", "source_file", "location_id", "fecha_hora", "fecha",
        "latitude", "longitude", "temperature_2m", "relative_humidity_2m",
        "wind_speed_10m", "wind_direction_10m", "rain", "pais_codigo", "pais_nombre",
        "region", "departamento", "record_hash", "raw_payload",
    ]
    df["location_id"] = None
    return _load_dataframe(conn, "staging.stg_openmeteo_clima", df, columns, chunk_size)


def load_air_quality(conn, batch_id: str, chunk_size: int) -> int:
    path = _find_file(["Open_meteo/air_quality_regional.parquet"])
    df = pd.read_parquet(path)
    df = df.rename(columns={"date": "fecha_hora", "lat": "latitude", "lon": "longitude"})
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"], utc=True).dt.tz_localize(None)
    df["fecha"] = df["fecha_hora"].dt.date
    code_map = {"UY": "URY", "AR": "ARG", "BR": "BRA", "BO": "BOL", "PY": "PRY", "CL": "CHL", "PE": "PER"}
    prefix = df["location"].astype("string").str.split("_", n=1).str[0]
    df["pais_codigo"] = prefix.map(code_map)
    df["departamento"] = df["location"]
    df["pais_nombre"] = df["pais_codigo"].map(_pais_nombre)
    df["region"] = None
    df["record_hash"] = _hash_series(df, ["location", "fecha_hora", "latitude", "longitude"], "air")
    df["source_file"] = str(path)
    df["batch_id"] = batch_id
    df["location_id"] = None
    df["co"] = None
    df["no2"] = None
    df["o3"] = None
    df["raw_payload"] = None
    start_id = _next_id(conn, "staging.stg_calidad_aire", "stg_calidad_aire_id")
    df.insert(0, "stg_calidad_aire_id", range(start_id, start_id + len(df)))
    columns = [
        "stg_calidad_aire_id", "batch_id", "source_file", "location_id", "fecha_hora", "fecha",
        "latitude", "longitude", "pm10", "pm2_5", "co", "no2", "o3", "pais_codigo",
        "pais_nombre", "region", "departamento", "record_hash", "raw_payload",
    ]
    return _load_dataframe(conn, "staging.stg_calidad_aire", df, columns, chunk_size)


def load_chirps(conn, batch_id: str, chunk_size: int) -> int:
    path = _find_file(["chirps_daily/csv_unificado.csv"])
    df = pd.read_csv(path)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha", "precipitacion_mm", "punto"])
    df = df[df["precipitacion_mm"] >= 0].copy()
    df["anio"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    monthly_mean = df.groupby(["punto", "mes"])["precipitacion_mm"].transform("mean")
    df["precipitacion_anomalia_pct"] = ((df["precipitacion_mm"] - monthly_mean) / monthly_mean.replace(0, np.nan)).round(4)
    df["latitude"] = df["punto"].map(lambda p: PUNTOS_METEO_SA.get(p, {}).get("lat"))
    df["longitude"] = df["punto"].map(lambda p: PUNTOS_METEO_SA.get(p, {}).get("lon"))
    df["pais_codigo"] = df["punto"].map(lambda p: PUNTOS_METEO_SA.get(p, {}).get("pais"))
    df["pais_nombre"] = df["pais_codigo"].map(_pais_nombre)
    df["region"] = None
    df["departamento"] = df["punto"]
    df = df.dropna(subset=["latitude", "longitude"])
    df["record_hash"] = _hash_series(df, ["punto", "anio", "mes"], "chirps")
    df["source_file"] = str(path)
    df["batch_id"] = batch_id
    df["raw_payload"] = None
    df = df.rename(columns={"precipitacion_mm": "precipitacion_acumulada_mm"})
    start_id = _next_id(conn, "staging.stg_chirps_precipitacion", "stg_precipitacion_id")
    df.insert(0, "stg_precipitacion_id", range(start_id, start_id + len(df)))
    columns = [
        "stg_precipitacion_id", "batch_id", "source_file", "anio", "mes", "latitude",
        "longitude", "precipitacion_acumulada_mm", "precipitacion_anomalia_pct",
        "pais_codigo", "pais_nombre", "region", "departamento", "record_hash", "raw_payload",
    ]
    return _load_dataframe(conn, "staging.stg_chirps_precipitacion", df, columns, chunk_size)


def load_modis(conn, batch_id: str, chunk_size: int) -> int:
    path = _find_file(["MODIS/modis_todos.csv"])
    df = pd.read_csv(path)
    df["anio"] = df["archivo"].astype(str).str.extract(r"doy(20\d{2})", expand=False).astype("Int64")
    df = df.dropna(subset=["anio", "lat", "lon", "valor"]).copy()
    df["anio"] = df["anio"].astype(int)
    df["codigo_cobertura"] = pd.to_numeric(df["valor"], errors="coerce").fillna(255).astype(int)
    df["tipo_cobertura"] = "IGBP_LC_Type1"
    df["descripcion_cobertura"] = df["codigo_cobertura"].map(IGBP_LABELS).fillna("Sin clasificar")
    df["combustibilidad"] = df["codigo_cobertura"].map(COMBUSTIBILIDAD).fillna("no clasificada")
    df["latitude"] = df["lat"]
    df["longitude"] = df["lon"]
    df["pais_codigo"] = "URY"
    df["pais_nombre"] = "Uruguay"
    df["region"] = None
    df["departamento"] = df["punto"]
    df["record_hash"] = _hash_series(df, ["punto", "anio", "codigo_cobertura"], "modis")
    df["source_file"] = str(path)
    df["batch_id"] = batch_id
    df["raw_payload"] = None
    start_id = _next_id(conn, "staging.stg_modis_cobertura", "stg_cobertura_id")
    df.insert(0, "stg_cobertura_id", range(start_id, start_id + len(df)))
    columns = [
        "stg_cobertura_id", "batch_id", "source_file", "anio", "latitude", "longitude",
        "codigo_cobertura", "tipo_cobertura", "descripcion_cobertura", "combustibilidad",
        "pais_codigo", "pais_nombre", "region", "departamento", "record_hash", "raw_payload",
    ]
    return _load_dataframe(conn, "staging.stg_modis_cobertura", df, columns, chunk_size)


def _load_dataframe(conn, table: str, df: pd.DataFrame, columns: list[str], chunk_size: int) -> int:
    update_columns = [c for c in columns if c not in {columns[0], "record_hash"}]
    loaded = 0
    for start in range(0, len(df), chunk_size):
        chunk = df.iloc[start:start + chunk_size]
        rows = [tuple(_safe(v) for v in row) for row in chunk[columns].itertuples(index=False, name=None)]
        loaded += _insert_values(conn, table, columns, rows, update_columns)
        conn.commit()
        print(f"{table}: {loaded:,}/{len(df):,}")
    return loaded


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga datasets ambientales crudos a staging PostgreSQL.")
    parser.add_argument("--source", choices=["all", "openmeteo", "air", "chirps", "modis"], default="all")
    parser.add_argument("--chunk-size", type=int, default=50_000)
    args = parser.parse_args()

    loaders = {
        "openmeteo": load_openmeteo,
        "air": load_air_quality,
        "chirps": load_chirps,
        "modis": load_modis,
    }
    selected = list(loaders) if args.source == "all" else [args.source]
    batch_id = "staging_ambiental_" + uuid.uuid4().hex[:12]

    with _conn() as conn:
        for source in selected:
            run_id = f"{batch_id}_{source}"
            start = time.perf_counter()
            try:
                print(f"\\n==> cargando {source} batch={batch_id}")
                rows = loaders[source](conn, batch_id, args.chunk_size)
                seconds = time.perf_counter() - start
                _write_audit(conn, run_id, source, rows, "success", seconds)
                conn.commit()
                print(f"OK {source}: {rows:,} filas en {seconds:.1f}s")
            except Exception as exc:
                conn.rollback()
                seconds = time.perf_counter() - start
                _write_audit(conn, run_id, source, 0, "failed", seconds, str(exc))
                conn.commit()
                print(f"ERROR {source}: {type(exc).__name__}: {exc}")
                raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
