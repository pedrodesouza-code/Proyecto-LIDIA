# D4 - Evidencias Change Data Capture

Este criterio demuestra CDC con `natural_key` y `record_hash` usando registros
reales de FIRMS ya cargados en `staging.stg_firms`. La prueba es controlada:
registra eventos en auditoria y MongoDB, pero no modifica `staging.stg_firms`
ni `dw.fact_incendio`.

## Archivos generados

- `scripts/d4_generar_evidencia_cdc.py`: ejecuta la prueba CDC en Python para
  Jupyter/UTEC. Requiere `DATABASE_URL` y `MONGO_URI`.
- `sql/validation/d4_validacion_cdc.sql`: consulta PostgreSQL para verificar
  eventos `alta`, `modificacion`, `sin_cambio`, trazabilidad por `run_id`,
  duplicados por `natural_key` e impacto en auditoria/staging/DW.
- `nosql/d4_validacion_cdc_mongo.js`: validacion equivalente en MongoDB para
  colecciones documentales de CDC, metadata, logs y snapshots.
- `evidencia/logs/d4_cdc_<timestamp>.log`: salida completa de la ejecucion D4.
- `evidencia/logs/d4_resumen_ultima_ejecucion.log`: resumen con ruta del log y
  exit code.

## Interpretacion

- **Carga inicial**: se toma un registro FIRMS real y se registra como
  `tipo_evento = 'alta'`.
- **Carga incremental sin cambios**: se procesa el mismo `natural_key` con el
  mismo `record_hash`, generando `tipo_evento = 'sin_cambio'`.
- **Actualizacion real simulada**: se usa el mismo `natural_key` de un registro
  real, pero con un `record_hash` distinto para representar una correccion del
  origen. Esto genera `tipo_evento = 'modificacion'`.
- **Registro nuevo real**: se toma un segundo registro FIRMS real y se registra
  como nueva `alta`.

## PostgreSQL

La evidencia queda en:

- `audit.etl_runs`: una corrida por fase de la prueba D4.
- `audit.cdc_eventos`: eventos CDC con `run_id`, `fuente`, `record_hash`,
  `tipo_evento`, `timestamp` y detalle con `natural_key`.

## MongoDB

MongoDB se usa como complemento documental, no reemplaza al Data Warehouse.
La evidencia queda en:

- `cdc_eventos`: eventos CDC documentales.
- `ingesta_metadata`: resumen por corrida.
- `pipeline_logs`: logs operativos de D4.
- `snapshots_firms`: snapshot resumido derivado de FIRMS real.

## Limitaciones

Si `staging.stg_firms` tiene menos de dos registros reales, la prueba no puede
demostrar simultaneamente alta nueva y modificacion controlada. En ese caso el
script finaliza con error y deja la limitacion en el log.
