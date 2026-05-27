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
SELECT u.pais_codigo, COALESCE(u.region, u.ubicacion, 'Sin region') AS region,
       COUNT(*)::bigint AS focos, ROUND(AVG(i.frp_mw), 3) AS frp_promedio_mw
FROM dw.fact_incendio i
JOIN dw.dim_ubicacion u ON u.ubicacion_id = i.ubicacion_id
GROUP BY u.pais_codigo, COALESCE(u.region, u.ubicacion, 'Sin region');

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
       CASE WHEN COUNT(a.calidad_aire_id) = 0 THEN 'Pendiente de fuente validada' ELSE 'Disponible' END AS estado_dato
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

GRANT SELECT ON dw.v_incendios_pais_periodo, dw.v_incendios_region,
    dw.v_incendios_clima, dw.v_incendios_precipitacion, dw.v_incendios_cobertura,
    dw.v_calidad_aire_alta_actividad, dw.v_calidad_pipeline TO lidia_dashboard;
