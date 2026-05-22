# SINIA-SA — Referencia Técnica del Pipeline
**UTEC ITR Norte · Quinto Semestre 2026**

Documentación técnica del sistema para desarrolladores: migración UY → SA, estructura del pipeline, puntos de monitoreo y decisiones de diseño.

---

## Resumen de la migración (Uruguay → Sudamérica)

Migración incremental de SINIA-UY (5 puntos Uruguay) a SINIA-SA (18 puntos, 6 países).
El 80% del código fue reutilizado. Solo se cambió lo estrictamente necesario.

---

## Archivos modificados

| Archivo | Tipo de cambio | Razón |
|---|---|---|
| `config/settings.py` | Expand | Reemplaza `COUNTRY_CODE`/`PUNTOS_METEO`/`TIMEZONE` por equivalentes SA |
| `etl/extract/extract_firms.py` | Fix | `COUNTRY_CODE` → `SA_BBOX` (bbox soporta multi-país) |
| `etl/transform/transform_firms.py` | Blocker fix | Filtro geográfico Uruguay → Sudamérica + asignación de `pais` |
| `etl/extract/extract_cams.py` | Fix | `timezone: America/Montevideo` → `UTC` |
| `etl/extract/extract_meteo.py` | Fix | `timezone: America/Montevideo` → `UTC` |
| `etl/load/load_postgres.py` | Expand | Agrega `pais` en INSERT focos_calor + 2 funciones nuevas + batch 50K filas |
| `etl/load/load_mongo.py` | Fix | Elimina "Uruguay" hardcoded + ruta meteo genérica |
| `etl/scheduler.py` | Expand | UTC timezone + job CHIRPS mensual + CDC watermark |
| `sql/ddl/02_schema.sql` | Expand | Elimina CHECK Uruguay, agrega `pais`, 3 tablas nuevas |
| `sql/dml/01_seed_puntos.sql` | Replace | 5 puntos UY → 18 puntos SA en 6 países |
| `dashboard/app.py` | Expand | Selector de año, página "Comparativo por País", página "Fuentes y Datos Crudos" |
| `dashboard/db.py` | Expand | `cargar_focos()` acepta fecha_inicio/fecha_fin/pais + LIMIT 100K ORDER BY FRP DESC |

## Archivos nuevos

| Archivo | Descripción |
|---|---|
| `etl/extract/extract_chirps.py` | Extractor CHIRPS precipitación mensual (ClimateSERV API) |
| `etl/extract/extract_modis.py` | Extractor MODIS MCD12Q1 cobertura vegetal (NASA AppEEARS) |
| `etl/carga_historica.py` | Carga histórica 2018–2023 en lotes por año |
| `etl/sincronizar_mongo_historico.py` | Sync PostgreSQL → MongoDB para años históricos |
| `sql/ddl/05_migracion_sa.sql` | ALTER TABLE para migrar base existente sin perder datos |

## Componentes sin cambios

| Módulo | Nota |
|---|---|
| `etl/transform/transform_meteo.py` | Fórmula de riesgo válida para SA |
| `etl/transform/transform_cams.py` | Trabaja sobre cualquier punto |
| `etl/utils/logger.py` | Logger JSON estructurado |
| `sql/ddl/01_roles.sql` | Roles y permisos |
| `sql/ddl/03_indices.sql` | Índices analíticos |
| `sql/ddl/04_vistas.sql` | 8 vistas SQL |
| `sql/queries/01_analiticas.sql` | 10 consultas analíticas |
| `tests/test_calidad_datos.py` | Tests de calidad e idempotencia |

---

## Alcance geográfico

**Bounding box SA:** `lon_min=-82.0, lat_min=-56.0, lon_max=-34.0, lat_max=13.0`

### 18 puntos de monitoreo SA

| País | Ciudad | Lat | Lon | Justificación |
|---|---|---|---|---|
| BRA | Cuiabá | -15.60 | -56.10 | Cerrado — máxima actividad de incendios |
| BRA | Porto Alegre | -30.03 | -51.23 | Frontera sur |
| BRA | Manaus | -3.10 | -60.02 | Amazonia occidental |
| BRA | Campo Grande | -20.47 | -54.62 | Pantanal |
| BRA | Brasília | -15.78 | -47.93 | Cerrado central |
| BOL | Santa Cruz | -17.80 | -63.17 | Chiquitanía — incendios críticos 2019/2020 |
| BOL | Trinidad | -14.83 | -64.90 | Beni amazónico |
| BOL | La Paz | -16.50 | -68.15 | Capital administrativa |
| PRY | Asunción | -25.29 | -57.64 | Corredor central |
| PRY | Concepción | -23.41 | -57.43 | Chaco norte |
| ARG | Salta | -24.79 | -65.41 | Yungas y chaco salteño |
| ARG | Posadas | -27.37 | -55.90 | Selva misionera |
| ARG | Buenos Aires | -34.61 | -58.37 | Referencia sur |
| ARG | Mendoza | -32.89 | -68.85 | Interfaz urbano-forestal |
| CHL | Santiago | -33.46 | -70.65 | Región Metropolitana |
| CHL | Temuco | -38.74 | -72.59 | La Araucanía — zona forestal crítica |
| PER | Lima | -12.06 | -77.04 | Capital costera |
| PER | Cusco | -13.53 | -71.97 | Sur andino |

### 5 puntos Uruguay legacy

