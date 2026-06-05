#!/usr/bin/env bash
set -euo pipefail

# Proyecto LIDIA EC3 - validacion local de CDC.
# Solo verifica eventos registrados en PostgreSQL/MongoDB locales. No modifica
# datos reales ni fabrica registros de origen.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

LOG_DIR="evidencia/logs"
LOG_FILE="$LOG_DIR/cdc_validacion_local.log"
ENV_FILE=".env.docker"
if [[ ! -f "$ENV_FILE" ]]; then
  ENV_FILE=".env.docker.example"
fi

mkdir -p "$LOG_DIR"

mask() {
  sed -E \
    -e 's#(postgresql://[^:]+:)[^@]+@#\1***@#g' \
    -e 's#(mongodb://[^:]+:)[^@]+@#\1***@#g' \
    -e 's#(--password )[A-Za-z0-9_.-]+#\1***#g' \
    -e 's#(-p )[A-Za-z0-9_.-]+#\1***#g'
}

if [[ "${LIDIA_CDC_LOGGING:-0}" != "1" ]]; then
  export LIDIA_CDC_LOGGING=1
  bash "$0" "$@" 2>&1 | mask | tee "$LOG_FILE"
  exit "${PIPESTATUS[0]}"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[CDC-local] ERROR: Docker no esta disponible en esta terminal."
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

COMPOSE=(docker compose --env-file "$ENV_FILE" -f docker-compose.yml)

echo "[CDC-local] Validando eventos CDC FIRMS en PostgreSQL local..."
"${COMPOSE[@]}" exec -T postgres psql -U "${POSTGRES_USER:-lidia}" -d "${POSTGRES_DB:-proyecto_lidia}" -c "
  SELECT fuente, tipo_evento, COUNT(*)::bigint AS eventos
  FROM audit.cdc_eventos
  WHERE fuente='FIRMS'
  GROUP BY fuente, tipo_evento
  ORDER BY fuente, tipo_evento;

  SELECT run_id, fuente, estado, filas_leidas, filas_insertadas, filas_actualizadas, filas_rechazadas, finalizado_en
  FROM audit.etl_runs
  WHERE fuente='FIRMS'
  ORDER BY finalizado_en DESC NULLS LAST, iniciado_en DESC
  LIMIT 5;

  SELECT COUNT(*)::bigint AS natural_keys_duplicadas
  FROM (
    SELECT natural_key
    FROM staging.stg_firms
    GROUP BY natural_key
    HAVING COUNT(*) > 1
  ) d;
"

echo "[CDC-local] Validando trazas MongoDB relacionadas..."
"${COMPOSE[@]}" exec -T mongo mongosh --quiet \
  --username "${MONGO_INITDB_ROOT_USERNAME:-lidia}" \
  --password "${MONGO_INITDB_ROOT_PASSWORD:-local_lidia}" \
  --authenticationDatabase admin \
  proyecto_lidia --eval '
    printjson({
      ingesta_metadata_firms: db.ingesta_metadata.countDocuments({fuente: "FIRMS"}),
      pipeline_logs_firms: db.pipeline_logs.countDocuments({fuente: "FIRMS"}),
      raw_payloads_firms: db.raw_payloads.countDocuments({fuente: "FIRMS"}),
      snapshots_firms: db.snapshots_firms.countDocuments()
    });
    printjson(db.ingesta_metadata.find({fuente: "FIRMS"}, {_id: 0}).sort({registrado_en: -1}).limit(3).toArray());
  '

echo
echo "[CDC-local] Interpretacion:"
echo "- 'alta' demuestra carga inicial de registros reales FIRMS."
echo "- 'sin_cambio' aparece cuando se ejecuta la misma carga controlada otra vez."
echo "- 'modificacion' solo aparece si el origen real cambia o si se ejecuta una simulacion CDC marcada explicitamente como tal."
echo "- Este script no simula modificaciones para no presentar datos fabricados como evidencia real."
