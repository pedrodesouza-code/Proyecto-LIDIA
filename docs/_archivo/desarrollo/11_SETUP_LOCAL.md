# 11 â€” Setup local en tu mÃ¡quina (Windows)

Objetivo: dejar Postgres + Mongo corriendo en tu PC, el ETL ejecutÃ¡ndose y el dashboard accesible en `http://localhost:8501`. Una vez que esto funcione, todo lo demÃ¡s (deploy a UTEC, git workflow) es replicar la misma idea.

## Prerrequisitos (instalar una sola vez)

| Software | VersiÃ³n mÃ­nima | Descarga | Para quÃ© sirve |
|----------|----------------|----------|----------------|
| Docker Desktop | 4.20+ | docker.com/products/docker-desktop | Levanta Postgres y Mongo en contenedores aislados |
| Python | 3.11 o 3.12 | python.org | Correr scripts de ETL en tu PC |
| Git | 2.40+ | git-scm.com | Versionado |
| VS Code | Ãºltima | code.visualstudio.com | Editor recomendado |
| DBeaver (opcional) | Ãºltima | dbeaver.io | Cliente grÃ¡fico para ver Postgres y Mongo |

**VerificÃ¡ la instalaciÃ³n abriendo PowerShell:**

```powershell
docker --version           # Docker version 24.x o superior
docker compose version     # Docker Compose version v2.x
python --version           # Python 3.11.x o 3.12.x
git --version              # git version 2.x
```

Si alguno no responde, reinstalÃ¡ ese.

## Paso 1 â€” Configurar el .env

El proyecto ya tiene `docker/.env` con valores por defecto. **Antes de seguir, decidÃ­**:

1. Si vas a trabajar solo localmente con datos de prueba: las credenciales por defecto estÃ¡n bien. SaltÃ¡ al Paso 2.
2. Si esto va a subirse a un repo pÃºblico (aunque sea privado en GitHub): **cambiÃ¡ todas las contraseÃ±as** del `.env` ahora. El `.env` no se sube por estar en `.gitignore`, pero conviene tener contraseÃ±as Ãºnicas no triviales.

Las contraseÃ±as que aparecen en `docker/.env`:

```
PG_SUPERPASS=postgres_super_2026          â† cambiar
PG_PASSWORD=sinia_etl_2026                â† cambiar
PG_DASH_PASSWORD=sinia_dash_2026          â† cambiar
MONGO_ROOT_PASS=mongo_admin_2026          â† cambiar
MONGO_PASSWORD=sinia_etl_2026             â† cambiar
FIRMS_MAP_KEY=tu_api_key_aqui              â† tu API key de NASA FIRMS
```

> Nota sobre la `FIRMS_MAP_KEY`: no se versiona una clave real. Si en algÃºn momento una clave queda expuesta pÃºblicamente, regenerala en `https://firms.modaps.eosdis.nasa.gov/api/map_key/`.

## Paso 2 â€” Levantar Postgres y Mongo con Docker

AbrÃ­ PowerShell en la carpeta del proyecto:

```powershell
cd "C:\Users\rqf18\OneDrive\Documentos\api\Custom Office Templates\EjercicioSQL\Escritorio\PROYECTO INGIENERIA DE DATOS\SONIA-UY"
cd docker
docker compose up -d postgres mongo
```

`-d` significa "detached" (en segundo plano). EsperÃ¡ ~20 segundos a que pasen los healthchecks. VerificÃ¡:

```powershell
docker compose ps
```

DeberÃ­as ver:

```
NAME             STATUS                  PORTS
sinia_postgres   Up 30s (healthy)        0.0.0.0:5432->5432/tcp
sinia_mongo      Up 30s (healthy)        0.0.0.0:27017->27017/tcp
```

Si Postgres no estÃ¡ `healthy` en 1 minuto, mirÃ¡ los logs:

```powershell
docker compose logs postgres
```

### QuÃ© pasÃ³ por debajo

Cuando Postgres arrancÃ³ por primera vez, Docker leyÃ³ los archivos del directorio `sql/ddl/` y `sql/dml/` (montados como volumen en `/docker-entrypoint-initdb.d/`) y los ejecutÃ³ en orden:

1. `01_roles.sql` â€” creÃ³ `sinia_readonly`, `sinia_etl`, `sinia_admin` + usuarios sin password versionado.
2. `02_set_app_passwords.sh` â€” asignÃ³ passwords desde variables de entorno (`PG_PASSWORD`, `PG_DASH_PASSWORD`).
3. `02_schema.sql` â€” creÃ³ las 8 tablas con CHECK constraints y triggers.
4. `03_indices.sql` â€” creÃ³ Ã­ndices para queries analÃ­ticas.
5. `04_vistas.sql` â€” creÃ³ vistas (seguras y analÃ­ticas).
6. `05_seed.sql` (= `dml/01_seed_puntos.sql`) â€” insertÃ³ los 19 puntos de monitoreo.

