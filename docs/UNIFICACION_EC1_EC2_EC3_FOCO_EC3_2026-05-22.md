# Unificacion EC1, EC2 y EC3 - foco de preparacion EC3

Fecha de trabajo: 2026-05-22.

Este documento unifica las tres consignas de seguimiento del proyecto y las conecta con el estado actual de SINIA-UY. La idea central para estudiar es simple: **EC3 no es un proyecto nuevo; EC3 demuestra funcionando lo que EC1 definio y EC2 diseno**.

## 1. Lectura integrada de las etapas

| Etapa | Pregunta central | Resultado esperado | En SINIA-UY |
|---|---|---|---|
| EC1 | Que problema real voy a resolver y con que datos? | Dominio, fuentes reales, preguntas analiticas y exploracion preliminar | Monitoreo ambiental/incendios con FIRMS, Open-Meteo, CAMS, CHIRPS y MODIS |
| EC2 | Como integro esas fuentes en una arquitectura coherente? | Modelo destino SQL/NoSQL, arquitectura, ETL disenado, reglas e indicadores | Modelo PostgreSQL + MongoDB, ETL modular, dashboard y decisiones tecnicas |
| EC3 | Ese diseno funciona con datos reales y es reproducible? | Sistema ejecutable, ETL real, CDC, tests, seguridad, dashboard y despliegue | Pipeline completo validado, 20 tests PASS, reportes y Streamlit |

Frase clave:

> EC1 justifica el problema, EC2 justifica el diseno, EC3 prueba la implementacion.

## 2. EC1 - Que habia que cubrir

La consigna de EC1 pide:

- problema claro y delimitado;
- objetivo general y 3 a 6 objetivos especificos;
- minimo 3 fuentes reales;
- fuentes heterogeneas, no datasets triviales;
- exploracion preliminar;
- al menos 10 preguntas analiticas;
- analisis del dominio;
- actores, variables, dimension temporal y espacial;
- evidencia real: codigo, tablas, capturas o analisis;
- arquitectura preliminar.

### Como se cumple en el proyecto

| Exigencia EC1 | Evidencia del repo | Como defenderlo |
|---|---|---|
| Problema real | `docs/GUIA_DEFENSA_TECNICA_COMPLETA_2026-05-22.md`, `docs/_archivo/historico/INFORME_EC1.md` | El problema es integrar datos ambientales dispersos para monitoreo regional |
| Datos reales | `data/processed/`, `reports/carga_completa_ultimo.json` | Hay millones de focos FIRMS y datasets meteorologicos/ambientales reales |
| Minimo 3 fuentes | FIRMS, Open-Meteo, CAMS, CHIRPS, MODIS | Se usan 5 fuentes, con formatos y granularidades distintas |
| Preguntas analiticas | `sql/queries/01_analiticas.sql`, `docs/CORRESPONDENCIA_PREGUNTAS_CONSULTAS_DASHBOARD.md` | El dashboard y SQL responden preguntas por pais, fecha, riesgo, calidad de aire |
| Exploracion/calidad | `tests/test_calidad_datos.py` | Se valida completitud, unicidad, consistencia y dominios |
| Dominio | `docs/GUIA_DEFENSA_TECNICA_COMPLETA_2026-05-22.md`, `docs/GUIA_DEFENSA_FINAL.md` | Incendios, meteorologia, aire, precipitacion y cobertura vegetal |

### Como decirlo en defensa

> En EC1 se definio un problema de ingenieria de datos: las fuentes ambientales existen, pero estan dispersas, tienen formatos distintos y no permiten responder directamente preguntas integradas. Por eso el proyecto toma fuentes reales y heterogeneas, define alcance geografico/temporal y formula preguntas analiticas que luego se implementan.

## 3. EC2 - Que habia que cubrir

La consigna de EC2 pide:

- diagrama ER/EER con explicacion formal;
- transformacion completa al modelo relacional;
- normalizacion explicita y justificada;
- esquema relacional fisico preliminar;
- modelo NoSQL;
- arquitectura detallada;
- diseno detallado del ETL;
- reglas de integridad: constraints/checks SQL y JSON Schema NoSQL;
- metricas preliminares;
- justificacion tecnica, alternativas y trade-offs;
- mapeo fuente-destino;
- resolucion de conflictos de nombres, tipos, claves y granularidades.

### Como se cumple en el proyecto

| Exigencia EC2 | Evidencia del repo | Como defenderlo |
|---|---|---|
| Modelo relacional | `sql/ddl/02_schema.sql`, `docs/ANEXO_A_DDL_MYSQL.md` | PostgreSQL implementa tablas de hechos y dimensiones |
| ER/EER y arquitectura | `docs/figures/`, `docs/GUIA_DEFENSA_TECNICA_COMPLETA_2026-05-22.md` | Hay arquitectura por capas: fuentes, ETL, SQL/NoSQL, dashboard |
| Normalizacion | `docs/GUIA_DEFENSA_TECNICA_COMPLETA_2026-05-22.md` | Puntos y paises son dimensiones; mediciones son hechos |
| NoSQL | `nosql/schemas/`, `docs/ANEXO_B_JSON_SCHEMA_MONGODB.md` | Mongo guarda snapshots, alertas y ejecuciones ETL |
| Reglas de integridad | `CHECK`, `UNIQUE`, `FK`, JSON Schema | SQL protege consistencia fuerte; Mongo valida estructura documental |
| ETL disenado | `etl/extract/`, `etl/transform/`, `etl/load/` | Separacion clara por responsabilidad |
| Trade-offs | `docs/SLA_Y_RENDIMIENTO.md`, `docs/REPLICACION_Y_SHARDING.md` | Se explica por que SQL para analitica y Mongo para documentos |

