# Guia tecnica completa para defensa - SINIA-UY

Fecha de referencia: 2026-05-22.

Esta guia explica el proyecto desde cero: que problema resuelve, que se hizo, como se hizo, con que tecnologias, por que se eligio cada componente, como son las bases de datos, como fluye el dato, como se valida y que responder si el tribunal pregunta detalle por detalle.

## 1. Resumen en una frase

SINIA-UY es un sistema de ingenieria de datos que integra fuentes ambientales reales, las procesa con un ETL modular en Python, guarda datos estructurados en PostgreSQL y datos operacionales/flexibles en MongoDB, valida calidad, idempotencia y CDC, y expone resultados en un dashboard Streamlit.

## 2. Problema que resuelve

El problema no es la falta de datos, sino su dispersion.

Hay focos de calor en NASA FIRMS, meteorologia y pronostico en Open-Meteo, calidad del aire CAMS via Open-Meteo, precipitacion CHIRPS y cobertura vegetal MODIS/AppEEARS. Cada fuente viene con formato, granularidad y semantica distinta. El proyecto convierte esas fuentes heterogeneas en un sistema integrado, consultable y reproducible.

La pregunta de negocio/analitica es:

> Como monitorear riesgo de incendios, focos de calor y condiciones ambientales relevantes para Uruguay y la region usando datos reales, trazables y actualizables.

## 3. Alcance geografico

El alcance actual es de cuatro paises y 36 puntos de monitoreo:

| Pais | Puntos | Justificacion |
|---|---:|---|
| Uruguay | 19 | Cobertura nacional completa por capital/departamental |
| Brasil | 5 | Fuente regional importante de focos y humo transfronterizo |
| Argentina | 4 | Pais limitrofe y comparativo directo |
| Chile | 8 | Eventos volcanicos y transporte atmosferico regional |

Los codigos usados son ISO alpha-3: `URY`, `BRA`, `ARG`, `CHL`.

Chile se justifica por eventos volcanicos documentados como Puyehue-Cordon Caulle y Calbuco, cuyas cenizas tuvieron impacto regional. No se agrega por incendios solamente, sino por calidad del aire y transporte atmosferico.

## 4. Arquitectura general

Flujo conceptual:

```text
Fuentes externas
  -> Extractores Python
  -> Transformaciones pandas
  -> Archivos Parquet procesados
  -> Carga PostgreSQL
  -> Carga MongoDB
  -> Tests y reportes
  -> Dashboard Streamlit
```

Por que esta arquitectura:

- Python permite integrar APIs, archivos, transformaciones y cargas con el mismo lenguaje.
- pandas permite limpiar, normalizar y agregar datos tabulares.
- Parquet es eficiente para datos analiticos: conserva tipos, comprime bien y carga rapido.
- PostgreSQL asegura integridad, relaciones, SQL, vistas, indices y consultas analiticas.
- MongoDB permite documentos flexibles, snapshots diarios y alertas sin forzar un esquema tabular.
- Streamlit permite construir un dashboard rapido y defendible en Python.
- Docker Compose documenta la infraestructura local reproducible.

## 5. Carpetas principales

| Carpeta | Rol |
|---|---|
| `config/` | Configuracion central, rutas, credenciales por entorno, puntos y paises |
| `etl/extract/` | Descarga datos desde fuentes externas |
| `etl/transform/` | Limpia, normaliza, calcula variables y guarda Parquet |
| `etl/load/` | Carga datos a PostgreSQL y MongoDB |
| `etl/scheduler.py` | Ejecuta cargas incrementales automaticamente |
| `sql/ddl/` | Modelo SQL, roles, tablas, indices, vistas |
| `nosql/` | Schemas, inicializacion y consultas MongoDB |
| `dashboard/` | Streamlit y capa de acceso a datos |
| `tests/` | Pruebas de calidad, idempotencia y CDC |
| `reports/` | Evidencia reproducible de cargas, rendimiento y validaciones |
| `docs/` | Documentacion de entrega, defensa, despliegue y cumplimiento |

## 6. Fuentes de datos

