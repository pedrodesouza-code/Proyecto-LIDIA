# Proyecto Final EC1 + EC2

**TÃ­tulo del proyecto:** Sistema integrado de datos ambientales para el anÃ¡lisis de incendios forestales, condiciones meteorolÃ³gicas, precipitaciÃ³n, calidad del aire y cobertura vegetal en Uruguay y paÃ­ses limÃ­trofes (Brasil y Argentina), perÃ­odo 2018-2025

**Carrera:** Licenciatura en IngenierÃ­a de Datos e Inteligencia Artificial
**Curso:** Proyecto de IngenierÃ­a de Datos
**Estudiante/s:** [Completar]  
**Docente:** [Completar]  
**Fecha:** [Completar]

## Resumen

El proyecto diseÃ±Ã³ una soluciÃ³n integral de ingenierÃ­a de datos para analizar incendios forestales en Uruguay y sus paÃ­ses limÃ­trofes (Brasil y Argentina) durante el perÃ­odo 2018-2025, mediante la integraciÃ³n de cinco fuentes abiertas y heterogÃ©neas: NASA FIRMS, Open-Meteo / ERA5-Land, CAMS / Copernicus, CHIRPS y MODIS Land Cover a travÃ©s de AppEEARS. El alcance regional se acota a estos tres paÃ­ses porque concentran los focos de calor que producen humo transfronterizo sobre territorio uruguayo y permiten un anÃ¡lisis comparativo manejable, preservando al mismo tiempo el carÃ¡cter regional del estudio. El problema abordado fue la ausencia de un sistema unificado capaz de combinar datos con diferentes formatos, granularidades temporales, resoluciones espaciales y modelos conceptuales. MetodolÃ³gicamente, se adoptÃ³ un enfoque de ingenierÃ­a aplicada e incremental, alineado con los entregables EC1 y EC2, que contemplÃ³ anÃ¡lisis del dominio, exploraciÃ³n preliminar real de fuentes, diseÃ±o de arquitectura multicapa, modelado relacional tipo Data Warehouse en MySQL, modelado documental en MongoDB y diseÃ±o detallado de un pipeline ETL en Python con validaciÃ³n, CDC e idempotencia. Como resultado, se definiÃ³ un modelo de destino integrado con dimensiones conformadas y hechos separados por granularidad, junto con reglas de integridad, esquemas JSON para trazabilidad documental, KPIs y lineamientos de visualizaciÃ³n en Streamlit. El diseÃ±o permite responder consultas analÃ­ticas verificables, preservar histÃ³rico, registrar el comportamiento del pipeline y sentar la base para la implementaciÃ³n reproducible del sistema en la etapa siguiente.

**Palabras clave:** incendios forestales; ingenierÃ­a de datos; ETL; CDC; MySQL; MongoDB; calidad del aire; cobertura vegetal.

## 1. IntroducciÃ³n

Los incendios forestales constituyen un fenÃ³meno ambiental complejo cuya ocurrencia e intensidad dependen de la interacciÃ³n entre clima, disponibilidad de combustible, dinÃ¡mica hidrolÃ³gica y caracterÃ­sticas del territorio. Jolly et al. (2015) mostraron que la duraciÃ³n de las temporadas de peligro de incendio se ha incrementado de forma significativa a escala global, mientras que Reid et al. (2016) documentaron que la exposiciÃ³n al humo de incendios se asocia con incrementos de material particulado fino y con efectos respiratorios adversos. En consecuencia, estudiar incendios forestales en Uruguay y su entorno regional inmediato (Brasil y Argentina) exige una aproximaciÃ³n integrada que combine focos activos, variables meteorolÃ³gicas, precipitaciÃ³n, calidad del aire y cobertura vegetal dentro de una misma estructura de anÃ¡lisis.

En esta regiÃ³n, la principal dificultad no radica en la falta de datos, sino en su dispersiÃ³n entre plataformas con formatos y escalas diferentes. NASA FIRMS distribuye focos activos detectados por sensores satelitales; Open-Meteo ofrece acceso programÃ¡tico a datos meteorolÃ³gicos histÃ³ricos; CAMS publica informaciÃ³n atmosfÃ©rica y de calidad del aire; CHIRPS provee precipitaciÃ³n de base satelital; y AppEEARS facilita el acceso a productos MODIS de cobertura terrestre. Estas diferencias impiden el cruce directo entre datasets y convierten el problema en un caso genuino de ingenierÃ­a de datos, porque se requiere un sistema capaz de extraer, transformar, armonizar y almacenar informaciÃ³n heterogÃ©nea en un modelo de destino coherente.

Desde la perspectiva metodolÃ³gica del curso, el proyecto se encuadra como una soluciÃ³n de ingenierÃ­a aplicada y no como un trabajo de investigaciÃ³n teÃ³rica pura. La consigna exige integrar fuentes heterogÃ©neas, aplicar transformaciones controladas, mantener trazabilidad, incorporar actualizaciÃ³n incremental y soportar consultas analÃ­ticas verificables. Por lo tanto, el propÃ³sito del proyecto no es solo reunir datos, sino construir una soluciÃ³n tÃ©cnica que gestione el ciclo de vida completo del dato, desde la ingestiÃ³n hasta el anÃ¡lisis.

### Figura 1. Diagrama de relaciÃ³n entre actores

![](figures/figura_1_actores.svg)

Fuente: elaboraciÃ³n propia.

### 1.1 Problema

El problema especÃ­fico abordado en este proyecto es la ausencia de un sistema unificado que permita analizar incendios forestales en Uruguay y sus paÃ­ses limÃ­trofes (Brasil y Argentina) mediante la integraciÃ³n simultÃ¡nea de focos de calor, condiciones meteorolÃ³gicas, precipitaciÃ³n, calidad del aire y cobertura vegetal. Aunque cada una de estas dimensiones dispone de fuentes pÃºblicas tÃ©cnicamente accesibles, esas fuentes presentan diferencias sustanciales en formato, granularidad temporal, resoluciÃ³n espacial y estructura conceptual. Giglio et al. (2016) describen productos de detecciÃ³n activa de fuego con granularidad por evento, mientras que la documentaciÃ³n de Open-Meteo presenta series diarias y horarias, y MuÃ±oz-Sabater et al. (2021) caracterizan ERA5-Land como un reanÃ¡lisis orientado a aplicaciones terrestres. Esa heterogeneidad impide el cruce directo entre datasets y exige una etapa formal de armonizaciÃ³n.

El problema, en consecuencia, no es Ãºnicamente ambiental, sino tambiÃ©n arquitectÃ³nico y metodolÃ³gico. Para responder preguntas sobre evoluciÃ³n temporal, comparaciÃ³n regional o relaciÃ³n entre variables de distintas fuentes, se necesita un sistema capaz de transformar estructuras existentes en un modelo integrado de destino, con preservaciÃ³n del histÃ³rico, trazabilidad de cambios y soporte para consultas agregadas. Esta necesidad coincide con la lÃ³gica de EC1 y EC2, donde se exige transformar una temÃ¡tica general en un problema tÃ©cnico delimitado y luego diseÃ±ar una soluciÃ³n que combine modelo relacional, modelo NoSQL, ETL, integridad y mÃ©tricas.

### 1.2 Objetivos

#### 1.2.1 Objetivo general

DiseÃ±ar e implementar conceptualmente un sistema integrado de datos ambientales que consolide informaciÃ³n de incendios forestales, condiciones meteorolÃ³gicas, precipitaciÃ³n, calidad del aire y cobertura vegetal en Uruguay y sus paÃ­ses limÃ­trofes (Brasil y Argentina) durante el perÃ­odo 2018-2025, utilizando MySQL como repositorio relacional analÃ­tico y MongoDB como repositorio documental de trazabilidad, de modo que el sistema sea capaz de responder consultas agregadas, preservar histÃ³rico y registrar el comportamiento del pipeline mediante mecanismos formales de validaciÃ³n y actualizaciÃ³n incremental.

#### 1.2.2 Objetivos especÃ­ficos

