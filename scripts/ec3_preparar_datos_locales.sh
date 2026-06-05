#!/usr/bin/env bash
set -euo pipefail

# Proyecto LIDIA EC3 - preparacion local reproducible.
# Levanta PostgreSQL/MongoDB locales, crea estructuras, carga FIRMS real
# acotado desde data/processed y genera evidencia. No usa datos sinteticos.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

LOG_DIR="evidencia/logs"
LOG_FILE="$LOG_DIR/ec3_preparar_datos_locales.log"
ENV_FILE=".env.docker"
if [[ ! -f "$ENV_FILE" ]]; then
  ENV_FILE=".env.docker.example"
fi

mkdir -p "$LOG_DIR"

mask() {
  sed -E \
    -e 's#(postgresql://[^:]+:)[^@]+@#\1***@#g' \
    -e 's#(mongodb://[^:]+:)[^@]+@#\1***@#g' \
    -e 's#(POSTGRES_PASSWORD=).+#\1***#g' \
    -e 's#(MONGO_INITDB_ROOT_PASSWORD=).+#\1***#g' \
    -e 's#(--password )[A-Za-z0-9_.-]+#\1***#g' \
    -e 's#(-p )[A-Za-z0-9_.-]+#\1***#g'
}

if [[ "${LIDIA_PREPARAR_DATOS_LOGGING:-0}" != "1" ]]; then
  export LIDIA_PREPARAR_DATOS_LOGGING=1
  bash "$0" "$@" 2>&1 | mask | tee "$LOG_FILE"
  exit "${PIPESTATUS[0]}"
fi

echo "[EC3-local] Proyecto: $PROJECT_ROOT"

for required in docker-compose.yml "$ENV_FILE" etl/main.py sql/ddl/00_schemas.sql scripts/cargar_bases_local_docker.sh scripts/cargar_firms_smoke_local.sh; do
  if [[ ! -e "$required" ]]; then
    echo "[EC3-local] ERROR: falta $required"
    exit 1
  fi
done

if [[ ! -f "data/processed/firms_nrt_procesado.parquet" ]]; then
  echo "[EC3-local] ERROR: falta data/processed/firms_nrt_procesado.parquet"
  echo "[EC3-local] Copie el archivo FIRMS real a ese path o configure FIRMS_FILE en config/.env."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[EC3-local] ERROR: Docker no esta disponible en esta terminal."
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

COMPOSE=(docker compose --env-file "$ENV_FILE" -f docker-compose.yml)

echo "[EC3-local] Levantando PostgreSQL y MongoDB locales..."
"${COMPOSE[@]}" up -d --wait postgres mongo --remove-orphans

echo "[EC3-local] Estado Docker:"
"${COMPOSE[@]}" ps

echo "[EC3-local] Preparando estructuras PostgreSQL/MongoDB..."
bash scripts/cargar_bases_local_docker.sh

echo "[EC3-local] Carga FIRMS real controlada - corrida 1..."
bash scripts/cargar_firms_smoke_local.sh

echo "[EC3-local] Conteo despues de corrida 1..."
COUNT_AFTER_1="$("${COMPOSE[@]}" exec -T postgres psql -U "${POSTGRES_USER:-lidia}" -d "${POSTGRES_DB:-proyecto_lidia}" -Atc "SELECT COUNT(*) FROM dw.fact_incendio;")"
echo "[EC3-local] dw.fact_incendio despues corrida 1: ${COUNT_AFTER_1}"

echo "[EC3-local] Carga FIRMS real controlada - corrida 2 para idempotencia..."
{
  bash scripts/cargar_firms_smoke_local.sh
  echo
  echo "== Conteos CDC FIRMS =="
  "${COMPOSE[@]}" exec -T postgres psql -U "${POSTGRES_USER:-lidia}" -d "${POSTGRES_DB:-proyecto_lidia}" -c "
    SELECT fuente, tipo_evento, COUNT(*)::bigint AS eventos
    FROM audit.cdc_eventos
    WHERE fuente='FIRMS'
    GROUP BY fuente, tipo_evento
    ORDER BY fuente, tipo_evento;
  "
  echo
  echo "== Duplicados por natural_key en dw.fact_incendio =="
  "${COMPOSE[@]}" exec -T postgres psql -U "${POSTGRES_USER:-lidia}" -d "${POSTGRES_DB:-proyecto_lidia}" -c "
    SELECT COUNT(*)::bigint AS natural_keys_duplicadas
    FROM (
      SELECT natural_key
      FROM dw.fact_incendio
      GROUP BY natural_key
      HAVING COUNT(*) > 1
    ) d;
  "
} 2>&1 | tee "$LOG_DIR/idempotencia_firms_smoke.log"

