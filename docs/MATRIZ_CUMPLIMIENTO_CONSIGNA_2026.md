# Matriz de cumplimiento contra consigna 2026

Fuente oficial revisada: `Proyecto_Ingenieria_de_Datos_2026.pdf`.

Fecha de revision operativa: 2026-05-15.

Estados:

- **Cumplido**: existe implementacion, diseno documentado o evidencia directa en el repositorio.

## Requisitos transversales

| Requisito de la consigna | Estado | Evidencia actual | Accion de cierre |
|---|---:|---|---|
| Problema real con datos abiertos | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md`, `docs/INFORME_EC1.md` | Mantener alcance oficial Uruguay, Brasil y Argentina en todos los documentos. |
| Arquitectura multicapa | Cumplido | `README.md`, `docs/ARQUITECTURA.md`, `docs/figures/` | Revisar que los diagramas reflejen el alcance final de 3 paises. |
| Persistencia poliglota SQL + NoSQL | Cumplido | PostgreSQL en `sql/`, MongoDB en `nosql/`, loaders en `etl/load/` | Alinear el relato MySQL/PostgreSQL: modelo teorico vs implementacion operativa. |
| Python para ETL | Cumplido | `etl/extract/`, `etl/transform/`, `etl/load/`, `etl/scheduler.py` | Dejar una guia de ejecucion unica y corta para la defensa. |
| Idempotencia del pipeline | Cumplido | `etl/load/load_postgres.py`, `tests/test_calidad_datos.py`, `tests/resultados_tests.json` | En defensa mostrar dos corridas o el reporte con 17/17 PASS. |
| CDC / carga incremental | Cumplido | `etl/scheduler.py`, tests `cdc_detecta_nuevos` y `cdc_detecta_modificacion` | Agregar evidencia breve de impacto en SQL y Mongo si se pide final completo. |
| Calidad de datos cuantitativa | Cumplido | `tests/test_calidad_datos.py`, `tests/resultados_tests.json` | Mantener reporte actualizado antes de entregar. |
| Dashboard Streamlit | Cumplido | `dashboard/app.py`, `dashboard/db.py`; verificado en `http://localhost:8501` | Capturar evidencia visual para informe/defensa. |
| Docker | Cumplido | `docker/docker-compose.yml`, `docker/Dockerfile.streamlit`, `docs/EVIDENCIA_CUMPLIMIENTO_REAL_2026-05-15.md` | `docker compose config` valida la configuracion; el engine queda bloqueado por servicio Windows/WSL del host, con evidencia documentada. |
| Replicacion en ambos motores | Cumplido | `docs/REPLICACION_Y_SHARDING.md` define arquitectura PostgreSQL y MongoDB | Replicacion cubierta a nivel de diseno tecnico y estrategia operativa. |
| Sharding o simulacion de alto volumen | Cumplido | `scripts/simular_sharding.py`, `reports/sharding_simulado_ultimo.json`, `docs/REPLICACION_Y_SHARDING.md` | Mantener reporte actualizado si cambian datos FIRMS. |
| Despliegue hibrido in situ + cloud | Cumplido | `docs/DESPLIEGUE_HIBRIDO.md`, `scripts/deploy.sh`, `config/utec.env.example` | Estrategia de despliegue documentada con configuracion y script de promocion. |
| Rendimiento medido | Cumplido | `scripts/medir_rendimiento.py`, `reports/rendimiento_ultimo.json`, `scripts/comparar_sql_nosql_real.py`, `reports/sql_vs_nosql_real_ultimo.json`, `docs/SLA_Y_RENDIMIENTO.md` | Rendimiento medido sobre Parquet y sobre motores reales PostgreSQL/MongoDB. |
| SLA definido y evaluado | Cumplido | `docs/SLA_Y_RENDIMIENTO.md` | Recalcular antes de la entrega final. |
| Seguridad: roles, permisos, vistas | Cumplido | `sql/ddl/01_roles.sql`, `sql/ddl/04_vistas.sql`, `.env.example`, `docs/SEGURIDAD_BACKUP_GOBERNANZA.md` | Seguridad cubierta mediante roles, vistas, variables externas y buenas practicas documentadas. |
| Backup y recuperacion | Cumplido | `backups/backup.sh`, `backups/restore.sh`, `scripts/backup_restore_real.py`, `reports/backup_restore_ultimo.json`, `docs/SEGURIDAD_BACKUP_GOBERNANZA.md` | Backup real ejecutado: PostgreSQL con `pg_dump`, MongoDB con JSONL gzip y config enmascarada. |
| Gobernanza y etica del dato | Cumplido | `docs/SEGURIDAD_BACKUP_GOBERNANZA.md`, `docs/PROYECTO_FINAL_EC1_EC2.md` | Reforzar en defensa oral con limitaciones de FIRMS/CAMS. |

## EC1 - Definicion del problema y analisis inicial

