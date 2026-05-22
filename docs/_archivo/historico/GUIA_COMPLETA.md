# GUÍA COMPLETA — SINIA-SA
## Manual de Presentación + EC1 Primera Entrega Continua

**Estudiante:** Rafael Quintanilla Fontané
**Institución:** UTEC — Universidad Tecnológica del Uruguay
**Carrera:** Licenciatura en Ingeniería de Datos e Inteligencia Artificial
**Docente:** Pablo Cuña
**Fecha:** Marzo 2026

---

# PARTE 1 — MANUAL DE PRESENTACIÓN AL PROFESOR

---

## Resumen del proyecto

**SINIA-SA** integra 5 fuentes de datos públicas y gratuitas en un pipeline ETL
automatizado, almacena los datos en PostgreSQL y MongoDB, y los visualiza en un
dashboard Streamlit con 8 páginas.

| Dato | Valor |
|---|---|
| Focos de calor totales | 19.510.222 (2018–2024) |
| Países cubiertos | Brasil, Bolivia, Paraguay, Argentina, Chile, Perú + Uruguay |
| Puntos de monitoreo | 23 (18 SA + 5 Uruguay legacy) |
| Fuentes integradas | 5 — FIRMS, Open-Meteo, CAMS, CHIRPS, MODIS |
| Costo de datos | $0 — todas las APIs son gratuitas |
| Base de datos relacional | PostgreSQL 16 — 8 tablas, 8 vistas SQL |
| Base de datos documental | MongoDB 6.0 — 3 colecciones, 2.521 documentos |
| Período histórico | 2018–2024 |
| Dashboard | http://localhost:8502 |

---

## Cómo abrir Git Bash

**Opción 1:** Tecla Windows → escribí `git bash` → Enter

**Opción 2:** Abrí el Explorador de archivos → navegá a la carpeta SONIA-UY → clic derecho → *"Open Git Bash here"*

---

## Paso 1 — Ir a la carpeta del proyecto

```bash
cd "/c/Users/rqf18/OneDrive/Documentos/api/Custom Office Templates/EjercicioSQL/Escritorio/PROYECTO INGIENERIA DE DATOS/SONIA-UY"
```

---

## Paso 2 — Iniciar PostgreSQL

```bash
"/c/Program Files/PostgreSQL/16/bin/pg_ctl" start -D "/c/Program Files/PostgreSQL/16/data" -l "/c/Program Files/PostgreSQL/16/data/log/pg_start.log"
```

Verificar:
```bash
"/c/Program Files/PostgreSQL/16/bin/pg_isready"
```
Debe decir: `localhost:5432 - accepting connections`

---

## Paso 3 — Iniciar MongoDB

Abrí una segunda pestaña de Git Bash:

```bash
"/c/Program Files/MongoDB/Server/6.0/bin/mongod.exe" --dbpath "C:/Users/rqf18/mongodb_data" --logpath "C:/Users/rqf18/mongodb_logs/mongod.log" --port 27017 --bind_ip 127.0.0.1 --logappend &
```

---

## Paso 4 — Levantar el dashboard

Tercera pestaña de Git Bash:

```bash
cd "/c/Users/rqf18/OneDrive/Documentos/api/Custom Office Templates/EjercicioSQL/Escritorio/PROYECTO INGIENERIA DE DATOS/SONIA-UY"
python -m streamlit run dashboard/app.py --server.port 8502
```

Abrí el navegador en: **http://localhost:8502**

---

## Paso 5 — Secuencia para mostrarle al profesor

### A) "Fuentes y Datos Crudos" (empezar acá)
Menú lateral → seleccioná **"Fuentes y Datos Crudos"**

Muestra las 5 fuentes con columnas explicadas y filas reales del CSV tal como llegaron de la API.

> *"Estos son los datos crudos antes de cualquier transformación. Vienen directamente de las APIs."*

### B) "Resumen General"
KPIs: focos totales, países, días de riesgo, FRP máximo.

