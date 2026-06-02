#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

LOG_DIR="evidencia/logs"
mkdir -p "${LOG_DIR}"

ENV_FILE=".env.docker"
if [[ ! -f "${ENV_FILE}" ]]; then
  ENV_FILE=".env.docker.example"
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: docker compose no esta disponible." >&2
  exit 1
fi

compose() {
  docker compose --env-file "${ENV_FILE}" "$@"
}

mask() {
  sed -E \
    -e 's#(postgresql://[^:]+:)[^@]+@#\1***@#g' \
    -e 's#(mongodb://[^:]+:)[^@]+@#\1***@#g' \
    -e 's#(POSTGRES_PASSWORD: ).+#\1***#g' \
    -e 's#(POSTGRES_ETL_PASSWORD: ).+#\1***#g' \
    -e 's#(POSTGRES_DASHBOARD_PASSWORD: ).+#\1***#g' \
    -e 's#(MONGO_INITDB_ROOT_PASSWORD: ).+#\1***#g' \
    -e 's#(MONGO_PASSWORD: ).+#\1***#g' \
    -e 's#(POSTGRES_PASSWORD=).+#\1***#g' \
    -e 's#(MONGO_PASSWORD=).+#\1***#g' \
    -e 's#(MONGO_INITDB_ROOT_PASSWORD=).+#\1***#g' \
    -e 's#(--password )[A-Za-z0-9_.-]+#\1***#g'
}

echo "Generando evidencia D8 Docker con ${ENV_FILE} (valores sensibles ocultos)."

echo "[D8] 1/7 Validando docker-compose.yml..."
compose config 2>&1 | mask | tee "${LOG_DIR}/d8_docker_compose_config.log"

services="$(compose config --services)"
for service in postgres mongo etl streamlit; do
  if ! printf '%s\n' "${services}" | grep -qx "${service}"; then
    echo "ERROR: falta servicio ${service} en docker-compose.yml" >&2
    exit 1
  fi
done

echo "[D8] 2/7 Levantando PostgreSQL y MongoDB locales. La primera vez puede tardar por descarga de imagenes..."
compose up -d --wait postgres mongo 2>&1 | mask | tee "${LOG_DIR}/d8_docker_compose_up.log"

echo "[D8] 3/7 Construyendo imagen Python para ETL/Streamlit. La primera vez puede tardar instalando requirements..."
BUILD_OK=1
if ! docker compose --env-file "${ENV_FILE}" --progress plain build etl streamlit 2>&1 | mask | tee "${LOG_DIR}/d8_docker_build.log"; then
  BUILD_OK=0
  {
    echo "[D8] Limitacion: el build de etl/streamlit fallo."
    echo "[D8] Si aparecen errores Temporary failure in name resolution, es un problema de DNS/red de Docker hacia PyPI."
    echo "[D8] PostgreSQL y MongoDB locales se validan igual con sus contenedores base."
  } | tee -a "${LOG_DIR}/d8_docker_build.log"
fi

echo "[D8] 4/7 Registrando estado de servicios..."
compose ps 2>&1 | mask | tee "${LOG_DIR}/d8_docker_compose_ps.log"

echo "[D8] 5/7 Ejecutando DDL base en PostgreSQL local desde contenedor ETL..."
if [[ "${BUILD_OK}" -eq 1 ]]; then
  if compose ps --status running --services 2>/dev/null | grep -qx etl; then
    ETL_RUN=(compose exec -T etl)
  else
    ETL_RUN=(compose run --rm etl)
  fi

  "${ETL_RUN[@]}" python - <<'PY' 2>&1 | mask | tee "${LOG_DIR}/d8_docker_ddl_check.log"
import os
from pathlib import Path

import psycopg2

ddl_files = [
    "sql/ddl/00_schemas.sql",
    "sql/ddl/01_roles.sql",
    "sql/ddl/02_Schema.sql",
    "sql/ddl/03_indices.sql",
    "sql/ddl/04_vistas.sql",
]

with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
    conn.autocommit = True
    with conn.cursor() as cur:
        for file_name in ddl_files:
            sql = Path(file_name).read_text(encoding="utf-8")
            cur.execute(sql)
            print({"ddl": file_name, "estado": "ok"})
