#!/usr/bin/env bash
set -euo pipefail

# Proyecto LIDIA EC3/D8
# Carga local de estructuras PostgreSQL y MongoDB usando Docker Compose.
# No usa credenciales reales de UTEC, no conecta a bases institucionales y no
# ejecuta carga historica. PostgreSQL sigue siendo el DW principal; MongoDB es
# complemento documental.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

LOG_DIR="evidencia/logs"
mkdir -p "${LOG_DIR}"

ENV_FILE=".env.docker"
if [[ ! -f "${ENV_FILE}" ]]; then
  ENV_FILE=".env.docker.example"
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

POSTGRES_DB="${POSTGRES_DB:-proyecto_lidia}"
POSTGRES_USER="${POSTGRES_USER:-lidia}"
MONGO_USER="${MONGO_INITDB_ROOT_USERNAME:-lidia}"
MONGO_PASSWORD="${MONGO_INITDB_ROOT_PASSWORD:-local_lidia}"

COMPOSE=(docker compose --env-file "${ENV_FILE}" -f docker-compose.yml)

mask() {
  sed -E \
    -e 's#(postgresql://[^:]+:)[^@]+@#\1***@#g' \
    -e 's#(mongodb://[^:]+:)[^@]+@#\1***@#g' \
    -e 's#(--password )[A-Za-z0-9_.-]+#\1***#g' \
    -e 's#(POSTGRES_PASSWORD=).+#\1***#g' \
    -e 's#(MONGO_INITDB_ROOT_PASSWORD=).+#\1***#g'
}

echo "[local-db] Levantando PostgreSQL y MongoDB locales..."
"${COMPOSE[@]}" up -d --wait postgres mongo --remove-orphans 2>&1 | mask | tee "${LOG_DIR}/local_db_compose_up.log"

echo "[local-db] Ejecutando DDL PostgreSQL local..."
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
      -U "${POSTGRES_USER}" \
      -d "${POSTGRES_DB}" \
      < "${sql_file}" 2>&1
  done
} | mask | tee "${LOG_DIR}/local_postgres_ddl.log"

echo "[local-db] Validando tablas PostgreSQL locales..."
"${COMPOSE[@]}" exec -T postgres psql \
  -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" \
  -c "
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema IN ('staging','dw','audit')
ORDER BY table_schema, table_name;
" 2>&1 | mask | tee "${LOG_DIR}/local_postgres_tablas.log"

echo "[local-db] Creando colecciones MongoDB locales con validadores y documentos minimos de evidencia..."
"${COMPOSE[@]}" exec -T mongo mongosh --quiet \
  --username "${MONGO_USER}" \
  --password "${MONGO_PASSWORD}" \
  --authenticationDatabase admin \
  proyecto_lidia <<'JS' 2>&1 | mask | tee "evidencia/logs/local_mongo_carga.log"
const now = new Date();
const runId = "local-d8-" + now.toISOString();

function ensureCollection(name, validator) {
  const exists = db.getCollectionNames().includes(name);
  if (!exists) {
    db.createCollection(name, { validator });
  } else {
    db.runCommand({ collMod: name, validator });
  }
}

const fuenteEnum = ["INUMET", "FIRMS", "CHIRPS", "METEO", "MODIS", "CAMS"];

ensureCollection("ingesta_metadata", {
  $jsonSchema: {
    bsonType: "object",
    required: ["run_id", "fuente", "estado", "metricas", "registrado_en"],
    properties: {
      run_id: { bsonType: "string" },
      fuente: { enum: fuenteEnum },
      estado: { enum: ["ok", "parcial", "error"] },
      metricas: { bsonType: "object" },
      registrado_en: { bsonType: "date" }
    }
  }
});

ensureCollection("rechazos_etl", {
  $jsonSchema: {
    bsonType: "object",
    required: ["run_id", "fuente", "motivo", "registro", "registrado_en"],
    properties: {
      run_id: { bsonType: "string" },
      fuente: { enum: fuenteEnum },
      motivo: { bsonType: "string" },
      registro: { bsonType: "object" },
      registrado_en: { bsonType: "date" }
    }
  }
});