| Fuente | Que aporta | Uso en el sistema |
|---|---|---|
| NASA FIRMS | Focos de calor satelitales | Tabla `focos_calor`, mapas y series de incendios |
| Open-Meteo Archive | Meteorologia historica | Tabla `meteo_diario`, indice de riesgo |
| Open-Meteo Forecast | Pronostico | Riesgo futuro en `meteo_diario` con `tipo_dato='forecast'` |
| CAMS via Open-Meteo | Calidad del aire, PM10, PM2.5, AQI | Tabla `calidad_aire_diario` |
| CHIRPS | Precipitacion mensual | Tabla `precipitacion_mensual` |
| MODIS/AppEEARS | Cobertura vegetal anual | Tabla `cobertura_vegetal` |

## 7. Configuracion central

Archivo: `config/settings.py`.

Este archivo evita valores dispersos en el codigo. Define:

- rutas del proyecto;
- URLs de APIs;
- credenciales leidas desde `.env`;
- configuracion PostgreSQL;
- configuracion MongoDB;
- paises del alcance;
- 36 puntos de monitoreo;
- pesos del indice de riesgo.

Concepto importante:

`.env` guarda secretos fuera del codigo. `.env.example` documenta que variables se necesitan sin exponer claves reales. Esto cumple seguridad basica y reproducibilidad.

## 8. ETL: que es y como esta implementado

ETL significa Extract, Transform, Load.

- Extract: obtener datos desde la fuente.
- Transform: convertirlos a un formato limpio, tipado y comparable.
- Load: cargarlos a las bases de datos destino.

En el proyecto:

| Etapa | Carpeta | Ejemplo |
|---|---|---|
| Extract | `etl/extract/` | `extract_firms.py`, `extract_meteo.py`, `extract_cams.py` |
| Transform | `etl/transform/` | `transform_firms.py`, `transform_meteo.py`, `transform_cams.py` |
| Load | `etl/load/` | `load_postgres.py`, `load_mongo.py` |

La separacion es importante porque permite probar cada etapa, cambiar una fuente sin romper todo, y defender el pipeline como modular.

## 9. Transformaciones principales

### FIRMS

Archivo: `etl/transform/transform_firms.py`.

Entrada: datos crudos NASA FIRMS.

Salida: `data/processed/firms_procesado.parquet`.

Columnas reales principales:

| Columna | Tipo | Significado |
|---|---|---|
| `latitud` | float | Coordenada del foco |
| `longitud` | float | Coordenada del foco |
| `fecha_adq` | datetime | Fecha de adquisicion satelital |
| `hora_adq_hhmm` | int | Hora HHMM de deteccion |
| `satelite` | string | Satelite que detecto el foco |
| `instrumento` | string | Sensor, por ejemplo VIIRS |
| `confianza_raw` | string | Confianza original `l/n/h` |
| `confianza_num` | int | Confianza normalizada: 1 baja, 2 nominal, 3 alta |
| `potencia_radiativa` | float | FRP, potencia radiativa del fuego |
| `dia_noche` | string | `D` o `N` |
| `es_diurno` | bool | Derivado para analisis |
| `pais` | string | Pais asignado por bounding box |

Por que se transforma:

- Se normalizan nombres y tipos.
- Se asigna pais para analisis regional.
- Se convierte confianza textual a numerica.
- Se deja una clave natural para evitar duplicados.

### Meteorologia

Archivo: `etl/transform/transform_meteo.py`.

Salida: `data/processed/meteo_procesado_todos.parquet`.

Columnas principales:

| Columna | Significado |
|---|---|
| `fecha` | Dia observado |
| `punto` | Punto de monitoreo |
| `latitud`, `longitud` | Coordenadas |
| `temperature_2m_max/min` | Temperatura diaria |
| `relative_humidity_2m_min/max` | Humedad relativa |
| `wind_speed_10m_max` | Viento maximo |
| `precipitation_sum` | Lluvia diaria |
| `et0_fao_evapotranspiration` | Evapotranspiracion |
| `riesgo_temp` | Componente normalizado por temperatura |
| `riesgo_humedad` | Componente normalizado por baja humedad |
| `riesgo_viento` | Componente normalizado por viento |
| `riesgo_sequia` | Componente normalizado por sequedad/evapotranspiracion |
| `indice_riesgo` | Resultado final entre 0 y 1 |
| `nivel_riesgo` | Bajo, moderado, alto, muy alto |

