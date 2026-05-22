# Defensa del dashboard: secciones, datos y propÃ³sito

El dashboard de SINIA-UY estÃ¡ hecho en Streamlit y es la capa de explotaciÃ³n
del modelo de datos. No reemplaza a PostgreSQL ni al ETL: consume los datos
procesados y permite mostrar el resultado del pipeline.

Archivo principal:

```text
dashboard/app.py
```

Capa de acceso a datos:

```text
dashboard/db.py
```

La lÃ³gica de acceso es:

1. Intentar leer desde PostgreSQL.
2. Si PostgreSQL no estÃ¡ disponible, usar Parquet desde `data/processed/`.

Esto permite defender que el sistema tiene una fuente analÃ­tica principal y un
fallback operativo para demo/despliegue.

## Filtros globales

El sidebar tiene filtros que afectan casi todo el dashboard.

### SecciÃ³n

Permite elegir una pÃ¡gina:

- Resumen General
- Focos de Calor
- Ãndice de Riesgo
- Calidad del Aire
- AnÃ¡lisis de Riesgo
- Comparativo por PaÃ­s
- Tiempo Real
- Fuentes y Datos Crudos

### PerÃ­odo

Obtiene el rango real de focos con `obtener_rango_focos()`.

Desde PostgreSQL:

```sql
SELECT MIN(fecha_adq), MAX(fecha_adq)
FROM focos_calor
WHERE pais IN ('ARG','BRA','URY');
```

Si no hay PostgreSQL, lee `firms_procesado.parquet`.

### PaÃ­s

Permite ver:

- Todos
- Brasil (`BRA`)
- Argentina (`ARG`)
- Uruguay (`URY`)

Este filtro es importante porque demuestra que el modelo usa cÃ³digos
normalizados de paÃ­s.

### Rango de fechas

Permite filtrar dentro del perÃ­odo elegido. Recalcula:

- focos del mapa;
- serie diaria;
- total de focos;
- estadÃ­sticas de FRP.

## SecciÃ³n 1: Resumen General

### Para quÃ© sirve

Es la pantalla ejecutiva. Resume el estado general del sistema y conecta todas
las fuentes: FIRMS, Open-Meteo, CAMS, CHIRPS y MODIS.

### QuÃ© muestra

- ExplicaciÃ³n del sistema.
- Fuentes integradas.
- Alertas activas.
- KPIs principales.
- Mapa de focos.
- EvoluciÃ³n semanal.
- DistribuciÃ³n de riesgo.

### Datos que consume

Desde `dashboard/db.py`:

- `cargar_focos()`
- `cargar_focos_por_dia()`
- `contar_focos()`
- `calcular_estadisticas_focos()`
- `cargar_focos_nrt()`
- `cargar_meteo()`
- `cargar_forecast()`
- `cargar_cams()`

### KPIs principales

#### Focos de calor detectados

Sale de `contar_focos()`.

En PostgreSQL:

```sql
SELECT COUNT(*)
FROM focos_calor
WHERE pais IN ('ARG','BRA','URY')
  AND fecha_adq BETWEEN fecha_inicio AND fecha_fin;
```

Defensa:

> Este KPI no usa la muestra del mapa. Usa `COUNT(*)` para mostrar el total
> real del perÃ­odo.

#### FRP mÃ¡ximo registrado

Sale de `calcular_estadisticas_focos()`.

```sql
SELECT MAX(potencia_radiativa)
FROM focos_calor;
```

Defensa:

> FRP significa Fire Radiative Power. Mide intensidad del foco en megawatts.

#### DÃ­as de riesgo alto o muy alto

Sale de `meteo`, usando `nivel_riesgo`.

Defensa:

> Este indicador no viene crudo de una API. Es resultado del ETL, que calcula
> el Ã­ndice de riesgo y lo clasifica.

#### Ãšltimo nivel de riesgo registrado

Sale del Ãºltimo registro meteorolÃ³gico disponible.

Defensa:

> Resume el estado mÃ¡s reciente de riesgo segÃºn datos histÃ³ricos procesados.

### Mapa de focos

Puede mostrar:

- focos actuales NRT;
- focos del perÃ­odo seleccionado.

Usa latitud y longitud de FIRMS.

Defensa:

> El mapa demuestra que los datos son georreferenciados. Cada punto proviene
> de una detecciÃ³n satelital.

### Focos por semana

Agrupa la serie diaria en semanas.

Defensa:

> Esto transforma eventos individuales en una lectura temporal para detectar
> picos de actividad.

## SecciÃ³n 2: Focos de Calor

### Para quÃ© sirve

Analiza especÃ­ficamente las detecciones satelitales FIRMS.

### QuÃ© muestra

