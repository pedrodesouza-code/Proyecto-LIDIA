# D8 Entorno Local Docker

Este entorno Docker prepara una versión local reproducible del Proyecto LIDIA EC3. No usa credenciales reales de UTEC y no se conecta a PostgreSQL ni MongoDB institucionales.

## Qué Corre En Docker Local

- `postgres`: Data Warehouse PostgreSQL local con base `proyecto_lidia`.
- `mongo`: MongoDB local como capa documental complementaria para metadata, logs, rechazos, snapshots y raw payloads controlados.
- `etl`: servicio Python para ejecutar validaciones y ETL smoke.
- `streamlit`: dashboard conectado al PostgreSQL local mediante vistas `dw`.

PostgreSQL sigue siendo el Data Warehouse principal. MongoDB no reemplaza el modelo relacional.

## Qué Corre En UTEC/Jupyter

En UTEC/Jupyter se ejecutan las cargas reales, validaciones y evidencias contra el entorno institucional autorizado. Docker local es solo una prueba reproducible de despliegue y configuración, no una sustitución del entorno UTEC.

## Por Qué Docker No Se Ejecuta En UTEC

El entorno Jupyter/UTEC puede no permitir Docker, exponer puertos o administrar volúmenes persistentes. Por eso Docker queda documentado como entorno local reproducible, mientras que las cargas reales y evidencias de datos productivos se ejecutan en Jupyter/UTEC.

## Configuración

Copiar el ejemplo local si se quiere modificar puertos o credenciales ficticias:

```bash
cp .env.docker.example .env.docker
```

No usar credenciales reales. El archivo `.env.docker` está excluido de Git.

## Levantar El Entorno

```bash
docker compose --env-file .env.docker.example up -d postgres mongo
docker compose --env-file .env.docker.example up --build etl
docker compose --env-file .env.docker.example up --build streamlit
```

Streamlit queda disponible en:

```text
http://localhost:8501
```

## Ejecutar ETL Smoke Local

La corrida smoke usa datos reales si están configurados localmente, acota el volumen y no ejecuta la carga histórica completa.

```bash
docker compose --env-file .env.docker.example run --rm etl \
  python etl/main.py --smoke --start-date 2025-01-01 --end-date 2025-01-07 \
  --countries URY --max-records-per-source 1000 --skip-mongo
```

## Generar Evidencia D8

```bash
bash scripts/d8_generar_evidencia_docker.sh
```

La evidencia se guarda en:

- `evidencia/logs/d8_docker_compose_config.log`
- `evidencia/logs/d8_docker_compose_ps.log`
- `evidencia/logs/d8_docker_postgres_check.log`
- `evidencia/logs/d8_docker_mongo_check.log`
- `evidencia/logs/d8_resumen_despliegue.md`

## Limitaciones

- El entorno local puede iniciar sin datos reales cargados si no se montan archivos fuente.
- No se deben ejecutar cargas históricas completas desde Docker sin planificar tiempos, memoria y almacenamiento.
- CAMS/Open-Meteo Air Quality, Open-Meteo histórico y otras APIs pueden depender de red, cupos y tiempos de respuesta.
- Docker local demuestra reproducibilidad técnica; la evidencia de carga real integrada corresponde al entorno Jupyter/UTEC.

## Fuentes Del Proyecto

Las fuentes válidas son NASA FIRMS, METEO/Open-Meteo histórico, CAMS/Open-Meteo Air Quality, CHIRPS, MODIS e INUMET. No se incluye ningún servicio de pronóstico como fuente del proyecto.
