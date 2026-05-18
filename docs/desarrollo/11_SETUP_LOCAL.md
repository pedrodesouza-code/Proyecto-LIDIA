# 11 — Setup local en tu máquina (Windows)

Objetivo: dejar Postgres + Mongo corriendo en tu PC, el ETL ejecutándose y el dashboard accesible en `http://localhost:8501`. Una vez que esto funcione, todo lo demás (deploy a UTEC, git workflow) es replicar la misma idea.

## Prerrequisitos (instalar una sola vez)

| Software | Versión mínima | Descarga | Para qué sirve |
|----------|----------------|----------|----------------|
| Docker Desktop | 4.20+ | docker.com/products/docker-desktop | Levanta Postgres y Mongo en contenedores aislados |
| Python | 3.11 o 3.12 | python.org | Correr scripts de ETL en tu PC |
| Git | 2.40+ | git-scm.com | Versionado |
| VS Code | última | code.visualstudio.com | Editor recomendado |
| DBeaver (opcional) | última | dbeaver.io | Cliente gráfico para ver Postgres y Mongo |

**Verificá la instalación abriendo PowerShell:**

```powershell
docker --version           # Docker version 24.x o superior
docker compose version     # Docker Compose version v2.x
python --version           # Python 3.11.x o 3.12.x
git --version              # git version 2.x
```

Si alguno no responde, reinstalá ese.

## Paso 1 — Configurar el .env

El proyecto ya tiene `docker/.env` con valores por defecto. **Antes de seguir, decidí**:

1. Si vas a trabajar solo localmente con datos de prueba: las credenciales por defecto están bien. Saltá al Paso 2.
2. Si esto va a subirse a un repo público (aunque sea privado en GitHub): **cambiá todas las contraseñas** del `.env` ahora. El `.env` no se sube por estar en `.gitignore`, pero conviene tener contraseñas únicas no triviales.

Las contraseñas que aparecen en `docker/.env`:

```
PG_SUPERPASS=postgres_super_2026          ← cambiar
PG_PASSWORD=sinia_etl_2026                ← cambiar
PG_DASH_PASSWORD=sinia_dash_2026          ← cambiar
MONGO_ROOT_PASS=mongo_admin_2026          ← cambiar
MONGO_PASSWORD=sinia_etl_2026             ← cambiar
FIRMS_MAP_KEY=tu_api_key_aqui              ← tu API key de NASA FIRMS
```

> Nota sobre la `FIRMS_MAP_KEY`: no se versiona una clave real. Si en algún momento una clave queda expuesta públicamente, regenerala en `https://firms.modaps.eosdis.nasa.gov/api/map_key/`.

## Paso 2 — Levantar Postgres y Mongo con Docker

Abrí PowerShell en la carpeta del proyecto:

```powershell
cd "C:\Users\rqf18\OneDrive\Documentos\api\Custom Office Templates\EjercicioSQL\Escritorio\PROYECTO INGIENERIA DE DATOS\SONIA-UY"
cd docker
docker compose up -d postgres mongo
```

`-d` significa "detached" (en segundo plano). Esperá ~20 segundos a que pasen los healthchecks. Verificá:

```powershell
docker compose ps
```

Deberías ver:

```
NAME             STATUS                  PORTS
sinia_postgres   Up 30s (healthy)        0.0.0.0:5432->5432/tcp
sinia_mongo      Up 30s (healthy)        0.0.0.0:27017->27017/tcp
```

Si Postgres no está `healthy` en 1 minuto, mirá los logs:

```powershell
docker compose logs postgres
```

### Qué pasó por debajo

Cuando Postgres arrancó por primera vez, Docker leyó los archivos del directorio `sql/ddl/` y `sql/dml/` (montados como volumen en `/docker-entrypoint-initdb.d/`) y los ejecutó en orden:

1. `01_roles.sql` — creó `sinia_readonly`, `sinia_etl`, `sinia_admin` + usuarios sin password versionado.
2. `02_set_app_passwords.sh` — asignó passwords desde variables de entorno (`PG_PASSWORD`, `PG_DASH_PASSWORD`).
3. `02_schema.sql` — creó las 8 tablas con CHECK constraints y triggers.
4. `03_indices.sql` — creó índices para queries analíticas.
5. `04_vistas.sql` — creó vistas (seguras y analíticas).
6. `05_seed.sql` (= `dml/01_seed_puntos.sql`) — insertó los 19 puntos de monitoreo.

Mongo también ejecutó `nosql/init/01_setup_mongo.js`.

**Importante**: estos scripts se ejecutan **solo en el primer arranque**, cuando el volumen está vacío. Si después modificás el schema, hay dos opciones:

- (a) Hacer la migración con un script ALTER que aplicás manualmente.
- (b) Borrar el volumen y dejar que recree desde cero (perdés los datos):
  ```powershell
  docker compose down -v   # ← borra todo
  docker compose up -d postgres mongo
  ```

## Paso 3 — Verificar las bases de datos visualmente

### Opción A — psql y mongosh (rápido, terminal)

**Postgres:**
```powershell
docker exec -it sinia_postgres psql -U postgres -d sinia_uy
```

