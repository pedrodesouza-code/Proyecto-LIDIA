"""Integra un complemento FIRMS real 2025 al parquet principal 2018-2025."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.preparar_firms_historico_desde_shapefile import (
    ALLOWED_COUNTRIES,
    classify_countries,
    load_country_geometries,
    normalize_firms,
)

LOG_DIR = ROOT / "evidencia" / "logs"
DEFAULT_COMPLEMENT = ROOT / "data" / "raw" / "firms" / "firms_2025_complemento.csv"
DEFAULT_HISTORY = ROOT / "data" / "processed" / "firms_2018_2025.parquet"
DEFAULT_BOUNDARIES = ROOT / "data" / "reference" / "ne_10m_admin_0_countries.shp"


def find_complement() -> Path:
    if DEFAULT_COMPLEMENT.exists():
        return DEFAULT_COMPLEMENT
    raw_dir = ROOT / "data" / "raw" / "firms"
    candidates: list[Path] = []
    for suffix in ("*.csv", "*.parquet", "*.shp", "*.zip"):
        candidates.extend(raw_dir.rglob(suffix))
    filtered = [
        path
        for path in candidates
        if any(token in path.name.lower() for token in ("firms", "fire", "760803", "2025"))
        and "nrt" not in path.name.lower()
    ]
    shp = [path for path in filtered if path.suffix.lower() == ".shp"]
    return sorted(shp or filtered, key=lambda p: str(p))[-1]


def read_complement(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".shp":
        return gpd.read_file(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Formato no soportado para integracion directa: {path}")


def upper_firms_columns(frame: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "latitude": "LATITUDE",
        "latitud": "LATITUDE",
        "longitude": "LONGITUDE",
        "longitud": "LONGITUDE",
        "brightness": "BRIGHTNESS",
        "brillo_ti4": "BRIGHTNESS",
        "bright_ti4": "BRIGHTNESS",
        "scan": "SCAN",
        "track": "TRACK",
        "acq_date": "ACQ_DATE",
        "fecha_adq": "ACQ_DATE",
        "date": "ACQ_DATE",
        "acq_time": "ACQ_TIME",
        "hora_adq_hhmm": "ACQ_TIME",
        "satellite": "SATELLITE",
        "satelite": "SATELLITE",
        "instrument": "INSTRUMENT",
        "instrumento": "INSTRUMENT",
        "confidence": "CONFIDENCE",
        "confianza_raw": "CONFIDENCE",
        "confianza_num": "CONFIDENCE",
        "version": "VERSION",
        "bright_t31": "BRIGHT_T31",
        "brillo_ti5": "BRIGHT_T31",
        "frp": "FRP",
        "potencia_radiativa": "FRP",
        "daynight": "DAYNIGHT",
        "dia_noche": "DAYNIGHT",
        "type": "TYPE",
    }
    renamed = {column: mapping[column.lower()] for column in frame.columns if column.lower() in mapping}
    output = frame.rename(columns=renamed).copy()
    for column in ["SCAN", "TRACK", "VERSION", "TYPE"]:
        if column not in output.columns:
            output[column] = None
    return output


def audit_raw(path: Path, frame: pd.DataFrame, countries: pd.Series | None) -> dict[str, Any]:
    date_col = next((col for col in ("ACQ_DATE", "fecha_adq", "acq_date", "fecha", "date") if col in frame.columns), None)
    dates = pd.to_datetime(frame[date_col], errors="coerce") if date_col else pd.Series([], dtype="datetime64[ns]")
    fields = [
        "BRIGHTNESS",
        "bright_ti4",
        "brillo_ti4",
        "FRP",
        "frp",
        "CONFIDENCE",
        "SATELLITE",
        "INSTRUMENT",
        "ACQ_DATE",
        "ACQ_TIME",
        "LATITUDE",
        "LONGITUDE",
        "DAYNIGHT",
    ]
    profile = {
        "ruta": str(path),
        "formato": path.suffix.lower().lstrip("."),
        "filas": int(len(frame)),
        "columnas": list(map(str, frame.columns)),
        "columna_temporal_detectada": date_col,
        "fecha_min": dates.min().date().isoformat() if len(dates) and dates.notna().any() else None,
        "fecha_max": dates.max().date().isoformat() if len(dates) and dates.notna().any() else None,
        "coordenadas": {"latitud": "LATITUDE" in frame.columns, "longitud": "LONGITUDE" in frame.columns},
        "columnas_firms_disponibles": [field for field in fields if field in frame.columns],
        "brightness_descripcion": "brillo_termico_pixel_satelital_no_temperatura_aire",
    }
    country_col = next((col for col in ("pais_codigo", "pais", "country") if col in frame.columns), None)
    if country_col:
        profile["columna_pais"] = country_col
        profile["conteo_por_pais_original"] = {
            str(k).upper(): int(v) for k, v in frame[country_col].astype(str).str.upper().value_counts().sort_index().to_dict().items()
        }
    if countries is not None:
        profile["conteo_por_pais_clasificado"] = {
            str(k or "SIN_PAIS"): int(v) for k, v in countries.value_counts().sort_index().to_dict().items()
        }
    return profile


def natural_key_frame(frame: pd.DataFrame) -> pd.Series:
    parts = [
        frame["fecha_adq"].astype(str),
        frame["latitud"].round(5).astype(str),
        frame["longitud"].round(5).astype(str),
        frame["hora_adq_hhmm"].astype(str),
        frame["satelite"].astype(str),
        frame["instrumento"].astype(str),
        frame["brillo_ti4"].round(3).astype(str),
        frame["potencia_radiativa"].round(3).astype(str),
    ]
    key = parts[0]
    for part in parts[1:]:
        key = key + "|" + part
    return key


def main() -> int:
    parser = argparse.ArgumentParser(description="Integra complemento FIRMS 2025 real.")
    parser.add_argument("--input", default="", help="Archivo complemento FIRMS 2025.")
    parser.add_argument("--history", default=str(DEFAULT_HISTORY))
    parser.add_argument("--boundaries-file", default=str(DEFAULT_BOUNDARIES))
    parser.add_argument("--audit-log", default=str(LOG_DIR / "firms_2025_complemento_auditoria.log"))
    parser.add_argument("--integration-log", default=str(LOG_DIR / "firms_2025_complemento_integracion.log"))
    args = parser.parse_args()

    complement = Path(args.input) if args.input else find_complement()
    history_file = Path(args.history)
    boundaries_file = Path(args.boundaries_file)
    if not complement.exists():
        raise FileNotFoundError(f"No existe complemento FIRMS: {complement}")
    if not history_file.exists():
        raise FileNotFoundError(f"No existe historico FIRMS: {history_file}")

    raw = upper_firms_columns(read_complement(complement))
    geometries = load_country_geometries(boundaries_file)
    countries = classify_countries(raw, geometries)
    audit = audit_raw(complement, raw, countries)
    Path(args.audit_log).parent.mkdir(parents=True, exist_ok=True)
    Path(args.audit_log).write_text(json.dumps(audit, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

    normalized = normalize_firms(raw, countries)
    dates = pd.to_datetime(normalized["fecha_adq"], errors="coerce", utc=True)
    useful = normalized[
        dates.between(pd.Timestamp("2025-01-02", tz="UTC"), pd.Timestamp("2025-12-31 23:59:59", tz="UTC"))
        & normalized["pais_codigo"].isin(ALLOWED_COUNTRIES)
    ].copy()

    history = pd.read_parquet(history_file)
    before_rows = len(history)
    complement_rows = len(raw)
    useful_rows = len(useful)
    history_keys = natural_key_frame(history)
    useful_keys = natural_key_frame(useful)
    before_concat = len(history) + len(useful)
    combined = pd.concat([history.assign(_natural_key_tmp=history_keys), useful.assign(_natural_key_tmp=useful_keys)], ignore_index=True)
    combined = combined.drop_duplicates(subset=["_natural_key_tmp"], keep="first").drop(columns=["_natural_key_tmp"])

    backup_file = history_file.with_name("firms_2018_2025_before_2025_complement.parquet")
    if not backup_file.exists():
        history.to_parquet(backup_file, index=False)
    combined.to_parquet(history_file, index=False)

    final_dates = pd.to_datetime(combined["fecha_adq"], errors="coerce", utc=True)
    result = {
        "historico_inicial_filas": int(before_rows),
        "complemento_original_filas": int(complement_rows),
        "complemento_util_filas": int(useful_rows),
        "filas_antes_de_deduplicar": int(before_concat),
        "filas_finales": int(len(combined)),
        "duplicados_eliminados": int(before_concat - len(combined)),
        "fecha_min_final": final_dates.min().date().isoformat() if final_dates.notna().any() else None,
        "fecha_max_final": final_dates.max().date().isoformat() if final_dates.notna().any() else None,
        "conteo_por_pais_final": {
            str(k): int(v) for k, v in combined["pais_codigo"].value_counts().sort_index().to_dict().items()
        },
        "conteo_por_pais_complemento_util": {
            str(k): int(v) for k, v in useful["pais_codigo"].value_counts().sort_index().to_dict().items()
        },
        "chl_final": int((combined["pais_codigo"].astype(str).str.upper() == "CHL").sum()),
        "archivo_final": str(history_file),
        "backup": str(backup_file),
        "brightness_descripcion": "brillo_termico_pixel_satelital_no_temperatura_aire",
    }
    Path(args.integration_log).write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
