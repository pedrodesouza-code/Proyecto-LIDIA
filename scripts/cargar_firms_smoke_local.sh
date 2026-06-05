#!/usr/bin/env bash
set -euo pipefail

# Proyecto LIDIA EC3 - carga FIRMS smoke local contra PostgreSQL/MongoDB Docker.
# No usa UTEC/Jupyter. No modifica el alcance: solo URY, ARG y BRA.
# CHL u otros paises del origen se registran como fuera de alcance y se descartan
# por la normalizacion del ETL.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

LOG_DIR="evidencia/logs"
ENV_FILE="config/.env"
DOCKER_ENV=".env.docker.example"
LOAD_LOG="$LOG_DIR/carga_firms_smoke_local.log"
VALIDATION_LOG="$LOG_DIR/carga_firms_validaciones.log"
PROFILE_LOG="$LOG_DIR/firms_dataset_perfil.log"
OUT_OF_SCOPE_LOG="$LOG_DIR/firms_paises_fuera_alcance.log"
POSTGRES_COUNTS_LOG="$LOG_DIR/postgres_conteos_post_carga.log"
POSTGRES_SCOPE_LOG="$LOG_DIR/postgres_validacion_paises_alcance.log"
MONGO_STATE_LOG="$LOG_DIR/mongo_estado_post_carga.log"
MONGO_SCOPE_LOG="$LOG_DIR/mongo_validacion_paises_alcance.log"
FINAL_LOG="$LOG_DIR/validacion_final_entorno_local.log"

mkdir -p "$LOG_DIR" config

echo "[FIRMS] Buscando archivo FIRMS Parquet/CSV dentro del proyecto..."
FIRMS_FILE_FOUND="$(
  find "$PROJECT_ROOT" -type f \( \
      -iname "*firms*.parquet" -o -iname "*FIRMS*.parquet" \
      -o -iname "*firms*.pq" -o -iname "*FIRMS*.pq" \
      -o -iname "*firms*.csv" -o -iname "*FIRMS*.csv" \
    \) \
    -not -path "*/.git/*" \
    -not -path "*/_no_entregar/*" \
    | sort \
    | head -n 1
)"

if [[ -z "${FIRMS_FILE_FOUND}" ]]; then
  echo "[FIRMS] ERROR: No se encontró archivo FIRMS Parquet/CSV."
  echo "[FIRMS] Configure manualmente FIRMS_FILE en config/.env"
  echo "[FIRMS] Nota: el ETL actual soporta CSV y Parquet; shapefile requiere conversión previa."
  exit 1
fi

echo "[FIRMS] Archivo seleccionado: $FIRMS_FILE_FOUND"

# Ruta con comillas: compatible con bash source y python-dotenv.
touch "$ENV_FILE"
FIRMS_FILE_ENV_VALUE="${FIRMS_FILE_FOUND//\"/\\\"}"
if grep -q "^FIRMS_FILE=" "$ENV_FILE"; then
  sed -i "s|^FIRMS_FILE=.*|FIRMS_FILE=\"${FIRMS_FILE_ENV_VALUE}\"|" "$ENV_FILE"
else
  printf '\nFIRMS_FILE="%s"\n' "$FIRMS_FILE_ENV_VALUE" >> "$ENV_FILE"
fi
echo "[FIRMS] FIRMS_FILE actualizado en $ENV_FILE"

python3 - <<'PY'
import os
from pathlib import Path
from dotenv import dotenv_values

value = dotenv_values("config/.env").get("FIRMS_FILE", "")
path = Path(value)
print({"FIRMS_FILE": value, "exists": path.exists()})
if not path.exists():
    raise SystemExit("FIRMS_FILE no existe despues de configurar config/.env")
PY

echo "[FIRMS] Perfilando dataset origen..."
FIRMS_PROFILE_JSON="$(
python3 - <<'PY' "$FIRMS_FILE_FOUND" "$PROFILE_LOG" "$OUT_OF_SCOPE_LOG"
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

source = Path(sys.argv[1])
profile_log = Path(sys.argv[2])
out_log = Path(sys.argv[3])
allowed = {"URY", "ARG", "BRA"}

if source.suffix.lower() in {".parquet", ".pq"}:
    df = pd.read_parquet(source)
elif source.suffix.lower() == ".csv":
    df = pd.read_csv(source)
else:
    raise SystemExit("FIRMS_FILE debe ser CSV o Parquet")

date_col = "fecha_adq" if "fecha_adq" in df.columns else "acq_date"
country_col = "pais" if "pais" in df.columns else "pais_codigo"
dates = pd.to_datetime(df[date_col], errors="coerce")
countries = df[country_col].astype("string").str.upper().fillna("NA")
in_scope = df[countries.isin(allowed)].copy()
in_scope_dates = pd.to_datetime(in_scope[date_col], errors="coerce")

