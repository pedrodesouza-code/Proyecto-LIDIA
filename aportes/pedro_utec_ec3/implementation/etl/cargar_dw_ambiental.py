from __future__ import annotations

import argparse
import sys
import time
import uuid
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import PG_CONFIG


def connect():
    return psycopg2.connect(**PG_CONFIG)


def scalar(cur, sql: str) -> int:
    cur.execute(sql)
    return int(cur.fetchone()[0])


def execute_step(conn, name: str, sql: str) -> int:
    start = time.perf_counter()
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else 0
    conn.commit()
    print(f"{name}: rows={rows:,} seconds={time.perf_counter() - start:.1f}", flush=True)
    return rows


def write_audit(conn, run_id: str, rows_loaded: int, seconds: float, status: str = "success", error: str | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(etl_run_id), 0) + 1 FROM audit.etl_runs")
        etl_run_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO audit.etl_runs (
                etl_run_id, run_id, source_name, pipeline_name, load_type, status,
                started_at, finished_at, duration_seconds,
                records_extracted, records_transformed, records_loaded, records_rejected,
                parameters, error_message
            )
            VALUES (
                %s, %s, 'staging_ambiental', 'cargar_dw_ambiental', 'full', %s,
                NOW() - (%s || ' seconds')::interval, NOW(), %s,
                %s, %s, %s, 0, '{"target":"dw"}'::jsonb, %s
            )
            ON CONFLICT (run_id) DO NOTHING
            """,
            (etl_run_id, run_id, status, seconds, round(seconds, 3), rows_loaded, rows_loaded, rows_loaded, error),
        )
        cur.execute("SELECT COALESCE(MAX(log_id), 0) + 1 FROM audit.pipeline_logs")
        log_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO audit.pipeline_logs (log_id, run_id, log_level, step_name, message, details)
            VALUES (%s, %s, %s, 'load_dw', %s, %s::jsonb)
            """,
            (
                log_id,
                run_id,
                "INFO" if status == "success" else "ERROR",
                f"cargar_dw_ambiental {status}, rows={rows_loaded}",
                f'{{"rows":{rows_loaded}}}',
            ),
        )
    conn.commit()


INSERT_ENV_UBICACIONES = """
WITH raw AS (
    SELECT DISTINCT
        pais_codigo::char(3) AS pais_codigo,
        COALESCE(pais_nombre, pais_codigo::text) AS pais_nombre,
        region,
        departamento,
        ROUND(latitude::numeric, 6) AS latitud,
        ROUND(longitude::numeric, 6) AS longitud,
        'staging_openmeteo' AS fuente_ubicacion
    FROM staging.stg_openmeteo_clima
    WHERE pais_codigo IS NOT NULL
    UNION
    SELECT DISTINCT
        pais_codigo::char(3),
        COALESCE(pais_nombre, pais_codigo::text),
        region,
        departamento,
        ROUND(latitude::numeric, 6),
        ROUND(longitude::numeric, 6),
        'staging_calidad_aire'
    FROM staging.stg_calidad_aire
    WHERE pais_codigo IS NOT NULL
    UNION
    SELECT DISTINCT
        pais_codigo::char(3),
        COALESCE(pais_nombre, pais_codigo::text),
        region,
        departamento,
        ROUND(latitude::numeric, 6),
        ROUND(longitude::numeric, 6),
        'staging_chirps'
    FROM staging.stg_chirps_precipitacion
    WHERE pais_codigo IS NOT NULL
    UNION
    SELECT DISTINCT
        pais_codigo::char(3),
        COALESCE(pais_nombre, pais_codigo::text),
        region,
        departamento,
        ROUND(latitude::numeric, 6),
        ROUND(longitude::numeric, 6),
        'staging_modis'
    FROM staging.stg_modis_cobertura
    WHERE pais_codigo IS NOT NULL
),
dedup AS (
    SELECT pais_codigo, pais_nombre, MAX(region) AS region, MAX(departamento) AS departamento,
           latitud, longitud, STRING_AGG(DISTINCT fuente_ubicacion, ',') AS fuente_ubicacion
    FROM raw
    GROUP BY pais_codigo, pais_nombre, latitud, longitud
),
numbered AS (
    SELECT
        (SELECT COALESCE(MAX(ubicacion_id), 0) FROM dw.dim_ubicacion)
        + ROW_NUMBER() OVER (ORDER BY pais_codigo, latitud, longitud) AS ubicacion_id,
        *
    FROM dedup d
    WHERE NOT EXISTS (
        SELECT 1 FROM dw.dim_ubicacion u
        WHERE u.pais_codigo = d.pais_codigo
          AND u.latitud = d.latitud
          AND u.longitud = d.longitud
    )
)
INSERT INTO dw.dim_ubicacion (
    ubicacion_id, pais_codigo, pais_nombre, region, departamento, latitud, longitud, fuente_ubicacion
)
SELECT ubicacion_id, pais_codigo, pais_nombre, region, departamento, latitud, longitud, fuente_ubicacion
FROM numbered
ON CONFLICT (pais_codigo, latitud, longitud) DO NOTHING;
"""


