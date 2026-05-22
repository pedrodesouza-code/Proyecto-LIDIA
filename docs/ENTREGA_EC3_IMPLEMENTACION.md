# Entrega EC3 - Implementacion funcional

Estado operativo actualizado: **2026-05-20**.

La fuente de verdad del estado actual es `docs/ESTADO_ACTUAL_PROYECTO_2026-05-20.md`. Los documentos fechados el `2026-05-15` se conservan como evidencia historica de una sincronizacion UTEC anterior.

## Resumen ejecutivo

SINIA-UY esta implementado y ejecutable como proyecto de ingenieria de datos. Integra fuentes ambientales reales, ejecuta ETL modular en Python, persiste datos en PostgreSQL y MongoDB, valida calidad/idempotencia/CDC y expone resultados mediante dashboard Streamlit y reportes reproducibles.

Evidencia actual:

- Alcance vigente: `ARG`, `BRA`, `CHL`, `URY`.
- Puntos de monitoreo: `36`.
- Tests de datos: `20 PASS / 0 FAIL`.
- FIRMS procesado: `1.946.361` focos.
- Docker Compose: configuracion valida con `docker compose config --quiet`.
- Reporte central: `reports/carga_completa_ultimo.json`.

## 1. Modelo relacional SQL

| Exigencia | Implementacion | Evidencia |
|---|---|---|
| DDL completo | Roles, schema, indices, vistas y materializadas | `sql/ddl/01_roles.sql` a `sql/ddl/07_optimizacion_materializada.sql` |
| Integridad referencial | FK entre hechos y puntos de monitoreo | `sql/ddl/02_schema.sql` |
| Restricciones | `CHECK`, `NOT NULL`, claves naturales y unicidad | `sql/ddl/02_schema.sql` |
| Indices | Fecha, punto, riesgo, FRP, calidad de aire y ejecuciones ETL | `sql/ddl/03_indices.sql` |
| Carga real ETL | Upsert e idempotencia hacia PostgreSQL | `etl/load/load_postgres.py` |
| Validacion post-carga | Reportes y tests | `reports/carga_completa_ultimo.json`, `tests/resultados_tests.json` |

Evidencia actual de carga:

| Control | Resultado |
|---|---:|
| FIRMS procesado en Parquet | `1.946.361` |
| PostgreSQL `focos_calor` ARG | `1.039.964` |
| PostgreSQL `focos_calor` BRA | `9.257.301` |
| PostgreSQL `focos_calor` CHL | `109.824` |
| PostgreSQL `focos_calor` URY | `46.317` |
| Puntos meteorologicos | `36` |

Nota: los conteos PostgreSQL son mayores al Parquet consolidado porque reflejan cargas historicas/materializadas acumuladas en la base usada para evidencia.

## 2. Modelo NoSQL

| Exigencia | Implementacion | Evidencia |
|---|---|---|
| Estructura documental | Snapshots, alertas y ejecuciones ETL | `nosql/schemas/`, `docs/ANEXO_B_JSON_SCHEMA_MONGODB.md` |
| Datos reales | Snapshots FIRMS y resumenes materializados | `etl/load/load_mongo.py`, `scripts/optimizar_mongo_resumenes.py` |
| Consultas representativas | Agregaciones por pais, mes y trazabilidad | `nosql/queries/01_consultas.js` |
| Comparacion SQL/NoSQL | Reporte real contra motores | `reports/sql_vs_nosql_real_ultimo.json` |

Evidencia MongoDB actual:

| Control | Resultado |
|---|---:|
| `focos_snapshots` | `799` |
| `focos_resumen_pais` | `4` documentos |
| `focos_resumen_mes` | `63` documentos |
| Alcance resumido | `ARG`, `BRA`, `CHL`, `URY` |

## 3. ETL estructurado en Python

| Exigencia | Implementacion | Evidencia |
|---|---|---|
| Codigo modular | Extract, transform, load y scheduler separados | `etl/extract/`, `etl/transform/`, `etl/load/`, `etl/scheduler.py` |
| Separacion de etapas | Directorios por responsabilidad | `etl/` |
| Manejo de errores | Try/except, estados ETL y logs | `etl/load/`, `etl/utils/logger.py` |
| Configuracion externa | Variables de entorno y `.env.example` | `config/settings.py`, `config/utec.env.example`, `docker/.env.example` |
| Automatizacion | Scheduler y scripts reproducibles | `etl/scheduler.py`, `scripts/` |