profile = {
    "archivo": str(source),
    "filas": int(len(df)),
    "columnas": list(df.columns),
    "fecha_columna": date_col,
    "fecha_min": None if dates.dropna().empty else str(dates.min().date()),
    "fecha_max": None if dates.dropna().empty else str(dates.max().date()),
    "conteo_por_pais": {str(k): int(v) for k, v in countries.value_counts(dropna=False).sort_index().items()},
    "conteo_por_anio": {str(int(k)): int(v) for k, v in dates.dt.year.value_counts(dropna=True).sort_index().items()},
    "nulos_columnas_clave": {
        col: int(df[col].isna().sum()) for col in [
            "latitud", "longitud", "fecha_adq", "hora_adq_hhmm", "pais", "potencia_radiativa", "brillo_ti4"
        ] if col in df.columns
    },
}
out_scope = countries[~countries.isin(allowed)].value_counts(dropna=False).sort_index()
out_scope_payload = {
    "permitidos": sorted(allowed),
    "fuera_alcance": {str(k): int(v) for k, v in out_scope.items()},
    "nota": "CHL corresponde a Chile y se descarta porque no pertenece al alcance Proyecto LIDIA.",
}

preferred_start = pd.Timestamp("2026-05-01")
preferred_end = pd.Timestamp("2026-05-31")
preferred_rows = in_scope[(in_scope_dates >= preferred_start) & (in_scope_dates <= preferred_end)]
if len(preferred_rows) > 0:
    start = preferred_start.date().isoformat()
    end = preferred_end.date().isoformat()
else:
    valid_dates = in_scope_dates.dropna()
    if valid_dates.empty:
        raise SystemExit("No hay fechas validas dentro de URY/ARG/BRA")
    start = valid_dates.min().date().isoformat()
    end = valid_dates.max().date().isoformat()

profile["rango_smoke_seleccionado"] = {"start_date": start, "end_date": end, "filas_preferidas": int(len(preferred_rows))}

profile_log.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
out_log.write_text(json.dumps(out_scope_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"start_date": start, "end_date": end, "out_of_scope": out_scope_payload["fuera_alcance"]}, ensure_ascii=False))
PY
)"
echo "$FIRMS_PROFILE_JSON"
START_DATE="$(python3 - <<'PY' "$FIRMS_PROFILE_JSON"
import json, sys
print(json.loads(sys.argv[1])["start_date"])
PY
)"
END_DATE="$(python3 - <<'PY' "$FIRMS_PROFILE_JSON"
import json, sys
print(json.loads(sys.argv[1])["end_date"])
PY
)"

