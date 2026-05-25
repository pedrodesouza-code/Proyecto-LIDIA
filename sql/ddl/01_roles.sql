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

-- Usuarios de aplicacion.
-- Las contrasenas reales NO se versionan en este archivo.
-- Despues de crear los usuarios, asignar passwords desde un entorno seguro:
--
--   ALTER USER sinia_dash_user WITH PASSWORD '<valor_seguro_del_env>';
--   ALTER USER sinia_etl_user  WITH PASSWORD '<valor_seguro_del_env>';
--
-- En Docker o despliegue, esos valores deben venir de docker/.env, config/.env
-- o del gestor de secretos del ambiente.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sinia_dash_user') THEN
        CREATE USER sinia_dash_user IN ROLE sinia_readonly;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sinia_etl_user') THEN
        CREATE USER sinia_etl_user IN ROLE sinia_etl;
    END IF;
END
$$;

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
