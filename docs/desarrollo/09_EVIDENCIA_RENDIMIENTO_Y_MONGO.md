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
mongo_estado = ok
mongo_metricas = 6
```

MongoDB local quedo activo usando `mongod.exe` nativo de Windows, sin depender
de Docker Desktop.

## 5. Evidencia PostgreSQL medida

Del reporte `reports/sql_vs_nosql_real_ultimo.json`:

| Consulta PostgreSQL | Tiempo promedio | Resultado |
|---|---:|---|
| Focos por pais | `3.252 ms` | ARG, BRA, URY |
| Focos por mes | `2.920 ms` | `255` filas |
| Ejecuciones ETL | `2.620 ms` | `72` ejecuciones |
| Riesgo por pais | `65.374 ms` | promedio por pais |

Lectura para defensa:

> PostgreSQL responde consultas agregadas y materializadas en tiempos muy bajos.
> Esto justifica los indices y vistas materializadas para el dashboard.

## 6. Estado MongoDB local

Estado final:

```text
localhost:27017 -> True
MongoDB local conectado: sinia_uy
colecciones: alertas, ejecuciones_etl, focos_snapshots
```

MongoDB se levanto con el binario nativo:

```text
C:\Program Files\MongoDB\Server\6.0\bin\mongod.exe
```

Se cargo MongoDB local con:

```bash
python etl/load/load_mongo.py
python scripts/optimizar_mongo_resumenes.py
```

Resultado local:

```text
focos_snapshots = 347
focos_resumen_pais = 3
focos_resumen_mes = 36
ejecuciones_etl = 1
```

Lectura para defensa actualizada:

> MongoDB local esta operativo sin Docker. Se cargaron snapshots reales desde
> Parquet, se crearon resumenes materializados y se valido CDC documental con
> insercion y limpieza controlada.

## 7. Comparacion Mongo embebido vs materializado

Del reporte `reports/sql_vs_nosql_real_ultimo.json`:

| Consulta MongoDB | Tiempo promedio | Resultado |
|---|---:|---|
| Focos por pais embebidos | `9630.797 ms` | ARG, BRA, URY |
| Focos por pais materializado | `4.472 ms` | ARG, BRA, URY |
| Snapshots por mes | `4.783 ms` | `12` |
| Focos por mes materializado | `1.759 ms` | `36` |
| Ejecuciones ETL | `1.740 ms` | `1` |
| Snapshots totales | `2.482 ms` | `347` |

Frase de defensa:

> La comparacion demuestra por que materializamos resumenes en MongoDB. Recorrer
> arrays embebidos completos es mucho mas costoso; consultar resumenes
> materializados responde en milisegundos.

## 8. Evidencia MongoDB UTEC disponible

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

## 9. Como levantar demo Mongo local

Opcion recomendada sin Docker:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/levantar_mongo_nativo.ps1
python etl/load/load_mongo.py
python scripts/optimizar_mongo_resumenes.py
python scripts/comparar_sql_nosql_real.py
python scripts/evidenciar_cdc_ec3.py
```

El script usa:

```text
tmp/mongo-local-db
tmp/mongo-local-log/mongod.log
```

Estos directorios son temporales locales y no se versionan.

Opcion Docker, si WSL esta funcionando:

Si se quiere hacer demo local completa:

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env.example up -d mongo
python scripts/comparar_sql_nosql_real.py
python scripts/evidenciar_cdc_ec3.py
```

Si Docker Desktop esta apagado, primero abrir Docker Desktop y esperar que el
engine Linux este disponible.

Si aparece `Wsl/0x80070422`, resolver primero Windows/WSL:

```powershell
wsl --status
wsl --shutdown
```

Si sigue fallando, habilitar o reinstalar WSL/Docker Desktop desde Windows.
Ese paso es de sistema operativo, no de codigo del proyecto.

## 10. Como explicarlo al profesor

Si pregunta por el bloqueo Docker/WSL:

> Docker dependia de WSL y Windows devolvia `Wsl/0x80070422`. Para no depender
> de ese servicio, levantamos MongoDB nativo con `mongod.exe`. El resultado final
> es Mongo local operativo en `localhost:27017`.

## 11. Cierre

Con estos reportes queda cubierta la evidencia de rendimiento actualizada y la
comparacion SQL/NoSQL local completa. PostgreSQL queda medido en vivo; MongoDB
queda cargado con snapshots reales, resumenes materializados y prueba CDC
documental.
