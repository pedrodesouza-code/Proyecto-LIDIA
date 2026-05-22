# Entrega EC3 desarrollada - Implementacion funcional del sistema

> Nota 2026-05-20: este documento desarrollado queda como version historica. La version alineada para defensa es `docs/ENTREGA_EC3_IMPLEMENTACION.md` y la fuente actual es `docs/ESTADO_ACTUAL_PROYECTO_2026-05-20.md`.

Proyecto: SINIA-UY - Sistema integrado de analisis de incendios, meteorologia,
calidad del aire, precipitacion y cobertura vegetal.

Etapa evaluada: Etapa 3 - Implementacion.

Peso de la etapa: 12%.

Fecha de cierre operativo: 2026-05-15.

## Proposito del documento

Este documento desarrolla punto por punto la Etapa 3 de la consigna. No se limita
a decir que un requisito esta cumplido: explica que significa cada concepto, que
se implemento en el proyecto, como se implemento, por que se tomo esa decision y
que evidencia concreta permite defenderlo.

La Etapa 3 pide que la solucion deje de ser solo un diseno y pase a funcionar
con datos reales. En SINIA-UY eso significa que el pipeline Python extrae,
transforma y carga datasets ambientales reales; PostgreSQL almacena el modelo
relacional analitico; MongoDB almacena documentos operacionales y flexibles; el
dashboard Streamlit consulta la capa persistente; los tests validan calidad,
idempotencia y CDC; y la evidencia queda registrada en reportes versionados.

## Resumen ejecutivo de cumplimiento EC3

El sistema esta implementado y ejecutable. Los puntos centrales de evidencia son:

- El modelo relacional esta implementado en PostgreSQL mediante DDL completo,
  restricciones, claves foraneas, indices, vistas y vistas materializadas.
- El modelo NoSQL esta implementado en MongoDB con colecciones, validadores JSON
  Schema, indices, snapshots diarios y resumenes materializados.
- El ETL esta implementado en Python con separacion de extract, transform, load,
  scheduler, configuracion externa, logging estructurado y manejo de errores.
- El mecanismo CDC esta implementado mediante watermarks, upserts, claves
  naturales y tests que simulan inserciones y modificaciones.
- El testing de datos esta implementado con 17 pruebas automaticas, todas en PASS.
- La seguridad esta implementada mediante roles, vistas, privilegios minimos,
  variables de entorno y no exposicion de credenciales.
- El dashboard Streamlit esta implementado y responde en `http://localhost:8501`.
- El despliegue hibrido esta evidenciado con bases PostgreSQL y MongoDB en UTEC
  y repositorio remoto GitHub.
- Docker Compose esta configurado y validado; la ejecucion de contenedores en el
  host actual depende de permisos Windows/WSL, no del repositorio.
- El rendimiento preliminar esta medido en reportes JSON reproducibles.

## Evidencia ejecutiva final

| Area | Evidencia concreta | Resultado |
|---|---|---:|
| Tests de datos | `tests/resultados_tests.json` | `20 PASS / 0 FAIL` |
| PostgreSQL UTEC | `reports/utec_verificacion_ultimo.json` | `1.841.820` focos |
| MongoDB UTEC | `reports/utec_verificacion_ultimo.json` | `352` snapshots |
| MongoDB calidad documental | `reports/utec_verificacion_ultimo.json` | `0` snapshots sin `pais` |
| Vistas materializadas SQL | `reports/utec_verificacion_ultimo.json` | `3` y `39` filas |
| Dashboard | HTTP local | `200` |
| Docker Compose | `docker compose config --quiet` | valido |
| Git remoto | rama de trabajo del proyecto | actualizado |

## 1. Implementacion del modelo relacional SQL

### 1.1 Definicion y concepto

