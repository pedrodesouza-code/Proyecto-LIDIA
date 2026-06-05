#!/usr/bin/env bash
set -euo pipefail

# Proyecto LIDIA - reconstruccion local desde datos procesados reales.
# Requiere CONFIRM_RESET=1 porque borra esquemas locales staging/dw/audit.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LOG_DIR="evidencia/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/local_reset_and_load.log"

if [[ "${CONFIRM_RESET:-0}" != "1" ]]; then
  echo "[local-reset] ERROR: esta operacion borra esquemas locales staging/dw/audit."
  echo "[local-reset] Ejecute: CONFIRM_RESET=1 bash scripts/local_reset_and_load.sh"
  exit 1
fi

if [[ "${LIDIA_LOCAL_RESET_LOGGING:-0}" != "1" ]]; then
  export LIDIA_LOCAL_RESET_LOGGING=1
  bash "$0" "$@" 2>&1 | tee "$LOG_FILE"
  exit "${PIPESTATUS[0]}"
fi

echo "[local-reset] $(date -Iseconds)"
echo "[local-reset] Comando: CONFIRM_RESET=1 bash scripts/local_reset_and_load.sh"
CONFIRM_RESET=1 bash scripts/cargar_todos_datos_locales.sh
echo "[local-reset] Finalizado: $(date -Iseconds)"
