# Guia de estudio para defensa - Proceso completo SINIA-UY

Fecha de preparacion: 2026-05-15

Esta guia explica el proyecto desde el principio hasta el final: que se hizo,
como se hizo, por que se hizo y para que sirve cada parte.

## 1. Idea general del proyecto

El proyecto SINIA-UY es un sistema de ingenieria de datos para monitoreo de
riesgo ambiental e incendios en Uruguay y la region.

El sistema integra varias fuentes externas:

- FIRMS/NASA: focos de calor detectados por satelite.
- Open-Meteo: datos meteorologicos historicos y pronostico.
- CAMS/Copernicus: calidad de aire, principalmente PM10.
- CHIRPS: precipitacion.
- MODIS: cobertura vegetal.

La idea central es tomar datos crudos desde APIs o archivos, limpiarlos,
transformarlos, cargarlos en bases de datos y mostrarlos en un dashboard.

El flujo general es:

```text
Fuentes externas
    -> Extraccion
    -> Datos raw
    -> Transformacion
    -> Datos procesados
    -> Carga PostgreSQL / MongoDB
    -> Consultas SQL / NoSQL
    -> Dashboard Streamlit
    -> Verificacion, tests y sincronizacion UTEC
```

## 2. Para que se hizo

El objetivo academico y tecnico fue demostrar un pipeline completo de datos:

- Ingesta de datos desde fuentes reales.
- Procesamiento ETL.
- Uso de base relacional PostgreSQL.
- Uso de base NoSQL MongoDB.
- Automatizacion de cargas incrementales.
- Validacion de calidad de datos.
- Dashboard analitico y operativo.
- Despliegue local y sincronizacion con servidor UTEC.
- Evidencia de rendimiento, gobernanza, seguridad, replicacion y sharding.

En terminos practicos, el sistema permite responder preguntas como:

- Donde hay focos de calor recientes?
- Cuales son los paises o zonas mas afectadas?
- Que riesgo meteorologico hay para los proximos dias?
- Como esta la calidad del aire?
- El sistema esta actualizado en tiempo real?
- La base del servidor esta sincronizada?

## 3. Estructura principal del proyecto

Las carpetas mas importantes son:

| Carpeta | Funcion |
|---|---|
| `etl/extract` | Extrae datos desde APIs o archivos externos |
| `etl/transform` | Limpia, normaliza y calcula variables derivadas |
| `etl/load` | Carga datos a PostgreSQL y MongoDB |
| `etl/scheduler.py` | Automatiza cargas periodicas |
| `dashboard` | Aplicacion Streamlit para visualizar datos |
| `sql/ddl` | Definicion de tablas, vistas y estructuras SQL |
| `sql/dml` | Datos iniciales y scripts de limpieza |
| `nosql/schemas` | JSON Schema para MongoDB |
| `tests` | Tests de calidad, consistencia, idempotencia y CDC |
| `docs` | Documentacion tecnica y material de defensa |
| `reports` | Resultados de rendimiento y simulaciones |
| `data/raw` | Datos descargados sin procesar |
| `data/processed` | Datos limpios en formato parquet |

## 4. Fuentes de datos usadas

### 4.1 FIRMS/NASA

FIRMS es la fuente de focos de calor. Entrega observaciones satelitales con:

- latitud y longitud;
- fecha y hora de adquisicion;
- satelite;
- potencia radiativa del fuego;
- confianza de deteccion;
- indicador dia/noche.

Por que se uso:

- Es una fuente real y publica.
- Sirve directamente para monitoreo de incendios.
- Permite trabajar con datos historicos y datos casi en tiempo real.

Para que sirve en el sistema:

- Alimenta mapas de focos.
- Permite contar focos por pais, fecha y periodo.
- Es la base de los snapshots MongoDB.
- Es una fuente clave para el dashboard de tiempo real.

### 4.2 Open-Meteo

Open-Meteo se usa para datos meteorologicos historicos y pronostico:

- temperatura maxima;
- humedad relativa;
- viento;
- precipitacion;
- variables para calcular indice de riesgo.

Por que se uso:

- El riesgo de incendio no depende solo de focos ya detectados.
- Tambien importa si las condiciones climaticas favorecen incendios.

Para que sirve:

- Calcular `indice_riesgo`.
- Clasificar el riesgo como bajo, medio, alto o muy alto.
- Mostrar pronostico de riesgo para 7 dias.