- Mapa de focos.
- Tabla o muestras de focos.
- Distribuciones por fecha, paÃ­s, confianza o FRP.
- EvoluciÃ³n temporal.

### Datos que consume

Principalmente:

- `focos_calor` en PostgreSQL.
- `firms_procesado.parquet` como fallback.

### Campos importantes

- `fecha_adq`
- `latitud`
- `longitud`
- `pais`
- `potencia_radiativa`
- `confianza_raw`
- `confianza_num`
- `satelite`
- `dia_noche`
- `es_diurno`

### Defensa

> Esta secciÃ³n muestra los hechos de incendio o anomalÃ­a tÃ©rmica. FIRMS no
> dice necesariamente que cada punto sea un incendio confirmado por bomberos,
> sino una detecciÃ³n satelital de calor con confianza y potencia radiativa.

### Pregunta probable

Â¿Por quÃ© el mapa no muestra millones de puntos?

Respuesta:

> Por rendimiento visual. El KPI usa el total real, pero el mapa limita o
> muestra una muestra para que la visualizaciÃ³n sea navegable.

## SecciÃ³n 3: Ãndice de Riesgo

### Para quÃ© sirve

Explica el riesgo calculado a partir de meteorologÃ­a.

### QuÃ© muestra

- Riesgo por punto.
- Riesgo por fecha.
- Niveles `bajo`, `moderado`, `alto`, `muy_alto`.
- Variables meteorolÃ³gicas asociadas.

### Datos que consume

- `meteo_diario`
- vista `v_riesgo_historico`
- vista `v_riesgo_actual`
- Parquet `meteo_procesado_*.parquet` como fallback.

### FÃ³rmula

```text
indice_riesgo =
riesgo_temp * 0.25 +
riesgo_humedad * 0.30 +
riesgo_viento * 0.20 +
riesgo_sequia * 0.25
```

### Defensa

> Esta secciÃ³n muestra una transformaciÃ³n analÃ­tica creada por el proyecto.
> Open-Meteo entrega variables meteorolÃ³gicas crudas; el ETL las normaliza y
> calcula una mÃ©trica Ãºnica entre 0 y 1.

### Pregunta probable

Â¿El Ã­ndice viene de Open-Meteo?

Respuesta:

> No. Open-Meteo entrega temperatura, humedad, viento y evapotranspiraciÃ³n.
> El Ã­ndice es una variable derivada del proyecto.

## SecciÃ³n 4: Calidad del Aire

### Para quÃ© sirve

Analiza contaminaciÃ³n y partÃ­culas asociadas a condiciones ambientales o humo.

### QuÃ© muestra

- PM10.
- PM2.5.
- AQI europeo.
- DÃ­as que superan el umbral OMS.
- Nivel de PM10: normal, elevado o alerta.

### Datos que consume

- `calidad_aire_diario`.
- vista `v_alertas_calidad_aire`.
- Parquet `cams_procesado_*.parquet` como fallback.

### TransformaciÃ³n clave

CAMS llega horario. El ETL lo agrupa a diario:

- `pm10_media`
- `pm10_max`
- `pm10_p95`
- `pm2_5_media`
- `pm2_5_max`
- `horas_validas`

### Defensa

> Esta secciÃ³n demuestra transformaciÃ³n de granularidad: de datos horarios a
> indicadores diarios. AdemÃ¡s aplica una regla de negocio: PM10 medio diario
> mayor a 45 Âµg/mÂ³ supera el umbral OMS.

## SecciÃ³n 5: AnÃ¡lisis de Riesgo

### Para quÃ© sirve

Cruza riesgo, meteorologÃ­a y dÃ­as crÃ­ticos para entender patrones.

### QuÃ© muestra

- DÃ­as crÃ­ticos.
- Puntos con mayor riesgo.
- DistribuciÃ³n de niveles.
- Variables que explican el riesgo.

### Datos que consume

- `v_dias_criticos`.
- `v_riesgo_historico`.
- `meteo_diario`.

### Defensa

> Esta secciÃ³n es analÃ­tica. No se limita a mostrar datos crudos, sino que
> permite interpretar cuÃ¡ndo y dÃ³nde hubo condiciones peligrosas.

### Pregunta probable

Â¿QuÃ© es un dÃ­a crÃ­tico?

Respuesta:

> Un dÃ­a crÃ­tico es una fecha en la que al menos un punto tuvo `nivel_riesgo`
> alto o muy alto. La vista `v_dias_criticos` agrupa esos casos.

## SecciÃ³n 6: Comparativo por PaÃ­s

### Para quÃ© sirve

Compara Uruguay, Brasil, Argentina y Chile.

### QuÃ© muestra

