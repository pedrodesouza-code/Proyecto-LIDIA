#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$ROOT/evidencia/logs/backup_mongodb_final.log"
OUT="$ROOT/backups/mongo_lidia"
mkdir -p "$ROOT/evidencia/logs" "$ROOT/backups"

{
  echo "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "accion=backup_mongodb"
  if [ -f "$ROOT/config/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT/config/.env"
    set +a
  fi
  if [ -z "${MONGO_URI:-}" ]; then
    : "${MONGO_HOST:=localhost}"
    : "${MONGO_PORT:=27017}"
    : "${MONGO_DB:=proyecto_lidia}"
    : "${MONGO_AUTH_SOURCE:=admin}"
    if [ -n "${MONGO_USER:-}" ] && [ -n "${MONGO_PASSWORD:-}" ]; then
      MONGO_URI="mongodb://${MONGO_USER}:${MONGO_PASSWORD}@${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB}?authSource=${MONGO_AUTH_SOURCE}"
    else
      MONGO_URI="mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB}"
    fi
  fi
  echo "output=$OUT"
  echo "uri=***OCULTO***"
  mongodump --uri="$MONGO_URI" --out "$OUT"
  echo "estado=OK"
  echo "restore_documentado_no_ejecutado=mongorestore --uri=\"***OCULTO***\" backups/mongo_lidia/"
} 2>&1 | tee "$LOG"
