# FUENTES DE DATOS Y DATOS DEL PROYECTO — SINIA-SA
**UTEC · Ingeniería de Datos e IA · 2026 · Rafael Quintanilla Fontané**

---

## Resumen de fuentes

| # | Fuente | Qué provee | Costo | Clave requerida |
|---|---|---|---|---|
| 1 | NASA FIRMS VIIRS | Focos de calor satelitales | Gratis | Sí (NASA Earthdata) |
| 2 | Open-Meteo Archive | Meteorología histórica diaria | Gratis | No |
| 3 | Open-Meteo Forecast | Pronóstico meteorológico 7 días | Gratis | No |
| 4 | CAMS vía Open-Meteo | Calidad del aire horaria | Gratis | No |
| 5 | CHIRPS / ClimateSERV | Precipitación mensual satelital | Gratis | No |
| 6 | NASA MODIS AppEEARS | Cobertura vegetal anual | Gratis | Sí (NASA Earthdata) |

**Costo total de datos: $0**

---

## 1. NASA FIRMS — Focos de Calor Satelitales

**Proveedor:** NASA / LANCE FIRMS (Land, Atmosphere Near real-time Capability for EOS)
**Satélite:** VIIRS Suomi NPP — resolución ~375m
**Módulo ETL:** `etl/extract/extract_firms.py`

| Atributo | Valor |
|---|---|
| Tipo de acceso | API REST — requiere clave gratuita en NASA Earthdata |
| Granularidad | Por foco individual detectado |
| Latencia NRT | ~3 horas desde el paso del satélite |
| Cobertura temporal | 2018–2024 en este proyecto |
| Cobertura geográfica | Bounding box SA: lat [-56, +13] · lon [-82, -34] |
| Archivos descargados | 9 CSV |
| Filas totales | 20.068.119 |
| Carpeta | `data/raw/firms/` |

### Columnas del dato crudo

| Columna | Tipo | Descripción |
|---|---|---|
| `latitude` | float | Latitud del foco (grados decimales) |
| `longitude` | float | Longitud del foco (grados decimales) |
| `bright_ti4` | float | Temperatura de brillo banda I4 en Kelvin — detecta calor |
| `bright_ti5` | float | Temperatura de brillo banda I5 en Kelvin — referencia |
| `scan` | float | Tamaño del pixel en dirección de escaneo (km) |
| `track` | float | Tamaño del pixel en dirección de avance (km) |
| `acq_date` | date | Fecha de adquisición (YYYY-MM-DD) |
| `acq_time` | int | Hora UTC de adquisición (HHMM) |
| `satellite` | str | Satélite (N = Suomi NPP) |
| `instrument` | str | Instrumento sensor (VIIRS) |
| `confidence` | str | Nivel de confianza: n (nominal), h (high), l (low) |
| `version` | str | Versión del algoritmo de detección |
| `frp` | float | **Fire Radiative Power — potencia del fuego en Megawatts** |
| `daynight` | str | D = diurno, N = nocturno |
| `type` | int | 0 = vegetación, 1 = volcán, 2 = offshore, 3 = otro |

### Datos reales del proyecto

| Métrica | Valor |
|---|---|
| Total focos 2018–2024 | **19.510.222** |
| Peor año | **2024 — 3.831.103 focos** |
| Peor día histórico | **11/09/2024 — 71.058 focos** |
| FRP máximo registrado | **2.089 MW (Bolivia, Chiquitanía)** |
| País con más focos | Brasil 55,1% |
| Focos diurnos | ~64% |

### Distribución por país (2018–2024)

| País | Focos | % | FRP máximo (MW) |
|---|---|---|---|
| Brasil | 9.254.368 | 55,1% | 1.663 |
| Bolivia | 3.544.906 | 21,1% | 2.089 |
| Paraguay | 1.748.037 | 10,4% | 1.525 |
| Argentina | 1.037.688 | 6,2% | 1.286 |
| Perú | 824.603 | 4,9% | 947 |
| Chile | 326.012 | 1,9% | 1.380 |
| Uruguay | 46.243 | 0,3% | 579 |

---

## 2. Open-Meteo Archive — Meteorología Histórica Diaria

**Proveedor:** Open-Meteo (modelo ERA5-Land / ECMWF reanalysis)
**Módulo ETL:** `etl/extract/extract_meteo.py`

| Atributo | Valor |
|---|---|
| Tipo de acceso | API REST completamente gratuita, sin clave |
| Granularidad | Diaria por punto geográfico |
| Cobertura temporal | Desde 1940 hasta ayer |
| Puntos monitoreados | 18 ciudades SA + Rivera (Uruguay) = 19 puntos |
| Archivos descargados | 268 CSV (ciudad × año) |
| Filas totales | ~96.000 |
| Carpeta | `data/raw/meteo/` |

### Columnas del dato crudo

