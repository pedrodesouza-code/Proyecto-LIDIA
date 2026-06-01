from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from config.settings import SOURCE_FILES


def _max_records() -> int | None:
    value = os.getenv("LIDIA_MAX_RECORDS_PER_SOURCE", "").strip()
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def read_source(source: str, path: str | Path | None = None) -> pd.DataFrame:
    configured = str(path or SOURCE_FILES[source]).strip()
    if not configured:
        raise FileNotFoundError(f"{source}: configure {source}_FILE en config/.env")
    candidate = Path(configured).expanduser()
    if not candidate.exists():
        raise FileNotFoundError(f"{source}: archivo no encontrado: {candidate}")
    max_records = _max_records()
    if candidate.suffix.lower() in {".parquet", ".pq"}:
        frame = pd.read_parquet(candidate)
        return frame.head(max_records) if max_records else frame
    if candidate.suffix.lower() == ".csv":
        return pd.read_csv(candidate, nrows=max_records)
    raise ValueError(f"{source}: formato soportado: CSV o Parquet")
