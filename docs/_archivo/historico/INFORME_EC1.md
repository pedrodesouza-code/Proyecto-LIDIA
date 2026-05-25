# SEDE: RIVERA

# Proyecto de IngenierÃ­a de Datos

## LICENCIATURA EN INGENIERÃA DE DATOS E INTELIGENCIA ARTIFICIAL

---

**Nombre del trabajo:** "AnÃ¡lisis integrado de incendios forestales, condiciones meteorolÃ³gicas, precipitaciÃ³n, calidad del aire y cobertura vegetal en AmÃ©rica del Sur durante el perÃ­odo 2018â€“2025"

**Autores:** Pedro De Souza, Rafael Quintanilla, Katerin Gonzalez

---

## Ãndice

1. IntroducciÃ³n
2. FormulaciÃ³n del problema
   - 2.1 Contexto del problema
   - 2.2 Actores involucrados
   - 2.3 Variables clave del fenÃ³meno
   - 2.4 DimensiÃ³n temporal
   - 2.5 DimensiÃ³n espacial
   - 2.6 JustificaciÃ³n de la relevancia del problema
   - 2.7 Problema
3. Objetivos
   - 3.1 Objetivo general
   - 3.2 Objetivos especÃ­ficos
4. IdentificaciÃ³n y anÃ¡lisis de fuentes de datos
   - 4.1 NASA FIRMS (VIIRS)
   - 4.2 Open-Meteo (ERA5-Land)
   - 4.3 Copernicus Atmosphere Monitoring Service
   - 4.4 CHIRPS
   - 4.5 MODIS (Cobertura vegetal)
   - 4.6 INUMET (fuente evaluada fuera de alcance)
5. ExploraciÃ³n preliminar de datos
   - 5.1 Acceso real a los datos
   - 5.2 Evidencias
   - 5.3 ObservaciÃ³n
   - 5.4 Problemas destacados
6. EvaluaciÃ³n preliminar de calidad de datos
   - 6.1 Completitud
   - 6.2 Unicidad
   - 6.3 Consistencia bÃ¡sica
   - 6.4 Validez simple
7. Viabilidad tÃ©cnica
   - 7.1 Principales riesgos
8. Preguntas iniciales
9. Arquitectura preliminar
   - 9.1 JustificaciÃ³n
10. Riesgos y limitaciones
    - 10.1 Riesgos
    - 10.2 Limitaciones
11. Referencias (APA)

---

## 1. IntroducciÃ³n

Los incendios forestales constituyen un fenÃ³meno ambiental de alta relevancia debido a su capacidad para alterar ecosistemas, afectar los ciclos naturales del ambiente y modificar la composiciÃ³n atmosfÃ©rica. La literatura cientÃ­fica seÃ±ala que los incendios desempeÃ±an un papel importante en los sistemas terrestres y atmosfÃ©ricos, y que su comportamiento estÃ¡ estrechamente vinculado con la estructura de la vegetaciÃ³n, el clima y la disponibilidad de combustible.

De acuerdo con Jolly et al. (2015), la variaciÃ³n del peligro global de incendios se encuentra asociada a condiciones climÃ¡ticas, y la duraciÃ³n de la temporada de incendios ha aumentado en muchas regiones del mundo. En ese marco, variables como temperatura, humedad relativa, precipitaciÃ³n y viento resultan claves para comprender la ocurrencia y propagaciÃ³n del fuego.

Estudios realizados por Reid et al. (2016) muestran que el humo de incendios forestales contiene elevadas concentraciones de material particulado fino y otros contaminantes atmosfÃ©ricos, lo que genera un deterioro significativo en la calidad del aire. Por esta razÃ³n, la calidad del aire constituye una dimensiÃ³n central para el anÃ¡lisis de estos eventos.

