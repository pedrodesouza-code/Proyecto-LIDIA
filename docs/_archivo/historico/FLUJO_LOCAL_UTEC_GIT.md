# Flujo Local -> GitHub -> UTEC

Este proyecto puede trabajarse en dos entornos distintos:

- Local: desarrollo y pruebas en tu PC con `sinia_uy`
- UTEC: despliegue remoto en `grp03db`

## 1. Trabajar local

Usar `config/.env` con valores locales:

```env
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=sinia_uy

MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DATABASE=sinia_uy
```

Antes de correr el ETL:

```bash
python etl/load/load_postgres.py
python etl/load/load_mongo.py
```

## 2. Subir codigo a GitHub

Revisar cambios:

```bash
git status
```

Crear commit:

```bash
git add <archivos>
git commit -m "mensaje claro"
git push origin <rama>
```

## 3. Actualizar UTEC

En UTEC usar un `.env` remoto con:

```env
PG_HOST=10.200.245.40
PG_PORT=15434
PG_DATABASE=grp03db

MONGO_HOST=10.200.245.40
MONGO_PORT=27023
MONGO_DATABASE=grp03db
MONGO_AUTH_SOURCE=grp03db
```

La primera vez:

```bash
python scripts/crear_bases_datos.py --base-existente
```

Luego de cada `git pull`:

```bash
python etl/load/load_postgres.py
python etl/load/load_mongo.py
```

## 4. Recomendacion

Desarrollar siempre local primero. Subir a UTEC solo cuando el cambio ya funcione en tu PC.
