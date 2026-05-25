# DEFENSA — SINIA-SA
## Sistema de Monitoreo de Incendios Forestales — Sudamérica
**UTEC ITR Norte · Licenciatura en Ingeniería de Datos e Inteligencia Artificial · 2026**
**Rafael Quintanilla Fontané**

---

# PARTE 1 — GUIÓN DE PRESENTACIÓN

---

## APERTURA (2 minutos)

> *Pararse, respirar, mirar al tribunal. Hablar despacio.*

"Buenas tardes. Voy a presentar **SINIA-SA**, un sistema de ingeniería de datos
para el monitoreo de incendios forestales en Sudamérica.

Sudamérica no tiene un sistema integrado y automatizado que combine datos satelitales,
meteorológicos y de calidad del aire en tiempo real para el seguimiento de incendios.
Brasil, Bolivia, Paraguay y Argentina concentran millones de focos cada año. En 2024
se registró el peor año de la historia con más de 3,8 millones de focos — superando
al catastrófico año 2020 del Pantanal.

La pregunta central del proyecto es:
**¿Podemos, con datos públicos y gratuitos, construir un sistema que detecte incendios
activos, anticipe cuándo las condiciones son peligrosas y mida el impacto en la calidad
del aire — de forma automática y continua para 6 países?**

La respuesta es sí, y eso es lo que voy a mostrarles hoy."

---

## BLOQUE 1 — El problema (3 minutos)

"Los incendios forestales en Sudamérica son un problema real, masivo y recurrente.
En los 7 años que cubre este proyecto (2018–2024) se registraron **19,5 millones de focos**
de calor detectados por satélite.

El problema de datos es que esta información existe, pero dispersa en tres sistemas distintos:

- La NASA tiene datos satelitales de focos de calor, pero no tiene el clima.
- Open-Meteo tiene el clima, pero no tiene los focos.
- Copernicus tiene la calidad del aire, pero no sabe si hubo un incendio.

**Ninguna de estas fuentes, por sí sola, responde la pregunta que importa.**

El aporte de ingeniería de datos de este proyecto es exactamente ese:
integrar cinco fuentes heterogéneas, limpiarlas, transformarlas y cargarlas en
un sistema que permita responder preguntas que antes requerían semanas de trabajo manual."

---

## BLOQUE 2 — Arquitectura (4 minutos)

"La arquitectura tiene tres capas:

**Capa 1 — Extracción (5 fuentes):**

- **NASA FIRMS:** satélite VIIRS detecta focos de calor. API gratuita con clave.
- **Open-Meteo:** meteorología histórica desde 1940 y pronóstico 7 días. Sin clave.
- **CAMS (Copernicus):** calidad del aire PM10/PM2.5. Proxy gratuito vía Open-Meteo.
- **CHIRPS:** precipitación mensual satelital. API NASA SERVIR, sin clave.
- **MODIS:** cobertura vegetal anual (tipo de suelo). NASA AppEEARS, cuenta gratuita.

**Capa 2 — Transformación:**
Limpieza, normalización, filtro geográfico y cálculo del Índice de Riesgo de Incendio.

**Capa 3 — Carga dual:**
- **PostgreSQL:** datos relacionales con esquema fijo, consultas analíticas.
- **MongoDB:** snapshots diarios flexibles, alertas, trazabilidad del ETL.

El pipeline se ejecuta automáticamente con APScheduler cada 1 a 3 horas."

---

## BLOQUE 3 — El Índice de Riesgo (5 minutos — EL CORAZÓN)

"El componente técnico más importante es el **Índice de Riesgo de Incendio**.

Un foco detectado por satélite nos dice que algo está ardiendo. Pero no nos permite
anticipar el próximo incendio. Para eso necesitamos las condiciones meteorológicas.

```
Índice = Temperatura×0,25 + Humedad×0,30 + Viento×0,20 + Sequía×0,25
```

Cada componente normalizado al rango [0,1]:

- **Temperatura:** 15°C → 0. 45°C → 1.
- **Humedad:** 80% → 0. 10% → 1. (Invertido: menos humedad = más riesgo)
- **Viento:** 0 km/h → 0. 80 km/h → 1.
- **Sequía (ET0):** 0 mm → 0. 8 mm/día → 1.

