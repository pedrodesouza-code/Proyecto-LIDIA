#!/usr/bin/env bash
set -Eeuo pipefail

if [ "${CONFIRM_RESTORE:-}" != "1" ]; then
  echo "ERROR: para restaurar MongoDB usá CONFIRM_RESTORE=1"
  exit 1
fi

if [ -z "${MONGO_BACKUP_DIR:-}" ]; then
  echo "ERROR: falta MONGO_BACKUP_DIR"
  echo "Ejemplo:"
  echo "MONGO_BACKUP_DIR='backups/mongo/jupyter_mongo_jsonl_20260605_140146' CONFIRM_RESTORE=1 bash scripts/import_mongo_jsonl_to_local.sh"
  exit 1
fi

if [ ! -d "$MONGO_BACKUP_DIR" ]; then
  echo "ERROR: no existe el directorio $MONGO_BACKUP_DIR"
  exit 1
fi

if [ -f ".env.docker.example" ]; then
  set -a
  source .env.docker.example
  set +a
fi

MONGO_SERVICE="${MONGO_SERVICE:-mongo}"
MONGO_DB="${MONGO_DB:-${MONGO_INITDB_DATABASE:-proyecto_lidia}}"

MONGO_USER="${MONGO_USER:-${MONGO_INITDB_ROOT_USERNAME:-}}"
MONGO_PASSWORD="${MONGO_PASSWORD:-${MONGO_INITDB_ROOT_PASSWORD:-}}"
MONGO_AUTH_DB="${MONGO_AUTH_DB:-admin}"

AUTH_ARGS=()
if [ -n "$MONGO_USER" ] && [ -n "$MONGO_PASSWORD" ]; then
  AUTH_ARGS+=(--username "$MONGO_USER")
  AUTH_ARGS+=(--password "$MONGO_PASSWORD")
  AUTH_ARGS+=(--authenticationDatabase "$MONGO_AUTH_DB")
fi

echo "=== IMPORT MONGODB JSONL LOCAL ==="
echo "Backup: $MONGO_BACKUP_DIR"
echo "Servicio Mongo: $MONGO_SERVICE"
echo "Base destino: $MONGO_DB"
echo "Auth DB: $MONGO_AUTH_DB"
if [ -n "$MONGO_USER" ]; then
  echo "Usuario Mongo: $MONGO_USER"
else
  echo "Usuario Mongo: sin autenticación"
fi

for file in "$MONGO_BACKUP_DIR"/*.jsonl.gz; do
  [ -e "$file" ] || continue

  coll="$(basename "$file" .jsonl.gz)"

  echo "Importando colección: $coll"

  gzip -dc "$file" | docker compose --env-file .env.docker.example exec -T "$MONGO_SERVICE" \
    mongoimport \
      --host localhost \
      --port 27017 \
      "${AUTH_ARGS[@]}" \
      --db "$MONGO_DB" \
      --collection "$coll" \
      --drop \
      --mode insert
done

echo "=== IMPORT MONGODB FINALIZADO ==="