| Ciudad | Lat | Lon |
|---|---|---|
| Rivera | -31.38 | -55.98 |
| Artigas | -30.40 | -56.47 |
| Tacuarembó | -31.73 | -55.98 |
| Paysandú | -32.32 | -58.08 |
| Montevideo | -34.90 | -56.19 |

---

## Estado de datos (2026-03-22)

| Tabla | Registros |
|---|---|
| focos_calor | 19.510.222 (2018–2024) |
| meteo_diario | 46.243 |
| calidad_aire_diario | 45.931 |
| precipitacion_mensual | 1.404 |
| cobertura_vegetal | 126 |
| puntos_monitoreo | 23 |
| paises_referencia | 7 |
| MongoDB focos_snapshots | 2.521 docs |

---

## Vistas SQL (8 total)

| Vista | Descripción |
|---|---|
| `v_riesgo_actual` | Último registro de riesgo por punto |
| `v_riesgo_historico` | Histórico de riesgo con clasificación |
| `v_focos_resumen_diario` | Resumen diario de focos por zona |
| `v_alertas_calidad_aire` | Días sobre límite OMS de PM10 |
| `v_dias_criticos` | Días con riesgo ALTO o MUY ALTO |
| `v_forecast_riesgo` | Pronóstico de riesgo 7 días |
| `v_riesgo_por_pais` | Comparativo mensual de riesgo por país |
| `v_focos_por_pais_mes` | Focos mensuales por país (materializada) |

---

## Scheduler — frecuencia de actualización

| Job | Frecuencia | Fuente |
|---|---|---|
| FIRMS NRT | Cada 3 horas | NASA FIRMS API |
| Meteorología | Cada 1 hora | Open-Meteo Forecast |
| Calidad del aire | Cada 1 hora | CAMS vía Open-Meteo |
| CHIRPS precipitación | Cada 30 días | ClimateSERV API |

CDC watermark: `_get_watermark()` lee `MAX(fecha)` de PG antes de cada descarga.

---

## Decisiones de diseño clave

| Decisión | Justificación |
|---|---|
| PostgreSQL para analítica | SQL estándar, vistas materializadas, índices funcionales |
| MongoDB para snapshots | Documentos flexibles, arrays embebidos, sin JOINs para consultas operativas |
| Vista materializada `v_focos_por_pais_mes` | Reduce tiempo de consulta de 6.270ms → 0,4ms |
| Batch inserts 50K (`execute_values`) | Evita crash de PG con transacciones de 2,4M+ filas |
| Watermark CDC | Re-lanzar el scheduler no reprocesa datos ya cargados |
| Reordenamiento `_BBOX_PAISES` | URY/PRY/BOL primero, BRA último — evita absorción por bbox grande |
| Parquet como staging | Desacopla APIs de la carga; permite reprocesar sin re-llamar APIs |
| UTC como timezone | Neutro para 6 países con distintos husos horarios |

---

## Bugs corregidos relevantes

| Fecha | Bug | Solución |
|---|---|---|
| 2026-03-20 | `cargar_focos_calor` crasheaba con 2,4M filas (server closed connection) | Reescrito de fila-por-fila a `execute_values` con commits cada 50K |
| 2026-03-20 | `decimal.Decimal` no serializable en MongoDB sync | Psycopg2 type adapter para convertir a float |
| 2026-03-19 | `select_dtypes(include=["object","str"])` fallaba en pandas 3.x | Cambiado a `include=["object"]` |
| 2026-03-19 | Focos de Paraguay y Bolivia asignados a Brasil | Reordenado `_BBOX_PAISES` con países pequeños primero |
| 2026-03-19 | CHIRPS polling devolvía `[100.0]` (float, no dict) | Corregido parsing y agregación diario→mensual |

---

## Cómo aplicar la migración en una instalación nueva

```bash
# 1. Iniciar PostgreSQL
"/c/Program Files/PostgreSQL/16/bin/pg_ctl" start -D "/c/Program Files/PostgreSQL/16/data" -l "/c/Program Files/PostgreSQL/16/data/log/pg_start.log"

# 2. Crear esquema base
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" -U postgres -d sinia_uy -f sql/ddl/01_roles.sql
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" -U postgres -d sinia_uy -f sql/ddl/02_schema.sql
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" -U postgres -d sinia_uy -f sql/ddl/03_indices.sql
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" -U postgres -d sinia_uy -f sql/ddl/04_vistas.sql

# 3. Si ya existe la BD de la versión UY — aplicar migración SA
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" -U postgres -d sinia_uy -f sql/ddl/05_migracion_sa.sql

# 4. Cargar puntos de monitoreo
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" -U postgres -d sinia_uy -f sql/dml/01_seed_puntos.sql

# 5. Verificar
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" -U postgres -d sinia_uy -c "SELECT pais, COUNT(*) FROM puntos_monitoreo GROUP BY pais ORDER BY pais;"
```

---

## Variables de entorno (.env)

```ini
# PostgreSQL
PG_HOST=localhost
PG_PORT=5432
PG_DB=sinia_uy
PG_USER=sinia_etl_user
PG_PASSWORD=sinia_etl_2026

# MongoDB
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=sinia_uy

# NASA FIRMS (obligatorio)
FIRMS_MAP_KEY=tu_clave_nasa_earthdata

# NASA AppEEARS (para MODIS — opcional)
APPEEARS_USER=tu_usuario_earthdata
APPEEARS_PASSWORD=tu_password_earthdata
```

---

*Documentación actualizada: 2026-03-22 | UTEC ITR Norte — Quinto Semestre — Rafael Quintanilla Fontané*