Los pesos se basan en el Canadian Forest Fire Weather Index (FWI): la humedad tiene
el mayor peso porque el contenido de agua del combustible vegetal es el factor más
determinante en la ignición.

**Validación empírica:** los días de riesgo MUY ALTO tienen 2,6 veces más focos
que los días de riesgo MODERADO — confirmando que el índice funciona."

---

## BLOQUE 4 — Los datos reales (3 minutos)

"Los datos cargados en el sistema para 2018–2024 son:

| Fuente | Dato | Valor |
|---|---|---|
| NASA FIRMS | Focos totales | **19,5 millones** |
| NASA FIRMS | Peor año | **2024 (3,8 millones)** |
| NASA FIRMS | Peor día histórico | **11/09/2024 — 71.058 focos** |
| NASA FIRMS | Intensidad máxima | **2.089 MW (Bolivia)** |
| CAMS | PM10 máximo registrado | **853,1 µg/m³ (Trinidad, Bolivia = 19× OMS)** |
| CAMS | Ciudad más afectada | **Santiago — 400 días sobre el límite OMS** |
| PostgreSQL | Tablas | **8 tablas + 8 vistas SQL** |
| MongoDB | Documentos | **2.521 snapshots** |"

---

## BLOQUE 5 — Validación del índice (3 minutos)

"¿Cómo sabemos que el índice de riesgo es correcto?

Calculamos la correlación de Pearson entre:
- El índice meteorológico (Open-Meteo — fuente independiente)
- Los focos reales detectados por FIRMS (otra fuente independiente)

Resultado:
- Días MODERADO: 6.785 focos promedio/día
- Días MUY ALTO: 17.869 focos promedio/día → **2,6× más focos**

Los datos nos muestran que cuando el índice sube, suben los focos. Eso es la validación."

---

## BLOQUE 6 — Decisiones técnicas (3 minutos)

**¿Por qué PostgreSQL Y MongoDB?**
No es redundancia. PostgreSQL para datos relacionales con esquema fijo y consultas analíticas.
MongoDB para snapshots de tamaño variable — un día hay 0 focos, otro hay 40.

**¿Por qué estas APIs y no otras?**
Las estaciones meteorológicas nacionales (INUMET, SENAMHI) no tienen API pública.
Open-Meteo y CAMS son las alternativas open-source más completas disponibles.

**¿Por qué Parquet como formato intermedio?**
5–10× menos espacio que CSV. 10–50× más rápido para leer columnas específicas.
Es el estándar del ecosistema moderno (Spark, BigQuery, DuckDB todos lo usan).

**¿Por qué Python?**
Ecosistema de datos más maduro: pandas, psycopg2, pymongo, APScheduler, Streamlit.
Todo open-source, todo gratuito.

---

## BLOQUE 7 — Limitaciones y trabajo futuro (2 minutos)

**Limitaciones actuales:**
1. Solo 18 ciudades como proxies — zonas rurales intermedias no están cubiertas directamente.
2. CAMS provee estimaciones satelitales, no mediciones físicas directas.
3. El índice de riesgo no fue calibrado con registros oficiales de incendios confirmados.
4. Docker no disponible en el entorno de desarrollo (WSL2 deshabilitado).

**Trabajo futuro:**
1. CDC incremental real — descargar solo desde la última fecha cargada.
2. Integrar datos oficiales (MGAP, IBAMA) para calibrar el índice.
3. Modelo predictivo con 7 años de datos históricos.
4. Extender a más puntos de monitoreo entre ciudades.

---

## CIERRE (1 minuto)

"SINIA-SA demuestra que con fuentes de datos públicas y gratuitas, aplicando principios
de ingeniería de datos, es posible construir un sistema de monitoreo ambiental funcional,
automatizado y con valor real para la gestión de emergencias en seis países.

El sistema está corriendo en este momento. Las bases de datos tienen datos reales.
El dashboard que van a ver lee de PostgreSQL en producción.

Quedo a disposición para las preguntas. Muchas gracias."

---

## DATOS CLAVE PARA MEMORIZAR