Indice de riesgo:

```text
indice_riesgo =
  riesgo_temp * 0.25
  + riesgo_humedad * 0.30
  + riesgo_viento * 0.20
  + riesgo_sequia * 0.25
```

Justificacion:

- temperatura alta aumenta inflamabilidad;
- baja humedad seca combustible;
- viento propaga incendios;
- sequia/evapotranspiracion refleja estres hidrico.

### CAMS/calidad de aire

Archivo: `etl/transform/transform_cams.py`.

Salida: `data/processed/cams_procesado_todos.parquet`.

Columnas:

| Columna | Significado |
|---|---|
| `fecha` | Dia |
| `punto` | Punto de monitoreo |
| `pm10_media`, `pm10_max`, `pm10_p95` | Material particulado PM10 |
| `pm2_5_media`, `pm2_5_max` | PM2.5 |
| `aerosol_optical_depth_media` | Carga de aerosoles |
| `european_aqi_media/max` | Indice europeo de calidad del aire |
| `horas_validas` | Horas del dia con dato valido |
| `supera_oms_pm10` | Si supera umbral OMS |
| `nivel_pm10` | normal, elevado, alerta |

Por que importa:

Los incendios y cenizas afectan calidad del aire. PM10 permite conectar focos/riesgo con impacto ambiental.

### CHIRPS

Archivo: `etl/transform/transform_chirps.py`.

Salida: `chirps_sa.parquet`.

Uso:

- precipitacion mensual por punto;
- anomalia porcentual;
- deficit hidrico.

Sirve para explicar condiciones de sequia y acumulacion de combustible seco.

### MODIS

Archivo: `etl/transform/transform_modis.py`.

Salida: `modis_lc.parquet`.

Uso:

- tipo de cobertura vegetal anual;
- combustibilidad aproximada del terreno.

Permite justificar que no todos los puntos tienen igual riesgo: una zona urbana no se comporta igual que bosque/pastizal.

## 10. Modelo relacional PostgreSQL

PostgreSQL es la base analitica estructurada. Se usa porque:

- tiene SQL fuerte;
- permite claves primarias y foraneas;
- permite `CHECK`, `UNIQUE`, indices y vistas;
- sirve bien para dashboard y consultas agregadas.

Archivo principal: `sql/ddl/02_schema.sql`.

### 10.1 Tabla `puntos_monitoreo`

Tipo: dimension geografica.

Grano: un registro por punto de monitoreo.

Columnas:

| Columna | Tipo | Explicacion |
|---|---|---|
| `id` | SERIAL PK | Identificador interno |
| `nombre` | VARCHAR(50) UNIQUE | Nombre del punto |
| `pais` | CHAR(3) | Codigo ISO: URY, BRA, ARG, CHL |
| `region` | VARCHAR(80) | Descripcion territorial |
| `latitud` | NUMERIC(9,6) | Coordenada, con `CHECK` |
| `longitud` | NUMERIC(9,6) | Coordenada, con `CHECK` |
| `activo` | BOOLEAN | Permite desactivar sin borrar |
| `creado_en` | TIMESTAMP | Auditoria |

Relacion:

Es referenciada por meteorologia, calidad de aire, precipitacion y cobertura vegetal.

### 10.2 Tabla `focos_calor`

Tipo: tabla de hechos.

Grano: un foco satelital detectado.

Columnas:

