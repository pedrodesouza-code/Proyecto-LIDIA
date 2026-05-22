# 10 â€” ExplicaciÃ³n del proyecto paso a paso

## 1. Â¿QuÃ© hace SINIA-UY?

Es un **sistema de monitoreo ambiental para detectar y predecir riesgo de incendios forestales en Uruguay** (con extensiÃ³n a 6 paÃ­ses de SudamÃ©rica). El sistema:

1. Descarga datos desde APIs pÃºblicas (NASA, Open-Meteo, CAMS).
2. Los limpia, transforma y calcula un **Ã­ndice de riesgo de incendio**.
3. Los guarda en dos bases de datos: PostgreSQL (analÃ­tica) y MongoDB (operacional).
4. Los muestra en un **dashboard Streamlit** con mapa, series y alertas.
5. Se actualiza automÃ¡ticamente mediante un scheduler.

## 2. Las capas del sistema (vista de pÃ¡jaro)

```
[Capa 1] Fuentes externas (APIs pÃºblicas)
            â†“
[Capa 2] ETL en Python (extract â†’ transform â†’ load)
            â†“
[Capa 3] Almacenamiento (PostgreSQL + MongoDB)
            â†“
[Capa 4] AnalÃ­tica + Dashboard Streamlit
            â†“
[Capa 5] AutomatizaciÃ³n (scheduler) + Tests de calidad + Backups
```

Cada capa estÃ¡ en una carpeta del proyecto. No hay magia: una capa lee la anterior y escribe a la siguiente.

## 3. Capa por capa con archivos reales

### 3.1 Fuentes externas â€” quÃ© entra al sistema

| Fuente | QuÃ© da | Granularidad | CÃ³mo se accede |
|--------|--------|--------------|----------------|
| NASA FIRMS VIIRS NRT | Focos de calor de las Ãºltimas horas | Punto + hora | API REST con `FIRMS_MAP_KEY` |
| NASA FIRMS VIIRS SP | Archivo histÃ³rico de focos | Punto + hora | Misma API, modo archivo |
| Open-Meteo Forecast | PronÃ³stico meteo 7 dÃ­as | Diario por punto | API REST sin clave |
| Open-Meteo Archive | HistÃ³rico meteorolÃ³gico desde 1940 | Diario por punto | API REST sin clave |
| CAMS via Open-Meteo | Calidad del aire (PM10, PM2.5) | Horario por punto | API REST sin clave |
| CHIRPS (UCSB) | PrecipitaciÃ³n mensual histÃ³rica | Mensual por punto | API ClimateSERV |
| MODIS MCD12Q1 | Cobertura vegetal anual | Anual por punto | NASA AppEEARS |

Todo configurado en `config/settings.py` (URLs base, listas de puntos, paÃ­ses, pesos del Ã­ndice).

### 3.2 ETL â€” el corazÃ³n

Carpeta `etl/`. Tres etapas estrictamente separadas:

**Extract (`etl/extract/`)** â€” un archivo por fuente:
- `extract_firms.py` â†’ descarga CSVs de FIRMS y los guarda en `data/raw/firms/`.
- `extract_meteo.py` â†’ meteo histÃ³rico de las 19 ciudades a `data/raw/meteo/`.
- `extract_forecast.py` â†’ pronÃ³stico 7 dÃ­as para los 5 puntos de Uruguay.
- `extract_cams.py` â†’ calidad del aire horaria, guarda CSVs por ciudad.
- `extract_chirps.py` y `extract_modis.py` â†’ fuentes complementarias.

Cada extractor: hace request HTTP â†’ recibe JSON/CSV â†’ guarda CSV crudo con el nombre del punto, sensor y rango de fechas. **Nunca modifica datos**, solo los baja.

**Transform (`etl/transform/`)** â€” un archivo por fuente:
- `transform_meteo.py` â†’ lee meteo crudo, calcula los 4 componentes del Ã­ndice de riesgo (temperatura, humedad, viento, sequÃ­a), los pondera (0.25/0.30/0.20/0.25) y clasifica en `bajo/moderado/alto/muy_alto`. Escribe a `data/processed/meteo_procesado_<ciudad>.parquet`.
- `transform_cams.py` â†’ agrega CAMS horario a media diaria, calcula percentiles, marca si supera el lÃ­mite OMS de 45 Âµg/mÂ³ de PM10.
- `transform_firms.py` â†’ normaliza coordenadas, asigna paÃ­s por bounding box, normaliza confianza (l/n/h â†’ 1/2/3).
- `transform_chirps.py` / `transform_modis.py` â†’ procesado de las fuentes complementarias.

Salida estÃ¡ndar: archivos **Parquet** en `data/processed/` (formato comprimido y rÃ¡pido).

**Load (`etl/load/`)** â€” dos destinos:
- `load_postgres.py` â†’ lee los parquets y hace **UPSERT idempotente** a PostgreSQL. Si un registro ya existe (misma clave natural) se actualiza; si no, se inserta. Sin duplicados.
- `load_mongo.py` â†’ escribe snapshots diarios, alertas y trazas de ejecuciÃ³n a MongoDB.

