# Auditoria y Cronograma

> Nota 2026-05-20: este documento es una auditoria historica del 11/05. No representa el estado actual del proyecto. Para defensa usar `docs/ESTADO_ACTUAL_PROYECTO_2026-05-20.md`.

Fecha de corte: 2026-05-11

## Metodologia

La auditoria se baso en:

- Consigna oficial del curso en `Proyecto_Ingeniería_de_Datos_2026.pdf`
- Documentacion principal del repositorio
- Revision de codigo en ETL, SQL, dashboard, Docker y tests
- Verificacion operativa local y remota realizada el 2026-05-11
- Ejecucion real de `python tests/test_calidad_datos.py`

## Diagnostico Ejecutivo

El proyecto tiene una base tecnica solida y ya resolvio una parte importante del problema:

- integra fuentes reales y heterogeneas
- tiene pipeline ETL modular en Python
- usa persistencia poliglota PostgreSQL + MongoDB
- cuenta con dashboard en Streamlit
- tiene datos reales cargados localmente

En la auditoria del 2026-05-11 todavia no estaba cerrado para defensa o entrega final. Los principales riesgos detectados entonces estaban en:

- coherencia entre alcance documentado y datos reales
- calidad e idempotencia del flujo meteorologico
- estabilidad operativa de Mongo local
- despliegue UTEC todavia no ejecutado en esa fecha
- requisitos de replicacion y sharding solo documentados, no configurados

## Hallazgos Criticos

### 1. Replicacion y sharding no estan implementados en la arquitectura operativa

La consigna pide configurar replicacion en ambos motores e implementar o simular sharding. La implementacion actual levanta un solo contenedor PostgreSQL y un solo contenedor MongoDB en `docker/docker-compose.yml`, sin replicas, sin replica set y sin cluster.

Referencias:

- `docker/docker-compose.yml`
- `Proyecto_Ingeniería_de_Datos_2026.pdf`
- `docs/PROYECTO_FINAL_EC1_EC2.md`

Impacto observado el 2026-05-11:

- brecha de infraestructura a cerrar antes de la defensa
- la defensa queda expuesta si se afirma que esta operativo y no solo diseniado

### 2. El proyecto no esta desplegado en UTEC

La verificacion remota realizada el 2026-05-11 mostro conectividad correcta a `10.200.245.40`, pero la base remota `grp03db` no contiene aun el esquema ni los datos de SINIA. Solo se observaron tablas de ejemplo en PostgreSQL y la coleccion `eventos` en MongoDB.

Impacto observado el 2026-05-11:

- hoy la fuente de verdad real del proyecto es el entorno local
- la puesta en produccion academica debia ejecutarse antes del cierre final

### 3. El alcance del proyecto es inconsistente entre codigo, datos y documentacion

Hoy conviven varias versiones del alcance:

- `config/settings.py` define 3 paises: Uruguay, Brasil y Argentina
- `dashboard/app.py` expone 6 paises SA y ademas muestra "6 SA + Uruguay"
- `sql/ddl/02_schema.sql` comenta 3 paises, pero el sistema operativo real tiene 7 en `paises_referencia`
- `firms_procesado.parquet` contiene 8 codigos pais (`ARG`, `BOL`, `BRA`, `CHL`, `OTR`, `PER`, `PRY`, `URY`)

Impacto:

- rompe coherencia narrativa de la solucion
- complica la defensa y la validacion de calidad
- hace fallar pruebas que asumen solo Uruguay

## Hallazgos Altos

### 4. Las pruebas de calidad no pasan sobre los datos actuales

La ejecucion real de `python tests/test_calidad_datos.py` el 2026-05-11 fallo con al menos estos casos:

- `test_meteo_sin_duplicados_por_punto_fecha`: 1638 duplicados
- `test_firms_coordenadas_en_uruguay`: 3827428 focos fuera del bounding box de Uruguay
- `test_meteo_carga_doble_sin_duplicados`: falla de idempotencia (`25945 -> 24307`)

Interpretacion:

- o hay duplicados reales en meteorologia
- o el grano asumido por la prueba no coincide con el grano real del dataset
- el test geografico esta desalineado con el alcance regional actual

### 5. La suite de testing tiene defectos de implementacion

Problemas detectados en `tests/test_calidad_datos.py`:

- el conteo de invalidos en `test_firms_confianza_valida` usa `int(~serie.isin(...).sum())`, lo que produce valores negativos por precedencia de operadores
- el logger imprime caracteres como `✓`, `✗` y flechas que rompen la salida en consolas CP1252
- la suite valida Parquet procesado, no las tablas de PostgreSQL ni las colecciones de MongoDB

Impacto:

- resultados poco confiables
- trazabilidad de calidad en proceso de cierre
- evidencia de testing debil para defensa

### 6. La documentacion principal no esta completamente alineada con la implementacion viva

Se detectaron diferencias relevantes:

- varios documentos centrales siguen describiendo MySQL como motor principal, mientras que la operacion real usa PostgreSQL
- `README.md` menciona un volumen aproximado de `~365 registros/año por tabla principal`, inconsistente con los millones de filas actuales en focos
- el documento final EC1/EC2 mezcla diseno teorico en MySQL con operacion real en PostgreSQL; esto es defendible, pero hoy necesita una explicacion mas limpia y consistente

Impacto:

- riesgo alto de contradiccion en defensa o correccion docente

## Hallazgos Medios

### 7. Mongo local no esta estable como servicio

Al momento del corte, el servicio `MongoDB` local figura `Stopped` y `Disabled`. Aunque Compass ya se conecto en etapas previas, hoy la operacion local no esta garantizada de forma persistente.

Impacto:

- el entorno local depende de arranques manuales
- complica pruebas repetibles y demos

