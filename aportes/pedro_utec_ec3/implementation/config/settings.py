"""Configuracion externa para la implementacion EC3 de Proyecto LIDIA."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
for env_path in (ROOT / "config" / ".env", ROOT / "config" / "utec.env", ROOT / ".env"):
    if env_path.exists():
        load_dotenv(env_path, override=False)
        break

DATA_ROOT = Path(os.getenv("LIDIA_DATA_ROOT", str(ROOT / "data"))).expanduser()
PROCESSED_DIR = DATA_ROOT / "processed"
LOG_DIR = Path(os.getenv("LIDIA_LOG_DIR", str(ROOT / "logs"))).expanduser()

FUENTES_VALIDAS = ("INUMET", "FIRMS", "CHIRPS", "FORECAST", "METEO", "MODIS")
PAISES = {
    "URY": {"nombre": "Uruguay", "iso2": "UY"},
    "ARG": {"nombre": "Argentina", "iso2": "AR"},
    "BRA": {"nombre": "Brasil", "iso2": "BR"},
}

PUNTOS_MONITOREO = {
    "Montevideo": {"lat": -34.9011, "lon": -56.1645, "pais": "URY"},
    "Rivera": {"lat": -30.9053, "lon": -55.5508, "pais": "URY"},
    "Buenos_Aires": {"lat": -34.6037, "lon": -58.3816, "pais": "ARG"},
    "Posadas": {"lat": -27.3621, "lon": -55.9009, "pais": "ARG"},
    "Porto_Alegre": {"lat": -30.0346, "lon": -51.2177, "pais": "BRA"},
    "Campo_Grande": {"lat": -20.4697, "lon": -54.6201, "pais": "BRA"},
}

# Caja envolvente operacional del alcance URY/ARG/BRA; el filtro final usa codigo de pais.
FIRMS_BBOX = os.getenv("FIRMS_BBOX", "-73.99,-55.98,-34.73,5.28")
FIRMS_BASE_URL = os.getenv("FIRMS_BASE_URL", "https://firms.modaps.eosdis.nasa.gov/api/area/csv")
FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "")

SOURCE_FILES = {
    "FIRMS": os.getenv("FIRMS_FILE", ""),
    "METEO": os.getenv("METEO_FILE", ""),
    "FORECAST": os.getenv("FORECAST_FILE", ""),
    "CHIRPS": os.getenv("CHIRPS_FILE", ""),
    "MODIS": os.getenv("MODIS_FILE", ""),
    "INUMET": os.getenv("INUMET_FILE", ""),
}

PG_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "lidia_ec3"),
    "user": os.getenv("POSTGRES_USER", "lidia_etl_user"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

MONGO_CONFIG = {
    "host": os.getenv("MONGO_HOST", "localhost"),
    "port": int(os.getenv("MONGO_PORT", "27017")),
    "database": os.getenv("MONGO_DB", "lidia_ec3"),
    "user": os.getenv("MONGO_USER", ""),
    "password": os.getenv("MONGO_PASSWORD", ""),
    "auth_source": os.getenv("MONGO_AUTH_SOURCE", "admin"),
}

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
