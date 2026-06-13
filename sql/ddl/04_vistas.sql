-- Proyecto LIDIA - vistas que alimentan Streamlit.
CREATE OR REPLACE VIEW dw.v_incendios_pais_periodo AS
SELECT u.pais_codigo, u.pais_nombre, fch.anio, fch.mes,
       COUNT(*)::bigint AS focos,
       ROUND(AVG(i.frp_mw), 3) AS frp_promedio_mw,
       ROUND(SUM(i.frp_mw), 3) AS frp_total_mw
FROM dw.fact_incendio i
JOIN dw.dim_fecha fch ON fch.fecha_id = i.fecha_id
JOIN dw.dim_ubicacion u ON u.ubicacion_id = i.ubicacion_id
GROUP BY u.pais_codigo, u.pais_nombre, fch.anio, fch.mes;

CREATE OR REPLACE VIEW dw.v_incendios_region AS
SELECT u.pais_codigo, NULLIF(TRIM(u.region), '')::VARCHAR AS region,
       COUNT(*)::bigint AS focos, ROUND(AVG(i.frp_mw), 3) AS frp_promedio_mw
FROM dw.fact_incendio i
JOIN dw.dim_ubicacion u ON u.ubicacion_id = i.ubicacion_id
GROUP BY u.pais_codigo, NULLIF(TRIM(u.region), '')::VARCHAR;

CREATE OR REPLACE VIEW dw.v_focos_zona_espacial AS
SELECT
    u.pais_codigo,
    ROUND(u.latitud::numeric, 1) AS latitud_grilla,
    ROUND(u.longitud::numeric, 1) AS longitud_grilla,
    CONCAT(
        u.pais_codigo,
        '_LAT_', ROUND(u.latitud::numeric, 1),
        '_LON_', ROUND(u.longitud::numeric, 1)
    ) AS zona_espacial,
    COUNT(*)::bigint AS cantidad_focos,
    ROUND(AVG(i.frp_mw), 2) AS frp_promedio_mw
FROM dw.fact_incendio i
JOIN dw.dim_ubicacion u ON u.ubicacion_id = i.ubicacion_id
WHERE u.latitud IS NOT NULL
  AND u.longitud IS NOT NULL
GROUP BY
    u.pais_codigo,
    ROUND(u.latitud::numeric, 1),
    ROUND(u.longitud::numeric, 1);

CREATE OR REPLACE VIEW dw.v_focos_zona_espacial_ury AS
SELECT *
FROM dw.v_focos_zona_espacial
WHERE pais_codigo = 'URY';

CREATE OR REPLACE VIEW dw.v_incendios_clima AS
SELECT u.pais_codigo, fch.fecha, COUNT(*)::bigint AS focos,
       ROUND(AVG(i.frp_mw), 3) AS frp_promedio_mw,
       ROUND(AVG(c.temperatura_c), 2) AS temperatura_media_c,
       ROUND(AVG(c.humedad_pct), 2) AS humedad_media_pct
FROM dw.fact_incendio i
JOIN dw.dim_fecha fch ON fch.fecha_id = i.fecha_id
JOIN dw.dim_ubicacion u ON u.ubicacion_id = i.ubicacion_id
LEFT JOIN dw.dim_clima c ON c.clima_id = i.clima_id
GROUP BY u.pais_codigo, fch.fecha;

CREATE OR REPLACE VIEW dw.v_incendios_precipitacion AS
SELECT u.pais_codigo, fch.anio, fch.mes, COUNT(*)::bigint AS focos,
       ROUND(AVG(p.precipitacion_mm), 3) AS precipitacion_mm_promedio
FROM dw.fact_incendio i
JOIN dw.dim_fecha fch ON fch.fecha_id = i.fecha_id
JOIN dw.dim_ubicacion u ON u.ubicacion_id = i.ubicacion_id
LEFT JOIN dw.dim_precipitacion p ON p.precipitacion_id = i.precipitacion_id
GROUP BY u.pais_codigo, fch.anio, fch.mes;