En paralelo, el desarrollo de sensores satelitales permitiÃ³ mejorar sustancialmente el monitoreo ambiental. SegÃºn Giglio et al. (2016), los productos MODIS de incendios activos constituyen una base robusta para detectar eventos tÃ©rmicos y construir anÃ¡lisis espaciales y temporales. A su vez, NASA FIRMS distribuye datos globales de incendios activos a partir de MODIS y VIIRS con actualizaciÃ³n casi en tiempo real.

La disponibilidad de APIs meteorolÃ³gicas, datos atmosfÃ©ricos, productos de precipitaciÃ³n satelital y datasets globales de cobertura del suelo plantea un desafÃ­o propio de la ingenierÃ­a de datos: integrar fuentes heterogÃ©neas, armonizar granularidades distintas y construir una capa analÃ­tica reutilizable. En este contexto, la disponibilidad de datos climÃ¡ticos globales de alta resoluciÃ³n ha facilitado el anÃ¡lisis ambiental a gran escala.

---

## 2. FormulaciÃ³n del problema

### 2.1 Contexto del problema

En AmÃ©rica del Sur, los incendios forestales afectan ecosistemas de gran relevancia ecolÃ³gica y productiva. Su ocurrencia no depende de una Ãºnica variable, sino de la interacciÃ³n entre condiciones meteorolÃ³gicas, disponibilidad de combustible, estacionalidad, precipitaciÃ³n acumulada y contexto de cobertura vegetal. La literatura cientÃ­fica indica que el fuego debe analizarse como parte del sistema terrestre y no como un evento aislado.

AdemÃ¡s, los incendios producen emisiones atmosfÃ©ricas que deterioran la calidad del aire a escala regional. En consecuencia, un anÃ¡lisis con sentido aplicado no deberÃ­a limitarse a contar focos de calor, sino estudiar en quÃ© condiciones ocurrieron, sobre quÃ© tipo de cobertura del suelo se produjeron y quÃ© efecto tuvieron sobre la atmÃ³sfera.

### 2.2 Actores involucrados

Los principales actores involucrados en este dominio son:

- Organismos internacionales de observaciÃ³n ambiental, como NASA, que generan y distribuyen datos satelitales de incendios.
- Proveedores de datos meteorolÃ³gicos y atmosfÃ©ricos, como Open-Meteo, que ofrecen variables climÃ¡ticas y de calidad del aire mediante APIs.
- Centros de investigaciÃ³n climÃ¡tica y ambiental, que desarrollan productos como CHIRPS y datasets globales de cobertura del suelo.
- Usuarios del sistema, como investigadores, analistas de datos y organismos de monitoreo ambiental.

### 2.3 Variables clave del fenÃ³meno

Las variables principales del proyecto son:

**Incendios**
- latitud
- longitud
- fecha
- hora
- brillo tÃ©rmico / intensidad
- potencia radiativa del fuego
- confianza de detecciÃ³n

**Condiciones meteorolÃ³gicas**
- temperatura
- humedad relativa
- velocidad del viento
- precipitaciÃ³n

**Calidad del aire**
- PM2.5
- PM10
- CO
- NOâ‚‚
- Oâ‚ƒ

**Cobertura vegetal / uso del suelo**
- tipo de cobertura dominante
- clase de vegetaciÃ³n o uso del suelo
- distribuciÃ³n espacial anual de coberturas

### 2.4 DimensiÃ³n temporal

El anÃ¡lisis se realizarÃ¡ sobre el perÃ­odo 2018â€“2025. Ese rango permite estudiar patrones estacionales e interanuales y, al mismo tiempo, aprovechar fuentes con cobertura histÃ³rica suficiente. Open-Meteo documenta disponibilidad histÃ³rica amplia para variables meteorolÃ³gicas; CHIRPS ofrece precipitaciÃ³n diaria desde 1981; y MCD12Q1 es un producto anual global de cobertura del suelo.

### 2.5 DimensiÃ³n espacial

La unidad territorial del proyecto serÃ¡ AmÃ©rica del Sur. Esta delimitaciÃ³n amplÃ­a el volumen de datos respecto a un enfoque nacional, permite comparaciones por paÃ­s o subregiÃ³n y justifica de mejor manera una arquitectura de ingenierÃ­a de datos con integraciÃ³n multifuente y anÃ¡lisis agregado.

