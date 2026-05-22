# Guia separada del modelo ER y tablas

Este archivo explica el modelo relacional para defensa de base de datos.

## ER mental

```text
paises_referencia
  -> puntos_monitoreo
       -> meteo_diario
       -> calidad_aire_diario
       -> precipitacion_mensual
       -> cobertura_vegetal

focos_calor usa pais, fecha y coordenadas.
etl_ejecuciones audita el pipeline.
```

## puntos_monitoreo

Rol: dimension geografica.

| Campo | Tipo | Motivo |
|---|---|---|
| `id` | `SERIAL PK` | Clave interna |
| `nombre` | `VARCHAR(50)` | Nombre del punto |
| `pais` | `CHAR(3)` | Codigo ISO |
| `region` | `VARCHAR(80)` | Descripcion opcional |
| `latitud` | `NUMERIC(9,6)` | Coordenada precisa |
| `longitud` | `NUMERIC(9,6)` | Coordenada precisa |
| `activo` | `BOOLEAN` | Desactivar sin borrar |
| `creado_en` | `TIMESTAMP` | Auditoria |

## focos_calor

Rol: hechos satelitales FIRMS.

Clave natural:

```text
latitud + longitud + fecha_adq + hora_adq_hhmm + satelite
```

| Crudo | Final | Tipo final |
|---|---|---|
| `latitude` | `latitud` | `NUMERIC(8,5)` |
| `longitude` | `longitud` | `NUMERIC(8,5)` |
| `acq_date` | `fecha_adq` | `DATE` |
| `acq_time` | `hora_adq_hhmm` | `INTEGER` |
| `frp` | `potencia_radiativa` | `NUMERIC(10,3)` |
| `confidence` | `confianza_raw` | `VARCHAR(5)` |
| `confidence` | `confianza_num` | `SMALLINT` |
| `satellite` | `satelite` | `VARCHAR(20)` |
| `instrument` | `instrumento` | `VARCHAR(20)` |
| `daynight` | `dia_noche` | `CHAR(1)` |
| `daynight` | `es_diurno` | `BOOLEAN` |
| `bright_ti4` | `brillo_ti4` | `NUMERIC(8,3)` |
| `bright_ti5` | `brillo_ti5` | `NUMERIC(8,3)` |
| coordenadas | `pais` | `CHAR(3)` |

## meteo_diario

Rol: hechos meteorologicos diarios y riesgo.

Clave natural:

```text
fecha + id_punto + tipo_dato
```

| Crudo | Final | Tipo final |
|---|---|---|
| `fecha` | `fecha` | `DATE` |
| `punto` | `id_punto` | `INTEGER FK` |
| `temperature_2m_max` | igual | `NUMERIC(5,2)` |
| `temperature_2m_min` | igual | `NUMERIC(5,2)` |
| `relative_humidity_2m_max` | igual | `NUMERIC(5,2)` |
| `relative_humidity_2m_min` | igual | `NUMERIC(5,2)` |
| `wind_speed_10m_max` | igual | `NUMERIC(6,2)` |
| `wind_gusts_10m_max` | igual | `NUMERIC(6,2)` |
| `precipitation_sum` | igual | `NUMERIC(7,2)` |
| `et0_fao_evapotranspiration` | igual | `NUMERIC(6,3)` |

Calculados: `riesgo_temp`, `riesgo_humedad`, `riesgo_viento`, `riesgo_sequia`, `indice_riesgo`, `nivel_riesgo`.

## calidad_aire_diario

Rol: hechos diarios de calidad del aire.

Clave natural:

```text
fecha + id_punto
```

| Crudo horario | Final diario | Tipo final |
|---|---|---|
| `fecha_hora` | `fecha` | `DATE` |
| `punto` | `id_punto` | `INTEGER FK` |
| `pm10` | `pm10_media` | `NUMERIC(8,3)` |
| `pm10` | `pm10_max` | `NUMERIC(8,3)` |
| `pm10` | `pm10_p95` | `NUMERIC(8,3)` |
| `pm2_5` | `pm2_5_media` | `NUMERIC(8,3)` |
| `pm2_5` | `pm2_5_max` | `NUMERIC(8,3)` |
| `european_aqi` | `european_aqi_media` | `NUMERIC(6,2)` |
| `european_aqi` | `european_aqi_max` | `NUMERIC(6,2)` |
| conteo | `horas_validas` | `SMALLINT` |
| regla PM10 | `supera_oms_pm10` | `BOOLEAN` |
| regla PM10 | `nivel_pm10` | `VARCHAR(10)` |

## precipitacion_mensual

Rol: hechos mensuales CHIRPS.

Clave natural:

```text
anio + mes + id_punto
```

## cobertura_vegetal

Rol: hechos anuales MODIS.

Clave natural:

```text
anio + id_punto
```

## etl_ejecuciones

Rol: auditoria. Registra fuente, etapa, tipo de carga, procesados, insertados, actualizados, sin cambio, estado y duracion.
