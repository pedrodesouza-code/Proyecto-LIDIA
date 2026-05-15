# SEDE: RIVERA

# Proyecto de Ingeniería de Datos

## LICENCIATURA EN INGENIERÍA DE DATOS E INTELIGENCIA ARTIFICIAL

---

**Nombre del trabajo:** "Análisis integrado de incendios forestales, condiciones meteorológicas, precipitación, calidad del aire y cobertura vegetal en América del Sur durante el período 2018–2025"

**Autores:** Pedro De Souza, Rafael Quintanilla, Katerin Gonzalez

---

## Índice

1. Introducción
2. Formulación del problema
   - 2.1 Contexto del problema
   - 2.2 Actores involucrados
   - 2.3 Variables clave del fenómeno
   - 2.4 Dimensión temporal
   - 2.5 Dimensión espacial
   - 2.6 Justificación de la relevancia del problema
   - 2.7 Problema
3. Objetivos
   - 3.1 Objetivo general
   - 3.2 Objetivos específicos
4. Identificación y análisis de fuentes de datos
   - 4.1 NASA FIRMS (VIIRS)
   - 4.2 Open-Meteo (ERA5-Land)
   - 4.3 Copernicus Atmosphere Monitoring Service
   - 4.4 CHIRPS
   - 4.5 MODIS (Cobertura vegetal)
   - 4.6 INUMET (fuente evaluada fuera de alcance)
5. Exploración preliminar de datos
   - 5.1 Acceso real a los datos
   - 5.2 Evidencias
   - 5.3 Observación
   - 5.4 Problemas destacados
6. Evaluación preliminar de calidad de datos
   - 6.1 Completitud
   - 6.2 Unicidad
   - 6.3 Consistencia básica
   - 6.4 Validez simple
7. Viabilidad técnica
   - 7.1 Principales riesgos
8. Preguntas iniciales
9. Arquitectura preliminar
   - 9.1 Justificación
10. Riesgos y limitaciones
    - 10.1 Riesgos
    - 10.2 Limitaciones
11. Referencias (APA)

---

## 1. Introducción

Los incendios forestales constituyen un fenómeno ambiental de alta relevancia debido a su capacidad para alterar ecosistemas, afectar los ciclos naturales del ambiente y modificar la composición atmosférica. La literatura científica señala que los incendios desempeñan un papel importante en los sistemas terrestres y atmosféricos, y que su comportamiento está estrechamente vinculado con la estructura de la vegetación, el clima y la disponibilidad de combustible.

De acuerdo con Jolly et al. (2015), la variación del peligro global de incendios se encuentra asociada a condiciones climáticas, y la duración de la temporada de incendios ha aumentado en muchas regiones del mundo. En ese marco, variables como temperatura, humedad relativa, precipitación y viento resultan claves para comprender la ocurrencia y propagación del fuego.

Estudios realizados por Reid et al. (2016) muestran que el humo de incendios forestales contiene elevadas concentraciones de material particulado fino y otros contaminantes atmosféricos, lo que genera un deterioro significativo en la calidad del aire. Por esta razón, la calidad del aire constituye una dimensión central para el análisis de estos eventos.

En paralelo, el desarrollo de sensores satelitales permitió mejorar sustancialmente el monitoreo ambiental. Según Giglio et al. (2016), los productos MODIS de incendios activos constituyen una base robusta para detectar eventos térmicos y construir análisis espaciales y temporales. A su vez, NASA FIRMS distribuye datos globales de incendios activos a partir de MODIS y VIIRS con actualización casi en tiempo real.

La disponibilidad de APIs meteorológicas, datos atmosféricos, productos de precipitación satelital y datasets globales de cobertura del suelo plantea un desafío propio de la ingeniería de datos: integrar fuentes heterogéneas, armonizar granularidades distintas y construir una capa analítica reutilizable. En este contexto, la disponibilidad de datos climáticos globales de alta resolución ha facilitado el análisis ambiental a gran escala.

