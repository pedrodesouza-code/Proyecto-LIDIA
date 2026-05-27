# ETL

El pipeline acepta exclusivamente `INUMET`, `FIRMS`, `CHIRPS`, `FORECAST`,
`METEO` y `MODIS`. Las rutas de CSV o Parquet se configuran en
`config/.env`; los datos no se versionan.

```bash
cd implementation
python -m etl.main --source FIRMS
python -m etl.main --source ALL
```

Cada lote valida país, campos críticos, fechas y rangos. Las filas inválidas se
persisten en `staging.rechazos_etl`. `natural_key` identifica la observación y
`record_hash` permite registrar `alta`, `modificacion` o `sin_cambio` en
`audit.cdc_eventos`; la ejecución resume conteos en `audit.etl_runs`.

`INUMET` rechaza registros fuera de Uruguay. `brillo_termico` de FIRMS se
conserva como medición satelital y no se utiliza como temperatura del aire.
