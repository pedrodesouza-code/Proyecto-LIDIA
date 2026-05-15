-- =============================================================================
-- SINIA-UY - Optimizacion materializada para agregados pesados
-- =============================================================================
-- Objetivo:
--   Reducir tiempos de consultas analiticas frecuentes sobre focos_calor.
--   La tabla supera los 10 millones de registros aun luego de acotar el alcance
--   a Uruguay, Brasil y Argentina; por eso se materializan los agregados usados
--   por dashboard, defensa y comparacion SQL vs NoSQL.
--
-- Refresco recomendado despues de cada carga incremental:
--   REFRESH MATERIALIZED VIEW mv_focos_por_pais;
--   REFRESH MATERIALIZED VIEW mv_focos_por_pais_mes;
-- =============================================================================

DROP MATERIALIZED VIEW IF EXISTS mv_focos_por_pais_mes;
DROP MATERIALIZED VIEW IF EXISTS mv_focos_por_pais;

CREATE MATERIALIZED VIEW mv_focos_por_pais AS
SELECT
    pais,
    COUNT(*) AS total_focos,
    ROUND(AVG(potencia_radiativa)::NUMERIC, 2) AS frp_promedio,
    ROUND(MAX(potencia_radiativa)::NUMERIC, 2) AS frp_maximo,
    SUM(CASE WHEN confianza_num = 3 THEN 1 ELSE 0 END) AS focos_alta_confianza
FROM focos_calor
WHERE pais IN ('ARG', 'BRA', 'URY')
GROUP BY pais;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_focos_por_pais_pais
    ON mv_focos_por_pais (pais);

CREATE MATERIALIZED VIEW mv_focos_por_pais_mes AS
SELECT
    pais,
    DATE_TRUNC('month', fecha_adq)::DATE AS mes,
    COUNT(*) AS total_focos,
    ROUND(AVG(potencia_radiativa)::NUMERIC, 2) AS frp_promedio,
    ROUND(MAX(potencia_radiativa)::NUMERIC, 2) AS frp_maximo,
    SUM(CASE WHEN confianza_num = 3 THEN 1 ELSE 0 END) AS focos_alta_confianza
FROM focos_calor
WHERE pais IN ('ARG', 'BRA', 'URY')
GROUP BY pais, DATE_TRUNC('month', fecha_adq)::DATE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_focos_por_pais_mes_pk
    ON mv_focos_por_pais_mes (pais, mes);

GRANT SELECT ON mv_focos_por_pais TO sinia_readonly;
GRANT SELECT ON mv_focos_por_pais_mes TO sinia_readonly;

COMMENT ON MATERIALIZED VIEW mv_focos_por_pais IS
    'Agregado materializado de focos por pais para consultas rapidas de dashboard y defensa';

COMMENT ON MATERIALIZED VIEW mv_focos_por_pais_mes IS
    'Agregado materializado de focos por pais y mes para evitar GROUP BY repetido sobre millones de filas';