---

## 2. Formulación del problema

### 2.1 Contexto del problema

En América del Sur, los incendios forestales afectan ecosistemas de gran relevancia ecológica y productiva. Su ocurrencia no depende de una única variable, sino de la interacción entre condiciones meteorológicas, disponibilidad de combustible, estacionalidad, precipitación acumulada y contexto de cobertura vegetal. La literatura científica indica que el fuego debe analizarse como parte del sistema terrestre y no como un evento aislado.

Además, los incendios producen emisiones atmosféricas que deterioran la calidad del aire a escala regional. En consecuencia, un análisis con sentido aplicado no debería limitarse a contar focos de calor, sino estudiar en qué condiciones ocurrieron, sobre qué tipo de cobertura del suelo se produjeron y qué efecto tuvieron sobre la atmósfera.

### 2.2 Actores involucrados

Los principales actores involucrados en este dominio son:

- Organismos internacionales de observación ambiental, como NASA, que generan y distribuyen datos satelitales de incendios.
- Proveedores de datos meteorológicos y atmosféricos, como Open-Meteo, que ofrecen variables climáticas y de calidad del aire mediante APIs.
- Centros de investigación climática y ambiental, que desarrollan productos como CHIRPS y datasets globales de cobertura del suelo.
- Usuarios del sistema, como investigadores, analistas de datos y organismos de monitoreo ambiental.

### 2.3 Variables clave del fenómeno

Las variables principales del proyecto son:

**Incendios**
- latitud
- longitud
- fecha
- hora
- brillo térmico / intensidad
- potencia radiativa del fuego
- confianza de detección

**Condiciones meteorológicas**
- temperatura
- humedad relativa
- velocidad del viento
- precipitación

**Calidad del aire**
- PM2.5
- PM10
- CO
- NO₂
- O₃

**Cobertura vegetal / uso del suelo**
- tipo de cobertura dominante
- clase de vegetación o uso del suelo
- distribución espacial anual de coberturas

### 2.4 Dimensión temporal

El análisis se realizará sobre el período 2018–2025. Ese rango permite estudiar patrones estacionales e interanuales y, al mismo tiempo, aprovechar fuentes con cobertura histórica suficiente. Open-Meteo documenta disponibilidad histórica amplia para variables meteorológicas; CHIRPS ofrece precipitación diaria desde 1981; y MCD12Q1 es un producto anual global de cobertura del suelo.

### 2.5 Dimensión espacial

La unidad territorial del proyecto será América del Sur. Esta delimitación amplía el volumen de datos respecto a un enfoque nacional, permite comparaciones por país o subregión y justifica de mejor manera una arquitectura de ingeniería de datos con integración multifuente y análisis agregado.

### 2.6 Justificación de la relevancia del problema

El valor del proyecto no radica sólo en detectar incendios, sino en cruzar datos con sentido para comprender cómo se comportan según el contexto climático, qué impacto tienen sobre la calidad del aire y sobre qué tipos de cobertura vegetal ocurren con mayor frecuencia. Esa integración puede transformarse en una herramienta útil para monitoreo ambiental, análisis territorial y generación de indicadores históricos reutilizables.

### 2.7 Problema

El proyecto estudiará la relación entre la ocurrencia de incendios forestales, las condiciones meteorológicas, la precipitación, la calidad del aire y la cobertura vegetal en América del Sur durante el período 2018–2025, utilizando datos abiertos y heterogéneos provenientes de sensores satelitales, APIs ambientales y datasets geoespaciales.

El problema de ingeniería de datos consiste en integrar fuentes que presentan diferencias en formato, granularidad temporal, resolución espacial y estructura conceptual, para construir una base analítica unificada que permita responder preguntas descriptivas y comparativas. Quedan fuera del alcance de esta etapa la predicción de incendios, el análisis sanitario y la evaluación económica.

---

## 3. Objetivos

### 3.1 Objetivo general

