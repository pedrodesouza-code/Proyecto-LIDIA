\pset pager off
\pset null '[NULL]'
\echo 'D3 - Validacion ETL Python Proyecto LIDIA EC3'
\echo 'Fecha de ejecucion'
SELECT now() AS ejecutado_en;

CREATE TEMP TABLE d3_evidencia (
    seccion TEXT,
    item TEXT,
    valor TEXT
) ON COMMIT DROP;

DO $$
DECLARE
    rec RECORD;
    query TEXT;
BEGIN
    INSERT INTO d3_evidencia VALUES
        ('catalogo', 'audit.etl_runs existe', (to_regclass('audit.etl_runs') IS NOT NULL)::TEXT),
        ('catalogo', 'staging.ingesta_metadata existe', (to_regclass('staging.ingesta_metadata') IS NOT NULL)::TEXT),
        ('catalogo', 'staging.rechazos_etl existe', (to_regclass('staging.rechazos_etl') IS NOT NULL)::TEXT),
        ('catalogo', 'dw.fact_incendio existe', (to_regclass('dw.fact_incendio') IS NOT NULL)::TEXT);

    IF to_regclass('audit.etl_runs') IS NOT NULL THEN
        INSERT INTO d3_evidencia
        SELECT 'audit.etl_runs ultimas corridas',
               COALESCE(fuente, '[sin_fuente]') || ' | ' || COALESCE(etapa, '[sin_etapa]') || ' | ' || COALESCE(estado, '[sin_estado]'),
               jsonb_build_object(
                   'run_id', run_id,
                   'iniciado_en', iniciado_en,
                   'finalizado_en', finalizado_en,
                   'filas_leidas', filas_leidas,
                   'filas_insertadas', filas_insertadas,
                   'filas_actualizadas', filas_actualizadas,
                   'filas_rechazadas', filas_rechazadas,
                   'duracion_segundos', duracion_segundos
               )::TEXT
        FROM audit.etl_runs
        ORDER BY iniciado_en DESC NULLS LAST
        LIMIT 20;

        INSERT INTO d3_evidencia
        SELECT 'audit.etl_runs resumen por fuente',
               COALESCE(fuente, '[sin_fuente]') || ' | ' || COALESCE(estado, '[sin_estado]'),
               jsonb_build_object(
                   'corridas', COUNT(*),
                   'filas_leidas', COALESCE(SUM(filas_leidas), 0),
                   'filas_insertadas', COALESCE(SUM(filas_insertadas), 0),
                   'filas_actualizadas', COALESCE(SUM(filas_actualizadas), 0),
                   'filas_rechazadas', COALESCE(SUM(filas_rechazadas), 0),
                   'ultima_corrida', MAX(iniciado_en)
               )::TEXT
        FROM audit.etl_runs
        GROUP BY fuente, estado
        ORDER BY fuente, estado;
    ELSE
        INSERT INTO d3_evidencia VALUES ('limitacion', 'audit.etl_runs', 'No existe; no se puede validar corridas ETL.');
    END IF;

    IF to_regclass('staging.ingesta_metadata') IS NOT NULL THEN
        INSERT INTO d3_evidencia
        SELECT 'staging.ingesta_metadata resumen',
               COALESCE(fuente, '[sin_fuente]') || ' | ' || COALESCE(estado, '[sin_estado]'),
               jsonb_build_object(
                   'corridas', COUNT(*),
                   'filas_leidas', COALESCE(SUM(filas_leidas), 0),
                   'filas_insertadas', COALESCE(SUM(filas_insertadas), 0),
                   'filas_actualizadas', COALESCE(SUM(filas_actualizadas), 0),
                   'filas_rechazadas', COALESCE(SUM(filas_rechazadas), 0),
                   'ultima_fecha_procesada', MAX(ultima_fecha_procesada)
               )::TEXT
        FROM staging.ingesta_metadata
        GROUP BY fuente, estado
        ORDER BY fuente, estado;
    ELSE
        INSERT INTO d3_evidencia VALUES ('limitacion', 'staging.ingesta_metadata', 'No existe; no se puede validar metadata de ingesta.');
    END IF;

    IF to_regclass('staging.rechazos_etl') IS NOT NULL THEN
        INSERT INTO d3_evidencia
        SELECT 'staging.rechazos_etl por fuente y motivo',
               COALESCE(fuente, '[sin_fuente]') || ' | ' || COALESCE(motivo, '[sin_motivo]'),
               COUNT(*)::TEXT
        FROM staging.rechazos_etl
        GROUP BY fuente, motivo
        ORDER BY fuente, COUNT(*) DESC, motivo;

        INSERT INTO d3_evidencia
        SELECT 'staging.rechazos_etl valores invalidos aislados',
               COALESCE(fuente, '[sin_fuente]'),
               jsonb_build_object(
                   'rechazos', COUNT(*),
                   'motivos_distintos', COUNT(DISTINCT motivo),
                   'primer_rechazo', MIN(rechazado_en),
                   'ultimo_rechazo', MAX(rechazado_en)
               )::TEXT
        FROM staging.rechazos_etl
        GROUP BY fuente
        ORDER BY fuente;
    ELSE
        INSERT INTO d3_evidencia VALUES ('limitacion', 'staging.rechazos_etl', 'No existe; no se puede validar manejo de errores/rechazos.');
    END IF;

    FOR rec IN
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema IN ('staging','dw')
          AND table_name IN (
              'stg_firms','stg_meteo','stg_chirps','stg_modis','stg_calidad_aire',
              'fact_incendio'
          )
        ORDER BY table_schema, table_name
    LOOP
        EXECUTE format('INSERT INTO d3_evidencia SELECT %L, %L, COUNT(*)::TEXT FROM %I.%I',
                       'conteos por tabla ETL/DW', rec.table_schema || '.' || rec.table_name,
                       rec.table_schema, rec.table_name);

        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema=rec.table_schema AND table_name=rec.table_name AND column_name='natural_key'
        ) THEN
            EXECUTE format('INSERT INTO d3_evidencia SELECT %L, %L, COUNT(*)::TEXT FROM %I.%I WHERE natural_key IS NULL',
                           'presencia natural_key nulos', rec.table_schema || '.' || rec.table_name,
                           rec.table_schema, rec.table_name);
            EXECUTE format('INSERT INTO d3_evidencia SELECT %L, %L, COUNT(*)::TEXT FROM (SELECT natural_key FROM %I.%I GROUP BY natural_key HAVING COUNT(*) > 1) d',
                           'duplicados por natural_key', rec.table_schema || '.' || rec.table_name,
                           rec.table_schema, rec.table_name);
        ELSE
            INSERT INTO d3_evidencia VALUES ('limitacion natural_key', rec.table_schema || '.' || rec.table_name, 'La tabla no tiene columna natural_key.');
        END IF;

        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema=rec.table_schema AND table_name=rec.table_name AND column_name='record_hash'
        ) THEN
            EXECUTE format('INSERT INTO d3_evidencia SELECT %L, %L, COUNT(*)::TEXT FROM %I.%I WHERE record_hash IS NULL',
                           'presencia record_hash nulos', rec.table_schema || '.' || rec.table_name,
                           rec.table_schema, rec.table_name);
        ELSE
            INSERT INTO d3_evidencia VALUES ('limitacion record_hash', rec.table_schema || '.' || rec.table_name, 'La tabla no tiene columna record_hash.');
        END IF;

        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema=rec.table_schema AND table_name=rec.table_name AND column_name='fuente'
        ) THEN
            EXECUTE format('INSERT INTO d3_evidencia SELECT %L, COALESCE(fuente, %L), COUNT(*)::TEXT FROM %I.%I GROUP BY fuente ORDER BY fuente',
                           'trazabilidad de fuente', '[sin_fuente]',
                           rec.table_schema, rec.table_name);
        ELSIF rec.table_schema='dw' AND rec.table_name='fact_incendio' THEN
            INSERT INTO d3_evidencia VALUES ('trazabilidad de fuente', 'dw.fact_incendio', 'Hechos FIRMS; la fuente queda trazada por staging.stg_firms y metadata ETL.');
        ELSE
            INSERT INTO d3_evidencia VALUES ('limitacion fuente', rec.table_schema || '.' || rec.table_name, 'La tabla no tiene columna fuente.');
        END IF;
    END LOOP;

    IF to_regclass('dw.fact_incendio') IS NOT NULL THEN
        INSERT INTO d3_evidencia
        SELECT 'dw.fact_incendio conteos',
               'resumen hechos',
               jsonb_build_object(
                   'total', COUNT(*),
                   'natural_keys_distintas', COUNT(DISTINCT natural_key),
                   'record_hash_nulos', COUNT(*) FILTER (WHERE record_hash IS NULL),
                   'brillo_termico_no_nulo', COUNT(brillo_termico),
                   'frp_invalidos', COUNT(*) FILTER (WHERE frp_mw < 0)
               )::TEXT
        FROM dw.fact_incendio;
    END IF;
END $$;

\echo '1. Evidencia D3 consolidada'
SELECT seccion, item, valor
FROM d3_evidencia
ORDER BY seccion, item, valor;

\echo '2. Columnas natural_key y record_hash por tabla'
SELECT table_schema AS esquema, table_name AS tabla,
       BOOL_OR(column_name='natural_key') AS tiene_natural_key,
       BOOL_OR(column_name='record_hash') AS tiene_record_hash
FROM information_schema.columns
WHERE table_schema IN ('staging','dw')
GROUP BY table_schema, table_name
HAVING table_name IN ('stg_firms','stg_meteo','stg_chirps','stg_modis','stg_calidad_aire','fact_incendio')
ORDER BY table_schema, table_name;

\echo '3. Trazabilidad fuente en tablas con columna fuente'
SELECT table_schema AS esquema, table_name AS tabla, column_name AS columna
FROM information_schema.columns
WHERE table_schema IN ('staging','dw','audit')
  AND column_name='fuente'
ORDER BY table_schema, table_name;

\echo 'D3 - Fin validacion ETL'