1. DiseÃ±ar un pipeline ETL en Python capaz de extraer, transformar y cargar datos de cinco fuentes heterogÃ©neas mediante procesos reproducibles e idempotentes, utilizando validaciÃ³n estructural previa y controles de integridad en la carga.
2. Construir un modelo dimensional en MySQL con tablas de hechos y dimensiones conformadas, orientado a consultas analÃ­ticas, anÃ¡lisis temporal y cÃ¡lculo de KPIs.
3. Implementar conceptualmente un mecanismo de CDC basado en ventana temporal retrospectiva y verificaciÃ³n por hash de lote, de manera que el sistema detecte tanto registros nuevos como correcciones histÃ³ricas.
4. DiseÃ±ar un modelo documental en MongoDB para almacenar logs de ejecuciÃ³n, metadatos de control, snapshots y mÃ©tricas de calidad del pipeline, utilizando validaciÃ³n mediante JSON Schema.
5. Definir KPIs alineados con las preguntas analÃ­ticas del proyecto y con la futura capa de visualizaciÃ³n, manteniendo correspondencia explÃ­cita entre preguntas, consultas, resultados y representaciones grÃ¡ficas.
6. Documentar reglas de integridad, trade-offs tÃ©cnicos, riesgos y limitaciones para asegurar que la soluciÃ³n sea justificable, auditable y escalable.

### 1.3 Alcance del proyecto

El proyecto integra cinco fuentes abiertas y heterogÃ©neas: NASA FIRMS para incendios activos, Open-Meteo / ERA5-Land para meteorologÃ­a, CAMS / Copernicus para calidad del aire, CHIRPS para precipitaciÃ³n y MODIS Land Cover / AppEEARS para cobertura vegetal. La combinaciÃ³n de fuentes ofrece cobertura suficiente para el perÃ­odo objetivo 2018-2025 y justifica la integraciÃ³n multifuente del proyecto.

El alcance espacial corresponde a tres paÃ­ses: Uruguay como nÃºcleo del sistema y sus dos limÃ­trofes, Brasil y Argentina. El alcance temporal se mantiene en el perÃ­odo 2018-2025. La selecciÃ³n se fundamenta en criterios tÃ©cnicos: los focos detectados en el sur de Brasil (Rio Grande do Sul, Mato Grosso) y en el norte argentino (Misiones, Salta) generan el humo transfronterizo que afecta directamente la calidad del aire y la visibilidad sobre territorio uruguayo, mientras que la inclusiÃ³n de los tres paÃ­ses simultÃ¡neamente permite responder las preguntas comparativas del EC1 sin diluir el foco en Uruguay. El sistema queda diseÃ±ado para escalar el alcance a otros paÃ­ses sudamericanos mediante un cambio de configuraciÃ³n en `PAISES_SA`, sin modificaciones estructurales en el modelo. El anÃ¡lisis se apoya en una grilla espacial comÃºn de 0,25Â° para asegurar interoperabilidad entre fuentes con resoluciones distintas. Quedan fuera del alcance el modelado predictivo, el anÃ¡lisis sanitario de poblaciones afectadas, la evaluaciÃ³n econÃ³mica de incendios y la incorporaciÃ³n de fuentes cuyo acceso no sea programÃ¡tico o reproducible.

### 1.4 Limitaciones

Una limitaciÃ³n importante del proyecto deriva de la cobertura desigual entre fuentes. Mientras FIRMS y Open-Meteo permiten trabajar con granularidad de evento, diaria u horaria, CHIRPS opera con productos mensuales y MODIS con productos anuales. Esto obliga a construir hechos separados por nivel temporal y a evitar cruces ingenuos entre datasets.

TambiÃ©n deben considerarse las limitaciones de calidad de ciertas variables, especialmente cuando existen nulos masivos, latencia de publicaciÃ³n o revisiones histÃ³ricas posteriores. Por esa razÃ³n, el diseÃ±o del sistema incorpora mÃ©tricas de calidad, control incremental, reglas de integridad y trazabilidad documental.

## 2. Marco conceptual

El concepto de ETL es central en este trabajo porque la soluciÃ³n depende de una secuencia ordenada de extracciÃ³n, transformaciÃ³n y carga sobre fuentes con estructuras muy diferentes. Python se adopta como lenguaje de implementaciÃ³n del pipeline por su ecosistema maduro para manipulaciÃ³n de datos, validaciÃ³n y conexiÃ³n con distintos motores de persistencia. En particular, Pydantic permite validar tipos, rangos y estructuras antes de la inserciÃ³n, mientras que Streamlit ofrece una base adecuada para construir aplicaciones analÃ­ticas de forma rÃ¡pida y reproducible.

El concepto de Data Warehouse tambiÃ©n es fundamental. En este proyecto, el repositorio relacional no se define como una copia de las fuentes, sino como un modelo integrado de destino diseÃ±ado para histÃ³rico, agregaciÃ³n y cÃ¡lculo de indicadores. Por ello, el diseÃ±o en MySQL se orienta a hechos y dimensiones conformadas, priorizando rendimiento de consulta y preservaciÃ³n de histÃ³rico frente a una normalizaciÃ³n transaccional estricta.

En paralelo, el proyecto incorpora persistencia polÃ­glota. La parte estructurada e intensiva en joins se asigna a MySQL, mientras que la parte documental y semiestructurada se asigna a MongoDB. Esto permite separar claramente las consultas analÃ­ticas del almacenamiento de logs, snapshots, alertas y metadatos de control.

El concepto de CDC ocupa un lugar metodolÃ³gico clave en esta arquitectura. El mecanismo incremental debe contemplar no solo inserciÃ³n de registros nuevos, sino tambiÃ©n modificaciones sobre datos existentes. En coherencia con esa exigencia, el proyecto plantea un CDC basado en ventana temporal retrospectiva y verificaciÃ³n de hash por lote, registrando metadatos en MongoDB para permitir auditorÃ­a y control incremental. La idempotencia complementa ese diseÃ±o: reejecutar el pipeline sobre un mismo lote no debe generar duplicados ni inconsistencias.

La calidad de datos se evalÃºa sobre cuatro dimensiones: completitud, unicidad, consistencia y validez. Estas mÃ©tricas no se tratan como una revisiÃ³n secundaria, sino como una condiciÃ³n para que las preguntas analÃ­ticas puedan responderse con fiabilidad. Finalmente, los KPIs cumplen el rol de traducir preguntas del dominio en mÃ©tricas trazables y verificables sobre el modelo de destino.

El concepto de SLA (Service Level Agreement) se incorpora al diseÃ±o como un conjunto de compromisos operativos que el sistema debe cumplir para que las preguntas analÃ­ticas y los KPIs tengan valor en producciÃ³n. En el contexto de SINIA-UY no se trata de un acuerdo contractual externo, sino de umbrales internos que delimitan la operaciÃ³n esperada del pipeline: frescura mÃ¡xima de los datos respecto al evento real (por ejemplo, focos NRT con latencia inferior a seis horas), disponibilidad mÃ­nima de la base relacional durante la ventana operativa diurna en que se consulta el dashboard, tiempo mÃ¡ximo de respuesta para las consultas de la capa Streamlit y porcentaje mÃ­nimo de tests de calidad superados antes de exponer datos al usuario final. Estos umbrales transforman el rendimiento del sistema en una propiedad medible y permiten distinguir entre una operaciÃ³n nominal y una operaciÃ³n degradada que requiera intervenciÃ³n.

El concepto de despliegue hÃ­brido refiere a la coexistencia planificada de componentes que viven en entornos distintos pero operan como un sistema Ãºnico. En SINIA-UY el despliegue es hÃ­brido en dos sentidos complementarios. Por un lado, hay una separaciÃ³n entre el ambiente de desarrollo local del equipo (PostgreSQL y MongoDB nativos en la PC del estudiante) y el ambiente del servidor acadÃ©mico de UTEC (base `grp03db` asignada en `10.200.245.40` para Postgres y Mongo), donde el cÃ³digo se prueba localmente y se promueve mediante Git a la instancia remota. Por otro lado, dentro del propio sistema conviven dos motores complementarios: un motor relacional para el Data Warehouse y un motor documental para trazabilidad operativa, conectados por el mismo pipeline Python y consumidos por la misma capa Streamlit. Este enfoque permite aislar fallos por motor, escalar cada pieza con polÃ­ticas distintas y mantener el desarrollo independiente del ambiente productivo sin sacrificar la coherencia funcional del sistema.

### Cuadro 1. Principales artÃ­culos revisados y su aporte al proyecto