### 2.6 JustificaciÃ³n de la relevancia del problema

El valor del proyecto no radica sÃ³lo en detectar incendios, sino en cruzar datos con sentido para comprender cÃ³mo se comportan segÃºn el contexto climÃ¡tico, quÃ© impacto tienen sobre la calidad del aire y sobre quÃ© tipos de cobertura vegetal ocurren con mayor frecuencia. Esa integraciÃ³n puede transformarse en una herramienta Ãºtil para monitoreo ambiental, anÃ¡lisis territorial y generaciÃ³n de indicadores histÃ³ricos reutilizables.

### 2.7 Problema

El proyecto estudiarÃ¡ la relaciÃ³n entre la ocurrencia de incendios forestales, las condiciones meteorolÃ³gicas, la precipitaciÃ³n, la calidad del aire y la cobertura vegetal en AmÃ©rica del Sur durante el perÃ­odo 2018â€“2025, utilizando datos abiertos y heterogÃ©neos provenientes de sensores satelitales, APIs ambientales y datasets geoespaciales.

El problema de ingenierÃ­a de datos consiste en integrar fuentes que presentan diferencias en formato, granularidad temporal, resoluciÃ³n espacial y estructura conceptual, para construir una base analÃ­tica unificada que permita responder preguntas descriptivas y comparativas. Quedan fuera del alcance de esta etapa la predicciÃ³n de incendios, el anÃ¡lisis sanitario y la evaluaciÃ³n econÃ³mica.

---

## 3. Objetivos

### 3.1 Objetivo general

Analizar la relaciÃ³n entre incendios forestales, condiciones meteorolÃ³gicas, la calidad del aire y la cobertura vegetal mediante la integraciÃ³n de mÃºltiples fuentes de datos ambientales en AmÃ©rica del Sur durante el perÃ­odo 2018â€“2025.

### 3.2 Objetivos especÃ­ficos

1. Comparar patrones de incendios entre diferentes paÃ­ses de AmÃ©rica del Sur.
2. Analizar la evoluciÃ³n temporal de los incendios forestales en AmÃ©rica del Sur durante el perÃ­odo 2018â€“2025.
3. Evaluar la relaciÃ³n entre variables meteorolÃ³gicas â€”temperatura, humedad, viento y precipitaciÃ³nâ€” y la ocurrencia de incendios forestales.
4. Analizar cÃ³mo varÃ­an la calidad del aire y la distribuciÃ³n de incendios segÃºn el tipo de cobertura vegetal dominante.

---

## 4. IdentificaciÃ³n y anÃ¡lisis de fuentes de datos

### 4.1 NASA FIRMS (VIIRS)

| Campo | Detalle |
|---|---|
| **Nombre y origen** | NASA FIRMS (Fire Information for Resource Management System), basado en sensores VIIRS de la NASA |
| **Enlace oficial** | https://firms.modaps.eosdis.nasa.gov/ |
| **Tipo de acceso** | API / descarga directa |
| **Formato** | JSON |
| **Volumen aproximado** | 6,900 registros (Uruguay) |
| **Frecuencia de actualizaciÃ³n** | Casi en tiempo real (minutos/horas) |
| **Granularidad** | Alta (detecciÃ³n puntual por coordenadas) |
| **Variables relevantes** | Latitud / Longitud, Fecha / Hora, Brightness, Confidence |
| **Limitaciones** | Posibles falsos positivos; interferencia por nubosidad |
| **Riesgos tÃ©cnicos** | Variabilidad en calidad (`confidence`); necesidad de filtrado previo |

### 4.2 Open-Meteo (ERA5-Land)

