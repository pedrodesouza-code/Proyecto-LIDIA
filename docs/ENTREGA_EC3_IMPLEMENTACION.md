# Entrega EC3 - Implementacion funcional

Fecha de cierre operativo: 2026-05-15.

Objetivo de EC3: demostrar que SINIA-UY funciona con datos reales, ETL modular,
persistencia SQL/NoSQL, CDC, testing de datos, seguridad, dashboard, despliegue
hibrido y mediciones preliminares de rendimiento.

## Resumen ejecutivo

El sistema esta implementado y ejecutable. La evidencia principal esta versionada
en codigo, reportes JSON y documentacion tecnica:

- Tests de datos: `17 PASS / 0 FAIL` en `tests/resultados_tests.json`.
- PostgreSQL UTEC: `1.841.820` focos reales, alcance `ARG/BRA/URY`.
- MongoDB UTEC: `352` snapshots reales, todos con `pais` embebido.
- Dashboard Streamlit: responde en `http://localhost:8501`.
- Docker Compose: configuracion validada con `docker compose config --quiet`.
- GitHub remoto: rama `codex-flujo-local-utec` actualizada.

## 1. Modelo relacional SQL

| Exigencia | Implementacion | Evidencia |
|---|---|---|
| Script DDL completo | DDL separado por roles, schema, indices y vistas | `sql/ddl/01_roles.sql` a `sql/ddl/04_vistas.sql`, `sql/ddl/07_optimizacion_materializada.sql` |
| Integridad referencial | FK entre hechos y dimensiones/puntos | `sql/ddl/02_schema.sql` |
| Restricciones | `CHECK`, `NOT NULL`, claves naturales y unicidad | `sql/ddl/02_schema.sql` |
| Indices | Indices por fecha, pais, punto, fuente y ejecucion | `sql/ddl/03_indices.sql` |
| Carga real ETL | Loaders Python con upsert/idempotencia | `etl/load/load_postgres.py` |
| Validacion post-carga | Verificacion UTEC y tests | `reports/utec_verificacion_ultimo.json`, `tests/resultados_tests.json` |

Evidencia UTEC final:

| Control | Resultado |
|---|---:|
| `focos_calor` | `1.841.820` |
| rango focos | `2024-01-01` a `2026-05-15` |
| focos ultimos 7 dias | `5.283` |
| paises | `ARG`, `BRA`, `URY` |
| `mv_focos_por_pais` | `3` |
| `mv_focos_por_pais_mes` | `39` |

## 2. Modelo NoSQL

| Exigencia | Implementacion | Evidencia |
|---|---|---|
| Estructura coherente | Colecciones para auditoria, alertas y snapshots | `nosql/schemas/`, `docs/ANEXO_B_JSON_SCHEMA_MONGODB.md` |
| Datos reales | Snapshots FIRMS historicos y NRT | `reports/utec_sync_ultimo.json` |
| Caso de uso operativo | Documentos autocontenidos para consulta diaria, logs y alertas | `etl/load/load_mongo.py` |
| Consultas representativas | Queries NoSQL y resumenes materializados | `nosql/queries/01_consultas.js`, `scripts/optimizar_mongo_resumenes.py` |

Evidencia MongoDB UTEC final:

| Control | Resultado |
|---|---:|
| `focos_snapshots` | `352` |
| snapshots con `pais` | `352` |
| snapshots sin `pais` | `0` |
| `focos_resumen_pais` | `3` |
| `focos_resumen_mes` | `39` |
| `ejecuciones_etl` | `3` |

## 3. ETL estructurado en Python

| Exigencia | Implementacion | Evidencia |
|---|---|---|
| Codigo modular | Extract, transform, load y scheduler separados | `etl/extract/`, `etl/transform/`, `etl/load/`, `etl/scheduler.py` |
| Separacion de etapas | Directorios y scripts por etapa | `etl/` |
| Manejo formal de errores | Try/except, registro de errores y estados ETL | `etl/load/load_postgres.py`, `etl/load/load_mongo.py` |
| Logging estructurado | Logger JSON con `etl_stage`, `source`, filas y estado | `etl/utils/logger.py`, `logs/sinia_2026-05-15.json` |
| Configuracion externa | Variables por `.env` | `config/settings.py`, `config/utec.env.example`, `docker/.env.example` |
| Automatizacion reproducible | Scheduler y scripts de setup/sync | `etl/scheduler.py`, `scripts/crear_bases_datos.py`, `scripts/sincronizar_utec_real.py` |

## 4. CDC funcional

| Exigencia | Implementacion | Evidencia |
|---|---|---|
| Carga inicial completa | Parquets procesados y carga a motores | `data/processed/`, `etl/load/` |
| Carga incremental | Watermark por fecha y upsert | `etl/scheduler.py` |
| Insercion nueva | Test `cdc_detecta_nuevos` | `tests/test_calidad_datos.py`, `tests/resultados_tests.json` |
| Modificacion existente | Test `cdc_detecta_modificacion` | `tests/test_calidad_datos.py`, `tests/resultados_tests.json` |
| Comparacion de impacto | Metricas insertados/actualizados/sin cambio | `etl_ejecuciones`, `ejecuciones_etl`, logs JSON |

Resultado de testing CDC: ambos casos quedan en `PASS`.

## 5. Testing y validacion

Suite principal: `tests/test_calidad_datos.py`.

