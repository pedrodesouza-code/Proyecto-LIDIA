-- =============================================================================
-- SINIA-UY — Roles y Seguridad PostgreSQL
-- =============================================================================
-- Principio: privilegio mínimo. Cada rol solo tiene lo que necesita.
--
-- Roles:
--   sinia_readonly  → dashboard y consultas analíticas (solo lectura)
--   sinia_etl       → proceso de carga ETL (lectura + escritura en tablas de datos)
--   sinia_admin     → administración total (solo para mantenimiento)
--
-- Ejecutar como superusuario de PostgreSQL.
-- =============================================================================

-- Evitar errores si ya existen
DO $$
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
$$;

-- Los usuarios LOGIN se crean desde docker/init_roles.sh usando variables de
-- entorno. Este SQL solo define roles lógicos y permisos mínimos.

-- =============================================================================
-- Permisos sobre el schema public
-- =============================================================================

-- sinia_readonly: puede consultar todas las tablas y vistas
GRANT USAGE ON SCHEMA public TO sinia_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sinia_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO sinia_readonly;

-- sinia_etl: puede insertar, actualizar y consultar (no borrar datos, no DDL)
GRANT USAGE ON SCHEMA public TO sinia_etl;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO sinia_etl;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sinia_etl;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE ON TABLES TO sinia_etl;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO sinia_etl;

-- sinia_admin: acceso completo
GRANT ALL PRIVILEGES ON SCHEMA public TO sinia_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sinia_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sinia_admin;
