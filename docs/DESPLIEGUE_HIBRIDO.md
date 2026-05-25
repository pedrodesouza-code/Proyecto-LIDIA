# Despliegue hibrido

Revision actualizada: **2026-05-22**.

La consigna pide integrar componentes en infraestructura institucional/in situ y componentes ejecutables localmente o en entorno cloud. El proyecto cubre esa arquitectura con PostgreSQL, MongoDB, Streamlit, Docker y configuracion externa.

## Distribucion propuesta

| Componente | Ubicacion | Justificacion |
|---|---|---|
| PostgreSQL / Data Warehouse | Servidor institucional UTEC o contenedor Docker | Persistencia analitica, integridad y consultas SQL |
| MongoDB operacional | Servidor institucional UTEC o contenedor Docker | Snapshots, trazabilidad ETL y alertas |
| Dashboard Streamlit | Local, cloud o contenedor | Capa visual de analitica |
| Repositorio Git | GitHub | Versionado y evidencia |
| ETL Python | Local/UTEC segun etapa | Ejecuta extraccion, transformacion y carga |

## Estado actual del repositorio

| Control | Estado |
|---|---|
| Alcance funcional | `ARG`, `BRA`, `CHL`, `URY` |
| Puntos | `36` |
| Tests | `20 PASS / 0 FAIL` |
| Docker Compose | Configuracion valida |
| Dashboard | Ejecutable localmente con fallback a Parquet |
| Evidencia UTEC | Historica al `2026-05-15` |

## Evidencia actual

- `docs/ESTADO_ACTUAL_PROYECTO_2026-05-22.md`
- `reports/carga_completa_ultimo.json`
- `reports/sql_vs_nosql_real_ultimo.json`
- `tests/resultados_tests.json`
- `docker/docker-compose.yml`
- `config/utec.env.example`
- `scripts/deploy.sh`

## Evidencia UTEC historica

El archivo `reports/utec_verificacion_ultimo.json` corresponde a una verificacion del `2026-05-15` con alcance anterior `ARG/BRA/URY`.

Esa evidencia demuestra:

- conectividad institucional;
- PostgreSQL remoto disponible;
- MongoDB remoto disponible;
- carga real en servidor UTEC;
- materializadas y snapshots generados.

No debe usarse para afirmar que Chile ya esta sincronizado en UTEC. Para eso hay que regenerar el reporte remoto.

## Comandos reproducibles

Validar Docker Compose:

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env.example config --quiet
```

Ejecutar tests:

```bash
pytest tests -q
```

Levantar dashboard:

```bash
streamlit run dashboard/app.py
```

Verificacion UTEC, si el entorno y credenciales estan disponibles:

```bash
python scripts/verificar_utec.py
```

## Estado de defensa

El despliegue hibrido queda defendible asi:

> El proyecto tiene infraestructura definida y validada por Docker Compose, evidencia historica de integracion con UTEC y dashboard ejecutable local/cloud. El estado funcional actual del repositorio es de cuatro paises y treinta y seis puntos; la evidencia UTEC versionada es una foto anterior que puede regenerarse si se requiere sincronizacion remota completa.
