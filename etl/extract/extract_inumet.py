from __future__ import annotations

import pandas as pd

from config.settings import INUMET_HUMEDAD_FILE, INUMET_TEMPERATURA_FILE
from .base import read_source


STATIONS = {
    "Rocha G3": {"departamento": "Rocha", "latitud": -34.48, "longitud": -54.33},
    "Colonia G3": {"departamento": "Colonia", "latitud": -34.47, "longitud": -57.84},
    "Salto G3": {"departamento": "Salto", "latitud": -31.38, "longitud": -57.97},
    "Paso de los Toros G3": {"departamento": "Tacuarembo", "latitud": -32.82, "longitud": -56.51},
    "Aeropuerto Melilla G3": {"departamento": "Montevideo", "latitud": -34.79, "longitud": -56.26},
    "Mercedes G3": {"departamento": "Soriano", "latitud": -33.25, "longitud": -58.03},
    "Artigas G3": {"departamento": "Artigas", "latitud": -30.40, "longitud": -56.47},
}


def build_frame(temperatura_file: str, humedad_file: str) -> pd.DataFrame:
    temp = pd.read_csv(temperatura_file, sep=";")
    hum = pd.read_csv(humedad_file, sep=";")
    temp = temp.rename(columns={"temp_aire": "temperatura_c", "estacion_id": "estacion"})
    hum = hum.rename(columns={"hum_relativa": "humedad_pct", "estacion_id": "estacion"})
    for frame in (temp, hum):
        frame["fecha"] = pd.to_datetime(frame["fecha"], errors="coerce", utc=True)
        frame["estacion"] = frame["estacion"].astype("string")
        frame.dropna(subset=["fecha", "estacion"], inplace=True)
        frame.drop(frame.loc[~frame["estacion"].isin(STATIONS)].index, inplace=True)
    merged = temp.merge(hum, on=["fecha", "estacion"], how="outer")
    merged["pais_codigo"] = "URY"
    merged["ubicacion"] = merged["estacion"]
    merged["fecha_hora_utc"] = merged["fecha"]
    merged["fuente"] = "INUMET"
    merged["departamento"] = merged["estacion"].map(lambda value: STATIONS[value]["departamento"])
    merged["latitud"] = merged["estacion"].map(lambda value: STATIONS[value]["latitud"])
    merged["longitud"] = merged["estacion"].map(lambda value: STATIONS[value]["longitud"])
    return merged[
        [
            "fecha_hora_utc",
            "pais_codigo",
            "ubicacion",
            "departamento",
            "latitud",
            "longitud",
            "temperatura_c",
            "humedad_pct",
            "fuente",
        ]
    ].sort_values(["ubicacion", "fecha_hora_utc"]).reset_index(drop=True)


def extract(path=None):
    """INUMET aplica exclusivamente a estaciones de Uruguay."""
    try:
        return read_source("INUMET", path)
    except FileNotFoundError:
        if INUMET_TEMPERATURA_FILE and INUMET_HUMEDAD_FILE:
            return build_frame(INUMET_TEMPERATURA_FILE, INUMET_HUMEDAD_FILE)
        raise