INSERT_DIM_CLIMA = """
WITH src AS (
    SELECT
        f.fecha_id,
        u.ubicacion_id,
        AVG(s.temperature_2m)::numeric(8,3) AS temperatura_media_c,
        AVG(s.relative_humidity_2m)::numeric(8,3) AS humedad_relativa_media_pct,
        AVG(s.wind_speed_10m)::numeric(8,3) AS velocidad_viento_media_kmh,
        AVG(s.wind_direction_10m)::numeric(8,3) AS direccion_viento_grados,
        SUM(COALESCE(s.rain, 0))::numeric(10,3) AS lluvia_mm
    FROM staging.stg_openmeteo_clima s
    JOIN dw.dim_fecha f ON f.fecha = s.fecha
    JOIN dw.dim_ubicacion u
      ON u.pais_codigo = s.pais_codigo
     AND u.latitud = ROUND(s.latitude::numeric, 6)
     AND u.longitud = ROUND(s.longitude::numeric, 6)
    GROUP BY f.fecha_id, u.ubicacion_id
),
numbered AS (
    SELECT
        (SELECT COALESCE(MAX(clima_id), 0) FROM dw.dim_clima)
        + ROW_NUMBER() OVER (ORDER BY fecha_id, ubicacion_id) AS clima_id,
        src.*
    FROM src
)
INSERT INTO dw.dim_clima (
    clima_id, fecha_id, ubicacion_id, temperatura_media_c,
    humedad_relativa_media_pct, velocidad_viento_media_kmh,
    direccion_viento_grados, lluvia_mm, fuente
)
SELECT clima_id, fecha_id, ubicacion_id, temperatura_media_c,
       humedad_relativa_media_pct, velocidad_viento_media_kmh,
       direccion_viento_grados, lluvia_mm, 'Open-Meteo'
FROM numbered
ON CONFLICT (fecha_id, ubicacion_id) DO UPDATE SET
    temperatura_media_c = EXCLUDED.temperatura_media_c,
    humedad_relativa_media_pct = EXCLUDED.humedad_relativa_media_pct,
    velocidad_viento_media_kmh = EXCLUDED.velocidad_viento_media_kmh,
    direccion_viento_grados = EXCLUDED.direccion_viento_grados,
    lluvia_mm = EXCLUDED.lluvia_mm,
    fuente = EXCLUDED.fuente;
"""


