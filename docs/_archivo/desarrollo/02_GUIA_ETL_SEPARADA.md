# Guia separada del ETL

Este archivo explica solo el ETL: que entra, que se transforma, que sale y donde queda.

## Extract

Ruta:

```text
etl/extract/
```

| Script | Fuente | Que descarga |
|---|---|---|
| `extract_firms.py` | NASA FIRMS | Focos de calor satelitales |
| `extract_meteo.py` | Open-Meteo Archive | Meteorologia historica |
| `extract_forecast.py` | Open-Meteo Forecast | Pronostico |
| `extract_cams.py` | CAMS/Open-Meteo Air Quality | Calidad del aire |
| `extract_chirps.py` | CHIRPS | Precipitacion mensual |
| `extract_modis.py` | MODIS/AppEEARS | Cobertura vegetal |

Salida cruda:

```text
data/raw/
```

Defensa: se guarda crudo para trazabilidad y reproceso.

## Transform

Ruta:

```text
etl/transform/
```

### FIRMS

Archivo: `etl/transform/transform_firms.py`

Transforma:

| Crudo | Final |
|---|---|
| `latitude` | `latitud` |
| `longitude` | `longitud` |
| `acq_date` | `fecha_adq` |
| `acq_time` | `hora_adq_hhmm` |
| `frp` | `potencia_radiativa` |
| `confidence` | `confianza_raw` y `confianza_num` |
| `satellite` | `satelite` |
| `instrument` | `instrumento` |
| `daynight` | `dia_noche` y `es_diurno` |
| coordenadas | `pais` |

Hace conversion de tipos, filtro geografico, asignacion de pais, deduplicacion y guardado en `firms_procesado.parquet`.

### Meteorologia

Archivo: `etl/transform/transform_meteo.py`

Calcula:

```text
indice_riesgo =
riesgo_temp * 0.25 +
riesgo_humedad * 0.30 +
riesgo_viento * 0.20 +
riesgo_sequia * 0.25
```

Salidas:

```text
meteo_procesado_todos.parquet
forecast_riesgo.parquet
```

### CAMS

Archivo: `etl/transform/transform_cams.py`

Convierte datos horarios a diarios:

| Crudo horario | Final diario |
|---|---|
| `fecha_hora` | `fecha` |
| `pm10` | `pm10_media`, `pm10_max`, `pm10_p95` |
| `pm2_5` | `pm2_5_media`, `pm2_5_max` |
| `european_aqi` | media y maximo |
| conteo horario | `horas_validas` |
| regla PM10 | `supera_oms_pm10`, `nivel_pm10` |

### CHIRPS

Archivo: `etl/transform/transform_chirps.py`

Transforma `fecha` en `anio`, `mes`, `anio_mes`; valida `precipitacion_mm`; calcula anomalia y deficit hidrico.

### MODIS

Archivo: `etl/transform/transform_modis.py`

Valida `lc_type1`, agrega `lc_descripcion` y `combustibilidad`.

## Load

Ruta:

```text
etl/load/
```

Principal:

```text
etl/load/load_postgres.py
```

Carga:

- `focos_calor`
- `meteo_diario`
- `calidad_aire_diario`
- `precipitacion_mensual`
- `cobertura_vegetal`

Usa claves naturales, `ON CONFLICT`, upsert y auditoria en `etl_ejecuciones`.

Defensa: la carga es idempotente; no duplica datos al repetir el proceso.