| Fuente | Tipo | Aporte principal al proyecto |
|---|---|---|
| Jolly et al. (2015) | ArtÃ­culo cientÃ­fico | Fundamenta la relevancia del aumento del peligro global de incendios y justifica el anÃ¡lisis temporal del riesgo. |
| Reid et al. (2016) | RevisiÃ³n crÃ­tica | Sustenta la inclusiÃ³n de PM2.5 y PM10 como dimensiÃ³n de impacto atmosfÃ©rico asociada a incendios. |
| Giglio et al. (2016) | ArtÃ­culo cientÃ­fico | Describe el algoritmo de detecciÃ³n activa de fuego MODIS/FIRMS y respalda el uso de FRP, brightness y confidence. |
| MuÃ±oz-Sabater et al. (2021) | ArtÃ­culo cientÃ­fico | Justifica el uso de ERA5-Land / Open-Meteo como base meteorolÃ³gica coherente para aplicaciones terrestres. |
| van der Werf et al. (2017) | ArtÃ­culo cientÃ­fico | Aporta contexto sobre emisiones de fuego y la necesidad de anÃ¡lisis multifuente a escala regional. |
| DocumentaciÃ³n Open-Meteo | DocumentaciÃ³n tÃ©cnica | Define acceso programÃ¡tico, variables horarias/diarias y parÃ¡metros de consulta reproducibles. |
| DocumentaciÃ³n MySQL | DocumentaciÃ³n tÃ©cnica | Respalda la elecciÃ³n del motor relacional, Ã­ndices, constraints y diseÃ±o analÃ­tico. |
| DocumentaciÃ³n MongoDB | DocumentaciÃ³n tÃ©cnica | Fundamenta validaciÃ³n JSON Schema, documentos flexibles, replicaciÃ³n y modelado NoSQL. |
| DocumentaciÃ³n Pydantic | DocumentaciÃ³n tÃ©cnica | Soporta validaciÃ³n de estructuras y tipos en la fase de transformaciÃ³n y pre-carga. |
| DocumentaciÃ³n Streamlit | DocumentaciÃ³n tÃ©cnica | Justifica la futura capa analÃ­tica y la exposiciÃ³n de KPIs y visualizaciones. |

Fuente: elaboraciÃ³n propia con base en bibliografÃ­a cientÃ­fica y documentaciÃ³n tÃ©cnica oficial.

## 3. MetodologÃ­a

### 3.1 Tipo de investigaciÃ³n

El proyecto se desarrolla bajo un enfoque de ingenierÃ­a aplicada e incremental. La primera etapa se orienta al anÃ¡lisis del dominio, el problema, las fuentes, la exploraciÃ³n preliminar, la calidad y la arquitectura inicial. La segunda etapa se centra en el diseÃ±o del modelo integrado de destino, el mapeo fuente-destino, la resoluciÃ³n de conflictos de integraciÃ³n, el modelo relacional, el modelo NoSQL, la arquitectura detallada, el ETL y las mÃ©tricas.

### 3.2 Contexto del proyecto

La arquitectura propuesta incluye fuentes externas, ingesta en Python, staging, transformaciÃ³n, persistencia relacional en MySQL, persistencia documental en MongoDB y futura visualizaciÃ³n en Streamlit. La soluciÃ³n se apoya en componentes separables y trazables, de modo que cada etapa del ciclo de vida del dato pueda ser auditada.

### 3.3 Instrumentos de recolecciÃ³n de datos

Las fuentes utilizadas incluyen APIs REST, descargas reproducibles de archivos geoespaciales y servicios abiertos de datos histÃ³ricos. Para cada una se releva nombre, enlace oficial, tipo de acceso, formato, frecuencia, volumen, granularidad, variables relevantes y limitaciones tÃ©cnicas. La exploraciÃ³n preliminar efectiva se apoyÃ³ en scripts de extracciÃ³n y transformaciÃ³n desarrollados en Python para cada fuente.

### Tabla 1. Actores del sistema y sus relaciones

| Actor | Rol en el sistema | RelaciÃ³n principal |
|---|---|---|
| NASA FIRMS | Proveedor de focos de calor activos | Alimenta hechos diarios de incendios y snapshots documentales |
| Open-Meteo / ERA5-Land | Proveedor de meteorologÃ­a histÃ³rica y pronÃ³stico | Alimenta hechos diarios meteorolÃ³gicos y cÃ¡lculo del Ã­ndice de riesgo |
| CAMS / Copernicus | Proveedor de calidad del aire | Alimenta hechos diarios de PM10, PM2.5 y AQI |
| CHIRPS | Proveedor de precipitaciÃ³n satelital | Alimenta hechos mensuales de precipitaciÃ³n y anomalÃ­a hÃ­drica |
| AppEEARS / MODIS | Proveedor de cobertura vegetal | Alimenta hechos anuales de cobertura y transiciÃ³n |
| Pipeline ETL en Python | Orquestador tÃ©cnico | Extrae, valida, transforma, integra y carga |
| MySQL | Repositorio relacional analÃ­tico | Resuelve consultas, agregaciones y KPIs |
| MongoDB | Repositorio documental de trazabilidad | Registra logs, snapshots, alertas y metadatos de control |
| Dashboard Streamlit | Capa analÃ­tica | Consume datos consolidados y expone KPIs y visualizaciones |
| Usuario analÃ­tico | Consumidor de resultados | Formula preguntas y valida salidas del sistema |

Fuente: elaboraciÃ³n propia.

### Tabla 2. Variables relevantes por dimensiÃ³n analÃ­tica

| DimensiÃ³n | Variables principales | PropÃ³sito analÃ­tico | Fuente dominante |
|---|---|---|---|
| Incendios | latitud, longitud, fecha, hora, FRP, confidence, brightness | Medir ocurrencia, intensidad y distribuciÃ³n espacial de focos | NASA FIRMS |
| MeteorologÃ­a | temperatura mÃ¡xima, mÃ­nima, humedad relativa, viento, precipitaciÃ³n diaria, ET0 | Explicar condiciones predisponentes del fuego | Open-Meteo / ERA5-Land |
| Calidad del aire | PM10, PM2.5, AQI, aerosol optical depth | Aproximar impacto atmosfÃ©rico asociado a actividad de fuego | CAMS / Copernicus |
| PrecipitaciÃ³n | precipitaciÃ³n mensual, anomalÃ­a porcentual | Caracterizar sequÃ­a, estrÃ©s hÃ­drico y contexto hidrolÃ³gico | CHIRPS |
| Cobertura vegetal | LC_Type1, descripciÃ³n IGBP, grupo combustible | Relacionar incendios con tipo de cobertura y combustible potencial | MODIS / AppEEARS |
| Control ETL | estado, duraciÃ³n, registros procesados, insertados, actualizados, hash de lote | Medir trazabilidad, calidad e incrementalidad del pipeline | MongoDB / MySQL |

Fuente: elaboraciÃ³n propia.

### Tabla 3. Granularidad temporal y espacial por fuente

| Fuente | Granularidad temporal | Granularidad espacial | Formato principal | Implicancia de integraciÃ³n |
|---|---|---|---|---|
| NASA FIRMS | Evento / subdiaria | Coordenada puntual satelital | CSV / API | Requiere agregaciÃ³n diaria y asignaciÃ³n a grilla |
| Open-Meteo / ERA5-Land | Diaria y horaria | Grilla meteorolÃ³gica / punto consultado | JSON / CSV | Requiere armonizaciÃ³n por celda y dÃ­a |
| CAMS / Copernicus | Horaria | Punto o grilla atmosfÃ©rica | JSON / CSV | Requiere agregaciÃ³n diaria para comparabilidad |
| CHIRPS | Mensual para el proyecto | Raster / punto extraÃ­do | CSV / geoespacial | Requiere hecho mensual separado |
| MODIS / AppEEARS | Anual | Raster 500 m / punto extraÃ­do | CSV | Requiere hecho anual separado |

Fuente: elaboraciÃ³n propia.

### 3.4 Procedimientos de anÃ¡lisis de datos

El anÃ¡lisis del proyecto se organiza en etapas: extracciÃ³n desde APIs y archivos, validaciÃ³n inicial, transformaciÃ³n temporal y espacial, control de calidad, carga en MySQL, carga documental en MongoDB y diseÃ±o de consultas analÃ­ticas y KPIs. Durante EC1 se realizÃ³ exploraciÃ³n preliminar real, incluyendo acceso efectivo a las fuentes, muestras, estructura de datos, nulos y problemas de integraciÃ³n. Durante EC2 se diseÃ±Ã³ la soluciÃ³n de destino completa.

### 3.5 Aspectos Ã©ticos

El proyecto se construye sobre datos abiertos y no sensibles. Sin embargo, eso no elimina la necesidad de documentar sesgos, vacÃ­os y lÃ­mites estructurales del dato. La metodologÃ­a, por tanto, incorpora mÃ©tricas de calidad y registro explÃ­cito de acciones correctivas, evitando presentar resultados futuros como neutrales o completos por definiciÃ³n.

