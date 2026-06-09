"""Regenera FIRMS 2018-2025 desde shapefile historico y fronteras auxiliares.

La geometria de paises se usa solo como referencia tecnica para clasificar
puntos FIRMS por pais. No agrega una nueva fuente analitica al Proyecto LIDIA.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import geopandas as gpd
import pandas as pd
import shapely

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "evidencia" / "logs"
ALLOWED_COUNTRIES = {"URY", "ARG", "BRA"}
NE_URL = "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_0_countries.zip"


def ensure_boundaries(path: Path) -> Path:
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "ne_10m_admin_0_countries.zip"
        urllib.request.urlretrieve(NE_URL, zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(path.parent)
    if not path.exists():
        raise FileNotFoundError(f"No se pudo obtener frontera auxiliar: {path}")
    return path


def load_country_geometries(boundaries_file: Path) -> dict[str, Any]:
    countries = gpd.read_file(boundaries_file)
    iso_col = next((col for col in ("ISO_A3", "ADM0_A3", "SOV_A3") if col in countries.columns), None)
    if iso_col is None:
        raise ValueError("El archivo de fronteras no tiene columna ISO_A3/ADM0_A3/SOV_A3")
    countries = countries.to_crs("EPSG:4326")
    geometries: dict[str, Any] = {}
    for iso in sorted(ALLOWED_COUNTRIES | {"CHL"}):
        subset = countries[countries[iso_col].astype(str).str.upper().eq(iso)]
        if not subset.empty:
            geometries[iso] = shapely.union_all(subset.geometry.to_numpy())
    missing = sorted(ALLOWED_COUNTRIES - set(geometries))
    if missing:
        raise ValueError(f"Faltan geometrias para paises requeridos: {missing}")
    return geometries


def classify_countries(frame: pd.DataFrame, geometries: dict[str, Any]) -> pd.Series:
    lat = pd.to_numeric(frame["LATITUDE"], errors="coerce")
    lon = pd.to_numeric(frame["LONGITUDE"], errors="coerce")
    country = pd.Series([""] * len(frame), index=frame.index, dtype="object")
    finite = lat.notna() & lon.notna()
    lon_values = lon.to_numpy()
    lat_values = lat.to_numpy()
    for iso, geometry in geometries.items():
        inside = finite & shapely.contains_xy(geometry, lon_values, lat_values)
        country.loc[inside] = iso
    return country


def normalize_firms(frame: pd.DataFrame, countries: pd.Series) -> pd.DataFrame:
    selected = frame.loc[countries.isin(ALLOWED_COUNTRIES)].copy()
    selected["pais_codigo"] = countries.loc[selected.index].values

    output = pd.DataFrame(
        {
            "latitud": pd.to_numeric(selected["LATITUDE"], errors="coerce"),
            "longitud": pd.to_numeric(selected["LONGITUDE"], errors="coerce"),
            "brillo_ti4": pd.to_numeric(selected["BRIGHTNESS"], errors="coerce"),
            "scan": pd.to_numeric(selected["SCAN"], errors="coerce"),
            "track": pd.to_numeric(selected["TRACK"], errors="coerce"),
            "fecha_adq": pd.to_datetime(selected["ACQ_DATE"], errors="coerce").dt.date.astype(str),
            "hora_adq_hhmm": selected["ACQ_TIME"].astype(str).str.zfill(4),
            "satelite": selected["SATELLITE"].astype(str),
            "instrumento": selected["INSTRUMENT"].astype(str),
            "confianza_raw": selected["CONFIDENCE"],
            "version": selected["VERSION"].astype(str),
            "brillo_ti5": pd.to_numeric(selected["BRIGHT_T31"], errors="coerce"),
            "potencia_radiativa": pd.to_numeric(selected["FRP"], errors="coerce"),
            "dia_noche": selected["DAYNIGHT"].astype(str),
            "type": selected["TYPE"],
            "pais": selected["pais_codigo"],
            "pais_codigo": selected["pais_codigo"],
        }
    )
    output["confianza_num"] = pd.to_numeric(output["confianza_raw"], errors="coerce")
    output["hora_adq"] = output["hora_adq_hhmm"]
    output["es_diurno"] = output["dia_noche"].eq("D")
    output = output[
        pd.to_datetime(output["fecha_adq"], errors="coerce", utc=True).between(
            pd.Timestamp("2018-01-01", tz="UTC"),
            pd.Timestamp("2025-12-31 23:59:59", tz="UTC"),
        )
    ].copy()
    output = output.dropna(subset=["fecha_adq", "latitud", "longitud"])
    output = output.drop_duplicates(subset=["fecha_adq", "latitud", "longitud", "hora_adq_hhmm", "satelite"])
    return output


def summarize(output: pd.DataFrame, raw_rows: int, countries: pd.Series, output_file: Path) -> dict[str, Any]:
    dates = pd.to_datetime(output["fecha_adq"], errors="coerce", utc=True)
    return {
        "input_rows": raw_rows,
        "output_file": str(output_file),
        "output_rows": int(len(output)),
        "fecha_min": dates.min().date().isoformat() if dates.notna().any() else None,
        "fecha_max": dates.max().date().isoformat() if dates.notna().any() else None,
        "conteo_por_pais": {str(k): int(v) for k, v in output["pais_codigo"].value_counts().sort_index().to_dict().items()},
        "clasificacion_total": {str(k or "SIN_PAIS"): int(v) for k, v in countries.value_counts().sort_index().to_dict().items()},
        "chl_eliminado": bool((countries == "CHL").any()),
        "brightness_descripcion": "brillo_termico_pixel_satelital_no_temperatura_aire",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara FIRMS historico 2018-2025 desde shapefile.")
    parser.add_argument(
        "--input",
        default="/home/pepo/Datos completos/DL_FIRE_M-C61_740435/fire_archive_M-C61_740435.shp",
        help="Shapefile historico FIRMS.",
    )
    parser.add_argument(
        "--boundaries-file",
        default=str(ROOT / "data" / "reference" / "ne_10m_admin_0_countries.shp"),
        help="Shapefile auxiliar de fronteras de paises.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "processed" / "firms_2018_2025.parquet"),
        help="Parquet final normalizado para ETL.",
    )
    parser.add_argument(
        "--log",
        default=str(LOG_DIR / "preparacion_firms_historico_2018_2025.log"),
        help="Log de evidencia.",
    )
    args = parser.parse_args()

    input_file = Path(args.input)
    if not input_file.exists():
        raise FileNotFoundError(f"No existe shapefile FIRMS historico: {input_file}")
    boundaries_file = ensure_boundaries(Path(args.boundaries_file))
    output_file = Path(args.output)
    log_file = Path(args.log)

    geometries = load_country_geometries(boundaries_file)
    frame = gpd.read_file(input_file)
    countries = classify_countries(frame, geometries)
    output = normalize_firms(frame, countries)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(output_file, index=False)

    result = summarize(output, len(frame), countries, output_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
