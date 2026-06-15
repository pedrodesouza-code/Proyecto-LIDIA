# Resumen de cierre de evidencias finales

Fecha de generación: 2026-06-15

## Evidencias generadas o actualizadas

| Evidencia | Archivo/log | Estado | Observación |
| --- | --- | --- | --- |
| Validación sintáctica Python | `evidencia/logs/compileall_final.log` | OK | `python3 -m compileall -q .` finalizó correctamente. |
| Tests automáticos | `evidencia/logs/pytest_final.log` | OK | En Jupyter: `43 passed`. |
| Refresh materialized views | `evidencia/logs/refresh_materialized_views_final.log` | OK | En Jupyter: `dw.mv_dashboard_focos_pais_periodo` refrescó en 10.1236 s y `dw.mv_dashboard_incendios_precipitacion` en 8.7859 s; duración total 18.9237 s. |
| Humedad por rangos | `evidencia/logs/humedad_focos_rangos_final.log` | OK | En Jupyter: baja humedad 830 focos, humedad media 6.192 focos, alta humedad 540 focos y sin dato 39 focos. |
| MongoDB evidencia final | `evidencia/logs/mongodb_evidencia_final.log` | OK | En Jupyter: colecciones complementarias con documentos reales; `raw_payloads` 262.836, `pipeline_logs` 934, `rechazos_etl` 5.003, `ingesta_metadata` 21, `snapshots_firms` 3 y `cdc_eventos` 4. |
| CDC smoke incremental | `evidencia/logs/cdc_smoke_incremental_final.log` | OK | En Jupyter: `audit.cdc_eventos` contiene altas, modificaciones y sin cambios; `dw.fact_incendio` 2.774.831 y duplicados por `natural_key` = 0. |
| Carga completa histórica con tiempo total | `evidencia/logs/carga_completa_oficial_tiempo.log` | PARCIAL | En Jupyter se registraron conteos iniciales reales, pero la ejecución fue interrumpida controladamente por ventana interactiva agotada. No se declara tiempo total inventado. |
| Backup PostgreSQL | `evidencia/logs/backup_postgres_final.log` | OK | En Jupyter se generó `backups/proyecto_lidia.dump` mediante `pg_dump`. Restore documentado, no ejecutado. |
| Backup MongoDB | `evidencia/logs/backup_mongodb_final.log` | PARCIAL | En Jupyter no se pudo generar dump documental porque `mongodump` no está instalado. |
| Sharding MongoDB local | `evidencia/logs/mongodb_sharding_final.log` | NO APLICA en Jupyter | El entorno Jupyter no tiene `docker-compose.sharding.yml`; sharding queda como evidencia local académica cuando Docker esté disponible. |

## Documento corregido

Archivo editable corregido:

- `/home/pepo/Descargas/Entregable Final.docx`

Backup creado:

- `/home/pepo/Descargas/Entregable Final_backup_codex_cierre_20260615_155240.docx`
- `/home/pepo/Descargas/Entregable Final_backup_codex_jupyter_evidencias_20260615_181531.docx`

Correcciones aplicadas:

- Título del Anexo H corregido a `Anexo H. Capturas`.
- `Tabla 4 bis. Caracterización técnica complementaria de fuentes` convertida a tabla DOCX real.
- Filas 8, 9 y 10 de `Tabla E1` convertidas desde texto con pipes a filas de tabla DOCX real.
- Texto de replicación productiva en `Tabla G1` reemplazado por una limitación explícita, sin declarar evidencia operativa inexistente.
- Anexos D, E, F y G ajustados con evidencia real ejecutada en Jupyter cuando estuvo disponible.
- La carga completa histórica quedó marcada como parcial porque no finalizó en la ventana interactiva; no se inventó duración total.
- MongoDB quedó documentado como capa complementaria con colecciones y conteos reales.
- Backup PostgreSQL quedó documentado con dump real generado; backup MongoDB queda limitado por ausencia de `mongodump`.

## Scripts creados

| Script | Propósito | Comando |
| --- | --- | --- |
| `scripts/evidencia_refresh_materialized_views.py` | Refrescar y medir `dw.mv_dashboard_focos_pais_periodo` y `dw.mv_dashboard_incendios_precipitacion`. | `python3 scripts/evidencia_refresh_materialized_views.py` |
| `scripts/evidencia_humedad_focos_rangos.py` | Consultar focos de Uruguay por rangos de humedad relativa. | `python3 scripts/evidencia_humedad_focos_rangos.py` |
| `scripts/evidencia_mongodb_final.py` | Listar colecciones MongoDB, conteos, muestras y consultas representativas. | `python3 scripts/evidencia_mongodb_final.py` |
| `scripts/evidencia_cdc_smoke_incremental.py` | Resumir evidencia CDC no destructiva desde `audit.cdc_eventos`. | `python3 scripts/evidencia_cdc_smoke_incremental.py` |
| `scripts/evidencia_carga_completa_tiempo.py` | Medir carga completa oficial del ETL y conteos antes/después. | `python3 scripts/evidencia_carga_completa_tiempo.py` |
| `scripts/backup_postgres_final.sh` | Generar `backups/proyecto_lidia.dump` con `pg_dump`. | `bash scripts/backup_postgres_final.sh` |
| `scripts/backup_mongodb_final.sh` | Generar `backups/mongo_lidia/` con `mongodump`. | `bash scripts/backup_mongodb_final.sh` |
| `scripts/evidencia_mongodb_sharding.sh` | Evidencia local académica de sharding si Docker está disponible. | `bash scripts/evidencia_mongodb_sharding.sh` |

## Pendientes reales

- Completar una carga histórica cronometrada de punta a punta solo en una ventana con tiempo suficiente; la ejecución de cierre en Jupyter fue interrumpida controladamente y no se declara duración total.
- Instalar `mongodump` o usar un contenedor Mongo con herramientas administrativas para generar backup documental.
- Ejecutar evidencia de sharding en entorno local con Docker disponible; no corresponde declararla como operativa en Jupyter.

## Comandos recomendados en Jupyter/UTEC

```bash
cd /app/Proyecto-LIDIA
PYTHONPATH=. python3 scripts/evidencia_refresh_materialized_views.py
PYTHONPATH=. python3 scripts/evidencia_humedad_focos_rangos.py
PYTHONPATH=. python3 scripts/evidencia_cdc_smoke_incremental.py
PYTHONPATH=. python3 scripts/evidencia_mongodb_final.py
PYTHONPATH=. python3 -m compileall -q .
PYTHONPATH=. python3 -m pytest -q tests
```

Para carga completa histórica, ejecutar solo cuando el entorno tenga tiempo/recursos suficientes:

```bash
cd /app/Proyecto-LIDIA
PYTHONPATH=. python3 scripts/evidencia_carga_completa_tiempo.py
```

## Comandos recomendados en local Docker

```bash
cd "/home/pepo/Datos completos/Proyecto-LIDIA-ec3-pedro"
docker compose --env-file .env.docker.example up -d postgres mongo
python3 scripts/evidencia_refresh_materialized_views.py
python3 scripts/evidencia_humedad_focos_rangos.py
python3 scripts/evidencia_cdc_smoke_incremental.py
python3 scripts/evidencia_mongodb_final.py
bash scripts/backup_postgres_final.sh
bash scripts/backup_mongodb_final.sh
```

Sharding local académico, solo si Docker está disponible:

```bash
bash scripts/evidencia_mongodb_sharding.sh
```
