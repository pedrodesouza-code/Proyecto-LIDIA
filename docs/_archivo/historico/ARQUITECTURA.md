# ARQUITECTURA DEL PROYECTO — SINIA-SA
**UTEC · Ingeniería de Datos e IA · 2026 · Rafael Quintanilla Fontané**

---

## Visión general

SINIA-SA es un sistema de monitoreo de incendios forestales para Sudamérica.
Su arquitectura es un **pipeline ETL con almacenamiento dual** que combina una base
de datos relacional (PostgreSQL) con una documental (MongoDB), expuesto a través
de un dashboard analítico (Streamlit).

```
┌──────────────────────────────────────────────────────────────┐
│                      FUENTES DE DATOS                        │
│                                                              │
│   NASA FIRMS    Open-Meteo    CAMS    CHIRPS    MODIS       │
│   (satélite)   (meteorología) (aire) (lluvia) (vegetación) │
└─────────────────────────┬────────────────────────────────────┘
                          │  APIs REST (HTTP/JSON/CSV)
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                    ETL PIPELINE (Python)                     │
│                                                              │
│   ┌──────────┐    ┌────────────┐    ┌──────────────────┐   │
│   │ EXTRACT  │ →  │ TRANSFORM  │ →  │      LOAD        │   │
│   │          │    │            │    │                  │   │
│   │ APIs →   │    │ Limpieza   │    │ PostgreSQL       │   │
│   │ CSV raw  │    │ Normaliz.  │    │ MongoDB          │   │
│   │ data/raw │    │ Índice     │    │ data/processed/  │   │
│   │          │    │ riesgo     │    │ (Parquet)        │   │
│   └──────────┘    └────────────┘    └──────────────────┘   │
│                                                              │
│   APScheduler — actualización automática con CDC watermark  │
└──────────────────┬───────────────────────┬──────────────────┘
                   │                       │
                   ▼                       ▼
    ┌──────────────────────┐   ┌──────────────────────────┐
    │    PostgreSQL 16     │   │       MongoDB 6.0         │
    │    Data Warehouse    │   │    Base operacional       │
    │                      │   │                          │
    │  8 tablas            │   │  3 colecciones           │
    │  8 vistas SQL        │   │  focos_snapshots         │
    │  índices analíticos  │   │  alertas                 │
    │  roles y permisos    │   │  ejecuciones_etl         │
    └──────────┬───────────┘   └────────────┬─────────────┘
               └─────────────────┬──────────┘
                                 │  Fallback a Parquet si BD no disponible
                                 ▼
                  ┌──────────────────────────────┐
                  │      Dashboard Streamlit      │
                  │      8 secciones              │
                  │      http://localhost:8502    │
                  └──────────────────────────────┘
```

---

## Capa 1 — Extracción

Cada fuente tiene su propio módulo extractor en `etl/extract/`. Cada extractor:
- Llama a la API correspondiente
- Guarda el resultado como CSV en `data/raw/<fuente>/`
- Maneja errores, reintentos y rate limiting

| Módulo | Fuente | Frecuencia |
|---|---|---|
| `extract_firms.py` | NASA FIRMS — focos NRT | Cada 3h (scheduler) |
| `extract_meteo.py` | Open-Meteo — histórico | Una vez (carga histórica) |
| `extract_forecast.py` | Open-Meteo — pronóstico | Cada 1h (scheduler) |
| `extract_cams.py` | CAMS — calidad del aire | Cada 1h (scheduler) |
| `extract_chirps.py` | CHIRPS — precipitación | Cada 30 días (scheduler) |
| `extract_modis.py` | MODIS — cobertura vegetal | Una vez (carga histórica) |

---

## Capa 2 — Transformación

Los módulos en `etl/transform/` procesan los CSVs crudos y generan Parquet limpios en `data/processed/`.

| Módulo | Qué hace |
|---|---|
| `transform_firms.py` | Filtra focos dentro del bbox SA, asigna país, normaliza columnas |
| `transform_meteo.py` | Normaliza tipos, **calcula el Índice de Riesgo de Incendio** |
| `transform_cams.py` | Agrega horario → diario, normaliza columnas |

