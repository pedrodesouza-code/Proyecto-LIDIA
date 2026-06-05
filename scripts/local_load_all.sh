#!/usr/bin/env bash
set -euo pipefail

# Proyecto LIDIA - carga local idempotente sin borrar datos existentes.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LOG_DIR="evidencia/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/local_load_all.log"

if [[ "${LIDIA_LOCAL_LOAD_LOGGING:-0}" != "1" ]]; then
  export LIDIA_LOCAL_LOAD_LOGGING=1
  bash "$0" "$@" 2>&1 | tee "$LOG_FILE"
  exit "${PIPESTATUS[0]}"
fi

echo "[local-load] $(date -Iseconds)"
echo "[local-load] Comando: bash scripts/local_load_all.sh"
CONFIRM_RESET=0 bash scripts/cargar_todos_datos_locales.sh
echo "[local-load] Finalizado: $(date -Iseconds)"