### 4.3 CAMS/Copernicus

CAMS aporta datos de calidad de aire, especialmente PM10.

Por que se uso:

- Los incendios afectan la calidad del aire.
- Permite complementar el analisis ambiental.

Para que sirve:

- Mostrar niveles diarios de PM10.
- Relacionar contaminacion con eventos ambientales.
- Agregar otra dimension al dashboard.

### 4.4 CHIRPS y MODIS

CHIRPS se usa para precipitacion y MODIS para cobertura vegetal.

Por que se usaron:

- La lluvia reduce riesgo de incendios.
- La vegetacion es combustible potencial.

Para que sirven:

- Enriquecer el modelo ambiental.
- Cumplir con integracion de multiples fuentes.
- Dar contexto territorial.

## 5. Etapa de extraccion

La extraccion es la primera parte del ETL. Su trabajo es traer datos desde
fuentes externas y guardarlos como datos crudos.

Archivos principales:

- `etl/extract/extract_firms.py`
- `etl/extract/extract_forecast.py`
- `etl/extract/extract_meteo.py`
- `etl/extract/extract_cams.py`
- `etl/extract/extract_chirps.py`
- `etl/extract/extract_modis.py`

Que se hizo:

- Se conectaron APIs externas.
- Se descargaron datos para puntos de monitoreo o regiones definidas.
- Se guardaron resultados en `data/raw`.
- Se separo la extraccion historica de la extraccion NRT.

Por que se hizo asi:

- Los datos raw son evidencia de lo descargado.
- Permiten reprocesar sin volver a llamar APIs.
- Separar raw y processed es una buena practica de ingenieria de datos.

Ejemplo de defensa:

> En la etapa de extraccion no modificamos el significado de los datos. Solo los
> traemos desde las fuentes y los conservamos en formato crudo para tener
> trazabilidad y posibilidad de reproceso.

## 6. Etapa de transformacion

La transformacion convierte datos crudos en datos limpios y consistentes.

Archivos principales:

- `etl/transform/transform_firms.py`
- `etl/transform/transform_meteo.py`
- `etl/transform/transform_cams.py`
- `etl/transform/transform_chirps.py`
- `etl/transform/transform_modis.py`

Que se hizo:

- Normalizacion de nombres de columnas.
- Conversion de fechas.
- Conversion de tipos numericos.
- Filtro geografico a paises de interes.
- Eliminacion de duplicados.
- Calculo de variables derivadas.
- Guardado en formato parquet.

Por que parquet:

- Es eficiente para lectura analitica.
- Conserva tipos de datos mejor que CSV.
- Permite trabajar localmente aunque la base este apagada.
- Sirve como capa intermedia entre raw y base de datos.

### 6.1 Transformacion FIRMS

Se limpiaron focos de calor:

- coordenadas;
- fecha/hora;
- pais;
- confianza;
- potencia radiativa;
- satelite;
- indicador diurno/nocturno.

Tambien se controlo que los focos estuvieran dentro del alcance regional.

Para que:

- Evitar cargar datos fuera del dominio del proyecto.
- Tener claves consistentes para detectar duplicados.
- Alimentar mapas y conteos del dashboard.

### 6.2 Transformacion meteorologica

Se calcularon indicadores de riesgo:

- temperatura alta aumenta riesgo;
- humedad baja aumenta riesgo;
- viento alto aumenta riesgo;
- lluvia reduce riesgo.

Resultado importante:

- `indice_riesgo`: valor numerico entre 0 y 1.
- `nivel_riesgo`: categoria legible para dashboard.

Para que:

- Pasar de datos climaticos sueltos a una metrica de decision.
- Mostrar riesgo futuro, no solo eventos pasados.

### 6.3 Transformacion CAMS

Se procesaron datos de PM10:

- promedio diario;
- nivel de contaminacion;
- consistencia temporal.

Para que:

- Incorporar calidad de aire al monitoreo ambiental.

## 7. Carga en PostgreSQL

PostgreSQL es la base relacional principal del proyecto.

Archivo principal:

- `etl/load/load_postgres.py`

Tablas principales:

- `focos_calor`
- `meteo_diario`
- `calidad_aire_diario`
- `precipitacion_diaria`
- `cobertura_vegetal`
- `puntos_monitoreo`
- `etl_ejecuciones`