Analizar la relación entre incendios forestales, condiciones meteorológicas, la calidad del aire y la cobertura vegetal mediante la integración de múltiples fuentes de datos ambientales en América del Sur durante el período 2018–2025.

### 3.2 Objetivos específicos

1. Comparar patrones de incendios entre diferentes países de América del Sur.
2. Analizar la evolución temporal de los incendios forestales en América del Sur durante el período 2018–2025.
3. Evaluar la relación entre variables meteorológicas —temperatura, humedad, viento y precipitación— y la ocurrencia de incendios forestales.
4. Analizar cómo varían la calidad del aire y la distribución de incendios según el tipo de cobertura vegetal dominante.

---

## 4. Identificación y análisis de fuentes de datos

### 4.1 NASA FIRMS (VIIRS)

| Campo | Detalle |
|---|---|
| **Nombre y origen** | NASA FIRMS (Fire Information for Resource Management System), basado en sensores VIIRS de la NASA |
| **Enlace oficial** | https://firms.modaps.eosdis.nasa.gov/ |
| **Tipo de acceso** | API / descarga directa |
| **Formato** | JSON |
| **Volumen aproximado** | 6,900 registros (Uruguay) |
| **Frecuencia de actualización** | Casi en tiempo real (minutos/horas) |
| **Granularidad** | Alta (detección puntual por coordenadas) |
| **Variables relevantes** | Latitud / Longitud, Fecha / Hora, Brightness, Confidence |
| **Limitaciones** | Posibles falsos positivos; interferencia por nubosidad |
| **Riesgos técnicos** | Variabilidad en calidad (`confidence`); necesidad de filtrado previo |

### 4.2 Open-Meteo (ERA5-Land)

| Campo | Detalle |
|---|---|
| **Nombre y origen** | Open-Meteo (datos derivados de ERA5-Land, modelo climático europeo) |
| **Enlace oficial** | https://open-meteo.com/ |
| **Tipo de acceso** | API REST |
| **Formato** | JSON |
| **Volumen aproximado** | 1,332,888 registros |
| **Frecuencia de actualización** | Horaria |
| **Granularidad** | Media (grilla geoespacial) |
| **Variables relevantes** | Temperatura, Humedad, Velocidad del viento, Precipitación, ET0 |
| **Limitaciones** | Datos modelados (no observados) |
| **Riesgos técnicos** | Sesgo local; interpolación espacial; dependencia de API |

```python
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

url = "https://archive-api.open-meteo.com/v1/archive"
params = {
    "latitude": [-34.9011, -34.6627, -34.3375, -33.2333, -34.5389, -33.5389, -30.9053,
                 -33.2542, -34.3375, -32.3214, -34.3759, -34.4833, -32.3171, -31.3833,
                 -33.5303, -34.4333, -32.375, -30.2533, -31.7333],
    "longitude": [-56.1645, -56.2194, -56.7136, -54.3833, -56.2847, -56.8886, -55.5508,
                  -54.0964, -55.2372, -58.0756, -55.2377, -57.8333, -58.0807, -57.9667,
                  -56.8983, -57.2333, -54.1675, -57.6167, -55.9833],
    "start_date": "2018-01-01",
    "end_date": "2026-01-01",
    "hourly": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m",
               "wind_direction_10m", "rain"],
}
responses = openmeteo.weather_api(url, params=params)
all_data = []
for i, response in enumerate(responses):
    hourly = response.Hourly()
    df = pd.DataFrame({
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "temperature_2m":        hourly.Variables(0).ValuesAsNumpy(),
        "relative_humidity_2m":  hourly.Variables(1).ValuesAsNumpy(),
        "wind_speed_10m":        hourly.Variables(2).ValuesAsNumpy(),
        "wind_direction_10m":    hourly.Variables(3).ValuesAsNumpy(),
        "rain":                  hourly.Variables(4).ValuesAsNumpy(),
    })
    df["location_id"] = i
    df["latitude"]    = response.Latitude()
    df["longitude"]   = response.Longitude()
    all_data.append(df)

final_df = pd.concat(all_data, ignore_index=True)
print("Shape final:", final_df.shape)
print(final_df.head())
```