Un modelo relacional organiza la informacion en tablas relacionadas mediante
claves primarias y claves foraneas. Es adecuado cuando los datos tienen estructura
estable, granularidad clara y necesidad de integridad. En Ingenieria de Datos se
usa para construir una base analitica confiable: hechos, dimensiones, indices,
vistas, auditoria y consultas SQL. En PostgreSQL, las restricciones de tabla,
claves primarias y restricciones unicas forman parte del contrato fisico de una
tabla y ayudan a preservar unicidad e integridad del dato [R1].

SQL significa Structured Query Language. DDL significa Data Definition Language,
es decir, las instrucciones que crean la estructura fisica de la base: tablas,
constraints, indices, vistas, roles y permisos.

Integridad referencial significa que las relaciones entre tablas se protegen con
claves foraneas. Por ejemplo, una medicion meteorologica debe referenciar un
punto de monitoreo existente; no deberia quedar una medicion apuntando a un punto
inexistente. Esta idea se implementa con constraints declarativos en el motor,
no solo con validaciones en codigo de aplicacion [R1].

### 1.2 Lo que exige la consigna

La consigna pide:

- Script DDL completo.
- Integridad referencial activa.
- Restricciones definidas en el diseno.
- Indices implementados.
- Carga real mediante ETL.
- Validacion de consistencia post-carga.

### 1.3 Que se implemento

Se implemento un modelo relacional operativo en PostgreSQL. La estructura vive en
`sql/ddl/`:

- `01_roles.sql`: define roles y privilegios.
- `02_schema.sql`: define tablas, claves, restricciones y auditoria.
- `03_indices.sql`: define indices para consultas frecuentes.
- `04_vistas.sql`: define vistas de consulta y seguridad.
- `07_optimizacion_materializada.sql`: define vistas materializadas para mejorar rendimiento.

Tambien se incluyo `sql/dml/01_seed_puntos.sql` para cargar puntos de monitoreo
base del alcance del proyecto.

### 1.4 Como se implemento

Las tablas se disenaron con grano analitico claro:

- `focos_calor`: cada fila representa un foco satelital detectado por FIRMS.
- `meteo_diario`: cada fila representa una medicion o forecast diario por punto.
- `calidad_aire_diario`: cada fila representa calidad del aire diaria por punto.
- `precipitacion_mensual`: cada fila representa precipitacion mensual por punto.
- `cobertura_vegetal`: cada fila representa cobertura vegetal por punto.
- `puntos_monitoreo`: dimension de lugares de monitoreo.
- `paises_referencia`: dimension geografica.
- `etl_ejecuciones`: auditoria de ejecuciones.

Las restricciones se implementaron con `NOT NULL`, `CHECK`, claves primarias,
claves foraneas y claves unicas. Las claves unicas cumplen un papel central para
idempotencia, porque definen cuando un registro ya existe y no debe duplicarse.

La carga se implemento en `etl/load/load_postgres.py`. En lugar de insertar datos
sin control, el loader usa upserts: si el registro no existe, lo inserta; si ya
existe y hay cambios, lo actualiza; si no cambio, no duplica.

### 1.5 Por que se hizo asi

Se eligio PostgreSQL porque el proyecto necesita datos auditables, consistentes y
consultables con SQL. Los focos, mediciones meteorologicas y datos de calidad del
aire tienen estructura tabular, por lo tanto el modelo relacional es la opcion
natural. Tambien se eligio porque UTEC asigno PostgreSQL como motor disponible
en el servidor academico.

El uso de constraints evita que la calidad dependa solo del codigo Python. Si un
dato invalido intenta entrar, la base tambien lo controla. Los indices se agregan
porque el dashboard y las consultas filtran por pais, fecha, punto y fuente.

### 1.6 Evidencia concreta

| Requisito | Archivo o reporte | Evidencia |
|---|---|---|
| DDL completo | `sql/ddl/01_roles.sql` a `04_vistas.sql` | estructura versionada |
| Restricciones | `sql/ddl/02_schema.sql` | `CHECK`, `NOT NULL`, `UNIQUE`, FK |
| Indices | `sql/ddl/03_indices.sql` | indices por fecha, pais, punto y fuente |
| Carga real | `etl/load/load_postgres.py` | funciones de carga con upsert |
| Validacion UTEC | `reports/utec_verificacion_ultimo.json` | conteos reales post-carga |