> *"Este panel integra las 5 fuentes. Sin el ETL no se podría ver esto junto."*

### C) "Focos de Calor"
Evolución diaria 2018–2024, distribución por confianza, histograma FRP.

> *"2024 fue el peor año histórico con 3,8 millones de focos."*

### D) "Índice de Riesgo"
Seleccioná **Rivera**. Mostrar el gráfico con bandas de color.

> *Fórmula:* `Índice = Temperatura×0,25 + Humedad×0,30 + Viento×0,20 + Sequía×0,25`

### E) "Comparativo por País"
Tabla y gráfico comparando los 6 países SA.

> *"Brasil tiene el mayor volumen. Bolivia los incendios más intensos (2.089 MW)."*

---

## Paso 6 — Ver datos en la base de datos directamente (si el profesor lo pide)

```bash
# Cuántos focos hay
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" -U postgres -d sinia_uy -c "SELECT COUNT(*) FROM focos_calor;"

# Focos por país
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" -U postgres -d sinia_uy -c "SELECT pais, COUNT(*) as focos FROM focos_calor GROUP BY pais ORDER BY focos DESC;"

# Focos por año
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" -U postgres -d sinia_uy -c "SELECT EXTRACT(YEAR FROM fecha) as anio, COUNT(*) FROM focos_calor GROUP BY anio ORDER BY anio;"

# Qué tablas hay
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" -U postgres -d sinia_uy -c "\dt"

# Qué vistas hay
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" -U postgres -d sinia_uy -c "\dv"
```

---

## Paso 7 — Ver archivos crudos en el Explorador de Windows

Pegá esto en la barra de direcciones del Explorador:

```
C:\Users\rqf18\OneDrive\Documentos\api\Custom Office Templates\EjercicioSQL\Escritorio\PROYECTO INGIENERIA DE DATOS\SONIA-UY\data\raw
```

