#!/bin/bash
# =============================================================================
# SINIA-UY — Script de despliegue en servidor UTEC
# =============================================================================
# Uso: bash scripts/deploy.sh
# Ejecutar desde la raíz del proyecto (/opt/sinia-uy o equivalente).
# =============================================================================

set -e   # cualquier error aborta el script
set -u   # variables sin definir abortan el script

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> 1/6 Verificando que estamos en main"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "ERROR: estás en la rama '$CURRENT_BRANCH', no en main. Abortando."
    exit 1
fi

echo "==> 2/6 Pull desde origin/main"
git fetch origin
git pull origin main

echo "==> 3/6 Activando venv y actualizando dependencias Python"
if [ ! -d ".venv" ]; then
    echo "ERROR: no existe .venv. Corré primero: python3.11 -m venv .venv"
    exit 1
fi
source .venv/bin/activate
pip install -r requirements.txt --quiet

echo "==> 4/6 Reiniciando contenedores Docker"
cd docker
docker compose pull
docker compose up -d --build
docker compose ps
cd ..

echo "==> 5/6 Reiniciando scheduler (si existe el servicio)"
if systemctl list-unit-files | grep -q sinia-scheduler.service; then
    sudo systemctl restart sinia-scheduler
    sudo systemctl status sinia-scheduler --no-pager
else
    echo "    (servicio sinia-scheduler no encontrado, salto este paso)"
fi

echo "==> 6/6 Validando tests de calidad"
python tests/test_calidad_datos.py || {
    echo "AVISO: tests fallaron. Revisar tests/resultados_tests.json"
    exit 2
}

echo ""
echo "============================================="
echo "Deploy completo — $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================="
