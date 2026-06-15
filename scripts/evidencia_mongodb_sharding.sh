#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$ROOT/evidencia/logs/mongodb_sharding_final.log"
mkdir -p "$ROOT/evidencia/logs"

{
  echo "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "accion=evidencia_sharding_mongodb_local_academica"
  if [ ! -f "$ROOT/docker-compose.sharding.yml" ]; then
    echo "estado=NO_APLICA"
    echo "motivo=docker-compose.sharding.yml no existe"
    exit 0
  fi
  echo "estado=configuracion_encontrada"
  docker compose -f "$ROOT/docker-compose.yml" -f "$ROOT/docker-compose.sharding.yml" ps
  echo "=== sh.status() ==="
  docker compose -f "$ROOT/docker-compose.yml" -f "$ROOT/docker-compose.sharding.yml" exec -T mongo \
    mongosh --quiet --eval 'sh.status()'
  echo "=== distribucion eventos_enriquecidos ==="
  docker compose -f "$ROOT/docker-compose.yml" -f "$ROOT/docker-compose.sharding.yml" exec -T mongo \
    mongosh --quiet proyecto_lidia --eval 'db.eventos_enriquecidos.getShardDistribution()'
  echo "nota=Evidencia local academica; no se declara sharding productivo ni institucional."
} 2>&1 | tee "$LOG"
