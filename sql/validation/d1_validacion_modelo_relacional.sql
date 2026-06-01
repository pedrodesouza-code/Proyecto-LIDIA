\pset pager off
\pset null '[NULL]'
\echo 'D1 - Validacion del modelo relacional Proyecto LIDIA EC3'
\echo 'Fecha de ejecucion'
SELECT now() AS ejecutado_en;

\echo '1. Existencia de esquemas requeridos'
SELECT schema_name,
       CASE WHEN schema_name IS NOT NULL THEN 'OK' ELSE 'FALTA' END AS estado
FROM (VALUES ('staging'), ('dw'), ('audit')) AS esperado(schema_name)
LEFT JOIN information_schema.schemata s USING (schema_name)
ORDER BY esperado.schema_name;

\echo '2. Existencia de tablas principales'
WITH esperadas(schema_name, table_name) AS (
    VALUES
    ('staging','ingesta_metadata'),
    ('staging','rechazos_etl'),
    ('staging','stg_firms'),
    ('staging','stg_meteo'),
    ('staging','stg_chirps'),
    ('staging','stg_modis'),
    ('staging','stg_calidad_aire'),
    ('dw','dim_fecha'),
    ('dw','dim_ubicacion'),
    ('dw','dim_estacion_meteorologica'),
    ('dw','dim_clima'),
    ('dw','dim_precipitacion'),
    ('dw','dim_cobertura_vegetal'),
    ('dw','dim_calidad_aire'),
    ('dw','fact_incendio'),
    ('audit','etl_runs'),
    ('audit','cdc_eventos'),
    ('audit','asociacion_espacial_runs')
)
SELECT e.schema_name, e.table_name,
       CASE WHEN t.table_name IS NULL THEN 'FALTA' ELSE 'OK' END AS estado
FROM esperadas e
LEFT JOIN information_schema.tables t
       ON t.table_schema=e.schema_name AND t.table_name=e.table_name
ORDER BY e.schema_name, e.table_name;

\echo '3. Claves primarias'
SELECT n.nspname AS esquema, c.relname AS tabla, con.conname AS constraint_name,
       pg_get_constraintdef(con.oid) AS definicion
FROM pg_constraint con
JOIN pg_class c ON c.oid=con.conrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname IN ('staging','dw','audit') AND con.contype='p'
ORDER BY n.nspname, c.relname, con.conname;

\echo '4. Claves foraneas'
SELECT n.nspname AS esquema, c.relname AS tabla, con.conname AS constraint_name,
       pg_get_constraintdef(con.oid) AS definicion
FROM pg_constraint con
JOIN pg_class c ON c.oid=con.conrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname IN ('staging','dw','audit') AND con.contype='f'
ORDER BY n.nspname, c.relname, con.conname;

\echo '5. Restricciones CHECK'
SELECT n.nspname AS esquema, c.relname AS tabla, con.conname AS constraint_name,
       pg_get_constraintdef(con.oid) AS definicion
FROM pg_constraint con
JOIN pg_class c ON c.oid=con.conrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname IN ('staging','dw','audit') AND con.contype='c'
ORDER BY n.nspname, c.relname, con.conname;

\echo '6. Restricciones UNIQUE'
SELECT n.nspname AS esquema, c.relname AS tabla, con.conname AS constraint_name,
       pg_get_constraintdef(con.oid) AS definicion
FROM pg_constraint con
JOIN pg_class c ON c.oid=con.conrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname IN ('staging','dw','audit') AND con.contype='u'
ORDER BY n.nspname, c.relname, con.conname;

\echo '7. Columnas NOT NULL'
SELECT table_schema AS esquema, table_name AS tabla, column_name AS columna, data_type
FROM information_schema.columns
WHERE table_schema IN ('staging','dw','audit') AND is_nullable='NO'
ORDER BY table_schema, table_name, ordinal_position;

\echo '8. Indices existentes'
SELECT schemaname AS esquema, tablename AS tabla, indexname AS indice, indexdef
FROM pg_indexes
WHERE schemaname IN ('staging','dw','audit')
ORDER BY schemaname, tablename, indexname;

\echo '9. Vistas analiticas del esquema dw'
SELECT table_schema AS esquema, table_name AS vista
FROM information_schema.views
WHERE table_schema='dw'
ORDER BY table_name;