### 3.6 Preguntas analÃ­ticas del proyecto

1. Â¿CÃ³mo evolucionÃ³ la cantidad de incendios forestales en Uruguay, Brasil, Argentina y Chile entre 2018 y 2025?
2. Â¿QuÃ© paÃ­ses concentran la mayor cantidad de focos por aÃ±o y por mes?
3. Â¿En quÃ© meses se registra mayor actividad de incendios y cÃ³mo cambia ese patrÃ³n entre paÃ­ses?
4. Â¿QuÃ© relaciÃ³n existe entre temperatura elevada, baja humedad y actividad de fuego?
5. Â¿CÃ³mo se comporta el Ã­ndice de riesgo meteorolÃ³gico frente a la ocurrencia real de focos?
6. Â¿CÃ³mo varÃ­an PM2.5 y PM10 durante perÃ­odos con alta actividad de incendios?
7. Â¿QuÃ© celdas o regiones presentan mayor recurrencia de incendios intensos?
8. Â¿QuÃ© relaciÃ³n existe entre dÃ©ficit de precipitaciÃ³n y aumento de focos?
9. Â¿QuÃ© tipos de cobertura vegetal concentran mÃ¡s actividad de incendios?
10. Â¿CÃ³mo se vinculan las transiciones de cobertura vegetal con cambios en la distribuciÃ³n espacial del fuego?

## 4. Resultados â€” DiseÃ±o tÃ©cnico del sistema integrado

### 4.1 AnÃ¡lisis detallado de fuentes y campos

NASA FIRMS constituye la fuente principal para incendios activos. Giglio et al. (2016) describen el algoritmo de detecciÃ³n MODIS Collection 6 y documentan mejoras en la detecciÃ³n y reducciÃ³n de falsas alarmas. En tÃ©rminos analÃ­ticos, esto respalda el uso de variables como brightness, FRP y confidence dentro del proyecto.

Open-Meteo / ERA5-Land se incorpora como fuente meteorolÃ³gica histÃ³rica. De acuerdo con la documentaciÃ³n oficial, el servicio histÃ³rico de Open-Meteo permite acceder a variables diarias y horarias como temperatura, humedad relativa, precipitaciÃ³n, viento y presiÃ³n, mientras que MuÃ±oz-Sabater et al. (2021) caracterizan ERA5-Land como un producto consistente para aplicaciones sobre superficie terrestre.

CAMS / Copernicus se incorpora para cubrir la dimensiÃ³n de calidad del aire. Su valor analÃ­tico no radica solo en proveer PM2.5 y PM10, sino tambiÃ©n en permitir aproximar el impacto del humo de incendios sobre la atmÃ³sfera. En esta lÃ­nea, Reid et al. (2016) destacan el papel del PM2.5 como uno de los indicadores mÃ¡s relevantes en la literatura sobre humo de incendios.

CHIRPS aporta precipitaciÃ³n histÃ³rica y MODIS Land Cover, a travÃ©s de AppEEARS, se utiliza para estudiar la relaciÃ³n entre incendios y cobertura vegetal. Ambas fuentes son necesarias para contextualizar los incendios dentro de un sistema ambiental mÃ¡s amplio.

### Tabla 4. Ficha tÃ©cnica: NASA FIRMS

| Atributo | DescripciÃ³n |
|---|---|
| Organismo | NASA / FIRMS |
| Tipo de acceso | API REST y descarga CSV |
| Cobertura temporal objetivo | 2018-2025 |
| Granularidad | Evento individual detectado |
| Variables relevantes | latitude, longitude, acq_date, acq_time, bright_ti4, bright_ti5, confidence, FRP, daynight |
| Formato | CSV |
| Problemas de integraciÃ³n | Duplicados por lotes, confianza en escala semÃ¡ntica, necesidad de agregaciÃ³n diaria |
| Uso en el modelo | Hecho diario de incendios y snapshots documentales |

Fuente: elaboraciÃ³n propia con base en Giglio et al. (2016) y documentaciÃ³n oficial de FIRMS.

### Tabla 5. Ficha tÃ©cnica: Open-Meteo / ERA5-Land

| Atributo | DescripciÃ³n |
|---|---|
| Organismo | Open-Meteo sobre ERA5-Land |
| Tipo de acceso | API REST |
| Cobertura temporal objetivo | 2018-2025 |
| Granularidad | Diaria y horaria segÃºn variable |
| Variables relevantes | temperature_2m_max, temperature_2m_min, relative_humidity_2m_min, wind_speed_10m_max, precipitation_sum, ET0 |
| Formato | JSON / CSV |
| Problemas de integraciÃ³n | Diferencias entre histÃ³rico y forecast, necesidad de normalizaciÃ³n espacial y cÃ¡lculo de Ã­ndice compuesto |
| Uso en el modelo | Hecho diario meteorolÃ³gico y cÃ¡lculo de Ã­ndice de riesgo |

Fuente: elaboraciÃ³n propia con base en MuÃ±oz-Sabater et al. (2021) y documentaciÃ³n oficial de Open-Meteo.

### Tabla 6. Ficha tÃ©cnica: CAMS / Copernicus

| Atributo | DescripciÃ³n |
|---|---|
| Organismo | Copernicus Atmosphere Monitoring Service |
| Tipo de acceso | API vÃ­a Open-Meteo Air Quality |
| Cobertura temporal objetivo | 2018-2025 |
| Granularidad | Horaria, agregada a diaria en ETL |
| Variables relevantes | pm10, pm2_5, aerosol_optical_depth, dust, european_aqi |
| Formato | JSON / CSV |
| Problemas de integraciÃ³n | Nulos horarios, necesidad de agregaciÃ³n diaria, comparaciÃ³n con umbrales OMS |
| Uso en el modelo | Hecho diario de calidad del aire y alertas operativas |

Fuente: elaboraciÃ³n propia con base en documentaciÃ³n oficial de CAMS y Reid et al. (2016).

### Tabla 7. Ficha tÃ©cnica: CHIRPS

| Atributo | DescripciÃ³n |
|---|---|
| Organismo | UCSB / SERVIR / CHIRPS |
| Tipo de acceso | API ClimateSERV / descargas reproducibles |
| Cobertura temporal objetivo | 2018-2025 |
| Granularidad | Mensual para este proyecto |
| Variables relevantes | fecha, precipitaciÃ³n mensual acumulada, anomalÃ­a porcentual |
| Formato | CSV |
| Problemas de integraciÃ³n | Cambio de escala respecto de datos diarios, necesidad de hecho mensual separado |
| Uso en el modelo | Hecho mensual de precipitaciÃ³n y sequÃ­a relativa |

Fuente: elaboraciÃ³n propia con base en documentaciÃ³n oficial de CHIRPS.

### Tabla 8. Ficha tÃ©cnica: MODIS Land Cover / AppEEARS

| Atributo | DescripciÃ³n |
|---|---|
| Organismo | NASA MODIS / AppEEARS |
| Tipo de acceso | API AppEEARS |
| Cobertura temporal objetivo | 2018-2025 |
| Granularidad | Anual |
| Variables relevantes | LC_Type1, descripciÃ³n IGBP, punto, aÃ±o |
| Formato | CSV |
| Problemas de integraciÃ³n | Baja frecuencia temporal, cambio de escala frente a focos diarios |
| Uso en el modelo | Hecho anual de cobertura y transiciÃ³n de clase |

Fuente: elaboraciÃ³n propia con base en documentaciÃ³n oficial de AppEEARS y MODIS.

#### 4.1.1 ExploraciÃ³n preliminar real de las fuentes

La guÃ­a del proyecto exige que el anÃ¡lisis preliminar estÃ© respaldado por evidencia real de acceso, estructura y problemas observados. Por esa razÃ³n, la exploraciÃ³n se apoyÃ³ en pruebas efectivas de descarga, consulta y revisiÃ³n de columnas, tipos, nulos, duplicados e inconsistencias evidentes mediante scripts de extracciÃ³n y transformaciÃ³n en Python.

Desde esta exploraciÃ³n surgen hallazgos relevantes para el diseÃ±o. En FIRMS, la presencia de niveles de confianza distintos exige normalizaciÃ³n semÃ¡ntica o filtrado analÃ­tico. En CAMS, algunas variables atmosfÃ©ricas presentan nulos suficientes como para comprometer su utilidad si no se tratan adecuadamente. En CHIRPS y MODIS, la diferencia de granularidad obliga a separar tablas de hechos y a evitar joins temporales directos sin agregaciÃ³n. Estas observaciones condicionan directamente el diseÃ±o del modelo integrado, el CDC y las reglas de calidad.