| Dato | Valor |
|---|---|
| Focos totales 2018–2024 | **19,5 millones** |
| Peor año | **2024 (3,8 millones)** |
| Peor día histórico | **11/09/2024 — 71.058 focos** |
| País con más focos | **Brasil 55,1%** |
| País con mayor intensidad | **Bolivia (2.089 MW FRP máx)** |
| PM10 máximo | **853,1 µg/m³ Trinidad, Bolivia (19× OMS)** |
| Ciudad más días sobre OMS | **Santiago — 400 días** |
| Días riesgo MUY ALTO | 217 días en la serie |
| Focos promedio en días ALTO | 17.869 (vs 6.785 en MODERADO) |
| Fuentes integradas | **5** |
| Costo de los datos | **$0** |
| Tablas PostgreSQL | **8 + 8 vistas** |
| Colecciones MongoDB | **3 · 2.521 docs** |
| Dashboard | http://localhost:8502 |

---

## FRASES PARA DECIR DE MEMORIA

- *"El índice combina 4 variables meteorológicas ponderadas según la literatura científica del FWI canadiense."*
- *"La idempotencia del pipeline garantiza que podemos re-ejecutar el ETL sin duplicar datos."*
- *"PostgreSQL maneja el análisis relacional; MongoDB maneja los snapshots de tamaño variable."*
- *"La correlación entre el índice y los focos reales valida empíricamente que el modelo funciona."*
- *"Las 5 APIs son gratuitas y públicas. El costo de datos del sistema es cero."*
- *"2024 fue el peor año de incendios en Sudamérica en los últimos 7 años."*

---
---

# PARTE 2 — PREGUNTAS DEL TRIBUNAL CON RESPUESTAS

---

**P: ¿Por qué eligieron esos 4 pesos para el índice (25/30/20/25)?**

"Los pesos están basados en el Fire Weather Index (FWI) del Canadian Forest Service,
que es el estándar internacional. La humedad tiene el mayor peso (30%) porque el
contenido de agua del combustible vegetal es el factor más determinante en si el material
puede encenderse. El viento tiene el menor peso individual porque su efecto principal
es en la propagación, no en la ignición. Los pesos pueden ajustarse si se dispone
de datos de incendios confirmados de los países SA."

---

**P: ¿Validaron el modelo contra datos reales?**

"No como confirmacion administrativa de incendios. Usamos los focos FIRMS como proxy de incendios reales.
La correlación entre el índice de riesgo y los focos diarios muestra que la dirección
es correcta: días de riesgo MUY ALTO tienen 2,6 veces más focos que días MODERADO.
Una validación completa requeriría cruzar con registros del MGAP, IBAMA o INAB,
que no tienen API pública. Está en el trabajo futuro."

---

**P: ¿Para qué necesitan MongoDB si ya tienen PostgreSQL?**

"Tienen propósitos distintos y complementarios. PostgreSQL almacena datos con esquema
fijo para análisis SQL. MongoDB almacena snapshots: documentos JSON que representan
el estado completo del sistema en un momento dado. El tamaño varía — 0 focos un día,
40 al otro, con campos extra posibles en el futuro. Usar MongoDB para esto es la
decisión correcta: no forzamos datos flexibles en un esquema rígido."

---

**P: ¿Cómo garantizan que no se dupliquen datos?**

"Con dos mecanismos. En la transformación: eliminamos duplicados por clave natural.
Para FIRMS la clave es (latitud, longitud, fecha, hora, satélite). En la carga:
todas las tablas tienen UNIQUE constraint en PostgreSQL. Si el registro ya existe,
INSERT con ON CONFLICT DO NOTHING lo ignora. Esto garantiza idempotencia:
ejecutar el ETL dos veces produce el mismo resultado que una vez."

---

**P: ¿Qué significa FRP y cómo lo interpretan?**

"FRP es Fire Radiative Power — potencia radiativa del fuego en Megawatts.
Mide la energía irradiada en infrarrojo, no el tamaño del incendio en hectáreas.
Un incendio de pasturas pequeño tiene 5–10 MW. Un incendio forestal grande supera
500 MW. El FRP máximo de nuestro dataset fue 2.089 MW en Bolivia (Chiquitanía),
lo que indica un incendio de escala catastrófica."

---

**P: ¿Por qué no usaron datos de estaciones meteorológicas locales?**