### 4.3 Copernicus Atmosphere Monitoring Service (CAMS)

| Campo | Detalle |
|---|---|
| **Nombre y origen** | Copernicus Atmosphere Monitoring Service (CAMS), Unión Europea |
| **Enlace oficial** | https://atmosphere.copernicus.eu/ |
| **Tipo de acceso** | Descarga / API |
| **Formato** | NetCDF, CSV |
| **Volumen aproximado** | 1,332,888 registros |
| **Frecuencia de actualización** | Horaria |
| **Granularidad** | Media-baja (grillas grandes) |
| **Variables relevantes** | PM2.5, PM10, AQI, Polvo |
| **Limitaciones** | Baja resolución espacial |
| **Riesgos técnicos** | Datos faltantes; necesidad de agregación |

```python
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

url = "https://air-quality-api.open-meteo.com/v1/air-quality"
params = {
    "latitude": [-34.9011, -34.6627, -34.3375, -33.2333, -34.5389, -33.5389, -30.9053,
                 -33.2542, -34.3375, -32.3214, -34.3759, -34.4833, -32.3171, -31.3833,
                 -33.5303, -34.4333, -32.375, -30.2533, -31.7333],
    "longitude": [-56.1645, -56.2194, -56.7136, -54.3833, -56.2847, -56.8886, -55.5508,
                  -54.0964, -55.2372, -58.0756, -55.2377, -57.8333, -58.0807, -57.9667,
                  -56.8983, -57.2333, -54.1675, -57.6167, -55.9833],
    "start_date": "2018-01-01",
    "end_date": "2026-01-01",
    "hourly": ["pm10", "pm2_5"],
}
responses = openmeteo.weather_api(url, params=params)
all_data = []
for i, response in enumerate(responses):
    hourly = response.Hourly()
    df = pd.DataFrame({
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "pm10":  hourly.Variables(0).ValuesAsNumpy(),
        "pm2_5": hourly.Variables(1).ValuesAsNumpy(),
    })
    df["location_id"] = i
    df["latitude"]    = response.Latitude()
    df["longitude"]   = response.Longitude()
    all_data.append(df)

final_df = pd.concat(all_data, ignore_index=True)
final_df.to_parquet("uruguay_air_quality.parquet")
```

### 4.4 CHIRPS

| Campo | Detalle |
|---|---|
| **Nombre y origen** | CHIRPS (Climate Hazards Group) |
| **Enlace oficial** | https://climateserv.servirglobal.net/ |
| **Tipo de acceso** | Descarga |
| **Formato** | GeoTIFF, CSV |
| **Volumen aproximado** | 1,400 registros |
| **Frecuencia de actualización** | Mensual |
| **Granularidad** | Media |
| **Variables relevantes** | Precipitación acumulada |
| **Limitaciones** | Baja resolución temporal |
| **Riesgos técnicos** | Agregación mensual; procesamiento de raster |

### 4.5 MODIS (Cobertura vegetal)

| Campo | Detalle |
|---|---|
| **Nombre y origen** | MODIS (NASA), producto de cobertura terrestre |
| **Enlace oficial** | https://appeears.earthdatacloud.nasa.gov/ |
| **Tipo de acceso** | Descarga |
| **Formato** | GeoTIFF, HDF |
| **Volumen aproximado** | 167 registros |
| **Frecuencia de actualización** | Anual |
| **Granularidad** | Media |
| **Variables relevantes** | Tipo de cobertura (IGBP) |
| **Limitaciones** | Baja variabilidad temporal |
| **Riesgos técnicos** | Clasificación discreta; procesamiento geoespacial |

### 4.6 INUMET (fuente evaluada fuera de alcance)

