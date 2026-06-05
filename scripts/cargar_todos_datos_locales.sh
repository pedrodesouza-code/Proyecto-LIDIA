#!/usr/bin/env bash
set -euo pipefail

# Proyecto LIDIA EC3 - carga completa local de datos reales disponibles.
# Usa PostgreSQL local Docker como DW principal. MongoDB se usa como capa
# documental complementaria con metadata/logs/snapshots derivados; no se cargan
# millones de documentos raw.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

LOG_DIR="evidencia/logs"
LOG_FILE="$LOG_DIR/carga_completa_local.log"
ENV_FILE="config/.env"
DOCKER_ENV=".env.docker"
if [[ ! -f "$DOCKER_ENV" ]]; then
  DOCKER_ENV=".env.docker.example"
fi

mkdir -p "$LOG_DIR" config

mask() {
  sed -E \
    -e 's#(postgresql://[^:]+:)[^@]+@#\1***@#g' \
    -e 's#(mongodb://[^:]+:)[^@]+@#\1***@#g' \
    -e 's#(POSTGRES_PASSWORD=).+#\1***#g' \
    -e 's#(MONGO_INITDB_ROOT_PASSWORD=).+#\1***#g' \
    -e 's#(--password )[A-Za-z0-9_.-]+#\1***#g' \
    -e 's#(-p )[A-Za-z0-9_.-]+#\1***#g'
}

if [[ "${LIDIA_CARGA_COMPLETA_LOGGING:-0}" != "1" ]]; then
  export LIDIA_CARGA_COMPLETA_LOGGING=1
  bash "$0" "$@" 2>&1 | mask | tee "$LOG_FILE"
  exit "${PIPESTATUS[0]}"
fi

require_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    echo "[carga-completa] ADVERTENCIA: no existe $label en $path; fuente omitida."
    return 1
  fi
  return 0
}

upsert_env() {
  local key="$1"
  local value="$2"
  local escaped="${value//\"/\\\"}"
  touch "$ENV_FILE"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=\"${escaped}\"|" "$ENV_FILE"
  else
    printf '%s="%s"\n' "$key" "$escaped" >> "$ENV_FILE"
  fi
}

if ! command -v docker >/dev/null 2>&1; then
  echo "[carga-completa] ERROR: Docker no esta disponible en esta terminal."
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$DOCKER_ENV"
set +a

COMPOSE=(docker compose --env-file "$DOCKER_ENV" -f docker-compose.yml)
export PAGER=cat
export PSQL_PAGER=cat

FIRMS_FILE_PATH="$PROJECT_ROOT/data/processed/firms_procesado.parquet"
[[ -f "$FIRMS_FILE_PATH" ]] || FIRMS_FILE_PATH="$PROJECT_ROOT/data/processed/firms_nrt_procesado.parquet"
METEO_FILE_PATH="$PROJECT_ROOT/data/processed/meteo_procesado_todos.parquet"
CAMS_FILE_PATH="$PROJECT_ROOT/data/processed/cams_procesado_todos.parquet"
[[ -f "$CAMS_FILE_PATH" ]] || CAMS_FILE_PATH="$PROJECT_ROOT/data/processed/cams_nrt_procesado.parquet"
CHIRPS_FILE_PATH="$PROJECT_ROOT/data/processed/chirps_sa.parquet"
MODIS_FILE_PATH="$PROJECT_ROOT/data/processed/modis_lc.parquet"

SOURCES_TO_LOAD=()
if require_file "$FIRMS_FILE_PATH" "FIRMS"; then
  upsert_env FIRMS_FILE "$FIRMS_FILE_PATH"
  SOURCES_TO_LOAD+=("FIRMS")
fi
if require_file "$METEO_FILE_PATH" "METEO/Open-Meteo"; then
  upsert_env METEO_FILE "$METEO_FILE_PATH"
  SOURCES_TO_LOAD+=("METEO")
fi
if require_file "$CAMS_FILE_PATH" "CAMS/Open-Meteo Air Quality"; then
  upsert_env CAMS_FILE "$CAMS_FILE_PATH"
  SOURCES_TO_LOAD+=("CAMS")
fi
if require_file "$CHIRPS_FILE_PATH" "CHIRPS"; then
  upsert_env CHIRPS_FILE "$CHIRPS_FILE_PATH"
  SOURCES_TO_LOAD+=("CHIRPS")
