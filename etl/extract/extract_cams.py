"""Extractor para calidad del aire CAMS/Open-Meteo Air Quality.

Prioriza un archivo validado (`CAMS_FILE`/`AIR_QUALITY_FILE`). Si no existe y
`CAMS_API_ENABLED=true`, descarga PM2.5/PM10 desde Open-Meteo Air Quality para
puntos regionales controlados de Uruguay, Argentina y Brasil.
"""

from __future__ import annotations

import os
import time
from typing import Any

import pandas as pd
import requests

from config.settings import CAMS_AIR_QUALITY_API_URL
from etl.extract.base import read_source

POINTS = {
    # Uruguay: capitales departamentales aproximadas.
    "UY_Montevideo": ("URY", "Montevideo", -34.90, -56.16),
    "UY_Canelones": ("URY", "Canelones", -34.52, -56.28),
    "UY_Maldonado": ("URY", "Maldonado", -34.90, -54.95),
    "UY_Rocha": ("URY", "Rocha", -34.48, -54.33),
    "UY_Treinta_y_Tres": ("URY", "Treinta_y_Tres", -33.23, -54.38),
    "UY_Cerro_Largo": ("URY", "Cerro_Largo", -32.37, -54.17),
    "UY_Rivera": ("URY", "Rivera", -30.90, -55.55),
    "UY_Artigas": ("URY", "Artigas", -30.40, -56.47),
    "UY_Salto": ("URY", "Salto", -31.38, -57.97),
    "UY_Paysandu": ("URY", "Paysandu", -32.32, -58.08),
    "UY_Rio_Negro": ("URY", "Rio_Negro", -33.12, -58.31),
    "UY_Soriano": ("URY", "Soriano", -33.25, -58.03),
    "UY_Colonia": ("URY", "Colonia", -34.47, -57.84),
    "UY_San_Jose": ("URY", "San_Jose", -34.34, -56.71),
    "UY_Flores": ("URY", "Flores", -33.54, -56.89),
    "UY_Florida": ("URY", "Florida", -34.10, -56.21),
    "UY_Durazno": ("URY", "Durazno", -33.41, -56.50),
    "UY_Lavalleja": ("URY", "Lavalleja", -34.37, -55.23),
    "UY_Tacuarembo": ("URY", "Tacuarembo", -31.73, -55.98),
    # Argentina: norte y litoral de interes para el alcance EC3.
    "AR_Misiones": ("ARG", "Misiones", -27.37, -55.90),
    "AR_Corrientes": ("ARG", "Corrientes", -27.48, -58.83),
    "AR_Chaco": ("ARG", "Chaco", -27.45, -58.98),
    "AR_Formosa": ("ARG", "Formosa", -26.18, -58.18),
    "AR_Santiago_del_Estero": ("ARG", "Santiago_del_Estero", -27.78, -64.26),
    "AR_Salta": ("ARG", "Salta", -24.79, -65.41),
    # Brasil: sur y frontera regional.
    "BR_Rio_Grande_do_Sul": ("BRA", "Rio_Grande_do_Sul", -30.03, -51.23),
    "BR_Santa_Catarina": ("BRA", "Santa_Catarina", -27.59, -48.55),
    "BR_Parana": ("BRA", "Parana", -25.42, -49.27),
    "BR_Uruguaiana": ("BRA", "Uruguaiana", -29.76, -57.09),
    "BR_Pelotas": ("BRA", "Pelotas", -31.77, -52.34),
    "BR_Caxias_do_Sul": ("BRA", "Caxias_do_Sul", -29.17, -51.18),
}


def _api_enabled() -> bool:
    return os.getenv("CAMS_API_ENABLED", "false").strip().lower() in {"1", "true", "yes"}


def _max_records() -> int | None:
    value = os.getenv("LIDIA_MAX_RECORDS_PER_SOURCE", "").strip()
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _parse_hourly(response: dict[str, Any], point_key: str, country: str, location: str, lat: float, lon: float) -> pd.DataFrame:
    hourly = response.get("hourly") or {}
    dates = pd.to_datetime(hourly.get("time", []), errors="coerce", utc=True)
    frame = pd.DataFrame(
        {
            "location": point_key,
            "ubicacion": location,
            "pais_codigo": country,
            "latitud": lat,
            "longitud": lon,
            "fecha_hora_utc": dates,
            "pm10": hourly.get("pm10", []),
            "pm2_5": hourly.get("pm2_5", []),
            "fuente": "CAMS",
        }
    )
    return frame.dropna(subset=["pm10", "pm2_5"], how="all")


def _extract_api() -> pd.DataFrame:
    start_date = os.getenv("CAMS_START_DATE", "2025-01-01")
    end_date = os.getenv("CAMS_END_DATE", "2025-01-07")
    sleep_seconds = float(os.getenv("CAMS_API_SLEEP_SECONDS", "0"))
    max_records = _max_records()
    frames: list[pd.DataFrame] = []
    for point_key, (country, location, lat, lon) in POINTS.items():
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "pm10,pm2_5",
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "UTC",
        }
        response = requests.get(CAMS_AIR_QUALITY_API_URL, params=params, timeout=60)
        response.raise_for_status()
        frames.append(_parse_hourly(response.json(), point_key, country, location, lat, lon))
        if max_records and sum(len(frame) for frame in frames) >= max_records:
            break
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    if not frames:
        return _empty_frame()
    frame = pd.concat(frames, ignore_index=True)
    return frame.head(max_records) if max_records else frame


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "location", "ubicacion", "pais_codigo", "latitud", "longitud",
            "fecha_hora_utc", "date", "pm2_5", "pm10", "fuente",
        ]
    )


def extract(path=None) -> pd.DataFrame:
    """Lee una fuente validada de PM2.5/PM10 si fue configurada.

    Si no hay archivo y `CAMS_API_ENABLED` no esta activo, devuelve un lote vacio
    para dejar la dimension preparada sin inventar datos.
    """
    try:
        frame = read_source("CAMS", path)
        pm_columns = [column for column in ("pm25", "pm2_5", "pm2_5_media", "pm10", "pm10_media") if column in frame.columns]
        if pm_columns:
            return frame.loc[frame[pm_columns].notna().any(axis=1)].reset_index(drop=True)
        return frame
    except FileNotFoundError:
        if _api_enabled():
            return _extract_api()
        return _empty_frame()
