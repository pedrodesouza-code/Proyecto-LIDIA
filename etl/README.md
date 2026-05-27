# ETL

El pipeline acepta exclusivamente `INUMET`, `FIRMS`, `CHIRPS`, `FORECAST`,
`METEO` y `MODIS`. FIRMS, CHIRPS y una exportacion MODIS pueden configurarse
como archivos reales locales; METEO y FORECAST se obtienen mediante API.
Los datos no se versionan.

```bash
python -m etl.main --source FIRMS
python -m etl.main --source ALL
```

Cada lote valida país, campos críticos, fechas y rangos. Las filas inválidas se
persisten en `staging.rechazos_etl`. `natural_key` identifica la observación y
`record_hash` permite registrar `alta`, `modificacion` o `sin_cambio` en
`audit.cdc_eventos`; la ejecución resume conteos en `audit.etl_runs`.

`INUMET` rechaza registros fuera de Uruguay. `brillo_termico` de FIRMS se
conserva como medición satelital y no se utiliza como temperatura del aire.

## Carga Real Integrada

La carga real integra archivos y APIs disponibles:

```bash
python -m etl.load.real_integrated
```

`FIRMS_FILE` y `CHIRPS_FILE` se configuran con rutas relativas a la raiz del
proyecto. `FIRMS_COUNTRY_BOUNDARIES_FILE` apunta a una geometria auxiliar
local de limites nacionales, utilizada unicamente para asignar
`pais_codigo` a los puntos FIRMS. El cargador acepta solo `URY`, `ARG` y
`BRA`, registra de forma agregada los puntos fuera de alcance y carga
`brightness` como `brillo_termico`.

CHIRPS conserva sus coordenadas de punto para construir
`dw.dim_precipitacion`; la vinculacion a focos usa el punto mas cercano del
mismo pais y mes dentro del umbral configurado. Los registros fuera del alcance
se persisten como rechazos.

`METEO` consume datos historicos horarios 2018-2025 desde su API; `FORECAST`
consume el horizonte meteorologico operativo y queda identificado como tal en
`staging.stg_meteo`. `MODIS` se carga desde una exportacion anual real
configurada en `MODIS_FILE`. `INUMET` une los CSV horarios reales configurados
en `INUMET_TEMPERATURA_FILE` e `INUMET_HUMEDAD_FILE`, y siempre se restringe
a Uruguay.

Finalizada la ingesta, `associate_environmental_dimensions()` vincula cada
foco FIRMS con el vecino ambiental mas cercano dentro del mismo pais mediante
distancia Haversine. La regla temporal es misma fecha para clima (hora mas
cercana al horario FIRMS), mismo anio/mes para CHIRPS y mismo anio para MODIS.
Los umbrales quedan explicitados en `SPATIAL_THRESHOLDS_KM`: 100 km para
`METEO`, `FORECAST`, `CHIRPS` y `MODIS`, y 150 km para `INUMET`. Si no existe
candidato dentro de la regla, la clave foranea permanece nula.
