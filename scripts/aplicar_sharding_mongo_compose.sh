#!/usr/bin/env bash
set -euo pipefail

# Proyecto LIDIA EC3/D8
# Evidencia local academica de sharding MongoDB.
# No es una configuracion productiva y no reemplaza al DW PostgreSQL.
# MongoDB se mantiene como capa documental complementaria para metadata, logs,
# rechazos, snapshots y eventos enriquecidos.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

LOG_DIR="evidencia/logs"
mkdir -p "${LOG_DIR}"

ENV_FILE=".env.docker"
if [[ ! -f "${ENV_FILE}" ]]; then
  ENV_FILE=".env.docker.example"
fi

COMPOSE=(docker compose --env-file "${ENV_FILE}" -f docker-compose.yml -f docker-compose.sharding.yml)

cat > docker-compose.sharding.yml <<'YAML'
services:
  configsvr:
    image: mongo:7
    command: ["mongod", "--configsvr", "--replSet", "rs-config", "--bind_ip_all", "--port", "27017"]
    volumes:
      - lidia_configsvr_data:/data/db
    healthcheck:
      test: ["CMD-SHELL", "mongosh --quiet --eval 'db.adminCommand({ ping: 1 }).ok' | grep 1"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 20s

  shard01:
    image: mongo:7
    command: ["mongod", "--shardsvr", "--replSet", "rs-shard-01", "--bind_ip_all", "--port", "27017"]
    volumes:
      - lidia_shard01_data:/data/db
    healthcheck:
      test: ["CMD-SHELL", "mongosh --quiet --eval 'db.adminCommand({ ping: 1 }).ok' | grep 1"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 20s

  shard02:
    image: mongo:7
    command: ["mongod", "--shardsvr", "--replSet", "rs-shard-02", "--bind_ip_all", "--port", "27017"]
    volumes:
      - lidia_shard02_data:/data/db
    healthcheck:
      test: ["CMD-SHELL", "mongosh --quiet --eval 'db.adminCommand({ ping: 1 }).ok' | grep 1"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 20s

  mongo:
    image: mongo:7
    command: ["mongos", "--configdb", "rs-config/configsvr:27017", "--bind_ip_all", "--port", "27017"]
    depends_on:
      configsvr:
        condition: service_healthy
      shard01:
        condition: service_healthy
      shard02:
        condition: service_healthy

volumes:
  lidia_configsvr_data:
  lidia_shard01_data:
  lidia_shard02_data:
YAML

echo "[D8 sharding] docker-compose.sharding.yml creado/actualizado."

echo "[D8 sharding] Levantando config server y shards..."
"${COMPOSE[@]}" up -d --wait configsvr shard01 shard02

run_mongo() {
  local service="$1"
  local script="$2"
  "${COMPOSE[@]}" exec -T "${service}" mongosh --quiet --eval "${script}"
}

init_rs() {
  local service="$1"
  local rs_name="$2"
  local host="$3"
  echo "[D8 sharding] Inicializando ${rs_name} en ${service}..."
  if ! run_mongo "${service}" "rs.initiate({_id: '${rs_name}', members: [{ _id: 0, host: '${host}:27017' }]})"; then
    echo "[D8 sharding] ${rs_name} ya podria estar inicializado; se continua."
  fi
}

init_rs "configsvr" "rs-config" "configsvr"
init_rs "shard01" "rs-shard-01" "shard01"
init_rs "shard02" "rs-shard-02" "shard02"

echo "[D8 sharding] Esperando replica sets..."
sleep 10

echo "[D8 sharding] Levantando mongos router en servicio mongo..."
"${COMPOSE[@]}" up -d --wait mongo

mongos_eval() {
  local script="$1"
  "${COMPOSE[@]}" exec -T mongo mongosh --quiet --eval "${script}"
}

mongos_db_eval() {
  local database="$1"
  local script="$2"
  "${COMPOSE[@]}" exec -T mongo mongosh --quiet "${database}" --eval "${script}"
}

echo "[D8 sharding] Agregando shards al cluster..."
mongos_eval 'try { sh.addShard("rs-shard-01/shard01:27017") } catch (e) { print("shard01 ya agregado o no disponible todavia: " + e.message) }'
mongos_eval 'try { sh.addShard("rs-shard-02/shard02:27017") } catch (e) { print("shard02 ya agregado o no disponible todavia: " + e.message) }'

echo "[D8 sharding] Configurando base y coleccion shardeada..."
mongos_eval 'try { sh.enableSharding("proyecto_lidia") } catch (e) { print("enableSharding ya aplicado o no requerido: " + e.message) }'
mongos_db_eval "proyecto_lidia" 'db.createCollection("eventos_enriquecidos"); db.eventos_enriquecidos.createIndex({ _id: "hashed" })'
mongos_eval 'try { sh.shardCollection("proyecto_lidia.eventos_enriquecidos", { _id: "hashed" }) } catch (e) { print("shardCollection ya aplicado o no requerido: " + e.message) }'

echo "[D8 sharding] Insertando documentos minimos sinteticos para evidencia local academica..."
mongos_db_eval "proyecto_lidia" '
const paises = ["URY", "ARG", "BRA"];
const bulk = [];
for (let i = 0; i < 300; i++) {
  bulk.push({
    _id: "d8_lidia_sharding_" + i,
    criterio: "D8",
    tipo_evidencia: "sharding_local_academico",
    fuente: "FIRMS",
    pais_codigo: paises[i % paises.length],
    anio: 2018 + (i % 8),
    frp: Number((5 + (i % 97) * 1.17).toFixed(2)),
    brightness: Number((300 + (i % 70) * 0.83).toFixed(2)),
    brightness_descripcion: "brillo_termico_pixel_satelital",
    created_at: new Date()
  });
}
db.eventos_enriquecidos.bulkWrite(
  bulk.map(doc => ({ updateOne: { filter: { _id: doc._id }, update: { $set: doc }, upsert: true } })),
  { ordered: false }
);
printjson({
  coleccion: "proyecto_lidia.eventos_enriquecidos",
  documentos: db.eventos_enriquecidos.countDocuments({ tipo_evidencia: "sharding_local_academico" }),
  nota: "Documentos sinteticos minimos solo para evidencia local D8; no son datos reales del DW."
});
'

echo "[D8 sharding] Guardando evidencias..."
"${COMPOSE[@]}" ps > "${LOG_DIR}/d8_sharding_compose_ps.log"
mongos_eval 'db.hello()' > "${LOG_DIR}/d8_mongos_hello.log"
mongos_eval 'sh.status()' > "${LOG_DIR}/d8_sharding_status.log"
mongos_db_eval "proyecto_lidia" 'db.eventos_enriquecidos.getShardDistribution()' > "${LOG_DIR}/d8_sharding_distribution.log"

cat <<'MSG'

[D8 sharding] Evidencia local generada.

Comandos de observacion:
docker compose -f docker-compose.yml -f docker-compose.sharding.yml exec mongo mongosh --eval 'sh.status()'
docker compose -f docker-compose.yml -f docker-compose.sharding.yml exec mongo mongosh proyecto_lidia --eval 'db.eventos_enriquecidos.getShardDistribution()'

Logs:
- evidencia/logs/d8_sharding_compose_ps.log
- evidencia/logs/d8_mongos_hello.log
- evidencia/logs/d8_sharding_status.log
- evidencia/logs/d8_sharding_distribution.log
MSG