### Índice de Riesgo de Incendio

Calculado en `transform_meteo.py`. Fórmula basada en el Canadian Forest Fire Weather Index (FWI):

```
Índice = Temperatura × 0.25 + Humedad × 0.30 + Viento × 0.20 + Sequía × 0.25
```

Cada variable se normaliza al rango [0, 1] antes de aplicar los pesos:

| Variable | Umbral 0 (sin riesgo) | Umbral 1 (máximo riesgo) | Peso |
|---|---|---|---|
| Temperatura máxima | 15°C | 45°C | 25% |
| Humedad mínima (invertida) | 80% | 10% | 30% |
| Viento máximo | 0 km/h | 80 km/h | 20% |
| ET0 evapotranspiración | 0 mm/día | 8 mm/día | 25% |

| Rango del índice | Nivel de riesgo |
|---|---|
| 0,00 – 0,25 | Bajo |
| 0,25 – 0,50 | Moderado |
| 0,50 – 0,75 | Alto |
| 0,75 – 1,00 | Muy Alto |

**Validación empírica:** días de riesgo MUY ALTO tienen 2,6× más focos satelitales que días MODERADO.

---

## Capa 3 — Carga (almacenamiento dual)

### PostgreSQL 16 — Data Warehouse

**Puerto:** 5432 | **Base:** `sinia_uy` | **Usuario ETL:** `sinia_etl_user`

**¿Por qué PostgreSQL?**
- Los datos de focos, meteorología y calidad del aire tienen **esquema estable y fijo**.
- Requieren **JOINs frecuentes** entre tablas (focos + puntos + meteo).
- Las **vistas materializadas** permiten precalcular resultados pesados.
- Soporte nativo para índices analíticos (BTREE, BRIN para rangos de fechas).

#### Tablas

| Tabla | Descripción | Registros |
|---|---|---|
| `focos_calor` | Focos FIRMS por foco individual | 19.510.222 |
| `meteo_diario` | Meteorología diaria + índice de riesgo calculado | 46.243 |
| `calidad_aire_diario` | PM10, PM2.5, AQI diario por punto | 45.931 |
| `precipitacion_mensual` | Precipitación CHIRPS mensual | 1.404 |
| `cobertura_vegetal` | Tipo de suelo MODIS anual | 126 |
| `puntos_monitoreo` | 23 puntos (18 SA + 5 Uruguay legacy) | 23 |
| `paises_referencia` | 7 países con metadatos | 7 |
| `etl_ejecuciones` | Audit trail del pipeline | variable |

#### Vistas SQL (8 total)

| Vista | Descripción |
|---|---|
| `v_riesgo_actual` | Último registro de riesgo por punto |
| `v_riesgo_historico` | Histórico con clasificación de nivel |
| `v_focos_resumen_diario` | Resumen diario de focos por zona |
| `v_alertas_calidad_aire` | Días sobre límite OMS |
| `v_dias_criticos` | Días con nivel ALTO o MUY ALTO |
| `v_forecast_riesgo` | Pronóstico 7 días |
| `v_riesgo_por_pais` | Comparativo mensual de riesgo por país |
| `v_focos_por_pais_mes` | Focos mensuales por país (materializada — 6.270ms → 0,4ms) |

#### Mecanismo de carga idempotente

```sql
INSERT INTO focos_calor (...) VALUES (...)
ON CONFLICT (latitud, longitud, fecha_adq, hora_adq, satelite) DO NOTHING;
```

Ejecutar el ETL dos veces produce el mismo resultado. Sin duplicados.

#### Batch inserts

Los inserts masivos se hacen en lotes de 50.000 filas usando `execute_values` de psycopg2.
Esto evita el crash "server closed the connection unexpectedly" con transacciones de millones de filas.

---

### MongoDB 6.0 — Base Operacional

**Puerto:** 27017 | **Base:** `sinia_uy` | **Sin autenticación en desarrollo**

