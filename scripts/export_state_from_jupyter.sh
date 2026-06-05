#!/usr/bin/env bash
set -euo pipefail

# Proyecto LIDIA - export de snapshot desde Jupyter/UTEC o cualquier entorno
# con DATABASE_URL y opcionalmente MONGO_URI configurados.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="evidencia/logs"
PG_DIR="backups/postgres"
MONGO_DIR="backups/mongo/${TS}"
mkdir -p "$LOG_DIR" "$PG_DIR" "$MONGO_DIR"
LOG_FILE="$LOG_DIR/export_state_from_jupyter_${TS}.log"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ "${LIDIA_EXPORT_LOGGING:-0}" != "1" ]]; then
  export LIDIA_EXPORT_LOGGING=1
  bash "$0" "$@" 2>&1 | sed -E \
    -e 's#(postgresql://[^:]+:)[^@]+@#\1***@#g' \
    -e 's#(mongodb://[^:]+:)[^@]+@#\1***@#g' | tee "$LOG_FILE"
  exit "${PIPESTATUS[0]}"
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[export] ERROR: DATABASE_URL no esta definida."
  exit 1
fi

PG_SNAPSHOT="$PG_DIR/proyecto_lidia_${TS}.sql"
echo "[export] $(date -Iseconds)"
echo "[export] Exportando PostgreSQL a $PG_SNAPSHOT"
if ! command -v pg_dump >/dev/null 2>&1; then
  echo "[export] ERROR: pg_dump no esta disponible en este entorno."
  exit 1
fi
pg_dump "$DATABASE_URL" --clean --if-exists --no-owner --no-privileges > "$PG_SNAPSHOT"

echo "[export] PostgreSQL snapshot generado:"
ls -lh "$PG_SNAPSHOT"

if [[ -n "${MONGO_URI:-}" ]]; then
  if command -v mongodump >/dev/null 2>&1; then
    echo "[export] mongodump disponible; exportando dump BSON a $MONGO_DIR/dump"
    mongodump --uri="$MONGO_URI" --out="$MONGO_DIR/dump"
  else
    echo "[export] mongodump no disponible; exportando colecciones MongoDB como JSON con pymongo."
    MONGO_EXPORT_DIR="$MONGO_DIR/json" "$PYTHON_BIN" - <<'PY'
import json
import os
from datetime import datetime, date
from pathlib import Path

from bson import ObjectId
from pymongo import MongoClient

uri = os.environ["MONGO_URI"]
out = Path(os.environ["MONGO_EXPORT_DIR"])
out.mkdir(parents=True, exist_ok=True)
client = MongoClient(uri, serverSelectionTimeoutMS=5000)
try:
    db = client.get_default_database()
except Exception:
    db = client["proyecto_lidia"]

def encode(value):
    if isinstance(value, ObjectId):
        return {"$oid": str(value)}
    if isinstance(value, datetime):
        return {"$date": value.isoformat()}
    if isinstance(value, date):
        return {"$date": value.isoformat()}
    return str(value)

manifest = {"database": db.name, "collections": {}}
for name in sorted(db.list_collection_names()):
    path = out / f"{name}.jsonl"
    count = 0
    with path.open("w", encoding="utf-8") as fh:
        for doc in db[name].find({}):
            fh.write(json.dumps(doc, default=encode, ensure_ascii=False) + "\n")
            count += 1
    manifest["collections"][name] = {"documents": count, "file": path.name}
(out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(manifest, ensure_ascii=False, indent=2))
PY
  fi
else
  echo "[export] MONGO_URI no definida; se omite snapshot MongoDB."
fi

echo "[export] Finalizado. Snapshots:"
echo "- PostgreSQL: $PG_SNAPSHOT"
echo "- MongoDB: $MONGO_DIR"
