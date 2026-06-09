"""Completa CHIRPS 2025 desde GeoTIFF mensuales oficiales y regenera 2018-2025."""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import rasterio
import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etl.transform.normalize import LOCATION_COORDS

ALLOWED_COUNTRIES = {"URY", "ARG", "BRA"}
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw" / "chirps" / "2025"
LOG_DIR = ROOT / "evidencia" / "logs"
BASE_URL = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs"


def point_key(value: object) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def download_month(month: int, raw_dir: Path) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    gz_path = raw_dir / f"chirps-v2.0.2025.{month:02d}.tif.gz"
    tif_path = raw_dir / f"chirps-v2.0.2025.{month:02d}.tif"
    if tif_path.exists():
        return tif_path
    if not gz_path.exists():
        url = f"{BASE_URL}/{gz_path.name}"
        with requests.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()
            with gz_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
    with gzip.open(gz_path, "rb") as source, tif_path.open("wb") as target:
        shutil.copyfileobj(source, target)
    return tif_path


def load_points(history: pd.DataFrame) -> pd.DataFrame:
    points = history[["punto", "pais_codigo"]].drop_duplicates().copy()
    rows = []
    missing = []
    for row in points.to_dict(orient="records"):
        key = point_key(row["punto"])
        coords = LOCATION_COORDS.get(key)
        if coords is None:
            missing.append(row)
            continue
        rows.append(
            {
                "punto": row["punto"],
                "pais_codigo": row["pais_codigo"],
                "latitud": coords[0],
                "longitud": coords[1],
            }
        )
    return pd.DataFrame(rows), missing


def sample_month(tif_path: Path, points: pd.DataFrame, month: int) -> pd.DataFrame:
    rows = []
    with rasterio.open(tif_path) as dataset:
        coords = [(row["longitud"], row["latitud"]) for row in points.to_dict(orient="records")]
        values = list(dataset.sample(coords))
        nodata = dataset.nodata
    for point, value in zip(points.to_dict(orient="records"), values):
        precip = float(value[0]) if len(value) else None
        if nodata is not None and precip == nodata:
            precip = None
        if precip is not None and precip < 0:
            precip = None
        rows.append(
            {
                "punto": point["punto"],
                "pais": point["pais_codigo"],
                "pais_codigo": point["pais_codigo"],
                "fecha": f"2025-{month:02d}-01",
                "precipitacion_mm": precip,
                "fuente": "CHIRPS",
                "latitud": point["latitud"],
                "longitud": point["longitud"],
            }
        )
    return pd.DataFrame(rows)


