#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL no esta definida." >&2
  echo "Ejemplo: export DATABASE_URL='postgresql://usuario:password@host:5432/proyecto_lidia'" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/evidencia/logs"
mkdir -p "${LOG_DIR}"

RUN_TS="$(date -u +%Y%m%dT%H%M%SZ)"
ESTRUCTURA_LOG="${LOG_DIR}/d3_estructura_etl_${RUN_TS}.log"
TESTS_LOG="${LOG_DIR}/d3_compile_tests_${RUN_TS}.log"
PIPELINE_LOG="${LOG_DIR}/d3_pipeline_${RUN_TS}.log"
SQL_LOG="${LOG_DIR}/d3_validacion_etl_${RUN_TS}.log"
RESUMEN_LOG="${LOG_DIR}/d3_resumen_ultima_ejecucion.log"
DEFAULT_D3_ETL_COMMAND='PYTHONPATH="$(pwd)" python -u etl/main.py --smoke --start-date 2025-01-01 --end-date 2025-01-07 --countries URY --max-records-per-source 1000 --skip-mongo'

cd "${ROOT_DIR}"

{
  echo "D3 Proyecto LIDIA EC3 - prueba de conexion PostgreSQL"
  echo "Fecha UTC: ${RUN_TS}"
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "SELECT current_database() AS database, current_user AS usuario, now() AS conectado_en;"
} 2>&1 | tee "${RESUMEN_LOG}"

if grep -R "MONGO_ENABLED" -n etl config >/dev/null 2>&1; then
  if [[ "${MONGO_ENABLED:-false}" =~ ^(1|true|TRUE|yes|YES)$ && -z "${MONGO_URI:-}" ]]; then
    echo "ERROR: MONGO_ENABLED esta activo pero MONGO_URI no esta definida." 2>&1 | tee -a "${RESUMEN_LOG}" >&2
    exit 1
  fi
  if [[ -n "${MONGO_URI:-}" ]]; then
    echo "MongoDB documental detectado mediante MONGO_URI: configurado (valor oculto)." 2>&1 | tee -a "${RESUMEN_LOG}"
  else
    echo "MongoDB documental: MONGO_URI no definida; se valida ETL PostgreSQL y se documenta la limitacion NoSQL si aplica." 2>&1 | tee -a "${RESUMEN_LOG}"
  fi
fi

{
  echo "D3 Proyecto LIDIA EC3 - estructura ETL"
  echo "Fecha UTC: ${RUN_TS}"
  echo
  echo "Carpetas etl/"
  find etl -type d \
    -not -path '*/__pycache__*' \
    -not -path '*/.ipynb_checkpoints*' \
    | sort
  echo
  echo "Archivos principales ETL"
  find etl -type f \
    -not -path '*/__pycache__*' \
    -not -path '*/.ipynb_checkpoints*' \
    | sort
  echo
  echo "Fuentes esperadas: FIRMS, Open-Meteo historico (METEO tecnico), CAMS/Open-Meteo Air Quality, CHIRPS, MODIS, INUMET."
  echo "Configuracion externa: variables de entorno y config/.env.example; no se imprime contenido .env."
  echo
  echo "Comando pipeline configurado"
  echo "${D3_ETL_COMMAND:-${DEFAULT_D3_ETL_COMMAND}}"
  echo
  echo "Parametros detectados desde etl/main.py"
  python -m etl.main --help || true
} 2>&1 | tee "${ESTRUCTURA_LOG}"

{
  echo "D3 Proyecto LIDIA EC3 - compileall y tests"
  echo "Fecha UTC: ${RUN_TS}"
  python -m compileall -q .
  if [[ -d tests ]]; then
    python -m pytest -q tests
  else
    echo "No existe carpeta tests; se registra limitacion."
  fi
} 2>&1 | tee "${TESTS_LOG}"

{
  echo "D3 Proyecto LIDIA EC3 - ejecucion pipeline"
  echo "Fecha UTC: ${RUN_TS}"
  echo "Comando: ${D3_ETL_COMMAND:-${DEFAULT_D3_ETL_COMMAND}}"
  echo "Nota: no se imprime contenido de .env ni secretos."
  set +e
  eval "${D3_ETL_COMMAND:-${DEFAULT_D3_ETL_COMMAND}}"
  PIPELINE_EXIT_CODE=$?
  set -e
  echo "Exit code pipeline: ${PIPELINE_EXIT_CODE}"
  if [[ "${PIPELINE_EXIT_CODE}" -eq 137 || "${PIPELINE_EXIT_CODE}" -eq 9 ]]; then
    echo "LIMITACION: el proceso fue matado por recursos. Recomendacion: usar --smoke, acotar fechas/paises y bajar --max-records-per-source."
  elif [[ "${PIPELINE_EXIT_CODE}" -ne 0 ]]; then
    echo "LIMITACION: el pipeline finalizo con error; revisar stdout/stderr anteriores."
  fi
} 2>&1 | tee "${PIPELINE_LOG}"

{
  echo "D3 Proyecto LIDIA EC3 - validacion SQL ETL"
  echo "Fecha UTC: ${RUN_TS}"
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f sql/validation/d3_validacion_etl.sql
} 2>&1 | tee "${SQL_LOG}"

{
  echo "D3 ultima ejecucion"
  echo "Fecha UTC: ${RUN_TS}"
  echo "Estructura ETL log: ${ESTRUCTURA_LOG}"
  echo "Compile/tests log: ${TESTS_LOG}"
  echo "Pipeline log: ${PIPELINE_LOG}"
  echo "Validacion SQL log: ${SQL_LOG}"
  echo "Comando pipeline: ${D3_ETL_COMMAND:-${DEFAULT_D3_ETL_COMMAND}}"
  echo "Exit code pipeline: ${PIPELINE_EXIT_CODE:-no_ejecutado}"
  echo "Limitacion: si el exit code es 137 o 9, el proceso fue matado por recursos; usar corrida smoke acotada."
  echo "PostgreSQL es el Data Warehouse principal; MongoDB queda como complemento documental."
} 2>&1 | tee -a "${RESUMEN_LOG}"

exit "${PIPELINE_EXIT_CODE:-0}"
