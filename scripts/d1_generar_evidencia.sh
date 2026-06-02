#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL no esta definida." >&2
  echo "Definir DATABASE_URL como variable de entorno antes de ejecutar." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/evidencia/logs"
mkdir -p "${LOG_DIR}"

RUN_TS="$(date -u +%Y%m%dT%H%M%SZ)"
DDL_LOG="${LOG_DIR}/d1_ddl_${RUN_TS}.log"
VALIDACION_LOG="${LOG_DIR}/d1_validacion_modelo_relacional_${RUN_TS}.log"
RESUMEN_LOG="${LOG_DIR}/d1_resumen_ultima_ejecucion.log"

cd "${ROOT_DIR}"

{
  echo "D1 Proyecto LIDIA EC3 - prueba de conexion"
  echo "Fecha UTC: ${RUN_TS}"
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "SELECT current_database() AS database, current_user AS usuario, now() AS conectado_en;"
} 2>&1 | tee "${RESUMEN_LOG}"

{
  echo "D1 Proyecto LIDIA EC3 - ejecucion DDL"
  echo "Fecha UTC: ${RUN_TS}"
  echo "Ejecutando sql/ddl/00_schemas.sql"
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f sql/ddl/00_schemas.sql
  if psql "${DATABASE_URL}" -Atqc "SELECT pg_has_role(current_user, 'lidia_admin', 'USAGE') OR rolsuper FROM pg_roles WHERE rolname=current_user;" 2>/dev/null | grep -qx 't'; then
    echo "Ejecutando sql/ddl/01_roles.sql"
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f sql/ddl/01_roles.sql
  else
    echo "Omitiendo sql/ddl/01_roles.sql: el usuario actual no tiene permisos administrativos de roles."
  fi
  echo "Ejecutando sql/ddl/02_Schema.sql"
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f sql/ddl/02_Schema.sql
  echo "Ejecutando sql/ddl/03_indices.sql"
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f sql/ddl/03_indices.sql
  echo "Ejecutando sql/ddl/04_vistas.sql"
  if ! psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f sql/ddl/04_vistas.sql; then
    echo "04_vistas.sql fallo posiblemente por GRANT a rol inexistente. Reintentando cuerpo de vistas sin GRANT para entornos UTEC restringidos."
    sed '/^GRANT SELECT ON dw\\.v_incendios_pais_periodo/,$d' sql/ddl/04_vistas.sql | psql "${DATABASE_URL}" -v ON_ERROR_STOP=1
  fi
  echo "DDL D1 finalizado."
} 2>&1 | tee "${DDL_LOG}"

{
  echo "D1 Proyecto LIDIA EC3 - validacion modelo relacional"
  echo "Fecha UTC: ${RUN_TS}"
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f sql/validation/d1_validacion_modelo_relacional.sql
  echo "Validacion D1 finalizada."
} 2>&1 | tee "${VALIDACION_LOG}"

{
  echo "D1 ultima ejecucion"
  echo "Fecha UTC: ${RUN_TS}"
  echo "DDL log: ${DDL_LOG}"
  echo "Validacion log: ${VALIDACION_LOG}"
} 2>&1 | tee -a "${RESUMEN_LOG}"