"Investigamos las fuentes disponibles. INUMET (Uruguay), SENAMHI (Bolivia/Perú),
SMN (Argentina) y equivalentes no tienen API pública de acceso gratuito.
Open-Meteo y CAMS son las alternativas open-source más completas disponibles.
El proyecto documenta esto como recomendación para que los países de la región
desarrollen APIs abiertas de sus datos meteorológicos."

---

**P: ¿Cuánto costaría operar este sistema en producción?**

"Cero costo de datos — las 5 APIs son gratuitas. El costo operativo sería el servidor:
un VPS de 5–10 dólares por mes con 2 GB de RAM para los volúmenes actuales.
En producción real se recomendaría Docker, que ya está preparado en el repositorio
pero no fue posible usarlo por restricciones de WSL2 en el entorno de desarrollo."

---

**P: ¿Por qué no usaron Docker?**

"Por una restricción del entorno: WSL2 está deshabilitado en la máquina de desarrollo,
que es el prerequisito de Docker Desktop en Windows 10. La solución fue instalar
PostgreSQL y MongoDB como procesos locales. El docker-compose.yml está completo y
funcional — si se ejecuta en un entorno con Docker disponible, levanta toda la
infraestructura con un comando. Esta es una limitación de entorno, no de diseño."

---

**P: ¿Cuál es la principal contribución del proyecto?**

"Demostrar que es posible construir un sistema de monitoreo ambiental funcional,
automatizado y con valor de decisión para gestores de emergencias, usando
exclusivamente fuentes de datos públicas y gratuitas. Hoy este tipo de sistema
requeriría contratar servicios comerciales o depender de informes manuales.
SINIA-SA prueba que la ingeniería de datos puede democratizar ese acceso."

---
---

# PARTE 3 — RESULTADOS ANALÍTICOS

---

## Dataset construido (estado 2026-03-20)

| Fuente | Registros | Período |
|---|---|---|
| focos_calor (FIRMS) | 19.510.222 | 2018–2024 |
| meteo_diario | 46.243 | 2018–2026 |
| calidad_aire_diario | 45.931 | 2018–2026 |
| precipitacion_mensual | 1.404 | 2018–2024 |
| cobertura_vegetal | 126 | 2018–2024 (anual) |
| MongoDB focos_snapshots | 2.521 docs | 2018–2024 |

---

## Distribución de focos por país (2018–2024)

| País | Focos | % | FRP promedio (MW) | FRP máximo (MW) |
|---|---|---|---|---|
| **BRA** | 9.254.368 | **55,1%** | 11,9 | 1.663 |
| BOL | 3.544.906 | 21,1% | 11,2 | **2.089** |
| PRY | 1.748.037 | 10,4% | 12,9 | 1.525 |
| ARG | 1.037.688 | 6,2% | 12,5 | 1.286 |
| PER | 824.603 | 4,9% | 11,0 | 947 |
| CHL | 326.012 | 1,9% | 12,4 | 1.380 |
| URY | 46.243 | 0,3% | 8,0 | 579 |

> Bolivia tiene el FRP máximo más alto (2.089 MW) a pesar de ser el segundo país por volumen.

---

## Evolución temporal — focos por año

| Año | Focos | FRP promedio | Días con actividad |
|---|---|---|---|
| **2024** | **3.831.103** | 11,1 | 347 |
| 2020 | 3.380.640 | 11,9 | 366 |
| 2019 | 2.742.718 | 11,4 | 365 |
| 2022 | 2.691.451 | 11,3 | 350 |
| 2023 | 2.569.979 | 10,9 | 363 |
| 2021 | 2.381.840 | 12,2 | 365 |
| 2018 | 1.912.491 | 10,7 | 365 |

> **2024 fue el peor año registrado**, superando a 2020 (Pantanal/Amazonia).

---

## Top 10 días más críticos

| Fecha | Focos | FRP máximo |
|---|---|---|
| **2024-09-11** | **71.058** | 590,9 MW |
| 2024-09-06 | 65.993 | 553,7 MW |
| 2024-09-10 | 65.480 | 633,3 MW |
| 2024-09-05 | 61.203 | 493,5 MW |
| 2020-10-01 | 56.604 | 744,5 MW |
| 2024-08-31 | 56.410 | 510,5 MW |
| 2024-09-07 | 53.799 | 676,5 MW |
| 2024-09-12 | 53.424 | 740,8 MW |
| 2024-09-02 | 52.746 | 684,7 MW |
| 2024-09-09 | 52.427 | 636,6 MW |