| Campo | Detalle |
|---|---|
| **Nombre y origen** | Open-Meteo (datos derivados de ERA5-Land, modelo climÃ¡tico europeo) |
| **Enlace oficial** | https://open-meteo.com/ |
| **Tipo de acceso** | API REST |
| **Formato** | JSON |
| **Volumen aproximado** | 1,332,888 registros |
| **Frecuencia de actualizaciÃ³n** | Horaria |
| **Granularidad** | Media (grilla geoespacial) |
| **Variables relevantes** | Temperatura, Humedad, Velocidad del viento, PrecipitaciÃ³n, ET0 |
| **Limitaciones** | Datos modelados (no observados) |
| **Riesgos tÃ©cnicos** | Sesgo local; interpolaciÃ³n espacial; dependencia de API |

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
| **Nombre y origen** | Copernicus Atmosphere Monitoring Service (CAMS), UniÃ³n Europea |
| **Enlace oficial** | https://atmosphere.copernicus.eu/ |
| **Tipo de acceso** | Descarga / API |
| **Formato** | NetCDF, CSV |
| **Volumen aproximado** | 1,332,888 registros |
| **Frecuencia de actualizaciÃ³n** | Horaria |
| **Granularidad** | Media-baja (grillas grandes) |
| **Variables relevantes** | PM2.5, PM10, AQI, Polvo |
| **Limitaciones** | Baja resoluciÃ³n espacial |
| **Riesgos tÃ©cnicos** | Datos faltantes; necesidad de agregaciÃ³n |

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
| **Frecuencia de actualizaciÃ³n** | Mensual |
| **Granularidad** | Media |
| **Variables relevantes** | PrecipitaciÃ³n acumulada |
| **Limitaciones** | Baja resoluciÃ³n temporal |
| **Riesgos tÃ©cnicos** | AgregaciÃ³n mensual; procesamiento de raster |

### 4.5 MODIS (Cobertura vegetal)

| Campo | Detalle |
|---|---|
| **Nombre y origen** | MODIS (NASA), producto de cobertura terrestre |
| **Enlace oficial** | https://appeears.earthdatacloud.nasa.gov/ |
| **Tipo de acceso** | Descarga |
| **Formato** | GeoTIFF, HDF |
| **Volumen aproximado** | 167 registros |
| **Frecuencia de actualizaciÃ³n** | Anual |
| **Granularidad** | Media |
| **Variables relevantes** | Tipo de cobertura (IGBP) |
| **Limitaciones** | Baja variabilidad temporal |
| **Riesgos tÃ©cnicos** | ClasificaciÃ³n discreta; procesamiento geoespacial |

### 4.6 INUMET (fuente evaluada fuera de alcance)

| Campo | Detalle |
|---|---|
| **Nombre y origen** | Instituto Uruguayo de MeteorologÃ­a (INUMET) |
| **Enlace oficial** | https://www.inumet.gub.uy/ |
| **Tipo de acceso** | Portal institucional y servicios publicados |
| **Formato** | Web/descargas segun producto |
| **Volumen aproximado** | Variable por estacion/producto |
| **Frecuencia de actualizaciÃ³n** | Variable |
| **Granularidad** | Alta (estaciones meteorolÃ³gicas) |
| **Variables relevantes** | Temperatura, PrecipitaciÃ³n, Humedad, Viento |
| **Limitaciones** | Se descarta para el pipeline final para mantener fuentes abiertas transnacionales y comparables en Uruguay, Brasil, Argentina y Chile |
| **Riesgos tÃ©cnicos** | Datos faltantes; inconsistencias entre estaciones |

---

## 5. ExploraciÃ³n preliminar de datos

### 5.1 Acceso real a los datos

Se realizÃ³ una exploraciÃ³n preliminar de las fuentes seleccionadas mediante la descarga de muestras y consultas a las APIs correspondientes, con el objetivo de comprender su estructura y detectar posibles problemas iniciales.

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

### 5.3 ObservaciÃ³n

**NASA FIRMS â€” `df.dtypes`:**

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

**NASA FIRMS â€” `df.isnull().sum()`:**

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

**Open-Meteo ERA5-Land (meteorolÃ³gico) â€” `df.isnull().sum()`:**

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