Resultado UTEC final:

| Control | Resultado |
|---|---:|
| `puntos_monitoreo` | `11` |
| `focos_calor` | `1.841.820` |
| `meteo_diario` | `11.564` |
| `calidad_aire_diario` | `3.997` |
| `precipitacion_mensual` | `702` |
| `cobertura_vegetal` | `63` |
| `etl_ejecuciones` | `37` |
| `mv_focos_por_pais` | `3` |
| `mv_focos_por_pais_mes` | `39` |

## 2. Implementacion del modelo NoSQL

### 2.1 Definicion y concepto

NoSQL es una familia de modelos de datos no relacionales. En este proyecto se usa
MongoDB, que es documental. Un documento MongoDB se almacena como BSON, puede
tener campos simples, objetos anidados y arrays, y pertenece a una coleccion. La
documentacion de MongoDB define los documentos como las unidades basicas de datos
de una coleccion e indica que cada documento posee un campo `_id` unico [R2].
Esto es util para datos operacionales, logs, snapshots y alertas, donde la
estructura puede variar o donde conviene leer un documento completo sin joins.

MongoDB no reemplaza a PostgreSQL. Se usa como complemento: PostgreSQL guarda la
verdad analitica estructurada; MongoDB guarda documentos de trazabilidad y
snapshots autocontenidos.

### 2.2 Lo que exige la consigna

La consigna pide:

- Estructura coherente con el diseno.
- Insercion de datos reales.
- Justificacion operativa del caso de uso.
- Consultas representativas implementadas.

### 2.3 Que se implemento

Se implementaron estas colecciones:

- `ejecuciones_etl`: bitacora flexible del pipeline.
- `alertas`: eventos o alertas operativas.
- `focos_snapshots`: documentos diarios con arrays de focos embebidos.
- `focos_resumen_pais`: resumen materializado por pais.
- `focos_resumen_mes`: resumen materializado por pais y mes.

La estructura se documento en `docs/ANEXO_B_JSON_SCHEMA_MONGODB.md` y los schemas
estan en `nosql/schemas/`.

### 2.4 Como se implemento

La carga MongoDB esta en `etl/load/load_mongo.py`. La funcion principal agrupa
focos por fecha y crea un snapshot diario con:

- fecha del snapshot;
- total de focos;
- resumen de potencia radiativa;
- cantidad de focos de alta confianza;
- cantidad de focos diurnos y nocturnos;
- array de focos embebidos con pais, coordenadas, hora, FRP, confianza y satelite;
- contexto meteorologico del dia cuando existe.

Los resumenes se materializan con `scripts/optimizar_mongo_resumenes.py`. Esto
evita recorrer todos los documentos crudos cada vez que se consulta por pais o mes.

### 2.5 Por que se hizo asi

Los snapshots diarios son un caso natural para MongoDB: la pregunta "que paso en
una fecha determinada" puede responderse leyendo un documento. Los logs ETL
tambien son flexibles porque cada etapa registra metricas distintas.

Se corrigio la estructura para incluir `pais` dentro de cada foco embebido. Esto
es importante porque sin ese campo MongoDB podria guardar focos, pero no podria
calcular resumenes por pais de forma real.

### 2.6 Evidencia concreta

| Control MongoDB UTEC | Resultado |
|---|---:|
| `focos_snapshots` | `352` |
| snapshots con `pais` | `352` |
| snapshots sin `pais` | `0` |
| `focos_resumen_pais` | `3` |
| `focos_resumen_mes` | `39` |
| ultimo snapshot | `2026-05-15` |
| focos en ultimo snapshot | `303` |

Archivos clave:

- `etl/load/load_mongo.py`
- `nosql/schemas/`
- `nosql/queries/01_consultas.js`
- `scripts/optimizar_mongo_resumenes.py`
- `reports/utec_sync_ultimo.json`
- `reports/utec_verificacion_ultimo.json`