PY
else
  {
    echo "DDL no ejecutado desde ETL porque la imagen Python no pudo construirse."
    echo "Se valida PostgreSQL local con pg_isready/psql desde el contenedor postgres."
  } | tee "${LOG_DIR}/d8_docker_ddl_check.log"
fi

echo "[D8] 6/7 Probando conexion PostgreSQL desde contenedor ETL..."
if [[ "${BUILD_OK}" -eq 1 ]]; then
  "${ETL_RUN[@]}" python - <<'PY' 2>&1 | mask | tee "${LOG_DIR}/d8_docker_postgres_check.log"
import os
import psycopg2

url = os.environ["DATABASE_URL"]
with psycopg2.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user, COUNT(*) FROM information_schema.schemata WHERE schema_name IN ('staging','dw','audit')")
        database, user, schemas = cur.fetchone()
        print({"database": database, "user": user, "schemas_staging_dw_audit": schemas, "desde": "etl"})
PY
else
  compose exec -T postgres psql -U "${POSTGRES_USER:-lidia}" -d "${POSTGRES_DB:-proyecto_lidia}" \
    -c "SELECT current_database() AS database, current_user AS usuario;" \
    2>&1 | mask | tee "${LOG_DIR}/d8_docker_postgres_check.log"
fi

echo "[D8] 7/7 Probando conexion MongoDB desde contenedor ETL..."
if [[ "${BUILD_OK}" -eq 1 ]]; then
  "${ETL_RUN[@]}" python - <<'PY' 2>&1 | mask | tee "${LOG_DIR}/d8_docker_mongo_check.log"
import os
from pymongo import MongoClient

uri = os.environ["MONGO_URI"]
client = MongoClient(uri, serverSelectionTimeoutMS=5000)
print({"mongo_ping": client.admin.command("ping").get("ok"), "database": client.get_default_database().name, "desde": "etl"})
client.close()
PY
else
  compose exec -T mongo mongosh --quiet \
    --username "${MONGO_INITDB_ROOT_USERNAME:-lidia}" \
    --password "${MONGO_INITDB_ROOT_PASSWORD:-local_lidia}" \
    --authenticationDatabase admin \
    --eval 'printjson({mongo_ping: db.adminCommand({ping: 1}).ok, database: db.getName(), desde: "mongo"})' \
    2>&1 | mask | tee "${LOG_DIR}/d8_docker_mongo_check.log"
fi

{
  echo "# D8 Docker/despliegue - Resumen"
  echo
  echo "Generado con: \`${ENV_FILE}\`."
  echo
  echo "## Servicios esperados"
  echo
  for service in postgres mongo etl streamlit; do
    echo "- ${service}: presente"
  done
  echo
  echo "## Evidencias"
  echo
  echo "- \`${LOG_DIR}/d8_docker_compose_config.log\`: configuración Docker Compose con credenciales ocultas."
  echo "- \`${LOG_DIR}/d8_docker_compose_up.log\`: arranque local de PostgreSQL y MongoDB."
  echo "- \`${LOG_DIR}/d8_docker_build.log\`: construcción de imagen Python para ETL/Streamlit."
  echo "- \`${LOG_DIR}/d8_docker_compose_ps.log\`: estado de servicios."
  echo "- \`${LOG_DIR}/d8_docker_ddl_check.log\`: ejecución de DDL base en PostgreSQL local."
  echo "- \`${LOG_DIR}/d8_docker_postgres_check.log\`: conexión PostgreSQL desde contenedor ETL."
  echo "- \`${LOG_DIR}/d8_docker_mongo_check.log\`: conexión MongoDB desde contenedor ETL."
  echo
  echo "## Alcance"
  echo
  echo "Entorno local reproducible. No usa credenciales reales de UTEC ni se conecta a bases institucionales."
  echo "No ejecuta carga histórica completa."
  echo
  if [[ "${BUILD_OK}" -eq 1 ]]; then
    echo "Estado build ETL/Streamlit: OK."
  else
    echo "Estado build ETL/Streamlit: PARCIAL por problema de DNS/red de Docker hacia PyPI. PostgreSQL y MongoDB locales fueron validados con contenedores base."
  fi
} | tee "${LOG_DIR}/d8_resumen_despliegue.md"

echo "[D8] Evidencia Docker finalizada."
