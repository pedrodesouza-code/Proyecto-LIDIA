#!/usr/bin/env bash
set -euo pipefail

# Proyecto LIDIA - validacion de equivalencia/estado local Docker.
# Use SHARDING=1 para validar MongoDB a traves del router mongos definido por
# docker-compose.yml + docker-compose.sharding.yml.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LOG_DIR="evidencia/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/local_validate_state.log"
ENV_FILE=".env.docker"
if [[ ! -f "$ENV_FILE" ]]; then
  ENV_FILE=".env.docker.example"
fi

if [[ "${LIDIA_LOCAL_VALIDATE_LOGGING:-0}" != "1" ]]; then
  export LIDIA_LOCAL_VALIDATE_LOGGING=1
  bash "$0" "$@" 2>&1 | tee "$LOG_FILE"
  exit "${PIPESTATUS[0]}"
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
PYTHON_BIN="${PYTHON_BIN:-python3}"

COMPOSE=(docker compose --env-file "$ENV_FILE" -f docker-compose.yml)
if [[ "${SHARDING:-0}" == "1" ]]; then
  COMPOSE=(docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.sharding.yml)
fi

export PAGER=cat
export PSQL_PAGER=cat

echo "[local-validate] $(date -Iseconds)"
echo "[local-validate] Compose: ${COMPOSE[*]}"

echo "[local-validate] Estado Docker"
"${COMPOSE[@]}" ps

echo "[local-validate] PostgreSQL: tablas, claves, conteos y reglas del dominio"
"${COMPOSE[@]}" exec -T postgres psql -P pager=off -v ON_ERROR_STOP=1 \
  -U "${POSTGRES_USER:-lidia}" \
  -d "${POSTGRES_DB:-proyecto_lidia}" <<'SQL'
SELECT 'dw_tables' AS metrica, COUNT(*)::bigint AS valor
FROM information_schema.tables
WHERE table_schema='dw' AND table_type='BASE TABLE';

SELECT table_schema, table_name, COUNT(*) OVER () AS total_tablas
FROM information_schema.tables
WHERE table_schema IN ('staging','dw','audit')
ORDER BY table_schema, table_name;

SELECT tc.table_schema, tc.table_name, tc.constraint_type, COUNT(*)::bigint AS cantidad
FROM information_schema.table_constraints tc
WHERE tc.table_schema IN ('staging','dw','audit')
  AND tc.constraint_type IN ('PRIMARY KEY','FOREIGN KEY','UNIQUE','CHECK')
GROUP BY tc.table_schema, tc.table_name, tc.constraint_type
ORDER BY tc.table_schema, tc.table_name, tc.constraint_type;

SELECT 'staging.stg_firms' AS tabla, COUNT(*)::bigint AS filas FROM staging.stg_firms
UNION ALL SELECT 'staging.stg_meteo', COUNT(*) FROM staging.stg_meteo
UNION ALL SELECT 'staging.stg_calidad_aire', COUNT(*) FROM staging.stg_calidad_aire
UNION ALL SELECT 'staging.stg_chirps', COUNT(*) FROM staging.stg_chirps
UNION ALL SELECT 'staging.stg_modis', COUNT(*) FROM staging.stg_modis
UNION ALL SELECT 'staging.rechazos_etl', COUNT(*) FROM staging.rechazos_etl
UNION ALL SELECT 'dw.fact_incendio', COUNT(*) FROM dw.fact_incendio
UNION ALL SELECT 'dw.dim_clima', COUNT(*) FROM dw.dim_clima
UNION ALL SELECT 'dw.dim_calidad_aire', COUNT(*) FROM dw.dim_calidad_aire
UNION ALL SELECT 'dw.dim_precipitacion', COUNT(*) FROM dw.dim_precipitacion
UNION ALL SELECT 'dw.dim_cobertura_vegetal', COUNT(*) FROM dw.dim_cobertura_vegetal
UNION ALL SELECT 'audit.etl_runs', COUNT(*) FROM audit.etl_runs
UNION ALL SELECT 'audit.cdc_eventos', COUNT(*) FROM audit.cdc_eventos
ORDER BY tabla;

SELECT u.pais_codigo, COUNT(*)::bigint AS focos
FROM dw.fact_incendio f
JOIN dw.dim_ubicacion u ON u.ubicacion_id=f.ubicacion_id
GROUP BY u.pais_codigo
ORDER BY u.pais_codigo;

SELECT COUNT(*)::bigint AS hechos_fuera_alcance
FROM dw.fact_incendio f
JOIN dw.dim_ubicacion u ON u.ubicacion_id=f.ubicacion_id
WHERE u.pais_codigo NOT IN ('URY','ARG','BRA');

SELECT COUNT(*)::bigint AS inumet_fuera_uruguay
FROM staging.stg_meteo
WHERE fuente='INUMET' AND pais_codigo <> 'URY';

SELECT COUNT(*)::bigint AS calidad_aire_sin_pm_valido
FROM dw.dim_calidad_aire
WHERE pm25 IS NULL AND pm10 IS NULL;

SELECT COUNT(*)::bigint AS columnas_brightness_temperatura
FROM information_schema.columns
WHERE table_schema IN ('staging','dw')
  AND column_name ILIKE '%brightness%'
  AND column_name ILIKE '%temp%';

SELECT obj_description('dw.fact_incendio'::regclass) AS comentario_fact_incendio,
       col_description('dw.fact_incendio'::regclass, (
          SELECT ordinal_position
          FROM information_schema.columns
          WHERE table_schema='dw'
            AND table_name='fact_incendio'
            AND column_name='brillo_termico'
       )::int) AS comentario_brillo_termico;
SQL

echo "[local-validate] MongoDB: colecciones y documentos"
"${COMPOSE[@]}" exec -T mongo mongosh --quiet \
  --username "${MONGO_INITDB_ROOT_USERNAME:-lidia}" \
  --password "${MONGO_INITDB_ROOT_PASSWORD:-local_lidia}" \
  --authenticationDatabase admin \
  proyecto_lidia --eval '
    const names = db.getCollectionNames().sort();
    printjson({
      database: db.getName(),
      collections_count: names.length,
      collections: names,
      counts: Object.fromEntries(names.map(c => [c, db.getCollection(c).countDocuments()]))
    });
    printjson({
      ingesta_metadata_sample: db.ingesta_metadata.find({}, {_id: 0}).sort({registrado_en: -1}).limit(3).toArray(),
      snapshots_firms_sample: db.snapshots_firms.find({}, {_id: 0}).sort({fecha: -1}).limit(3).toArray()
    });
  '

if [[ "${SHARDING:-0}" == "1" ]]; then
  echo "[local-validate] MongoDB sharding via mongos"
  "${COMPOSE[@]}" exec -T mongo mongosh --quiet --eval 'printjson(db.adminCommand({ hello: 1 })); sh.status();'
fi

echo "[local-validate] ${PYTHON_BIN} -m compileall -q ."
"$PYTHON_BIN" -m compileall -q .

echo "[local-validate] ${PYTHON_BIN} -m pytest -q tests"
"$PYTHON_BIN" -m pytest -q tests

echo "[local-validate] Finalizado: $(date -Iseconds)"