| Columna | Tipo | Explicacion |
|---|---|---|
| `id` | BIGSERIAL PK | Identificador interno |
| `fecha_adq` | DATE | Fecha del foco |
| `hora_adq_hhmm` | INTEGER | Hora HHMM |
| `latitud`, `longitud` | NUMERIC | Ubicacion |
| `pais` | CHAR(3) | Pais asignado |
| `potencia_radiativa` | NUMERIC | Intensidad FRP |
| `confianza_raw` | VARCHAR | Valor original |
| `confianza_num` | SMALLINT | 1, 2, 3 |
| `satelite` | VARCHAR | Satelite |
| `instrumento` | VARCHAR | Sensor |
| `dia_noche` | CHAR(1) | D/N |
| `es_diurno` | BOOLEAN | Derivado |
| `brillo_ti4`, `brillo_ti5` | NUMERIC | Temperaturas de brillo |
| `fuente` | VARCHAR | FIRMS |
| `insertado_en` | TIMESTAMP | Auditoria |

Clave natural:

```sql
UNIQUE (latitud, longitud, fecha_adq, hora_adq_hhmm, satelite)
```

Por que:

Un foco se identifica naturalmente por lugar, fecha, hora y satelite. Esto permite idempotencia: si cargo dos veces el mismo archivo, no duplica.

### 10.3 Tabla `meteo_diario`

Tipo: tabla de hechos.

Grano: un dia por punto por tipo de dato.

Columnas clave:

| Columna | Explicacion |
|---|---|
| `fecha` | Dia |
| `id_punto` | FK a `puntos_monitoreo` |
| variables meteorologicas | temperatura, humedad, viento, precipitacion |
| `riesgo_temp/humedad/viento/sequia` | Componentes normalizados |
| `indice_riesgo` | Indice final |
| `nivel_riesgo` | Categoria |
| `tipo_dato` | `historico` o `forecast` |
| `insertado_en`, `actualizado_en` | Auditoria |

Clave natural:

```sql
UNIQUE (fecha, id_punto, tipo_dato)
```

Relacion:

`id_punto` referencia `puntos_monitoreo(id)`.

Por que `tipo_dato`:

El mismo punto y fecha puede existir como historico o forecast. Separarlo evita mezclar observacion pasada con pronostico.

### 10.4 Tabla `calidad_aire_diario`

Tipo: tabla de hechos.

Grano: un dia por punto.

Columnas:

| Columna | Explicacion |
|---|---|
| `fecha` | Dia |
| `id_punto` | FK a punto |
| `pm10_media/max/p95` | Indicadores PM10 |
| `pm2_5_media/max` | Indicadores PM2.5 |
| `aerosol_optical_depth_media` | Aerosoles |
| `european_aqi_media/max` | AQI |
| `horas_validas` | Calidad/cobertura del dato |
| `supera_oms_pm10` | Alerta por umbral |
| `nivel_pm10` | normal/elevado/alerta |

Clave natural:

```sql
UNIQUE (fecha, id_punto)
```

### 10.5 Tabla `etl_ejecuciones`

Tipo: auditoria.

Grano: una ejecucion ETL.

Guarda:

- fuente;
- etapa;
- tipo de carga;
- rango temporal;
- registros procesados;
- insertados;
- actualizados;
- sin cambio;
- estado;
- duracion.

Por que existe:

Permite trazabilidad, auditoria, evidencia de CDC y diagnostico de fallos.

### 10.6 Tabla `paises_referencia`

Tipo: dimension.

Grano: un pais del alcance.

Columnas:

- `codigo_iso3`;
- `codigo_iso2`;
- `nombre`;
- `region`;
- `activo`.

### 10.7 Tabla `precipitacion_mensual`

Tipo: hecho mensual.

Grano: anio + mes + punto.

Clave natural:

```sql
UNIQUE (anio, mes, id_punto)
```

### 10.8 Tabla `cobertura_vegetal`

Tipo: hecho anual.

Grano: anio + punto.

Clave natural:

```sql
UNIQUE (anio, id_punto)
```

Columnas:

- `lc_type1`: codigo IGBP de MODIS;
- `lc_descripcion`: descripcion legible;
- `fuente`: MODIS/AppEEARS.

## 11. Relaciones SQL

Modelo simplificado:

