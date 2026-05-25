# Aporte UTEC EC3 - pedrodesouza-code

Esta carpeta agrega la implementacion validada en el entorno institucional sin
reemplazar los archivos de la entrega principal. Contiene scripts de
diagnostico, carga de staging, carga de dimensiones ambientales, dashboard
Streamlit y configuracion reproducible sin credenciales.

## Entorno Validado

- Jupyter UTEC: proyecto desplegado en `/app/Proyecto-LIDIA`.
- PostgreSQL: conexion, lectura/escritura, schemas e indices validados.
- MongoDB: conexion, autenticacion y pruebas insert/find/delete validadas.
- Streamlit: aplicacion inicia y responde HTTP 200 dentro del entorno.
- Datos crudos: visibles en `/app/Proyecto-LIDIA/data/raw/`.

## Datasets Disponibles En Jupyter

Los binarios de datos no se incluyen en GitHub porque FIRMS contiene un
shapefile de mas de 1 GB y excede los limites normales del repositorio.
Estan cargados en Jupyter UTEC y fueron verificados por el pipeline.

| Fuente | Ubicacion en Jupyter | Estado |
| --- | --- | --- |
| NASA FIRMS | `data/raw/firms/fire_archive_M-C61_740435.*` | Subido y leido, 3.672.055 features |
| Open-Meteo | `data/raw/Open_meteo/` | Subido |
| Calidad del aire | `data/raw/Open_meteo/air_quality_regional.parquet` | Subido |
| CHIRPS | `data/raw/chirps_daily/csv_unificado.csv` | Subido |
| MODIS | `data/raw/MODIS/modis_todos.csv` | Subido |
| Inumet | `data/raw/Inumet/` | Subido |

## Carga Real Verificada

### Staging PostgreSQL

| Tabla | Registros |
| --- | ---: |
| `staging.stg_firms_incendios` | 3.672.055 |
| `staging.stg_openmeteo_clima` | 157.752 |
| `staging.stg_calidad_aire` | 1.630.848 |
| `staging.stg_chirps_precipitacion` | 1.404 |
| `staging.stg_modis_cobertura` | 266 |

Las cuatro cargas ambientales validaron unicidad de `record_hash` sin
duplicados.

### Data Warehouse

| Tabla | Registros |
| --- | ---: |
| `dw.fact_incendio` | 3.672.055 |
| `dw.dim_clima` | 6.573 |
| `dw.dim_calidad_aire` | 17.544 |
| `dw.dim_precipitacion` | 1.872 |
| `dw.dim_cobertura_vegetal` | 140 |

El enlace masivo de todas las dimensiones a `dw.fact_incendio` queda como
trabajo posterior por lotes o mediante tabla bridge. Se validaron 110.000
enlaces climaticos; no se presenta como carga final completa.

## Contenido

- `implementation/devops/`: diagnosticos automáticos UTEC.
- `implementation/etl/cargar_staging_ambiental.py`: carga idempotente de archivos ambientales.
- `implementation/etl/cargar_dw_ambiental.py`: carga de dimensiones y estrategia de enriquecimiento.
- `implementation/etl/cargar_firms_shapefile.py`: carga desde shapefile FIRMS.
- `implementation/dashboard/utec_dashboard.py`: dashboard analitico EC3.
- `implementation/streamlit/app.py`: entrypoint Streamlit institucional.
- `implementation/sql/ddl/`: extensiones de schemas, PostGIS, indices y vistas.
- `implementation/utec.env.example`: variables requeridas sin secretos.

## Ejecucion En Jupyter

La carpeta contiene un aporte separado. Para ejecutar la implementacion ya
desplegada en Jupyter:

```bash
cd /app/Proyecto-LIDIA
python -m devops.run_all_checks
python -m etl.cargar_staging_ambiental --source all
python -m etl.cargar_dw_ambiental --skip-link
python -m streamlit run dashboard/utec_dashboard.py --server.address 0.0.0.0 --server.port 8501
```