| Columna | Tipo | Descripción |
|---|---|---|
| `fecha` | date | Fecha del registro (YYYY-MM-DD) |
| `temperature_2m_max` | float | Temperatura máxima diaria a 2m (°C) |
| `temperature_2m_min` | float | Temperatura mínima diaria a 2m (°C) |
| `relative_humidity_2m_max` | float | Humedad relativa máxima (%) |
| `relative_humidity_2m_min` | float | **Humedad relativa mínima (%) — menor = mayor riesgo** |
| `wind_speed_10m_max` | float | Velocidad máxima del viento a 10m (km/h) |
| `wind_direction_10m_dominant` | float | Dirección dominante del viento (grados) |
| `precipitation_sum` | float | Precipitación acumulada diaria (mm) |
| `et0_fao_evapotranspiration` | float | **ET0 FAO (mm/día) — indicador de sequía acumulada** |
| `punto` | str | Nombre de la ciudad/punto de monitoreo |
| `latitud` | float | Latitud del punto |
| `longitud` | float | Longitud del punto |

### Muestra de datos (Rivera, enero 2024)

```
fecha       temp_max  temp_min  hum_min  hum_max  viento  precip  et0
2024-01-01  26.2      15.6      51       88       11.9    0.0     4.87
2024-01-02  26.8      17.5      66       96       17.3    1.7     4.85
2024-01-03  29.1      18.2      48       85       21.5    0.0     5.43
```

### Datos en PostgreSQL

| Métrica | Valor |
|---|---|
| Registros totales | 46.243 |
| Período | 2018–2026 |
| Puntos | 18 SA + Rivera |

---

## 3. Open-Meteo Forecast — Pronóstico Meteorológico

**Módulo ETL:** `etl/extract/extract_forecast.py`

| Atributo | Valor |
|---|---|
| Acceso | API REST gratuita, sin clave |
| Granularidad | Diaria — pronóstico 7 días hacia adelante |
| Actualización | Cada 1 hora (scheduler) |
| Archivos | Múltiples CSV en `data/raw/meteo/` (prefijo `forecast_`) |

Mismas columnas que el histórico. Se usa para calcular el Índice de Riesgo de los próximos 7 días.

---

## 4. CAMS vía Open-Meteo — Calidad del Aire

**Proveedor:** Copernicus Atmosphere Monitoring Service (CAMS) — Unión Europea
**Módulo ETL:** `etl/extract/extract_cams.py`

| Atributo | Valor |
|---|---|
| Tipo de acceso | Proxy gratuito vía Open-Meteo Air Quality API, sin clave |
| Granularidad | Horaria → diaria (promedio en ETL) |
| Cobertura temporal | 2018–2026 |
| Puntos monitoreados | 18 ciudades SA + Rivera |
| Archivos descargados | 192 CSV |
| Filas totales | ~1.400.000 (horario) |
| Carpeta | `data/raw/cams/` |

### Columnas del dato crudo

| Columna | Tipo | Descripción |
|---|---|---|
| `fecha_hora` | datetime | Fecha y hora UTC (ISO 8601) |
| `pm10` | float | **Partículas ≤10 µm en µg/m³ — límite OMS: 45** |
| `pm2_5` | float | **Partículas finas ≤2.5 µm en µg/m³ — límite OMS: 15** |
| `aerosol_optical_depth` | float | Profundidad óptica de aerosoles (adimensional) |
| `dust` | float | Concentración de polvo en suspensión (µg/m³) |
| `european_aqi` | float | Índice europeo calidad del aire (0–100, mayor = peor) |
| `european_aqi_pm10` | float | Sub-índice AQI para PM10 |
| `european_aqi_pm2_5` | float | Sub-índice AQI para PM2.5 |
| `punto` | str | Ciudad/punto de monitoreo |
| `latitud` | float | Latitud del punto |
| `longitud` | float | Longitud del punto |
| `fuente` | str | Identificador: CAMS_via_OpenMeteo |

### Datos reales del proyecto

| Ciudad | País | Días sobre OMS (PM10>45) | PM10 máximo |
|---|---|---|---|
| Santiago | Chile | **400 días** | 337,1 µg/m³ |
| Trinidad | Bolivia | 124 días | **853,1 µg/m³** (19× OMS) |
| Santa Cruz | Bolivia | 71 días | 489,9 µg/m³ |
| Manaus | Brasil | 66 días | 236,6 µg/m³ |
| Cuiabá | Brasil | 44 días | 201,2 µg/m³ |

### Datos en PostgreSQL

| Métrica | Valor |
|---|---|
| Registros totales (diario agregado) | 45.931 |
| Período | 2018–2026 |

---

## 5. CHIRPS — Precipitación Mensual Satelital

**Proveedor:** Climate Hazards Group InfraRed Precipitation with Stations (UCSB / NASA SERVIR)
**Módulo ETL:** `etl/extract/extract_chirps.py`