\echo '10. Conteos por tabla principal'
SELECT 'staging.ingesta_metadata' AS tabla, COUNT(*)::bigint AS filas FROM staging.ingesta_metadata
UNION ALL SELECT 'staging.rechazos_etl', COUNT(*)::bigint FROM staging.rechazos_etl
UNION ALL SELECT 'staging.stg_firms', COUNT(*)::bigint FROM staging.stg_firms
UNION ALL SELECT 'staging.stg_meteo', COUNT(*)::bigint FROM staging.stg_meteo
UNION ALL SELECT 'staging.stg_chirps', COUNT(*)::bigint FROM staging.stg_chirps
UNION ALL SELECT 'staging.stg_modis', COUNT(*)::bigint FROM staging.stg_modis
UNION ALL SELECT 'staging.stg_calidad_aire', COUNT(*)::bigint FROM staging.stg_calidad_aire
UNION ALL SELECT 'dw.dim_fecha', COUNT(*)::bigint FROM dw.dim_fecha
UNION ALL SELECT 'dw.dim_ubicacion', COUNT(*)::bigint FROM dw.dim_ubicacion
UNION ALL SELECT 'dw.dim_estacion_meteorologica', COUNT(*)::bigint FROM dw.dim_estacion_meteorologica
UNION ALL SELECT 'dw.dim_clima', COUNT(*)::bigint FROM dw.dim_clima
UNION ALL SELECT 'dw.dim_precipitacion', COUNT(*)::bigint FROM dw.dim_precipitacion
UNION ALL SELECT 'dw.dim_cobertura_vegetal', COUNT(*)::bigint FROM dw.dim_cobertura_vegetal
UNION ALL SELECT 'dw.dim_calidad_aire', COUNT(*)::bigint FROM dw.dim_calidad_aire
UNION ALL SELECT 'dw.fact_incendio', COUNT(*)::bigint FROM dw.fact_incendio
UNION ALL SELECT 'audit.etl_runs', COUNT(*)::bigint FROM audit.etl_runs
UNION ALL SELECT 'audit.cdc_eventos', COUNT(*)::bigint FROM audit.cdc_eventos
UNION ALL SELECT 'audit.asociacion_espacial_runs', COUNT(*)::bigint FROM audit.asociacion_espacial_runs
ORDER BY tabla;

\echo '11. Conteos especificos en dw.fact_incendio'
SELECT COUNT(*)::bigint AS total_incendios,
       COUNT(clima_id)::bigint AS con_clima,
       COUNT(precipitacion_id)::bigint AS con_precipitacion,
       COUNT(cobertura_id)::bigint AS con_cobertura,
       COUNT(calidad_aire_id)::bigint AS con_calidad_aire,
       COUNT(DISTINCT natural_key)::bigint AS natural_keys_distintas
FROM dw.fact_incendio;

\echo '12. Conteos en staging.rechazos_etl'
SELECT fuente, motivo, COUNT(*)::bigint AS registros
FROM staging.rechazos_etl
GROUP BY fuente, motivo
ORDER BY fuente, registros DESC, motivo;

\echo '13. Resumen de staging.ingesta_metadata'
SELECT fuente, estado,
       COUNT(*)::bigint AS corridas,
       COALESCE(SUM(filas_leidas), 0)::bigint AS filas_leidas,
       COALESCE(SUM(filas_insertadas), 0)::bigint AS filas_insertadas,
       COALESCE(SUM(filas_actualizadas), 0)::bigint AS filas_actualizadas,
       COALESCE(SUM(filas_rechazadas), 0)::bigint AS filas_rechazadas,
       MAX(ultima_fecha_procesada) AS ultima_fecha_procesada
FROM staging.ingesta_metadata
GROUP BY fuente, estado
ORDER BY fuente, estado;

\echo '14. Validacion de paises permitidos URY, ARG, BRA'
SELECT 'staging.stg_firms' AS tabla, COUNT(*)::bigint AS filas_invalidas
FROM staging.stg_firms WHERE pais_codigo NOT IN ('URY','ARG','BRA')
UNION ALL SELECT 'staging.stg_meteo', COUNT(*)::bigint
FROM staging.stg_meteo WHERE pais_codigo NOT IN ('URY','ARG','BRA')
UNION ALL SELECT 'staging.stg_chirps', COUNT(*)::bigint
FROM staging.stg_chirps WHERE pais_codigo NOT IN ('URY','ARG','BRA')
UNION ALL SELECT 'staging.stg_modis', COUNT(*)::bigint
FROM staging.stg_modis WHERE pais_codigo NOT IN ('URY','ARG','BRA')
UNION ALL SELECT 'staging.stg_calidad_aire', COUNT(*)::bigint
FROM staging.stg_calidad_aire WHERE pais_codigo NOT IN ('URY','ARG','BRA')
UNION ALL SELECT 'dw.dim_ubicacion', COUNT(*)::bigint
FROM dw.dim_ubicacion WHERE pais_codigo NOT IN ('URY','ARG','BRA')
UNION ALL SELECT 'dw.dim_estacion_meteorologica', COUNT(*)::bigint
FROM dw.dim_estacion_meteorologica WHERE pais_codigo <> 'URY';