INSERT_DIM_CALIDAD = """
WITH src AS (
    SELECT
        f.fecha_id,
        u.ubicacion_id,
        AVG(s.pm2_5)::numeric(10,3) AS pm25_ug_m3,
        AVG(s.pm10)::numeric(10,3) AS pm10_ug_m3,
        AVG(s.co)::numeric(10,3) AS co_ug_m3,
        AVG(s.no2)::numeric(10,3) AS no2_ug_m3,
        AVG(s.o3)::numeric(10,3) AS o3_ug_m3
    FROM staging.stg_calidad_aire s
    JOIN dw.dim_fecha f ON f.fecha = s.fecha
    JOIN dw.dim_ubicacion u
      ON u.pais_codigo = s.pais_codigo
     AND u.latitud = ROUND(s.latitude::numeric, 6)
     AND u.longitud = ROUND(s.longitude::numeric, 6)
    WHERE s.pm10 IS NOT NULL OR s.pm2_5 IS NOT NULL OR s.co IS NOT NULL OR s.no2 IS NOT NULL OR s.o3 IS NOT NULL
    GROUP BY f.fecha_id, u.ubicacion_id
),
numbered AS (
    SELECT
        (SELECT COALESCE(MAX(calidad_aire_id), 0) FROM dw.dim_calidad_aire)
        + ROW_NUMBER() OVER (ORDER BY fecha_id, ubicacion_id) AS calidad_aire_id,
        src.*
    FROM src
)
INSERT INTO dw.dim_calidad_aire (
    calidad_aire_id, fecha_id, ubicacion_id,
    pm25_ug_m3, pm10_ug_m3, co_ug_m3, no2_ug_m3, o3_ug_m3, fuente
)
SELECT calidad_aire_id, fecha_id, ubicacion_id,
       pm25_ug_m3, pm10_ug_m3, co_ug_m3, no2_ug_m3, o3_ug_m3,
       'Open-Meteo Air Quality / CAMS'
FROM numbered
ON CONFLICT (fecha_id, ubicacion_id) DO UPDATE SET
    pm25_ug_m3 = EXCLUDED.pm25_ug_m3,
    pm10_ug_m3 = EXCLUDED.pm10_ug_m3,
    co_ug_m3 = EXCLUDED.co_ug_m3,
    no2_ug_m3 = EXCLUDED.no2_ug_m3,
    o3_ug_m3 = EXCLUDED.o3_ug_m3,
    fuente = EXCLUDED.fuente;
"""


INSERT_DIM_PRECIPITACION = """
WITH src AS (
    SELECT
        u.ubicacion_id,
        s.anio,
        s.mes,
        AVG(s.precipitacion_acumulada_mm)::numeric(10,3) AS precipitacion_acumulada_mm,
        AVG(s.precipitacion_anomalia_pct)::numeric(10,4) AS precipitacion_anomalia_pct
    FROM staging.stg_chirps_precipitacion s
    JOIN dw.dim_ubicacion u
      ON u.pais_codigo = s.pais_codigo
     AND u.latitud = ROUND(s.latitude::numeric, 6)
     AND u.longitud = ROUND(s.longitude::numeric, 6)
    GROUP BY u.ubicacion_id, s.anio, s.mes
),
numbered AS (
    SELECT
        (SELECT COALESCE(MAX(precipitacion_id), 0) FROM dw.dim_precipitacion)
        + ROW_NUMBER() OVER (ORDER BY ubicacion_id, anio, mes) AS precipitacion_id,
        src.*
    FROM src
)
INSERT INTO dw.dim_precipitacion (
    precipitacion_id, ubicacion_id, anio, mes,
    precipitacion_acumulada_mm, precipitacion_anomalia_pct, fuente
)
SELECT precipitacion_id, ubicacion_id, anio, mes,
       precipitacion_acumulada_mm, precipitacion_anomalia_pct, 'CHIRPS'
FROM numbered
ON CONFLICT (ubicacion_id, anio, mes) DO UPDATE SET
    precipitacion_acumulada_mm = EXCLUDED.precipitacion_acumulada_mm,
    precipitacion_anomalia_pct = EXCLUDED.precipitacion_anomalia_pct,
    fuente = EXCLUDED.fuente;
"""