COUNT_AFTER_2="$("${COMPOSE[@]}" exec -T postgres psql -U "${POSTGRES_USER:-lidia}" -d "${POSTGRES_DB:-proyecto_lidia}" -Atc "SELECT COUNT(*) FROM dw.fact_incendio;")"
echo "[EC3-local] dw.fact_incendio despues corrida 2: ${COUNT_AFTER_2}"

if [[ "$COUNT_AFTER_1" != "$COUNT_AFTER_2" ]]; then
  echo "[EC3-local] ERROR: idempotencia fallida; el conteo de hechos cambio entre corridas."
  exit 1
fi

echo "[EC3-local] Ejecutando validacion CDC local..."
bash scripts/ec3_validar_cdc_local.sh || true

echo "[EC3-local] Ejecutando compileall..."
python3 -m compileall -q .

echo "[EC3-local] Ejecutando pytest..."
python3 -m pytest -q tests

echo "[EC3-local] Ejecutando auditor EC3..."
python3 scripts/ec3_verificar_logrado.py || true

echo "[EC3-local] Resumen PostgreSQL:"
"${COMPOSE[@]}" exec -T postgres psql -U "${POSTGRES_USER:-lidia}" -d "${POSTGRES_DB:-proyecto_lidia}" -c "
  SELECT 'staging.stg_firms' AS tabla, COUNT(*)::bigint AS filas FROM staging.stg_firms
  UNION ALL
  SELECT 'dw.fact_incendio', COUNT(*) FROM dw.fact_incendio;

  SELECT pais_codigo, COUNT(*)::bigint AS filas
  FROM staging.stg_firms
  GROUP BY pais_codigo
  ORDER BY pais_codigo;

  SELECT COUNT(*)::bigint AS fuera_alcance
  FROM staging.stg_firms
  WHERE pais_codigo NOT IN ('URY','ARG','BRA');
"

echo "[EC3-local] Resumen MongoDB:"
"${COMPOSE[@]}" exec -T mongo mongosh --quiet \
  --username "${MONGO_INITDB_ROOT_USERNAME:-lidia}" \
  --password "${MONGO_INITDB_ROOT_PASSWORD:-local_lidia}" \
  --authenticationDatabase admin \
  proyecto_lidia --eval '
    printjson({
      database: db.getName(),
      collections: db.getCollectionNames().sort(),
      counts: Object.fromEntries(db.getCollectionNames().sort().map(c => [c, db.getCollection(c).countDocuments()]))
    })
  '

echo
echo "# Resumen EC3 local"
echo "- Docker: postgres/mongo levantados con docker-compose.yml"
echo "- PostgreSQL staging.stg_firms y dw.fact_incendio cargados desde FIRMS real local."
echo "- MongoDB: metadata/logs/raw_payloads/snapshots complementarios."
echo "- Idempotencia: conteo dw.fact_incendio corrida 1=${COUNT_AFTER_1}, corrida 2=${COUNT_AFTER_2}."
echo "- Logs principales:"
echo "  - $LOG_FILE"
echo "  - evidencia/logs/firms_dataset_perfil.log"
echo "  - evidencia/logs/firms_paises_fuera_alcance.log"
echo "  - evidencia/logs/carga_firms_smoke_local.log"
echo "  - evidencia/logs/postgres_conteos_post_carga.log"
echo "  - evidencia/logs/mongo_estado_post_carga.log"
echo "  - evidencia/logs/idempotencia_firms_smoke.log"
echo "  - evidencia/logs/cdc_validacion_local.log"