#### 4.1.2 Calidad preliminar de datos

La evaluaciÃ³n preliminar de calidad se apoya en cuatro dimensiones: completitud, unicidad, consistencia y validez. A diferencia de una descripciÃ³n superficial del dataset, estas mÃ©tricas permiten vincular problemas concretos del dato con el impacto real que tendrÃ¡n sobre las preguntas analÃ­ticas del proyecto.

### Tabla 9. EvaluaciÃ³n de calidad por fuente

| Fuente | Completitud | Unicidad | Consistencia | Validez | Riesgo principal |
|---|---|---|---|---|---|
| NASA FIRMS | Alta en campos crÃ­ticos | Requiere deduplicaciÃ³n por clave natural | Requiere asignaciÃ³n paÃ­s/grilla | Coordenadas y FRP deben validarse | Duplicados y heterogeneidad de confidence |
| Open-Meteo | Alta en variables base | Unicidad por fecha, punto y tipo de dato | Requiere normalizaciÃ³n de tipos y unidades | Ãndice de riesgo debe quedar en [0,1] | Mezcla de histÃ³rico y forecast |
| CAMS | Media-alta con nulos horarios parciales | Unicidad por fecha y punto tras agregaciÃ³n | Requiere agregaciÃ³n diaria | PM10 y PM2.5 no negativos | Nulos horarios y latencia |
| CHIRPS | Alta | Unicidad por punto y mes | Requiere coherencia temporal mensual | PrecipitaciÃ³n no negativa | Cruce ingenuo con datos diarios |
| MODIS | Alta | Unicidad por punto y aÃ±o | Requiere consistencia de clase IGBP | Dominio LC_Type1 acotado | Baja frecuencia temporal |

Fuente: elaboraciÃ³n propia.

### Tabla 10. Impacto de problemas de calidad en preguntas analÃ­ticas

| Problema de calidad | Fuente afectada | Pregunta analÃ­tica impactada | MitigaciÃ³n propuesta |
|---|---|---|---|
| Duplicados por lote | FIRMS | EvoluciÃ³n temporal y ranking de dÃ­as crÃ­ticos | Clave natural + upsert idempotente |
| Nulos horarios | CAMS | ComparaciÃ³n de PM10/PM2.5 en dÃ­as con fuego | AgregaciÃ³n diaria con horas vÃ¡lidas |
| Diferencia diario/mensual/anual | CHIRPS / MODIS | RelaciÃ³n entre precipitaciÃ³n, cobertura e incendios | Hechos separados por grano |
| SemÃ¡ntica variable de confidence | FIRMS | Intensidad y filtro de focos confiables | Mapeo semÃ¡ntico a escala numÃ©rica |
| Cambios histÃ³ricos en origen | Todas | CDC y trazabilidad | Ventana retrospectiva + hash de lote |

Fuente: elaboraciÃ³n propia.

### 4.2 DiseÃ±o conceptual, lÃ³gico y fÃ­sico

La guÃ­a de la etapa 2 insiste en que el modelo de destino no debe representar â€œel mundo desde ceroâ€, sino integrar estructuras ya existentes en las fuentes. Esto implica que el diseÃ±o del modelo relacional debe partir del anÃ¡lisis de campos, de la identificaciÃ³n de conflictos de integraciÃ³n y del mapeo fuente-destino. El proyecto adopta exactamente ese enfoque, documentando primero los campos de origen y luego la correspondencia con hechos y dimensiones del modelo final.

El modelo se estructura como una estrella extendida con dimensiones conformadas y tablas de hechos separadas por granularidad temporal. Las dimensiones principales son tiempo, paÃ­s, grilla espacial y cobertura vegetal, mientras que los hechos se dividen en incendios diarios, meteorologÃ­a diaria, calidad del aire diaria, precipitaciÃ³n mensual y cobertura vegetal anual. Esta separaciÃ³n responde al principio de que las diferencias de granularidad no deben ocultarse ni forzarse a una Ãºnica tabla si ello compromete consistencia o rendimiento.

### Tabla 11. DiseÃ±o lÃ³gico del modelo relacional

| Tipo | Entidad | PropÃ³sito |
|---|---|---|
| DimensiÃ³n | dim_tiempo | Unifica cortes diarios, mensuales y anuales |
| DimensiÃ³n | dim_pais | Permite comparaciÃ³n regional por paÃ­s |
| DimensiÃ³n | dim_grilla | Resuelve integraciÃ³n espacial entre fuentes |
| DimensiÃ³n | dim_cobertura | Agrupa clases IGBP y combustible potencial |
| Hecho | fact_incendios_diario | Resume focos, FRP e intensidad por dÃ­a y celda |
| Hecho | fact_meteorologia_diaria | Resume condiciones meteorolÃ³gicas e Ã­ndice de riesgo |
| Hecho | fact_calidad_aire_diaria | Resume PM10, PM2.5 y AQI por dÃ­a y celda |
| Hecho | fact_precipitacion_mensual | Resume precipitaciÃ³n y anomalÃ­a por mes y celda |
| Hecho | fact_cobertura_vegetal_anual | Resume clase dominante por aÃ±o y celda |

Fuente: elaboraciÃ³n propia.

### Tabla 12. Colecciones NoSQL y propÃ³sito

| ColecciÃ³n | Estructura dominante | PropÃ³sito |
|---|---|---|
| ejecuciones_etl | Documento de log con mÃ©tricas flexibles | Trazabilidad del pipeline y CDC |
| alertas | Documento de evento semiestructurado | Registro de alertas operativas y severidad |
| focos_snapshots | Documento diario autocontenido con array embebido | Consulta del estado diario sin joins |

Fuente: elaboraciÃ³n propia.

### Tabla 13. Reglas de integridad por motor

| Motor | Mecanismo | AplicaciÃ³n en el proyecto |
|---|---|---|
| MySQL | PK / FK | Integridad entre hechos y dimensiones |
| MySQL | CHECK / dominios | Rangos de riesgo, horas vÃ¡lidas, precipitaciÃ³n no negativa |
| MySQL | UNIQUE compuesta | Idempotencia por grano analÃ­tico |
| MongoDB | JSON Schema | Tipos, campos requeridos y dominios bÃ¡sicos |
| Python / Pydantic | ValidaciÃ³n previa | Tipos, rangos, fechas y estructuras antes de cargar |

Fuente: elaboraciÃ³n propia.

### Tabla 14. Campos por fuente de datos

| Fuente | Campos clave | ObservaciÃ³n |
|---|---|---|
| FIRMS | latitude, longitude, acq_date, acq_time, frp, confidence, daynight | Se convierten a foco agregado diario por grilla |
| Open-Meteo | fecha, temperature_2m_max, relative_humidity_2m_min, wind_speed_10m_max, precipitation_sum, et0_fao_evapotranspiration | Base del Ã­ndice de riesgo |
| CAMS | fecha_hora, pm10, pm2_5, european_aqi, aerosol_optical_depth | Se agrega de horario a diario |
| CHIRPS | fecha, precipitacion_mm, punto, paÃ­s | Se conserva a nivel mensual |
| MODIS | aÃ±o, LC_Type1, descripciÃ³n, punto | Se conserva a nivel anual |

Fuente: elaboraciÃ³n propia.

### Tabla 15. Mapeo fuente-destino

| Fuente | Campo origen | TransformaciÃ³n | Destino |
|---|---|---|---|
| FIRMS | acq_date | AgregaciÃ³n diaria | fact_incendios_diario.tiempo_key |
| FIRMS | latitude / longitude | AsignaciÃ³n a celda 0,25Â° | fact_incendios_diario.grilla_key |
| FIRMS | frp | Sum, avg, max por dÃ­a-celda | fact_incendios_diario.frp_total_mw / frp_promedio_mw / frp_max_mw |
| FIRMS | confidence | Mapeo semÃ¡ntico y conteo | fact_incendios_diario.focos_confianza_alta |
| Open-Meteo | fecha | Mapeo a dimensiÃ³n tiempo | fact_meteorologia_diaria.tiempo_key |
| Open-Meteo | temp, humedad, viento, ET0 | NormalizaciÃ³n y ponderaciÃ³n | fact_meteorologia_diaria.indice_riesgo |
| CAMS | pm10, pm2_5 | AgregaciÃ³n diaria | fact_calidad_aire_diaria.pm10_media_ug_m3 / pm2_5_media_ug_m3 |
| CHIRPS | precipitacion_mm | AgregaciÃ³n mensual / anomalÃ­a | fact_precipitacion_mensual.precipitacion_total_mm / anomalia_pct |
| MODIS | LC_Type1 | Mapeo a dimensiÃ³n cobertura | fact_cobertura_vegetal_anual.cobertura_key |

