-- =============================================================================
-- SINIA-SA — Migración FIRMS geoespacial/PostGIS
-- =============================================================================
-- Usar en bases existentes creadas antes de incorporar shapefile/PostGIS.
-- Agrega geometría puntual, adapta confianza MODIS 0-100 y crea índices.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

ALTER TABLE focos_calor
    ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326),
    ADD COLUMN IF NOT EXISTS tipo_foco SMALLINT;

ALTER TABLE focos_calor
    ALTER COLUMN confianza_raw TYPE VARCHAR(10);

ALTER TABLE focos_calor
    DROP CONSTRAINT IF EXISTS focos_calor_confianza_num_check;

ALTER TABLE focos_calor
    ADD CONSTRAINT focos_calor_confianza_num_check
    CHECK (confianza_num BETWEEN 0 AND 100);

UPDATE focos_calor
SET geom = ST_SetSRID(ST_MakePoint(longitud::double precision, latitud::double precision), 4326)
WHERE geom IS NULL
  AND longitud IS NOT NULL
  AND latitud IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_focos_geom_gist
    ON focos_calor USING GIST (geom)
    WHERE geom IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_focos_pais_fecha
    ON focos_calor (pais, fecha_adq DESC)
    WHERE pais IS NOT NULL;