CREATE OR REPLACE VIEW dw.v_incendios_cobertura AS
SELECT u.pais_codigo, COALESCE(c.descripcion_cobertura, 'Sin dato MODIS') AS cobertura,
       COUNT(*)::bigint AS focos, ROUND(AVG(i.frp_mw), 3) AS frp_promedio_mw
FROM dw.fact_incendio i
JOIN dw.dim_ubicacion u ON u.ubicacion_id = i.ubicacion_id
LEFT JOIN dw.dim_cobertura_vegetal c ON c.cobertura_id = i.cobertura_id
GROUP BY u.pais_codigo, COALESCE(c.descripcion_cobertura, 'Sin dato MODIS');

CREATE OR REPLACE VIEW dw.v_calidad_aire_alta_actividad AS
SELECT u.pais_codigo, fch.fecha, COUNT(*)::bigint AS focos,
       ROUND(AVG(a.pm25), 3) AS pm25, ROUND(AVG(a.pm10), 3) AS pm10,
       CASE WHEN COUNT(a.calidad_aire_id) = 0 THEN 'Pendiente CAMS/Open-Meteo Air Quality' ELSE 'Disponible' END AS estado_dato
FROM dw.fact_incendio i
JOIN dw.dim_fecha fch ON fch.fecha_id = i.fecha_id
JOIN dw.dim_ubicacion u ON u.ubicacion_id = i.ubicacion_id
LEFT JOIN dw.dim_calidad_aire a ON a.calidad_aire_id = i.calidad_aire_id
GROUP BY u.pais_codigo, fch.fecha
HAVING COUNT(*) >= 10;

CREATE OR REPLACE VIEW dw.v_calidad_pipeline AS
SELECT fuente, estado, iniciado_en, finalizado_en, duracion_segundos,
       filas_leidas, filas_insertadas, filas_actualizadas, filas_rechazadas
FROM audit.etl_runs
ORDER BY iniciado_en DESC;

CREATE OR REPLACE VIEW dw.v_resumen_calidad_pipeline AS
SELECT
    COALESCE(SUM(filas_insertadas), 0)::bigint AS altas,
    COALESCE(SUM(filas_actualizadas), 0)::bigint AS modificaciones,
    COALESCE(SUM(filas_rechazadas), 0)::bigint AS descartes_auditoria,
    (SELECT COUNT(*)::bigint FROM staging.rechazos_etl) AS rechazos_detallados
FROM audit.etl_runs;

-- Resumenes materializados para Streamlit.
-- Evitan recalcular uniones sobre millones de focos en cada interaccion del dashboard.
DROP MATERIALIZED VIEW IF EXISTS dw.mv_dashboard_focos_pais_periodo;
CREATE MATERIALIZED VIEW dw.mv_dashboard_focos_pais_periodo AS
SELECT *
FROM dw.v_incendios_pais_periodo;

CREATE INDEX IF NOT EXISTS idx_mv_dashboard_focos_pais_periodo
    ON dw.mv_dashboard_focos_pais_periodo (pais_codigo, anio, mes);

DROP MATERIALIZED VIEW IF EXISTS dw.mv_dashboard_incendios_precipitacion;
CREATE MATERIALIZED VIEW dw.mv_dashboard_incendios_precipitacion AS
SELECT *
FROM dw.v_incendios_precipitacion;

CREATE INDEX IF NOT EXISTS idx_mv_dashboard_incendios_precipitacion
    ON dw.mv_dashboard_incendios_precipitacion (pais_codigo, anio, mes);

GRANT SELECT ON dw.v_incendios_pais_periodo, dw.v_incendios_region,
    dw.v_focos_zona_espacial, dw.v_focos_zona_espacial_ury,
    dw.v_incendios_clima, dw.v_incendios_precipitacion, dw.v_incendios_cobertura,
    dw.v_calidad_aire_alta_actividad, dw.v_calidad_pipeline,
    dw.v_resumen_calidad_pipeline,
    dw.mv_dashboard_focos_pais_periodo, dw.mv_dashboard_incendios_precipitacion
    TO lidia_dashboard;
