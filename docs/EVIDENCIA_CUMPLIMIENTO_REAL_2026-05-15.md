# Evidencia de cumplimiento real - 2026-05-15

Este documento registra verificaciones ejecutadas sobre el entorno local real del proyecto SINIA-UY.

## Bases de datos reales

Comando:

```bash
python scripts/verificar_bases_locales.py
```

Resultado verificado:

- PostgreSQL `sinia_uy` conectado.
- 8 tablas.
- 9 vistas.
- 11 puntos de monitoreo.
- MongoDB `sinia_uy` conectado.
- Colecciones: `alertas`, `ejecuciones_etl`, `focos_snapshots`, `focos_resumen_pais`, `focos_resumen_mes`.

## Limpieza de alcance

Comando:

```bash
python scripts/limpiar_alcance_real.py
```

Evidencia:

- Reporte: `reports/limpieza_alcance_ultimo.json`
- Alcance final: `URY`, `BRA`, `ARG`.
- PostgreSQL:
  - `paises_referencia`: 3.
  - `puntos_monitoreo`: 11.
  - `focos_calor`: 10.343.582.
  - Distribucion final de focos: ARG, BRA, URY.
- MongoDB:
  - `focos_snapshots`: 2.520.
  - Distribucion final de focos embebidos: ARG, BRA, URY.

## Calidad, CDC e idempotencia

Comando:

```bash
python tests/test_calidad_datos.py
```

Resultado:

- 17 PASS.
- 0 FAIL.
- Reporte: `tests/resultados_tests.json`.

Incluye pruebas de completitud, unicidad, consistencia, validez, idempotencia y CDC.

## Optimizacion SQL

DDL aplicado:

```bash
sql/ddl/07_optimizacion_materializada.sql
```

Resultado:

- `mv_focos_por_pais`: 3 filas materializadas.
- `mv_focos_por_pais_mes`: 255 filas materializadas.
- Consultas frecuentes de focos dejan de agrupar 10,3M filas en tiempo de dashboard.

## Optimizacion MongoDB

Comando:

```bash
python scripts/optimizar_mongo_resumenes.py
```

Resultado:

- `focos_resumen_pais`: 3 documentos.
- `focos_resumen_mes`: 179 documentos.
- Reporte: `reports/mongo_resumenes_ultimo.json`.

## Comparacion SQL vs NoSQL real

Comando:

```bash
python scripts/comparar_sql_nosql_real.py
```

Evidencia:

- Reporte: `reports/sql_vs_nosql_real_ultimo.json`.
- PostgreSQL materializado:
  - focos por pais: ~59,662 ms promedio.
  - focos por mes: ~4,634 ms promedio.
  - ejecuciones ETL: ~12,835 ms promedio.
  - riesgo por pais: ~53,626 ms promedio.
- MongoDB materializado:
  - focos por pais: ~2,168 ms promedio.
  - focos por mes: ~2,477 ms promedio.
  - ejecuciones ETL: ~1,981 ms promedio.

Las consultas operativas materializadas quedan bajo el SLA de 3000 ms.

## Backup real

Comando:

```bash
python scripts/backup_restore_real.py backup
```

Evidencia:

- Reporte: `reports/backup_restore_ultimo.json`.
- PostgreSQL respaldado con `pg_dump`.
- MongoDB respaldado con exportacion JSONL gzip mediante `pymongo`.
- Configuracion respaldada con secretos enmascarados.

Ultimo backup real posterior a limpieza:

- `backups/real_20260515_150720/`

## Dashboard real

Comando:

```bash
python -m streamlit run dashboard/app.py --server.port 8501 --server.headless true
```

Resultado:

- HTTP 200 en `http://localhost:8501`.
- Verificado en navegador integrado.
- Dashboard muestra:
  - `SINIA-UY`.
  - `3 paises · 11 puntos · 2018-2025`.
  - Conexion a PostgreSQL.
  - Secciones: resumen, focos, riesgo, calidad del aire, comparativo, tiempo real y fuentes.

## Docker

Comando validado:

```bash
docker compose config
```

Resultado:

- Compose renderiza correctamente los servicios `postgres`, `mongo` y `streamlit`.

Bloqueo del host:

- `docker compose ps` y `docker version` no pueden conectar al engine.
- `com.docker.service` esta detenido.
- `wsl -l -v` devuelve `Wsl/0x80070422`.
- `sc.exe start com.docker.service` devuelve `Access denied`.

Conclusion:

- La configuracion Docker del proyecto es valida.
- La ejecucion Docker queda bloqueada por permisos/servicios del host Windows, no por archivos del repositorio.
- El sistema fue verificado funcionalmente por la ruta local real: PostgreSQL, MongoDB, Streamlit, tests, rendimiento, backup y optimizacion.
