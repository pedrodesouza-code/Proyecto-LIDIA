"""Completa METEO/Open-Meteo historico 2025 y regenera el parquet 2018-2025."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import PUNTOS_MONITOREO
from etl.extract import extract_meteo
from etl.extract import base as extract_base

ALLOWED_COUNTRIES = {"URY", "ARG", "BRA"}
START = pd.Timestamp("2018-01-01", tz="UTC")
END = pd.Timestamp("2025-12-31 23:59:59", tz="UTC")
LOG_DIR = ROOT / "evidencia" / "logs"
PROCESSED_DIR = ROOT / "data" / "processed"


def normalize_2025(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["fecha_hora_utc"] = pd.to_datetime(output["time"], errors="coerce", utc=True)
    output["fecha"] = output["fecha_hora_utc"].dt.date.astype(str)
    output["pais_codigo"] = output["pais"].astype(str).str.upper()
    output["punto"] = output["ubicacion"].astype(str)
    output["latitud"] = pd.to_numeric(output["lat"], errors="coerce")
    output["longitud"] = pd.to_numeric(output["lon"], errors="coerce")
    output["fuente"] = "METEO"
    output = output[
        output["fecha_hora_utc"].between(pd.Timestamp("2025-01-01", tz="UTC"), END)
        & output["pais_codigo"].isin(ALLOWED_COUNTRIES)
    ].copy()
    return output.drop(columns=[col for col in ("time", "pais", "lat", "lon") if col in output.columns])


def make_dedup_key(frame: pd.DataFrame) -> pd.Series:
    fecha_hora = pd.to_datetime(frame.get("fecha_hora_utc"), errors="coerce", utc=True)
    fecha = pd.to_datetime(frame.get("fecha"), errors="coerce", utc=True)
    temporal = fecha_hora.fillna(fecha)
    ubicacion = frame.get("ubicacion", frame.get("punto", pd.Series([""] * len(frame), index=frame.index)))
    latitud = pd.to_numeric(frame.get("latitud"), errors="coerce").round(5).astype(str)
    longitud = pd.to_numeric(frame.get("longitud"), errors="coerce").round(5).astype(str)
    return (
        frame.get("pais_codigo", pd.Series([""] * len(frame), index=frame.index)).astype(str)
        + "|"
        + ubicacion.astype(str)
        + "|"
        + latitud
        + "|"
        + longitud
        + "|"
        + temporal.dt.strftime("%Y-%m-%dT%H:%M:%SZ").fillna("")
    )


def summarize(frame: pd.DataFrame) -> dict[str, Any]:
    temporal = pd.to_datetime(frame.get("fecha_hora_utc"), errors="coerce", utc=True)
    fecha = pd.to_datetime(frame.get("fecha"), errors="coerce", utc=True)
    dates = temporal.fillna(fecha)
    return {
        "filas": int(len(frame)),
        "fecha_min": dates.min().date().isoformat() if dates.notna().any() else None,
        "fecha_max": dates.max().date().isoformat() if dates.notna().any() else None,
        "paises": {str(k): int(v) for k, v in frame["pais_codigo"].value_counts().sort_index().to_dict().items()}
        if "pais_codigo" in frame.columns
        else {},
        "puntos": sorted(frame["punto"].dropna().astype(str).unique().tolist())
        if "punto" in frame.columns
        else sorted(frame["ubicacion"].dropna().astype(str).unique().tolist())
        if "ubicacion" in frame.columns
        else [],
    }


def sanitize_for_parquet(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    if "fecha" in output.columns:
        fecha = pd.to_datetime(output["fecha"], errors="coerce", utc=True)
        output["fecha"] = fecha.dt.date.astype("string")
    if "fecha_hora_utc" in output.columns:
        output["fecha_hora_utc"] = pd.to_datetime(output["fecha_hora_utc"], errors="coerce", utc=True)
    for column in ("pais_codigo", "ubicacion", "punto", "fuente", "nivel_riesgo"):
        if column in output.columns:
            output[column] = output[column].astype("string")
    for column in (
        "latitud",
        "longitud",
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "wind_direction_10m",
        "rain",
        "surface_pressure",
        "temperature_2m_max",
        "temperature_2m_min",
        "relative_humidity_2m_min",
        "relative_humidity_2m_max",
        "wind_speed_10m_max",
        "wind_direction_10m_dominant",
        "precipitation_sum",
        "et0_fao_evapotranspiration",
        "riesgo_temp",
        "riesgo_humedad",
        "riesgo_viento",
        "riesgo_sequia",
        "indice_riesgo",
    ):
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara METEO/Open-Meteo 2025.")
    parser.add_argument("--start-date", default="2025-01-01")
    parser.add_argument("--end-date", default="2025-12-31")
    parser.add_argument("--sleep-seconds", default=os.getenv("METEO_API_SLEEP_SECONDS", "0"))
    parser.add_argument("--output-2025", default=str(PROCESSED_DIR / "meteo_2025.parquet"))
    parser.add_argument("--history", default=str(PROCESSED_DIR / "meteo_2018_2025.parquet"))
    parser.add_argument("--fallback-history", default=str(PROCESSED_DIR / "meteo_procesado_todos.parquet"))
    parser.add_argument("--log", default=str(LOG_DIR / "preparacion_meteo_2025.log"))
    args = parser.parse_args()

    os.environ["METEO_API_ENABLED"] = "true"
    os.environ["METEO_FILE"] = ""
    os.environ["METEO_START_DATE"] = args.start_date
    os.environ["METEO_END_DATE"] = args.end_date
    os.environ["METEO_API_SLEEP_SECONDS"] = str(args.sleep_seconds)
    os.environ.pop("LIDIA_MAX_RECORDS_PER_SOURCE", None)
    extract_base.SOURCE_FILES["METEO"] = ""

    log: dict[str, Any] = {
        "fuente": "Open-Meteo historico",
        "etiqueta_tecnica": "METEO",
        "periodo_incremental": {"desde": args.start_date, "hasta": args.end_date},
        "puntos_configurados": len(PUNTOS_MONITOREO),
        "variables": extract_meteo.HOURLY_VARIABLES,
        "errores_api": [],
    }

    output_2025 = Path(args.output_2025)
    if output_2025.exists():
        meteo_2025 = pd.read_parquet(output_2025)
        raw_2025 = meteo_2025
        log["particion_2025_reutilizada"] = True
    else:
        try:
            raw_2025 = extract_meteo.extract(path="")
        except Exception as exc:
            log["estado"] = "error_api"
            log["errores_api"].append(f"{type(exc).__name__}: {exc}")
            Path(args.log).parent.mkdir(parents=True, exist_ok=True)
            Path(args.log).write_text(json.dumps(log, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
            print(json.dumps(log, ensure_ascii=False, indent=2, default=str))
            return 1
        meteo_2025 = normalize_2025(raw_2025)
        output_2025.parent.mkdir(parents=True, exist_ok=True)
        sanitize_for_parquet(meteo_2025).to_parquet(output_2025, index=False)
        log["particion_2025_reutilizada"] = False

    history_path = Path(args.history)
    fallback_history = Path(args.fallback_history)
    source_history = history_path if history_path.exists() else fallback_history
    if not source_history.exists():
        raise FileNotFoundError(f"No existe historico METEO: {source_history}")

    history = pd.read_parquet(source_history)
    if "pais_codigo" not in history.columns and "pais" in history.columns:
        history["pais_codigo"] = history["pais"].astype(str).str.upper()
    if "punto" not in history.columns and "ubicacion" in history.columns:
        history["punto"] = history["ubicacion"]
    if "ubicacion" not in history.columns and "punto" in history.columns:
        history["ubicacion"] = history["punto"]
    if "fuente" not in history.columns:
        history["fuente"] = "METEO"

    combined = pd.concat([history, meteo_2025], ignore_index=True, sort=False)
    temporal = pd.to_datetime(combined.get("fecha_hora_utc"), errors="coerce", utc=True)
    fecha = pd.to_datetime(combined.get("fecha"), errors="coerce", utc=True)
    dates = temporal.fillna(fecha)
    combined = combined[
        dates.between(START, END)
        & combined["pais_codigo"].astype(str).str.upper().isin(ALLOWED_COUNTRIES)
    ].copy()
    before_dedup = len(combined)
    combined["_dedup_key"] = make_dedup_key(combined)
    combined = combined.drop_duplicates(subset=["_dedup_key"], keep="last").drop(columns=["_dedup_key"])

    backup = history_path.with_name("meteo_2018_2025_before_2025_complement.parquet")
    if history_path.exists() and not backup.exists():
        pd.read_parquet(history_path).to_parquet(backup, index=False)
    combined = sanitize_for_parquet(combined)
    combined.to_parquet(history_path, index=False)

    log.update(
        {
            "estado": "ok",
            "archivo_2025": str(output_2025),
            "archivo_final": str(history_path),
            "historico_usado": str(source_history),
            "backup": str(backup) if backup.exists() else None,
            "filas_2025_raw": int(len(raw_2025)),
            "filas_2025_utiles": int(len(meteo_2025)),
            "filas_finales": int(len(combined)),
            "duplicados_eliminados": int(before_dedup - len(combined)),
            "resumen_2025": summarize(meteo_2025),
            "resumen_final": summarize(combined),
        }
    )
    Path(args.log).parent.mkdir(parents=True, exist_ok=True)
    Path(args.log).write_text(json.dumps(log, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(log, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