**Open-Meteo ERA5-Land (meteorolÃ³gico) â€” `df.info()`:**

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

**CAMS Calidad del Aire â€” `df.info()`:**

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

Durante el anÃ¡lisis de las fuentes de datos se detectÃ³ una heterogeneidad significativa en la granularidad temporal. Algunas fuentes, como NASA FIRMS y Open-Meteo, trabajan con datos en tiempo casi real u horarios, mientras que otras como CHIRPS presentan informaciÃ³n agregada a nivel mensual, y MODIS ofrece actualizaciones anuales.

Esta disparidad implica un desafÃ­o tÃ©cnico relevante para la integraciÃ³n de datos, ya que no es posible realizar anÃ¡lisis directos sin un proceso de armonizaciÃ³n temporal. En consecuencia, serÃ¡ necesario definir una estrategia de transformaciÃ³n que permita llevar todas las fuentes a una escala temporal comÃºn (por ejemplo, agregaciÃ³n a nivel diario o mensual), asegurando consistencia y comparabilidad entre los distintos datasets.

Este proceso introduce ademÃ¡s posibles pÃ©rdidas de precisiÃ³n, especialmente al trabajar con datos originalmente mÃ¡s granulares, lo cual deberÃ¡ ser considerado en el anÃ¡lisis e interpretaciÃ³n de resultados.

---

## 6. EvaluaciÃ³n preliminar de calidad de datos

### 6.1 Completitud

DeberÃ¡ medirse sobre campos crÃ­ticos como fecha, coordenadas y variables ambientales principales.

### 6.2 Unicidad

Debe verificarse especialmente en incendios, donde podrÃ­an existir registros repetidos por combinaciones de fecha, hora, sensor y coordenadas.

### 6.3 Consistencia bÃ¡sica

SerÃ¡ necesario armonizar formatos de fecha, unidades de medida, granularidades temporales y escalas espaciales.

### 6.4 Validez simple

Se deberÃ¡n validar rangos bÃ¡sicos, por ejemplo: latitudes y longitudes vÃ¡lidas, precipitaciÃ³n no negativa, concentraciones atmosfÃ©ricas dentro de rangos plausibles.

**Tabla de mÃ©tricas de calidad â€” todas las fuentes de datos:**

**A. Estructura y completitud**

| MÃ©trica | NASA FIRMS | Open-Meteo ERA5-Land | CAMS Calidad del Aire | CHIRPS PrecipitaciÃ³n | MODIS Cobertura vegetal |
|---|---|---|---|---|---|
| Registros totales | 3,831,103 | 91 (por punto) | 31 (por punto) | 1,404 | 126 |
| Columnas | 19 | 18 | 16 | 10 | 7 |
| Valores nulos (total) | 0 | 0 | 0 | 13 | 0 |
| Campo/s con nulos | â€” | â€” | â€” | `precipitacion_anomalia_pct` (13) | â€” |
| Completitud | 100 % | 100 % | 100 % | 99.9 % | 100 % |
| Duplicados | 0 | 0 | 0 | 0 | 0 |

**B. Cobertura temporal y espacial**

| MÃ©trica | NASA FIRMS | Open-Meteo ERA5-Land | CAMS Calidad del Aire | CHIRPS PrecipitaciÃ³n | MODIS Cobertura vegetal |
|---|---|---|---|---|---|
| Rango temporal | 2024-01â€“2024-12 | 2024-01â€“2024-03 | 2024-01 | 2018-01â€“2024-06 | 2018â€“2024 |
| Granularidad temporal | Por evento (horas) | Diaria por estaciÃ³n | Diaria por estaciÃ³n | Mensual por punto | Anual por punto |
| PaÃ­ses cubiertos | ARG, BOL, BRA, CHL, PER, PRY | Rivera (UY) | Rivera (UY) | ARG, BOL, BRA, CHL, PER, PRY | ARG, BOL, BRA, CHL, PER, PRY |
| Rango latitud | âˆ’54.5 a +12.6 | âˆ’31.4 (fijo) | âˆ’31.4 (fijo) | SudamÃ©rica | SudamÃ©rica |
| Rango longitud | âˆ’82.0 a âˆ’34.8 | âˆ’56.0 (fijo) | âˆ’56.0 (fijo) | SudamÃ©rica | SudamÃ©rica |

