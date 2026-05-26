#!/bin/sh
set -eu

psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=etl_password="${POSTGRES_ETL_PASSWORD:-CAMBIAR}" \
  --set=dashboard_password="${POSTGRES_DASHBOARD_PASSWORD:-CAMBIAR}" <<'SQL'
DO $block$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lidia_etl') THEN
        CREATE ROLE lidia_etl NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lidia_dashboard') THEN
        CREATE ROLE lidia_dashboard NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lidia_etl_user') THEN
        CREATE USER lidia_etl_user;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lidia_dashboard_user') THEN
        CREATE USER lidia_dashboard_user;
    END IF;
END
$block$;
ALTER USER lidia_etl_user PASSWORD :'etl_password';
ALTER USER lidia_dashboard_user PASSWORD :'dashboard_password';
GRANT lidia_etl TO lidia_etl_user;
GRANT lidia_dashboard TO lidia_dashboard_user;
SQL
