-- Proyecto LIDIA - capacidad geoespacial opcional para la tabla de hechos FIRMS.
-- Ejecutar solo en una instalacion PostgreSQL que disponga de PostGIS.
CREATE EXTENSION IF NOT EXISTS postgis;

ALTER TABLE dw.fact_incendio
    ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);

UPDATE dw.fact_incendio f
SET geom = ST_SetSRID(ST_MakePoint(u.longitud::double precision, u.latitud::double precision), 4326)
FROM dw.dim_ubicacion u
WHERE u.ubicacion_id = f.ubicacion_id AND f.geom IS NULL;

CREATE INDEX IF NOT EXISTS idx_fact_incendio_geom_gist
    ON dw.fact_incendio USING GIST (geom)
    WHERE geom IS NOT NULL;