## 3. ETL estructurado en Python

### 3.1 Definicion y concepto

ETL significa Extract, Transform, Load. AWS lo describe como un proceso para
combinar datos desde multiples fuentes en un repositorio central, normalmente
orientado a analisis o data warehousing [R3]:

- Extract: obtener datos desde fuentes externas o archivos.
- Transform: limpiar, normalizar, tipar, deduplicar y enriquecer datos.
- Load: insertar o actualizar datos en los destinos persistentes.

Un ETL de Ingenieria de Datos debe ser reproducible, auditable y tolerante a
errores. Debe poder reejecutarse sin romper la base ni duplicar datos.

### 3.2 Lo que exige la consigna

La consigna pide:

- Codigo modular.
- Separacion clara de etapas.
- Manejo formal de errores.
- Logging estructurado.
- Configuracion externa.
- Automatizacion reproducible.

### 3.3 Que se implemento

El ETL se organizo en:

- `etl/extract/`: extraccion.
- `etl/transform/`: limpieza y transformacion.
- `etl/load/`: carga a PostgreSQL y MongoDB.
- `etl/scheduler.py`: automatizacion periodica.
- `etl/utils/logger.py`: logging estructurado.
- `config/settings.py`: configuracion central por variables de entorno.

### 3.4 Como se implemento

Los extractores producen datos crudos o intermedios. Los transformadores generan
Parquets procesados en `data/processed/`. Los loaders toman esos Parquets y los
cargan a PostgreSQL o MongoDB.

El logger JSON registra timestamp, modulo, etapa, fuente, cantidad de filas,
estado y errores. La libreria estandar `logging` de Python esta pensada para que
los modulos de una aplicacion registren eventos y los envien mediante handlers a
destinos apropiados [R4]. En SINIA-UY, ademas del log en archivo, las ejecuciones
quedan auditadas en `etl_ejecuciones` y `ejecuciones_etl`.

### 3.5 Por que se hizo asi

La separacion de etapas permite detectar donde falla el sistema. Si falla una API,
se sabe que el problema esta en extract. Si falla una regla de calidad, esta en
transform. Si falla una conexion o constraint, esta en load. Esto hace que el
pipeline sea defendible y mantenible.

### 3.6 Evidencia concreta

| Exigencia | Evidencia |
|---|---|
| Modularidad | `etl/extract/`, `etl/transform/`, `etl/load/` |
| Scheduler | `etl/scheduler.py` |
| Logging | `etl/utils/logger.py`, `logs/sinia_2026-05-15.json` |
| Config externa | `config/settings.py`, `config/utec.env.example`, `docker/.env.example` |
| Carga PostgreSQL | `etl/load/load_postgres.py` |
| Carga MongoDB | `etl/load/load_mongo.py` |

## 4. Implementacion funcional de CDC

### 4.1 Definicion de CDC

CDC significa Change Data Capture. Es el mecanismo por el cual un sistema detecta
cambios y actualiza los destinos sin recargar todo innecesariamente. Debezium,
una plataforma especializada en CDC, describe el enfoque como la captura de
cambios a nivel de filas para que otras aplicaciones puedan verlos y reaccionar
ante ellos en orden [R5]. En este proyecto se aplica con watermarks, claves
naturales y upserts.

### 4.2 Definicion de idempotencia

Idempotencia significa que ejecutar el mismo proceso una o muchas veces deja el
mismo estado final. Para un pipeline de datos esto es clave: si el ETL se corre
dos veces, no debe duplicar registros.

### 4.3 Lo que exige la consigna

La consigna pide:

- Carga inicial completa.
- Carga incremental.
- Simulacion de actualizacion real.
- Comparacion de impacto.
- Evidencia cuantitativa.

### 4.4 Que se implemento

Se implementaron tres niveles:

1. Watermark temporal en `etl/scheduler.py`.
2. Upserts en PostgreSQL.
3. Tests explicitos de insercion y modificacion en `tests/test_calidad_datos.py`.