Que se hizo:

- Se cargaron datos procesados desde parquet.
- Se aplicaron cargas idempotentes.
- Se registraron ejecuciones ETL.
- Se crearon vistas para consultas del dashboard.

### 7.1 Que significa idempotencia

Idempotencia significa que si ejecuto la misma carga dos veces, no duplico datos.

Por que es importante:

- En sistemas reales puede fallar una ejecucion y repetirse.
- El scheduler puede correr varias veces.
- La nube y local pueden resincronizar datos.

Como se hizo:

- Se usan claves naturales o restricciones unicas.
- La carga detecta registros nuevos, modificados y sin cambio.
- Se reportan metricas como insertados, actualizados y sin cambio.

Ejemplo de defensa:

> El pipeline es idempotente porque repetir una carga no duplica datos. Esto es
> fundamental para un sistema incremental y automatizado.

### 7.2 Por que PostgreSQL

PostgreSQL se uso porque:

- Tiene integridad relacional.
- Permite SQL complejo.
- Sirve para analisis historico.
- Soporta vistas.
- Es ideal para dashboard analitico.

En este proyecto PostgreSQL responde preguntas estructuradas:

- focos por pais y mes;
- riesgo por punto;
- dias criticos;
- resumen de calidad de aire;
- conteos recientes.

## 8. Carga en MongoDB

MongoDB se uso como base NoSQL complementaria.

Archivo principal:

- `etl/load/load_mongo.py`

Colecciones:

- `focos_snapshots`
- `ejecuciones_etl`
- `alertas`
- `eventos`

### 8.1 Por que MongoDB

MongoDB se eligio porque algunos datos son documentos flexibles:

- logs ETL con metricas variables;
- alertas con estructuras semi-estructuradas;
- snapshots diarios con listas embebidas de focos.

No se uso MongoDB para reemplazar PostgreSQL. Se uso para complementar.

Ejemplo:

PostgreSQL guarda focos como filas normalizadas.

MongoDB guarda un documento por dia:

```text
fecha: 2026-05-15
total_focos: 303
resumen: {...}
focos: [
  {latitud, longitud, hora, satelite, confianza},
  ...
]
```

Para que sirve:

- Consultar rapido el estado completo de un dia.
- Evitar joins cuando se necesita un snapshot operativo.
- Modelar eventos y alertas con flexibilidad.

### 8.2 Validadores JSON Schema

Se definieron schemas para las colecciones MongoDB.

Para que:

- Documentar estructura esperada.
- Mejorar gobernanza.
- Evitar documentos mal formados.

Detalle actual:

- En local se pueden crear y usar schemas.
- En UTEC el usuario puede leer/escribir datos.
- Falta permiso `collMod` para modificar validadores en colecciones ya existentes.
- Ya se solicito ese permiso al encargado del servidor.

## 9. Scheduler y tiempo real

Archivo principal:

- `etl/scheduler.py`

El scheduler automatiza ejecuciones incrementales.

Jobs principales:

| Job | Funcion | Frecuencia |
|---|---|---|
| `job_firms_nrt` | Descarga focos recientes FIRMS | cada 3 horas |
| `job_pronostico` | Descarga forecast Open-Meteo | cada 1 hora |
| `job_cams` | Actualiza calidad de aire CAMS | cada 1 hora |
| `job_chirps_mensual` | Actualiza precipitacion | cada 30 dias |

Que se corrigio:

- FIRMS NRT pedia 7 dias, pero NASA acepta maximo 5.
- Se ajusto a 5 dias.
- Se corrigio un caracter Unicode en logs que daba problema en Windows.

Por que se hizo:

- Para que el sistema trabaje con datos recientes.
- Para no depender de ejecuciones manuales.
- Para simular un sistema operativo real.

Estado final local:

- Scheduler corriendo.
- Dashboard corriendo.
- PostgreSQL actualizado.
- MongoDB local levantado.
- Tests verdes.

## 10. Dashboard

Carpeta principal:

- `dashboard`

Archivos importantes:

- `dashboard/app.py`
- `dashboard/db.py`

El dashboard esta hecho con Streamlit.

Que muestra:

- resumen general;
- mapa de focos;
- focos en tiempo real;
- riesgo meteorologico;
- forecast;
- calidad de aire;
- consultas analiticas.

### 10.1 Como obtiene datos

