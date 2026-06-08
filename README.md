# Proyecto LIDIA - Aporte EC3 Pedro UTEC

Implementacion reproducible para analizar incendios forestales y sus
condiciones ambientales en **Uruguay, Argentina y Brasil** durante
**2018-2025**. El aporte utiliza exclusivamente las fuentes declaradas del
proyecto: **NASA FIRMS, Open-Meteo historico, CAMS/Open-Meteo Air Quality,
CHIRPS, MODIS e INUMET**.

No se versionan datasets crudos, shapefiles, parquets, claves ni contrasenas.
La dimension de calidad del aire integra CAMS/Open-Meteo Air Quality cuando
existe archivo o API validada con PM2.5/PM10; sigue siendo nullable para los
incendios sin dato ambiental cercano y no se inventan valores cuando no hay
carga real disponible. La base
PostgreSQL recomendada para una instalacion limpia es `proyecto_lidia`.
En servidores que inyectan una base compartida, `LIDIA_POSTGRES_DB` selecciona
explicitamente el Data Warehouse de este proyecto.

## Contenido Implementado

- `sql/ddl/`: esquemas `staging`, `dw`, `audit`, roles, modelo
  estrella, indices, vistas, migracion legacy segura y PostGIS opcional FIRMS.
- `etl/`: extractores por fuente, validacion, rechazos,
  promociones al DW y CDC mediante clave natural mas hash SHA-256.
- `nosql/`: schemas y consultas MongoDB para raw payloads, metadata, logs,
  rechazos y snapshots; PostgreSQL sigue siendo el Data Warehouse.
- `dashboard/streamlit_app.py`: dashboard conectado a vistas SQL.
- `tests/`: calidad, idempotencia y CDC con resultados numericos.
- `evidencia/`: procedimientos y resultados verificables generados en esta rama.

## Configuracion

En Jupyter/remoto se trabaja desde `/app/Proyecto-LIDIA` con `config/.env`
ya configurado por el entorno. No es obligatorio copiar `config/.env.example`
encima del archivo real.

```bash
cd /app/Proyecto-LIDIA
set -a
. config/.env
set +a
python -m pip install -r requirements-utec.txt
```

Las variables `*_FILE` apuntan a archivos locales CSV/Parquet de las fuentes
reales. `METEO` es la etiqueta tecnica interna de Open-Meteo historico e
`INUMET` se valida solo para Uruguay. En FIRMS, `brillo_termico`
representa brillo termico satelital, nunca temperatura del aire.
Para calidad del aire, `CAMS_FILE` o `AIR_QUALITY_FILE` apuntan a datos
CAMS/Open-Meteo Air Quality procesados; el ETL normaliza `pm2_5`/`pm2_5_media`
y `pm10`/`pm10_media`.

## Base De Datos

Con PostgreSQL disponible en Jupyter/remoto, cargar primero las variables del
`config/.env` ya configurado:

```bash
cd /app/Proyecto-LIDIA
set -a
. config/.env
set +a
```

Luego ejecutar los DDL en orden usando host, puerto, usuario y base definidos
en el entorno, sin depender de `DATABASE_URL`:

```bash
PGPASSWORD="$POSTGRES_PASSWORD" psql \
  -h "$POSTGRES_HOST" \
  -p "$POSTGRES_PORT" \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -f sql/ddl/00_schemas.sql
PGPASSWORD="$POSTGRES_PASSWORD" psql \
  -h "$POSTGRES_HOST" \
  -p "$POSTGRES_PORT" \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -f sql/ddl/01_roles.sql
PGPASSWORD="$POSTGRES_PASSWORD" psql \
  -h "$POSTGRES_HOST" \
  -p "$POSTGRES_PORT" \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -f sql/ddl/02_Schema.sql
PGPASSWORD="$POSTGRES_PASSWORD" psql \
  -h "$POSTGRES_HOST" \
  -p "$POSTGRES_PORT" \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -f sql/ddl/03_indices.sql
PGPASSWORD="$POSTGRES_PASSWORD" psql \
  -h "$POSTGRES_HOST" \
  -p "$POSTGRES_PORT" \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -f sql/ddl/04_vistas.sql

# Opcionales segun ambiente:
PGPASSWORD="$POSTGRES_PASSWORD" psql \
  -h "$POSTGRES_HOST" \
  -p "$POSTGRES_PORT" \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -f sql/ddl/05_migracion_Sa.sql
PGPASSWORD="$POSTGRES_PASSWORD" psql \
  -h "$POSTGRES_HOST" \
  -p "$POSTGRES_PORT" \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -f sql/ddl/06_postgis_firms_migracion.sql
```

`staging` conserva metadata, registros normalizados y rechazos. `dw` aplica
esquema estrella con `fact_incendio` FIRMS y dimensiones de fecha, ubicacion,
clima, precipitacion, cobertura, calidad del aire nullable y estaciones
INUMET. `audit` registra corridas y eventos CDC.