```text
puntos_monitoreo (1)
  -> meteo_diario (N)
  -> calidad_aire_diario (N)
  -> precipitacion_mensual (N)
  -> cobertura_vegetal (N)

focos_calor no usa id_punto porque los focos son eventos georreferenciados libres,
no mediciones tomadas exactamente en un punto.
```

Por que `focos_calor` no tiene `id_punto`:

NASA FIRMS detecta focos en cualquier coordenada. Forzarlos a un punto de monitoreo perderia precision. Para analisis se filtran por pais, fecha, bbox o cercania al punto, pero el evento conserva su coordenada real.

## 12. Indices

Archivo: `sql/ddl/03_indices.sql`.

Los indices aceleran filtros frecuentes.

Ejemplos:

| Indice | Tabla | Para que sirve |
|---|---|---|
| `idx_focos_fecha_adq` | `focos_calor` | Consultas por rango temporal |
| `idx_focos_lat_lon` | `focos_calor` | Filtros espaciales |
| `idx_focos_frp` | `focos_calor` | Ranking por intensidad |
| `idx_meteo_punto_fecha` | `meteo_diario` | Dashboard por punto y fecha |
| `idx_meteo_nivel_riesgo` | `meteo_diario` | Alertas de riesgo |
| `idx_cams_alerta_oms` | `calidad_aire_diario` | Solo dias con alerta PM10 |
| `idx_etl_fuente_inicio` | `etl_ejecuciones` | Ultima ejecucion por fuente |

Concepto:

Un indice parcial como `idx_cams_alerta_oms` guarda solo filas donde `supera_oms_pm10 = TRUE`. Es eficiente porque las alertas son una fraccion del total.

## 13. Vistas SQL

Archivo: `sql/ddl/04_vistas.sql`.

Las vistas sirven para:

- simplificar consultas del dashboard;
- separar datos base de datos expuestos;
- aplicar seguridad: el usuario readonly consulta vistas.

Vistas principales:

| Vista | Proposito |
|---|---|
| `v_riesgo_actual` | Ultimo riesgo por punto |
| `v_riesgo_historico` | Serie historica completa |
| `v_focos_resumen_diario` | Focos agregados por dia y pais |
| `v_alertas_calidad_aire` | Dias sobre umbral PM10 |
| `v_dias_criticos` | Dias con riesgo alto o muy alto |
| `v_forecast_riesgo` | Pronostico proximo |
| `v_riesgo_por_pais` | Riesgo mensual agregado por pais |
| `v_focos_por_pais_mes` | Focos mensuales por pais |

## 14. MongoDB

MongoDB se usa para datos operacionales y documentos flexibles.

Colecciones:

| Coleccion | Uso |
|---|---|
| `ejecuciones_etl` | Registro flexible de ejecuciones |
| `alertas` | Eventos de alerta |
| `focos_snapshots` | Documento diario auto-contenido de focos |
| `focos_resumen_pais` | Resumen materializado por pais |
| `focos_resumen_mes` | Resumen materializado por pais y mes |

### `focos_snapshots`

Grano: un documento por fecha.

Campos:

- `fecha`;
- `generado_en`;
- `total_focos`;
- `resumen`;
- `focos`: array embebido;
- `riesgo_del_dia`.

Por que Mongo:

La pregunta "que paso el dia X" se responde leyendo un documento, sin joins.

### `alertas`

Grano: una alerta generada.

Campos:

- `tipo_alerta`;
- `fecha_generacion`;
- `fuente`;
- `nivel`;
- `puntos_afectados`;
- `indicadores`;
- `mensaje`;
- `activa`;
- `resuelta_en`.

Por que Mongo:

Las alertas pueden cambiar de estructura segun sean de riesgo, focos, calidad de aire o combinadas.

### `ejecuciones_etl`

Grano: una ejecucion del pipeline.

Permite guardar metricas variables sin alterar tablas SQL.

## 15. CDC e idempotencia

CDC significa Change Data Capture: incorporar cambios nuevos o modificados sin recargar todo.

Idempotencia significa que correr dos veces el mismo proceso no duplica datos ni rompe consistencia.