| Tipo de prueba | Tests cubiertos | Evidencia |
|---|---|---|
| Calidad de datos | Completitud, unicidad, consistencia, validez | `tests/resultados_tests.json` |
| Idempotencia | Doble carga FIRMS y meteo sin duplicados logicos | `tests/resultados_tests.json` |
| CDC | Insercion nueva y modificacion de registro existente | `tests/resultados_tests.json` |
| Validacion funcional | SQL/NoSQL, dashboard y correspondencia preguntas-consultas | `docs/CORRESPONDENCIA_PREGUNTAS_CONSULTAS_DASHBOARD.md` |
| Trazabilidad | Logs y registros estructurados | `logs/sinia_2026-05-15.json`, `tests/resultados_tests.json` |

Resultado final:

```text
17 passed
```

## 6. Seguridad, backup y gobernanza

| Exigencia | Implementacion | Evidencia |
|---|---|---|
| Roles diferenciados | Admin, ETL/escritura y lectura | `sql/ddl/01_roles.sql` |
| Privilegios minimos | Grants acotados por rol y vistas | `sql/ddl/01_roles.sql`, `sql/ddl/04_vistas.sql` |
| Restriccion de tablas sensibles | Dashboard consume vistas y variables externas | `sql/ddl/04_vistas.sql`, `dashboard/db.py` |
| Variables de entorno | Credenciales fuera del codigo | `config/settings.py`, `.env.example` |
| No exposicion de credenciales | Repo sin claves reales versionadas | busqueda `rg` sin resultados sensibles |
| Backup/restore | Scripts y backup real ejecutado | `backups/backup.sh`, `backups/restore.sh`, `reports/backup_restore_ultimo.json` |
| Gobernanza y etica | Sesgos, limitaciones y uso responsable | `docs/SEGURIDAD_BACKUP_GOBERNANZA.md` |

## 7. Capa analitica Streamlit

Dashboard: `dashboard/app.py`.

Cumplimientos:

- Mas de 7 metricas clave: focos, paises, puntos, FRP, riesgo, PM10, NRT, forecast, cobertura.
- Mas de 2 agregaciones temporales: series por fecha, mes, forecast diario y NRT.
- Mas de 2 comparaciones: paises, periodos, riesgo vs focos, calidad del aire vs riesgo.
- Conexion directa a PostgreSQL con fallback controlado a Parquet.
- Correspondencia con preguntas analiticas documentada en `docs/CORRESPONDENCIA_PREGUNTAS_CONSULTAS_DASHBOARD.md`.

Validacion local:

```bash
python -m streamlit run dashboard/app.py --server.port 8501 --server.headless true
```

Resultado verificado: HTTP `200` en `http://localhost:8501`.

## 8. Despliegue hibrido y Docker

| Exigencia | Implementacion | Evidencia |
|---|---|---|
| Infraestructura in situ | PostgreSQL y MongoDB en servidor institucional UTEC | `reports/utec_verificacion_ultimo.json` |
| Componente remoto/cloud | Repositorio GitHub remoto y dashboard preparado para ejecucion remota | rama `codex-flujo-local-utec`, `docs/DESPLIEGUE_HIBRIDO.md` |
| Distribucion documentada | Componentes y justificacion | `docs/DESPLIEGUE_HIBRIDO.md` |
| Conectividad integrada | Verificacion real UTEC SQL/NoSQL | `scripts/verificar_utec.py`, `reports/utec_verificacion_ultimo.json` |
| Docker | Compose con PostgreSQL, MongoDB y Streamlit | `docker/docker-compose.yml`, `docker/Dockerfile.streamlit` |

Validacion Docker:

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env.example config --quiet
```

Resultado: configuracion valida. La ejecucion de contenedores en este host Windows
queda bloqueada por `WSLService` y `com.docker.service` deshabilitados, documentado
en `docs/EVIDENCIA_CUMPLIMIENTO_REAL_2026-05-15.md`.

## 9. Rendimiento preliminar

| Exigencia | Implementacion | Evidencia |
|---|---|---|
| Tiempo pipeline/lecturas | Medicion reproducible sobre datasets procesados | `scripts/medir_rendimiento.py`, `reports/rendimiento_ultimo.json` |
| Consultas analiticas | Comparacion SQL vs NoSQL real | `scripts/comparar_sql_nosql_real.py`, `reports/sql_vs_nosql_real_ultimo.json` |
| Impacto de indices | Uso de indices y materializadas | `sql/ddl/03_indices.sql`, `sql/ddl/07_optimizacion_materializada.sql` |
| Completa vs incremental | NRT y scheduler por watermark | `etl/scheduler.py`, `reports/utec_sync_ultimo.json` |

SLA documentado en `docs/SLA_Y_RENDIMIENTO.md`.

## Comandos de demo EC3

Ejecutar en este orden para defensa:

```bash
python -m pytest tests -q
python scripts/verificar_utec.py
python scripts/medir_rendimiento.py
docker compose -f docker/docker-compose.yml --env-file docker/.env.example config --quiet
python -m streamlit run dashboard/app.py --server.port 8501 --server.headless true
```

Mostrar luego:

- `tests/resultados_tests.json`.
- `reports/utec_verificacion_ultimo.json`.
- `reports/utec_sync_ultimo.json`.
- `reports/rendimiento_ultimo.json`.
- Dashboard en `http://localhost:8501`.

## Frase corta para defensa

EC3 queda cubierto porque el sistema no solo esta disenado: ejecuta ETL modular
con datos reales, carga PostgreSQL y MongoDB, aplica CDC e idempotencia, registra
tests cuantitativos, muestra resultados en Streamlit, mide rendimiento, respeta
seguridad por roles/configuracion externa y tiene evidencia de despliegue hibrido
con UTEC.