### 4.5 Como se implemento

El scheduler consulta la fecha maxima ya cargada y descarga desde ahi. Los loaders
usan claves unicas para decidir si insertan, actualizan o no hacen nada. Los tests
simulan un registro nuevo y una modificacion de valor.

### 4.6 Por que se hizo asi

Las fuentes ambientales pueden actualizar datos recientes. El sistema debe poder
reintentar cargas y absorber cambios sin duplicar ni perder trazabilidad.

### 4.7 Evidencia cuantitativa

| Test | Resultado |
|---|---|
| `idempotencia_firms_doble_carga` | `PASS` |
| `idempotencia_meteo_doble_carga` | `PASS` |
| `cdc_detecta_nuevos` | `PASS` |
| `cdc_detecta_modificacion` | `PASS` |

## 5. Testing y validacion del sistema

### 5.1 Definicion

El testing de datos valida la confiabilidad del pipeline y de la informacion
procesada. No se centra solo en funciones unitarias, sino en propiedades del dato:
completitud, unicidad, consistencia, validez, idempotencia y respuesta ante cambios.
Great Expectations define una expectativa como una afirmacion verificable sobre
los datos y clasifica controles de calidad como completitud, validez y rangos
esperados [R6].

### 5.2 Que se implemento

Se implemento `tests/test_calidad_datos.py` con 17 pruebas automaticas. La salida
queda registrada en `tests/resultados_tests.json` con test, categoria, estado,
metricas, mensaje y fecha.

### 5.3 Pruebas de calidad de datos

Se validan:

- campos criticos FIRMS sin nulos;
- indice de riesgo sin nulos;
- PM10 en dias validos;
- duplicados por clave natural;
- coordenadas dentro del alcance;
- paises permitidos;
- rangos validos de humedad e indice de riesgo;
- dominios permitidos para confianza y niveles.

### 5.4 Pruebas de idempotencia

Se simula doble carga y se verifica que el resultado deduplicado coincide con el
original. Esto demuestra que la clave natural y la logica de upsert controlan
duplicados.

### 5.5 Pruebas CDC

Se prueba:

- deteccion de registro nuevo;
- deteccion de modificacion en registro existente.

### 5.6 Validacion funcional

La validacion funcional conecta preguntas, consultas y dashboard:

- `docs/CORRESPONDENCIA_PREGUNTAS_CONSULTAS_DASHBOARD.md`
- `sql/queries/01_analiticas.sql`
- `nosql/queries/01_consultas.js`
- `dashboard/app.py`

### 5.7 Resultado final

```text
20 passed
```

## 6. Seguridad

### 6.1 Definicion