### 8. Streamlit existe y esta integrado, pero el arranque local no esta totalmente domesticado

La app tiene una estructura clara y consume principalmente PostgreSQL con fallback a Parquet, pero levantarla de manera automatizada en esta maquina dio friccion operativa.

Impacto:

- la capa analitica esta, pero el flujo de demo aun necesita simplificacion

## Fortalezas

### 1. Arquitectura tecnica bien encaminada

- ETL modular por fuente y por etapa
- configuracion externa con `.env`
- carga idempotente por `ON CONFLICT` en PostgreSQL
- validacion y trazabilidad operativa en MongoDB

### 2. Persistencia relacional madura

El entorno local en PostgreSQL ya tiene:

- tablas del dominio
- vistas analiticas
- volumen real util para defensa
- evidencias de consultas comparativas y temporales

### 3. Dashboard con narrativa analitica real

La app Streamlit ya cubre:

- resumen general
- focos de calor
- indice de riesgo
- calidad del aire
- comparativo por pais
- tiempo real
- fuentes y datos crudos

### 4. Documentacion abundante

Aunque hoy requiere consolidacion, el repositorio tiene mucho material reutilizable para informe, defensa y onboarding.

## Estado por Componente

### Dominio y fuentes

Estado: fuerte

- tema bien elegido y tecnicamente justificable
- 5 fuentes reales y heterogeneas
- buena base para preguntas analiticas

### ETL Python

Estado: bueno con ajustes

- modularidad correcta
- CDC e idempotencia presentes en diseno y en proceso de verificacion final
- necesita corregir meteo y consolidar pruebas

### PostgreSQL

Estado: fuerte

- motor principal real del proyecto
- datos cargados localmente
- vistas analiticas disponibles

### MongoDB

Estado: medio

- modelo documental razonable
- colecciones utiles para trazabilidad
- operacion local inestable
- poco peso hoy en la interfaz principal

### Streamlit

Estado: medio-bueno

- buena estructura funcional
- narrativa analitica consistente
- falta simplificar el arranque y estabilizar la demo local

### Docker e infraestructura

Estado: medio-bajo

- compose simple y util para desarrollo
- no cubre replicacion ni cluster

### Testing

Estado: medio-bajo

- existe suite
- valida dimensiones importantes
- hoy no pasa completo y necesita correccion metodologica

### UTEC / despliegue

Estado al 2026-05-11: bajo

- conectividad lograda
- configuracion remota preparada
- despliegue real programado para el cierre final

## Conclusion de la Auditoria

El proyecto esta avanzado y tiene sustancia real. No esta en estado "verde final", pero tampoco esta roto. Hoy lo describiria como:

**tecnicamente promisorio, localmente funcional en su nucleo, pero todavia inconsistente en testing, relato de alcance e infraestructura de entrega.**

Si se corrigen los puntos criticos en el orden correcto, es totalmente defendible.

## Cronograma Recomendado

Supuesto: plan intensivo de 14 dias a partir del 2026-05-11.

### Fase 1 - Consolidacion del alcance y del relato

Fechas: 2026-05-11 a 2026-05-12

Objetivos:

- decidir el alcance definitivo del proyecto: 3 paises o 6/7 paises
- alinear `config/settings.py`, SQL, dashboard y documento final
- definir una unica historia oficial para la defensa

Entregables:

- alcance unificado
- lista de paises cerrada
- notas de defensa corregidas

### Fase 2 - Correccion de calidad de datos y testing

Fechas: 2026-05-13 a 2026-05-15

Objetivos:

- corregir duplicados de meteorologia o redefinir el grano correctamente
- corregir tests desalineados con el alcance regional
- arreglar `test_firms_confianza_valida`
- dejar la suite ejecutable sin errores de codificacion

Entregables:

- `tests/test_calidad_datos.py` estable
- nuevo `resultados_tests.json`
- evidencia de pruebas sobre datos actuales

### Fase 3 - Estabilizacion operativa local

Fechas: 2026-05-16 a 2026-05-17

Objetivos:

- dejar Mongo local arrancable sin friccion
- dejar Streamlit local con un flujo de arranque claro
- verificar recorrido completo: ETL -> PostgreSQL -> MongoDB -> Streamlit

Entregables:

- demo local repetible
- checklist de arranque local

### Fase 4 - Despliegue academico en UTEC

Fechas: 2026-05-18 a 2026-05-19

Objetivos:

- crear esquema SINIA en `grp03db`
- cargar PostgreSQL remoto
- cargar Mongo remoto sin tocar colecciones ajenas
- validar consultas minimas remotas

Entregables:

- UTEC con esquema y datos del proyecto
- evidencia de conexion y carga

### Fase 5 - Requisitos de infraestructura para defensa

Fechas: 2026-05-20 a 2026-05-21

Objetivos:

- resolver como se va a defender replicacion y sharding
- opcion A: implementacion minima local o simulada
- opcion B: documentacion tecnica mas evidencia reproducible de simulacion

Entregables:

- narrativa cerrada sobre replicacion
- narrativa cerrada sobre sharding
- evidencia tecnica suficiente para tribunal

### Fase 6 - Cierre documental y defensa

Fechas: 2026-05-22 a 2026-05-24

Objetivos:

- actualizar informe principal
- corregir contradicciones MySQL/PostgreSQL
- preparar defensa oral y demo
- preparar plan B por si falla UTEC o Mongo

Entregables:

- documento final coherente
- demo ensayada
- guion de defensa

## Prioridad Recomendada

Orden sugerido de trabajo:

1. Alcance oficial del proyecto
2. Testing y meteo duplicado
3. Mongo local y Streamlit local
4. Deploy a UTEC
5. Replicacion/sharding
6. Defensa final
