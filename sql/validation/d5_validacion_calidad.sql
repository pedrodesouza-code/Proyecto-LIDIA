\pset pager off
\echo 'D5 - Validacion de calidad de datos Proyecto LIDIA'

\echo '1. Conteos por tablas principales'
SELECT 'staging.stg_firms' AS tabla, COUNT(*)::bigint AS filas FROM staging.stg_firms
UNION ALL SELECT 'staging.stg_meteo', COUNT(*)::bigint FROM staging.stg_meteo
UNION ALL SELECT 'staging.stg_chirps', COUNT(*)::bigint FROM staging.stg_chirps
UNION ALL SELECT 'staging.stg_modis', COUNT(*)::bigint FROM staging.stg_modis
UNION ALL SELECT 'staging.stg_calidad_aire', COUNT(*)::bigint FROM staging.stg_calidad_aire
UNION ALL SELECT 'dw.fact_incendio', COUNT(*)::bigint FROM dw.fact_incendio
UNION ALL SELECT 'dw.dim_fecha', COUNT(*)::bigint FROM dw.dim_fecha
UNION ALL SELECT 'dw.dim_ubicacion', COUNT(*)::bigint FROM dw.dim_ubicacion
UNION ALL SELECT 'dw.dim_clima', COUNT(*)::bigint FROM dw.dim_clima
UNION ALL SELECT 'dw.dim_precipitacion', COUNT(*)::bigint FROM dw.dim_precipitacion
UNION ALL SELECT 'dw.dim_cobertura_vegetal', COUNT(*)::bigint FROM dw.dim_cobertura_vegetal
UNION ALL SELECT 'dw.dim_calidad_aire', COUNT(*)::bigint FROM dw.dim_calidad_aire
UNION ALL SELECT 'dw.dim_estacion_meteorologica', COUNT(*)::bigint FROM dw.dim_estacion_meteorologica
ORDER BY tabla;

\echo '2. Completitud de campos criticos en dw.fact_incendio'
SELECT COUNT(*)::bigint AS total,
       COUNT(*) FILTER (WHERE natural_key IS NULL)::bigint AS natural_key_nulos,
       COUNT(*) FILTER (WHERE record_hash IS NULL)::bigint AS record_hash_nulos,
       COUNT(*) FILTER (WHERE fecha_id IS NULL)::bigint AS fecha_id_nulos,
       COUNT(*) FILTER (WHERE ubicacion_id IS NULL)::bigint AS ubicacion_id_nulos,
       COUNT(*) FILTER (WHERE frp_mw IS NULL)::bigint AS frp_nulos,
       COUNT(*) FILTER (WHERE brillo_termico IS NULL)::bigint AS brillo_termico_nulos,
       COUNT(*) FILTER (WHERE calidad_aire_id IS NULL)::bigint AS calidad_aire_id_nulos_permitidos
FROM dw.fact_incendio;

\echo '3. Unicidad por natural_key'
SELECT 'staging.stg_firms' AS tabla, COUNT(*)::bigint AS natural_keys_duplicadas
FROM (SELECT natural_key FROM staging.stg_firms GROUP BY natural_key HAVING COUNT(*) > 1) d
UNION ALL SELECT 'staging.stg_meteo', COUNT(*)::bigint
FROM (SELECT natural_key FROM staging.stg_meteo GROUP BY natural_key HAVING COUNT(*) > 1) d
UNION ALL SELECT 'staging.stg_chirps', COUNT(*)::bigint
FROM (SELECT natural_key FROM staging.stg_chirps GROUP BY natural_key HAVING COUNT(*) > 1) d
UNION ALL SELECT 'staging.stg_modis', COUNT(*)::bigint
FROM (SELECT natural_key FROM staging.stg_modis GROUP BY natural_key HAVING COUNT(*) > 1) d
UNION ALL SELECT 'staging.stg_calidad_aire', COUNT(*)::bigint
FROM (SELECT natural_key FROM staging.stg_calidad_aire GROUP BY natural_key HAVING COUNT(*) > 1) d
UNION ALL SELECT 'dw.fact_incendio', COUNT(*)::bigint
FROM (SELECT natural_key FROM dw.fact_incendio GROUP BY natural_key HAVING COUNT(*) > 1) d
ORDER BY tabla;