| Atributo | Valor |
|---|---|
| Tipo de acceso | API ClimateSERV gratuita, sin clave |
| Granularidad | Mensual por punto geográfico |
| Cobertura temporal | 1981–presente (proyecto usa 2018–2024) |
| Puntos monitoreados | 18 ciudades SA |
| Archivos descargados | 126 CSV (ciudad × año) |
| Carpeta | `data/raw/chirps/` |

### Columnas del dato crudo

| Columna | Descripción |
|---|---|
| `punto` | Ciudad/punto de monitoreo |
| `pais` | Código de país (BRA, BOL, PRY, ARG, CHL, PER) |
| `fecha` | Primer día del mes (YYYY-MM-01) |
| `precipitacion_mm` | Precipitación acumulada mensual en mm |
| `fuente` | CHIRPS_ClimateSERV |

### Uso en el proyecto

Se calcula la **anomalía de precipitación** respecto al promedio histórico de cada punto/mes para clasificar períodos de sequía: extrema (<-50% normal), severa (-30 a -50%), moderada (-15 a -30%), normal, húmedo (>+20%).

**Hallazgo clave:** Meses de sequía extrema tienen 1,2× más focos que meses normales. Septiembre 2020 fue el mes más catastrófico: 10 puntos en sequía severa/extrema → 790.753 focos.

### Datos en PostgreSQL

| Métrica | Valor |
|---|---|
| Registros totales | 1.404 |
| Período | 2018–2024 |

---

## 6. NASA MODIS AppEEARS — Cobertura Vegetal

**Proveedor:** NASA MODIS Terra+Aqua / AppEEARS
**Módulo ETL:** `etl/extract/extract_modis.py`

| Atributo | Valor |
|---|---|
| Producto | MCD12Q1 v6.1 — Land Cover Type (clasificación IGBP) |
| Tipo de acceso | API gratuita — requiere cuenta NASA Earthdata |
| Granularidad | Anual · resolución 500m |
| Cobertura temporal | 2018–2024 (un valor por año por punto) |
| Puntos monitoreados | 18 ciudades SA |
| Archivos descargados | 1 CSV consolidado |
| Filas | 126 (18 puntos × 7 años) |
| Carpeta | `data/raw/modis/` |

### Columnas del dato crudo

| Columna | Descripción |
|---|---|
| `Category` | Código de país |
| `ID` | Nombre del punto |
| `Latitude` / `Longitude` | Coordenadas |
| `Date` | Año del registro |
| `MCD12Q1_061_LC_Type1` | **Tipo de cobertura IGBP (número de clase)** |
| `MCD12Q1_061_QC_Name` | Descripción de la calidad del dato |

### Tipos de cobertura IGBP (LC_Type1)

| Código | Tipo | Relevancia para incendios |
|---|---|---|
| 1 | Bosque perenne de agujas | Alta combustibilidad |
| 2 | Bosque perenne de hojas anchas | Alta |
| 8 | Sabana arbolada | Muy alta |
| 9 | Sabana | Muy alta |
| 10 | Pastizal | Alta |
| 12 | Tierras de cultivo | Media |
| 13 | Urbano | Baja |

### Datos en PostgreSQL

| Métrica | Valor |
|---|---|
| Registros totales | 126 |
| Período | 2018–2024 (anual) |

---

## Volumen total de datos crudos

| Fuente | Archivos CSV | Filas totales |
|---|---|---|
| NASA FIRMS | 9 | 20.068.119 |
| Open-Meteo Meteo | 268 | ~96.000 |
| CAMS Calidad del Aire | 192 | ~1.400.000 |
| CHIRPS Precipitación | 126 | ~1.500 |
| MODIS Cobertura Vegetal | 1 | 126 |
| **TOTAL** | **596 archivos** | **~21.566.000 registros** |

---

## Dónde están los archivos

**Datos crudos (tal como llegan de las APIs):**
```
data/raw/
├── firms/     → 9 CSV · focos de calor
├── meteo/     → 268 CSV · meteorología + pronóstico
├── cams/      → 192 CSV · calidad del aire horaria
├── chirps/    → 126 CSV · precipitación mensual
└── modis/     → 1 CSV · cobertura vegetal
```

**Datos procesados (limpios, normalizados, en Parquet):**
```
data/processed/
├── firms_procesado.parquet
├── meteo_procesado_*.parquet
├── cams_procesado_*.parquet
├── cams_nrt_procesado.parquet
├── chirps_sa.parquet
├── forecast_riesgo.parquet
└── modis_lc.parquet
```

**Datos finales (en PostgreSQL y MongoDB):**
- PostgreSQL → base `sinia_uy` · 8 tablas · 8 vistas SQL
- MongoDB → base `sinia_uy` · 3 colecciones

---

*UTEC ITR Norte · Quinto Semestre 2026 · Rafael Quintanilla Fontané*