## ETL Y CDC

```bash
python -m etl.main --source FIRMS
python -m etl.main --source METEO
python -m etl.main --source CAMS
python -m etl.load.real_integrated
python -m etl.main --source ALL
```

Cada registro invalido se guarda como rechazo sin impedir la carga de las
filas validas. Para cada clave natural, el hash de contenido permite contar:
`alta`, `modificacion` y `sin_cambio`. Los conteos, duracion y ultima fecha
procesada quedan en `audit.etl_runs`.

## MongoDB

MongoDB complementa al DW con raw payloads por fuente, metadata de ejecucion,
logs, rechazos y snapshots FIRMS. El contrato esta en `nosql/mongo_schema.json`; no
reemplaza hechos ni dimensiones PostgreSQL.

## Estado De Datos

La carga reproducible local usa los archivos reales disponibles en
`data/processed/`. En el estado local preparado se cargan FIRMS,
METEO/Open-Meteo historico, CAMS/Open-Meteo Air Quality, CHIRPS, MODIS e
INUMET. Para INUMET, los CSV reales de temperatura y humedad se unifican en
`data/processed/inumet_procesado.parquet` mediante
`scripts/preparar_inumet_file_local.py`, dejando `INUMET_FILE` configurado en
`config/.env` local.

En evidencia previa de Jupyter/UTEC se registraron las seis fuentes del
proyecto: FIRMS, METEO/Open-Meteo historico, CAMS/Open-Meteo Air Quality,
CHIRPS, MODIS e INUMET. Los conteos verificables estan en
`evidencia/logs/metricas_carga_fuentes_final.md` y en los logs de carga local
`evidencia/logs/carga_completa_postgres_conteos.log`.

## Tests Y Dashboard

```bash
python -m pytest -q tests -p no:cacheprovider
streamlit run dashboard/streamlit_app.py
```

El dashboard consulta vistas `dw` y presenta ocho KPIs, series temporales,
comparacion por pais/region y cruces con clima, precipitacion y cobertura.
Tambien expone metricas de carga, CDC y rechazos.

## Docker Y Servidor UTEC

Para validacion local se provee `docker/docker-compose.yml`.
El servidor institucional debe usar servicios autorizados; este aporte no
asume Docker ni sharding disponibles. El procedimiento de backup/recuperacion
esta documentado en `docker/README.md`.

## Ejecucion Local Equivalente A Jupyter

El flujo operativo local esta documentado en `docs/ejecucion_local.md`.
Comandos principales:

```bash
docker compose --env-file .env.docker.example up -d
CONFIRM_RESET=1 bash scripts/local_reset_and_load.sh
bash scripts/local_load_all.sh
bash scripts/local_validate_state.sh
bash scripts/export_state_from_jupyter.sh
CONFIRM_RESTORE=1 bash scripts/import_state_to_local.sh
```

Para MongoDB shardeado local, usar el compose complementario y validar siempre
contra el servicio `mongo` como router `mongos`, no contra los shards.

## 3.4 Procedimientos De Analisis De Datos

La integracion parte de FIRMS como hecho central y enlaza dimensiones mediante
nearest neighbor Haversine dentro del mismo pais: clima en la misma fecha y
hora disponible mas cercana, CHIRPS por anio/mes y MODIS por anio. Se aplican
umbrales documentados y el hecho queda sin enlace cuando no existe candidato
compatible. Las vistas responden preguntas de cantidad y FRP por periodo/pais,
actividad regional, relacion con temperatura/humedad, precipitacion CHIRPS y
cobertura MODIS. Las asociaciones describen co-ocurrencias observadas; no
prueban causalidad.

## 3.5 Etica, Seguridad Y Gobernanza

El aporte minimiza privilegios con roles de dashboard, ETL y administracion;
excluye secretos y datos pesados de Git; registra origen, fallos y CDC; y
delimita el alcance geografico. Las localizaciones FIRMS se usan para analisis
ambiental agregado, evitando atribuciones de causalidad o responsabilidad.

## 4.2 Implementacion

La implementacion incluye DDL ejecutable, pipeline Python modular, persistencia
documental complementaria, dashboard SQL y tests unitarios de reglas
criticas. PostGIS agrega geometria de FIRMS de forma opcional y separada.

## Pendientes Verificables

- Ejecutar DDL y ETL contra la instancia UTEC con variables locales validas.
- Registrar conteos reales de una segunda corrida y capturas del dashboard.
- Mantener actualizados los CSV locales de INUMET si se agregan nuevas
  observaciones fuera del entorno Jupyter/UTEC.
- Validar con el equipo los umbrales documentados del enlace nearest neighbor:
  100 km para Open-Meteo historico, CHIRPS, MODIS y calidad del aire, y 150 km para INUMET.