\echo '4. Coordenadas y paises validos'
SELECT 'dw.dim_ubicacion coordenadas invalidas' AS validacion, COUNT(*)::bigint AS hallazgos
FROM dw.dim_ubicacion
WHERE latitud NOT BETWEEN -90 AND 90 OR longitud NOT BETWEEN -180 AND 180
UNION ALL
SELECT 'dw.dim_ubicacion pais fuera de alcance', COUNT(*)::bigint
FROM dw.dim_ubicacion
WHERE pais_codigo NOT IN ('URY','ARG','BRA')
UNION ALL
SELECT 'staging.stg_firms pais fuera de alcance', COUNT(*)::bigint
FROM staging.stg_firms
WHERE pais_codigo NOT IN ('URY','ARG','BRA')
UNION ALL
SELECT 'staging.stg_meteo pais fuera de alcance', COUNT(*)::bigint
FROM staging.stg_meteo
WHERE pais_codigo NOT IN ('URY','ARG','BRA')
UNION ALL
SELECT 'staging.stg_chirps pais fuera de alcance', COUNT(*)::bigint
FROM staging.stg_chirps
WHERE pais_codigo NOT IN ('URY','ARG','BRA')
UNION ALL
SELECT 'staging.stg_modis pais fuera de alcance', COUNT(*)::bigint
FROM staging.stg_modis
WHERE pais_codigo NOT IN ('URY','ARG','BRA')
UNION ALL
SELECT 'staging.stg_calidad_aire pais fuera de alcance', COUNT(*)::bigint
FROM staging.stg_calidad_aire
WHERE pais_codigo NOT IN ('URY','ARG','BRA')
ORDER BY validacion;

\echo '5. Rangos validos'
SELECT 'fact_incendio frp_mw negativo' AS validacion, COUNT(*)::bigint AS hallazgos
FROM dw.fact_incendio WHERE frp_mw < 0
UNION ALL
SELECT 'stg_firms frp_mw negativo', COUNT(*)::bigint
FROM staging.stg_firms WHERE frp_mw < 0
UNION ALL
SELECT 'dim_clima humedad fuera 0-100', COUNT(*)::bigint
FROM dw.dim_clima WHERE humedad_pct IS NOT NULL AND humedad_pct NOT BETWEEN 0 AND 100
UNION ALL
SELECT 'stg_meteo humedad fuera 0-100', COUNT(*)::bigint
FROM staging.stg_meteo WHERE humedad_pct IS NOT NULL AND humedad_pct NOT BETWEEN 0 AND 100
UNION ALL
SELECT 'dim_clima direccion viento fuera 0-360', COUNT(*)::bigint
FROM dw.dim_clima WHERE direccion_viento_grados IS NOT NULL AND direccion_viento_grados NOT BETWEEN 0 AND 360
UNION ALL
SELECT 'stg_meteo direccion viento fuera 0-360', COUNT(*)::bigint
FROM staging.stg_meteo WHERE direccion_viento_grados IS NOT NULL AND direccion_viento_grados NOT BETWEEN 0 AND 360
UNION ALL
SELECT 'dim_precipitacion negativa', COUNT(*)::bigint
FROM dw.dim_precipitacion WHERE precipitacion_mm < 0
UNION ALL
SELECT 'stg_chirps precipitacion negativa', COUNT(*)::bigint
FROM staging.stg_chirps WHERE precipitacion_mm < 0
UNION ALL
SELECT 'dim_calidad_aire pm25 negativa', COUNT(*)::bigint
FROM dw.dim_calidad_aire WHERE pm25 IS NOT NULL AND pm25 < 0
UNION ALL
SELECT 'dim_calidad_aire pm10 negativa', COUNT(*)::bigint
FROM dw.dim_calidad_aire WHERE pm10 IS NOT NULL AND pm10 < 0
UNION ALL
SELECT 'stg_calidad_aire pm25 negativa', COUNT(*)::bigint
FROM staging.stg_calidad_aire WHERE pm25 IS NOT NULL AND pm25 < 0
UNION ALL
SELECT 'stg_calidad_aire pm10 negativa', COUNT(*)::bigint
FROM staging.stg_calidad_aire WHERE pm10 IS NOT NULL AND pm10 < 0
ORDER BY validacion;

