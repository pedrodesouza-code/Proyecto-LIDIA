# UTEC EC3 DevOps Runbook

## 1. Preparar entorno

```bash
cd /app
cp .env.example .env
python -m devops.install_missing
```

Editar `.env` con credenciales reales. No subir `.env` al repo.
En Jupyter, si los archivos ocultos estan bloqueados, usar `config/utec.env`.

## 1.1 Desplegar cambios al Jupyter UTEC

Desde una maquina con VPN y token de Jupyter:

```bash
export JUPYTER_URL="http://10.200.245.40:18803"
export JUPYTER_TOKEN="PEGAR_TOKEN_SIN_COMILLAS"
python -m devops.deploy_jupyter --remote-dir Proyecto-LIDIA
```

El token aparece normalmente en la URL de Jupyter como `?token=...`.

Variables criticas:

```bash
POSTGRES_HOST=
POSTGRES_PORT=5432
POSTGRES_DB=grp03db
POSTGRES_USER=
POSTGRES_PASSWORD=

MONGO_HOST=
MONGO_PORT=27017
MONGO_DB=grp03db
MONGO_USER=
MONGO_PASSWORD=
```

## 2. Diagnostico completo

```bash
python -m devops.diagnose_env
python -m devops.check_postgres
python -m devops.check_mongo
python -m devops.check_datasets
python -m devops.check_streamlit
```

Todo junto:

```bash
python -m devops.run_all_checks
```

Los logs quedan en:

```text
logs/devops/<run_id>.jsonl
```

## 3. PostgreSQL

Inicializar schemas esperados:

```bash
psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f sql/ddl/00_schemas.sql
```

Validar lectura/escritura:

```bash
python -m devops.check_postgres
```

## 4. MongoDB

Validar conexion, auth, collections e insert/find/delete:

```bash
python -m devops.check_mongo
```

## 5. Streamlit

Dashboard liviano para UTEC:

```bash
python -m streamlit run dashboard/utec_dashboard.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
```

Diagnostico automatico:

```bash
python -m devops.check_streamlit
```

## 6. Datasets

Validar archivos locales y muestra FIRMS shapefile:

```bash
python -m devops.check_datasets
```

## 7. Criterio PASS/FAIL

- PASS: conexion o prueba funcional realizada.
- FAIL: el script imprime causa raiz tecnica y guarda detalle en JSONL.
- Las contrasenas se enmascaran como `***`.
