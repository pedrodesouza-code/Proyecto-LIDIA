"""Extraccion meteorologica historica real mediante API."""

from __future__ import annotations

import pandas as pd
import requests

from config.settings import METEO_API_URL, METEO_END_DATE, METEO_START_DATE, PUNTOS_MONITOREO

HOURLY = (
    "temperature_2m,relative_humidity_2m,wind_speed_10m,"
    "wind_direction_10m,rain,surface_pressure"
)


def _extract_point(name: str, point: dict) -> pd.DataFrame:
    response = requests.get(
        METEO_API_URL,
        params={
            "latitude": point["lat"], "longitude": point["lon"],
            "start_date": METEO_START_DATE, "end_date": METEO_END_DATE,
            "timezone": "UTC", "hourly": HOURLY,
        },
        timeout=180,
    )
    response.raise_for_status()
    hourly = response.json().get("hourly")
    if not hourly or not hourly.get("time"):
        raise RuntimeError(f"METEO: API sin datos horarios para {name}")
    frame = pd.DataFrame(hourly)
    frame["ubicacion"], frame["pais"] = name, point["pais"]
    frame["lat"], frame["lon"] = point["lat"], point["lon"]
    return frame


def extract_batches():
    """Entrega un punto por lote para mantener acotada la memoria de carga."""
    for name, point in PUNTOS_MONITOREO.items():
        yield _extract_point(name, point)


def extract(path=None) -> pd.DataFrame:
    """Obtiene historia horaria 2018-2025 para los puntos EC3 configurados."""
    return pd.concat(
        list(extract_batches()),
        ignore_index=True,
    )