\echo '6. INUMET solo Uruguay'
SELECT 'staging.stg_meteo INUMET fuera de URY' AS validacion, COUNT(*)::bigint AS hallazgos
FROM staging.stg_meteo
WHERE fuente = 'INUMET' AND pais_codigo <> 'URY'
UNION ALL
SELECT 'dw.dim_estacion_meteorologica pais distinto URY', COUNT(*)::bigint
FROM dw.dim_estacion_meteorologica
WHERE pais_codigo <> 'URY'
ORDER BY validacion;

\echo '7. brightness no modelado como temperatura de aire'
SELECT table_schema, table_name, column_name
FROM information_schema.columns
WHERE table_schema IN ('staging','dw')
  AND column_name ILIKE '%brightness%'
ORDER BY table_schema, table_name, column_name;

\echo '8. Columnas de temperatura reales'
SELECT table_schema, table_name, column_name
FROM information_schema.columns
WHERE table_schema IN ('staging','dw')
  AND column_name IN ('temperatura_c','brillo_termico')
ORDER BY table_schema, table_name, column_name;

\echo '9. Claves foraneas principales no rotas'
SELECT 'fact_incendio fecha_id sin dim_fecha' AS validacion, COUNT(*)::bigint AS hallazgos
FROM dw.fact_incendio f LEFT JOIN dw.dim_fecha d ON d.fecha_id = f.fecha_id
WHERE d.fecha_id IS NULL
UNION ALL
SELECT 'fact_incendio ubicacion_id sin dim_ubicacion', COUNT(*)::bigint
FROM dw.fact_incendio f LEFT JOIN dw.dim_ubicacion u ON u.ubicacion_id = f.ubicacion_id
WHERE u.ubicacion_id IS NULL
UNION ALL
SELECT 'fact_incendio clima_id roto', COUNT(*)::bigint
FROM dw.fact_incendio f LEFT JOIN dw.dim_clima c ON c.clima_id = f.clima_id
WHERE f.clima_id IS NOT NULL AND c.clima_id IS NULL
UNION ALL
SELECT 'fact_incendio precipitacion_id roto', COUNT(*)::bigint
FROM dw.fact_incendio f LEFT JOIN dw.dim_precipitacion p ON p.precipitacion_id = f.precipitacion_id
WHERE f.precipitacion_id IS NOT NULL AND p.precipitacion_id IS NULL
UNION ALL
SELECT 'fact_incendio cobertura_id roto', COUNT(*)::bigint
FROM dw.fact_incendio f LEFT JOIN dw.dim_cobertura_vegetal c ON c.cobertura_id = f.cobertura_id
WHERE f.cobertura_id IS NOT NULL AND c.cobertura_id IS NULL
UNION ALL
SELECT 'fact_incendio calidad_aire_id roto', COUNT(*)::bigint
FROM dw.fact_incendio f LEFT JOIN dw.dim_calidad_aire a ON a.calidad_aire_id = f.calidad_aire_id
WHERE f.calidad_aire_id IS NOT NULL AND a.calidad_aire_id IS NULL
ORDER BY validacion;

\echo '10. Rechazos por fuente y motivo'
SELECT fuente, motivo, COUNT(*)::bigint AS rechazos, MAX(rechazado_en) AS ultimo_rechazo
FROM staging.rechazos_etl
GROUP BY fuente, motivo
ORDER BY fuente, rechazos DESC, motivo;