Mongo tambiÃ©n ejecutÃ³ `nosql/init/01_setup_mongo.js`.

**Importante**: estos scripts se ejecutan **solo en el primer arranque**, cuando el volumen estÃ¡ vacÃ­o. Si despuÃ©s modificÃ¡s el schema, hay dos opciones:

- (a) Hacer la migraciÃ³n con un script ALTER que aplicÃ¡s manualmente.
- (b) Borrar el volumen y dejar que recree desde cero (perdÃ©s los datos):
  ```powershell
  docker compose down -v   # â† borra todo
  docker compose up -d postgres mongo
  ```

## Paso 3 â€” Verificar las bases de datos visualmente

### OpciÃ³n A â€” psql y mongosh (rÃ¡pido, terminal)

**Postgres:**
```powershell
docker exec -it sinia_postgres psql -U postgres -d sinia_uy
```

Una vez dentro:
```sql
\dt                                     -- lista todas las tablas
SELECT COUNT(*) FROM puntos_monitoreo;  -- deberÃ­a decir 19
\d focos_calor                          -- describe la tabla focos_calor
SELECT * FROM puntos_monitoreo LIMIT 5;
\q                                      -- salir
```

**Mongo:**
```powershell
docker exec -it sinia_mongo mongosh -u mongo_admin -p mongo_admin_2026
```

Una vez dentro:
```javascript
use sinia_uy
show collections                  // alertas, ejecuciones_etl, focos_snapshots
db.alertas.countDocuments()       // 0 hasta que cargues datos
exit
```

### OpciÃ³n B â€” DBeaver (grÃ¡fico, recomendado)

1. AbrÃ­ DBeaver â†’ New Connection â†’ PostgreSQL.
2. Datos:
   - Host: `localhost`
   - Port: `5432`
   - Database: `sinia_uy`
   - Username: `postgres`
   - Password: `postgres_super_2026` (o la que pusiste)
3. Test Connection â†’ Finish.
4. Para Mongo: New Connection â†’ MongoDB. Host `localhost`, Port `27017`, Database `sinia_uy`, Auth Database `admin`, user `mongo_admin`, password `mongo_admin_2026`.

DBeaver te deja explorar tablas, hacer queries y editar datos visualmente.

## Paso 4 â€” Instalar dependencias Python

CreÃ¡ un entorno virtual para no contaminar tu Python global:

```powershell
cd "C:\Users\rqf18\OneDrive\Documentos\api\Custom Office Templates\EjercicioSQL\Escritorio\PROYECTO INGIENERIA DE DATOS\SONIA-UY"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Cuando estÃ© activado el venv vas a ver `(.venv)` al inicio del prompt. Para desactivarlo: `deactivate`.

**Tip:** en VS Code abrÃ­ la paleta (Ctrl+Shift+P) â†’ "Python: Select Interpreter" â†’ elegÃ­ el de `.venv`.

## Paso 5 â€” Configurar el .env del ETL Python

El ETL Python lee de `config/.env` (distinto del `docker/.env`). CopiÃ¡:

```powershell
copy docker\.env.example config\.env
```

EditÃ¡ `config/.env` con las mismas credenciales del `docker/.env` pero **apuntando a localhost**:

```
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=sinia_uy
PG_USER=sinia_etl_user
PG_PASSWORD=sinia_etl_2026

MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DATABASE=sinia_uy
MONGO_USER=sinia_etl_user
MONGO_PASSWORD=sinia_etl_2026

