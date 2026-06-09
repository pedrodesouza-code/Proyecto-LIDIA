"""Audita Parquet de Proyecto LIDIA contra alcance EC3 2018-2025."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.preparar_datasets_2018_2025 import (
    ALLOWED_COUNTRIES,
    DATA_DIR,
    END,
    LOG_DIR,
    START,
    date_series,
    infer_country_frame,
)

DATE_CANDIDATES = ["fecha_adq", "acq_date", "fecha", "date", "time", "datetime", "fecha_hora", "fecha_hora_utc", "anio", "year"]


def audit_file(path: Path) -> dict[str, Any]:
    item: dict[str, Any] = {
        "archivo": str(path),
        "nombre": path.name,
        "size_bytes": path.stat().st_size,
    }
    try:
        frame = pd.read_parquet(path)
    except Exception as exc:
        item["error"] = f"{type(exc).__name__}: {exc}"
        return item
    item["filas"] = int(len(frame))
    item["columnas"] = list(map(str, frame.columns))
    date_column, parsed = date_series(frame, DATE_CANDIDATES)
    item["columna_temporal_detectada"] = date_column
    if parsed is not None:
        valid = parsed.dropna()
        item["nulos_temporales"] = int(parsed.isna().sum())
        if not valid.empty:
            item["fecha_min"] = valid.min().date().isoformat()
            item["fecha_max"] = valid.max().date().isoformat()
            item["fuera_2018_2025"] = bool((valid < START).any() or (valid > END).any())
            item["filas_fuera_2018_2025"] = int(((parsed < START) | (parsed > END)).sum())
        else:
            item["fuera_2018_2025"] = True
            item["filas_fuera_2018_2025"] = int(len(frame))
    else:
        item["fuera_2018_2025"] = None
        item["filas_fuera_2018_2025"] = None

    countries = infer_country_frame(frame)
    if len(countries):
        counts = countries.value_counts(dropna=False).to_dict()
        item["paises_detectados"] = {str(k): int(v) for k, v in counts.items()}
        outside = sorted({str(value) for value in countries.unique() if str(value) and str(value) not in ALLOWED_COUNTRIES})
        item["paises_fuera_alcance"] = outside
        item["contiene_paises_fuera_alcance"] = bool(outside)
    else:
        item["paises_detectados"] = {}
        item["paises_fuera_alcance"] = []
        item["contiene_paises_fuera_alcance"] = False
    item["es_nrt"] = "nrt" in path.name.lower()
    item["principal_recomendado"] = not item["es_nrt"] and path.name.endswith("_2018_2025.parquet")
    return item


def write_report(items: list[dict[str, Any]], path: Path) -> None:
    lines = ["# Auditoria Parquet 2018-2025", ""]
    lines.append("| archivo | filas | fecha min | fecha max | fuera 2018-2025 | paises fuera alcance | NRT |")
    lines.append("|---|---:|---|---|---|---|---|")
    for item in items:
        outside = ", ".join(item.get("paises_fuera_alcance", [])) or "-"
        lines.append(
            "| {name} | {rows} | {min_date} | {max_date} | {outside_period} | {outside_countries} | {nrt} |".format(
                name=item.get("nombre", "-"),
                rows=item.get("filas", "ERROR"),
                min_date=item.get("fecha_min", "-"),
                max_date=item.get("fecha_max", "-"),
                outside_period=item.get("fuera_2018_2025", "-"),
                outside_countries=outside,
                nrt=item.get("es_nrt", "-"),
            )
        )
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(items, ensure_ascii=False, indent=2, default=str))
    lines.append("```")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita Parquet procesados de Proyecto LIDIA.")
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--log", default=str(LOG_DIR / "auditoria_parquets_2018_2025.log"))
    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    files = sorted(data_dir.glob("*.parquet"))
    items = [audit_file(path) for path in files]
    write_report(items, Path(args.log))
    print(json.dumps(items, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