**C. Rangos de variables clave**

| Variable | NASA FIRMS | Open-Meteo ERA5-Land | CAMS Calidad del Aire | CHIRPS PrecipitaciÃ³n | MODIS Cobertura vegetal |
|---|---|---|---|---|---|
| Variable principal | Potencia radiativa (FRP) | Temperatura mÃ¡x. (Â°C) | PM10 diario (Âµg/mÂ³) | PrecipitaciÃ³n (mm) | Tipo cobertura (IGBP) |
| Valor mÃ­nimo | 0.0 MW | 20.4 Â°C | 2.2 Âµg/mÂ³ | 0.0 mm | â€” |
| Valor mÃ¡ximo | 1,314.5 MW | 35.1 Â°C | 11.2 Âµg/mÂ³ | 938.8 mm | â€” |
| Valor promedio | 11.1 MW | 28.5 Â°C | 6.5 Âµg/mÂ³ | 119.1 mm | â€” |
| Variable secundaria | Brillo tÃ©rmico (K) | Humedad mÃ­nima (%) | PM2.5 diario (Âµg/mÂ³) | AnomalÃ­a de precipitaciÃ³n (%) | Combustibilidad |
| Rango secundario | 208â€“367 K | 36â€“83 % | 1.5â€“7.7 Âµg/mÂ³ | âˆ’100 % a +364 % | â€” |
| ObservaciÃ³n de validez | FRP â‰¥ 0 âœ“; lat/lon dentro de SudamÃ©rica âœ“ | Temp. y humedad en rangos climÃ¡ticos plausibles âœ“ | PM10 muy por debajo del lÃ­mite OMS (45 Âµg/mÂ³) âœ“ | PrecipitaciÃ³n â‰¥ 0 âœ“; anomalÃ­as en rango razonable âœ“ | Cobertura tipo 13 (urbana) en todos los puntos monitoreados |

---

## 7. Viabilidad tÃ©cnica

El problema es viable mediante una arquitectura SQL + NoSQL, ya que combina:

- datos estructurados y agregables, adecuados para un Data Warehouse analÃ­tico,
- y datos semi-estructurados o metadata de ejecuciÃ³n, adecuados para un motor documental.

PostgreSQL resulta apropiado para almacenar hechos y dimensiones orientados a consultas agregadas, series temporales y KPIs. MongoDB puede utilizarse para snapshots de ingesta, metadata del ETL, registros crudos o documentos semi-estructurados de las APIs.

El volumen esperado es suficientemente alto como para justificar ETL, integraciÃ³n y persistencia analÃ­tica. Se combinarÃ¡n eventos de incendios, series horarias de clima y aire, precipitaciÃ³n diaria raster y cobertura del suelo anual. FIRMS ofrece cobertura global de incendios activos; Open-Meteo trabaja con resoluciÃ³n horaria; CHIRPS provee precipitaciÃ³n diaria; y MCD12Q1 aporta cobertura global anual.

La actualizaciÃ³n incremental puede implementarse mediante:
- consultas por rango temporal en las APIs,
- carga de nuevas particiones o nuevos archivos,
- control por fecha mÃ¡xima procesada y metadatos de carga.

### 7.1 Principales riesgos

- diferencias de granularidad temporal,
- cambios en APIs,
- series incompletas en algunos puntos,
- complejidad del procesamiento geoespacial,
- necesidad de definir una estrategia espacial razonable para AmÃ©rica del Sur.

---

## 8. Preguntas iniciales