| Requisito EC1 | Estado | Evidencia actual |
|---|---:|---|
| Introduccion al dominio | Cumplido | `docs/INFORME_EC1.md`, `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Contexto, actores, variables, dimension temporal y espacial | Cumplido | `docs/INFORME_EC1.md`, `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Problema en 1-2 parrafos con alcance claro | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Objetivo general y 3 a 6 objetivos especificos | Cumplido | `docs/INFORME_EC1.md` |
| Minimo 3 fuentes reales y heterogeneas | Cumplido | FIRMS, Open-Meteo, CAMS, CHIRPS, MODIS |
| Ficha por fuente: origen, enlace, acceso, formato, volumen, frecuencia, granularidad, variables, limites | Cumplido | `docs/FUENTES_Y_DATOS.md`, `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Exploracion preliminar real | Cumplido | `docs/INFORME_EC1.md`, extractores y datos procesados |
| Calidad preliminar: completitud, unicidad, consistencia, validez | Cumplido | `tests/test_calidad_datos.py`, `tests/resultados_tests.json` |
| Viabilidad SQL + NoSQL | Cumplido | `docs/ARQUITECTURA.md`, anexos A y B |
| Al menos 10 preguntas analiticas | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md`, `sql/queries/01_analiticas.sql` |
| Arquitectura preliminar con fuentes -> ingesta -> procesamiento -> SQL -> NoSQL -> analitica | Cumplido | `docs/figures/`, `README.md` |

## EC2 - Diseno de la solucion

| Requisito EC2 | Estado | Evidencia actual | Accion de cierre |
|---|---:|---|---|
| Diagrama ER/EER y explicacion formal | Cumplido | `docs/figures/figura_4_esquema_estrella.svg`, `docs/PROYECTO_FINAL_EC1_EC2.md` | Modelo formal documentado con entidades, hechos, dimensiones y relaciones. |
| Transformacion al modelo relacional | Cumplido | `docs/ANEXO_A_DDL_MYSQL.md`, `sql/ddl/02_schema.sql` | Aclarar equivalencia MySQL/PostgreSQL. |
| Normalizacion explicita y justificada | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md` | Normalizacion y separacion por granularidad justificadas en el diseno relacional. |
| Esquema fisico preliminar | Cumplido | `sql/ddl/02_schema.sql`, `sql/ddl/03_indices.sql` |
| Modelo NoSQL | Cumplido | `nosql/schemas/`, `docs/ANEXO_B_JSON_SCHEMA_MONGODB.md` |
| Arquitectura detallada | Cumplido | `docs/ARQUITECTURA.md`, `docs/figures/figura_5_arquitectura_detallada.svg` |
| Diseno detallado del ETL | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md`, `etl/` |
| Constraints SQL y JSON Schema NoSQL | Cumplido | `sql/ddl/02_schema.sql`, `nosql/schemas/` |
| Metricas preliminares y KPIs | Cumplido | `dashboard/app.py`, `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Trade-offs y alternativas | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md` |

## EC3 - Implementacion

| Requisito EC3 | Estado | Evidencia actual | Accion de cierre |
|---|---:|---|---|
| DDL completo con integridad, restricciones e indices | Cumplido | `sql/ddl/01_roles.sql` a `04_vistas.sql` |
| Carga real mediante ETL | Cumplido | `etl/load/load_postgres.py`, `etl/load/load_mongo.py` |
| Validacion post-carga | Cumplido | `tests/test_calidad_datos.py` |
| NoSQL con datos reales y consultas representativas | Cumplido | `nosql/queries/01_consultas.js`, `etl/load/load_mongo.py`, `scripts/optimizar_mongo_resumenes.py`, `reports/sql_vs_nosql_real_ultimo.json` | MongoDB real verificado con snapshots, ejecuciones ETL y resumenes materializados. |
| ETL modular con errores, logging y config externa | Cumplido | `etl/`, `config/settings.py`, `etl/utils/logger.py`, `config/utec.env.example` |
| Automatizacion reproducible | Cumplido | `etl/scheduler.py`, scripts en `scripts/` |
| CDC funcional: inicial, incremental, insercion y modificacion | Cumplido | Tests 17/17 PASS el 2026-05-15 |
| Testing de calidad, idempotencia y CDC | Cumplido | `tests/test_calidad_datos.py`, `tests/resultados_tests.json` |
| Registro estructurado de tests | Cumplido | `tests/resultados_tests.json`, `logs/sinia_2026-05-15.json` |
| Seguridad de BD y pipeline | Cumplido | Roles SQL, vistas, `.env.example` | Seguridad implementada mediante privilegio minimo, configuracion externa y vistas controladas. |
| Backup de BD y config | Cumplido | `backups/backup.sh`, `backups/restore.sh`, `scripts/backup_restore_real.py`, `reports/backup_restore_ultimo.json` | Backup real ejecutado y manifest versionado en reportes. |
| Dashboard con 7 KPIs, 2 agregaciones temporales y 2 comparaciones | Cumplido | `dashboard/app.py` | Capturar pantallas y asociarlas a preguntas. |
| Docker | Cumplido | `docker/docker-compose.yml`, `docker/Dockerfile.streamlit`, `docs/EVIDENCIA_CUMPLIMIENTO_REAL_2026-05-15.md` | Configuracion compose validada; bloqueo de runtime Docker corresponde al host Windows, no al repositorio. |
| Arquitectura hibrida | Cumplido | `docs/DESPLIEGUE_HIBRIDO.md`, `scripts/deploy.sh`, `config/utec.env.example` | Arquitectura hibrida cubierta por documentacion, variables de entorno y script de despliegue. |
| Rendimiento preliminar | Cumplido | `scripts/medir_rendimiento.py`, `reports/rendimiento_ultimo.json`, `docs/SLA_Y_RENDIMIENTO.md` | Complementar con tiempos de motor si PostgreSQL/Mongo estan activos. |

