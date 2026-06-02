#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${MONGO_URI:-}" ]]; then
  echo "ERROR: MONGO_URI no esta definida." >&2
  echo "Definir MONGO_URI como variable de entorno antes de ejecutar." >&2
  exit 1
fi

if ! command -v mongosh >/dev/null 2>&1; then
  echo "ERROR: mongosh no esta instalado o no esta en PATH." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/evidencia/logs"
mkdir -p "${LOG_DIR}"

RUN_TS="$(date -u +%Y%m%dT%H%M%SZ)"
CONN_LOG="${LOG_DIR}/d2_mongodb_conexion_${RUN_TS}.log"
VALIDACION_LOG="${LOG_DIR}/d2_validacion_mongodb_${RUN_TS}.log"
RESUMEN_LOG="${LOG_DIR}/d2_resumen_ultima_ejecucion.log"

cd "${ROOT_DIR}"

{
  echo "D2 Proyecto LIDIA EC3 - prueba de conexion MongoDB"
  echo "Fecha UTC: ${RUN_TS}"
  mongosh "${MONGO_URI}" --quiet --eval 'printjson({database: db.getName(), ping: db.runCommand({ping: 1}), timestamp: new Date().toISOString()})'
} 2>&1 | tee "${CONN_LOG}"

{
  echo "D2 Proyecto LIDIA EC3 - validacion NoSQL"
  echo "Fecha UTC: ${RUN_TS}"
  mongosh "${MONGO_URI}" --quiet nosql/d2_validacion_mongodb.js
  echo "Validacion D2 NoSQL finalizada."
} 2>&1 | tee "${VALIDACION_LOG}"

{
  echo "D2 ultima ejecucion"
  echo "Fecha UTC: ${RUN_TS}"
  echo "Conexion log: ${CONN_LOG}"
  echo "Validacion log: ${VALIDACION_LOG}"
  echo "Nota: MongoDB se valida como capa documental complementaria; PostgreSQL conserva el Data Warehouse principal."
} 2>&1 | tee "${RESUMEN_LOG}"