## 4. CDC e idempotencia

| Exigencia | Implementacion | Evidencia |
|---|---|---|
| Carga inicial | Parquets procesados y loaders | `data/processed/`, `etl/load/` |
| Carga incremental | Watermark temporal y upsert | `etl/scheduler.py` |
| Insercion nueva | Test `cdc_detecta_nuevos` | `tests/test_calidad_datos.py` |
| Modificacion existente | Test `cdc_detecta_modificacion` | `tests/test_calidad_datos.py` |
| Idempotencia | Claves naturales y deduplicacion | `tests/test_calidad_datos.py` |

Resultado actual:

```text
20 passed
```

## 5. Testing y validacion

Suite principal: `tests/test_calidad_datos.py`.

| Categoria | Cobertura |
|---|---|
| Alcance | 4 paises, 36 puntos y 19 departamentos de Uruguay |
| Calidad | Completitud, unicidad, consistencia y validez |
| Idempotencia | Doble carga FIRMS y meteo sin duplicados logicos |
| CDC | Nuevos registros y modificaciones |
| Cobertura de datasets | Meteo, CAMS y CHIRPS cubren los 36 puntos |

Comando:

```bash
pytest tests -q
```

Resultado validado:

```text
20 passed in 15.82s
```

## 6. Seguridad, backup y gobernanza

| Exigencia | Implementacion | Evidencia |
|---|---|---|
| Roles diferenciados | Admin, ETL/escritura y lectura | `sql/ddl/01_roles.sql` |
| Privilegio minimo | Grants y vistas controladas | `sql/ddl/01_roles.sql`, `sql/ddl/04_vistas.sql` |
| Variables externas | Credenciales fuera del codigo | `config/settings.py`, `.env.example` |
| Backup | PostgreSQL, MongoDB y config | `reports/backup_restore_ultimo.json` |
| Gobernanza | Limitaciones, sesgos y uso responsable | `docs/SEGURIDAD_BACKUP_GOBERNANZA.md` |

## 7. Dashboard Streamlit

Dashboard: `dashboard/app.py`.

Cumplimientos:

- Mas de 7 metricas clave.
- Agregaciones temporales diarias y mensuales.
- Comparaciones por pais, periodo, riesgo, focos y calidad del aire.
- Conexion directa a PostgreSQL.
- Fallback controlado a Parquet.
- Filtros por pais, periodo y punto de monitoreo.

Comando:

```bash
streamlit run dashboard/app.py
```

Acceso:

```text
http://localhost:8501
```

## 8. Despliegue hibrido y Docker

| Exigencia | Implementacion | Evidencia |
|---|---|---|
| Infraestructura institucional | Verificacion UTEC historica | `reports/utec_verificacion_ultimo.json` |
| Ejecucion local/cloud | Dashboard Streamlit y fallback Parquet | `dashboard/`, `.streamlit/` |
| Docker | PostgreSQL, MongoDB y Streamlit | `docker/docker-compose.yml`, `docker/Dockerfile.streamlit` |
| Configuracion validada | Compose parsea correctamente | `docker compose ... config --quiet` |

Importante para defensa: `reports/utec_verificacion_ultimo.json` es evidencia del `2026-05-15` con alcance anterior `ARG/BRA/URY`. El alcance actual del repositorio es `ARG/BRA/CHL/URY`.

## 9. Rendimiento

Evidencia:

- `reports/rendimiento_ultimo.json`
- `reports/sql_vs_nosql_real_ultimo.json`
- `docs/SLA_Y_RENDIMIENTO.md`

Resultado clave:

- Consultas SQL materializadas: bajo milisegundos en agregaciones por pais/mes.
- Mongo materializado: bajo milisegundos para resumenes por pais y mes.
- Mongo embebido sin materializar: mas lento, usado como evidencia del trade-off.

## Comandos de demo

```bash
pytest tests -q
python scripts/medir_rendimiento.py
python scripts/comparar_sql_nosql_real.py
docker compose -f docker/docker-compose.yml --env-file docker/.env.example config --quiet
streamlit run dashboard/app.py
```

## Frase corta para defensa

EC3 queda cubierto porque el sistema ejecuta el ciclo completo del dato: fuentes reales, ETL modular, persistencia SQL/NoSQL, calidad de datos, idempotencia, CDC, dashboard, rendimiento, seguridad, backup y evidencia reproducible.
