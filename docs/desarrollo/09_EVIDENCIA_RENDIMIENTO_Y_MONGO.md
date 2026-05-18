# Evidencia de rendimiento y MongoDB

Este documento resume la evidencia generada para rendimiento preliminar,
comparacion SQL/NoSQL y estado de MongoDB local.

## 1. Reportes generados

Se regeneraron los reportes:

```text
reports/rendimiento_ultimo.json
reports/rendimiento_20260517_213053.json
reports/sql_vs_nosql_real_ultimo.json
reports/sql_vs_nosql_real_20260517_213124.json
```

## 2. Rendimiento general

El script ejecutado fue:

```bash
python scripts/medir_rendimiento.py
```

Resultado:

```text
consultas_medidas = 12
sla_consulta_ms = 3000
```

Lectura para defensa:

> El proyecto mide rendimiento de lectura de archivos procesados, consultas
> analiticas, carga incremental e idempotencia. Las consultas medidas quedan por
> debajo del SLA de 3000 ms.

## 3. Ejemplos de metricas obtenidas

Del reporte `reports/rendimiento_ultimo.json`:

| Metrica | Tiempo promedio | Resultado |
|---|---:|---:|
| Lectura FIRMS procesado | `475.071 ms` | `1.836.537` filas |
| Focos por mes | `346.579 ms` | `12` meses |
| Ranking dias con focos | `49.441 ms` | `417.340` |
| Riesgo por punto | `2.775 ms` | `5.748` |
| PM10 por punto | `1.897 ms` | `21.74` |
| Incremental ultimos 7 dias | `133.141 ms` | `12.145` |
| Simulacion idempotente FIRMS | `70.812 ms` | `100.000` |

## 4. Comparacion SQL vs NoSQL

El script ejecutado fue:

```bash
python scripts/comparar_sql_nosql_real.py
```

Resultado:

```text
postgres_estado = ok
postgres_metricas = 4
mongo_estado = error
mongo_metricas = 0
```

Esto no invalida el proyecto: significa que PostgreSQL local estaba activo y
MongoDB local no estaba escuchando en `localhost:27017` durante la prueba.

## 5. Evidencia PostgreSQL medida

Del reporte `reports/sql_vs_nosql_real_ultimo.json`:

| Consulta PostgreSQL | Tiempo promedio | Resultado |
|---|---:|---|
| Focos por pais | `3.030 ms` | ARG, BRA, URY |
| Focos por mes | `2.389 ms` | `255` filas |
| Ejecuciones ETL | `3.438 ms` | `72` ejecuciones |
| Riesgo por pais | `26.090 ms` | promedio por pais |

Lectura para defensa:

> PostgreSQL responde consultas agregadas y materializadas en tiempos muy bajos.
> Esto justifica los indices y vistas materializadas para el dashboard.

## 6. Estado MongoDB local

Prueba de puerto:

```text
localhost:27017 -> False
```

Docker Desktop tampoco estaba activo:

```text
dockerDesktopLinuxEngine no disponible
```

Lectura para defensa:

> MongoDB no fallo por estructura de datos ni por schema. El servicio local no
> estaba levantado. La evidencia documental de MongoDB real queda respaldada por
> los reportes UTEC ya generados.

## 7. Evidencia MongoDB UTEC disponible

Usar:

```text
reports/utec_verificacion_ultimo.json
```

Ese reporte muestra:

| Control MongoDB UTEC | Resultado |
|---|---:|
| `focos_snapshots` | `352` |
| `focos_resumen_pais` | `3` |
| `focos_resumen_mes` | `39` |
| `snapshots_con_pais` | `352` |
| `snapshots_sin_pais` | `0` |
| `ejecuciones_etl` | `3` |

Frase de defensa:

> Para MongoDB tenemos evidencia en servidor UTEC: colecciones creadas,
> snapshots reales, resumenes materializados y validacion de que los documentos
> conservan el pais dentro de los focos embebidos.

## 8. Como completar demo Mongo local

Si se quiere hacer demo local completa:

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env.example up -d mongo
python scripts/comparar_sql_nosql_real.py
python scripts/evidenciar_cdc_ec3.py
```

Si Docker Desktop esta apagado, primero abrir Docker Desktop y esperar que el
engine Linux este disponible.

## 9. Como explicarlo al profesor

Si pregunta por el `mongo_estado = error`:

> Ese error no corresponde al modelo NoSQL. Corresponde a conectividad local: el
> puerto `27017` no estaba activo. Por eso el script ahora deja el estado de
> Mongo explicitado y no mezcla un problema de servicio con un problema de
> diseno. La evidencia real de Mongo en UTEC esta en
> `reports/utec_verificacion_ultimo.json`.

## 10. Cierre

Con estos reportes queda cubierta la evidencia de rendimiento actualizada y una
comparacion SQL/NoSQL robusta ante fallos de servicio local. PostgreSQL queda
medido en vivo; MongoDB queda documentado con evidencia UTEC y con pasos claros
para completar demo local cuando el servicio este levantado.