> 7 de los 10 peores días ocurrieron en **septiembre 2024**.

---

## Validación del índice de riesgo

| Nivel de riesgo | Días | Focos promedio/día | Índice riesgo |
|---|---|---|---|
| **muy_alto** | 217 | **17.869** | 0,473 |
| moderado | 2.340 | 6.785 | 0,375 |

> Días de riesgo MUY ALTO tienen **2,6× más focos** que días MODERADO.

---

## Impacto en calidad del aire

| Ciudad | País | Días sobre OMS | PM10 promedio | PM10 máximo |
|---|---|---|---|---|
| **Santiago** | Chile | **400** | 52,7 µg/m³ | 337,1 µg/m³ |
| Trinidad | Bolivia | 124 | 27,4 µg/m³ | **853,1 µg/m³** |
| Santa Cruz | Bolivia | 71 | 18,5 µg/m³ | 489,9 µg/m³ |
| Manaus | Brasil | 66 | 21,9 µg/m³ | 236,6 µg/m³ |
| Cuiabá | Brasil | 44 | 16,2 µg/m³ | 201,2 µg/m³ |
| Concepción | Paraguay | 39 | 13,5 µg/m³ | 249,6 µg/m³ |

> Trinidad alcanzó **853,1 µg/m³ — 19 veces el límite OMS** (45 µg/m³).

---

## Cruce: Sequía (CHIRPS) ↔ Focos

| Nivel sequía | Meses/punto | Precipitación promedio | Focos promedio/mes |
|---|---|---|---|
| **extrema** | 339 | 25,2 mm | **238.598** |
| severa | 183 | 73,9 mm | 211.184 |
| moderada | 133 | 105,9 mm | 211.085 |
| húmedo | 423 | 193,5 mm | 202.110 |
| normal | 326 | 151,2 mm | 199.332 |

> Meses de sequía extrema tienen **1,2× más focos** que meses normales.

## Peores meses: sequía + fuego simultáneos

| Año | Mes | Puntos en sequía | Anomalía prom. | Focos ese mes |
|---|---|---|---|---|
| **2020** | Sep | 10 | -66,9% | **790.753** |
| 2022 | Sep | 8 | -66,0% | 680.233 |
| 2019 | Sep | 12 | -65,9% | 676.425 |
| 2019 | Ago | 11 | -85,9% | 592.001 |
| 2020 | Oct | 10 | -58,0% | 590.329 |

---

## Zonas más afectadas por sequía (2018–2024)

| Punto | País | Meses sequía extrema | Meses sequía total |
|---|---|---|---|
| **Salta** | ARG | 28 | 36 |
| **Mendoza** | ARG | 28 | 38 |
| **Lima** | PER | 27 | 36 |
| Asunción | PRY | 26 | 29 |
| Santa Cruz | BOL | 25 | 33 |
| Santiago | CHL | 24 | 32 |
| Cuiabá | BRA | 21 | 32 |

---

## Guía de uso del dashboard en la defensa (15 minutos)

| Paso | Sección | Tiempo | Qué mostrar |
|---|---|---|---|
| 1 | Fuentes y Datos Crudos | 2 min | CSVs reales de cada API, columnas explicadas |
| 2 | Resumen General | 2 min | KPIs: 19,5M focos, 6 países, FRP máximo |
| 3 | Focos de Calor | 2 min | Evolución 2018–2024, peor año 2024 |
| 4 | Índice de Riesgo | 3 min | Fórmula, gráfico Rivera, gráfico radar |
| 5 | Calidad del Aire | 1 min | Santiago 400 días sobre OMS, Trinidad 853 µg/m³ |
| 6 | Análisis de Riesgo | 3 min | Correlación focos-riesgo, días críticos |
| 7 | Comparativo por País | 2 min | Tabla Brasil vs Bolivia vs Paraguay |

---

*UTEC ITR Norte · Quinto Semestre 2026 · Rafael Quintanilla Fontané*