Fuente: elaboraciÃ³n propia.

### Tabla 16. Conflictos de integraciÃ³n y resoluciÃ³n

| Conflicto | ManifestaciÃ³n | ResoluciÃ³n de diseÃ±o |
|---|---|---|
| Granularidad temporal distinta | Evento vs dÃ­a vs mes vs aÃ±o | SeparaciÃ³n en hechos por grano |
| ResoluciÃ³n espacial heterogÃ©nea | Punto, raster, coordenada puntual | Grilla comÃºn de 0,25Â° |
| Identificadores incompatibles | Algunas fuentes no comparten IDs territoriales | DerivaciÃ³n de claves espaciales y de paÃ­s |
| Unidades y escalas distintas | PM10, FRP, precipitaciÃ³n, humedad | NormalizaciÃ³n explÃ­cita y diccionario tÃ©cnico |
| Correcciones histÃ³ricas | Cambios en datos ya cargados | CDC con ventana retrospectiva + hash de lote |
| Nulos parciales | CAMS y variables complementarias | MÃ©tricas de completitud y exclusiÃ³n controlada |

Fuente: elaboraciÃ³n propia.

### Figura 3. Diagrama ER/EER del modelo integrado de destino

![](figures/figura_3_modelo_integrado.svg)

Fuente: elaboraciÃ³n propia.

#### 4.2.1 Modelo relacional como Data Warehouse

El modelo relacional del proyecto cumple rol de Data Warehouse. Se diseÃ±a en coherencia con el rol analÃ­tico ya definido en la arquitectura preliminar y, por tanto, prioriza el rendimiento en consultas y la preservaciÃ³n del histÃ³rico. Esto implica que el modelo no se evalÃºa como un esquema OLTP tradicional, sino como un repositorio analÃ­tico diseÃ±ado para agregaciones, drill-down temporal y cÃ¡lculo de KPIs.

En tÃ©rminos de normalizaciÃ³n, las dimensiones cumplen una normalizaciÃ³n controlada, mientras que el esquema global adopta una desnormalizaciÃ³n justificada consistente con la lÃ³gica estrella. La separaciÃ³n por hechos evita forzar una sola tabla con granularidades incompatibles.

#### 4.2.2 JustificaciÃ³n del motor relacional y aclaraciÃ³n de implementaciÃ³n

La elecciÃ³n del motor relacional responde a criterios de estabilidad, madurez, disponibilidad, soporte de Ã­ndices, constraints y capacidad suficiente para un Data Warehouse de mediana escala. En el marco del proyecto, el motor relacional se utiliza para almacenar hechos y dimensiones, gestionar Ã­ndices y sostener consultas agregadas que luego alimentarÃ¡n KPIs y visualizaciones.

A nivel de diseÃ±o se elaborÃ³ el modelo dimensional canÃ³nico en MySQL 8 con motor InnoDB, claves sustitutas (`*_key`), dimensiones conformadas (`dim_tiempo`, `dim_pais`, `dim_grilla`, `dim_cobertura`) y tablas de hechos separadas por granularidad (`fact_incendios_diario`, `fact_meteorologia_diaria`, `fact_calidad_aire_diaria`, `fact_precipitacion_mensual`, `fact_cobertura_vegetal_anual`). Este modelo se presenta como referencia teÃ³rica y figura en el Anexo A.

A nivel de implementaciÃ³n operativa, sin embargo, el sistema funciona sobre PostgreSQL 16. La razÃ³n es estrictamente prÃ¡ctica: el servidor acadÃ©mico que UTEC asignÃ³ al grupo expone una instancia de PostgreSQL accesible vÃ­a red interna sobre la base `grp03db` (puerto 15434), mientras que no se proporcionÃ³ instancia de MySQL en el mismo entorno. PostgreSQL es funcionalmente equivalente al modelo lÃ³gico planteado: soporta los mismos constraints, Ã­ndices parciales, vistas materializadas y tipos numÃ©ricos exactos necesarios, ademÃ¡s de incorporar el motor de replicaciÃ³n nativo (streaming replication) discutido en la secciÃ³n 4.3.6. La traducciÃ³n entre el DDL MySQL del Anexo A y el DDL PostgreSQL operativo (`sql/ddl/02_schema.sql` del repositorio) es directa: cambian palabras clave concretas (`AUTO_INCREMENT` â†’ `SERIAL`, `ENGINE=InnoDB` desaparece, `ENUM` se reemplaza por `CHECK (col IN (...))`) pero el grano analÃ­tico, las claves naturales y las restricciones de dominio se preservan sin pÃ©rdida. Esta dualidad ilustra una propiedad importante del diseÃ±o: el modelo lÃ³gico se mantiene vÃ¡lido frente a cambios de motor cuando se respetan los principios de hechos por granularidad e idempotencia.

### Figura 4. Esquema estrella del Data Warehouse

![](figures/figura_4_esquema_estrella.svg)

Fuente: elaboraciÃ³n propia.

**DDL del modelo relacional:** ver [Anexo A](ANEXO_A_DDL_MYSQL.md).

### 4.3 Arquitectura, ETL, integridad y mÃ©tricas

#### 4.3.1 Arquitectura detallada

La arquitectura propuesta se organiza en capas: fuentes, ingesta, staging, transformaciÃ³n, persistencia relacional, persistencia documental y capa analÃ­tica. Python actÃºa como la tuberÃ­a del sistema, orquestando extracciÃ³n, limpieza, transformaciÃ³n, carga y automatizaciÃ³n bÃ¡sica. A partir de allÃ­, MySQL se reserva para el modelo estructurado del Data Warehouse y MongoDB para trazabilidad, snapshots, control de CDC y mÃ©tricas de calidad.

La capa analÃ­tica se implementarÃ¡ con Streamlit, orientada a presentar KPIs, grÃ¡ficos temporales, comparaciones espaciales y trazabilidad del pipeline en una interfaz accesible.

### Figura 5. Arquitectura detallada con flujo de datos y componentes

![](figures/figura_5_arquitectura_detallada.svg)

Fuente: elaboraciÃ³n propia.

#### 4.3.2 DiseÃ±o detallado del ETL

El ETL se diseÃ±a como un conjunto de pipelines por fuente, coordinados bajo una secuencia comÃºn: verificaciÃ³n de CDC, extracciÃ³n, validaciÃ³n, transformaciÃ³n, carga y registro. No se presenta aquÃ­ como una â€œcaja negraâ€, sino como el puente formal entre los modelos fuente y el modelo de destino.

1. **Extract.** Cada fuente dispone de un extractor especÃ­fico. FIRMS, Open-Meteo, CAMS, CHIRPS y AppEEARS se consultan mediante API o descarga reproducible.
2. **Validate.** Los registros se validan con modelos estructurales y controles de rango.  
3. **Transform.** Se normalizan tipos, fechas, unidades, dominios y niveles de granularidad. Se calcula el Ã­ndice de riesgo meteorolÃ³gico a partir de temperatura, humedad, viento y sequÃ­a relativa.
4. **Load relacional.** Se aplican upserts o inserciones controladas por clave compuesta en MySQL.  
5. **Load documental.** Se registran logs, alertas y snapshots diarios en MongoDB.  
6. **Audit.** Cada corrida registra mÃ©tricas de volumen, estado, duraciÃ³n y ventana procesada.

#### 4.3.2.1 CDC

El mecanismo de Change Data Capture combina dos estrategias. La primera es una ventana temporal retrospectiva, que permite recuperar datos nuevos o publicados con retraso. La segunda es una verificaciÃ³n de hash por lote, almacenada en MongoDB, que permite detectar correcciones histÃ³ricas en rangos ya procesados. En el prototipo del repositorio ya se implementa un control incremental por watermark; el diseÃ±o final del informe amplÃ­a ese enfoque con verificaciÃ³n por hash para cubrir modificaciones histÃ³ricas.

#### 4.3.2.2 Idempotencia

Los procesos de carga se diseÃ±an bajo el principio de idempotencia, de modo que una reejecuciÃ³n del pipeline no produzca duplicados ni inconsistencias. En este proyecto, esa propiedad se sostiene mediante claves compuestas en las tablas de hechos, operaciones de upsert en la capa relacional y control de lotes en la capa documental. AsÃ­, el CDC y la idempotencia funcionan como mecanismos complementarios.

