# Matriz de cumplimiento contra consigna 2026

Revision operativa actualizada: **2026-05-20**.

Fuente de verdad del estado actual: `docs/ESTADO_ACTUAL_PROYECTO_2026-05-20.md`.

## Estado ejecutivo

El proyecto queda registrado como cumplido en los puntos centrales de la consigna: dominio, fuentes reales, ETL, persistencia SQL/NoSQL, calidad de datos, idempotencia, CDC, dashboard, rendimiento, SLA, sharding simulado, seguridad, backup, despliegue hibrido, replicacion documentada e informe/defensa.

Alcance vigente:

- `4` paises: `URY`, `BRA`, `ARG`, `CHL`.
- `36` puntos de monitoreo.
- Uruguay completo con `19` departamentos.
- Tests actuales: `20 PASS / 0 FAIL`.

## Requisitos transversales

| Requisito de la consigna | Estado | Evidencia actual | Nota de defensa |
|---|---:|---|---|
| Problema real con datos abiertos | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md`, `docs/FUENTES_Y_DATOS.md` | Riesgo de incendios y condiciones ambientales regionales. |
| Arquitectura multicapa | Cumplido | `README.md`, `docs/ARQUITECTURA.md`, `docs/figures/` | Fuentes -> ETL -> SQL/NoSQL -> dashboard. |
| Persistencia poliglota SQL + NoSQL | Cumplido | `sql/`, `nosql/`, `etl/load/` | PostgreSQL analitico, MongoDB operacional. |
| Python para ETL | Cumplido | `etl/extract/`, `etl/transform/`, `etl/load/`, `etl/scheduler.py` | Pipeline modular y reproducible. |
| Idempotencia del pipeline | Cumplido | `tests/test_calidad_datos.py`, `tests/resultados_tests.json` | Mostrar reporte con 20 tests. |
| CDC / carga incremental | Cumplido | `etl/scheduler.py`, tests CDC | Detecta nuevos y modificados. |
| Calidad de datos cuantitativa | Cumplido | `tests/test_calidad_datos.py` | Completitud, unicidad, consistencia, validez. |
| Dashboard Streamlit | Cumplido | `dashboard/app.py`, `dashboard/db.py` | Tiene fallback a Parquet. |
| Docker | Cumplido | `docker/docker-compose.yml`, `docker/Dockerfile.streamlit` | `docker compose config --quiet` valida la configuracion. |
| Replicacion en ambos motores | Cumplido en diseno | `docs/REPLICACION_Y_SHARDING.md` | Arquitectura documentada; ejecucion real depende de infraestructura. |
| Sharding o simulacion de alto volumen | Cumplido | `scripts/simular_sharding.py`, `reports/sharding_simulado_ultimo.json` | Simulacion reproducible, no sharding fisico. |
| Despliegue hibrido | Cumplido | `docs/DESPLIEGUE_HIBRIDO.md`, `scripts/deploy.sh` | UTEC historico + dashboard local/cloud. |
| Rendimiento medido | Cumplido | `reports/rendimiento_ultimo.json`, `reports/sql_vs_nosql_real_ultimo.json` | SQL/Mongo materializado bajo SLA. |
| SLA definido y evaluado | Cumplido | `docs/SLA_Y_RENDIMIENTO.md` | SLA interactivo 3000 ms. |
| Seguridad: roles, permisos, vistas | Cumplido | `sql/ddl/01_roles.sql`, `sql/ddl/04_vistas.sql`, `.env.example` | Credenciales fuera del repo. |
| Backup y recuperacion | Cumplido | `reports/backup_restore_ultimo.json`, `backups/backup.sh`, `backups/restore.sh` | Backup real registrado. |
| Gobernanza y etica del dato | Cumplido | `docs/SEGURIDAD_BACKUP_GOBERNANZA.md` | Limitaciones de sensores y uso responsable. |

## EC1 - Definicion del problema y analisis inicial

| Requisito EC1 | Estado | Evidencia actual |
|---|---:|---|
| Introduccion al dominio | Cumplido | `docs/INFORME_EC1.md`, `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Contexto, actores, variables, dimension temporal y espacial | Cumplido | `docs/INFORME_EC1.md`, `docs/FUENTES_Y_DATOS.md` |
| Problema claro y delimitado | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Objetivos | Cumplido | `docs/INFORME_EC1.md` |
| Minimo 3 fuentes reales y heterogeneas | Cumplido | FIRMS, Open-Meteo, CAMS, CHIRPS, MODIS |
| Exploracion preliminar real | Cumplido | Datos procesados y reportes en `reports/` |
| Calidad preliminar | Cumplido | `tests/test_calidad_datos.py` |
| Viabilidad SQL + NoSQL | Cumplido | `docs/ARQUITECTURA.md`, `sql/`, `nosql/` |
| Preguntas analiticas | Cumplido | `sql/queries/01_analiticas.sql`, `docs/CORRESPONDENCIA_PREGUNTAS_CONSULTAS_DASHBOARD.md` |

