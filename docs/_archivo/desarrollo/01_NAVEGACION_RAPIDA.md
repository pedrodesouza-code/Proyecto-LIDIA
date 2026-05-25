# Navegacion rapida del proyecto

Usa este archivo cuando abras el proyecto y necesites ubicarte rapido.

## Flujo del sistema

```text
APIs externas
  -> data/raw/
  -> etl/extract/
  -> etl/transform/
  -> data/processed/
  -> etl/load/
  -> PostgreSQL + MongoDB
  -> dashboard/
  -> tests/ + reports/
```

## Carpetas principales

| Carpeta | Que contiene | Para que abrirla |
|---|---|---|
| `config/` | Configuracion central | Ver paises, puntos, rutas, pesos y conexiones |
| `etl/` | Extraccion, transformacion y carga | Explicar el pipeline |
| `sql/` | DDL, indices, vistas y consultas | Defender base de datos |
| `nosql/` | MongoDB, schemas y queries | Defender NoSQL |
| `dashboard/` | App Streamlit y capa de datos | Explicar visualizacion |
| `data/raw/` | Datos crudos descargados | Mostrar trazabilidad |
| `data/processed/` | Parquets procesados | Mostrar salida del ETL y fallback |
| `tests/` | Tests de calidad | Probar datos e idempotencia |
| `reports/` | Reportes de verificacion | Mostrar evidencia |
| `docs/` | Documentacion | Estudiar y preparar defensa |
| `docker/` | Docker Compose | Levantar servicios |
| `scripts/` | Herramientas auxiliares | Verificar, medir, backup |

## Archivos que tenes que dominar

| Tema | Archivo |
|---|---|
| Configuracion | `config/settings.py` |
| Modelo relacional | `sql/ddl/02_schema.sql` |
| Indices | `sql/ddl/03_indices.sql` |
| Vistas | `sql/ddl/04_vistas.sql` |
| Transformacion FIRMS | `etl/transform/transform_firms.py` |
| Transformacion meteorologica | `etl/transform/transform_meteo.py` |
| Transformacion CAMS | `etl/transform/transform_cams.py` |
| Carga PostgreSQL | `etl/load/load_postgres.py` |
| Dashboard | `dashboard/app.py` |
| Datos del dashboard | `dashboard/db.py` |
| Tests | `tests/test_calidad_datos.py` |

## Comandos utiles

```bash
python -m pytest tests/test_calidad_datos.py -q
python tests/test_calidad_datos.py
python -m streamlit run dashboard/app.py --server.port 8502
git status --short
```

## Frase corta para defensa

> SINIA-UY toma datos ambientales reales, los guarda crudos, los transforma, los valida, los carga en bases SQL/NoSQL y los explota en un dashboard.