INSERT_DIM_COBERTURA = """
WITH src AS (
    SELECT
        u.ubicacion_id,
        s.anio,
        MAX(s.codigo_cobertura) AS codigo_cobertura,
        MAX(s.tipo_cobertura) AS tipo_cobertura,
        MAX(s.descripcion_cobertura) AS descripcion_cobertura,
        MAX(s.combustibilidad) AS combustibilidad
    FROM staging.stg_modis_cobertura s
    JOIN dw.dim_ubicacion u
      ON u.pais_codigo = s.pais_codigo
     AND u.latitud = ROUND(s.latitude::numeric, 6)
     AND u.longitud = ROUND(s.longitude::numeric, 6)
    GROUP BY u.ubicacion_id, s.anio
),
numbered AS (
    SELECT
        (SELECT COALESCE(MAX(cobertura_vegetal_id), 0) FROM dw.dim_cobertura_vegetal)
        + ROW_NUMBER() OVER (ORDER BY ubicacion_id, anio) AS cobertura_vegetal_id,
        src.*
    FROM src
)
INSERT INTO dw.dim_cobertura_vegetal (
    cobertura_vegetal_id, ubicacion_id, anio, codigo_cobertura,
    tipo_cobertura, descripcion_cobertura, combustibilidad, fuente
)
SELECT cobertura_vegetal_id, ubicacion_id, anio, codigo_cobertura,
       tipo_cobertura, descripcion_cobertura, combustibilidad, 'MODIS Land Cover'
FROM numbered
ON CONFLICT (ubicacion_id, anio) DO UPDATE SET
    codigo_cobertura = EXCLUDED.codigo_cobertura,
    tipo_cobertura = EXCLUDED.tipo_cobertura,
    descripcion_cobertura = EXCLUDED.descripcion_cobertura,
    combustibilidad = EXCLUDED.combustibilidad,
    fuente = EXCLUDED.fuente;
"""


INSERT_COUNTRY_AGG_UBICACIONES = """
WITH raw AS (
    SELECT 'COUNTRY_AGG_CLIMA' AS departamento, pais_codigo::char(3) AS pais_codigo,
           COALESCE(MAX(pais_nombre), pais_codigo::text) AS pais_nombre,
           AVG(latitude)::numeric(9,6) AS latitud,
           AVG(longitude)::numeric(9,6) AS longitud,
           'country_aggregate_clima' AS fuente_ubicacion
    FROM staging.stg_openmeteo_clima
    WHERE pais_codigo IS NOT NULL
    GROUP BY pais_codigo
    UNION ALL
    SELECT 'COUNTRY_AGG_AIRE', pais_codigo::char(3),
           COALESCE(MAX(pais_nombre), pais_codigo::text),
           AVG(latitude)::numeric(9,6),
           AVG(longitude)::numeric(9,6),
           'country_aggregate_air'
    FROM staging.stg_calidad_aire
    WHERE pais_codigo IS NOT NULL
    GROUP BY pais_codigo
    UNION ALL
    SELECT 'COUNTRY_AGG_PRECIPITACION', pais_codigo::char(3),
           COALESCE(MAX(pais_nombre), pais_codigo::text),
           AVG(latitude)::numeric(9,6),
           AVG(longitude)::numeric(9,6),
           'country_aggregate_chirps'
    FROM staging.stg_chirps_precipitacion
    WHERE pais_codigo IS NOT NULL
    GROUP BY pais_codigo
    UNION ALL
    SELECT 'COUNTRY_AGG_COBERTURA', pais_codigo::char(3),
           COALESCE(MAX(pais_nombre), pais_codigo::text),
           AVG(latitude)::numeric(9,6),
           AVG(longitude)::numeric(9,6),
           'country_aggregate_modis'
    FROM staging.stg_modis_cobertura
    WHERE pais_codigo IS NOT NULL
    GROUP BY pais_codigo
),
dedup AS (
    SELECT pais_codigo, pais_nombre, 'country_aggregate' AS region,
           departamento, latitud, longitud, fuente_ubicacion
    FROM raw
),
numbered AS (
    SELECT
        (SELECT COALESCE(MAX(ubicacion_id), 0) FROM dw.dim_ubicacion)
        + ROW_NUMBER() OVER (ORDER BY pais_codigo, departamento) AS ubicacion_id,
        *
    FROM dedup d
    WHERE NOT EXISTS (
        SELECT 1 FROM dw.dim_ubicacion u
        WHERE u.pais_codigo = d.pais_codigo
          AND u.latitud = d.latitud
          AND u.longitud = d.longitud
    )
)
INSERT INTO dw.dim_ubicacion (
    ubicacion_id, pais_codigo, pais_nombre, region, departamento, latitud, longitud, fuente_ubicacion
)
SELECT ubicacion_id, pais_codigo, pais_nombre, region, departamento, latitud, longitud, fuente_ubicacion
FROM numbered
ON CONFLICT (pais_codigo, latitud, longitud) DO NOTHING;
"""


