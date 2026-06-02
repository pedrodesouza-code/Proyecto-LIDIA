# D8 Docker/despliegue - Resumen

Generado con: `.env.docker.example`.

## Servicios esperados

- postgres: presente
- mongo: presente
- etl: presente
- streamlit: presente

## Evidencias

- `evidencia/logs/d8_docker_compose_config.log`: configuración Docker Compose con credenciales ocultas.
- `evidencia/logs/d8_docker_compose_up.log`: arranque local de PostgreSQL y MongoDB.
- `evidencia/logs/d8_docker_build.log`: construcción de imagen Python para ETL/Streamlit.
- `evidencia/logs/d8_docker_compose_ps.log`: estado de servicios.
- `evidencia/logs/d8_docker_ddl_check.log`: ejecución de DDL base en PostgreSQL local.
- `evidencia/logs/d8_docker_postgres_check.log`: conexión PostgreSQL desde contenedor ETL.
- `evidencia/logs/d8_docker_mongo_check.log`: conexión MongoDB desde contenedor ETL.

## Alcance

Entorno local reproducible. No usa credenciales reales de UTEC ni se conecta a bases institucionales.
No ejecuta carga histórica completa.

Estado build ETL/Streamlit: PARCIAL por problema de DNS/red de Docker hacia PyPI. PostgreSQL y MongoDB locales fueron validados con contenedores base.