En PostgreSQL se implementa con:

```sql
INSERT ... ON CONFLICT (...) DO UPDATE
```

Ejemplos:

- `focos_calor`: conflicto por latitud, longitud, fecha, hora, satelite.
- `meteo_diario`: conflicto por fecha, punto, tipo.
- `calidad_aire_diario`: conflicto por fecha, punto.
- `precipitacion_mensual`: conflicto por anio, mes, punto.
- `cobertura_vegetal`: conflicto por anio, punto.

En MongoDB:

- snapshots usan `replace_one(..., upsert=True)` por fecha;
- colecciones de resumen se regeneran con indices unicos;
- alertas se insertan como eventos.

## 16. Testing

Archivo: `tests/test_calidad_datos.py`.

Categorias:

| Categoria | Que valida |
|---|---|
| Alcance | 4 paises, 36 puntos, 19 departamentos de Uruguay |
| Completitud | Campos criticos no nulos |
| Unicidad | Sin duplicados por clave natural |
| Consistencia | Coordenadas, rangos, humedad, indice |
| Validez | Dominios permitidos |
| Idempotencia | Doble carga simulada no duplica |
| CDC | Detecta registros nuevos y modificaciones |

Resultado validado:

```text
20 passed
```

Si preguntan "como se que funciona":

Porque hay tests automatizados, reportes JSON y validacion del dashboard. No es solo una afirmacion documental.

## 17. Dashboard Streamlit

Archivos:

- `dashboard/app.py`: interfaz.
- `dashboard/db.py`: capa de acceso a datos.

Concepto:

El dashboard no deberia tener SQL complejo mezclado con UI. Por eso `db.py` encapsula consultas y fallback.

Caracteristicas:

- consulta PostgreSQL si esta disponible;
- usa Parquet como fallback;
- muestra focos, riesgo, calidad de aire, forecast, rendimiento y evidencia;
- permite defensa aunque la base local no este levantada.

Por que Streamlit:

Es Python puro, rapido para prototipos analiticos, facil de ejecutar y suficiente para exponer KPIs y graficos.

## 18. Scheduler

Archivo: `etl/scheduler.py`.

Usa APScheduler.

Jobs:

- FIRMS NRT cada 3 horas;
- forecast meteorologico cada 1 hora;
- CAMS NRT cada 1 hora;
- CHIRPS mensual.

Por que:

La consigna pide sistema funcional y distribuido/incremental. El scheduler automatiza actualizaciones y demuestra operacion continua.

## 19. Seguridad

Elementos implementados:

- credenciales fuera del codigo (`.env`);
- `.env.example` como plantilla;
- roles PostgreSQL;
- usuario dashboard readonly;
- vistas para exponer datos sin dar acceso completo a tablas;
- Mongo con usuario read/write y usuario read;
- backups y reportes de restore.

Respuesta corta:

> La seguridad se implementa separando configuracion sensible del codigo, usando roles con minimo privilegio y exponiendo al dashboard vistas y usuarios de lectura cuando corresponde.

## 20. Docker y despliegue

Archivo: `docker/docker-compose.yml`.

El objetivo de Docker Compose es documentar y levantar servicios de forma reproducible: PostgreSQL, MongoDB y dashboard.

Aunque en el entorno local tambien se usen bases nativas, Docker queda como definicion de infraestructura reproducible.