| Campo | Detalle |
|---|---|
| **Nombre y origen** | Instituto Uruguayo de Meteorología (INUMET) |
| **Enlace oficial** | https://www.inumet.gub.uy/ |
| **Tipo de acceso** | Portal institucional y servicios publicados |
| **Formato** | Web/descargas segun producto |
| **Volumen aproximado** | Variable por estacion/producto |
| **Frecuencia de actualización** | Variable |
| **Granularidad** | Alta (estaciones meteorológicas) |
| **Variables relevantes** | Temperatura, Precipitación, Humedad, Viento |
| **Limitaciones** | Se descarta para el pipeline final para mantener fuentes abiertas transnacionales y comparables en Uruguay, Brasil y Argentina |
| **Riesgos técnicos** | Datos faltantes; inconsistencias entre estaciones |

---

## 5. Exploración preliminar de datos

### 5.1 Acceso real a los datos

Se realizó una exploración preliminar de las fuentes seleccionadas mediante la descarga de muestras y consultas a las APIs correspondientes, con el objetivo de comprender su estructura y detectar posibles problemas iniciales.

### 5.2 Evidencias

**Dataset Open-Meteo ERA5-Land (`df.head()`):**

```
                      date  temperature_2m  relative_humidity_2m  \
0 2018-01-01 00:00:00+00:00       20.299999             62.685486
1 2018-01-01 01:00:00+00:00       20.200001             66.018921
2 2018-01-01 02:00:00+00:00       20.299999             67.120224
3 2018-01-01 03:00:00+00:00       20.299999             68.215935
4 2018-01-01 04:00:00+00:00       20.049999             71.783089

   wind_speed_10m  wind_direction_10m  rain  location_id   latitude  longitude
0       20.633371          132.878906   0.0            0 -34.903339 -56.192902
1       22.608458          127.234917   0.0            0 -34.903339 -56.192902
2       20.658480          112.543098   0.1            0 -34.903339 -56.192902
3       18.775301           94.398621   0.1            0 -34.903339 -56.192902
4       21.243050           89.028999   0.1            0 -34.903339 -56.192902
```

**Dataset NASA FIRMS (`df.head()`):**

| | latitude | longitude | acq_date | acq_time | satellite | confidence | type | track | frp | daynight | scan | version | bright_t31 | instrument | brightness |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | -33.5276 | -58.2158 | 2018-01-02 | 1414 | Terra | 40 | 2 | 1.1 | 7.1 | D | 1.2 | 6.03 | 305.4 | MODIS | 318.3 |
| 1 | -34.7275 | -56.2233 | 2018-01-02 | 1414 | Terra | 37 | 2 | 1.2 | 9.7 | D | 1.6 | 6.03 | 302.9 | MODIS | 315.2 |
| 2 | -34.7298 | -56.0030 | 2018-01-03 | 1735 | Aqua  | 46 | 0 | 1.0 | 7.7 | D | 1.1 | 6.03 | 309.4 | MODIS | 322.4 |
| 3 | -34.7205 | -56.0048 | 2018-01-03 | 1735 | Aqua  | 40 | 0 | 1.0 | 7.7 | D | 1.1 | 6.03 | 308.3 | MODIS | 322.8 |
| 4 | -34.7287 | -56.2201 | 2018-01-03 | 1735 | Aqua  | 54 | 0 | 1.0 | 10.5 | D | 1.1 | 6.03 | 308.2 | MODIS | 324.5 |

### 5.3 Observación

**NASA FIRMS — `df.dtypes`:**

```
latitude      float64
longitude     float64
acq_date          str
acq_time        int64
satellite         str
confidence      int64
type            int64
track         float64
frp           float64
daynight          str
scan          float64
version       float64
bright_t31    float64
instrument        str
brightness    float64
dtype: object
```

**NASA FIRMS — `df.isnull().sum()`:**

```
latitude      0
longitude     0
acq_date      0
acq_time      0
satellite     0
confidence    0
type          0
track         0
frp           0
daynight      0
scan          0
version       0
bright_t31    0
instrument    0
brightness    0
dtype: int64
```

