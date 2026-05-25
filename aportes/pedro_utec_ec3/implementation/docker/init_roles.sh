#!/usr/bin/env sh
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sinia_readonly') THEN
        CREATE ROLE sinia_readonly NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sinia_etl') THEN
        CREATE ROLE sinia_etl NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sinia_admin') THEN
        CREATE ROLE sinia_admin NOLOGIN;
    END IF;
END
\$\$;

DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sinia_dash_user') THEN
        CREATE USER sinia_dash_user WITH PASSWORD '${PG_DASH_PASSWORD:-CAMBIAR}';
    END IF;
    GRANT sinia_readonly TO sinia_dash_user;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${PG_USER:-sinia_etl_user}') THEN
        CREATE USER ${PG_USER:-sinia_etl_user} WITH PASSWORD '${PG_PASSWORD:-CAMBIAR}';
    END IF;
    GRANT sinia_etl TO ${PG_USER:-sinia_etl_user};
END
\$\$;
SQL
