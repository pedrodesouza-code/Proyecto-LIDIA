"""Extraccion de observaciones horarias reales de estaciones INUMET."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.settings import INUMET_HUMEDAD_FILE, INUMET_TEMPERATURA_FILE, ROOT

# Metadata publicada por INUMET para estaciones meteorologicas automaticas.
# https://www.inumet.gub.uy/tiempo/estaciones-meteorologicas-automaticas
STATIONS = {
    "Aeropuerto Melilla G3": {"departamento": "Montevideo", "lat": -34.78999, "lon": -56.26628},
    "Artigas G3": {"departamento": "Artigas", "lat": -30.39911, "lon": -56.51267},
    "Colonia G3": {"departamento": "Colonia", "lat": -34.45182, "lon": -57.76804},
    "Mercedes G3": {"departamento": "Soriano", "lat": -33.25068, "lon": -58.06920},
    "Paso de los Toros G3": {"departamento": "Tacuarembo", "lat": -32.79667, "lon": -56.51467},
    "Rocha G3": {"departamento": "Rocha", "lat": -34.49361, "lon": -54.31250},
    "Salto G3": {"departamento": "Salto", "lat": -31.43889, "lon": -57.98102},
}


def _path(configured: str, label: str) -> Path:
    if not configured.strip():
        raise FileNotFoundError(f"{label} no esta configurado")
    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise FileNotFoundError(f"{label}: archivo no encontrado: {path}")
    return path


def extract(path=None) -> pd.DataFrame:
    """Une temperatura y humedad INUMET, restringidas a Uruguay y 2018-2025."""
    temperature = pd.read_csv(_path(INUMET_TEMPERATURA_FILE, "INUMET_TEMPERATURA_FILE"), sep=";")
    humidity = pd.read_csv(_path(INUMET_HUMEDAD_FILE, "INUMET_HUMEDAD_FILE"), sep=";")
    frame = temperature.merge(humidity, on=["fecha", "estacion_id"], how="outer")
    frame["time"] = pd.to_datetime(frame["fecha"], errors="coerce", utc=True)
    frame = frame[
        frame["time"].between(pd.Timestamp("2018-01-01", tz="UTC"), pd.Timestamp("2025-12-31 23:59:59", tz="UTC"))
        & frame["estacion_id"].isin(STATIONS)
    ].copy()
    frame["pais"] = "URY"
    frame["ubicacion"] = frame["estacion_id"]
    frame["departamento"] = frame["estacion_id"].map(lambda value: STATIONS[value]["departamento"])
    frame["lat"] = frame["estacion_id"].map(lambda value: STATIONS[value]["lat"])
    frame["lon"] = frame["estacion_id"].map(lambda value: STATIONS[value]["lon"])
    frame["temperatura_c"] = frame["temp_aire"]
    frame["humedad_pct"] = frame["hum_relativa"]
    return frame[
        ["time", "pais", "ubicacion", "departamento", "lat", "lon", "temperatura_c", "humedad_pct"]
    ]