INSERT_DIM_CLIMA_COUNTRY = """
WITH src AS (
    SELECT
        f.fecha_id,
        u.ubicacion_id,
        AVG(s.temperature_2m)::numeric(8,3) AS temperatura_media_c,
        AVG(s.relative_humidity_2m)::numeric(8,3) AS humedad_relativa_media_pct,
        AVG(s.wind_speed_10m)::numeric(8,3) AS velocidad_viento_media_kmh,
        AVG(s.wind_direction_10m)::numeric(8,3) AS direccion_viento_grados,
        SUM(COALESCE(s.rain, 0))::numeric(10,3) AS lluvia_mm
    FROM staging.stg_openmeteo_clima s
    JOIN dw.dim_fecha f ON f.fecha = s.fecha
    JOIN dw.dim_ubicacion u
      ON u.pais_codigo = s.pais_codigo
     AND u.departamento = 'COUNTRY_AGG_CLIMA'
    WHERE s.pais_codigo IS NOT NULL
    GROUP BY f.fecha_id, u.ubicacion_id
),
numbered AS (
    SELECT
        (SELECT COALESCE(MAX(clima_id), 0) FROM dw.dim_clima)
        + ROW_NUMBER() OVER (ORDER BY fecha_id, ubicacion_id) AS clima_id,
        src.*
    FROM src
)
INSERT INTO dw.dim_clima (
    clima_id, fecha_id, ubicacion_id, temperatura_media_c,
    humedad_relativa_media_pct, velocidad_viento_media_kmh,
    direccion_viento_grados, lluvia_mm, fuente
)
SELECT clima_id, fecha_id, ubicacion_id, temperatura_media_c,
       humedad_relativa_media_pct, velocidad_viento_media_kmh,
       direccion_viento_grados, lluvia_mm, 'Open-Meteo country aggregate'
FROM numbered
ON CONFLICT (fecha_id, ubicacion_id) DO UPDATE SET
    temperatura_media_c = EXCLUDED.temperatura_media_c,
    humedad_relativa_media_pct = EXCLUDED.humedad_relativa_media_pct,
    velocidad_viento_media_kmh = EXCLUDED.velocidad_viento_media_kmh,
    direccion_viento_grados = EXCLUDED.direccion_viento_grados,
    lluvia_mm = EXCLUDED.lluvia_mm,
    fuente = EXCLUDED.fuente;
"""