**AuditorÃ­a CDC** â€” cada ejecuciÃ³n registra en `etl_ejecuciones` cuÃ¡ntos registros se procesaron, insertaron, actualizaron y cuÃ¡nto tardÃ³. Esto es lo que se examina en defensa cuando preguntan "Â¿cÃ³mo sabÃ©s que no duplica?".

### 3.3 Almacenamiento â€” dos motores complementarios

**PostgreSQL (`sql/`)** â€” Data Warehouse analÃ­tico:

| Tabla | Tipo | QuÃ© guarda |
|-------|------|-----------|
| `puntos_monitoreo` | DimensiÃ³n | 19 ciudades de monitoreo |
| `paises_referencia` | DimensiÃ³n | 7 paÃ­ses (BRA, BOL, PRY, ARG, CHL, PER, URY) |
| `focos_calor` | Hechos | Cada foco detectado por satÃ©lite |
| `meteo_diario` | Hechos | Meteo + Ã­ndice de riesgo, histÃ³rico y forecast |
| `calidad_aire_diario` | Hechos | PM10, PM2.5, AQI por dÃ­a/punto |
| `precipitacion_mensual` | Hechos | CHIRPS por punto/mes |
| `cobertura_vegetal` | Hechos | MODIS anual por punto |
| `etl_ejecuciones` | AuditorÃ­a | Cada corrida del pipeline |

Cada tabla tiene `CHECK` constraints, una `UNIQUE` para idempotencia y triggers de timestamp. Hay tres roles (`sinia_readonly`, `sinia_etl`, `sinia_admin`) con principio de mÃ­nimo privilegio.

Los archivos estÃ¡n organizados en orden de ejecuciÃ³n:
```
sql/ddl/
â”œâ”€â”€ 01_roles.sql     â† roles + usuarios
â”œâ”€â”€ 02_schema.sql    â† tablas con CHECKs y triggers
â”œâ”€â”€ 03_indices.sql   â† Ã­ndices analÃ­ticos
â”œâ”€â”€ 04_vistas.sql    â† vistas para dashboard y seguridad
â””â”€â”€ 05_migracion_sa.sql

sql/dml/
â””â”€â”€ 01_seed_puntos.sql  â† carga inicial de los 19 puntos

sql/queries/
â””â”€â”€ 01_analiticas.sql   â† 10 consultas representativas
```

Esto se ejecuta **automÃ¡ticamente** en orden alfabÃ©tico cuando Postgres arranca por primera vez gracias al volumen `docker-entrypoint-initdb.d/`.

**MongoDB (`nosql/`)** â€” base operacional flexible:

| ColecciÃ³n | QuÃ© guarda | Por quÃ© Mongo y no Postgres |
|-----------|-----------|-----------------------------|
| `focos_snapshots` | Un documento por dÃ­a con todos los focos | Documento embebido evita JOINs |
| `alertas` | Eventos de riesgo (no son tabulares, varÃ­an en campos) | Esquema flexible |
| `ejecuciones_etl` | Traza con logs nested | Logs anidados se modelan mejor como JSON |

Tiene `nosql/schemas/*.json` (JSON Schema para validaciÃ³n), `nosql/init/01_setup_mongo.js` (Ã­ndices y validators) y `nosql/queries/01_consultas.js` (consultas representativas).

### 3.4 Dashboard â€” Streamlit (`dashboard/`)

- `app.py` â†’ la UI: filtros por fecha y paÃ­s, mapa de focos, serie temporal de Ã­ndice, panel de alertas, tabla con detalles.
- `db.py` â†’ wrapper de conexiÃ³n a Postgres y Mongo (usa `PG_CONFIG` y `MONGO_CONFIG` de settings).

Se levanta con `streamlit run dashboard/app.py` (local) o vÃ­a contenedor Docker (`docker compose up streamlit`).

### 3.5 AnalÃ­tica avanzada (`analytics/`)

- `riesgo_analytics.py` â†’ consultas analÃ­ticas, clustering, detecciÃ³n de anomalÃ­as con scikit-learn.

### 3.6 Tests de calidad (`tests/`)

`tests/test_calidad_datos.py` â€” 17 tests categorizados:

- **Completitud** â€” sin nulos en campos crÃ­ticos.
- **Unicidad** â€” sin duplicados por clave natural.
- **Consistencia** â€” coordenadas dentro de Uruguay, humedad 0â€“100%, Ã­ndice 0â€“1.
- **Validez** â€” dominios permitidos (`bajo/moderado/alto/muy_alto`, etc.).
- **Idempotencia** â€” doble carga produce el mismo resultado.
- **CDC** â€” detecta correctamente nuevos registros y modificaciones.

Genera `tests/resultados_tests.json` con mÃ©tricas. **Ãšltima ejecuciÃ³n: 2026-03-19, 20/20 PASS.**