**Open-Meteo ERA5-Land (meteorológico) — `df.isnull().sum()`:**

```
date                    0
temperature_2m          0
relative_humidity_2m    0
wind_speed_10m          0
wind_direction_10m      0
rain                    0
location_id             0
latitude                0
longitude               0
dtype: int64
```

**Open-Meteo ERA5-Land (meteorológico) — `df.info()`:**

```
<class 'pandas.DataFrame'>
RangeIndex: 1332888 entries, 0 to 1332887
Data columns (total 9 columns):
 #   Column                Non-Null Count    Dtype
---  ------                --------------    -----
 0   date                  1332888 non-null  datetime64[s, UTC]
 1   temperature_2m        1332888 non-null  float32
 2   relative_humidity_2m  1332888 non-null  float32
 3   wind_speed_10m        1332888 non-null  float32
 4   wind_direction_10m    1332888 non-null  float32
 5   rain                  1332888 non-null  float32
 6   location_id           1332888 non-null  int64
 7   latitude              1332888 non-null  float64
 8   longitude             1332888 non-null  float64
dtypes: datetime64[s, UTC](1), float32(5), float64(2), int64(1)
memory usage: 50.8 MB
```

**CAMS Calidad del Aire — `df.info()`:**

```
<class 'pandas.DataFrame'>
RangeIndex: 1332888 entries, 0 to 1332887
Data columns (total 6 columns):
 #   Column       Non-Null Count    Dtype
---  ------       --------------    -----
 0   date         1332888 non-null  datetime64[s, UTC]
 1   pm10          568632 non-null  float32
 2   pm2_5         568632 non-null  float32
 3   location_id  1332888 non-null  int64
 4   latitude     1332888 non-null  float64
 5   longitude    1332888 non-null  float64
dtypes: datetime64[s, UTC](1), float32(2), float64(2), int64(1)
memory usage: 50.8 MB
```

### 5.4 Problemas destacados

**Problema identificado: diferencias en la granularidad temporal**

Durante el análisis de las fuentes de datos se detectó una heterogeneidad significativa en la granularidad temporal. Algunas fuentes, como NASA FIRMS y Open-Meteo, trabajan con datos en tiempo casi real u horarios, mientras que otras como CHIRPS presentan información agregada a nivel mensual, y MODIS ofrece actualizaciones anuales.

Esta disparidad implica un desafío técnico relevante para la integración de datos, ya que no es posible realizar análisis directos sin un proceso de armonización temporal. En consecuencia, será necesario definir una estrategia de transformación que permita llevar todas las fuentes a una escala temporal común (por ejemplo, agregación a nivel diario o mensual), asegurando consistencia y comparabilidad entre los distintos datasets.

Este proceso introduce además posibles pérdidas de precisión, especialmente al trabajar con datos originalmente más granulares, lo cual deberá ser considerado en el análisis e interpretación de resultados.

---

## 6. Evaluación preliminar de calidad de datos

### 6.1 Completitud

Deberá medirse sobre campos críticos como fecha, coordenadas y variables ambientales principales.

### 6.2 Unicidad

Debe verificarse especialmente en incendios, donde podrían existir registros repetidos por combinaciones de fecha, hora, sensor y coordenadas.

### 6.3 Consistencia básica

Será necesario armonizar formatos de fecha, unidades de medida, granularidades temporales y escalas espaciales.

### 6.4 Validez simple

Se deberán validar rangos básicos, por ejemplo: latitudes y longitudes válidas, precipitación no negativa, concentraciones atmosféricas dentro de rangos plausibles.

**Tabla de métricas de calidad — todas las fuentes de datos:**

**A. Estructura y completitud**

