from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.settings import SOURCE_FILES


def read_source(source: str, path: str | Path | None = None) -> pd.DataFrame:
    configured = str(path or SOURCE_FILES[source]).strip()
    if not configured:
        raise FileNotFoundError(f"{source}: configure {source}_FILE en config/.env")
    candidate = Path(configured).expanduser()
    if not candidate.exists():
        raise FileNotFoundError(f"{source}: archivo no encontrado: {candidate}")
    if candidate.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(candidate)
    if candidate.suffix.lower() == ".csv":
        return pd.read_csv(candidate)
    raise ValueError(f"{source}: formato soportado: CSV o Parquet")