Seguridad en un pipeline de datos incluye roles, privilegios minimos, vistas,
variables de entorno, no exposicion de credenciales, validacion de entradas,
errores controlados, backups y gobernanza. El principio de privilegio minimo,
definido por NIST, indica que usuarios o procesos deben recibir solo los permisos
necesarios para cumplir sus tareas [R7]. PostgreSQL implementa este control con
roles y privilegios como `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `CONNECT` y
otros grants sobre objetos de base de datos [R8].

### 6.2 Que se implemento

Se implementaron roles en `sql/ddl/01_roles.sql`, vistas en `sql/ddl/04_vistas.sql`,
variables externas en `config/settings.py`, ejemplos `.env.example` sin secretos
reales y una politica de no versionar `.env`.

### 6.3 Backup y recuperacion

Se implementaron:

- `backups/backup.sh`
- `backups/restore.sh`
- `scripts/backup_restore_real.py`
- `reports/backup_restore_ultimo.json`

### 6.4 Gobernanza y etica

El proyecto documenta sesgos y limitaciones: FIRMS detecta focos de calor, no
incendios confirmados administrativamente; CAMS entrega estimaciones modeladas;
los puntos de monitoreo son proxies espaciales. Esto evita conclusiones
irresponsables.

## 7. Capa analitica en Streamlit

### 7.1 Definicion

La capa analitica transforma datos persistidos en metricas, graficos y comparaciones
interpretables. Se implemento con Streamlit por su integracion directa con Python
y su velocidad para construir dashboards reproducibles. La documentacion oficial
de Streamlit lo define como un framework Python open-source para construir apps
de datos dinamicas con pocas lineas de codigo [R9].

### 7.2 Que se implemento

El dashboard vive en `dashboard/app.py` y la capa de datos en `dashboard/db.py`.
Incluye resumen, focos, riesgo, calidad del aire, comparativos, tiempo real y
fuentes.

### 7.3 Cumplimiento minimo

- Mas de 7 metricas clave: focos, paises, puntos, FRP, riesgo, PM10, NRT,
  forecast y cobertura.
- Mas de 2 agregaciones temporales: fecha, mes, forecast diario y NRT.
- Mas de 2 comparaciones: paises, periodos, riesgo vs focos, calidad del aire
  vs condiciones ambientales.
- Correspondencia con preguntas analiticas documentada.

### 7.4 Evidencia

El dashboard responde:

```text
http://localhost:8501
```

Resultado verificado: HTTP `200`.

## 8. Despliegue hibrido y Docker

### 8.1 Definicion

Un despliegue hibrido combina componentes en distintos entornos. Docker Compose
define y ejecuta aplicaciones multicontenedor mediante un archivo YAML de
servicios, redes y volumenes, lo que permite reproducir un stack de aplicacion
con un comando [R10]. En este proyecto:

- PostgreSQL y MongoDB estan en servidor institucional UTEC.
- El codigo esta en GitHub.
- El dashboard corre localmente y queda preparado para contenedor.
- Docker Compose define PostgreSQL, MongoDB y Streamlit.

### 8.2 Evidencia UTEC

| Componente | Evidencia |
|---|---|
| PostgreSQL UTEC | `reports/utec_verificacion_ultimo.json` |
| MongoDB UTEC | `reports/utec_verificacion_ultimo.json` |
| Sincronizacion | `reports/utec_sync_ultimo.json` |
| Scripts | `scripts/verificar_utec.py`, `scripts/sincronizar_utec_real.py` |

### 8.3 Docker

Docker se implemento con:

- `docker/docker-compose.yml`
- `docker/Dockerfile.streamlit`
- `docker/.env.example`
- `nosql/init/01_setup_mongo.js`

Validacion:

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env.example config --quiet
```

Resultado: configuracion valida.

### 8.4 Limitacion del host

En este equipo Windows, Docker Desktop no puede ejecutar contenedores porque
`WSLService` y `com.docker.service` estan deshabilitados por permisos del host.
Esto esta documentado en `docs/EVIDENCIA_CUMPLIMIENTO_REAL_2026-05-15.md`. La
configuracion del repositorio es correcta; el bloqueo es del runtime local.

## 9. Rendimiento preliminar

### 9.1 Definicion

La verificacion de rendimiento preliminar mide si el pipeline y las consultas
responden en tiempos razonables. Incluye tiempos de lectura, consultas analiticas,
impacto de indices y comparacion entre carga completa e incremental. En una base
relacional, los indices y restricciones unicas tambien influyen en planes de
consulta y en la forma en que el motor preserva unicidad, por eso se miden junto
con las consultas representativas [R1].

### 9.2 Que se implemento

- `scripts/medir_rendimiento.py`
- `scripts/comparar_sql_nosql_real.py`
- `reports/rendimiento_ultimo.json`
- `reports/sql_vs_nosql_real_ultimo.json`
- `docs/SLA_Y_RENDIMIENTO.md`

### 9.3 Por que se hizo asi

El dashboard necesita consultas rapidas. Por eso se agregaron indices y resumenes
materializados en PostgreSQL y MongoDB. Las mediciones permiten defender que el
sistema no solo carga datos, sino que tambien responde.

## 10. Comandos de demostracion EC3