| Métrica | NASA FIRMS | Open-Meteo ERA5-Land | CAMS Calidad del Aire | CHIRPS Precipitación | MODIS Cobertura vegetal |
|---|---|---|---|---|---|
| Registros totales | 3,831,103 | 91 (por punto) | 31 (por punto) | 1,404 | 126 |
| Columnas | 19 | 18 | 16 | 10 | 7 |
| Valores nulos (total) | 0 | 0 | 0 | 13 | 0 |
| Campo/s con nulos | — | — | — | `precipitacion_anomalia_pct` (13) | — |
| Completitud | 100 % | 100 % | 100 % | 99.9 % | 100 % |
| Duplicados | 0 | 0 | 0 | 0 | 0 |

**B. Cobertura temporal y espacial**

| Métrica | NASA FIRMS | Open-Meteo ERA5-Land | CAMS Calidad del Aire | CHIRPS Precipitación | MODIS Cobertura vegetal |
|---|---|---|---|---|---|
| Rango temporal | 2024-01–2024-12 | 2024-01–2024-03 | 2024-01 | 2018-01–2024-06 | 2018–2024 |
| Granularidad temporal | Por evento (horas) | Diaria por estación | Diaria por estación | Mensual por punto | Anual por punto |
| Países cubiertos | ARG, BOL, BRA, CHL, PER, PRY | Rivera (UY) | Rivera (UY) | ARG, BOL, BRA, CHL, PER, PRY | ARG, BOL, BRA, CHL, PER, PRY |
| Rango latitud | −54.5 a +12.6 | −31.4 (fijo) | −31.4 (fijo) | Sudamérica | Sudamérica |
| Rango longitud | −82.0 a −34.8 | −56.0 (fijo) | −56.0 (fijo) | Sudamérica | Sudamérica |

**C. Rangos de variables clave**

| Variable | NASA FIRMS | Open-Meteo ERA5-Land | CAMS Calidad del Aire | CHIRPS Precipitación | MODIS Cobertura vegetal |
|---|---|---|---|---|---|
| Variable principal | Potencia radiativa (FRP) | Temperatura máx. (°C) | PM10 diario (µg/m³) | Precipitación (mm) | Tipo cobertura (IGBP) |
| Valor mínimo | 0.0 MW | 20.4 °C | 2.2 µg/m³ | 0.0 mm | — |
| Valor máximo | 1,314.5 MW | 35.1 °C | 11.2 µg/m³ | 938.8 mm | — |
| Valor promedio | 11.1 MW | 28.5 °C | 6.5 µg/m³ | 119.1 mm | — |
| Variable secundaria | Brillo térmico (K) | Humedad mínima (%) | PM2.5 diario (µg/m³) | Anomalía de precipitación (%) | Combustibilidad |
| Rango secundario | 208–367 K | 36–83 % | 1.5–7.7 µg/m³ | −100 % a +364 % | — |
| Observación de validez | FRP ≥ 0 ✓; lat/lon dentro de Sudamérica ✓ | Temp. y humedad en rangos climáticos plausibles ✓ | PM10 muy por debajo del límite OMS (45 µg/m³) ✓ | Precipitación ≥ 0 ✓; anomalías en rango razonable ✓ | Cobertura tipo 13 (urbana) en todos los puntos monitoreados |

---

## 7. Viabilidad técnica

El problema es viable mediante una arquitectura SQL + NoSQL, ya que combina:

- datos estructurados y agregables, adecuados para un Data Warehouse analítico,
- y datos semi-estructurados o metadata de ejecución, adecuados para un motor documental.

PostgreSQL resulta apropiado para almacenar hechos y dimensiones orientados a consultas agregadas, series temporales y KPIs. MongoDB puede utilizarse para snapshots de ingesta, metadata del ETL, registros crudos o documentos semi-estructurados de las APIs.

El volumen esperado es suficientemente alto como para justificar ETL, integración y persistencia analítica. Se combinarán eventos de incendios, series horarias de clima y aire, precipitación diaria raster y cobertura del suelo anual. FIRMS ofrece cobertura global de incendios activos; Open-Meteo trabaja con resolución horaria; CHIRPS provee precipitación diaria; y MCD12Q1 aporta cobertura global anual.