INSERT_DIM_AIRE_COUNTRY = """
WITH src AS (
    SELECT
        f.fecha_id,
        u.ubicacion_id,
        AVG(s.pm2_5)::numeric(10,3) AS pm25_ug_m3,
        AVG(s.pm10)::numeric(10,3) AS pm10_ug_m3,
        AVG(s.co)::numeric(10,3) AS co_ug_m3,
        AVG(s.no2)::numeric(10,3) AS no2_ug_m3,
        AVG(s.o3)::numeric(10,3) AS o3_ug_m3
    FROM staging.stg_calidad_aire s
    JOIN dw.dim_fecha f ON f.fecha = s.fecha
    JOIN dw.dim_ubicacion u
      ON u.pais_codigo = s.pais_codigo
     AND u.departamento = 'COUNTRY_AGG_AIRE'
    WHERE s.pais_codigo IS NOT NULL
      AND (s.pm10 IS NOT NULL OR s.pm2_5 IS NOT NULL OR s.co IS NOT NULL OR s.no2 IS NOT NULL OR s.o3 IS NOT NULL)
    GROUP BY f.fecha_id, u.ubicacion_id
),
numbered AS (
    SELECT
        (SELECT COALESCE(MAX(calidad_aire_id), 0) FROM dw.dim_calidad_aire)
        + ROW_NUMBER() OVER (ORDER BY fecha_id, ubicacion_id) AS calidad_aire_id,
        src.*
    FROM src
)
INSERT INTO dw.dim_calidad_aire (
    calidad_aire_id, fecha_id, ubicacion_id,
    pm25_ug_m3, pm10_ug_m3, co_ug_m3, no2_ug_m3, o3_ug_m3, fuente
)
SELECT calidad_aire_id, fecha_id, ubicacion_id,
       pm25_ug_m3, pm10_ug_m3, co_ug_m3, no2_ug_m3, o3_ug_m3,
       'Open-Meteo Air Quality / CAMS country aggregate'
FROM numbered
ON CONFLICT (fecha_id, ubicacion_id) DO UPDATE SET
    pm25_ug_m3 = EXCLUDED.pm25_ug_m3,
    pm10_ug_m3 = EXCLUDED.pm10_ug_m3,
    co_ug_m3 = EXCLUDED.co_ug_m3,
    no2_ug_m3 = EXCLUDED.no2_ug_m3,
    o3_ug_m3 = EXCLUDED.o3_ug_m3,
    fuente = EXCLUDED.fuente;
"""


INSERT_DIM_PRECIPITACION_COUNTRY = """
WITH src AS (
    SELECT
        u.ubicacion_id,
        s.anio,
        s.mes,
        AVG(s.precipitacion_acumulada_mm)::numeric(10,3) AS precipitacion_acumulada_mm,
        AVG(s.precipitacion_anomalia_pct)::numeric(10,4) AS precipitacion_anomalia_pct
    FROM staging.stg_chirps_precipitacion s
    JOIN dw.dim_ubicacion u
      ON u.pais_codigo = s.pais_codigo
     AND u.departamento = 'COUNTRY_AGG_PRECIPITACION'
    WHERE s.pais_codigo IS NOT NULL
    GROUP BY u.ubicacion_id, s.anio, s.mes
),
numbered AS (
    SELECT
        (SELECT COALESCE(MAX(precipitacion_id), 0) FROM dw.dim_precipitacion)
        + ROW_NUMBER() OVER (ORDER BY ubicacion_id, anio, mes) AS precipitacion_id,
        src.*
    FROM src
)
INSERT INTO dw.dim_precipitacion (
    precipitacion_id, ubicacion_id, anio, mes,
    precipitacion_acumulada_mm, precipitacion_anomalia_pct, fuente
)
SELECT precipitacion_id, ubicacion_id, anio, mes,
       precipitacion_acumulada_mm, precipitacion_anomalia_pct, 'CHIRPS country aggregate'
FROM numbered
ON CONFLICT (ubicacion_id, anio, mes) DO UPDATE SET
    precipitacion_acumulada_mm = EXCLUDED.precipitacion_acumulada_mm,
    precipitacion_anomalia_pct = EXCLUDED.precipitacion_anomalia_pct,
    fuente = EXCLUDED.fuente;
"""