## EC2 - Diseno de la solucion

| Requisito EC2 | Estado | Evidencia actual |
|---|---:|---|
| Modelo ER/EER y explicacion formal | Cumplido | `docs/figures/figura_4_esquema_estrella.svg`, `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Transformacion al modelo relacional | Cumplido | `sql/ddl/02_schema.sql`, `docs/ANEXO_A_DDL_MYSQL.md` |
| Normalizacion justificada | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Esquema fisico | Cumplido | `sql/ddl/` |
| Modelo NoSQL | Cumplido | `nosql/schemas/`, `docs/ANEXO_B_JSON_SCHEMA_MONGODB.md` |
| Arquitectura detallada | Cumplido | `docs/ARQUITECTURA.md`, `docs/figures/figura_5_arquitectura_detallada.svg` |
| Diseno detallado del ETL | Cumplido | `etl/`, `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Constraints SQL y JSON Schema | Cumplido | `sql/ddl/02_schema.sql`, `nosql/schemas/` |
| KPIs | Cumplido | `dashboard/app.py` |
| Trade-offs | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md`, `docs/SLA_Y_RENDIMIENTO.md` |

## EC3 - Implementacion

| Requisito EC3 | Estado | Evidencia actual |
|---|---:|---|
| DDL completo con integridad, restricciones e indices | Cumplido | `sql/ddl/01_roles.sql` a `sql/ddl/04_vistas.sql` |
| Carga real mediante ETL | Cumplido | `etl/load/load_postgres.py`, `etl/load/load_mongo.py` |
| Validacion post-carga | Cumplido | `tests/test_calidad_datos.py`, `reports/carga_completa_ultimo.json` |
| NoSQL con datos reales y consultas | Cumplido | `nosql/queries/01_consultas.js`, `reports/sql_vs_nosql_real_ultimo.json` |
| ETL modular con logging y config externa | Cumplido | `etl/`, `config/settings.py`, `etl/utils/logger.py` |
| Automatizacion reproducible | Cumplido | `etl/scheduler.py`, `scripts/` |
| CDC funcional | Cumplido | Tests `cdc_detecta_nuevos` y `cdc_detecta_modificacion` |
| Testing de calidad, idempotencia y CDC | Cumplido | `20 PASS / 0 FAIL` |
| Seguridad de BD y pipeline | Cumplido | Roles, vistas, variables externas |
| Backup de BD y config | Cumplido | `reports/backup_restore_ultimo.json` |
| Dashboard | Cumplido | `dashboard/app.py` |
| Docker | Cumplido | Compose valido |
| Arquitectura hibrida | Cumplido | `docs/DESPLIEGUE_HIBRIDO.md` |
| Rendimiento preliminar | Cumplido | `reports/rendimiento_ultimo.json`, `reports/sql_vs_nosql_real_ultimo.json` |

## Prioridad para defensa

1. Mostrar `docs/ESTADO_ACTUAL_PROYECTO_2026-05-20.md`.
2. Ejecutar `pytest tests -q`.
3. Mostrar `reports/carga_completa_ultimo.json`.
4. Mostrar `reports/sql_vs_nosql_real_ultimo.json`.
5. Abrir dashboard Streamlit.
6. Explicar con honestidad que UTEC versionado es evidencia historica del 15/05 y que el estado actual local incorpora Chile.
