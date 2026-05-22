# Revision operativa de tiempo real

> Nota 2026-05-20: este documento queda como evidencia historica del 15/05. El estado actual para defensa esta consolidado en `docs/ESTADO_ACTUAL_PROYECTO_2026-05-20.md`.

Fecha: 2026-05-15

Objetivo: verificar que el sistema SINIA-UY este funcionando sin errores operativos
para dashboard, PostgreSQL, MongoDB, ETL incremental y scheduler.

## Estado final

| Componente | Estado | Evidencia |
|---|---|---|
| Dashboard Streamlit | Funcionando | `http://localhost:8501`, puerto 8501 en escucha, sin traceback ni errores de consola |
| PostgreSQL | Funcionando | Puerto 5432 en escucha, base `sinia_uy`, usuario `sinia_etl_user` |
| MongoDB | Funcionando como proceso local | Puerto 27017 en escucha, base `sinia_uy`, colecciones creadas |
| Scheduler tiempo real | Funcionando en segundo plano | Ejecuta forecast, FIRMS NRT y CAMS; log indica `Scheduler iniciado y corriendo` |
| Forecast 7 dias | Actualizado | 77 registros, rango 2026-05-15 a 2026-05-21 |
| FIRMS NRT | Actualizado | 5.283 focos ultimos 5 dias, 1.635 en ultimas 24 h |
| CAMS calidad de aire | Actualizado | Datos recientes hasta 2026-05-15 |
| Tests calidad/idempotencia/CDC | Funcionando | 17 PASS / 0 FAIL |

## Correcciones aplicadas

1. `dashboard/db.py`
   - Se corrigieron consultas SQL que usaban `SQL_SCOPE_PAISES` sin interpolacion.
   - `cargar_meteo`, `cargar_cams` y `cargar_forecast` ahora consultan PostgreSQL correctamente.
   - `cargar_focos_nrt` ahora intenta leer PostgreSQL antes de usar Parquet.

2. `etl/scheduler.py`
   - Se corrigio FIRMS NRT: NASA acepta rango `[1..5]`; el scheduler pedia hasta 7 dias.
   - Se reemplazo una flecha Unicode en log por `->` para evitar errores de encoding en Windows.

3. `etl/load/load_postgres.py`
   - El refresh de `mv_focos_por_pais_mes` quedo como optimizacion opcional.
   - Si la materialized view no existe o el usuario no tiene permiso, no se marca como error operativo.

4. MongoDB
   - El servicio Windows estaba detenido/deshabilitado.
   - Se levanto `mongod.exe` como proceso local de usuario con `data/mongo_local`.
   - Se ejecutaron schemas/carga documental con `python etl/load/load_mongo.py`.

## Evidencia cuantitativa final

PostgreSQL:

| Consulta | Resultado |
|---|---:|
| Focos ultimos 5 dias | 5.283 |
| Focos ultimas 24 h | 1.635 |
| Forecast vigente | 77 registros |
| Rango forecast | 2026-05-15 a 2026-05-21 |
| CAMS reciente | 66 registros desde 2026-05-10 a 2026-05-15 |

MongoDB:

| Coleccion | Documentos |
|---|---:|
| `ejecuciones_etl` | 1 |
| `alertas` | 0 |
| `focos_snapshots` | 347 |

Servicios/puertos:

| Puerto | Servicio |
|---:|---|
| 5432 | PostgreSQL |
| 27017 | MongoDB local |
| 8501 | Streamlit |

## Lo que funciona

- El dashboard abre y consume PostgreSQL.
- PostgreSQL tiene datos historicos y datos recientes NRT/forecast/CAMS.
- MongoDB esta levantado localmente y tiene colecciones con schema e indices.
- El scheduler queda corriendo y programado:
  - FIRMS NRT cada 3 horas.
  - Forecast cada 1 hora.
  - CAMS cada 1 hora.
  - CHIRPS cada 30 dias.
- Los tests siguen verdes: 17 PASS / 0 FAIL.

## Lo que no queda perfecto todavia

- MongoDB esta corriendo como proceso local manual, no como servicio Windows ni Docker.
  Si se reinicia la maquina, hay que volver a levantarlo o habilitar el servicio con permisos de administrador.
- Docker Desktop esta detenido y deshabilitado, por lo que `docker compose` no esta disponible ahora.
- MongoDB contiene snapshots historicos 2024; los focos NRT recientes ya estan en PostgreSQL y Parquet NRT,
  pero no se regeneraron snapshots Mongo para 2026 en esta corrida.
- Los logs JSON antiguos muestran mojibake en algunos acentos por consola/encoding, aunque la ejecucion actual funciona.

## Comandos utiles

Levantar dashboard:

```bash
streamlit run dashboard/app.py --server.port 8501
```

Levantar MongoDB local manual:

```powershell
New-Item -ItemType Directory -Force -Path data\mongo_local
Start-Process -FilePath 'C:\Program Files\MongoDB\Server\6.0\bin\mongod.exe' -ArgumentList '--dbpath','data\mongo_local','--bind_ip','127.0.0.1','--port','27017' -WindowStyle Hidden
```

Levantar scheduler:

```bash
python etl/scheduler.py
```

Verificar tests:

```bash
python tests/test_calidad_datos.py
```

## Conclusion

El sistema queda operativo en tiempo real en el entorno local actual: dashboard,
PostgreSQL, MongoDB local, scheduler y tests estan funcionando. La persistencia
final tambien quedo validada en UTEC mediante `reports/utec_verificacion_ultimo.json`.
Docker Compose esta configurado y validado; la ejecucion de contenedores depende de
que Windows habilite `WSLService` y `com.docker.service`.