```bash
python -m pytest tests -q
python scripts/verificar_utec.py
python scripts/medir_rendimiento.py
docker compose -f docker/docker-compose.yml --env-file docker/.env.example config --quiet
python -m streamlit run dashboard/app.py --server.port 8501 --server.headless true
```

## 11. Trazabilidad de entregables EC3

| Entregable EC3 | Evidencia |
|---|---|
| Sistema funcional ejecutable | `dashboard/app.py`, `etl/`, `scripts/verificar_utec.py` |
| ETL modular Python | `etl/extract/`, `etl/transform/`, `etl/load/`, `etl/scheduler.py` |
| SQL integrado | `sql/ddl/`, `etl/load/load_postgres.py` |
| NoSQL integrado | `nosql/schemas/`, `etl/load/load_mongo.py` |
| CDC operativo | `etl/scheduler.py`, `tests/test_calidad_datos.py` |
| Seguridad | `sql/ddl/01_roles.sql`, `config/settings.py`, `.env.example` |
| Dashboard Streamlit | `dashboard/app.py`, `dashboard/db.py` |
| Metricas preliminares | `reports/rendimiento_ultimo.json` |
| Docker | `docker/docker-compose.yml`, `docker/Dockerfile.streamlit` |
| Testing calidad | `tests/test_calidad_datos.py` |
| Evidencia idempotencia | `tests/resultados_tests.json` |
| Validacion CDC | `tests/resultados_tests.json` |
| Logs estructurados | `logs/sinia_2026-05-15.json` |
| Gobernanza | `docs/SEGURIDAD_BACKUP_GOBERNANZA.md` |
| Arquitectura hibrida | `docs/DESPLIEGUE_HIBRIDO.md`, `reports/utec_verificacion_ultimo.json` |

## 12. Conclusion

La Etapa 3 queda cumplida porque el proyecto no se limita a una propuesta
conceptual. Existe una implementacion real con datos reales, persistencia SQL y
NoSQL, ETL modular, CDC, validacion cuantitativa, seguridad, dashboard funcional,
despliegue hibrido y mediciones preliminares.

La idea central para defender EC3 es:

> El sistema funciona de punta a punta: ingesta datos reales, los transforma, los
> carga de forma idempotente en PostgreSQL y MongoDB, registra trazabilidad,
> valida calidad y CDC con tests, expone resultados en Streamlit y deja evidencia
> reproducible del despliegue y rendimiento.

## Referencias bibliograficas y tecnicas

| ID | Fuente | Uso en el documento |
|---|---|---|
| R1 | PostgreSQL Documentation - `CREATE TABLE`: https://www.postgresql.org/docs/current/sql-createtable.html | Modelo relacional, constraints, primary key, unique e indices asociados |
| R2 | MongoDB Manual - Documents: https://www.mongodb.com/docs/current/core/document/ | Modelo documental, documentos BSON, colecciones y campo `_id` |
| R3 | AWS - What is ETL?: https://aws.amazon.com/what-is/etl/ | Definicion de ETL y repositorio central analitico |
| R4 | Python Documentation - `logging`: https://docs.python.org/3/library/logging.html | Logging estructurado, loggers y handlers |
| R5 | Debezium Documentation: https://debezium.io/documentation/reference/stable/index.html | Concepto de CDC y captura de cambios de base de datos |
| R6 | Great Expectations - Expectations overview: https://docs.greatexpectations.io/docs/cloud/expectations/expectations_overview/ | Testing de calidad de datos mediante expectativas verificables |
| R7 | NIST CSRC - Least Privilege: https://csrc.nist.gov/glossary/term/least_privilege | Principio de privilegio minimo |
| R8 | PostgreSQL Documentation - Privileges: https://www.postgresql.org/docs/current/ddl-priv.html | Roles, grants y privilegios de base de datos |
| R9 | Streamlit Documentation: https://docs.streamlit.io/ | Definicion de Streamlit como framework Python para data apps |
| R10 | Docker Compose Documentation: https://docs.docker.com/compose/ | Definicion de Compose y servicios multicontenedor |