1. Â¿CÃ³mo evolucionÃ³ la cantidad anual de incendios forestales en AmÃ©rica del Sur entre 2018 y 2025?
2. Â¿QuÃ© paÃ­ses concentran la mayor cantidad de incendios por aÃ±o?
3. Â¿En quÃ© meses se registran mÃ¡s incendios y cÃ³mo cambia ese patrÃ³n entre paÃ­ses?
4. Â¿QuÃ© relaciÃ³n existe entre temperatura media y frecuencia de incendios?
5. Â¿QuÃ© relaciÃ³n existe entre baja humedad relativa y aumento de incendios?
6. Â¿CÃ³mo varÃ­an PM2.5 y PM10 durante perÃ­odos con alta actividad de incendios?
7. Â¿QuÃ© regiones presentan mayor recurrencia de incendios intensos?
8. Â¿QuÃ© relaciÃ³n existe entre dÃ©ficit de precipitaciÃ³n y aumento de incendios?
9. Â¿QuÃ© tipos de cobertura vegetal concentran mÃ¡s incendios por aÃ±o?
10. Â¿CÃ³mo cambia la distribuciÃ³n de incendios entre bosque, pastizal y superficie agrÃ­cola?

---

## 9. Arquitectura preliminar

```
Fuentes de datos
â”œâ”€â”€ NASA FIRMS (incendios satelitales)
â”œâ”€â”€ Open-Meteo Historical Weather API
â”œâ”€â”€ Open-Meteo Air Quality API
â”œâ”€â”€ CHIRPS (precipitaciÃ³n geoespacial)
â””â”€â”€ MODIS Land Cover (cobertura vegetal)
       â†“
Ingesta y extracciÃ³n (Python)
- descarga
- llamadas API
- validaciÃ³n inicial
- logging
       â†“
Procesamiento / staging
- limpieza
- estandarizaciÃ³n temporal
- armonizaciÃ³n espacial
- control de calidad preliminar
       â†“
Persistencia relacional (PostgreSQL)
- hechos
- dimensiones
- series integradas
- capa tipo Data Warehouse
       â†“
Persistencia NoSQL (MongoDB)
- metadata de ingesta
- snapshots
- trazas del pipeline
- documentos semiestructurados
       â†“
Capa analÃ­tica
- KPIs
- consultas agregadas
- dashboard en Streamlit
```

### 9.1 JustificaciÃ³n

Python cumplirÃ¡ el rol de ETL, tal como pide la consigna. PostgreSQL soportarÃ¡ el anÃ¡lisis agregado; MongoDB almacenarÃ¡ informaciÃ³n flexible del pipeline; y la capa analÃ­tica expondrÃ¡ indicadores, comparaciones y visualizaciones.

---

## 10. Riesgos y limitaciones

### 10.1 Riesgos

- valores faltantes,
- duplicados,
- diferencias de cobertura entre fuentes,
- cambios en APIs,
- complejidad del cruce espacial entre puntos, grillas raster y cobertura anual.

### 10.2 Limitaciones

- el proyecto se limita a anÃ¡lisis descriptivo y exploratorio,
- no incluye modelado predictivo,
- no incluye anÃ¡lisis sanitario ni econÃ³mico,
- la estrategia espacial final dependerÃ¡ de la disponibilidad y factibilidad tÃ©cnica de cada fuente.

---

## 11. Referencias (APA)

Giglio, L., Schroeder, W., & Justice, C. O. (2016). The collection 6 MODIS active fire detection algorithm and fire products. *Remote Sensing of Environment*, *178*, 31â€“41.

Jolly, W. M., Cochrane, M. A., Freeborn, P. H., Holden, Z. A., Brown, T. J., Williamson, G. J., & Bowman, D. M. J. S. (2015). Climate-induced variations in global wildfire danger from 1979 to 2013. *Nature Communications*, *6*, 7537.

Reid, C. E., Brauer, M., Johnston, F. H., Jerrett, M., Balmes, J. R., & Elliott, C. T. (2016). Critical review of health impacts of wildfire smoke exposure. *Environmental Health Perspectives*, *124*(9), 1334â€“1343.
