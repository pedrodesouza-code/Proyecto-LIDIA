# Evidencias D3 - ETL Python

Este directorio conserva evidencia para el criterio D3 de la rubrica EC3:
modularidad y reproducibilidad del ETL Python del Proyecto LIDIA.

## Archivos generados

- `d3_estructura_etl_<timestamp>.log`: lista carpetas y archivos del modulo
  `etl/`, muestra el comando de pipeline usado y la ayuda de `etl/main.py`.
- `d3_compile_tests_<timestamp>.log`: salida de `python -m compileall -q .` y
  `python -m pytest -q tests` cuando existe la carpeta `tests`.
- `d3_pipeline_<timestamp>.log`: stdout/stderr de la ejecucion del pipeline con
  un unico comando. Por defecto usa una corrida smoke acotada para evidencia:
  `python -u etl/main.py --smoke --start-date 2025-01-01 --end-date 2025-01-07 --countries URY --max-records-per-source 1000 --skip-mongo`.
- `d3_validacion_etl_<timestamp>.log`: salida de
  `sql/validation/d3_validacion_etl.sql`, con auditoria, metadata, conteos,
  rechazos, natural keys, hashes, duplicados y trazabilidad.
- `d3_resumen_ultima_ejecucion.log`: rutas de los logs de la ultima corrida y
  comando usado.

## Que demuestra cada parte

- **Modularidad**: `d3_estructura_etl_*` muestra `etl/extract`, `etl/transform`,
  `etl/load`, `etl/main.py` y los extractores por fuente.
- **Configuracion externa**: el log indica uso de variables de entorno y
  ejemplos `.env`, sin imprimir secretos ni contenido de `.env`.
- **Ejecucion con un unico comando**: `d3_pipeline_*` registra el comando
  ejecutado. Puede ajustarse con `D3_ETL_COMMAND`.
- **Logging**: el pipeline y el script guardan stdout/stderr en archivos con
  timestamp dentro de `evidencia/logs`.
- **Manejo de errores**: los rechazos quedan evidenciados en
  `staging.rechazos_etl` y resumidos por fuente/motivo en la validacion SQL.
- **Trazabilidad**: `audit.etl_runs`, `staging.ingesta_metadata`, `natural_key`,
  `record_hash` y la columna `fuente` permiten seguir corridas y registros.
- **Idempotencia**: la validacion SQL reporta duplicados por `natural_key` y
  presencia de `record_hash`; los tests automatizados cubren corridas
  repetidas a nivel de normalizacion.

## Ejecucion

Desde la raiz del proyecto en Jupyter/UTEC, usar la version Python:

```bash
export DATABASE_URL='postgresql://<oculto>
python scripts/d3_generar_evidencia_etl.py
```

Si se necesita ejecutar una fuente puntual, definir el comando explicitamente:

```bash
export D3_ETL_COMMAND='python -u etl/main.py --smoke --source FIRMS --start-date 2025-01-01 --end-date 2025-01-07 --countries URY --max-records-per-source 1000 --skip-mongo'
python scripts/d3_generar_evidencia_etl.py
```

Si MongoDB documental esta activo, configurar `MONGO_URI`; el script solo
verifica que exista cuando `MONGO_ENABLED` esta activo.

La variante `.sh` queda solo para entornos Linux con bash. En Jupyter se debe
usar `scripts/d3_generar_evidencia_etl.py`.

## Limitaciones

Si alguna tabla de auditoria no existe o no tiene datos, el SQL lo reporta como
limitacion. No se inventan corridas, rechazos ni documentos para satisfacer la
rubrica.

Si el pipeline queda con exit code `-9`, `9` o `137`, la evidencia debe
interpretarse como limitacion por recursos del entorno. La recomendacion es
mantener `--smoke`, reducir `--max-records-per-source` y acotar fechas/paises.