| Carpeta | Archivos | Filas totales | Para abrir con Excel |
|---|---|---|---|
| `firms\` | 9 CSV | 20.068.119 | `firms_archive_VIIRS_SNPP_SP_2024-01-01_2024-03-31.csv` |
| `meteo\` | 268 CSV | ~96.000 | `meteo_rivera_daily_2024-01-01_2024-03-31.csv` |
| `cams\` | 192 CSV | ~1.400.000 | `cams_rivera_hourly_2024-01-01_2024-01-31.csv` |
| `chirps\` | 126 CSV | ~1.500 | cualquier `chirps_*.csv` |
| `modis\` | 1 CSV | 126 | `modis_lc_*.csv` |

---

## Paso 8 — Apagar todo al terminar

```bash
"/c/Program Files/PostgreSQL/16/bin/pg_ctl" stop -D "/c/Program Files/PostgreSQL/16/data"
```

El dashboard y MongoDB se cierran solos al cerrar las ventanas de Git Bash.

---
---

# PARTE 2 — EC1: PRIMERA ENTREGA CONTINUA

---

## 1. Introducción al Dominio

Los incendios forestales en Sudamérica constituyen una de las principales amenazas ambientales del continente. En el período 2018–2024, la región registró más de 19 millones de focos de calor detectados por satélite, con impactos directos sobre la biodiversidad, la calidad del aire, la salud pública y la economía rural de seis países: Brasil, Bolivia, Paraguay, Argentina, Chile y Perú.

Brasil concentra el 55% de los focos del continente, con el bioma del Cerrado y la Amazonia como principales zonas afectadas. Bolivia registra los incendios de mayor intensidad, con un Fire Radiative Power (FRP) máximo histórico de 2.089 MW en la región de la Chiquitanía. Paraguay, Argentina, Chile y Perú completan el panorama con patrones propios vinculados a sus biomas: Chaco, Yungas, interfaz urbano-forestal andina y selva amazónica peruana.

El año 2024 fue el peor registrado en toda la serie histórica, superando a 2020 (año del gran incendio del Pantanal). Septiembre de 2024 concentró 7 de los 10 días más críticos de la historia, con un pico de 71.058 focos el 11 de septiembre.

A pesar de la magnitud del problema, no existe en la región un sistema integrado, automatizado y de acceso público que combine en tiempo real las tres dimensiones del fenómeno: detección de focos activos, condiciones meteorológicas y calidad del aire. La información existe, pero dispersa en sistemas incompatibles de distintas agencias internacionales.

---

## 2. Definición del Problema

### Problema central

La información necesaria para monitorear incendios forestales en Sudamérica existe pero está fragmentada en fuentes heterogéneas e incompatibles:

- **NASA FIRMS** provee focos de calor satelitales pero no tiene meteorología.
- **Open-Meteo** provee datos climáticos pero no tiene focos.
- **CAMS (Copernicus)** provee calidad del aire pero no sabe si hubo incendios.

Ninguna de estas fuentes, por sí sola, responde la pregunta que importa para la gestión de emergencias: **¿En qué zonas el riesgo es alto ahora y cuál es el impacto en la salud?**

### Brecha que cubre el proyecto

SINIA-SA es un pipeline de ingeniería de datos que extrae, transforma y carga datos de cinco fuentes públicas y gratuitas en un sistema de almacenamiento dual (PostgreSQL + MongoDB), con un dashboard que responde preguntas de gestión en tiempo real y se actualiza automáticamente cada 1 a 3 horas.

---

## 3. Objetivos

### Objetivo General

Diseñar e implementar un sistema de ingeniería de datos que integre fuentes satelitales, meteorológicas y de calidad del aire para el monitoreo continuo y automatizado de incendios forestales en seis países de Sudamérica, con análisis histórico (2018–2024) y seguimiento en tiempo real.

### Objetivos Específicos

1. Integrar cinco fuentes heterogéneas (NASA FIRMS, Open-Meteo, CAMS, CHIRPS, MODIS) mediante un pipeline ETL modular, idempotente y automatizado en Python.
2. Diseñar un modelo de datos relacional en PostgreSQL con esquema normalizado y consultas analíticas eficientes.
3. Implementar un índice de riesgo de incendio basado en cuatro variables meteorológicas con fundamento en el Canadian Forest Fire Weather Index (FWI).
4. Construir una base de datos documental en MongoDB para snapshots diarios, alertas y trazabilidad del pipeline.
5. Desarrollar un dashboard analítico en Streamlit con ocho secciones de análisis.
6. Automatizar la actualización con APScheduler y CDC watermark sin duplicación de datos.
7. Validar la calidad mediante tests de completitud, unicidad, consistencia, validez e idempotencia.

---

## 4. Análisis Detallado de Fuentes

### 4.1 NASA FIRMS — Focos de Calor

| Atributo | Detalle |
|---|---|
| Proveedor | NASA / LANCE FIRMS |
| Satélite | VIIRS Suomi NPP · ~375m resolución |
| Acceso | API REST gratuita (requiere clave NASA Earthdata) |
| Granularidad | Por foco individual |
| Cobertura | 2018–2024 · bounding box SA |
| Archivos | 9 CSV · 20.068.119 filas |
| Módulo ETL | `etl/extract/extract_firms.py` |

Columnas clave: `latitude`, `longitude`, `frp` (Megawatts), `acq_date`, `acq_time`, `confidence`, `daynight`

**Justificación:** fuente de referencia mundial para focos de calor, sin alternativa comparable.

---

### 4.2 Open-Meteo — Meteorología Histórica

| Atributo | Detalle |
|---|---|
| Proveedor | Open-Meteo (ERA5-Land / ECMWF reanalysis) |
| Acceso | API REST gratuita, sin clave |
| Granularidad | Diaria por punto geográfico |
| Cobertura | Desde 1940 · 18 ciudades SA + Rivera |
| Archivos | 268 CSV |
| Módulo ETL | `etl/extract/extract_meteo.py` |

Columnas clave: `temperature_2m_max`, `relative_humidity_2m_min`, `wind_speed_10m_max`, `et0_fao_evapotranspiration`, `precipitation_sum`

**Justificación:** las estaciones meteorológicas nacionales (INUMET, SENAMHI) no tienen API pública. Open-Meteo es la mejor alternativa open-source.

---

### 4.3 CAMS — Calidad del Aire

| Atributo | Detalle |
|---|---|
| Proveedor | Copernicus CAMS — Unión Europea |
| Acceso | Proxy gratuito vía Open-Meteo Air Quality API |
| Granularidad | Horaria → diaria (agregado en ETL) |
| Archivos | 192 CSV |
| Módulo ETL | `etl/extract/extract_cams.py` |

Columnas clave: `pm10` (límite OMS: 45 µg/m³), `pm2_5` (límite OMS: 15 µg/m³), `european_aqi`, `dust`

---

### 4.4 CHIRPS — Precipitación Mensual

| Atributo | Detalle |
|---|---|
| Proveedor | Climate Hazards Group / NASA SERVIR |
| Acceso | API ClimateSERV gratuita, sin clave |
| Granularidad | Mensual por punto |
| Archivos | 126 CSV |
| Módulo ETL | `etl/extract/extract_chirps.py` |

**Uso:** cálculo de anomalías de precipitación para detectar meses de sequía.

---

### 4.5 NASA MODIS — Cobertura Vegetal

| Atributo | Detalle |
|---|---|
| Proveedor | NASA MODIS / AppEEARS |
| Producto | MCD12Q1 v6.1 — Land Cover IGBP (17 clases) |
| Acceso | API gratuita (requiere cuenta NASA Earthdata) |
| Granularidad | Anual · 500m resolución |
| Archivos | 1 CSV · 126 filas (18 puntos × 7 años) |
| Módulo ETL | `etl/extract/extract_modis.py` |

---

## 5. Exploración Preliminar Real de Datos

### Volumen de datos crudos

| Fuente | Archivos CSV | Filas totales |
|---|---|---|
| NASA FIRMS | 9 | 20.068.119 |
| Open-Meteo Meteo | 268 | ~96.000 |
| CAMS Calidad del Aire | 192 | ~1.400.000 |
| CHIRPS Precipitación | 126 | ~1.500 |
| MODIS Cobertura Vegetal | 1 | 126 |
| **TOTAL** | **596** | **~21.566.000** |

### Distribución de focos por país (2018–2024)

| País | Focos | % | FRP máximo (MW) |
|---|---|---|---|
| Brasil | 9.254.368 | 55,1% | 1.663 |
| Bolivia | 3.544.906 | 21,1% | **2.089** |
| Paraguay | 1.748.037 | 10,4% | 1.525 |
| Argentina | 1.037.688 | 6,2% | 1.286 |
| Perú | 824.603 | 4,9% | 947 |
| Chile | 326.012 | 1,9% | 1.380 |
| Uruguay | 46.243 | 0,3% | 579 |

### Evolución por año

| Año | Focos |
|---|---|
| **2024** | **3.831.103** |
| 2020 | 3.380.640 |
| 2019 | 2.742.718 |
| 2022 | 2.691.451 |
| 2023 | 2.569.979 |
| 2021 | 2.381.840 |
| 2018 | 1.912.491 |

### Calidad del aire — días sobre límite OMS

| Ciudad | País | Días sobre OMS | PM10 máximo |
|---|---|---|---|
| Santiago | Chile | 400 | 337,1 µg/m³ |
| Trinidad | Bolivia | 124 | **853,1 µg/m³** |
| Santa Cruz | Bolivia | 71 | 489,9 µg/m³ |

---

## 6. Evaluación Preliminar de Calidad

### Completitud

| Fuente | Campo | % nulos | Acción |
|---|---|---|---|
| FIRMS | `frp` | < 0,1% | Imputación con 0,0 |
| Meteo | `indice_riesgo` | 0% | Calculado en transform |
| CAMS | `pm10` | < 2% | Interpolación de valores adyacentes |
| CHIRPS | `precipitacion_mm` | < 1% | Excluidos del promedio histórico |

### Unicidad — claves naturales

| Tabla | Clave natural | Mecanismo |
|---|---|---|
| `focos_calor` | `(latitud, longitud, fecha_adq, hora_adq, satelite)` | UNIQUE + ON CONFLICT DO NOTHING |
| `meteo_diario` | `(id_punto, fecha, tipo_dato)` | UNIQUE constraint |
| `calidad_aire_diario` | `(id_punto, fecha)` | UNIQUE constraint |

El pipeline es **idempotente**: ejecutarlo dos veces produce el mismo resultado.

### Consistencia geográfica

Todos los focos tienen coordenadas dentro del bounding box SA: lat [-56, +13], lon [-82, -34].
Se detectó y corrigió un bug de absorción geográfica: el bbox de Brasil absorbía focos de Paraguay y Bolivia. Solución: países pequeños tienen prioridad de asignación.

### Validez de rangos

| Variable | Rango válido | Acción si fuera de rango |
|---|---|---|
| FRP | 0 – 10.000 MW | Se registra con flag |
| Temperatura | -20 – 55°C | Se descarta |
| Humedad | 0 – 100% | Clamp a [0, 100] |
| Índice de riesgo | 0,0 – 1,0 | Normalizado por diseño |

### CDC — Change Data Capture

El scheduler implementa un watermark basado en `MAX(fecha)` de cada tabla. Al re-lanzarse solo descarga datos nuevos desde ese punto. No reprocesa el histórico completo en cada ejecución.

---

## 7. Preguntas Analíticas

| ID | Pregunta | Qué responde |
|---|---|---|
| PA-01 | ¿Cuántos focos se detectaron por mes y cuál fue su FRP promedio? | Evolución temporal de la actividad |
| PA-02 | ¿Cuáles son los 15 días con mayor cantidad de focos? | Identificación de días críticos |
| PA-03 | ¿Cuántos días en nivel ALTO o MUY ALTO tuvo cada punto? | Priorización territorial |
| PA-04 | ¿Cómo evoluciona el índice de riesgo mensual? ¿Hay estacionalidad? | Planificación anual |
| PA-05 | ¿Correlación entre riesgo meteorológico y focos satelitales? | Validación del índice |
| PA-06 | ¿Cuántos días superó cada ciudad el límite OMS de PM10? | Impacto en salud pública |
| PA-07 | ¿Cuál es el pronóstico de riesgo para los próximos 7 días? | Decisiones operativas |
| PA-08 | ¿Cuál es el mes del año con mayor riesgo histórico acumulado? | Estacionalidad del riesgo |
| PA-09 | ¿Los focos se concentran de día o de noche? | Optimización de patrullaje |
| PA-10 | ¿Existe correlación entre meses de sequía CHIRPS y aumento de focos? | Análisis multivariado |

---

## 8. Arquitectura Preliminar Justificada

```
┌──────────────────────────────────────────────────────────┐
│                   FUENTES DE DATOS                       │
│  NASA FIRMS   Open-Meteo   CAMS   CHIRPS   MODIS        │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│                ETL PIPELINE (Python)                     │
│  EXTRACT  →  TRANSFORM  →  LOAD                         │
│  APIs REST    Limpieza       PostgreSQL                  │
│  CSV raw      Normalización  MongoDB                     │
│  data/raw/    Índice riesgo  data/processed/ (Parquet)  │
│  APScheduler — actualización automática con CDC         │
└───────────────┬──────────────────────┬───────────────────┘
                ▼                      ▼
  ┌──────────────────────┐  ┌──────────────────────────┐
  │    PostgreSQL 16     │  │       MongoDB 6.0         │
  │    Data Warehouse    │  │    Base operacional       │
  │    8 tablas          │  │    3 colecciones          │
  │    8 vistas SQL      │  │    focos_snapshots        │
  │    índices + roles   │  │    alertas + etl_logs     │
  └──────────┬───────────┘  └─────────────┬────────────┘
             └──────────────┬─────────────┘
                            ▼
              ┌──────────────────────────┐
              │   Dashboard Streamlit    │
              │   8 secciones            │
              │   localhost:8502         │
              └──────────────────────────┘