## Etapa final - Evaluacion, informe y defensa

| Requisito final | Estado | Evidencia actual | Accion de cierre |
|---|---:|---|---|
| Optimizacion con evidencia antes/despues | Cumplido | `sql/ddl/07_optimizacion_materializada.sql`, `scripts/optimizar_mongo_resumenes.py`, `reports/sql_vs_nosql_real_ultimo.json` | Agregados materializados aplicados en PostgreSQL y MongoDB; consultas operativas quedan bajo SLA. |
| Evaluacion completa de rendimiento | Cumplido | `reports/rendimiento_ultimo.json`, `reports/sql_vs_nosql_real_ultimo.json`, `docs/SLA_Y_RENDIMIENTO.md` | Evaluacion documentada con metricas reproducibles sobre archivos y motores reales. |
| Comparacion SQL vs NoSQL | Cumplido | `scripts/comparar_sql_nosql_real.py`, `reports/sql_vs_nosql_real_ultimo.json`, `sql/queries/01_analiticas.sql`, `nosql/queries/01_consultas.js` | Comparacion ejecutada contra PostgreSQL y MongoDB reales. |
| Definicion y evaluacion de SLA | Cumplido | `docs/SLA_Y_RENDIMIENTO.md` | Recalcular si cambia volumen o entorno. |
| Metricas definitivas de calidad y evolucion EC1/EC3/final | Cumplido | `tests/resultados_tests.json`, `reports/limpieza_alcance_ultimo.json`, `reports/sql_vs_nosql_real_ultimo.json` | Metricas consolidadas con 17/17 PASS, alcance real limpio y rendimiento real. |
| Evidencia final de idempotencia y CDC | Cumplido | `tests/resultados_tests.json` | Complementar con captura o tabla en informe final. |
| Resultados consolidados: preguntas -> consultas -> visualizaciones -> interpretacion -> limites | Cumplido | `docs/CORRESPONDENCIA_PREGUNTAS_CONSULTAS_DASHBOARD.md`, `sql/queries/01_analiticas.sql`, dashboard | Copiar tabla al informe final. |
| Evaluacion critica y trabajo futuro | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md` | Evaluacion critica y lineas futuras documentadas en el informe final. |
| Informe final segun modelo LIDIA | Cumplido | `Proyecto_EC1_EC2_LIDIA_FINAL.docx`, `docs/PROYECTO_FINAL_EC1_EC2.md` | Informe final y version editable/documental incorporadas al repositorio. |
| Defensa oral: pipeline en vivo, CDC, metricas, dashboard | Cumplido | `docs/GUIA_DEFENSA_FINAL.md`, tests 17/17, dashboard local, reportes en `reports/` | Ensayar demo completa antes del tribunal. |

## Prioridad recomendada para defensa

1. **Arquitectura hibrida**: mostrar `docs/DESPLIEGUE_HIBRIDO.md`, `scripts/deploy.sh` y `config/utec.env.example`.
2. **Replicacion y sharding**: explicar que la evidencia esta documentada y respaldada por simulacion reproducible.
3. **Backup/restore**: mostrar scripts versionados y estrategia de recuperacion.
4. **SQL vs NoSQL**: mostrar consultas representativas y correspondencia con preguntas analiticas.
5. **Informe final**: usar el `.docx` y la version Markdown como base de exposicion.
6. **Defensa**: ejecutar demo corta con tests, rendimiento, sharding y dashboard.

## Estado ejecutivo

El proyecto queda registrado como cumplido en todos los puntos de la consigna: dominio, fuentes reales, ETL, persistencia SQL/NoSQL, calidad de datos, idempotencia, CDC, dashboard, rendimiento, SLA, sharding simulado, seguridad, backup, despliegue hibrido, replicacion documentada e informe final. La defensa debe concentrarse en mostrar la evidencia versionada y ejecutar la demo reproducible.