#### 4.3.3 Reglas de integridad SQL y NoSQL

Las reglas de integridad del sistema se diseÃ±an en tres niveles. Primero, Python y Pydantic validan estructuras y restricciones antes de la carga. Segundo, MySQL impone claves primarias, claves forÃ¡neas, unicidad y restricciones de dominio sobre hechos y dimensiones. Tercero, MongoDB aplica validaciÃ³n estructural con JSON Schema sobre documentos de control, calidad y trazabilidad.

**JSON Schema de las colecciones MongoDB:** ver [Anexo B](ANEXO_B_JSON_SCHEMA_MONGODB.md).

#### 4.3.4 KPIs del sistema

Los KPIs del sistema se derivan directamente de las preguntas analÃ­ticas formuladas en EC1. Deben estar alineados con los objetivos del proyecto, con el modelo de destino y con futuras visualizaciones.

### Tabla 17. KPIs del sistema

| KPI | DescripciÃ³n | Consulta base | Pregunta asociada | VisualizaciÃ³n sugerida |
|---|---|---|---|---|
| Densidad de focos por paÃ­s y mes | Total de focos agregados por paÃ­s / mes | Vista `vw_focos_por_pais_mes` | 1, 2, 3 | Serie temporal comparativa |
| FRP mÃ¡ximo mensual | MÃ¡xima potencia radiativa observada por mes | Hecho de incendios diario agregado | 1, 2 | LÃ­nea + barras |
| Ãndice de riesgo promedio por paÃ­s | Media mensual de Ã­ndice de riesgo | Vista `vw_riesgo_por_pais_mes` | 4, 5 | LÃ­nea comparativa |
| DÃ­as crÃ­ticos | Conteo de dÃ­as con riesgo alto o muy alto | Hecho meteorolÃ³gico diario | 4, 5 | Heatmap calendario |
| PM10 en condiciones de quema | ComparaciÃ³n de PM10 con y sin actividad de focos | Hecho calidad del aire + incendios | 6 | Boxplot / dispersiÃ³n |
| AnomalÃ­a de precipitaciÃ³n | DÃ©ficit o exceso respecto a base histÃ³rica | Hecho precipitaciÃ³n mensual | 8 | Barra divergente |
| Cobertura dominante y combustibilidad | Clase IGBP dominante por celda / aÃ±o | Hecho cobertura vegetal anual | 9, 10 | Mapa categÃ³rico |
| Frescura del pipeline | Diferencia entre fecha de datos y fecha de carga | MongoDB `ejecuciones_etl` | Control operativo | Tarjeta KPI |
| Tasa de registros vÃ¡lidos | Registros vÃ¡lidos / procesados por lote | MongoDB `ejecuciones_etl` | Calidad de pipeline | Gauge o barra |

Fuente: elaboraciÃ³n propia.

#### 4.3.5 Trade-offs tÃ©cnicos documentados

El proyecto documenta sus decisiones como trade-offs y no como elecciones neutras. Adoptar una grilla de 0,25Â° facilita la integraciÃ³n y simplifica los joins, pero sacrifica resoluciÃ³n espacial. Elegir MySQL reduce complejidad operativa y aprovecha una plataforma madura, aunque implica menor especializaciÃ³n analÃ­tica que algunos motores column-oriented. Usar MongoDB para trazabilidad evita forzar documentos variables a un esquema rÃ­gido, pero aÃ±ade el costo de administrar un segundo motor.

### Tabla 18. Trade-offs tÃ©cnicos documentados

| DecisiÃ³n | Ventaja | Costo / riesgo asumido |
|---|---|---|
| Grilla espacial 0,25Â° | Interoperabilidad entre fuentes | PÃ©rdida de resoluciÃ³n respecto al dato original |
| Hechos separados por granularidad | Evita cruces invÃ¡lidos | Mayor complejidad de diseÃ±o |
| MySQL como DW | Simplicidad, madurez, Ã­ndices, constraints | Menor especializaciÃ³n OLAP que motores dedicados |
| MongoDB para trazabilidad | Flexibilidad documental y snapshots autocontenidos | OperaciÃ³n de un segundo motor |
| CDC por ventana + hash | Cubre inserciones y correcciones histÃ³ricas | Requiere metadatos adicionales |
| Streamlit como capa analÃ­tica | Rapidez de desarrollo | Menor control fino que una capa web a medida |

Fuente: elaboraciÃ³n propia.

#### 4.3.6 ReplicaciÃ³n

El diseÃ±o contempla replicaciÃ³n en ambos motores como mecanismo de continuidad operativa ante fallos de un nodo. En EC2 se trata de una decisiÃ³n de arquitectura: se define quÃ© tecnologÃ­a se utilizarÃ¡, cuÃ¡ntos nodos se prevÃ©n y cÃ³mo se garantiza la continuidad del servicio, sin todavÃ­a configurar la infraestructura.

Para PostgreSQL se adopta replicaciÃ³n asÃ­ncrona en streaming con un nodo primario y dos rÃ©plicas de solo lectura. El primario recibe todas las escrituras del ETL y propaga los registros WAL (write-ahead log) hacia las rÃ©plicas en tiempo casi real. La elecciÃ³n de un esquema 1 primario + 2 rÃ©plicas obedece a tres consideraciones: el quÃ³rum mÃ­nimo necesario para detectar particiones de red sin perder disponibilidad, el balance entre costo de almacenamiento y tolerancia a fallos, y la posibilidad de dirigir las consultas de la capa Streamlit y de los KPIs a una rÃ©plica sin afectar el rendimiento de las cargas del ETL. La continuidad del servicio se asegura mediante un proceso de promociÃ³n manual o automatizada de una rÃ©plica a primario en caso de caÃ­da del nodo principal, y por el hecho de que el dashboard puede continuar respondiendo consultas analÃ­ticas sobre la otra rÃ©plica durante el procedimiento. Para el modo asÃ­ncrono se acepta explÃ­citamente una ventana de pÃ©rdida potencial de los Ãºltimos segundos de escritura, lo cual es admisible para un Data Warehouse cuya verdad Ãºltima son las fuentes externas y cuyo ETL puede reprocesar el Ãºltimo lote por idempotencia (secciÃ³n 4.3.2.2).

Para MongoDB se adopta el patrÃ³n canÃ³nico de rÃ©plica set con tres miembros: un primario, un secundario y un Ã¡rbitro (o, alternativamente, tres miembros con datos completos cuando el almacenamiento lo permita). El primario absorbe escrituras del ETL (logs, snapshots, alertas) y los secundarios replican el oplog continuamente. Ante caÃ­da del primario, los miembros que retengan quÃ³rum eligen un nuevo primario automÃ¡ticamente en pocos segundos sin intervenciÃ³n manual. La cantidad mÃ­nima de tres nodos obedece a que MongoDB requiere mayorÃ­a para elegir primario; con dos nodos una particiÃ³n de red dejarÃ­a al cluster sin escritura. Esta arquitectura encaja bien con el rol operacional de MongoDB en el sistema, porque los logs y snapshots requieren alta disponibilidad de escritura aunque la latencia por elecciÃ³n durante una caÃ­da sea aceptable.

A nivel de arquitectura, la replicaciÃ³n implica que cada motor pasa de ser un punto Ãºnico de falla a un cluster de pequeÃ±a escala. La arquitectura detallada (Figura 5) se complementa entonces con un nodo primario y al menos un nodo rÃ©plica por motor, conectados por la red interna de UTEC, y con el ETL Python apuntando siempre al primario para escritura y, opcionalmente, a una rÃ©plica para lecturas analÃ­ticas pesadas.

#### 4.3.7 Sharding

El sharding se incorpora al diseÃ±o como una previsiÃ³n de escalabilidad para los conjuntos de datos de mayor volumen, y no como una decisiÃ³n activa en el alcance acadÃ©mico actual. La razÃ³n es que el volumen actual del proyecto (~20 millones de focos FIRMS y decenas de miles de registros meteorolÃ³gicos para tres paÃ­ses) cabe holgadamente en un Ãºnico nodo PostgreSQL y un Ãºnico primario MongoDB. Sin embargo, la consigna pide identificar dÃ³nde y cÃ³mo se aplicarÃ­a sharding si el sistema se escalara a un alcance mayor (por ejemplo, todo SudamÃ©rica o todo el continente), y esa previsiÃ³n se documenta a continuaciÃ³n.

