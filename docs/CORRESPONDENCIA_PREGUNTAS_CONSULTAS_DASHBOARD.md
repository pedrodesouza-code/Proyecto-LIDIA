# Correspondencia preguntas, consultas, visualizaciones y resultados

Este documento conecta las preguntas analiticas definidas en EC1 con consultas SQL/NoSQL
y vistas del dashboard Streamlit.

| Pregunta | Consulta / evidencia | Vista dashboard | Resultado esperado | Limitacion |
|---|---|---|---|---|
| Q1. Cuantos focos de calor se detectaron por mes? | `sql/queries/01_analiticas.sql` Q1 | Resumen General, Focos de Calor | Serie mensual de focos y FRP promedio | FIRMS mide focos termicos, no incendios confirmados |
| Q2. Cuales fueron los dias con mas focos? | SQL Q2 | Focos de Calor, Analisis de Riesgo | Ranking de dias criticos | Puede concentrarse en eventos regionales fuera de Uruguay |
| Q3. Que puntos tuvieron mas dias de riesgo alto/muy alto? | SQL Q3 | Indice de Riesgo, Analisis de Riesgo | Ranking territorial preventivo | Los puntos son representativos, no cobertura continua |
| Q4. Como evoluciona el riesgo mensual por punto? | SQL Q4 | Indice de Riesgo | Estacionalidad del riesgo | Promedios mensuales suavizan extremos diarios |
| Q5. Hay relacion entre riesgo alto y focos detectados? | SQL Q5 | Analisis de Riesgo | Cruce riesgo meteorologico vs focos reales | La union por fecha no prueba causalidad |
| Q6. Cuantos dias superaron el limite OMS de PM10? | SQL Q6 | Calidad del Aire | Dias sobre limite por punto | CAMS/Open-Meteo es aproximacion modelada |
| Q7. Cual es el pronostico de riesgo para 7 dias? | SQL Q7 | Tiempo Real | Ranking de puntos por riesgo forecast | Pronostico puede cambiar con nuevas corridas |
| Q8. Cual es el mes con mayor riesgo historico? | SQL Q8 | Analisis de Riesgo | Meses criticos para planificacion | Depende del periodo historico cargado |
| Q9. En que horas se detectan mas focos? | SQL Q9 | Focos de Calor | Distribucion diurna/nocturna | Hora satelital depende de pasada orbital |
| Q10. Cuales son los focos mas intensos? | SQL Q10 | Focos de Calor | Top eventos por FRP | FRP puede verse afectado por sensor y geometria |

## Consultas NoSQL complementarias

| Necesidad | Consulta Mongo | Valor NoSQL |
|---|---|---|
| Ultimas ejecuciones ETL | `nosql/queries/01_consultas.js` Q1 | Auditoria operacional flexible |
| Alertas activas | Mongo Q2 | Documento con indicadores variables |
| Snapshot del dia mas reciente | Mongo Q3 | Documento autocontenido por fecha |
| Dias con mas de 5 focos | Mongo Q4 | Agregacion rapida sobre snapshots |
| Resumen ETL por fuente y estado | Mongo Q5 | Trazabilidad de pipeline |
| Alertas por nivel en ultimo mes | Mongo Q6 | Seguimiento operacional |
| Riesgo muy alto + focos simultaneos | Mongo Q7 | Correlacion sin joins relacionales |

## Evidencia de dashboard

El dashboard queda alineado al alcance actual del repositorio: `ARG`, `BRA`, `CHL`, `URY` y `36` puntos de monitoreo.

Comando de ejecucion:

```bash
streamlit run dashboard/app.py --server.port 8501
```

URL local:

```text
http://localhost:8501
```

Verificacion realizada:

- pagina responde en `http://localhost:8501`;
- aparece `SINIA-UY`;
- el dashboard consume PostgreSQL si esta disponible;
- si PostgreSQL no responde, usa fallback controlado a Parquet.

## Resultado consolidado

La correspondencia requerida por la consigna queda cubierta asi:

```text
preguntas EC1 -> consultas SQL/NoSQL -> dashboard Streamlit -> resultado numerico -> limitacion
```

Para el informe final, esta tabla puede copiarse como evidencia directa de alineacion
entre problema, arquitectura, persistencia y visualizacion.
