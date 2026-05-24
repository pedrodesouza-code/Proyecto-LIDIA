-- =============================================================================
-- SINIA-UY — Índices PostgreSQL
-- =============================================================================
-- Estrategia:
--   - Índices en columnas de filtro frecuente (fecha, punto, nivel_riesgo)
--   - Índice compuesto para el patrón de consulta más común: (fecha, id_punto)
--   - Índice en focos_calor por fecha_adq (consultas por rango temporal)
--   - Índice parcial para alertas (supera_oms_pm10 = TRUE) — evita scan completo
--
-- Ejecutar después de 02_schema.sql con datos cargados para medir impacto.
-- =============================================================================

-- ── focos_calor ───────────────────────────────────────────────────────────────
-- Consultas frecuentes: por fecha, por zona geográfica, por nivel de confianza

CREATE INDEX IF NOT EXISTS idx_focos_fecha_adq
    ON focos_calor (fecha_adq DESC);

-- Para filtros espaciales aproximados (bounding box por zona)
CREATE INDEX IF NOT EXISTS idx_focos_lat_lon
    ON focos_calor (latitud, longitud);

-- Para consultas geoespaciales reales con PostGIS (intersecciones, radios, polígonos)
CREATE INDEX IF NOT EXISTS idx_focos_geom_gist
    ON focos_calor USING GIST (geom)
    WHERE geom IS NOT NULL;

-- Patrón frecuente del dashboard y defensa: país + rango temporal
CREATE INDEX IF NOT EXISTS idx_focos_pais_fecha
    ON focos_calor (pais, fecha_adq DESC)
    WHERE pais IS NOT NULL;

-- Para análisis por confianza
CREATE INDEX IF NOT EXISTS idx_focos_confianza
    ON focos_calor (confianza_num)
    WHERE confianza_num IS NOT NULL;

-- Para análisis de intensidad (FRP)
CREATE INDEX IF NOT EXISTS idx_focos_frp
    ON focos_calor (potencia_radiativa DESC)
    WHERE potencia_radiativa IS NOT NULL;

-- ── meteo_diario ──────────────────────────────────────────────────────────────
-- Consultas frecuentes: por punto+fecha, por nivel_riesgo, por rango de fechas

-- Patrón de consulta principal del dashboard
CREATE INDEX IF NOT EXISTS idx_meteo_punto_fecha
    ON meteo_diario (id_punto, fecha DESC);

-- Para consultas por fecha sola (aggregaciones temporales)
CREATE INDEX IF NOT EXISTS idx_meteo_fecha
    ON meteo_diario (fecha DESC);

-- Para filtros por nivel de riesgo (alertas, análisis de días críticos)
CREATE INDEX IF NOT EXISTS idx_meteo_nivel_riesgo
    ON meteo_diario (nivel_riesgo, fecha DESC)
    WHERE nivel_riesgo IS NOT NULL;

-- Para el dashboard: solo forecast
CREATE INDEX IF NOT EXISTS idx_meteo_forecast
    ON meteo_diario (id_punto, fecha)
    WHERE tipo_dato = 'forecast';

-- ── calidad_aire_diario ───────────────────────────────────────────────────────

-- Patrón de consulta principal
CREATE INDEX IF NOT EXISTS idx_cams_punto_fecha
    ON calidad_aire_diario (id_punto, fecha DESC);

-- Índice parcial: solo días con alerta OMS (útil para el dashboard de alertas)
-- Evita scan completo de la tabla cuando se buscan solo días problemáticos
CREATE INDEX IF NOT EXISTS idx_cams_alerta_oms
    ON calidad_aire_diario (fecha DESC, id_punto)
    WHERE supera_oms_pm10 = TRUE;

-- Para análisis de tendencia temporal
CREATE INDEX IF NOT EXISTS idx_cams_fecha
    ON calidad_aire_diario (fecha DESC);

-- ── etl_ejecuciones ───────────────────────────────────────────────────────────

-- Para consultar la última ejecución de cada fuente (CDC)
CREATE INDEX IF NOT EXISTS idx_etl_fuente_inicio
    ON etl_ejecuciones (fuente, iniciado_en DESC);

CREATE INDEX IF NOT EXISTS idx_etl_estado
    ON etl_ejecuciones (estado, iniciado_en DESC)
    WHERE estado IN ('error', 'parcial');
