-- =============================================================================
-- SINIA-UY — Vistas analíticas regionales
-- =============================================================================
-- Las vistas cumplen dos roles:
--   1. Seguridad: el usuario dashboard (readonly) consulta vistas, no tablas base
--   2. Analítica: queries complejas pre-calculadas y reutilizables
--
-- Todas las vistas incluyen la columna `pais` para permitir
-- comparaciones entre Uruguay, Brasil, Argentina y Chile.
-- =============================================================================

-- ── Vista 1: v_riesgo_actual ──────────────────────────────────────────────────
-- KPI del dashboard: último nivel de riesgo por punto
CREATE OR REPLACE VIEW v_riesgo_actual AS
SELECT
    p.nombre           AS punto,
    p.pais,
    m.fecha,
    m.indice_riesgo,
    m.nivel_riesgo,
    m.temperature_2m_max       AS temp_max,
    m.relative_humidity_2m_min AS humedad_min,
    m.wind_speed_10m_max       AS viento_max,
    m.precipitation_sum        AS precipitacion
FROM meteo_diario m
JOIN puntos_monitoreo p ON p.id = m.id_punto
WHERE m.tipo_dato = 'historico'
  AND p.activo = TRUE
  AND p.pais IN ('ARG', 'BRA', 'CHL', 'URY')
  AND m.fecha = (
      SELECT MAX(fecha) FROM meteo_diario
      WHERE id_punto = m.id_punto AND tipo_dato = 'historico'
  );

COMMENT ON VIEW v_riesgo_actual IS 'Último registro histórico de riesgo de incendio por punto';

-- ── Vista 2: v_riesgo_historico ────────────────────────────────────────────────
-- Serie temporal completa de riesgo para todos los puntos
CREATE OR REPLACE VIEW v_riesgo_historico AS
SELECT
    p.nombre    AS punto,
    p.pais,
    m.fecha,
    m.tipo_dato,
    m.indice_riesgo,
    m.nivel_riesgo,
    m.temperature_2m_max,
    m.temperature_2m_min,
    m.relative_humidity_2m_min,
    m.wind_speed_10m_max,
    m.precipitation_sum,
    m.et0_fao_evapotranspiration,
    m.riesgo_temp,
    m.riesgo_humedad,
    m.riesgo_viento,
    m.riesgo_sequia
FROM meteo_diario m
JOIN puntos_monitoreo p ON p.id = m.id_punto
WHERE p.activo = TRUE
  AND p.pais IN ('ARG', 'BRA', 'CHL', 'URY')
ORDER BY p.nombre, m.fecha;

-- ── Vista 3: v_focos_resumen_diario ───────────────────────────────────────────
-- Agregación de focos por día y país: cantidad, FRP promedio, FRP máximo
CREATE OR REPLACE VIEW v_focos_resumen_diario AS
SELECT
    fecha_adq                  AS fecha,
    pais,
    COUNT(*)                   AS total_focos,
    ROUND(AVG(potencia_radiativa)::NUMERIC, 2) AS frp_promedio,
    ROUND(MAX(potencia_radiativa)::NUMERIC, 2) AS frp_maximo,
    SUM(CASE WHEN confianza_num = 3 THEN 1 ELSE 0 END) AS focos_alta_confianza,
    SUM(CASE WHEN es_diurno THEN 1 ELSE 0 END)         AS focos_diurnos
FROM focos_calor
GROUP BY fecha_adq, pais
ORDER BY fecha_adq DESC, total_focos DESC;

-- ── Vista 4: v_alertas_calidad_aire ──────────────────────────────────────────
-- Días con calidad del aire comprometida (sobre límite OMS)
CREATE OR REPLACE VIEW v_alertas_calidad_aire AS
SELECT
    p.nombre AS punto,
    p.pais,
    c.fecha,
    c.pm10_media,
    c.pm10_max,
    c.pm2_5_media,
    c.nivel_pm10,
    c.european_aqi_media,
    c.horas_validas
FROM calidad_aire_diario c
JOIN puntos_monitoreo p ON p.id = c.id_punto
WHERE c.supera_oms_pm10 = TRUE
  AND p.activo = TRUE
  AND p.pais IN ('ARG', 'BRA', 'CHL', 'URY')
ORDER BY c.fecha DESC, c.pm10_media DESC;

-- ── Vista 5: v_dias_criticos ──────────────────────────────────────────────────
-- Días con riesgo ALTO o MUY ALTO en al menos un punto (para alertas)
CREATE OR REPLACE VIEW v_dias_criticos AS
SELECT
    m.fecha,
    COUNT(DISTINCT m.id_punto)                    AS puntos_en_alerta,
    COUNT(DISTINCT p.pais)                        AS paises_en_alerta,
    MAX(m.indice_riesgo)                          AS indice_maximo,
    STRING_AGG(DISTINCT p.pais, ', ' ORDER BY p.pais) AS paises_afectados,
    STRING_AGG(p.nombre, ', ' ORDER BY p.nombre) AS puntos_afectados