if [[ -f "$DOCKER_ENV" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$DOCKER_ENV"
  set +a
else
  echo "[FIRMS] ADVERTENCIA: no existe $DOCKER_ENV"
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

export PYTHONPATH="$PROJECT_ROOT"

# Ejecucion local contra servicios Docker publicados.
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="${POSTGRES_PORT:-15432}"
export POSTGRES_DB="${POSTGRES_DB:-proyecto_lidia}"
export LIDIA_POSTGRES_DB="${POSTGRES_DB}"
export POSTGRES_USER="${POSTGRES_USER:-lidia}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-local_lidia}"
export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"

export MONGO_HOST="localhost"
export MONGO_PORT="${MONGO_PORT:-27027}"
export MONGO_DB="proyecto_lidia"
export MONGO_USER="${MONGO_USER:-${MONGO_INITDB_ROOT_USERNAME:-lidia}}"
export MONGO_PASSWORD="${MONGO_PASSWORD:-${MONGO_INITDB_ROOT_PASSWORD:-local_lidia}}"
export MONGO_AUTH_SOURCE="admin"
export MONGO_URI="mongodb://${MONGO_USER}:${MONGO_PASSWORD}@localhost:${MONGO_PORT}/${MONGO_DB}?authSource=admin"
export MONGO_ENABLED="true"

echo "[DOCKER] Levantando PostgreSQL y MongoDB locales..."
docker compose --env-file "$DOCKER_ENV" up -d postgres mongo --remove-orphans

echo "[POSTGRES] Validando conexión local localhost:${POSTGRES_PORT}..."
docker compose --env-file "$DOCKER_ENV" exec -T postgres \
  psql -U lidia -d proyecto_lidia \
  -c "SELECT current_database(), current_user;"

echo "[MONGO] Esperando y validando conexión local localhost:${MONGO_PORT}..."
MONGO_STATUS="advertencia"
for attempt in {1..20}; do
  if docker compose --env-file "$DOCKER_ENV" exec -T mongo \
    mongosh -u "$MONGO_USER" -p "$MONGO_PASSWORD" \
    --authenticationDatabase admin \
    --eval 'db.adminCommand({ ping: 1 })' >/tmp/lidia_mongo_ping.log 2>&1; then
    cat /tmp/lidia_mongo_ping.log
    MONGO_STATUS="ok"
    break
  fi
  sleep 2
done
if [[ "$MONGO_STATUS" != "ok" ]]; then
  cat /tmp/lidia_mongo_ping.log || true
  echo "[MONGO] ADVERTENCIA: MongoDB no pudo validarse. Se continúa con PostgreSQL y ETL si corresponde."
fi

echo "[LOCAL-DB] Preparando DDL PostgreSQL y colecciones Mongo locales..."
bash scripts/cargar_bases_local_docker.sh

echo "[ETL] Ejecutando carga controlada FIRMS para URY/ARG/BRA entre ${START_DATE} y ${END_DATE}..."
{
  python3 -u etl/main.py \
    --source FIRMS \
    --start-date "$START_DATE" \
    --end-date "$END_DATE" \
    --countries URY ARG BRA \
    --max-records-per-source 1000
} 2>&1 | tee "$LOAD_LOG"

python3 - <<'PY' "$LOAD_LOG"
import json
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="ignore")
loaded = 0
unchanged = 0
for line in text.splitlines():
    try:
        event = json.loads(line)
    except Exception:
        continue
    if event.get("fuente") == "FIRMS" and event.get("etapa") == "load" and event.get("estado") == "ok":
        loaded = int(event.get("filas_insertadas") or 0) + int(event.get("filas_actualizadas") or 0)
        unchanged = int(event.get("filas_sin_cambio") or event.get("sin_cambio") or 0)
if loaded <= 0 and unchanged <= 0:
    raise SystemExit("La carga FIRMS no puede declararse exitosa: filas insertadas/actualizadas/sin_cambio = 0")
print({"filas_cargadas_o_actualizadas": loaded, "filas_sin_cambio": unchanged})
PY

echo "[POSTGRES] Guardando conteos post carga..."
docker compose --env-file "$DOCKER_ENV" exec -T postgres psql -U lidia -d proyecto_lidia -c "
SELECT 'staging.stg_firms' AS tabla, COUNT(*)::bigint AS filas FROM staging.stg_firms
UNION ALL SELECT 'staging.rechazos_etl', COUNT(*) FROM staging.rechazos_etl
UNION ALL SELECT 'audit.etl_runs', COUNT(*) FROM audit.etl_runs
UNION ALL SELECT 'audit.cdc_eventos', COUNT(*) FROM audit.cdc_eventos
UNION ALL SELECT 'dw.fact_incendio', COUNT(*) FROM dw.fact_incendio;
" 2>&1 | tee "$POSTGRES_COUNTS_LOG"

docker compose --env-file "$DOCKER_ENV" exec -T postgres psql -U lidia -d proyecto_lidia -c "
WITH paises AS (
  SELECT pais_codigo::text AS pais_codigo, COUNT(*)::bigint AS filas, 'staging.stg_firms' AS origen
  FROM staging.stg_firms GROUP BY pais_codigo
  UNION ALL
  SELECT u.pais_codigo::text, COUNT(*)::bigint, 'dw.fact_incendio'
  FROM dw.fact_incendio f JOIN dw.dim_ubicacion u ON u.ubicacion_id=f.ubicacion_id
  GROUP BY u.pais_codigo
)
SELECT * FROM paises ORDER BY origen, pais_codigo;
SELECT COUNT(*)::bigint AS paises_fuera_alcance
FROM staging.stg_firms
WHERE pais_codigo NOT IN ('URY','ARG','BRA');
" 2>&1 | tee "$POSTGRES_SCOPE_LOG"

if docker compose --env-file "$DOCKER_ENV" exec -T postgres psql -U lidia -d proyecto_lidia -Atc \
  "SELECT COUNT(*) FROM staging.stg_firms WHERE pais_codigo NOT IN ('URY','ARG','BRA');" | grep -v '^$' | grep -vq '^0$'; then
  echo "[POSTGRES] ERROR: existen paises fuera del alcance en staging.stg_firms" | tee -a "$POSTGRES_SCOPE_LOG"
  exit 1
fi

echo "[MONGO] Guardando estado post carga..."
if [[ "$MONGO_STATUS" == "ok" ]]; then
  echo "[MONGO] Creando snapshots FIRMS derivados de PostgreSQL local..."
  while IFS='|' read -r pais total; do
    [[ -z "${pais}" || -z "${total}" ]] && continue
    docker compose --env-file "$DOCKER_ENV" exec -T mongo mongosh -u "$MONGO_USER" -p "$MONGO_PASSWORD" \
      --authenticationDatabase admin proyecto_lidia --eval "
        db.snapshots_firms.replaceOne(
          {fecha: new Date('${START_DATE}T00:00:00Z'), pais_codigo: '${pais}'},
          {
            fecha: new Date('${START_DATE}T00:00:00Z'),
            pais_codigo: '${pais}',
            total_focos: NumberInt(${total}),
            resumen: {
              fuente: 'FIRMS',
              tipo: 'snapshot_derivado_postgresql_local',
              rango_inicio: '${START_DATE}',
              rango_fin: '${END_DATE}',
              brightness_descripcion: 'brillo_termico_pixel_satelital'
            }
          },
          {upsert: true}
        )
      " >/dev/null
  done < <(
    docker compose --env-file "$DOCKER_ENV" exec -T postgres psql -U lidia -d proyecto_lidia -At -F '|' -c "
      SELECT pais_codigo, COUNT(*)::int
      FROM staging.stg_firms
      WHERE pais_codigo IN ('URY','ARG','BRA')
      GROUP BY pais_codigo
      ORDER BY pais_codigo;
    "
  )

  docker compose --env-file "$DOCKER_ENV" exec -T mongo mongosh -u "$MONGO_USER" -p "$MONGO_PASSWORD" \
    --authenticationDatabase admin proyecto_lidia --eval '
      printjson({
        database: db.getName(),
        collections: db.getCollectionNames().sort(),
        counts: Object.fromEntries(db.getCollectionNames().sort().map(c => [c, db.getCollection(c).countDocuments()]))
      })
    ' 2>&1 | tee "$MONGO_STATE_LOG"

  docker compose --env-file "$DOCKER_ENV" exec -T mongo mongosh -u "$MONGO_USER" -p "$MONGO_PASSWORD" \
    --authenticationDatabase admin proyecto_lidia --eval '
      const allowed = ["URY", "ARG", "BRA"];
      const collections = db.getCollectionNames();
      const result = {};
      for (const c of collections) {
        const query = {$or: [
          {pais: {$exists: true, $nin: allowed}},
          {pais_codigo: {$exists: true, $nin: allowed}},
          {"payload.pais": {$exists: true, $nin: allowed}},
          {"payload.pais_codigo": {$exists: true, $nin: allowed}},
          {"registro.pais": {$exists: true, $nin: allowed}},
          {"registro.pais_codigo": {$exists: true, $nin: allowed}}
        ]};
        result[c] = db.getCollection(c).countDocuments(query);
      }
      printjson(result);
    ' 2>&1 | tee "$MONGO_SCOPE_LOG"
else
  echo "MongoDB no validado; no se consultan colecciones." | tee "$MONGO_STATE_LOG" "$MONGO_SCOPE_LOG"
fi

echo "[VALIDACION] Ejecutando validaciones finales..."
{
  echo "[VALIDACION] python3 -m compileall -q ."
  python3 -m compileall -q .

  echo "[VALIDACION] python3 -m pytest -q tests"
  python3 -m pytest -q tests

  echo "[VALIDACION] python3 scripts/ec3_verificar_logrado.py"
  python3 scripts/ec3_verificar_logrado.py
} 2>&1 | tee "$VALIDATION_LOG" "$FINAL_LOG"

echo ""
echo "# Resumen carga FIRMS smoke local"
echo "- Archivo FIRMS usado: $FIRMS_FILE_FOUND"
echo "- Rango smoke usado: $START_DATE a $END_DATE"
echo "- Archivo de configuración: $ENV_FILE"
echo "- PostgreSQL: validado en localhost:${POSTGRES_PORT}"
echo "- MongoDB: $MONGO_STATUS en localhost:${MONGO_PORT}"
echo "- Perfil FIRMS: $PROFILE_LOG"
echo "- Paises fuera de alcance: $OUT_OF_SCOPE_LOG"
echo "- Log de carga: $LOAD_LOG"
echo "- Conteos PostgreSQL: $POSTGRES_COUNTS_LOG"
echo "- Validación países PostgreSQL: $POSTGRES_SCOPE_LOG"
echo "- Estado MongoDB: $MONGO_STATE_LOG"
echo "- Validación países MongoDB: $MONGO_SCOPE_LOG"
echo "- Log de validaciones: $VALIDATION_LOG"
echo ""
echo "[FIRMS] Proceso finalizado."