**¿Por qué MongoDB?**
- Los **snapshots diarios** tienen tamaño variable: un día hay 0 focos, otro hay 40. El modelo de documento maneja esto sin alterar el esquema.
- Las **alertas** tienen estructura semi-estructurada con campos opcionales por tipo.
- Los **logs ETL** tienen estructura diferente por ejecución.
- Una sola consulta devuelve todos los focos de un día sin JOINs.

#### Colecciones

| Colección | Descripción | Documentos |
|---|---|---|
| `focos_snapshots` | Resumen diario del estado del sistema + top 500 focos | 2.521 |
| `alertas` | Eventos de riesgo generados automáticamente | variable |
| `ejecuciones_etl` | Trazabilidad del pipeline (audit trail) | variable |

#### Estructura de un documento focos_snapshots

```json
{
  "fecha": "2024-09-11",
  "total_focos": 71058,
  "frp_max": 590.9,
  "focos_alta_confianza": 4832,
  "nivel_riesgo_dominante": "muy_alto",
  "top_focos": [
    {"lat": -15.2, "lon": -56.4, "frp": 590.9, "pais": "BRA"},
    ...
  ],
  "resumen_por_pais": {
    "BRA": 42130, "BOL": 18450, "PRY": 6201, ...
  }
}
```

---

## Zona de staging — Parquet

Entre la Transformación y la Carga, los datos procesados se guardan en `data/processed/` como archivos Parquet.

**¿Por qué Parquet y no CSV directo a la BD?**
1. **Desacoplamiento:** si la base de datos no está disponible, el dashboard puede leer Parquet directamente (fallback implementado en `dashboard/db.py`).
2. **Reproducibilidad:** si hay un error en la carga, se puede re-cargar desde Parquet sin volver a llamar a las APIs (que tienen rate limiting).
3. **Eficiencia:** Parquet es 5–10× más compacto que CSV y 10–50× más rápido para leer columnas específicas.

---

## Automatización — APScheduler

`etl/scheduler.py` orquesta la actualización automática del sistema.

| Job | Frecuencia | Qué hace |
|---|---|---|
| FIRMS NRT | Cada 3 horas | Descarga focos nuevos desde el último watermark |
| Meteorología + pronóstico | Cada 1 hora | Actualiza forecast 7 días |
| Calidad del aire CAMS | Cada 1 hora | Descarga datos de las últimas horas |
| CHIRPS precipitación | Cada 30 días | Descarga precipitación del mes anterior |

### CDC — Change Data Capture

El scheduler implementa un **watermark basado en MAX(fecha)**:

```python
def _get_watermark(tabla):
    # Lee la última fecha cargada en PostgreSQL
    return pg.query(f"SELECT MAX(fecha) FROM {tabla}")

# Solo descarga desde esa fecha hacia adelante
fecha_inicio = _get_watermark("focos_calor")
extract_firms(desde=fecha_inicio)
```

Resultado: re-lanzar el scheduler no reprocesa el histórico completo.

---

## Dashboard Streamlit

**Archivo:** `dashboard/app.py` | **Puerto:** 8502

La capa de datos (`dashboard/db.py`) intenta primero conectarse a PostgreSQL y cae en Parquet si no está disponible.

### Secciones del dashboard

| Sección | Contenido |
|---|---|
| Resumen General | KPIs: focos totales, FRP máximo, países, días de riesgo alto |
| Focos de Calor | Evolución diaria 2018–2024, distribución por confianza, histograma FRP |
| Índice de Riesgo | Gráfico histórico por punto, gráfico radar de componentes, forecast |
| Calidad del Aire | PM10/PM2.5 diario, comparación con límite OMS, días sobre el límite |
| Análisis de Riesgo | Correlación focos–riesgo, ranking de zonas, días críticos, anomalías |
| Comparativo por País | Tabla y gráfico de los 6 países SA |
| Tiempo Real | Datos FIRMS de las últimas 24 horas, NRT |
| Fuentes y Datos Crudos | Muestra de CSVs crudos de cada fuente, columnas explicadas |

---

## Estructura de carpetas del proyecto