FROM meteo_diario m
JOIN puntos_monitoreo p ON p.id = m.id_punto
WHERE m.nivel_riesgo IN ('alto', 'muy_alto')
  AND m.tipo_dato = 'historico'
  AND p.activo = TRUE
  AND p.pais IN ('ARG', 'BRA', 'CHL', 'URY')
GROUP BY m.fecha
ORDER BY m.fecha DESC;

-- ── Vista 6: v_forecast_riesgo ────────────────────────────────────────────────
-- Pronóstico de riesgo próximos 7 días (para el dashboard de tiempo real)
CREATE OR REPLACE VIEW v_forecast_riesgo AS
SELECT
    p.nombre AS punto,
    p.pais,
    m.fecha,
    m.indice_riesgo,
    m.nivel_riesgo,
    m.temperature_2m_max,
    m.relative_humidity_2m_min,
    m.wind_speed_10m_max,
    m.precipitation_probability_max
FROM meteo_diario m
JOIN puntos_monitoreo p ON p.id = m.id_punto
WHERE m.tipo_dato = 'forecast'
  AND p.activo = TRUE
  AND p.pais IN ('ARG', 'BRA', 'CHL', 'URY')
  AND m.fecha >= CURRENT_DATE
ORDER BY p.nombre, m.fecha;

-- ── Vista 7: v_riesgo_por_pais ────────────────────────────────────────────────
-- Agregación de riesgo a nivel país (KPI comparativo entre naciones)
CREATE OR REPLACE VIEW v_riesgo_por_pais AS
SELECT
    p.pais,
    DATE_TRUNC('month', m.fecha)::DATE          AS mes,
    ROUND(AVG(m.indice_riesgo)::NUMERIC, 4)     AS riesgo_promedio,
    ROUND(MAX(m.indice_riesgo)::NUMERIC, 4)     AS riesgo_maximo,
    COUNT(*) FILTER (WHERE m.nivel_riesgo IN ('alto','muy_alto'))
                                                 AS dias_criticos,
    COUNT(*)                                     AS total_registros
FROM meteo_diario m
JOIN puntos_monitoreo p ON p.id = m.id_punto
WHERE m.tipo_dato = 'historico'
  AND p.activo = TRUE
  AND p.pais IN ('ARG', 'BRA', 'CHL', 'URY')
GROUP BY p.pais, DATE_TRUNC('month', m.fecha)
ORDER BY p.pais, mes;

COMMENT ON VIEW v_riesgo_por_pais IS 'Riesgo de incendio mensual agregado por país — permite comparación entre Uruguay, Brasil, Argentina y Chile';

-- ── Vista 8: v_focos_por_pais_mes ─────────────────────────────────────────────
-- Cantidad de focos de calor por país y mes (para análisis comparativo)
CREATE OR REPLACE VIEW v_focos_por_pais_mes AS
SELECT
    pais,
    DATE_TRUNC('month', fecha_adq)::DATE AS mes,
    COUNT(*)                             AS total_focos,
    ROUND(AVG(potencia_radiativa)::NUMERIC, 2) AS frp_promedio,
    ROUND(MAX(potencia_radiativa)::NUMERIC, 2) AS frp_maximo,
    SUM(CASE WHEN confianza_num = 3 THEN 1 ELSE 0 END) AS focos_alta_confianza
FROM focos_calor
WHERE pais IN ('ARG', 'BRA', 'CHL', 'URY')
GROUP BY pais, DATE_TRUNC('month', fecha_adq)
ORDER BY pais, mes;

COMMENT ON VIEW v_focos_por_pais_mes IS 'Actividad de incendios mensual por país — base para análisis comparativo regional';

-- ── Otorgar acceso a las vistas al rol readonly ───────────────────────────────
GRANT SELECT ON v_riesgo_actual        TO sinia_readonly;
GRANT SELECT ON v_riesgo_historico     TO sinia_readonly;
GRANT SELECT ON v_focos_resumen_diario TO sinia_readonly;
GRANT SELECT ON v_alertas_calidad_aire TO sinia_readonly;
GRANT SELECT ON v_dias_criticos        TO sinia_readonly;
GRANT SELECT ON v_forecast_riesgo      TO sinia_readonly;
GRANT SELECT ON v_riesgo_por_pais      TO sinia_readonly;
GRANT SELECT ON v_focos_por_pais_mes   TO sinia_readonly;