def add_derived_columns(frame: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["fecha"] = pd.to_datetime(output["fecha"], errors="coerce")
    output["anio"] = output["fecha"].dt.year
    output["mes"] = output["fecha"].dt.month
    output["anio_mes"] = output["fecha"].dt.strftime("%Y-%m")
    base = baseline.copy()
    base["fecha"] = pd.to_datetime(base["fecha"], errors="coerce")
    base["mes"] = base["fecha"].dt.month
    means = base.groupby(["punto", "pais_codigo", "mes"], dropna=False)["precipitacion_mm"].mean().rename("media_historica")
    output = output.join(means, on=["punto", "pais_codigo", "mes"])
    output["precipitacion_anomalia_pct"] = (
        (output["precipitacion_mm"] - output["media_historica"]) / output["media_historica"]
    ).where(output["media_historica"].ne(0))
    output["deficit_hidrico"] = output["precipitacion_mm"] < output["media_historica"]
    output = output.drop(columns=["media_historica"])
    return output


def summarize(frame: pd.DataFrame) -> dict[str, Any]:
    dates = pd.to_datetime(frame["fecha"], errors="coerce")
    return {
        "filas": int(len(frame)),
        "fecha_min": dates.min().date().isoformat() if dates.notna().any() else None,
        "fecha_max": dates.max().date().isoformat() if dates.notna().any() else None,
        "paises": {str(k): int(v) for k, v in frame["pais_codigo"].value_counts().sort_index().to_dict().items()},
        "puntos": sorted(frame["punto"].dropna().astype(str).unique().tolist()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara CHIRPS 2025 y consolida 2018-2025.")
    parser.add_argument("--history", default=str(PROCESSED_DIR / "chirps_2018_2025.parquet"))
    parser.add_argument("--source-history", default=str(PROCESSED_DIR / "chirps_sa.parquet"))
    parser.add_argument("--output-2025", default=str(PROCESSED_DIR / "chirps_2025.parquet"))
    parser.add_argument("--output", default=str(PROCESSED_DIR / "chirps_2018_2025.parquet"))
    parser.add_argument("--log", default=str(LOG_DIR / "preparacion_chirps_2025.log"))
    args = parser.parse_args()

    history_path = Path(args.history)
    source_history = history_path if history_path.exists() else Path(args.source_history)
    if not source_history.exists():
        raise FileNotFoundError(f"No existe historico CHIRPS: {source_history}")
    history = pd.read_parquet(source_history)
    if "pais_codigo" not in history.columns:
        history["pais_codigo"] = history["pais"].astype(str).str.upper()
    history = history[history["pais_codigo"].isin(ALLOWED_COUNTRIES)].copy()

    points, missing_points = load_points(history)
    monthly_frames = []
    downloads = []
    errors = []
    for month in range(1, 13):
        try:
            tif_path = download_month(month, RAW_DIR)
            downloads.append(str(tif_path))
            monthly_frames.append(sample_month(tif_path, points, month))
        except Exception as exc:
            errors.append({"mes": month, "error": f"{type(exc).__name__}: {exc}"})

    if errors:
        status = "error_descarga_o_muestreo"
        chirps_2025 = pd.DataFrame()
    else:
        chirps_2025 = pd.concat(monthly_frames, ignore_index=True)
        chirps_2025 = chirps_2025.dropna(subset=["precipitacion_mm"])
        chirps_2025 = add_derived_columns(chirps_2025, history)

    output_2025 = Path(args.output_2025)
    output_2025.parent.mkdir(parents=True, exist_ok=True)
    if len(chirps_2025):
        chirps_2025.to_parquet(output_2025, index=False)

    before_rows = len(history)
    combined = pd.concat([history, chirps_2025], ignore_index=True, sort=False)
    combined["fecha"] = pd.to_datetime(combined["fecha"], errors="coerce")
    combined["pais_codigo"] = combined["pais_codigo"].astype(str).str.upper()
    combined = combined[
        combined["fecha"].between(pd.Timestamp("2018-01-01"), pd.Timestamp("2025-12-31"))
        & combined["pais_codigo"].isin(ALLOWED_COUNTRIES)
    ].copy()
    before_dedup = len(combined)
    combined = combined.drop_duplicates(subset=["fecha", "pais_codigo", "punto"], keep="last")
    output = Path(args.output)
    backup = output.with_name("chirps_2018_2025_before_2025_complement.parquet")
    if output.exists() and not backup.exists():
        pd.read_parquet(output).to_parquet(backup, index=False)
    combined.to_parquet(output, index=False)

    result = {
        "estado": "ok" if not errors else status,
        "fuente": "CHIRPS",
        "servidor": BASE_URL,
        "descargas": downloads,
        "errores": errors,
        "netcdf_locales": "Los .nc locales en /home/pepo/Datos completos/chirps_daily son HTML 404 y no se usaron.",
        "puntos_procesados": int(len(points)),
        "puntos_sin_coordenadas": missing_points,
        "filas_historico_inicial": int(before_rows),
        "filas_2025": int(len(chirps_2025)),
        "filas_finales": int(len(combined)),
        "duplicados_eliminados": int(before_dedup - len(combined)),
        "archivo_2025": str(output_2025) if len(chirps_2025) else None,
        "archivo_final": str(output),
        "resumen_2025": summarize(chirps_2025) if len(chirps_2025) else {},
        "resumen_final": summarize(combined),
        "chl_final": int((combined["pais_codigo"] == "CHL").sum()),
        "nota": "No se inventan valores; se muestrean GeoTIFF mensuales oficiales CHIRPS para los puntos ya usados por el proyecto.",
    }
    log = Path(args.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
