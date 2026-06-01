\pset pager off
\echo 'D5 - Validacion funcional y consultas analiticas Proyecto LIDIA'

\echo '1. Estado de vistas dw esperadas'
WITH expected(view_name) AS (
    VALUES
        ('dw.v_incendios_pais_periodo'),
        ('dw.v_incendios_region'),
        ('dw.v_incendios_clima'),
        ('dw.v_incendios_precipitacion'),
        ('dw.v_incendios_cobertura'),
        ('dw.v_calidad_aire_alta_actividad'),
        ('dw.v_calidad_pipeline')
)
SELECT view_name,
       CASE WHEN to_regclass(view_name) IS NULL THEN 'FALTA' ELSE 'OK' END AS estado
FROM expected
ORDER BY view_name;

\echo '2. Focos por año'
SELECT d.anio, COUNT(*)::bigint AS focos, ROUND(AVG(f.frp_mw), 3) AS frp_promedio_mw
FROM dw.fact_incendio f
JOIN dw.dim_fecha d ON d.fecha_id = f.fecha_id
GROUP BY d.anio
ORDER BY d.anio;

\echo '3. Focos por pais usando vista dw.v_incendios_pais_periodo'
SELECT pais_codigo, pais_nombre, SUM(focos)::bigint AS focos, ROUND(AVG(frp_promedio_mw), 3) AS frp_promedio_mw
FROM dw.v_incendios_pais_periodo
GROUP BY pais_codigo, pais_nombre
ORDER BY focos DESC;

\echo '4. FRP promedio global'
SELECT COUNT(*)::bigint AS focos,
       ROUND(AVG(frp_mw), 3) AS frp_promedio_mw,
       ROUND(SUM(frp_mw), 3) AS frp_total_mw
FROM dw.fact_incendio;

\echo '5. Focos por confianza'
SELECT CASE
           WHEN confianza IS NULL THEN 'Sin dato'
           WHEN confianza < 30 THEN 'Baja'
           WHEN confianza < 80 THEN 'Media'
           ELSE 'Alta'
       END AS rango_confianza,
       COUNT(*)::bigint AS focos
FROM dw.fact_incendio
GROUP BY rango_confianza
ORDER BY rango_confianza;

\echo '6. Focos por cobertura vegetal si hay datos'
SELECT *
FROM dw.v_incendios_cobertura
ORDER BY focos DESC
LIMIT 20;

\echo '7. Relacion focos-clima si hay datos'
SELECT *
FROM dw.v_incendios_clima
WHERE temperatura_media_c IS NOT NULL OR humedad_media_pct IS NOT NULL
ORDER BY fecha DESC
LIMIT 20;

\echo '8. Precipitacion mensual si hay datos'
SELECT *
FROM dw.v_incendios_precipitacion
WHERE precipitacion_mm_promedio IS NOT NULL
ORDER BY anio DESC, mes DESC, pais_codigo
LIMIT 20;

\echo '9. Calidad del aire si hay datos o pendiente documentado'
SELECT *
FROM dw.v_calidad_aire_alta_actividad
ORDER BY fecha DESC, pais_codigo
LIMIT 20;

\echo '10. Metricas de calidad del pipeline'
SELECT fuente, estado,
       COUNT(*)::bigint AS corridas,
       COALESCE(SUM(filas_leidas), 0)::bigint AS filas_leidas,
       COALESCE(SUM(filas_insertadas), 0)::bigint AS filas_insertadas,
       COALESCE(SUM(filas_actualizadas), 0)::bigint AS filas_actualizadas,
       COALESCE(SUM(filas_rechazadas), 0)::bigint AS filas_rechazadas,
       MAX(iniciado_en) AS ultima_corrida
FROM dw.v_calidad_pipeline
GROUP BY fuente, estado
ORDER BY fuente, estado;
