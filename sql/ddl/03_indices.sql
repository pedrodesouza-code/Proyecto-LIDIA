-- Proyecto LIDIA - indices B-tree para joins y filtros analiticos.
CREATE INDEX IF NOT EXISTS idx_fact_fecha ON dw.fact_incendio (fecha_id);
CREATE INDEX IF NOT EXISTS idx_fact_ubicacion_fecha ON dw.fact_incendio (ubicacion_id, fecha_id);
CREATE INDEX IF NOT EXISTS idx_fact_frp ON dw.fact_incendio (frp_mw DESC) WHERE frp_mw IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fecha_anio_mes ON dw.dim_fecha (anio, mes);
CREATE INDEX IF NOT EXISTS idx_ubicacion_pais ON dw.dim_ubicacion (pais_codigo);
CREATE INDEX IF NOT EXISTS idx_clima_ubicacion_fecha ON dw.dim_clima (ubicacion_id, fecha_id);
CREATE INDEX IF NOT EXISTS idx_clima_ubicacion_instante ON dw.dim_clima (ubicacion_id, fecha_hora_utc);
CREATE INDEX IF NOT EXISTS idx_precipitacion_ubicacion_fecha ON dw.dim_precipitacion (ubicacion_id, fecha_id);
CREATE INDEX IF NOT EXISTS idx_cobertura_ubicacion_anio ON dw.dim_cobertura_vegetal (ubicacion_id, anio);
CREATE INDEX IF NOT EXISTS idx_etl_fuente_inicio ON audit.etl_runs (fuente, iniciado_en DESC);
CREATE INDEX IF NOT EXISTS idx_cdc_run_tipo ON audit.cdc_eventos (run_id, tipo_evento);