```
SONIA-UY/
├── config/
│   ├── .env                    Variables de entorno (NO commitear)
│   └── settings.py             Configuración central (puntos, bbox, pesos riesgo)
├── etl/
│   ├── extract/                Extractores por fuente (6 módulos)
│   ├── transform/              Transformadores por fuente (3 módulos)
│   ├── load/
│   │   ├── load_postgres.py    Carga idempotente a PostgreSQL
│   │   └── load_mongo.py       Carga a MongoDB
│   ├── utils/
│   │   └── logger.py           Logger estructurado JSON
│   ├── carga_historica.py      Carga histórica 2018–2023 por año
│   ├── sincronizar_mongo_historico.py
│   └── scheduler.py            Scheduler APScheduler con CDC
├── sql/
│   ├── ddl/                    Scripts de creación (roles, schema, índices, vistas)
│   ├── dml/                    Datos semilla (puntos de monitoreo)
│   └── queries/                10 consultas analíticas documentadas
├── nosql/
│   ├── schemas/                JSON Schema de colecciones MongoDB
│   ├── queries/                Consultas MongoDB representativas
│   └── init/                   Script de inicialización
├── dashboard/
│   ├── app.py                  Dashboard Streamlit (8 secciones)
│   └── db.py                   Capa de acceso a datos (PG + Parquet fallback)
├── analytics/
│   └── riesgo_analytics.py     Análisis avanzado (correlación, anomalías Isolation Forest)
├── tests/
│   └── test_calidad_datos.py   Tests: completitud, unicidad, consistencia, idempotencia
├── backups/
│   ├── backup.sh               Script de backup (PG + MongoDB + config)
│   └── restore.sh              Script de restauración
├── docs/                       Documentación del proyecto
├── data/
│   ├── raw/                    Datos crudos por fuente (CSV)
│   └── processed/              Datos transformados (Parquet)
├── logs/                       Logs estructurados JSON
└── requirements.txt            Dependencias Python
```

---

## Stack tecnológico

| Componente | Tecnología | Versión | Rol |
|---|---|---|---|
| Lenguaje | Python | 3.13 | Todo el pipeline |
| Base relacional | PostgreSQL | 16 | Data Warehouse |
| Base documental | MongoDB | 6.0 | Base operacional |
| Transformación | pandas | 3.x | ETL Transform |
| Conector PG | psycopg2 | 2.x | Load PostgreSQL |
| Conector Mongo | pymongo | 4.x | Load MongoDB |
| Scheduler | APScheduler | 3.x | Automatización |
| Dashboard | Streamlit | 1.x | Visualización |
| Gráficos | Plotly | 5.x | Charts interactivos |
| Formato staging | Apache Parquet | — | Zona intermedia |
| Contenedores | Docker Compose | — | Despliegue (preparado, no activo en dev) |

---

## Decisiones de diseño justificadas

| Decisión | Justificación |
|---|---|
| PostgreSQL para datos analíticos | SQL estándar, vistas materializadas, índices funcionales, soporte OLAP liviano |
| MongoDB para snapshots | Documentos de tamaño variable, arrays embebidos, sin JOINs para consultas operativas |
| Parquet como staging | Desacopla APIs de la BD, permite reprocesar sin re-llamar APIs con rate limiting |
| Batch de 50K filas | Evita crash de PG al insertar 2,4M+ filas en una sola transacción |
| Vista materializada focos_por_pais_mes | Reduce tiempo de consulta de 6.270ms a 0,4ms |
| Watermark CDC | Re-lanzar el scheduler no reprocesa el histórico completo |
| UTC como timezone | Neutro para 6 países con distintos husos horarios |
| Reordenamiento _BBOX_PAISES | PRY/BOL/PER primero, BRA último — evita absorción por bbox grande |
| ON CONFLICT DO NOTHING | Garantiza idempotencia del pipeline en todas las tablas |

---

## Conexiones de base de datos

| Sistema | Host | Puerto | Usuario | Base |
|---|---|---|---|---|
| PostgreSQL | localhost | 5432 | postgres / sinia_etl_user | sinia_uy |
| MongoDB | localhost | 27017 | sin auth (dev) | sinia_uy |

---

*UTEC ITR Norte · Quinto Semestre 2026 · Rafael Quintanilla Fontané*
