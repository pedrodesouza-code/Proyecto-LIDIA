# Docker Local

Este `compose` levanta PostgreSQL, MongoDB y Streamlit para validacion local.
Copiar `.env.example` a `.env` local y cambiar passwords antes de iniciarlo.

```bash
cd implementation/docker
docker compose up -d postgres mongo
docker compose up -d streamlit
```

En un servidor institucional se deben usar los servicios PostgreSQL y MongoDB
autorizados por UTEC; no se asume disponibilidad de Docker ni de sharding.

## Backup y recuperacion

```bash
docker compose exec postgres pg_dump -U postgres -d lidia_ec3 -Fc > lidia_ec3.dump
docker compose exec -T postgres pg_restore -U postgres -d lidia_ec3 --clean < lidia_ec3.dump
docker compose exec mongo mongodump --db lidia_ec3 --archive=/tmp/lidia.archive
```

Los respaldos contienen datos y no deben versionarse en GitHub.