```

### Por qué PostgreSQL
- Datos con esquema fijo — ideal para modelo relacional.
- JOINs frecuentes entre focos, meteorología y puntos.
- Vistas materializadas reducen consultas de 6.270 ms a 0,4 ms.

### Por qué MongoDB
- Snapshots diarios tienen tamaño variable (0 a 40+ focos) — el modelo de documento lo maneja naturalmente.
- Alertas y logs ETL tienen estructura semi-estructurada con campos opcionales.
- No es redundancia sino complementariedad.

### Por qué Parquet
- 5–10× menos espacio que CSV.
- Desacopla la base de datos del dashboard: si PostgreSQL no está disponible, el dashboard lee Parquet.
- Permite re-procesar sin re-llamar APIs.

### Índice de Riesgo de Incendio

```
Índice = Temperatura × 0,25 + Humedad × 0,30 + Viento × 0,20 + Sequía × 0,25
```

| Variable | Umbral riesgo 0 | Umbral riesgo 1 |
|---|---|---|
| Temperatura máxima | 15°C | 45°C |
| Humedad mínima (invertida) | 80% | 10% |
| Viento máximo | 0 km/h | 80 km/h |
| ET0 evapotranspiración | 0 mm | 8 mm/día |

| Rango | Nivel |
|---|---|
| 0,00 – 0,25 | Bajo |
| 0,25 – 0,50 | Moderado |
| 0,50 – 0,75 | Alto |
| 0,75 – 1,00 | Muy Alto |

---

## 9. Riesgos y Limitaciones

### Limitaciones

| ID | Limitación |
|---|---|
| L-01 | 18 ciudades como proxies — zonas rurales intermedias no cubiertas directamente |
| L-02 | CAMS provee estimaciones satelitales, no mediciones físicas directas |
| L-03 | Índice de riesgo no calibrado con registros oficiales de incendios confirmados |
| L-04 | Docker no disponible (WSL2 deshabilitado) — infraestructura corre como procesos locales |
| L-05 | Ventanas temporales distintas por fuente segun disponibilidad real |

### Riesgos técnicos

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| NASA FIRMS cambia su API | Baja | Extractor modular — solo se modifica `extract_firms.py` |
| Open-Meteo aplica rate limiting | Media | Retries con backoff exponencial |
| Crash PG con inserts masivos | Bajo | Resuelto: batch 50K filas con `execute_values` |
| Duplicación de datos | Bajo | Resuelto: UNIQUE + ON CONFLICT DO NOTHING |
| Absorción geográfica | Bajo | Resuelto: reordenamiento de bbox por país |

### Trabajo futuro

1. CDC incremental real — solo descargar desde la última fecha cargada.
2. Integración con datos oficiales (MGAP, IBAMA, INAB) para calibrar el índice.
3. Modelo predictivo con los 7 años de histórico.
4. Expansión a más puntos intermedios entre ciudades.
5. API REST pública del sistema para consumo externo.

---

## Conclusión

SINIA-SA demuestra que con fuentes de datos públicas y gratuitas, aplicando principios
de ingeniería de datos, es posible construir un sistema de monitoreo ambiental funcional,
automatizado y con valor real para la gestión de emergencias en seis países de Sudamérica.

El hallazgo más relevante: **2024 fue el peor año de incendios en Sudamérica en los últimos
7 años**, con septiembre de 2024 como el mes más crítico de toda la serie histórica y
Trinidad (Bolivia) alcanzando PM10 de 853 µg/m³ — 19 veces el límite de la OMS.

---

*UTEC ITR Norte · Licenciatura en Ingeniería de Datos e Inteligencia Artificial · Quinto Semestre 2026 · Rafael Quintanilla Fontané*
