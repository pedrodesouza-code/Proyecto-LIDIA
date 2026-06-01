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

# METEO es la etiqueta tecnica interna para Open-Meteo historico.
FUENTES_VALIDAS = ("INUMET", "FIRMS", "CHIRPS", "METEO", "MODIS", "CAMS")
PAISES = {
    "URY": {"nombre": "Uruguay", "iso2": "UY"},
    "ARG": {"nombre": "Argentina", "iso2": "AR"},
    "BRA": {"nombre": "Brasil", "iso2": "BR"},
}

PUNTOS_MONITOREO = {
    "UY_Montevideo": {"pais": "URY", "ubicacion": "Montevideo", "lat": -34.90, "lon": -56.16},
    "UY_Canelones": {"pais": "URY", "ubicacion": "Canelones", "lat": -34.52, "lon": -56.28},
    "UY_Maldonado": {"pais": "URY", "ubicacion": "Maldonado", "lat": -34.90, "lon": -54.95},
    "UY_Rocha": {"pais": "URY", "ubicacion": "Rocha", "lat": -34.48, "lon": -54.33},
    "UY_Treinta_y_Tres": {"pais": "URY", "ubicacion": "Treinta_y_Tres", "lat": -33.23, "lon": -54.38},
    "UY_Cerro_Largo": {"pais": "URY", "ubicacion": "Cerro_Largo", "lat": -32.37, "lon": -54.17},
    "UY_Rivera": {"pais": "URY", "ubicacion": "Rivera", "lat": -30.90, "lon": -55.55},
    "UY_Artigas": {"pais": "URY", "ubicacion": "Artigas", "lat": -30.40, "lon": -56.47},
    "UY_Salto": {"pais": "URY", "ubicacion": "Salto", "lat": -31.38, "lon": -57.97},
    "UY_Paysandu": {"pais": "URY", "ubicacion": "Paysandu", "lat": -32.32, "lon": -58.08},
    "UY_Rio_Negro": {"pais": "URY", "ubicacion": "Rio_Negro", "lat": -33.12, "lon": -58.31},
    "UY_Soriano": {"pais": "URY", "ubicacion": "Soriano", "lat": -33.25, "lon": -58.03},
    "UY_Colonia": {"pais": "URY", "ubicacion": "Colonia", "lat": -34.47, "lon": -57.84},
    "UY_San_Jose": {"pais": "URY", "ubicacion": "San_Jose", "lat": -34.34, "lon": -56.71},
    "UY_Flores": {"pais": "URY", "ubicacion": "Flores", "lat": -33.54, "lon": -56.89},
    "UY_Florida": {"pais": "URY", "ubicacion": "Florida", "lat": -34.10, "lon": -56.21},
    "UY_Durazno": {"pais": "URY", "ubicacion": "Durazno", "lat": -33.41, "lon": -56.50},
    "UY_Lavalleja": {"pais": "URY", "ubicacion": "Lavalleja", "lat": -34.37, "lon": -55.23},
    "UY_Tacuarembo": {"pais": "URY", "ubicacion": "Tacuarembo", "lat": -31.73, "lon": -55.98},
    "AR_Misiones": {"pais": "ARG", "ubicacion": "Misiones", "lat": -27.37, "lon": -55.90},
    "AR_Corrientes": {"pais": "ARG", "ubicacion": "Corrientes", "lat": -27.48, "lon": -58.83},
    "AR_Chaco": {"pais": "ARG", "ubicacion": "Chaco", "lat": -27.45, "lon": -58.98},
    "AR_Formosa": {"pais": "ARG", "ubicacion": "Formosa", "lat": -26.18, "lon": -58.18},
    "AR_Santiago_del_Estero": {"pais": "ARG", "ubicacion": "Santiago_del_Estero", "lat": -27.78, "lon": -64.26},
    "AR_Salta": {"pais": "ARG", "ubicacion": "Salta", "lat": -24.79, "lon": -65.41},
    "BR_Rio_Grande_do_Sul": {"pais": "BRA", "ubicacion": "Rio_Grande_do_Sul", "lat": -30.03, "lon": -51.23},
    "BR_Santa_Catarina": {"pais": "BRA", "ubicacion": "Santa_Catarina", "lat": -27.59, "lon": -48.55},
    "BR_Parana": {"pais": "BRA", "ubicacion": "Parana", "lat": -25.42, "lon": -49.27},
    "BR_Uruguaiana": {"pais": "BRA", "ubicacion": "Uruguaiana", "lat": -29.76, "lon": -57.09},
    "BR_Pelotas": {"pais": "BRA", "ubicacion": "Pelotas", "lat": -31.77, "lon": -52.34},
    "BR_Caxias_do_Sul": {"pais": "BRA", "ubicacion": "Caxias_do_Sul", "lat": -29.17, "lon": -51.18},
}

# Caja envolvente operacional del alcance URY/ARG/BRA; el filtro final usa codigo de pais.
FIRMS_BBOX = os.getenv("FIRMS_BBOX", "-73.99,-55.98,-34.73,5.28")
FIRMS_BASE_URL = os.getenv("FIRMS_BASE_URL", "https://firms.modaps.eosdis.nasa.gov/api/area/csv")
FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "")

SOURCE_FILES = {
    "FIRMS": os.getenv("FIRMS_FILE", ""),
    "METEO": os.getenv("METEO_FILE", ""),
    "CHIRPS": os.getenv("CHIRPS_FILE", ""),
    "MODIS": os.getenv("MODIS_FILE", ""),
    "INUMET": os.getenv("INUMET_FILE", ""),
    "CAMS": os.getenv("CAMS_FILE", os.getenv("AIR_QUALITY_FILE", "")),
}
FIRMS_COUNTRY_BOUNDARIES_FILE = os.getenv("FIRMS_COUNTRY_BOUNDARIES_FILE", "")
METEO_API_URL = os.getenv("METEO_API_URL", "https://archive-api.open-meteo.com/v1/archive")
METEO_START_DATE = os.getenv("METEO_START_DATE", "2018-01-01")
METEO_END_DATE = os.getenv("METEO_END_DATE", "2025-12-31")
CAMS_AIR_QUALITY_API_URL = os.getenv(
    "CAMS_AIR_QUALITY_API_URL",
    "https://air-quality-api.open-meteo.com/v1/air-quality",
)
INUMET_TEMPERATURA_FILE = os.getenv("INUMET_TEMPERATURA_FILE", "")
INUMET_HUMEDAD_FILE = os.getenv("INUMET_HUMEDAD_FILE", "")

PG_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("LIDIA_POSTGRES_DB", os.getenv("POSTGRES_DB", "proyecto_lidia")),
    "user": os.getenv("POSTGRES_USER", "lidia_etl_user"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

MONGO_CONFIG = {
    "host": os.getenv("MONGO_HOST", "localhost"),
    "port": int(os.getenv("MONGO_PORT", "27017")),
    "database": os.getenv("MONGO_DB", "proyecto_lidia"),
    "user": os.getenv("MONGO_USER", ""),
    "password": os.getenv("MONGO_PASSWORD", ""),
    "auth_source": os.getenv("MONGO_AUTH_SOURCE", "admin"),
}
MONGO_ENABLED = os.getenv("MONGO_ENABLED", "false").lower() in {"1", "true", "yes"}

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