El dashboard intenta leer desde PostgreSQL.

Si no puede, usa parquet como respaldo.

Por que:

- PostgreSQL es la fuente operativa principal.
- Parquet permite que el dashboard no quede completamente inutil si la base no esta disponible.

### 10.2 Correcciones hechas

Se corrigio `dashboard/db.py`:

- Algunas consultas tenian `SQL_SCOPE_PAISES` sin interpolar.
- Eso hacia que fallaran y el dashboard cayera a parquet.
- Se corrigio para que consulte PostgreSQL correctamente.

Tambien se mejoro `cargar_focos_nrt`:

- Ahora lee primero focos recientes desde PostgreSQL.
- Si no hay conexion, usa `firms_nrt_procesado.parquet`.

Se corrigio `dashboard/app.py`:

- Un marcador vertical de Plotly daba error con fechas.
- Se cambio por `add_shape` y `add_annotation`.

Resultado:

- Dashboard abre en `http://localhost:8501`.
- No muestra traceback.
- Consume datos actualizados.

## 11. Sincronizacion con UTEC

El proyecto tiene configuracion para servidor UTEC.

Servidor:

- PostgreSQL UTEC: `10.200.245.40:15434`
- MongoDB UTEC: `10.200.245.40:27023`
- Base: `grp03db`

### 11.1 Estado inicial UTEC corregido

Antes del cierre final, UTEC estaba accesible pero mezclaba el alcance historico
anterior con el alcance actual del proyecto:

- PostgreSQL tenia datos de paises fuera del alcance final (`BOL`, `CHL`, `PER`, `PRY`, `OTR`).
- MongoDB tenia snapshots sin `pais` embebido, por lo que no servian para resumenes reales por pais.
- Las vistas materializadas finales aun no existian.

Conclusion inicial:

> El servidor estaba disponible, pero necesitaba limpieza de alcance,
> recarga documental real y materializacion de agregados.

### 11.2 Que se cargo en UTEC

En PostgreSQL UTEC:

- Limpieza de alcance a `URY`, `BRA`, `ARG`.
- Conservacion de datos historicos validos y NRT hasta `2026-05-15`.
- Creacion de `mv_focos_por_pais` y `mv_focos_por_pais_mes`.

En MongoDB UTEC:

- Eliminacion de snapshots viejos sin `pais` embebido.
- Recarga de `347` snapshots historicos y `5` snapshots NRT.
- Materializacion de `focos_resumen_pais` y `focos_resumen_mes`.
- 1 ejecucion ETL registrada para la carga final.

### 11.3 Estado final UTEC

PostgreSQL UTEC:

- `focos_calor`: `1.841.820`, datos hasta `2026-05-15`.
- FIRMS NRT ultimos 5 dias: `5283`.
- `mv_focos_por_pais`: `3`.
- `mv_focos_por_pais_mes`: `39`.

MongoDB UTEC:

- `focos_snapshots`: `352`.
- `snapshots_con_pais`: `352`.
- `snapshots_sin_pais`: `0`.
- `focos_resumen_pais`: `3`.
- `focos_resumen_mes`: `39`.
- Ultimo snapshot: `2026-05-15`.
- Focos en ultimo snapshot: `303`.
- Ultima ejecucion Mongo: `firms_nrt/load`, estado `ok`.

Decision importante:

- Se corrigio el alcance real del servidor.
- Se recargo MongoDB con documentos reales y consultables por pais.
- La evidencia quedo versionada en `reports/utec_verificacion_ultimo.json` y `reports/utec_sync_ultimo.json`.

## 12. Pruebas de calidad

Archivo:

- `tests/test_calidad_datos.py`

Resultado final:

```text
17 PASS / 0 FAIL
```

Que se valido:

- Completitud: campos criticos no nulos.
- Unicidad: no duplicados.
- Consistencia: rangos validos.
- Validez: dominios permitidos.
- Idempotencia: doble carga no duplica.
- CDC: deteccion de cambios y nuevos registros.

### 12.1 Por que son importantes

Los tests demuestran que el pipeline no solo corre, sino que produce datos
confiables.

Ejemplo de defensa:

> Las pruebas verifican calidad de datos antes de confiar en el dashboard. No
> alcanza con visualizar informacion; hay que demostrar que los datos son
> completos, consistentes, unicos e idempotentes.

## 13. CDC

CDC significa Change Data Capture.

