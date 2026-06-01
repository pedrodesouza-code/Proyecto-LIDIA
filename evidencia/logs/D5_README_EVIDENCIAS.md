# D5 - Testing y validacion del sistema consolidado

D5 consolida evidencia cuantitativa del Proyecto LIDIA sobre PostgreSQL,
MongoDB, ETL Python, vistas `dw` y dashboard Streamlit.

## Archivos

- `scripts/d5_generar_evidencia_validacion.py`: orquestador principal para
  Jupyter/UTEC. Ejecuta compilacion, tests, dos corridas smoke consecutivas,
  validaciones SQL, CDC, MongoDB y resumen final.
- `sql/validation/d5_validacion_calidad.sql`: calidad de datos relacional:
  completitud, unicidad, rangos, paises validos, claves foraneas, rechazos e
  INUMET solo Uruguay.
- `sql/validation/d5_validacion_funcional.sql`: consultas analiticas y vistas
  usadas por Streamlit.
- `scripts/d5_validar_mongo_cdc.py`: validacion documental de CDC D4 en
  `pipeline_logs`.
- `evidencia/logs/d5_resumen_ultima_ejecucion.log`: resumen JSON final con
  estados OK/error.

## Que demuestra cada parte

- **Calidad**: conteos principales, nulos criticos, duplicados por
  `natural_key`, coordenadas y paises validos, rangos ambientales y rechazos.
- **Tests automaticos**: resultado de `python -m compileall -q .` y
  `python -m pytest -q tests`.
- **Idempotencia**: dos corridas consecutivas del mismo smoke ETL y comparacion
  de duplicados antes, entre ambas y despues.
- **CDC**: presencia cuantitativa de `alta`, `modificacion` y `sin_cambio` en
  `audit.cdc_eventos`, mas documento D4 en MongoDB si `MONGO_URI` esta definido.
- **Consultas analiticas**: vistas `dw.v_incendios_*`,
  `dw.v_calidad_aire_alta_actividad` y `dw.v_calidad_pipeline`.
- **Dashboard/vistas**: confirma que las vistas consumidas por
  `dashboard/streamlit_app.py` existen y responden.
- **Trazabilidad**: usa `audit.etl_runs`, `audit.cdc_eventos`,
  `staging.rechazos_etl` y `pipeline_logs`.

## Limitaciones

Si `MONGO_URI` no esta definido, la validacion MongoDB queda como limitacion y
el estado CDC documental no puede marcarse OK. Si una vista falta, se reporta
como `FALTA` en vez de inventar resultados.