Una vez dentro:
```sql
\dt                                     -- lista todas las tablas
SELECT COUNT(*) FROM puntos_monitoreo;  -- debería decir 19
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

### Opción B — DBeaver (gráfico, recomendado)

1. Abrí DBeaver → New Connection → PostgreSQL.
2. Datos:
   - Host: `localhost`
   - Port: `5432`
   - Database: `sinia_uy`
   - Username: `postgres`
   - Password: `postgres_super_2026` (o la que pusiste)
3. Test Connection → Finish.
4. Para Mongo: New Connection → MongoDB. Host `localhost`, Port `27017`, Database `sinia_uy`, Auth Database `admin`, user `mongo_admin`, password `mongo_admin_2026`.

DBeaver te deja explorar tablas, hacer queries y editar datos visualmente.

## Paso 4 — Instalar dependencias Python

Creá un entorno virtual para no contaminar tu Python global:

```powershell
cd "C:\Users\rqf18\OneDrive\Documentos\api\Custom Office Templates\EjercicioSQL\Escritorio\PROYECTO INGIENERIA DE DATOS\SONIA-UY"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Cuando esté activado el venv vas a ver `(.venv)` al inicio del prompt. Para desactivarlo: `deactivate`.

**Tip:** en VS Code abrí la paleta (Ctrl+Shift+P) → "Python: Select Interpreter" → elegí el de `.venv`.

## Paso 5 — Configurar el .env del ETL Python

El ETL Python lee de `config/.env` (distinto del `docker/.env`). Copiá:

```powershell
copy docker\.env.example config\.env
```

Editá `config/.env` con las mismas credenciales del `docker/.env` pero **apuntando a localhost**:

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

Por qué `localhost` y no `postgres`: en tu PC los contenedores exponen los puertos a `localhost`. Dentro del contenedor de Streamlit (que corre en la misma red Docker) los hosts son `postgres` y `mongo` por DNS interno.

## Paso 6 — Correr el ETL la primera vez

Activá el venv si no lo está:

```powershell
.venv\Scripts\activate
```

Extraé datos de las APIs (tarda algunos minutos, hace decenas de requests):

```powershell
python etl/extract/extract_firms.py
python etl/extract/extract_meteo.py
python etl/extract/extract_cams.py
python etl/extract/extract_forecast.py
```

Estos comandos descargan archivos a `data/raw/`. Si una API está caída o respondió mal, vas a ver el error en logs. Reintentá.

Transformá:

```powershell
python etl/transform/transform_firms.py
python etl/transform/transform_meteo.py
python etl/transform/transform_cams.py
```

Salen archivos `.parquet` en `data/processed/`. Verificá:

```powershell
dir data\processed
```

Cargá a las BDs:

```powershell
python etl/load/load_postgres.py
python etl/load/load_mongo.py
```

Esto hace el UPSERT idempotente. Vas a ver logs con `INSERT`/`UPDATE`/`SKIP` por registro o batch.

Verificá que cargó:

```powershell
docker exec -it sinia_postgres psql -U postgres -d sinia_uy -c "SELECT COUNT(*) FROM focos_calor;"
docker exec -it sinia_postgres psql -U postgres -d sinia_uy -c "SELECT COUNT(*) FROM meteo_diario;"
```

## Paso 7 — Correr los tests de calidad

```powershell
python tests/test_calidad_datos.py
```

Esto genera `tests/resultados_tests.json`. La meta es **17/17 PASS**. Si alguno falla, mirá la sección `mensaje` del JSON: te dice exactamente qué validación no se cumplió.

Versión más detallada:

```powershell
pytest tests/test_calidad_datos.py -v
```

## Paso 8 — Levantar el dashboard

**Opción A — local con streamlit directo (rápido, hot reload):**

```powershell
streamlit run dashboard/app.py
```

Abre automáticamente `http://localhost:8501`. Cualquier cambio en `dashboard/app.py` se refresca solo.

**Opción B — todo en Docker (más cerca de producción):**

```powershell
cd docker
docker compose up -d
```

Esto levanta también el contenedor `sinia_dashboard` con Streamlit. Abrí `http://localhost:8501`.

## Paso 9 — Levantar el scheduler (opcional, para simular automatización)

En otra terminal con el venv activo:

```powershell
python etl/scheduler.py
```

Se queda corriendo y dispara los extractores y loaders según el cron configurado. Ctrl+C lo para.

## Comandos útiles que vas a usar todos los días

| Acción | Comando |
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

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `docker compose up` dice "port 5432 already in use" | Tenés Postgres nativo corriendo | Pará el Postgres nativo o cambiá `PG_PORT=5433` en `.env` |
| `psycopg2.OperationalError: could not connect` | Postgres no arrancó | `docker compose logs postgres` y mirá el error |
| `pymongo.errors.ServerSelectionTimeoutError` | Mongo no levantó o credenciales mal | Verificá `docker compose ps` y el `.env` |
| Streamlit muestra "No hay datos" | No corriste el ETL | Volvé al Paso 6 |
| Healthcheck de Mongo falla | Imagen mongo:7.0 a veces tarda | Esperá 30s más; si persiste, `docker compose restart mongo` |
| Tests fallan con "parquet not found" | No corrió transform | Volvé al Paso 6 |

## Cuando todo funcione localmente

Tenés que poder responder "sí" a estas tres preguntas:

1. `docker compose ps` muestra Postgres y Mongo `healthy`.
2. `python tests/test_calidad_datos.py` da 17/17 PASS.
3. `streamlit run dashboard/app.py` abre el dashboard y se ve el mapa con datos.

Cuando los tres pasan, estás listo para el siguiente paso: versionado con git.

---

**Próximo paso:** [12_WORKFLOW_GIT.md](12_WORKFLOW_GIT.md) — versionar todo y subirlo a GitHub.
