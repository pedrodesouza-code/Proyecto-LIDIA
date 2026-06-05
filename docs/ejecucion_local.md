# Ejecucion Local Y Sincronizacion Jupyter

Esta guia deja un flujo reproducible para trabajar el Proyecto LIDIA EC3 en Docker local y mantenerlo equivalente al entorno Jupyter/UTEC.

## Alcance

El proyecto analiza incendios forestales y variables ambientales en Uruguay, Argentina y Brasil durante 2018-2025.

Fuentes validas:

- NASA FIRMS.
- METEO/Open-Meteo historico.
- CAMS/Open-Meteo Air Quality.
- CHIRPS.
- MODIS.
- INUMET, solo Uruguay.

PostgreSQL es el Data Warehouse principal. MongoDB es complementario para metadata, logs, snapshots, rechazos y payloads documentales controlados.

## Flujo Local Docker

Levantar contenedores:

```bash
docker compose --env-file .env.docker.example up -d
```

Cargar todo desde cero, borrando esquemas locales `staging`, `dw` y `audit`:

```bash
CONFIRM_RESET=1 bash scripts/local_reset_and_load.sh
```

Cargar sin reset, usando upsert/idempotencia:

```bash
bash scripts/local_load_all.sh
```

Validar estado:

```bash
bash scripts/local_validate_state.sh
```

Validar estado usando sharding local de MongoDB:

```bash
SHARDING=1 bash scripts/local_validate_state.sh
```

Ejecutar validaciones Python:

```bash
python3 -m compileall -q .
python3 -m pytest -q tests
```

Los scripts usan `python3` por defecto. Si el entorno tiene otro binario,
definir `PYTHON_BIN`, por ejemplo `PYTHON_BIN=python`.

## Sharding MongoDB Local

El compose principal no se modifica. La evidencia local de sharding se activa con:

```bash
bash scripts/aplicar_sharding_mongo_compose.sh
```

Observar estado del cluster:

```bash
docker compose -f docker-compose.yml -f docker-compose.sharding.yml exec mongo mongosh --eval 'sh.status()'
```

Consultar distribucion:

```bash
docker compose -f docker-compose.yml -f docker-compose.sharding.yml exec mongo mongosh proyecto_lidia --eval 'db.eventos_enriquecidos.getShardDistribution()'
```

Cuando se usa sharding, la aplicacion debe conectarse al servicio `mongo`, que funciona como router `mongos`; no se debe usar `shard01` ni `shard02` como endpoint de aplicacion.

## Snapshot Desde Jupyter/UTEC

En Jupyter/UTEC definir variables autorizadas:

```bash
export DATABASE_URL='postgresql://...'
export MONGO_URI='mongodb://...'
```

Exportar snapshot:

```bash
bash scripts/export_state_from_jupyter.sh
```

El export genera:

- `backups/postgres/proyecto_lidia_<timestamp>.sql`
- `backups/mongo/<timestamp>/`

`backups/` esta ignorado por Git para evitar subir dumps pesados.

## Importar Snapshot En Docker Local

Restaurar el snapshot mas reciente:

```bash
CONFIRM_RESTORE=1 bash scripts/import_state_to_local.sh
```

Restaurar rutas especificas:

```bash
CONFIRM_RESTORE=1 \
POSTGRES_SNAPSHOT=backups/postgres/proyecto_lidia_YYYYMMDDTHHMMSSZ.sql \
MONGO_SNAPSHOT=backups/mongo/YYYYMMDDTHHMMSSZ \
bash scripts/import_state_to_local.sh
```

Si MongoDB local esta shardeado, restaurar usando el router:

```bash
CONFIRM_RESTORE=1 SHARDING=1 bash scripts/import_state_to_local.sh
```

## Validaciones Que Ejecuta El Flujo

`scripts/local_validate_state.sh` verifica:

- tablas en esquemas `staging`, `dw` y `audit`;
- claves primarias, foraneas, unique y check;
- conteos en tablas principales;
- conteo de `dw.fact_incendio`;
- conteos por pais;
- ausencia de paises fuera de URY, ARG y BRA en hechos;
- INUMET solo Uruguay;
- calidad del aire nullable cuando no hay PM valido;
- `brillo_termico` documentado como brillo termico satelital, no temperatura del aire;
- colecciones MongoDB y conteos por coleccion;
- `python -m compileall -q .`;
- `python -m pytest -q tests`.

## Logs

Todos los scripts escriben evidencia en `evidencia/logs/`, incluyendo fecha/hora, comandos, conteos y resultado de validaciones.

Logs principales:

- `evidencia/logs/local_reset_and_load.log`
- `evidencia/logs/local_load_all.log`
- `evidencia/logs/local_validate_state.log`
- `evidencia/logs/export_state_from_jupyter_<timestamp>.log`
- `evidencia/logs/import_state_to_local.log`
- `evidencia/logs/carga_completa_postgres_conteos.log`
- `evidencia/logs/carga_completa_mongo_conteos.log`

## Diferencia Entre Caminos

Camino A, reconstruccion reproducible:

```bash
docker compose --env-file .env.docker.example up -d
CONFIRM_RESET=1 bash scripts/local_reset_and_load.sh
bash scripts/local_validate_state.sh
```

Camino B, snapshot Jupyter hacia local:

```bash
bash scripts/export_state_from_jupyter.sh
CONFIRM_RESTORE=1 bash scripts/import_state_to_local.sh
bash scripts/local_validate_state.sh
```

El camino A depende de los archivos reales en `data/processed/`. El camino B replica el estado ya materializado en Jupyter/UTEC.