Comando validado:

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env.example config --quiet
```

## 21. Evidencia actual

Datos procesados principales:

| Archivo | Filas |
|---|---:|
| `firms_procesado.parquet` | 1.946.361 |
| `firms_nrt_procesado.parquet` | 5.283 |
| `meteo_procesado_todos.parquet` | 88.087 |
| `cams_procesado_todos.parquet` | 98.449 |
| `forecast_riesgo.parquet` | 77 |
| `chirps_sa.parquet` | 2.886 |
| `modis_lc.parquet` | 63 |
| `eventos_volcanicos_impacto_uruguay.parquet` | 2 |

Distribucion vigente de `firms_nrt_procesado.parquet` por pais, luego de
reclasificar el snapshot NRT con el alcance actual `ARG/BRA/CHL/URY`:

| Pais | Focos NRT |
|---|---:|
| ARG | 1.334 |
| BRA | 2.930 |
| CHL | 945 |
| URY | 74 |

Evidencia reproducible: `reports/firms_nrt_reclasificacion_ultimo.json`.

Validaciones del cierre:

- tests: 20 passed;
- compilacion Python: sin errores;
- Docker Compose config: valida;
- dashboard local: HTTP 200.

## 22. Preguntas duras del profesor

### Por que PostgreSQL y MongoDB a la vez?

PostgreSQL se usa para datos estructurados, relaciones, integridad y consultas SQL. MongoDB se usa para documentos flexibles, snapshots y alertas. No es duplicacion: cada motor cubre un tipo de necesidad distinto.

### Que es el grano de una tabla?

El grano es que representa una fila. Por ejemplo, en `meteo_diario` una fila representa un dia, un punto y un tipo de dato. En `focos_calor`, una fila representa una deteccion satelital.

### Como se evita duplicar datos?

Con claves naturales y `ON CONFLICT`. Si el mismo registro vuelve a cargarse, PostgreSQL lo detecta y no crea otro duplicado.

### Como se detecta un cambio?

En `ON CONFLICT DO UPDATE`, se actualizan campos solo si son distintos (`IS DISTINCT FROM`). Eso permite distinguir sin cambio de modificacion.

### Por que Parquet y no CSV?

Parquet conserva tipos, comprime mejor, lee columnas selectivamente y es mas eficiente para analitica.

### Por que `focos_calor` no referencia `puntos_monitoreo`?

Porque un foco satelital ocurre en una coordenada libre. Asociarlo forzosamente a un punto perderia precision. Se puede filtrar por cercania, pero el dato original debe conservarse.

### Que significa idempotencia?

Que puedo correr el pipeline dos veces con el mismo input y el estado final queda igual. No duplica ni corrompe datos.

### Que significa CDC?

Change Data Capture: cargar solo nuevos o modificados. En este proyecto se implementa con upserts, claves naturales, watermarks en scheduler y pruebas que simulan cambios.

### Por que hay vistas?

Para simplificar consultas, mejorar seguridad y separar logica analitica de tablas base.

### Que representa `indice_riesgo`?

Un indicador entre 0 y 1 calculado con temperatura, humedad, viento y sequia. No predice incendios por si solo; estima condiciones meteorologicas favorables al riesgo.

### Que limitaciones tiene?

- La asignacion de pais de FIRMS se basa en bounding boxes.
- El indice de riesgo es heuristico, no un modelo supervisado.
- La sincronizacion UTEC historica puede no reflejar Chile si no se ejecuta una nueva verificacion remota.
- Algunos datasets tienen distinta resolucion temporal y espacial.

Responder limitaciones es positivo: muestra criterio tecnico.

## 23. Guion mental para explicar el proyecto

1. Empiezo por el problema: datos ambientales dispersos.
2. Explico el alcance: Uruguay completo + paises regionales relevantes.
3. Muestro arquitectura: fuentes -> ETL -> Parquet -> PostgreSQL/Mongo -> dashboard.
4. Defiendo PostgreSQL: integridad, tablas, relaciones, SQL.
5. Defiendo MongoDB: documentos flexibles, alertas, snapshots.
6. Explico CDC/idempotencia con `ON CONFLICT`.
7. Explico pruebas: calidad, unicidad, consistencia, CDC.
8. Cierro con evidencia: 20 tests, reportes, dashboard.

## 24. Respuesta final corta para defensa

> El proyecto transforma fuentes ambientales reales en un sistema integrado. Los extractores descargan datos, las transformaciones normalizan y calculan indicadores, PostgreSQL guarda el modelo analitico con integridad y MongoDB guarda documentos operacionales. El sistema es reproducible porque usa configuracion externa, Parquet, Docker, pruebas automatizadas, logs y reportes. La idempotencia y el CDC se implementan con claves naturales, upserts y validaciones automatizadas.