INSERT_DIM_COBERTURA_COUNTRY = """
WITH src AS (
    SELECT
        u.ubicacion_id,
        s.anio,
        MODE() WITHIN GROUP (ORDER BY s.codigo_cobertura) AS codigo_cobertura,
        MAX(s.tipo_cobertura) AS tipo_cobertura,
        MODE() WITHIN GROUP (ORDER BY s.descripcion_cobertura) AS descripcion_cobertura,
        MODE() WITHIN GROUP (ORDER BY s.combustibilidad) AS combustibilidad
    FROM staging.stg_modis_cobertura s
    JOIN dw.dim_ubicacion u
      ON u.pais_codigo = s.pais_codigo
     AND u.departamento = 'COUNTRY_AGG_COBERTURA'
    WHERE s.pais_codigo IS NOT NULL
    GROUP BY u.ubicacion_id, s.anio
),
numbered AS (
    SELECT
        (SELECT COALESCE(MAX(cobertura_vegetal_id), 0) FROM dw.dim_cobertura_vegetal)
        + ROW_NUMBER() OVER (ORDER BY ubicacion_id, anio) AS cobertura_vegetal_id,
        src.*
    FROM src
)
INSERT INTO dw.dim_cobertura_vegetal (
    cobertura_vegetal_id, ubicacion_id, anio, codigo_cobertura,
    tipo_cobertura, descripcion_cobertura, combustibilidad, fuente
)
SELECT cobertura_vegetal_id, ubicacion_id, anio, codigo_cobertura,
       tipo_cobertura, descripcion_cobertura, combustibilidad, 'MODIS Land Cover country aggregate'
FROM numbered
ON CONFLICT (ubicacion_id, anio) DO UPDATE SET
    codigo_cobertura = EXCLUDED.codigo_cobertura,
    tipo_cobertura = EXCLUDED.tipo_cobertura,
    descripcion_cobertura = EXCLUDED.descripcion_cobertura,
    combustibilidad = EXCLUDED.combustibilidad,
    fuente = EXCLUDED.fuente;
"""


UPDATE_FACT_CLIMA = """
WITH clima_country AS (
    SELECT DISTINCT ON (dc.fecha_id, u.pais_codigo)
        dc.fecha_id,
        u.pais_codigo,
        dc.clima_id
    FROM dw.dim_clima dc
    JOIN dw.dim_ubicacion u ON u.ubicacion_id = dc.ubicacion_id
    WHERE dc.fuente LIKE 'Open-Meteo%'
    ORDER BY dc.fecha_id, u.pais_codigo, (u.region = 'country_aggregate') DESC, dc.clima_id
)
UPDATE dw.fact_incendio f
SET clima_id = dc.clima_id,
    fecha_actualizacion = NOW()
FROM dw.dim_ubicacion uf
JOIN clima_country dc ON dc.pais_codigo = uf.pais_codigo
WHERE f.clima_id IS NULL
  AND f.ubicacion_id = uf.ubicacion_id
  AND dc.fecha_id = f.fecha_id;
"""


UPDATE_FACT_AIRE = """
UPDATE dw.fact_incendio f
SET calidad_aire_id = da.calidad_aire_id,
    fecha_actualizacion = NOW()
FROM dw.dim_ubicacion uf
JOIN dw.dim_ubicacion ue
  ON ue.pais_codigo = uf.pais_codigo
 AND ue.departamento = 'COUNTRY_AGG_AIRE'
JOIN dw.dim_calidad_aire da ON da.ubicacion_id = ue.ubicacion_id
WHERE f.calidad_aire_id IS NULL
  AND f.ubicacion_id = uf.ubicacion_id
  AND da.fecha_id = f.fecha_id;
"""


UPDATE_FACT_PRECIPITACION = """
UPDATE dw.fact_incendio f
SET precipitacion_id = dp.precipitacion_id,
    fecha_actualizacion = NOW()
FROM dw.dim_ubicacion uf
JOIN dw.dim_ubicacion ue
  ON ue.pais_codigo = uf.pais_codigo
 AND ue.departamento = 'COUNTRY_AGG_PRECIPITACION'
JOIN dw.dim_fecha df ON df.fecha_id = f.fecha_id
JOIN dw.dim_precipitacion dp ON dp.ubicacion_id = ue.ubicacion_id
WHERE f.precipitacion_id IS NULL
  AND f.ubicacion_id = uf.ubicacion_id
  AND dp.anio = df.anio
  AND dp.mes = df.mes;
"""