La actualización incremental puede implementarse mediante:
- consultas por rango temporal en las APIs,
- carga de nuevas particiones o nuevos archivos,
- control por fecha máxima procesada y metadatos de carga.

### 7.1 Principales riesgos

- diferencias de granularidad temporal,
- cambios en APIs,
- series incompletas en algunos puntos,
- complejidad del procesamiento geoespacial,
- necesidad de definir una estrategia espacial razonable para América del Sur.

---

## 8. Preguntas iniciales

1. ¿Cómo evolucionó la cantidad anual de incendios forestales en América del Sur entre 2018 y 2025?
2. ¿Qué países concentran la mayor cantidad de incendios por año?
3. ¿En qué meses se registran más incendios y cómo cambia ese patrón entre países?
4. ¿Qué relación existe entre temperatura media y frecuencia de incendios?
5. ¿Qué relación existe entre baja humedad relativa y aumento de incendios?
6. ¿Cómo varían PM2.5 y PM10 durante períodos con alta actividad de incendios?
7. ¿Qué regiones presentan mayor recurrencia de incendios intensos?
8. ¿Qué relación existe entre déficit de precipitación y aumento de incendios?
9. ¿Qué tipos de cobertura vegetal concentran más incendios por año?
10. ¿Cómo cambia la distribución de incendios entre bosque, pastizal y superficie agrícola?

---

## 9. Arquitectura preliminar

```
Fuentes de datos
├── NASA FIRMS (incendios satelitales)
├── Open-Meteo Historical Weather API
├── Open-Meteo Air Quality API
├── CHIRPS (precipitación geoespacial)
└── MODIS Land Cover (cobertura vegetal)
       ↓
Ingesta y extracción (Python)
- descarga
- llamadas API
- validación inicial
- logging
       ↓
Procesamiento / staging
- limpieza
- estandarización temporal
- armonización espacial
- control de calidad preliminar
       ↓
Persistencia relacional (PostgreSQL)
- hechos
- dimensiones
- series integradas
- capa tipo Data Warehouse
       ↓
Persistencia NoSQL (MongoDB)
- metadata de ingesta
- snapshots
- trazas del pipeline
- documentos semiestructurados
       ↓
Capa analítica
- KPIs
- consultas agregadas
- dashboard en Streamlit
```

### 9.1 Justificación

Python cumplirá el rol de ETL, tal como pide la consigna. PostgreSQL soportará el análisis agregado; MongoDB almacenará información flexible del pipeline; y la capa analítica expondrá indicadores, comparaciones y visualizaciones.

---

## 10. Riesgos y limitaciones

### 10.1 Riesgos

- valores faltantes,
- duplicados,
- diferencias de cobertura entre fuentes,
- cambios en APIs,
- complejidad del cruce espacial entre puntos, grillas raster y cobertura anual.

### 10.2 Limitaciones

- el proyecto se limita a análisis descriptivo y exploratorio,
- no incluye modelado predictivo,
- no incluye análisis sanitario ni económico,
- la estrategia espacial final dependerá de la disponibilidad y factibilidad técnica de cada fuente.

---

## 11. Referencias (APA)

Giglio, L., Schroeder, W., & Justice, C. O. (2016). The collection 6 MODIS active fire detection algorithm and fire products. *Remote Sensing of Environment*, *178*, 31–41.

Jolly, W. M., Cochrane, M. A., Freeborn, P. H., Holden, Z. A., Brown, T. J., Williamson, G. J., & Bowman, D. M. J. S. (2015). Climate-induced variations in global wildfire danger from 1979 to 2013. *Nature Communications*, *6*, 7537.

Reid, C. E., Brauer, M., Johnston, F. H., Jerrett, M., Balmes, J. R., & Elliott, C. T. (2016). Critical review of health impacts of wildfire smoke exposure. *Environmental Health Perspectives*, *124*(9), 1334–1343.