En el proyecto se usa para detectar:

- registros nuevos;
- registros modificados;
- registros sin cambio.

Para que sirve:

- Evitar recargar todo innecesariamente.
- Actualizar solo lo necesario.
- Mantener trazabilidad de cambios.

Ejemplo:

Si un registro meteorologico ya existe pero cambia el indice de riesgo, el
sistema lo puede actualizar. Si no cambio, lo deja igual.

## 14. Vistas SQL y consultas

Las vistas SQL preparan datos para el dashboard y la defensa.

Archivo principal:

- `sql/ddl/04_vistas.sql`

Para que sirven:

- Simplificar consultas complejas.
- Evitar repetir logica en dashboard.
- Mejorar legibilidad.
- Separar logica analitica de la interfaz.

Ejemplos de vistas o consultas:

- focos por pais y mes;
- dias criticos;
- riesgo por pais;
- resumen por punto de monitoreo.

## 15. Rendimiento, replicacion y sharding

Se agregaron evidencias de rendimiento y diseno distribuido.

Archivos:

- `scripts/medir_rendimiento.py`
- `scripts/simular_sharding.py`
- `docs/SLA_Y_RENDIMIENTO.md`
- `docs/REPLICACION_Y_SHARDING.md`

### 15.1 Rendimiento

Se midio:

- tiempo de consultas;
- volumen de filas;
- comportamiento de cargas;
- evidencia para SLA.

Para que:

- Mostrar que el sistema no es solo conceptual.
- Tener datos para justificar decisiones.

### 15.2 Replicacion

La replicacion se documento como estrategia de disponibilidad:

- base local para desarrollo;
- base UTEC como servidor compartido;
- sincronizacion incremental.

### 15.3 Sharding

El sharding se simulo para explicar como se podria particionar el crecimiento:

- por pais;
- por fecha;
- por tipo de fuente.

Para que:

- Mostrar escalabilidad futura.
- Responder requerimientos de arquitectura distribuida.

## 16. Seguridad, backup y gobernanza

Documentacion relacionada:

- `docs/SEGURIDAD_BACKUP_GOBERNANZA.md`
- `docs/DESPLIEGUE_HIBRIDO.md`

Que se hizo o documento:

- Uso de archivos `.env` para credenciales.
- Separacion de configuracion local y UTEC.
- No exponer contrasenas en documentacion.
- Backups y restauracion como practica recomendada.
- Validadores JSON Schema en MongoDB.
- Tests de calidad como control de gobernanza.

Idea para defensa:

> Gobernanza no es solo permisos. Tambien incluye calidad, trazabilidad,
> documentacion, esquemas, logs y capacidad de auditar ejecuciones.

## 17. Que problemas aparecieron y como se resolvieron

### Problema 1: Dashboard no usaba bien PostgreSQL

Causa:

- Consultas con variable SQL sin interpolar.

Solucion:

- Se corrigieron las cadenas SQL.
- El dashboard ahora consulta PostgreSQL correctamente.

### Problema 2: FIRMS NRT fallaba

Causa:

- NASA FIRMS acepta hasta 5 dias.
- El scheduler pedia 7.

Solucion:

- Se ajusto el maximo a 5 dias.

### Problema 3: Error de Plotly en fecha vertical

Causa:

- `add_vline` tenia problema con tipo de fecha.

Solucion:

- Se cambio a `add_shape` y `add_annotation`.

### Problema 4: MongoDB local no estaba como servicio

Causa:

- Servicio Windows detenido/deshabilitado.

Solucion:

- Se levanto `mongod.exe` como proceso local.

Estado final:

- Docker Compose esta configurado y validado.
- En este host Windows la ejecucion de Docker depende de habilitar `WSLService` y `com.docker.service`.

### Problema 5: Permisos MongoDB UTEC

Causa:

- El usuario de UTEC necesitaba permisos suficientes para actualizar validadores.

Solucion:

- Se verifico acceso a MongoDB UTEC con el usuario `grp03`.
- `crear_bases_datos.py --base-existente` actualizo validadores e indices.
- MongoDB quedo con `352` snapshots reales, todos con `pais` embebido.

## 18. Estado final del sistema

Local:

- Dashboard funcionando en `localhost:8501`.
- PostgreSQL funcionando.
- MongoDB funcionando como proceso local.
- Scheduler corriendo.
- Datos recientes cargados.
- Tests: `17 PASS / 0 FAIL`.

