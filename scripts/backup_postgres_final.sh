#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$ROOT/evidencia/logs/backup_postgres_final.log"
OUT="$ROOT/backups/proyecto_lidia.dump"
mkdir -p "$ROOT/evidencia/logs" "$ROOT/backups"

{
  echo "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "accion=backup_postgres"
  if [ -f "$ROOT/config/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT/config/.env"
    set +a
  fi
  : "${POSTGRES_HOST:=localhost}"
  : "${POSTGRES_PORT:=15432}"
  : "${POSTGRES_DB:=${LIDIA_POSTGRES_DB:-proyecto_lidia}}"
  : "${POSTGRES_USER:=lidia}"
  if [ -z "${POSTGRES_PASSWORD:-}" ]; then
    echo "estado=ERROR"
    echo "error=POSTGRES_PASSWORD no definido"
    exit 1
  fi
  echo "host=$POSTGRES_HOST"
  echo "port=$POSTGRES_PORT"
  echo "database=$POSTGRES_DB"
  echo "user=$POSTGRES_USER"
  echo "output=$OUT"
  PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -Fc \
    -f "$OUT"
  echo "estado=OK"
  echo "restore_documentado_no_ejecutado=pg_restore -h <host> -p <puerto> -U <user> -d proyecto_lidia --clean backups/proyecto_lidia.dump"
} 2>&1 | tee "$LOG"
