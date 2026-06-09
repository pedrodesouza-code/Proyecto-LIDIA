#!/usr/bin/env bash
# Proyecto LIDIA EC3 - variables de entorno para datasets procesados 2018-2025.
# No contiene credenciales. Debe ejecutarse con: source scripts/set_env_2018_2025.sh

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_LIDIA_ROOT="$(cd "${_SCRIPT_DIR}/.." && pwd)"

export LIDIA_DATA_ROOT="${_LIDIA_ROOT}/data"
export FIRMS_FILE="${_LIDIA_ROOT}/data/processed/firms_2018_2025.parquet"
export METEO_FILE="${_LIDIA_ROOT}/data/processed/meteo_2018_2025.parquet"
export CAMS_FILE="${_LIDIA_ROOT}/data/processed/cams_2018_2025.parquet"
export AIR_QUALITY_FILE="${CAMS_FILE}"
export CHIRPS_FILE="${_LIDIA_ROOT}/data/processed/chirps_2018_2025.parquet"
export MODIS_FILE="${_LIDIA_ROOT}/data/processed/modis_2018_2025.parquet"
export INUMET_FILE="${_LIDIA_ROOT}/data/processed/inumet_procesado.parquet"
export METEO_START_DATE="2018-01-01"
export METEO_END_DATE="2025-12-31"
export CAMS_START_DATE="2018-01-01"
export CAMS_END_DATE="2025-12-31"
export MONGO_ENABLED="${MONGO_ENABLED:-false}"
