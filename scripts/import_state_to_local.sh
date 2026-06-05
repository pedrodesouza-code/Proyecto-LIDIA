#!/usr/bin/env bash
set -euo pipefail

# Proyecto LIDIA - import de snapshot Jupyter/UTEC hacia Docker local.
# Requiere CONFIRM_RESTORE=1 porque reemplaza estado local restaurado.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LOG_DIR="evidencia/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/import_state_to_local.log"
ENV_FILE=".env.docker"
if [[ ! -f "$ENV_FILE" ]]; then
  ENV_FILE=".env.docker.example"
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ "${CONFIRM_RESTORE:-0}" != "1" ]]; then
  echo "[import] ERROR: esta operacion restaura snapshots sobre el entorno local."
  echo "[import] Ejecute: CONFIRM_RESTORE=1 bash scripts/import_state_to_local.sh"
  exit 1
fi

if [[ "${LIDIA_IMPORT_LOGGING:-0}" != "1" ]]; then
  export LIDIA_IMPORT_LOGGING=1
  bash "$0" "$@" 2>&1 | sed -E \
    -e 's#(postgresql://[^:]+:)[^@]+@#\1***@#g' \
    -e 's#(mongodb://[^:]+:)[^@]+@#\1***@#g' \
    -e 's#(--password )[A-Za-z0-9_.-]+#\1***#g' \
    -e 's#(-p )[A-Za-z0-9_.-]+#\1***#g' | tee "$LOG_FILE"
  exit "${PIPESTATUS[0]}"
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

COMPOSE=(docker compose --env-file "$ENV_FILE" -f docker-compose.yml)
if [[ "${SHARDING:-0}" == "1" ]]; then
  COMPOSE=(docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.sharding.yml)
fi

PG_SNAPSHOT="${POSTGRES_SNAPSHOT:-}"
if [[ -z "$PG_SNAPSHOT" ]]; then
  PG_SNAPSHOT="$(find backups/postgres -type f -name '*.sql' 2>/dev/null | sort | tail -1 || true)"
fi
if [[ -z "$PG_SNAPSHOT" || ! -f "$PG_SNAPSHOT" ]]; then
  echo "[import] ERROR: no se encontro snapshot PostgreSQL. Use POSTGRES_SNAPSHOT=/ruta/archivo.sql"
  exit 1
fi

MONGO_SNAPSHOT="${MONGO_SNAPSHOT:-}"
if [[ -z "$MONGO_SNAPSHOT" ]]; then
  MONGO_SNAPSHOT="$(find backups/mongo -maxdepth 1 -mindepth 1 -type d 2>/dev/null | sort | tail -1 || true)"
fi

echo "[import] $(date -Iseconds)"
echo "[import] Levantando servicios locales"
"${COMPOSE[@]}" up -d --wait postgres mongo

echo "[import] Restaurando PostgreSQL desde $PG_SNAPSHOT"
"${COMPOSE[@]}" exec -T postgres psql -v ON_ERROR_STOP=1 \
  -U "${POSTGRES_USER:-lidia}" \
  -d "${POSTGRES_DB:-proyecto_lidia}" \
  < "$PG_SNAPSHOT"

if [[ -n "$MONGO_SNAPSHOT" && -d "$MONGO_SNAPSHOT" ]]; then
  echo "[import] Restaurando MongoDB desde $MONGO_SNAPSHOT"
  if [[ -d "$MONGO_SNAPSHOT/dump" ]] && command -v mongorestore >/dev/null 2>&1; then
    mongorestore \
      --uri="mongodb://${MONGO_INITDB_ROOT_USERNAME:-lidia}:${MONGO_INITDB_ROOT_PASSWORD:-local_lidia}@localhost:${MONGO_PORT:-27027}/proyecto_lidia?authSource=admin" \
      --drop "$MONGO_SNAPSHOT/dump"
  elif [[ -d "$MONGO_SNAPSHOT/json" ]]; then
    LOCAL_MONGO_URI="mongodb://${MONGO_INITDB_ROOT_USERNAME:-lidia}:${MONGO_INITDB_ROOT_PASSWORD:-local_lidia}@localhost:${MONGO_PORT:-27027}/proyecto_lidia?authSource=admin" \
    MONGO_IMPORT_DIR="$MONGO_SNAPSHOT/json" "$PYTHON_BIN" - <<'PY'
import json
import os
from datetime import datetime
from pathlib import Path

from bson import ObjectId
from pymongo import MongoClient

uri = os.environ["LOCAL_MONGO_URI"]
root = Path(os.environ["MONGO_IMPORT_DIR"])
client = MongoClient(uri, serverSelectionTimeoutMS=5000)
try:
    db = client.get_default_database()
except Exception:
    db = client["proyecto_lidia"]

def decode(value):
    if isinstance(value, dict) and set(value) == {"$oid"}:
        return ObjectId(value["$oid"])
    if isinstance(value, dict) and set(value) == {"$date"}:
        try:
            return datetime.fromisoformat(value["$date"].replace("Z", "+00:00"))
        except ValueError:
            return value["$date"]
    if isinstance(value, dict):
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value

for path in sorted(root.glob("*.jsonl")):
    name = path.stem
    db[name].drop()
    docs = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                docs.append(decode(json.loads(line)))
    if docs:
        db[name].insert_many(docs)
    print({"collection": name, "documents": len(docs)})
PY
  else
    echo "[import] ADVERTENCIA: no hay dump/json MongoDB restaurable en $MONGO_SNAPSHOT"
  fi
else
  echo "[import] MONGO_SNAPSHOT no encontrado; se omite MongoDB."
fi

echo "[import] Validando estado restaurado"
bash scripts/local_validate_state.sh
echo "[import] Finalizado: $(date -Iseconds)"