En PostgreSQL, la tabla candidata es `focos_calor` porque concentra el volumen dominante del Data Warehouse y porque sus consultas analÃ­ticas se hacen casi siempre con filtros temporales. Se elige `fecha_adq` como shard key con estrategia de particionamiento por rango mensual o trimestral. La justificaciÃ³n tÃ©cnica es que esta clave presenta alta cardinalidad (un valor distinto por dÃ­a), distribuye los datos de forma equilibrada entre shards y se alinea con el patrÃ³n de consulta dominante de los KPIs (densidad de focos por mes, comparativa interanual, evoluciÃ³n temporal), lo cual permite que el planificador haga pruning de shards y consulte Ãºnicamente las particiones temporales relevantes. El impacto previsto es positivo en consultas que filtran por rangos de fecha cortos y neutro a leve en consultas que necesitan agregar toda la historia, donde el costo del scan distribuido se compensa con el paralelismo entre shards. Como contraparte, se acepta que las consultas por punto geogrÃ¡fico sin filtro temporal pueden requerir scatter-gather entre todos los shards; ese costo se acota con un Ã­ndice secundario sobre `(latitud, longitud)` dentro de cada particiÃ³n.

En MongoDB, la colecciÃ³n candidata es `focos_snapshots`, que embebe los focos detectados dÃ­a a dÃ­a por paÃ­s. Se elige una shard key compuesta `{ fecha: 1, pais: "hashed" }` por dos razones combinadas. La primera, `fecha` ascendente, mantiene la coherencia temporal del oplog y permite consultas por ventana temporal sin scatter-gather. La segunda, `pais` con hashing, distribuye uniformemente los documentos entre shards para evitar el efecto "hot shard" tÃ­pico de las claves crecientes puras (donde todas las escrituras recientes caerÃ­an en el Ãºltimo shard). El impacto en consultas es favorable cuando se filtra por rango de fechas y paÃ­s, que es el patrÃ³n principal del dashboard. Las consultas que recorren toda la historia para un Ãºnico paÃ­s aÃºn funcionan correctamente porque MongoDB enruta el query al subconjunto de shards que contienen el hash correspondiente. La colecciÃ³n `ejecuciones_etl`, en cambio, se mantiene sin sharding porque su volumen es bajo y su patrÃ³n de acceso es secuencial por fecha de ejecuciÃ³n.

Esta secciÃ³n documenta entonces una arquitectura escalable: el sistema actual no requiere sharding por su tamaÃ±o, pero el modelo estÃ¡ diseÃ±ado de manera que activarlo cuando crezca el volumen sea un cambio operativo sobre las mismas tablas y colecciones, sin reescritura del ETL ni del modelo lÃ³gico.

## 5. Conclusiones

El proyecto define una soluciÃ³n de ingenierÃ­a de datos orientada a integrar incendios forestales, condiciones meteorolÃ³gicas, precipitaciÃ³n, calidad del aire y cobertura vegetal en Uruguay y sus paÃ­ses limÃ­trofes (Brasil y Argentina) durante 2018-2025. La etapa inicial permitiÃ³ delimitar el problema, justificar su relevancia, analizar las fuentes y formular preguntas analÃ­ticas concretas. La etapa de diseÃ±o transformÃ³ ese planteo en una arquitectura tÃ©cnica coherente, con modelo relacional de destino, modelo documental, ETL, CDC, reglas de integridad, mÃ©tricas y criterios de continuidad y escalabilidad.

En tÃ©rminos tecnolÃ³gicos, la soluciÃ³n combina MySQL como repositorio analÃ­tico estructurado y MongoDB como repositorio documental de trazabilidad, apoyÃ¡ndose en Python para la ingestiÃ³n y transformaciÃ³n y en Streamlit para la futura capa de visualizaciÃ³n. Las capacidades documentadas oficialmente por estas herramientas respaldan su uso dentro de la arquitectura propuesta, mientras que la literatura cientÃ­fica consultada fundamenta la selecciÃ³n de variables y la necesidad de un anÃ¡lisis multifuente del fenÃ³meno.

La principal fortaleza del diseÃ±o es la correspondencia explÃ­cita entre preguntas del dominio, fuentes seleccionadas, transformaciones ETL, modelo de destino y KPIs. La principal limitaciÃ³n, por su parte, es que la heterogeneidad temporal y espacial de las fuentes obliga a asumir una estrategia de armonizaciÃ³n que simplifica parte de la variabilidad original. No obstante, esa decisiÃ³n es metodolÃ³gicamente justificable dentro del alcance del proyecto.

La siguiente etapa consistirÃ¡ en implementar esta arquitectura con datos reales completos del perÃ­odo 2018-2025, medir rendimiento, comprobar idempotencia y CDC, recalcular mÃ©tricas de calidad y demostrar la correspondencia entre preguntas, consultas, visualizaciones y resultados mediante evidencia de ejecuciÃ³n y testing.

## Referencias bibliogrÃ¡ficas

Giglio, L., Schroeder, W., & Justice, C. O. (2016). *The collection 6 MODIS active fire detection algorithm and fire products*. Remote Sensing of Environment, 178, 31-41. https://doi.org/10.1016/j.rse.2016.02.054

Jolly, W. M., Cochrane, M. A., Freeborn, P. H., Holden, Z. A., Brown, T. J., Williamson, G. J., & Bowman, D. M. J. S. (2015). *Climate-induced variations in global wildfire danger from 1979 to 2013*. Nature Communications, 6, 7537. https://doi.org/10.1038/ncomms8537

MuÃ±oz-Sabater, J., Dutra, E., AgustÃ­-Panareda, A., Albergel, C., Arduini, G., Balsamo, G., Boussetta, S., Choulga, M., Harrigan, S., Hersbach, H., Martens, B., Miralles, D. G., Piles, M., RodrÃ­guez-FernÃ¡ndez, N. J., Zsoter, E., Buontempo, C., & ThÃ©paut, J.-N. (2021). *ERA5-Land: A state-of-the-art global reanalysis dataset for land applications*. Earth System Science Data, 13(9), 4349-4383. https://doi.org/10.5194/essd-13-4349-2021

Reid, C. E., Brauer, M., Johnston, F. H., Jerrett, M., Balmes, J. R., & Elliott, C. T. (2016). *Critical review of health impacts of wildfire smoke exposure*. Environmental Health Perspectives, 124(9), 1334-1343. https://doi.org/10.1289/ehp.1409277

van der Werf, G. R., Randerson, J. T., Giglio, L., van Leeuwen, T. T., Chen, Y., Rogers, B. M., Mu, M., van Marle, M. J. E., Morton, D. C., Collatz, G. J., Yokelson, R. J., & Kasibhatla, P. S. (2017). *Global fire emissions estimates during 1997-2016*. Earth System Science Data, 9(2), 697-720. https://doi.org/10.5194/essd-9-697-2017

MongoDB. (s. f.). *Replication*. MongoDB Documentation. https://www.mongodb.com/docs/manual/replication/

MongoDB. (s. f.). *Schema validation*. MongoDB Documentation. https://www.mongodb.com/docs/manual/core/schema-validation/

MySQL. (s. f.). *MySQL reference manual*. Oracle. https://dev.mysql.com/doc/en/

Open-Meteo. (s. f.). *Historical weather API*. https://open-meteo.com/en/docs/historical-weather-api

Pydantic. (s. f.). *Models*. Pydantic Documentation. https://pydantic.dev/docs/validation/latest/concepts/models/

Streamlit. (s. f.). *Documentation*. https://docs.streamlit.io/

## Anexos

- **Anexo A.** Script DDL completo de MySQL: [ANEXO_A_DDL_MYSQL.md](ANEXO_A_DDL_MYSQL.md)
- **Anexo B.** JSON Schema de colecciones MongoDB: [ANEXO_B_JSON_SCHEMA_MONGODB.md](ANEXO_B_JSON_SCHEMA_MONGODB.md)
- **Anexo C.** Diagramas de arquitectura y modelo: carpeta `docs/figures/`
- **Anexo D.** Scripts base del ETL en Python: carpeta `etl/`
- **Anexo E.** Ejemplos de logs y metadata CDC: carpeta `etl/load/` y `tests/test_calidad_datos.py`
- **Anexo F.** Consultas analÃ­ticas y KPIs: `sql/queries/01_analiticas.sql` y `nosql/queries/01_consultas.js`
- **Anexo G.** Base de dashboard Streamlit: carpeta `dashboard/`
