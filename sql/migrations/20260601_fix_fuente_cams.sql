-- Proyecto LIDIA EC3
-- Migracion incremental: habilita CAMS/Open-Meteo Air Quality como fuente valida.
-- No elimina restricciones de dominio; las reemplaza por CHECK coherentes con EC1/EC2.

DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    IF to_regclass('staging.ingesta_metadata') IS NOT NULL THEN
        FOR constraint_name IN
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class cls ON cls.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace
            WHERE nsp.nspname = 'staging'
              AND cls.relname = 'ingesta_metadata'
              AND con.contype = 'c'
              AND pg_get_constraintdef(con.oid) ILIKE '%fuente%'
        LOOP
            EXECUTE format('ALTER TABLE staging.ingesta_metadata DROP CONSTRAINT IF EXISTS %I', constraint_name);
        END LOOP;
        ALTER TABLE staging.ingesta_metadata
            ADD CONSTRAINT ingesta_metadata_fuente_check
            CHECK (fuente IN ('INUMET','FIRMS','CHIRPS','METEO','MODIS','CAMS')) NOT VALID;
    END IF;

    IF to_regclass('staging.rechazos_etl') IS NOT NULL
       AND EXISTS (
           SELECT 1
           FROM information_schema.columns
           WHERE table_schema='staging' AND table_name='rechazos_etl' AND column_name='fuente'
       )
    THEN
        FOR constraint_name IN
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class cls ON cls.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace
            WHERE nsp.nspname = 'staging'
              AND cls.relname = 'rechazos_etl'
              AND con.contype = 'c'
              AND pg_get_constraintdef(con.oid) ILIKE '%fuente%'
        LOOP
            EXECUTE format('ALTER TABLE staging.rechazos_etl DROP CONSTRAINT IF EXISTS %I', constraint_name);
        END LOOP;
        ALTER TABLE staging.rechazos_etl
            ADD CONSTRAINT rechazos_etl_fuente_check
            CHECK (fuente IN ('INUMET','FIRMS','CHIRPS','METEO','MODIS','CAMS')) NOT VALID;
    END IF;

    IF to_regclass('staging.stg_meteo') IS NOT NULL THEN
        FOR constraint_name IN
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class cls ON cls.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace
            WHERE nsp.nspname = 'staging'
              AND cls.relname = 'stg_meteo'
              AND con.contype = 'c'
              AND pg_get_constraintdef(con.oid) ILIKE '%fuente%'
        LOOP
            EXECUTE format('ALTER TABLE staging.stg_meteo DROP CONSTRAINT IF EXISTS %I', constraint_name);
        END LOOP;
        ALTER TABLE staging.stg_meteo
            ADD CONSTRAINT stg_meteo_fuente_check
            CHECK (fuente IN ('METEO','INUMET')) NOT VALID;
    END IF;

    IF to_regclass('audit.etl_runs') IS NOT NULL THEN
        FOR constraint_name IN
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class cls ON cls.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace
            WHERE nsp.nspname = 'audit'
              AND cls.relname = 'etl_runs'
              AND con.contype = 'c'
              AND pg_get_constraintdef(con.oid) ILIKE '%fuente%'
        LOOP
            EXECUTE format('ALTER TABLE audit.etl_runs DROP CONSTRAINT IF EXISTS %I', constraint_name);
        END LOOP;
        ALTER TABLE audit.etl_runs
            ADD CONSTRAINT etl_runs_fuente_check
            CHECK (fuente IN ('INUMET','FIRMS','CHIRPS','METEO','MODIS','CAMS')) NOT VALID;
    END IF;

    IF to_regclass('audit.cdc_eventos') IS NOT NULL
       AND EXISTS (
           SELECT 1
           FROM information_schema.columns
           WHERE table_schema='audit' AND table_name='cdc_eventos' AND column_name='fuente'
       )
    THEN
        FOR constraint_name IN
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class cls ON cls.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace
            WHERE nsp.nspname = 'audit'
              AND cls.relname = 'cdc_eventos'
              AND con.contype = 'c'
              AND pg_get_constraintdef(con.oid) ILIKE '%fuente%'
        LOOP
            EXECUTE format('ALTER TABLE audit.cdc_eventos DROP CONSTRAINT IF EXISTS %I', constraint_name);
        END LOOP;
        ALTER TABLE audit.cdc_eventos
            ADD CONSTRAINT cdc_eventos_fuente_check
            CHECK (fuente IN ('INUMET','FIRMS','CHIRPS','METEO','MODIS','CAMS')) NOT VALID;
    END IF;

    IF to_regclass('dw.dim_clima') IS NOT NULL THEN
        FOR constraint_name IN
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class cls ON cls.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace
            WHERE nsp.nspname = 'dw'
              AND cls.relname = 'dim_clima'
              AND con.contype = 'c'
              AND pg_get_constraintdef(con.oid) ILIKE '%fuente%'
        LOOP
            EXECUTE format('ALTER TABLE dw.dim_clima DROP CONSTRAINT IF EXISTS %I', constraint_name);
        END LOOP;
        ALTER TABLE dw.dim_clima
            ADD CONSTRAINT dim_clima_fuente_check
            CHECK (fuente IN ('METEO','INUMET')) NOT VALID;
    END IF;
END
$$;

-- Evidencia de constraints fuente luego de la migracion.
SELECT nsp.nspname AS esquema,
       cls.relname AS tabla,
       con.conname AS constraint_name,
       pg_get_constraintdef(con.oid) AS definicion
FROM pg_constraint con
JOIN pg_class cls ON cls.oid = con.conrelid
JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace
WHERE nsp.nspname IN ('staging','audit','dw')
  AND con.contype = 'c'
  AND pg_get_constraintdef(con.oid) ILIKE '%fuente%'
ORDER BY nsp.nspname, cls.relname, con.conname;
