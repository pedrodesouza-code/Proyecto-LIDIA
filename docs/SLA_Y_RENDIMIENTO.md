# SLA y rendimiento

Revision actualizada: **2026-05-20**.

Reportes usados:

- `reports/rendimiento_ultimo.json`
- `reports/sql_vs_nosql_real_ultimo.json`
- `reports/carga_completa_ultimo.json`

## SLA definidos

| Dimension | SLA esperado | Justificacion | Estado |
|---|---:|---|---|
| Carga completa local desde datos procesados | <= 15 min | Volumen academico reprocesable | Cumple para lectura/procesamiento local |
| Carga incremental NRT | <= 2 min | Refresco operativo sin reprocesar todo | Cumple en medicion local |
| Consulta analitica interactiva | <= 3000 ms | Uso en dashboard Streamlit | Cumple |
| Consulta de calidad/riesgo por punto | <= 1000 ms | KPI operativo | Cumple |
| Actualizacion minima | Historico diario; NRT cada 1-3 h | Valor operativo de FIRMS/CAMS | Cumple en diseno de scheduler |

## Metricas locales de rendimiento

Ultimo `reports/rendimiento_ultimo.json`:

| Medicion | Resultado | Tiempo promedio |
|---|---:|---:|
| Lectura `firms_procesado.parquet` | `1.946.361` filas | `1104.172 ms` |
| Lectura `meteo_procesado_todos.parquet` | `88.087` filas | `41.821 ms` |
| Lectura `cams_procesado_todos.parquet` | `98.449` filas | `38.159 ms` |
| Q1 focos por mes | `27` meses | `457.157 ms` |
| Q2 ranking dias con focos | `418.747` resultado acumulado | `65.682 ms` |
| Q3 riesgo por punto | `13.969` | `7.882 ms` |
| Q4 PM10 por punto | `47.9617` max promedio | `8.171 ms` |
| Incremental FIRMS ultimos 7 dias | `3.508` registros | `145.293 ms` |
| Carga doble idempotente simulada | `100.000` registros finales | `88.521 ms` |

## Metricas SQL vs NoSQL

Ultimo `reports/sql_vs_nosql_real_ultimo.json`:

| Motor | Consulta | Tiempo promedio | Lectura |
|---|---|---:|---|
| PostgreSQL | Focos por pais | `0.690 ms` | Materializada / agregada |
| PostgreSQL | Focos por mes | `0.936 ms` | Materializada / agregada |
| PostgreSQL | Riesgo por pais | `51.496 ms` | Agregacion analitica |
| MongoDB | Focos por pais embebidos | `3870.447 ms` | Scan documental |
| MongoDB | Focos por pais materializado | `0.606 ms` | Resumen materializado |
| MongoDB | Focos por mes materializado | `1.141 ms` | Resumen materializado |

## Interpretacion tecnica

La medicion muestra un punto importante para defensa: MongoDB con documentos embebidos es flexible pero puede ser mas lento para agregaciones masivas si se consulta sin resumenes. Al materializar resumenes por pais y mes, MongoDB queda en tiempos comparables a PostgreSQL para el uso operacional del dashboard.

PostgreSQL sigue siendo la capa principal para analitica estructurada, integridad, filtros temporales, vistas y agregaciones confiables. MongoDB complementa con snapshots, trazabilidad y documentos autocontenidos.

## Idempotencia y CDC

La suite actual de `tests/test_calidad_datos.py` valida:

- claves naturales;
- ausencia de duplicados logicos;
- doble carga sin duplicacion final;
- deteccion de registros nuevos;
- deteccion de modificaciones.

Resultado actual:

```text
20 PASS / 0 FAIL
```

## Riesgos y limites

- `reports/rendimiento_ultimo.json` mide lectura local sobre Parquet y simulaciones reproducibles.
- `reports/sql_vs_nosql_real_ultimo.json` mide consultas contra motores reales disponibles al momento de la corrida.
- `reports/utec_verificacion_ultimo.json` es evidencia historica del `2026-05-15` y no representa el alcance local actual con Chile.
- Para una defensa con infraestructura institucional, conviene regenerar `utec_verificacion_ultimo.json` si el tribunal exige que Chile este sincronizado en UTEC.