fi
if require_file "$MODIS_FILE_PATH" "MODIS"; then
  upsert_env MODIS_FILE "$MODIS_FILE_PATH"
  SOURCES_TO_LOAD+=("MODIS")
fi

if grep -q '^INUMET_FILE=' "$ENV_FILE" && [[ -n "$(grep '^INUMET_FILE=' "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d '"')" ]]; then
  SOURCES_TO_LOAD+=("INUMET")
else
  echo "[carga-completa] INUMET omitido: no hay INUMET_FILE real configurado."
fi

if [[ "${#SOURCES_TO_LOAD[@]}" -eq 0 ]]; then
  echo "[carga-completa] ERROR: no hay fuentes reales disponibles para cargar."
  exit 1
fi

echo "[carga-completa] Fuentes a cargar: ${SOURCES_TO_LOAD[*]}"
echo "[carga-completa] Nota: CHL/Chile queda fuera del alcance y sera rechazado/descartado por restricciones URY/ARG/BRA."

echo "[carga-completa] Levantando PostgreSQL y MongoDB locales..."
"${COMPOSE[@]}" up -d --wait postgres mongo --remove-orphans

if [[ "${CONFIRM_RESET:-0}" == "1" ]]; then
  echo "[carga-completa] CONFIRM_RESET=1 detectado: reiniciando esquemas locales staging/dw/audit."
  "${COMPOSE[@]}" exec -T postgres psql -v ON_ERROR_STOP=1 \
    -P pager=off \
    -U "${POSTGRES_USER:-lidia}" \
    -d "${POSTGRES_DB:-proyecto_lidia}" \
    -c "DROP SCHEMA IF EXISTS staging CASCADE; DROP SCHEMA IF EXISTS dw CASCADE; DROP SCHEMA IF EXISTS audit CASCADE;"
else
  echo "[carga-completa] Sin reset: se preservan datos existentes y se aplican cargas idempotentes."
  echo "[carga-completa] Para borrar y reconstruir desde cero use CONFIRM_RESET=1."
fi

echo "[carga-completa] Recreando estructuras SQL/NoSQL locales..."
{
  for sql_file in \
    sql/ddl/00_schemas.sql \
    sql/ddl/01_roles.sql \
    sql/ddl/02_Schema.sql \
    sql/ddl/03_indices.sql \
    sql/ddl/04_vistas.sql
  do
    echo "== ${sql_file} =="
    "${COMPOSE[@]}" exec -T postgres psql \
      -v ON_ERROR_STOP=1 \
      -P pager=off \
      -U "${POSTGRES_USER:-lidia}" \
      -d "${POSTGRES_DB:-proyecto_lidia}" \
      < "$sql_file"
  done
} 2>&1 | tee "$LOG_DIR/carga_completa_ddl.log"

echo "[carga-completa] Creando colecciones MongoDB locales..."
LIDIA_LOCAL_DB_SKIP_DDL=1 bash scripts/cargar_bases_local_docker.sh >/tmp/lidia_local_db_setup.log 2>&1
cat /tmp/lidia_local_db_setup.log | grep -E 'local-db|database|collections|counts|Listo|ERROR|ADVERTENCIA' || true

export PYTHONPATH="$PROJECT_ROOT"
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="${POSTGRES_PORT:-15432}"
export POSTGRES_DB="${POSTGRES_DB:-proyecto_lidia}"
export LIDIA_POSTGRES_DB="$POSTGRES_DB"
export POSTGRES_USER="${POSTGRES_USER:-lidia}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-local_lidia}"
export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"
export MONGO_HOST="localhost"
export MONGO_PORT="${MONGO_PORT:-27027}"
export MONGO_DB="proyecto_lidia"
export MONGO_USER="${MONGO_INITDB_ROOT_USERNAME:-lidia}"
export MONGO_PASSWORD="${MONGO_INITDB_ROOT_PASSWORD:-local_lidia}"
export MONGO_AUTH_SOURCE="admin"
export MONGO_URI="mongodb://${MONGO_USER}:${MONGO_PASSWORD}@localhost:${MONGO_PORT}/${MONGO_DB}?authSource=admin"
export MONGO_ENABLED="false"
unset LIDIA_MAX_RECORDS_PER_SOURCE

for source in "${SOURCES_TO_LOAD[@]}"; do
  echo
  echo "[carga-completa] Cargando fuente real ${source}..."
  python3 -u etl/main.py --source "$source" --countries URY ARG BRA --skip-mongo \
    2>&1 | tee "$LOG_DIR/carga_completa_${source,,}.log"
done

echo "[carga-completa] Asociando dimensiones ambientales por proximidad espacial/temporal si hay datos..."
python3 - <<'PY' 2>&1 | tee "evidencia/logs/carga_completa_asociacion_ambiental.log"
from etl.load.postgres import associate_environmental_dimensions
print(associate_environmental_dimensions())
PY

echo "[carga-completa] Insertando metadata y snapshots reales en MongoDB local..."
"${COMPOSE[@]}" exec -T mongo mongosh --quiet \
  --username "${MONGO_INITDB_ROOT_USERNAME:-lidia}" \
  --password "${MONGO_INITDB_ROOT_PASSWORD:-local_lidia}" \
  --authenticationDatabase admin \
  proyecto_lidia --eval 'db.ingesta_metadata.deleteMany({modo: "carga_completa_local"}); db.pipeline_logs.deleteMany({modo: "carga_completa_local"}); db.snapshots_firms.deleteMany({"resumen.modo": "carga_completa_local"});'

while IFS='|' read -r fuente leidas insertadas actualizadas rechazadas estado; do
  [[ -z "${fuente}" ]] && continue
  "${COMPOSE[@]}" exec -T mongo mongosh --quiet \
    --username "${MONGO_INITDB_ROOT_USERNAME:-lidia}" \
    --password "${MONGO_INITDB_ROOT_PASSWORD:-local_lidia}" \
    --authenticationDatabase admin proyecto_lidia --eval "
      db.ingesta_metadata.insertOne({
        run_id: 'local-completa-${fuente}',
        fuente: '${fuente}',
        estado: '${estado}',
        metricas: {
          filas_leidas: NumberInt(${leidas}),
          filas_insertadas: NumberInt(${insertadas}),
          filas_actualizadas: NumberInt(${actualizadas}),
          filas_rechazadas: NumberInt(${rechazadas})
        },
        modo: 'carga_completa_local',
        registrado_en: new Date()
      });
      db.pipeline_logs.insertOne({
        run_id: 'local-completa-${fuente}',
        fuente: '${fuente}',
        estado: '${estado}',
        mensaje: 'Carga completa local registrada desde PostgreSQL',
        modo: 'carga_completa_local',
        registrado_en: new Date()
      });
    " >/dev/null
done < <(
  "${COMPOSE[@]}" exec -T postgres psql -U "${POSTGRES_USER:-lidia}" -d "${POSTGRES_DB:-proyecto_lidia}" -At -F '|' -c "
    SELECT fuente,
           COALESCE(SUM(filas_leidas),0)::int,
           COALESCE(SUM(filas_insertadas),0)::int,
           COALESCE(SUM(filas_actualizadas),0)::int,
           COALESCE(SUM(filas_rechazadas),0)::int,
           CASE WHEN BOOL_OR(estado='error') THEN 'error' ELSE 'ok' END
    FROM audit.etl_runs
    GROUP BY fuente
    ORDER BY fuente;
  "
)

while IFS='|' read -r pais total frp_total frp_prom; do
  [[ -z "${pais}" ]] && continue
  "${COMPOSE[@]}" exec -T mongo mongosh --quiet \
    --username "${MONGO_INITDB_ROOT_USERNAME:-lidia}" \
    --password "${MONGO_INITDB_ROOT_PASSWORD:-local_lidia}" \
    --authenticationDatabase admin proyecto_lidia --eval "
      db.snapshots_firms.insertOne({
        fecha: new Date(),
        pais_codigo: '${pais}',
        total_focos: NumberInt(${total}),
        resumen: {
          modo: 'carga_completa_local',
          fuente: 'FIRMS',
          frp_total_mw: Number(${frp_total:-0}),
          frp_promedio_mw: Number(${frp_prom:-0}),
          brightness_descripcion: 'brillo_termico_pixel_satelital'
        }
      });
    " >/dev/null
done < <(
  "${COMPOSE[@]}" exec -T postgres psql -U "${POSTGRES_USER:-lidia}" -d "${POSTGRES_DB:-proyecto_lidia}" -At -F '|' -c "
    SELECT u.pais_codigo,
           COUNT(*)::int,
           COALESCE(ROUND(SUM(f.frp_mw), 3), 0),
           COALESCE(ROUND(AVG(f.frp_mw), 3), 0)
    FROM dw.fact_incendio f
    JOIN dw.dim_ubicacion u ON u.ubicacion_id=f.ubicacion_id
    GROUP BY u.pais_codigo
    ORDER BY u.pais_codigo;
  "
)

echo "[carga-completa] Validando conteos finales PostgreSQL..."
"${COMPOSE[@]}" exec -T postgres psql -U "${POSTGRES_USER:-lidia}" -d "${POSTGRES_DB:-proyecto_lidia}" -c "
  SELECT 'staging.stg_firms' AS tabla, COUNT(*)::bigint AS filas FROM staging.stg_firms
  UNION ALL SELECT 'staging.stg_meteo', COUNT(*) FROM staging.stg_meteo
  UNION ALL SELECT 'staging.stg_calidad_aire', COUNT(*) FROM staging.stg_calidad_aire
  UNION ALL SELECT 'staging.stg_chirps', COUNT(*) FROM staging.stg_chirps
  UNION ALL SELECT 'staging.stg_modis', COUNT(*) FROM staging.stg_modis
  UNION ALL SELECT 'dw.fact_incendio', COUNT(*) FROM dw.fact_incendio
  UNION ALL SELECT 'dw.dim_clima', COUNT(*) FROM dw.dim_clima
  UNION ALL SELECT 'dw.dim_calidad_aire', COUNT(*) FROM dw.dim_calidad_aire
  UNION ALL SELECT 'dw.dim_precipitacion', COUNT(*) FROM dw.dim_precipitacion
  UNION ALL SELECT 'dw.dim_cobertura_vegetal', COUNT(*) FROM dw.dim_cobertura_vegetal;

  SELECT u.pais_codigo, COUNT(*)::bigint AS focos
  FROM dw.fact_incendio f
  JOIN dw.dim_ubicacion u ON u.ubicacion_id=f.ubicacion_id
  GROUP BY u.pais_codigo
  ORDER BY u.pais_codigo;

  SELECT COUNT(*)::bigint AS paises_fuera_alcance_staging_firms
  FROM staging.stg_firms
  WHERE pais_codigo NOT IN ('URY','ARG','BRA');

  SELECT fuente, COUNT(*)::bigint AS rechazos
  FROM staging.rechazos_etl
  GROUP BY fuente
  ORDER BY fuente;
" 2>&1 | tee "$LOG_DIR/carga_completa_postgres_conteos.log"

echo "[carga-completa] Validando MongoDB local..."
"${COMPOSE[@]}" exec -T mongo mongosh --quiet \
  --username "${MONGO_INITDB_ROOT_USERNAME:-lidia}" \
  --password "${MONGO_INITDB_ROOT_PASSWORD:-local_lidia}" \
  --authenticationDatabase admin \
  proyecto_lidia --eval '
    printjson({
      database: db.getName(),
      collections: db.getCollectionNames().sort(),
      counts: Object.fromEntries(db.getCollectionNames().sort().map(c => [c, db.getCollection(c).countDocuments()]))
    });
    printjson(db.ingesta_metadata.find({modo: "carga_completa_local"}, {_id: 0}).sort({fuente: 1}).toArray());
    printjson(db.snapshots_firms.find({"resumen.modo": "carga_completa_local"}, {_id: 0}).sort({pais_codigo: 1}).toArray());
  ' 2>&1 | tee "$LOG_DIR/carga_completa_mongo_conteos.log"

echo "[carga-completa] Ejecutando compileall y pytest..."
python3 -m compileall -q .
python3 -m pytest -q tests | tee "$LOG_DIR/carga_completa_pytest.log"

echo
echo "# Carga completa local finalizada"
echo "- Log general: $LOG_FILE"
echo "- Conteos PostgreSQL: evidencia/logs/carga_completa_postgres_conteos.log"
echo "- Conteos MongoDB: evidencia/logs/carga_completa_mongo_conteos.log"
echo "- Fuentes cargadas: ${SOURCES_TO_LOAD[*]}"
echo "- INUMET queda omitido si no se configuro INUMET_FILE real."