UTEC:

- PostgreSQL actualizado con datos recientes al `2026-05-15`.
- MongoDB actualizado con historico y NRT al `2026-05-15`.
- Validadores, indices y resumenes materializados verificados.

## 19. Como explicarlo en la defensa

Una forma clara de explicarlo:

> El proyecto implementa un pipeline ETL completo para monitoreo ambiental.
> Primero extraemos datos reales desde FIRMS, Open-Meteo, CAMS, CHIRPS y MODIS.
> Luego los transformamos para limpiar fechas, tipos, duplicados, paises y
> calcular indicadores como el indice de riesgo. Despues cargamos los datos en
> PostgreSQL para analisis estructurado y en MongoDB para documentos flexibles
> como snapshots, alertas y logs. Finalmente el dashboard consulta PostgreSQL y
> muestra focos, riesgo, forecast y calidad de aire. El scheduler automatiza
> cargas incrementales y los tests validan calidad, unicidad, idempotencia y CDC.

Si preguntan por que dos bases:

> PostgreSQL se usa para datos tabulares, historicos y consultas SQL. MongoDB se
> usa para documentos flexibles, como snapshots diarios con arrays de focos,
> logs ETL y alertas. No compiten; se complementan.

Si preguntan por tiempo real:

> El sistema trabaja con cargas incrementales programadas. FIRMS NRT se actualiza
> cada 3 horas, forecast y CAMS cada 1 hora. El dashboard lee esos datos desde
> PostgreSQL y usa parquet como respaldo.

Si preguntan por calidad:

> Se implementaron tests de completitud, unicidad, consistencia, validez,
> idempotencia y CDC. La ultima ejecucion dio 17 PASS y 0 FAIL.

Si preguntan por UTEC:

> Se verifico que el servidor estaba accesible pero no actualizado. Luego se
> corrigio el alcance a Uruguay, Brasil y Argentina, se materializaron resumenes
> SQL y se recargo MongoDB con snapshots historicos y NRT reales. Al final UTEC
> quedo con datos hasta el 15 de mayo de 2026 y evidencia en reportes versionados.

## 20. Preguntas probables y respuestas cortas

### Que es ETL?

ETL significa Extract, Transform, Load. Primero extraemos datos, luego los
limpiamos y transformamos, y finalmente los cargamos en bases de datos.

### Por que usan parquet?

Porque es eficiente, conserva tipos de datos y funciona como capa intermedia
entre los datos crudos y las bases.

### Que es idempotencia?

Que repetir una carga no duplica datos. Es clave para procesos automatizados.

### Que es CDC?

Es deteccion de cambios. Permite saber si un registro es nuevo, cambio o sigue
igual.

### Por que PostgreSQL?

Porque permite integridad, SQL, vistas y analisis estructurado.

### Por que MongoDB?

Porque permite documentos flexibles, snapshots diarios, alertas y logs con
estructura variable.

### Que significa tiempo real en este proyecto?

Significa actualizacion periodica e incremental con datos NRT, no streaming puro
segundo a segundo. FIRMS NRT, forecast y CAMS se actualizan automaticamente.

### Que limitacion operativa queda?

Docker Desktop no puede iniciar en este host Windows porque `WSLService` y
`com.docker.service` estan deshabilitados por permisos del sistema. El repositorio
tiene Compose validado; los datos, dashboard, UTEC y tests ya estan operativos.

## 21. Orden recomendado para estudiar

1. Entender el objetivo del proyecto.
2. Estudiar fuentes de datos.
3. Seguir el flujo ETL: extract, transform, load.
4. Entender PostgreSQL y sus tablas.
5. Entender MongoDB y sus colecciones.
6. Revisar scheduler y tiempo real.
7. Revisar dashboard.
8. Estudiar tests y calidad.
9. Estudiar sincronizacion UTEC.
10. Practicar respuestas cortas de defensa.

## 22. Frase final para cerrar la defensa

> El proyecto demuestra un ciclo completo de ingenieria de datos: integra
> fuentes reales, procesa datos historicos y recientes, los almacena en modelos
> relacional y documental, automatiza actualizaciones, valida calidad y ofrece
> visualizacion operativa mediante dashboard. Ademas, fue verificado localmente
> y sincronizado con el servidor UTEC.