- Riesgo mensual por paÃ­s.
- Focos mensuales por paÃ­s.
- Tabla comparativa.
- Total de focos.
- Riesgo promedio.
- Riesgo mÃ¡ximo.
- DÃ­as crÃ­ticos.
- FRP mÃ¡ximo.

### Datos que consume

- `v_riesgo_por_pais`.
- `v_focos_por_pais_mes`.
- fallback desde Parquet calculado en `dashboard/db.py`.

### Defensa

> Esta secciÃ³n justifica el alcance regional. Uruguay se analiza junto con
> Brasil y Argentina porque el riesgo ambiental y el humo no respetan fronteras
> administrativas.

### Pregunta probable

Â¿Por quÃ© comparar paÃ­ses y no solo Uruguay?

Respuesta:

> Porque el sistema estudia riesgo regional. Brasil y Argentina pueden tener
> actividad de focos o condiciones que afectan el contexto ambiental uruguayo.

## SecciÃ³n 7: Tiempo Real

### Para quÃ© sirve

Muestra informaciÃ³n reciente y pronÃ³stico.

### QuÃ© muestra

- Focos NRT de las Ãºltimas 24 horas.
- Forecast de riesgo.
- Estado de actualizaciÃ³n.
- Alertas si se superan umbrales.

### Datos que consume

- `cargar_focos_nrt()`.
- `cargar_forecast()`.
- `firms_nrt_procesado.parquet`.
- `forecast_riesgo.parquet`.
- vista `v_forecast_riesgo` si existe PostgreSQL.

### Defensa

> Esta secciÃ³n separa histÃ³rico de operaciÃ³n reciente. FIRMS NRT permite ver
> focos cercanos al presente y forecast permite anticipar riesgo futuro.

### Pregunta probable

Â¿QuÃ© diferencia hay entre histÃ³rico y NRT?

Respuesta:

> HistÃ³rico es dato consolidado de aÃ±os anteriores. NRT significa Near Real
> Time: datos recientes con menor latencia.

## SecciÃ³n 8: Fuentes y Datos Crudos

### Para quÃ© sirve

Demuestra trazabilidad.

### QuÃ© muestra

- DescripciÃ³n de cada fuente.
- Archivos crudos descargados.
- Columnas originales.
- Muestras de CSV crudo.
- Volumen aproximado de filas.

### Fuentes mostradas

- NASA FIRMS.
- Open-Meteo.
- CAMS.
- CHIRPS.
- MODIS.

### Defensa

> Esta secciÃ³n es importante para auditorÃ­a. Permite demostrar que el dato no
> aparece mÃ¡gicamente en la base, sino que viene de fuentes externas concretas
> y queda guardado antes de transformarse.

### Pregunta probable

Â¿Por quÃ© mostrar datos crudos al usuario?

Respuesta:

> No es una pantalla para usuario final comÃºn; es una pantalla de evidencia
> tÃ©cnica. Sirve para defensa, auditorÃ­a y trazabilidad del pipeline.

## Estado de base de datos

El sidebar muestra si se estÃ¡ usando:

- PostgreSQL.
- Parquet.

Defensa:

> Esto permite saber si el dashboard estÃ¡ trabajando contra la base analÃ­tica
> principal o contra el fallback procesado.

## Auto-refresh

El dashboard tiene opciÃ³n de auto-refresh cada 5 minutos.

Defensa:

> Es Ãºtil para monitoreo operativo, especialmente con datos NRT y forecast.

## CÃ³mo defender el dashboard en una frase

> El dashboard es la capa de visualizaciÃ³n y explotaciÃ³n del modelo de datos:
> consume PostgreSQL como fuente principal, usa Parquet como fallback, permite
> filtrar por paÃ­s y perÃ­odo, muestra focos FIRMS, riesgo meteorolÃ³gico, calidad
> del aire, comparaciones regionales, tiempo real y evidencia de datos crudos.

## Preguntas trampa

### El dashboard calcula todo?

No. Algunas agregaciones se hacen en vistas SQL o en la capa `dashboard/db.py`.
El dashboard principalmente visualiza y coordina filtros.

### Si PostgreSQL falla, se cae todo?

No. Hay fallback a Parquet para muchas funciones.

### Por quÃ© hay muestras y no todos los focos en mapa?

Por rendimiento visual. El total real se calcula con SQL, pero visualizar
millones de puntos puede volver inutilizable el mapa.

### QuÃ© secciÃ³n demuestra mejor la base de datos?

Comparativo por PaÃ­s y AnÃ¡lisis de Riesgo, porque usan vistas, agregaciones,
filtros y relaciones entre puntos, paÃ­ses y hechos.

### QuÃ© secciÃ³n demuestra mejor el ETL?

Fuentes y Datos Crudos, porque permite comparar datos originales con datos
procesados; Ãndice de Riesgo, porque muestra una variable derivada del ETL.