### Conflictos de integracion y resolucion

| Conflicto | Ejemplo | Decision tomada |
|---|---|---|
| Nombres distintos | `acq_date`/fecha, PM10, AQI | Se normalizan columnas en transformaciones |
| Tipos distintos | Fechas como texto, numericos con nulos | pandas convierte tipos antes de Parquet/BD |
| Granularidad distinta | FIRMS por evento, meteo diaria, CHIRPS mensual, MODIS anual | Se modelan tablas con granos diferentes y claves naturales propias |
| Claves no compartidas | FIRMS no trae `id_punto` | Focos conservan coordenada real; puntos se usan para meteo/CAMS/CHIRPS/MODIS |
| Valores faltantes | CAMS puede tener horas sin dato | Se registra `horas_validas` y se testea completitud donde corresponde |

### Como decirlo en defensa

> En EC2 se decidio que el modelo integrado no fuerza todas las fuentes a una unica tabla. Cada tabla respeta su grano: foco satelital, medicion diaria, precipitacion mensual o cobertura anual. PostgreSQL conserva integridad relacional y MongoDB almacena estructuras flexibles como snapshots y alertas.

## 4. EC3 - Que hay que defender ahora

La consigna de EC3 pide:

- sistema funcional ejecutable con datos reales;
- ETL modular en Python con configuracion externa, logs y manejo de errores;
- SQL y NoSQL integrados con consultas alineadas a los objetivos;
- CDC operativo: carga inicial + incremental con evidencia;
- testing documentado: calidad, idempotencia y CDC;
- seguridad, etica y gobernanza;
- dashboard Streamlit funcional;
- arquitectura distribuida/documentada;
- docker-compose y despliegue;
- repositorio con README, carpetas claras, scripts, reportes y evidencias.

### Mapa de cumplimiento EC3

| Requisito EC3 | Implementacion | Evidencia directa |
|---|---|---|
| Sistema ejecutable | Proyecto Python + Streamlit + BD + Parquet | `README.md`, `MANUAL_ARRANQUE.md` |
| Datos reales | FIRMS, Open-Meteo, CAMS, CHIRPS, MODIS | `data/processed/`, `reports/carga_completa_ultimo.json` |
| ETL modular | Extract, transform, load, scheduler | `etl/` |
| Config externa | `.env`, settings, ejemplos | `config/settings.py`, `config/utec.env.example`, `docker/.env.example` |
| Logs y errores | Logger JSON y manejo try/except | `etl/utils/logger.py`, `logs/` |
| SQL implementado | Roles, tablas, indices, vistas | `sql/ddl/` |
| NoSQL implementado | Schemas, consultas, snapshots | `nosql/`, `etl/load/load_mongo.py` |
| CDC | Upserts, watermarks, tests | `etl/scheduler.py`, `etl/load/load_postgres.py`, `tests/test_calidad_datos.py` |
| Idempotencia | Claves naturales y `ON CONFLICT` | `sql/ddl/02_schema.sql`, tests |
| Testing | 20 pruebas automatizadas | `tests/test_calidad_datos.py`, `tests/resultados_tests.json` |
| Seguridad | Roles, vistas, credenciales fuera del codigo | `sql/ddl/01_roles.sql`, `.gitignore`, `.env.example` |
| Backup | Backup/restore evidenciado | `reports/backup_restore_ultimo.json` |
| Dashboard | Streamlit con fallback a Parquet | `dashboard/app.py`, `dashboard/db.py` |
| Docker | Compose y Dockerfile | `docker/docker-compose.yml`, `docker/Dockerfile.streamlit` |
| Rendimiento/SLA | Medicion reproducible | `reports/rendimiento_ultimo.json`, `docs/SLA_Y_RENDIMIENTO.md` |

## 5. Foco de estudio para EC3

Para la defensa, no conviene empezar por todas las carpetas. Conviene seguir este orden:

1. Problema y fuentes: explicar por que el proyecto existe.
2. Arquitectura: explicar el flujo completo del dato.
3. Modelo SQL: explicar tablas, claves, relaciones, constraints e indices.
4. Modelo NoSQL: explicar por que Mongo y que guarda.
5. ETL: explicar extract, transform, load y scheduler.
6. CDC/idempotencia: explicar `ON CONFLICT`, claves naturales y tests.
7. Testing: explicar categorias y resultado.
8. Dashboard: explicar que responde y de donde lee.
9. Seguridad/despliegue: explicar `.env`, roles, Docker y UTEC.
10. Limitaciones: decir honestamente que UTEC historico refleja un alcance anterior y que el estado actual local incluye Chile.

