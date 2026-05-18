#!/bin/sh
set -eu

# Assign application passwords from Docker environment variables.
# The SQL DDL creates roles/users without storing secrets in the repository.

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  -v etl_password="$PG_PASSWORD" \
  -v dash_password="$PG_DASH_PASSWORD" <<'EOSQL'
ALTER USER sinia_etl_user WITH PASSWORD :'etl_password';
ALTER USER sinia_dash_user WITH PASSWORD :'dash_password';
EOSQL
