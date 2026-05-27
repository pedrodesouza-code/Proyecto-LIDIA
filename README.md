# Proyecto LIDIA - Aporte EC3 Pedro UTEC

Implementacion reproducible para analizar incendios forestales y sus
condiciones ambientales en **Uruguay, Argentina y Brasil** durante
**2018-2025**. El aporte utiliza exclusivamente las fuentes declaradas del
proyecto: **INUMET, FIRMS, CHIRPS, FORECAST, METEO y MODIS**.

No se versionan datasets crudos, shapefiles, parquets, claves ni contrasenas.
La dimension de calidad del aire se mantiene nullable y pendiente de carga
hasta disponer de una fuente aprobada y trazable del proyecto. La base
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

```bash
cp config/.env.example config/.env
# Completar passwords y rutas locales; config/.env esta ignorado por Git.
python -m pip install -r requirements-utec.txt
```

Las variables `*_FILE` apuntan a archivos locales CSV/Parquet de las fuentes
reales. `INUMET` se valida solo para Uruguay. En FIRMS, `brillo_termico`
representa brillo termico satelital, nunca temperatura del aire.

## Base De Datos

Con PostgreSQL disponible, ejecutar en orden:

```bash
psql "$DATABASE_URL" -f sql/ddl/00_schemas.sql
psql "$DATABASE_URL" -f sql/ddl/01_roles.sql
psql "$DATABASE_URL" -f sql/ddl/02_Schema.sql
psql "$DATABASE_URL" -f sql/ddl/03_indices.sql
psql "$DATABASE_URL" -f sql/ddl/04_vistas.sql
# Opcionales segun ambiente:
psql "$DATABASE_URL" -f sql/ddl/05_migracion_Sa.sql
psql "$DATABASE_URL" -f sql/ddl/06_postgis_firms_migracion.sql
```

`staging` conserva metadata, registros normalizados y rechazos. `dw` aplica
esquema estrella con `fact_incendio` FIRMS y dimensiones de fecha, ubicacion,
clima, precipitacion, cobertura, calidad del aire nullable y estaciones
INUMET. `audit` registra corridas y eventos CDC.

## ETL Y CDC

```bash
python -m etl.main --source FIRMS
python -m etl.main --source METEO
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

## 3.4 Procedimientos De Analisis De Datos

La integracion parte de FIRMS como hecho central y enlaza dimensiones por
fecha y ubicacion. Las vistas responden preguntas de cantidad y FRP por
periodo/pais, actividad regional, relacion con temperatura/humedad,
precipitacion CHIRPS y cobertura MODIS. Las asociaciones describen
co-ocurrencias observadas; no prueban causalidad.

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
- Cargar calidad del aire solo si el equipo confirma una fuente permitida.
- Revisar el enlace espacial/temporal de dimensiones con el volumen real FIRMS.