ensureCollection("raw_payloads", {
  $jsonSchema: {
    bsonType: "object",
    required: ["run_id", "fuente", "payload", "registrado_en"],
    properties: {
      run_id: { bsonType: "string" },
      fuente: { enum: fuenteEnum },
      payload: { bsonType: "object" },
      registrado_en: { bsonType: "date" }
    }
  }
});

ensureCollection("pipeline_logs", {
  $jsonSchema: {
    bsonType: "object",
    required: ["run_id", "fuente", "estado", "mensaje", "registrado_en"],
    properties: {
      run_id: { bsonType: "string" },
      fuente: { enum: fuenteEnum },
      estado: { enum: ["inicio", "ok", "parcial", "error"] },
      mensaje: { bsonType: "string" },
      registrado_en: { bsonType: "date" }
    }
  }
});

ensureCollection("snapshots_firms", {
  $jsonSchema: {
    bsonType: "object",
    required: ["fecha", "pais_codigo", "total_focos", "resumen"],
    properties: {
      fecha: { bsonType: "date" },
      pais_codigo: { enum: ["URY", "ARG", "BRA"] },
      total_focos: { bsonType: "int", minimum: 0 },
      resumen: { bsonType: "object" }
    }
  }
});

db.ingesta_metadata.replaceOne(
  { run_id: runId, fuente: "FIRMS" },
  {
    run_id: runId,
    fuente: "FIRMS",
    estado: "ok",
    metricas: {
      tipo: "evidencia_local_docker",
      filas_reales_cargadas: 0,
      nota: "Documento operativo local; no representa carga historica real."
    },
    registrado_en: now
  },
  { upsert: true }
);

db.pipeline_logs.replaceOne(
  { run_id: runId, fuente: "FIRMS", mensaje: "Carga local Docker PostgreSQL/Mongo validada" },
  {
    run_id: runId,
    fuente: "FIRMS",
    estado: "ok",
    mensaje: "Carga local Docker PostgreSQL/Mongo validada",
    registrado_en: now
  },
  { upsert: true }
);

db.raw_payloads.replaceOne(
  { run_id: runId, fuente: "FIRMS" },
  {
    run_id: runId,
    fuente: "FIRMS",
    payload: {
      tipo: "snapshot_controlado_local",
      brightness_descripcion: "brillo_termico_pixel_satelital",
      paises_alcance: ["URY", "ARG", "BRA"]
    },
    registrado_en: now
  },
  { upsert: true }
);

for (const pais of ["URY", "ARG", "BRA"]) {
  db.snapshots_firms.replaceOne(
    { fecha: new Date("2025-01-01T00:00:00Z"), pais_codigo: pais },
    {
      fecha: new Date("2025-01-01T00:00:00Z"),
      pais_codigo: pais,
      total_focos: NumberInt(0),
      resumen: {
        tipo: "estructura_local_sin_carga_historica",
        fuente: "FIRMS",
        nota: "Conteo cero porque no se ejecuta carga historica local."
      }
    },
    { upsert: true }
  );
}

printjson({
  database: db.getName(),
  collections: db.getCollectionNames().sort(),
  counts: {
    ingesta_metadata: db.ingesta_metadata.countDocuments(),
    rechazos_etl: db.rechazos_etl.countDocuments(),
    raw_payloads: db.raw_payloads.countDocuments(),
    pipeline_logs: db.pipeline_logs.countDocuments(),
    snapshots_firms: db.snapshots_firms.countDocuments()
  }
});
JS

echo "[local-db] Resumen final local..."
{
  echo "# Carga Local PostgreSQL/Mongo - Proyecto LIDIA"
  echo
  echo "- PostgreSQL local: DDL ejecutado para esquemas staging, dw y audit."
  echo "- MongoDB local: colecciones documentales creadas con validadores."
  echo "- No se ejecutó carga histórica completa."
  echo "- No se usaron credenciales reales de UTEC."
  echo "- MongoDB sigue siendo complemento documental; PostgreSQL es el DW principal."
  echo
  echo "Logs:"
  echo "- evidencia/logs/local_db_compose_up.log"
  echo "- evidencia/logs/local_postgres_ddl.log"
  echo "- evidencia/logs/local_postgres_tablas.log"
  echo "- evidencia/logs/local_mongo_carga.log"
} | tee "${LOG_DIR}/local_db_resumen.md"

echo "[local-db] Listo."