FIRMS_MAP_KEY=tu_api_key_aqui
LOG_LEVEL=INFO
```

Por quÃ© `localhost` y no `postgres`: en tu PC los contenedores exponen los puertos a `localhost`. Dentro del contenedor de Streamlit (que corre en la misma red Docker) los hosts son `postgres` y `mongo` por DNS interno.

## Paso 6 â€” Correr el ETL la primera vez

ActivÃ¡ el venv si no lo estÃ¡:

```powershell
.venv\Scripts\activate
```

ExtraÃ© datos de las APIs (tarda algunos minutos, hace decenas de requests):

```powershell
python etl/extract/extract_firms.py
python etl/extract/extract_meteo.py
python etl/extract/extract_cams.py
python etl/extract/extract_forecast.py
```

Estos comandos descargan archivos a `data/raw/`. Si una API estÃ¡ caÃ­da o respondiÃ³ mal, vas a ver el error en logs. ReintentÃ¡.

TransformÃ¡:

```powershell
python etl/transform/transform_firms.py
python etl/transform/transform_meteo.py
python etl/transform/transform_cams.py
```

Salen archivos `.parquet` en `data/processed/`. VerificÃ¡:

```powershell
dir data\processed
```

CargÃ¡ a las BDs:

```powershell
python etl/load/load_postgres.py
python etl/load/load_mongo.py
```

Esto hace el UPSERT idempotente. Vas a ver logs con `INSERT`/`UPDATE`/`SKIP` por registro o batch.

VerificÃ¡ que cargÃ³:

```powershell
docker exec -it sinia_postgres psql -U postgres -d sinia_uy -c "SELECT COUNT(*) FROM focos_calor;"
docker exec -it sinia_postgres psql -U postgres -d sinia_uy -c "SELECT COUNT(*) FROM meteo_diario;"
```

## Paso 7 â€” Correr los tests de calidad

```powershell
python tests/test_calidad_datos.py
```

Esto genera `tests/resultados_tests.json`. La meta es **20/20 PASS**. Si alguno falla, mirÃ¡ la secciÃ³n `mensaje` del JSON: te dice exactamente quÃ© validaciÃ³n no se cumpliÃ³.

VersiÃ³n mÃ¡s detallada:

```powershell
pytest tests/test_calidad_datos.py -v
```

## Paso 8 â€” Levantar el dashboard

**OpciÃ³n A â€” local con streamlit directo (rÃ¡pido, hot reload):**

```powershell
streamlit run dashboard/app.py
```

Abre automÃ¡ticamente `http://localhost:8501`. Cualquier cambio en `dashboard/app.py` se refresca solo.

**OpciÃ³n B â€” todo en Docker (mÃ¡s cerca de producciÃ³n):**

```powershell
cd docker
docker compose up -d
```

Esto levanta tambiÃ©n el contenedor `sinia_dashboard` con Streamlit. AbrÃ­ `http://localhost:8501`.

## Paso 9 â€” Levantar el scheduler (opcional, para simular automatizaciÃ³n)

En otra terminal con el venv activo:

```powershell
python etl/scheduler.py
```

Se queda corriendo y dispara los extractores y loaders segÃºn el cron configurado. Ctrl+C lo para.

## Comandos Ãºtiles que vas a usar todos los dÃ­as

| AcciÃ³n | Comando |
|--------|---------|
| Ver containers corriendo | `docker compose ps` |
| Ver logs de Postgres | `docker compose logs -f postgres` |
| Apagar containers (preserva datos) | `docker compose stop` |
| Reanudar containers | `docker compose start` |
| Reiniciar un servicio | `docker compose restart postgres` |
| Borrar todo (incluyendo datos) | `docker compose down -v` |
| Entrar a Postgres por terminal | `docker exec -it sinia_postgres psql -U postgres -d sinia_uy` |
| Entrar a Mongo por terminal | `docker exec -it sinia_mongo mongosh -u mongo_admin -p mongo_admin_2026` |
| Backup completo | `bash backups/backup.sh` (necesita Git Bash o WSL en Windows) |

## Errores frecuentes en local

| SÃ­ntoma | Causa probable | SoluciÃ³n |
|---------|----------------|----------|
| `docker compose up` dice "port 5432 already in use" | TenÃ©s Postgres nativo corriendo | ParÃ¡ el Postgres nativo o cambiÃ¡ `PG_PORT=5433` en `.env` |
| `psycopg2.OperationalError: could not connect` | Postgres no arrancÃ³ | `docker compose logs postgres` y mirÃ¡ el error |
| `pymongo.errors.ServerSelectionTimeoutError` | Mongo no levantÃ³ o credenciales mal | VerificÃ¡ `docker compose ps` y el `.env` |
| Streamlit muestra "No hay datos" | No corriste el ETL | VolvÃ© al Paso 6 |
| Healthcheck de Mongo falla | Imagen mongo:7.0 a veces tarda | EsperÃ¡ 30s mÃ¡s; si persiste, `docker compose restart mongo` |
| Tests fallan con "parquet not found" | No corriÃ³ transform | VolvÃ© al Paso 6 |

## Cuando todo funcione localmente

TenÃ©s que poder responder "sÃ­" a estas tres preguntas:

1. `docker compose ps` muestra Postgres y Mongo `healthy`.
2. `python tests/test_calidad_datos.py` da 20/20 PASS.
3. `streamlit run dashboard/app.py` abre el dashboard y se ve el mapa con datos.

Cuando los tres pasan, estÃ¡s listo para el siguiente paso: versionado con git.

---

**PrÃ³ximo paso:** [12_WORKFLOW_GIT.md](12_WORKFLOW_GIT.md) â€” versionar todo y subirlo a GitHub.
