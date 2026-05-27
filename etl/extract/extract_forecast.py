"""Extraccion real de pronostico meteorologico mediante API."""

from __future__ import annotations

import pandas as pd
import requests

from config.settings import FORECAST_API_URL, FORECAST_DAYS, PUNTOS_MONITOREO
from etl.extract.extract_meteo import HOURLY


def _extract_point(name: str, point: dict) -> pd.DataFrame:
    response = requests.get(
        FORECAST_API_URL,
        params={
            "latitude": point["lat"], "longitude": point["lon"],
            "forecast_days": FORECAST_DAYS, "timezone": "UTC", "hourly": HOURLY,
        },
        timeout=60,
    )
    response.raise_for_status()
    hourly = response.json().get("hourly")
    if not hourly or not hourly.get("time"):
        raise RuntimeError(f"FORECAST: API sin datos horarios para {name}")
    frame = pd.DataFrame(hourly)
    frame["ubicacion"], frame["pais"] = name, point["pais"]
    frame["lat"], frame["lon"] = point["lat"], point["lon"]
    return frame


def extract(path=None) -> pd.DataFrame:
    """Obtiene pronostico operativo actual, siempre identificado como FORECAST."""
    return pd.concat(
        [_extract_point(name, point) for name, point in PUNTOS_MONITOREO.items()],
        ignore_index=True,
    )
