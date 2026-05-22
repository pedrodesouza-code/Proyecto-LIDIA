# SINIA-UY / SONIA-UY

Sistema de Ingenieria de Datos para monitoreo ambiental, focos de calor y riesgo de incendios forestales en Uruguay y la region.

Estado oficial del proyecto: **2026-05-22**.

## Resumen

SINIA-UY integra fuentes reales satelitales, meteorologicas y atmosfericas para construir un pipeline completo de datos:

```text
Fuentes externas
  -> ETL Python
  -> Parquet procesado
  -> PostgreSQL analitico
  -> MongoDB operacional
  -> Tests, reportes y dashboard Streamlit
```

El sistema permite analizar focos de calor, riesgo meteorologico, calidad del aire, precipitacion y cobertura vegetal.

## Alcance Actual

El alcance vigente del repositorio es:

| Pais | Puntos |
|---|---:|
| Uruguay | 19 |
| Brasil | 5 |
| Argentina | 4 |
| Chile | 8 |
| **Total** | **36** |

Uruguay esta cubierto por sus 19 departamentos. Chile se incorpora por su relevancia en eventos volcanicos y transporte atmosferico regional.

## Fuentes De Datos

| Fuente | Uso en el proyecto |
|---|---|
| NASA FIRMS | Focos de calor satelitales historicos y NRT |
| Open-Meteo | Meteorologia historica y pronostico |
| CAMS via Open-Meteo | Calidad del aire, PM10, PM2.5 y AQI |
| CHIRPS | Precipitacion mensual |
| MODIS / AppEEARS | Cobertura vegetal |

## Componentes Principales

| Componente | Ubicacion |
|---|---|
| Configuracion central | `config/settings.py` |
| Extraccion | `etl/extract/` |
| Transformacion | `etl/transform/` |
| Carga PostgreSQL / MongoDB | `etl/load/` |
| Scheduler incremental | `etl/scheduler.py` |
| Modelo SQL | `sql/ddl/` |
| Modelo NoSQL | `nosql/schemas/` |
| Dashboard | `dashboard/app.py` |
| Tests | `tests/test_calidad_datos.py` |
| Reportes de evidencia | `reports/` |

## Evidencia Actual

Ultima validacion local:

```bash
pytest tests -q
```

Resultado validado el `2026-05-22`:

```text
20 passed in 21.12s
```

Reportes principales:

- `reports/carga_completa_ultimo.json`
- `reports/sql_vs_nosql_real_ultimo.json`
- `reports/rendimiento_ultimo.json`
- `reports/backup_restore_ultimo.json`
- `reports/sharding_simulado_ultimo.json`

Metricas destacadas del estado actual:

- FIRMS procesado: `1.946.361` focos.
- Alcance: `ARG`, `BRA`, `CHL`, `URY`.
- Puntos de monitoreo: `36`.
- Tests: `20 PASS / 0 FAIL`.

## Levantamiento Rapido

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar tests:

```bash
pytest tests -q
```

Levantar dashboard:

```bash
streamlit run dashboard/app.py
```

Acceso local:

```text
http://localhost:8501
```

Validar Docker Compose:

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env.example config --quiet
```

## Nota Para Defensa

Los documentos con fecha `2026-05-15` reflejan una sincronizacion historica UTEC de alcance anterior. La fuente de verdad actual del repositorio para defensa es:

- `docs/CIERRE_ENTREGA_2026-05-22.md`
- `docs/ESTADO_ACTUAL_PROYECTO_2026-05-20.md`
- `docs/ENTREGA_EC3_IMPLEMENTACION.md`
- `docs/GUIA_DEFENSA_FINAL.md`
- `docs/MATRIZ_CUMPLIMIENTO_CONSIGNA_2026.md`

La respuesta corta del proyecto:

> SINIA-UY implementa un pipeline de ingenieria de datos con fuentes ambientales reales, ETL modular en Python, persistencia PostgreSQL y MongoDB, validaciones de calidad, idempotencia y CDC, dashboard Streamlit y evidencia reproducible para defensa.