UPDATE_FACT_COBERTURA = """
UPDATE dw.fact_incendio f
SET cobertura_vegetal_id = dc.cobertura_vegetal_id,
    fecha_actualizacion = NOW()
FROM dw.dim_ubicacion uf
JOIN dw.dim_ubicacion ue
  ON ue.pais_codigo = uf.pais_codigo
 AND ue.departamento = 'COUNTRY_AGG_COBERTURA'
JOIN dw.dim_fecha df ON df.fecha_id = f.fecha_id
JOIN dw.dim_cobertura_vegetal dc ON dc.ubicacion_id = ue.ubicacion_id
WHERE f.cobertura_vegetal_id IS NULL
  AND f.ubicacion_id = uf.ubicacion_id
  AND dc.anio = df.anio;
"""


VERIFY_SQL = """
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE clima_id IS NOT NULL) AS con_clima,
    COUNT(*) FILTER (WHERE calidad_aire_id IS NOT NULL) AS con_calidad_aire,
    COUNT(*) FILTER (WHERE precipitacion_id IS NOT NULL) AS con_precipitacion,
    COUNT(*) FILTER (WHERE cobertura_vegetal_id IS NOT NULL) AS con_cobertura
FROM dw.fact_incendio;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga dimensiones ambientales DW y enlaza fact_incendio.")
    parser.add_argument("--skip-link", action="store_true", help="Solo pobla dimensiones, no actualiza fact_incendio.")
    parser.add_argument("--link-only", action="store_true", help="Solo actualiza fact_incendio, asumiendo dimensiones ya pobladas.")
    args = parser.parse_args()

    run_id = "dw_ambiental_" + uuid.uuid4().hex[:12]
    start = time.perf_counter()
    rows_total = 0
    try:
        with connect() as conn:
            dimension_steps = [
                ("dim_ubicacion ambientales", INSERT_ENV_UBICACIONES),
                ("dim_clima", INSERT_DIM_CLIMA),
                ("dim_calidad_aire", INSERT_DIM_CALIDAD),
                ("dim_precipitacion", INSERT_DIM_PRECIPITACION),
                ("dim_cobertura_vegetal", INSERT_DIM_COBERTURA),
                ("dim_ubicacion agregados pais", INSERT_COUNTRY_AGG_UBICACIONES),
                ("dim_clima agregada pais", INSERT_DIM_CLIMA_COUNTRY),
                ("dim_calidad_aire agregada pais", INSERT_DIM_AIRE_COUNTRY),
                ("dim_precipitacion agregada pais", INSERT_DIM_PRECIPITACION_COUNTRY),
                ("dim_cobertura_vegetal agregada pais", INSERT_DIM_COBERTURA_COUNTRY),
            ]

            steps = [] if args.link_only else dimension_steps
            if not args.skip_link:
                steps.extend([
                    ("fact_incendio clima", UPDATE_FACT_CLIMA),
                    ("fact_incendio calidad_aire", UPDATE_FACT_AIRE),
                    ("fact_incendio precipitacion", UPDATE_FACT_PRECIPITACION),
                    ("fact_incendio cobertura", UPDATE_FACT_COBERTURA),
                ])

            for name, sql in steps:
                rows_total += execute_step(conn, name, sql)

            with conn.cursor() as cur:
                print("\nConteos dimensiones:")
                for table in ["dw.dim_clima", "dw.dim_calidad_aire", "dw.dim_precipitacion", "dw.dim_cobertura_vegetal"]:
                    print(table, scalar(cur, f"SELECT COUNT(*) FROM {table}"))
                cur.execute(VERIFY_SQL)
                print("Fact links:", cur.fetchone())

            write_audit(conn, run_id, rows_total, time.perf_counter() - start, "success")
        return 0
    except Exception as exc:
        try:
            with connect() as conn:
                write_audit(conn, run_id, rows_total, time.perf_counter() - start, "failed", str(exc))
        except Exception:
            pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())