\echo '15. Validacion de coordenadas latitud/longitud'
SELECT 'staging.stg_firms' AS tabla, COUNT(*)::bigint AS filas_invalidas
FROM staging.stg_firms WHERE latitud NOT BETWEEN -90 AND 90 OR longitud NOT BETWEEN -180 AND 180
UNION ALL SELECT 'staging.stg_calidad_aire', COUNT(*)::bigint
FROM staging.stg_calidad_aire
WHERE (latitud IS NOT NULL AND latitud NOT BETWEEN -90 AND 90)
   OR (longitud IS NOT NULL AND longitud NOT BETWEEN -180 AND 180)
UNION ALL SELECT 'dw.dim_ubicacion', COUNT(*)::bigint
FROM dw.dim_ubicacion WHERE latitud NOT BETWEEN -90 AND 90 OR longitud NOT BETWEEN -180 AND 180;

\echo '16. Validacion de rangos ambientales y FIRMS'
SELECT 'staging.stg_firms.frp_mw' AS regla, COUNT(*)::bigint AS filas_invalidas
FROM staging.stg_firms WHERE frp_mw < 0
UNION ALL SELECT 'dw.fact_incendio.frp_mw', COUNT(*)::bigint
FROM dw.fact_incendio WHERE frp_mw < 0
UNION ALL SELECT 'staging.stg_meteo.humedad_pct', COUNT(*)::bigint
FROM staging.stg_meteo WHERE humedad_pct IS NOT NULL AND humedad_pct NOT BETWEEN 0 AND 100
UNION ALL SELECT 'dw.dim_clima.humedad_pct', COUNT(*)::bigint
FROM dw.dim_clima WHERE humedad_pct IS NOT NULL AND humedad_pct NOT BETWEEN 0 AND 100
UNION ALL SELECT 'staging.stg_meteo.direccion_viento_grados', COUNT(*)::bigint
FROM staging.stg_meteo WHERE direccion_viento_grados IS NOT NULL AND direccion_viento_grados NOT BETWEEN 0 AND 360
UNION ALL SELECT 'dw.dim_clima.direccion_viento_grados', COUNT(*)::bigint
FROM dw.dim_clima WHERE direccion_viento_grados IS NOT NULL AND direccion_viento_grados NOT BETWEEN 0 AND 360
UNION ALL SELECT 'staging.stg_chirps.precipitacion_mm', COUNT(*)::bigint
FROM staging.stg_chirps WHERE precipitacion_mm < 0
UNION ALL SELECT 'dw.dim_precipitacion.precipitacion_mm', COUNT(*)::bigint
FROM dw.dim_precipitacion WHERE precipitacion_mm < 0
UNION ALL SELECT 'staging.stg_calidad_aire.pm25', COUNT(*)::bigint
FROM staging.stg_calidad_aire WHERE pm25 IS NOT NULL AND pm25 < 0
UNION ALL SELECT 'staging.stg_calidad_aire.pm10', COUNT(*)::bigint
FROM staging.stg_calidad_aire WHERE pm10 IS NOT NULL AND pm10 < 0
UNION ALL SELECT 'dw.dim_calidad_aire.pm25', COUNT(*)::bigint
FROM dw.dim_calidad_aire WHERE pm25 IS NOT NULL AND pm25 < 0
UNION ALL SELECT 'dw.dim_calidad_aire.pm10', COUNT(*)::bigint
FROM dw.dim_calidad_aire WHERE pm10 IS NOT NULL AND pm10 < 0
ORDER BY regla;

\echo '17. Validacion INUMET solo Uruguay'
SELECT 'staging.stg_meteo fuente INUMET' AS regla, COUNT(*)::bigint AS filas_invalidas
FROM staging.stg_meteo
WHERE fuente='INUMET' AND pais_codigo <> 'URY'
UNION ALL SELECT 'dw.dim_estacion_meteorologica', COUNT(*)::bigint
FROM dw.dim_estacion_meteorologica
WHERE pais_codigo <> 'URY' OR fuente <> 'INUMET';

\echo '18. Validacion brillo_termico FIRMS no modelado como temperatura del aire'
SELECT 'fact_incendio tiene brillo_termico' AS regla,
       CASE WHEN EXISTS (
           SELECT 1 FROM information_schema.columns
           WHERE table_schema='dw' AND table_name='fact_incendio' AND column_name='brillo_termico'
       ) THEN 'OK' ELSE 'FALTA' END AS estado
UNION ALL
SELECT 'fact_incendio no tiene temperatura_c', 
       CASE WHEN NOT EXISTS (
           SELECT 1 FROM information_schema.columns
           WHERE table_schema='dw' AND table_name='fact_incendio' AND column_name='temperatura_c'
       ) THEN 'OK' ELSE 'REVISAR' END AS estado;

\echo 'D1 - Fin de validacion'