### 3.7 Scheduler y automatizaciÃ³n (`etl/scheduler.py`)

Usa APScheduler para correr extractores y loaders periÃ³dicamente. En servidor se levanta como proceso de fondo (o servicio systemd) para mantener los datos frescos.

### 3.8 Backups (`backups/`)

- `backup.sh` â†’ `pg_dump` de Postgres + `mongodump` de Mongo + tar de configs, todo timestampeado.
- `restore.sh` â†’ restaura desde una carpeta de backup.

### 3.9 Logs (`logs/`)

Cada mÃ³dulo loguea en JSON estructurado vÃ­a `etl/utils/logger.py`. Un log por dÃ­a (`sinia_YYYY-MM-DD.json`). Esto permite hacer `jq` sobre los logs y construir mÃ©tricas operacionales.

### 3.10 Docker (`docker/`)

- `docker-compose.yml` â†’ orquesta los 3 servicios (postgres, mongo, streamlit).
- `Dockerfile.streamlit` â†’ imagen del dashboard.
- `.env` â†’ credenciales (NO se sube a git).
- `.env.example` â†’ plantilla del `.env`.

## 4. Flujo de datos de punta a punta (ejemplo)

QuerÃ©s saber el riesgo de incendio en Rivera para hoy. Esto es lo que pasa por debajo:

```
1. scheduler.py dispara el ciclo a las 03:00 UTC
   â†“
2. extract_forecast.py llama Open-Meteo con (lat=-30.91, lon=-55.55)
   â†’ guarda data/raw/meteo/forecast_rivera_20260511_0300.csv
   â†“
3. extract_cams.py llama CAMS Air Quality para la misma fecha
   â†’ guarda data/raw/cams/cams_rivera_hourly_2026-05-11.csv
   â†“
4. transform_meteo.py lee el forecast, calcula Ã­ndice:
   indice = tempÃ—0.25 + humedadÃ—0.30 + vientoÃ—0.20 + sequiaÃ—0.25
   â†’ guarda data/processed/meteo_procesado_rivera.parquet
   â†“
5. transform_cams.py agrega 24 valores horarios â†’ 1 diario, marca alerta si PM10 > 45
   â†“
6. load_postgres.py hace UPSERT en meteo_diario y calidad_aire_diario
   â†“
7. load_mongo.py guarda snapshot diario en focos_snapshots y
   si hay riesgo "alto/muy_alto" inserta un documento en alertas
   â†“
8. Se registra la ejecuciÃ³n en etl_ejecuciones (Postgres) y
   ejecuciones_etl (Mongo)
   â†“
9. dashboard/app.py refresca: el usuario ve el Ã­ndice de hoy en Rivera
```

Si algo falla en cualquier paso, el logger captura el error con stack trace y la auditorÃ­a queda en estado `error` o `parcial` con el mensaje.

## 5. Decisiones de diseÃ±o que se preguntan en defensa

| DecisiÃ³n | RazÃ³n corta |
|----------|------------|
| Â¿Por quÃ© dos bases (Postgres + Mongo)? | Complementariedad: Postgres es OLAP estructurado; Mongo es operacional con esquema variable (logs, alertas, snapshots). |
| Â¿Por quÃ© Parquet entre transform y load? | CompresiÃ³n + columnar = lectura analÃ­tica rÃ¡pida; preserva tipos exactos. |
| Â¿Por quÃ© UPSERT y no INSERT? | Idempotencia: rerunnable sin duplicados. Habilita reintentos seguros. |
| Â¿Por quÃ© CHECK constraints en las tablas? | Calidad de datos al borde: nada invÃ¡lido entra a la BD aunque el ETL falle. |
| Â¿Por quÃ© auditorÃ­a en `etl_ejecuciones`? | Permite responder "Â¿cuÃ¡ndo corriÃ³ por Ãºltima vez X y con quÃ© resultado?" sin leer logs. |
| Â¿Por quÃ© tres roles Postgres? | Principio de mÃ­nimo privilegio: el dashboard solo lee, el ETL no borra ni hace DDL. |
| Â¿Por quÃ© no sharding? | Volumen actual (~365 reg/aÃ±o/tabla) no lo justifica. Se documenta la estrategia hipotÃ©tica con `fecha` como shard key. |

## 6. Lo que no hace (alcance)

- **No es modelo predictivo** â€” el Ã­ndice es un score determinÃ­stico, no un ML predictor de incendios.
- **No tiene autenticaciÃ³n en el dashboard** â€” corre en red interna, no en internet abierto.
- **No tiene alta disponibilidad** â€” una sola instancia de cada servicio.
- **No procesa imÃ¡genes satelitales raw** â€” usa productos derivados ya procesados por NASA/Copernicus.

Estos lÃ­mites estÃ¡n bien para un proyecto acadÃ©mico y se mencionan como "trabajos futuros" en la defensa.

---

**PrÃ³ximo paso:** [11_SETUP_LOCAL.md](11_SETUP_LOCAL.md) â€” levantar todo esto en tu PC.
