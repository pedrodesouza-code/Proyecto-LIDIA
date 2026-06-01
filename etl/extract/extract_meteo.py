"""Extractor de Open-Meteo historico para variables meteorologicas."""

from __future__ import annotations

import os
import time
from typing import Any

import pandas as pd
import requests

from config.settings import METEO_API_URL, METEO_END_DATE, METEO_START_DATE, PUNTOS_MONITOREO
from .base import read_source


HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "rain",
    "surface_pressure",
]


def _api_enabled() -> bool:
    return os.getenv("METEO_API_ENABLED", "false").strip().lower() in {"1", "true", "yes"}


def _max_records() -> int | None:
    value = os.getenv("LIDIA_MAX_RECORDS_PER_SOURCE", "").strip()
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _selected_points() -> dict[str, dict[str, Any]]:
    raw = os.getenv("METEO_POINTS", "").strip()
    if not raw:
        return PUNTOS_MONITOREO
    wanted = {item.strip() for item in raw.split(",") if item.strip()}
    return {name: spec for name, spec in PUNTOS_MONITOREO.items() if name in wanted}


def _parse_hourly(response: dict[str, Any], name: str, spec: dict[str, Any]) -> pd.DataFrame:
    hourly = response.get("hourly") or {}
    dates = pd.to_datetime(hourly.get("time", []), errors="coerce", utc=True)
    return pd.DataFrame(
        {
            "time": dates,
            "pais": spec["pais"],
            "ubicacion": spec.get("ubicacion", name),
            "lat": spec["lat"],
            "lon": spec["lon"],
            "temperature_2m": hourly.get("temperature_2m", []),
            "relative_humidity_2m": hourly.get("relative_humidity_2m", []),
            "wind_speed_10m": hourly.get("wind_speed_10m", []),
            "wind_direction_10m": hourly.get("wind_direction_10m", []),
            "rain": hourly.get("rain", []),
            "surface_pressure": hourly.get("surface_pressure", []),
        }
    )


def _extract_api() -> pd.DataFrame:
    start_date = os.getenv("METEO_START_DATE", METEO_START_DATE)
    end_date = os.getenv("METEO_END_DATE", METEO_END_DATE)
    sleep_seconds = float(os.getenv("METEO_API_SLEEP_SECONDS", "0"))
    max_records = _max_records()
    frames: list[pd.DataFrame] = []
    for name, spec in _selected_points().items():
        params = {
            "latitude": spec["lat"],
            "longitude": spec["lon"],
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(HOURLY_VARIABLES),
            "timezone": "UTC",
        }
        response = requests.get(METEO_API_URL, params=params, timeout=90)
        response.raise_for_status()
        frames.append(_parse_hourly(response.json(), name, spec))
        if max_records and sum(len(frame) for frame in frames) >= max_records:
            break
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    if not frames:
        return pd.DataFrame()
    frame = pd.concat(frames, ignore_index=True)
    return frame.head(max_records) if max_records else frame


def extract(path=None):
    try:
        return read_source("METEO", path)
    except FileNotFoundError:
        if _api_enabled():
            return _extract_api()
        raise