## 6. Secuencia de demo recomendada

### Paso 1 - Mostrar estado actual

Archivo:

```text
docs/CIERRE_ENTREGA_2026-05-22.md
```

Que decir:

> Esta es la fuente de cierre operativo: resume alcance, tests, datos procesados y proximos pasos opcionales.

### Paso 2 - Ejecutar tests

```bash
pytest tests -q
```

Que decir:

> La suite valida alcance, calidad, unicidad, consistencia, idempotencia y CDC.

### Paso 3 - Mostrar modelo SQL

Archivos:

```text
sql/ddl/02_schema.sql
sql/ddl/03_indices.sql
sql/ddl/04_vistas.sql
```

Que decir:

> El modelo relacional separa dimensiones y hechos. Las claves naturales permiten idempotencia y las foreign keys mantienen integridad.

### Paso 4 - Mostrar modelo NoSQL

Archivos:

```text
nosql/schemas/
etl/load/load_mongo.py
```

Que decir:

> MongoDB se usa para documentos operacionales: snapshots, alertas y ejecuciones. No reemplaza al SQL; lo complementa.

### Paso 5 - Mostrar ETL

Archivos:

```text
etl/extract/
etl/transform/
etl/load/
etl/scheduler.py
```

Que decir:

> El ETL esta separado por responsabilidad: descargar, transformar y cargar. El scheduler ejecuta incrementales.

### Paso 6 - Mostrar dashboard

```bash
streamlit run dashboard/app.py
```

Que decir:

> El dashboard consume PostgreSQL cuando esta disponible y usa Parquet como fallback controlado, por eso la demo no depende exclusivamente de la base levantada.

## 7. Preguntas previsibles y respuestas cortas

### Por que EC3 no cambia el diseno de EC2?

Porque EC3 implementa el modelo destino definido en EC2. Si aparecen ajustes, deben estar justificados por datos reales, no por cambio arbitrario de alcance.

### Donde se ve que hay datos reales?

En `data/processed/`, `reports/carga_completa_ultimo.json` y en los conteos: FIRMS procesado tiene `1.946.361` focos.

### Donde esta la carga incremental?

En `etl/scheduler.py` y en los loaders con `ON CONFLICT DO UPDATE`. La idea es cargar nuevos datos o actualizar modificados sin recargar todo.

### Donde esta la idempotencia?

En las claves naturales `UNIQUE` y en los tests de doble carga. Por ejemplo, `focos_calor` evita duplicar el mismo foco por latitud, longitud, fecha, hora y satelite.

### Por que algunas fuentes no tienen la misma granularidad?

Porque representan fenomenos distintos: FIRMS es por evento, meteo/CAMS diario, CHIRPS mensual y MODIS anual. El modelo respeta cada grano en vez de deformar los datos.

### Por que usar SQL y NoSQL?

SQL para datos estructurados, integridad y analitica. NoSQL para documentos flexibles, snapshots y alertas. Es persistencia poliglota justificada por uso.

### Que muestra el dashboard?

Muestra focos, riesgo meteorologico, calidad del aire, forecast, comparaciones por pais, dias criticos y evidencia operativa.

### Que pasa si el profesor pregunta por UTEC?

Respuesta honesta:

> La verificacion UTEC registrada es evidencia historica del 2026-05-15 con alcance anterior. El estado funcional actual del repositorio, validado localmente el 2026-05-22, incorpora `ARG`, `BRA`, `CHL`, `URY` y 36 puntos.

## 8. Checklist final de preparacion EC3

- [x] Entender EC1 como justificacion del problema.
- [x] Entender EC2 como justificacion del diseno.
- [x] Entender EC3 como demostracion funcional.
- [x] Tener ubicadas las evidencias principales.
- [x] Saber explicar tablas SQL y colecciones Mongo.
- [x] Saber explicar CDC e idempotencia.
- [x] Saber ejecutar tests.
- [x] Saber levantar dashboard.
- [x] Material base listo para ensayar defensa oral con preguntas duras.

## 9. Documentos de estudio recomendados

Leer en este orden:

1. `docs/UNIFICACION_EC1_EC2_EC3_FOCO_EC3_2026-05-22.md`
2. `docs/GUIA_DEFENSA_TECNICA_COMPLETA_2026-05-22.md`
3. `docs/CIERRE_ENTREGA_2026-05-22.md`
4. `docs/MATRIZ_CUMPLIMIENTO_CONSIGNA_2026.md`
5. `docs/ENTREGA_EC3_IMPLEMENTACION.md`
6. `sql/ddl/02_schema.sql`
7. `etl/load/load_postgres.py`
8. `dashboard/db.py`

## 10. Idea central para memorizar

> El proyecto es defendible porque cada etapa tiene continuidad: EC1 define un problema real con fuentes heterogeneas; EC2 diseña un modelo integrado SQL/NoSQL y un ETL; EC3 demuestra que ese diseño corre con datos reales, controles de calidad, CDC, dashboard, seguridad y evidencia reproducible.

