-- Proyecto LIDIA - regiones administrativas auxiliares.
--
-- Este script prepara una referencia geoespacial opcional para asignar
-- departamentos de Uruguay por point-in-polygon. No crea polígonos ficticios:
-- requiere cargar una capa cartográfica real mediante
-- scripts/cargar_regiones_administrativas.py.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'postgis') THEN
        CREATE EXTENSION IF NOT EXISTS postgis;

        EXECUTE $ddl$
            CREATE TABLE IF NOT EXISTS dw.ref_region_administrativa (
                region_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                pais_codigo CHAR(3) NOT NULL CHECK (pais_codigo IN ('URY','ARG','BRA')),
                region VARCHAR(100) NOT NULL,
                nivel_administrativo VARCHAR(40) NOT NULL,
                fuente_cartografica VARCHAR(200) NOT NULL,
                geom geometry(MultiPolygon, 4326) NOT NULL,
                creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (pais_codigo, region, nivel_administrativo)
            )
        $ddl$;

        EXECUTE $ddl$
            CREATE INDEX IF NOT EXISTS idx_ref_region_admin_geom
            ON dw.ref_region_administrativa USING GIST (geom)
        $ddl$;

        EXECUTE $ddl$
            CREATE INDEX IF NOT EXISTS idx_ref_region_admin_pais_nivel
            ON dw.ref_region_administrativa (pais_codigo, nivel_administrativo, region)
        $ddl$;

        EXECUTE $ddl$
            CREATE OR REPLACE FUNCTION dw.actualizar_region_ubicacion_desde_poligonos()
            RETURNS TABLE(ubicaciones_actualizadas BIGINT)
            LANGUAGE plpgsql
            AS $fn$
            BEGIN
                UPDATE dw.dim_ubicacion u
                SET region = r.region
                FROM dw.ref_region_administrativa r
                WHERE u.pais_codigo = r.pais_codigo
                  AND u.pais_codigo = 'URY'
                  AND r.nivel_administrativo = 'departamento'
                  AND u.latitud IS NOT NULL
                  AND u.longitud IS NOT NULL
                  AND (u.region IS NULL OR TRIM(u.region) = '')
                  AND ST_Contains(
                      r.geom,
                      ST_SetSRID(ST_Point(u.longitud::double precision, u.latitud::double precision), 4326)
                  );

                GET DIAGNOSTICS ubicaciones_actualizadas = ROW_COUNT;
                RETURN NEXT;
            END
            $fn$
        $ddl$;
    ELSE
        RAISE NOTICE 'PostGIS no está disponible. No se crea dw.ref_region_administrativa.';
    END IF;
END $$;
