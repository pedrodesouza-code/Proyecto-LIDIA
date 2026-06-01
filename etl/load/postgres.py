from __future__ import annotations

import json
import time
import uuid
from datetime import date

import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json

from config.settings import PG_CONFIG

SPATIAL_THRESHOLDS_KM = {
    "METEO": 100.0,
    "INUMET": 150.0,
    "CHIRPS": 100.0,
    "MODIS": 100.0,
    "CAMS": 100.0,
}

TABLES = {
    "FIRMS": ("stg_firms", ["record_hash", "natural_key", "fecha_adq", "hora_adq_hhmm", "latitud", "longitud", "pais_codigo", "frp_mw", "brillo_termico", "confianza", "satelite", "instrumento", "dia_noche", "raw_payload"]),
    "METEO": ("stg_meteo", ["record_hash", "natural_key", "fuente", "fecha", "fecha_hora_utc", "pais_codigo", "ubicacion", "departamento", "latitud", "longitud", "temperatura_c", "humedad_pct", "viento_kmh", "direccion_viento_grados", "presion_superficie_hpa", "precipitacion_mm", "raw_payload"]),
    "INUMET": ("stg_meteo", ["record_hash", "natural_key", "fuente", "fecha", "fecha_hora_utc", "pais_codigo", "ubicacion", "departamento", "latitud", "longitud", "temperatura_c", "humedad_pct", "viento_kmh", "direccion_viento_grados", "presion_superficie_hpa", "precipitacion_mm", "raw_payload"]),
    "CHIRPS": ("stg_chirps", ["record_hash", "natural_key", "fecha", "pais_codigo", "ubicacion", "latitud", "longitud", "precipitacion_mm", "raw_payload"]),
    "MODIS": ("stg_modis", ["record_hash", "natural_key", "anio", "pais_codigo", "ubicacion", "latitud", "longitud", "codigo_cobertura", "descripcion_cobertura", "raw_payload"]),
    "CAMS": ("stg_calidad_aire", ["record_hash", "natural_key", "fecha", "fecha_hora_utc", "pais_codigo", "ubicacion", "latitud", "longitud", "pm25", "pm10", "fuente", "raw_payload"]),
}


def connect():
    return psycopg2.connect(**PG_CONFIG)


def _event(cur, run_id, source, hash_value, kind, detail=None):
    cur.execute(
        "INSERT INTO audit.cdc_eventos (run_id, fuente, record_hash, tipo_evento, detalle) VALUES (%s,%s,%s,%s,%s)",
        (run_id, source, hash_value, kind, Json(detail or {})),
    )


def load_staging(source: str, accepted: list[dict], rejected: list[dict], promote: bool = True) -> dict[str, int]:
    """Carga incremental: clave natural detecta registro y hash detecta cambio."""
    table, columns = TABLES[source]
    run_id = str(uuid.uuid4())
    start = time.perf_counter()
    counts = {"leidas": len(accepted) + len(rejected), "insertadas": 0, "actualizadas": 0, "sin_cambio": 0, "rechazadas": len(rejected)}
    with connect() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO audit.etl_runs (run_id, fuente, etapa, estado) VALUES (%s,%s,'load','iniciado')", (run_id, source))
        for rejected_row in rejected:
            cur.execute(
                "INSERT INTO staging.rechazos_etl (run_id, fuente, motivo, registro) VALUES (%s,%s,%s,%s)",
                (run_id, source, rejected_row["motivo"], Json(rejected_row["registro"])),
            )
            _event(cur, run_id, source, "0" * 64, "rechazo", {"motivo": rejected_row["motivo"]})
        insert_stmt = sql.SQL("INSERT INTO staging.{} ({}) VALUES ({})").format(
            sql.Identifier(table), sql.SQL(",").join(map(sql.Identifier, columns)),
            sql.SQL(",").join(sql.Placeholder() for _ in columns),
        )
        update_cols = [col for col in columns if col not in {"natural_key"}]
        update_stmt = sql.SQL("UPDATE staging.{} SET {} WHERE natural_key=%s").format(
            sql.Identifier(table),
            sql.SQL(",").join(sql.SQL("{}=%s").format(sql.Identifier(col)) for col in update_cols),
        )
        for row in accepted:
            cur.execute(sql.SQL("SELECT record_hash FROM staging.{} WHERE natural_key=%s").format(sql.Identifier(table)), (row["natural_key"],))
            prior = cur.fetchone()
            values = [Json(row[col]) if col == "raw_payload" else row.get(col) for col in columns]
            if prior is None:
                cur.execute(insert_stmt, values)
                counts["insertadas"] += 1
                _event(cur, run_id, source, row["record_hash"], "alta")
            elif prior[0] == row["record_hash"]:
                counts["sin_cambio"] += 1
                _event(cur, run_id, source, row["record_hash"], "sin_cambio")
            else:
                updated = [Json(row[col]) if col == "raw_payload" else row.get(col) for col in update_cols]
                cur.execute(update_stmt, (*updated, row["natural_key"]))
                counts["actualizadas"] += 1
                _event(cur, run_id, source, row["record_hash"], "modificacion", {"hash_anterior": prior[0]})
        if promote and accepted:
            _promote(cur, source)
        latest = _latest_date(accepted)
        cur.execute(
            """UPDATE audit.etl_runs SET estado='ok', ultima_fecha_procesada=%s,
               filas_leidas=%s, filas_insertadas=%s, filas_actualizadas=%s,
               filas_rechazadas=%s, duracion_segundos=%s, finalizado_en=NOW()
               WHERE run_id=%s""",
            (latest, counts["leidas"], counts["insertadas"], counts["actualizadas"], counts["rechazadas"], round(time.perf_counter() - start, 3), run_id),
        )
    counts["run_id"] = run_id
    return counts


def _latest_date(rows: list[dict]) -> date | None:
    values = [row.get("fecha_adq") or row.get("fecha") for row in rows]
    values = [date.fromisoformat(v) for v in values if v]
    return max(values) if values else None


def _promote(cur, source: str) -> None:
    if source == "FIRMS":
        cur.execute("""INSERT INTO dw.dim_fecha (fecha, anio, mes, trimestre)
            SELECT DISTINCT fecha_adq, EXTRACT(YEAR FROM fecha_adq), EXTRACT(MONTH FROM fecha_adq), EXTRACT(QUARTER FROM fecha_adq)
            FROM staging.stg_firms ON CONFLICT (fecha) DO NOTHING""")
        cur.execute("""INSERT INTO dw.dim_ubicacion (pais_codigo,pais_nombre,latitud,longitud)
            SELECT DISTINCT pais_codigo, CASE pais_codigo WHEN 'URY' THEN 'Uruguay' WHEN 'ARG' THEN 'Argentina' ELSE 'Brasil' END, latitud, longitud
            FROM staging.stg_firms ON CONFLICT (pais_codigo,latitud,longitud) DO NOTHING""")
        cur.execute("""INSERT INTO dw.fact_incendio
            (natural_key,record_hash,fecha_id,ubicacion_id,frp_mw,brillo_termico,confianza,satelite,instrumento,dia_noche)
            SELECT s.natural_key,s.record_hash,d.fecha_id,u.ubicacion_id,s.frp_mw,s.brillo_termico,s.confianza,s.satelite,s.instrumento,s.dia_noche
            FROM staging.stg_firms s JOIN dw.dim_fecha d ON d.fecha=s.fecha_adq
            JOIN dw.dim_ubicacion u ON u.pais_codigo=s.pais_codigo AND u.latitud=s.latitud AND u.longitud=s.longitud
            ON CONFLICT (natural_key) DO UPDATE SET record_hash=EXCLUDED.record_hash, frp_mw=EXCLUDED.frp_mw,
              confianza=EXCLUDED.confianza, brillo_termico=EXCLUDED.brillo_termico, actualizado_en=NOW()""")
    elif source in {"METEO", "INUMET"}:
        cur.execute("""INSERT INTO dw.dim_fecha (fecha, anio, mes, trimestre)
            SELECT DISTINCT fecha, EXTRACT(YEAR FROM fecha), EXTRACT(MONTH FROM fecha), EXTRACT(QUARTER FROM fecha)
            FROM staging.stg_meteo WHERE fuente=%s ON CONFLICT (fecha) DO NOTHING""", (source,))
        cur.execute("""INSERT INTO dw.dim_ubicacion (pais_codigo,pais_nombre,ubicacion,latitud,longitud)
            SELECT DISTINCT pais_codigo, CASE pais_codigo WHEN 'URY' THEN 'Uruguay' WHEN 'ARG' THEN 'Argentina' ELSE 'Brasil' END,
                   ubicacion, latitud, longitud FROM staging.stg_meteo
            WHERE fuente=%s AND latitud IS NOT NULL AND longitud IS NOT NULL
            ON CONFLICT (pais_codigo,latitud,longitud) DO UPDATE
            SET ubicacion=COALESCE(dw.dim_ubicacion.ubicacion, EXCLUDED.ubicacion)""", (source,))
        if source == "INUMET":
            cur.execute("""INSERT INTO dw.dim_estacion_meteorologica
                (codigo_estacion,nombre,departamento,latitud,longitud)
                SELECT DISTINCT ubicacion, ubicacion, departamento, latitud, longitud FROM staging.stg_meteo
                WHERE fuente='INUMET' AND latitud IS NOT NULL AND longitud IS NOT NULL
                ON CONFLICT (codigo_estacion) DO UPDATE SET departamento=EXCLUDED.departamento,
                  latitud=EXCLUDED.latitud, longitud=EXCLUDED.longitud""")
        cur.execute("""INSERT INTO dw.dim_clima
            (fecha_id,ubicacion_id,estacion_id,fuente,fecha_hora_utc,temperatura_c,humedad_pct,
             viento_kmh,direccion_viento_grados,presion_superficie_hpa)
            SELECT d.fecha_id,u.ubicacion_id,e.estacion_id,s.fuente,s.fecha_hora_utc,s.temperatura_c,
                   s.humedad_pct,s.viento_kmh,s.direccion_viento_grados,s.presion_superficie_hpa
            FROM staging.stg_meteo s JOIN dw.dim_fecha d ON d.fecha=s.fecha
            JOIN dw.dim_ubicacion u ON u.pais_codigo=s.pais_codigo AND u.latitud=s.latitud AND u.longitud=s.longitud
            LEFT JOIN dw.dim_estacion_meteorologica e ON s.fuente='INUMET' AND e.codigo_estacion=s.ubicacion
            WHERE s.fuente=%s AND s.latitud IS NOT NULL AND s.longitud IS NOT NULL
            ON CONFLICT (fecha_hora_utc,ubicacion_id,fuente) DO UPDATE SET estacion_id=EXCLUDED.estacion_id,
              temperatura_c=EXCLUDED.temperatura_c, humedad_pct=EXCLUDED.humedad_pct,
              viento_kmh=EXCLUDED.viento_kmh, direccion_viento_grados=EXCLUDED.direccion_viento_grados,
              presion_superficie_hpa=EXCLUDED.presion_superficie_hpa""", (source,))
    elif source == "CHIRPS":
        cur.execute("""INSERT INTO dw.dim_fecha (fecha, anio, mes, trimestre)
            SELECT DISTINCT fecha, EXTRACT(YEAR FROM fecha), EXTRACT(MONTH FROM fecha), EXTRACT(QUARTER FROM fecha)
            FROM staging.stg_chirps ON CONFLICT (fecha) DO NOTHING""")
        cur.execute("""INSERT INTO dw.dim_ubicacion
            (pais_codigo,pais_nombre,ubicacion,latitud,longitud)
            SELECT DISTINCT pais_codigo,
                   CASE pais_codigo WHEN 'URY' THEN 'Uruguay' WHEN 'ARG' THEN 'Argentina' ELSE 'Brasil' END,
                   ubicacion, latitud, longitud
            FROM staging.stg_chirps
            WHERE latitud IS NOT NULL AND longitud IS NOT NULL
            ON CONFLICT (pais_codigo,latitud,longitud) DO UPDATE
            SET ubicacion=COALESCE(dw.dim_ubicacion.ubicacion, EXCLUDED.ubicacion)""")
        cur.execute("""INSERT INTO dw.dim_precipitacion (fecha_id,ubicacion_id,precipitacion_mm)
            SELECT d.fecha_id,u.ubicacion_id,s.precipitacion_mm FROM staging.stg_chirps s
            JOIN dw.dim_fecha d ON d.fecha=s.fecha
            JOIN dw.dim_ubicacion u ON u.pais_codigo=s.pais_codigo
             AND u.latitud=s.latitud AND u.longitud=s.longitud
            WHERE s.latitud IS NOT NULL AND s.longitud IS NOT NULL
            ON CONFLICT (fecha_id,ubicacion_id,fuente) DO UPDATE SET precipitacion_mm=EXCLUDED.precipitacion_mm""")
    elif source == "MODIS":
        cur.execute("""INSERT INTO dw.dim_ubicacion
            (pais_codigo,pais_nombre,ubicacion,latitud,longitud)
            SELECT DISTINCT pais_codigo,
                   CASE pais_codigo WHEN 'URY' THEN 'Uruguay' WHEN 'ARG' THEN 'Argentina' ELSE 'Brasil' END,
                   ubicacion, latitud, longitud
            FROM staging.stg_modis
            WHERE latitud IS NOT NULL AND longitud IS NOT NULL
            ON CONFLICT (pais_codigo,latitud,longitud) DO UPDATE
            SET ubicacion=COALESCE(dw.dim_ubicacion.ubicacion, EXCLUDED.ubicacion)""")
        cur.execute("""INSERT INTO dw.dim_cobertura_vegetal (anio,ubicacion_id,codigo_cobertura,descripcion_cobertura)
            SELECT s.anio,u.ubicacion_id,s.codigo_cobertura,s.descripcion_cobertura FROM staging.stg_modis s
            JOIN dw.dim_ubicacion u ON u.pais_codigo=s.pais_codigo
             AND u.latitud=s.latitud AND u.longitud=s.longitud
            WHERE s.latitud IS NOT NULL AND s.longitud IS NOT NULL
            ON CONFLICT (anio,ubicacion_id) DO UPDATE SET codigo_cobertura=EXCLUDED.codigo_cobertura, descripcion_cobertura=EXCLUDED.descripcion_cobertura""")
    elif source == "CAMS":
        cur.execute("""INSERT INTO dw.dim_fecha (fecha, anio, mes, trimestre)
            SELECT DISTINCT fecha, EXTRACT(YEAR FROM fecha), EXTRACT(MONTH FROM fecha), EXTRACT(QUARTER FROM fecha)
            FROM staging.stg_calidad_aire ON CONFLICT (fecha) DO NOTHING""")
        cur.execute("""INSERT INTO dw.dim_ubicacion
            (pais_codigo,pais_nombre,ubicacion,latitud,longitud)
            SELECT DISTINCT pais_codigo,
                   CASE pais_codigo WHEN 'URY' THEN 'Uruguay' WHEN 'ARG' THEN 'Argentina' ELSE 'Brasil' END,
                   ubicacion, latitud, longitud
            FROM staging.stg_calidad_aire
            WHERE latitud IS NOT NULL AND longitud IS NOT NULL
            ON CONFLICT (pais_codigo,latitud,longitud) DO UPDATE
            SET ubicacion=COALESCE(dw.dim_ubicacion.ubicacion, EXCLUDED.ubicacion)""")
        cur.execute("""INSERT INTO dw.dim_calidad_aire (fecha_id,ubicacion_id,pm25,pm10,fuente,observacion)
            SELECT d.fecha_id,u.ubicacion_id,ROUND(AVG(s.pm25), 3),ROUND(AVG(s.pm10), 3),'CAMS',
                   'CAMS/Open-Meteo Air Quality normalizado por Proyecto LIDIA'
            FROM staging.stg_calidad_aire s
            JOIN dw.dim_fecha d ON d.fecha=s.fecha
            JOIN dw.dim_ubicacion u ON u.pais_codigo=s.pais_codigo
             AND u.latitud=s.latitud AND u.longitud=s.longitud
            WHERE s.latitud IS NOT NULL AND s.longitud IS NOT NULL
            GROUP BY d.fecha_id,u.ubicacion_id
            ON CONFLICT (fecha_id,ubicacion_id) DO UPDATE SET
              pm25=EXCLUDED.pm25, pm10=EXCLUDED.pm10, fuente=EXCLUDED.fuente,
              observacion=EXCLUDED.observacion""")


def associate_environmental_dimensions() -> dict:
    """Vincula hechos con el vecino ambiental mas cercano compatible por pais y periodo."""
    association_id = str(uuid.uuid4())
    started = time.perf_counter()
    updates = {"clima": 0, "precipitacion": 0, "cobertura": 0}
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """CREATE TEMP TABLE tmp_clima_ubicaciones AS
               SELECT DISTINCT c.fecha_id, c.fuente, c.ubicacion_id,
                      u.pais_codigo, u.latitud, u.longitud
               FROM dw.dim_clima c
               JOIN dw.dim_ubicacion u ON u.ubicacion_id=c.ubicacion_id"""
        )
        cur.execute(
            "CREATE INDEX tmp_clima_fecha_pais ON tmp_clima_ubicaciones (fecha_id, pais_codigo)"
        )
        cur.execute(
            "SELECT DISTINCT fecha_id FROM dw.fact_incendio ORDER BY fecha_id"
        )
        date_ids = [row[0] for row in cur.fetchall()]
        for dimension in updates:
            cur.execute(
                sql.SQL("UPDATE dw.fact_incendio SET {}=NULL WHERE {} IS NOT NULL").format(
                    sql.Identifier(dimension + "_id"), sql.Identifier(dimension + "_id")
                )
            )
        conn.commit()

        for date_id in date_ids:
            cur.execute(
                """WITH matches AS (
                       SELECT f.incendio_id, chosen.clima_id
                       FROM dw.fact_incendio f
                       JOIN dw.dim_fecha fecha_foco ON fecha_foco.fecha_id=f.fecha_id
                       JOIN dw.dim_ubicacion foco ON foco.ubicacion_id=f.ubicacion_id
                       LEFT JOIN staging.stg_firms sf ON sf.natural_key=f.natural_key
                       CROSS JOIN LATERAL (
                           SELECT hourly.clima_id
                           FROM tmp_clima_ubicaciones ambiente
                           CROSS JOIN LATERAL (
                               SELECT c.clima_id
                               FROM dw.dim_clima c
                               WHERE c.fecha_id=ambiente.fecha_id
                                 AND c.fuente=ambiente.fuente
                                 AND c.ubicacion_id=ambiente.ubicacion_id
                               ORDER BY ABS(EXTRACT(EPOCH FROM (
                                   c.fecha_hora_utc -
                                   ((fecha_foco.fecha::timestamp AT TIME ZONE 'UTC')
                                    + make_interval(
                                        hours => COALESCE(sf.hora_adq_hhmm, 1200) / 100,
                                        mins => COALESCE(sf.hora_adq_hhmm, 1200) %% 100
                                    ))
                               ))), c.clima_id
                               LIMIT 1
                           ) hourly
                           WHERE ambiente.fecha_id=f.fecha_id
                             AND ambiente.pais_codigo=foco.pais_codigo
                             AND dw.distancia_haversine_km(
                                 foco.latitud::double precision, foco.longitud::double precision,
                                 ambiente.latitud::double precision, ambiente.longitud::double precision
                             ) <= CASE ambiente.fuente WHEN 'INUMET' THEN %s ELSE %s END
                           ORDER BY dw.distancia_haversine_km(
                                        foco.latitud::double precision, foco.longitud::double precision,
                                        ambiente.latitud::double precision, ambiente.longitud::double precision
                                    ),
                                    CASE ambiente.fuente
                                        WHEN 'INUMET' THEN 0 WHEN 'METEO' THEN 1 ELSE 2 END,
                                    hourly.clima_id
                           LIMIT 1
                       ) chosen
                       WHERE f.fecha_id=%s
                   )
                   UPDATE dw.fact_incendio f SET clima_id=m.clima_id, actualizado_en=NOW()
                   FROM matches m WHERE f.incendio_id=m.incendio_id""",
                (SPATIAL_THRESHOLDS_KM["INUMET"], SPATIAL_THRESHOLDS_KM["METEO"], date_id),
            )
            updates["clima"] += cur.rowcount
            cur.execute(
                """WITH matches AS (
                       SELECT f.incendio_id, chosen.precipitacion_id
                       FROM dw.fact_incendio f
                       JOIN dw.dim_fecha fecha_foco ON fecha_foco.fecha_id=f.fecha_id
                       JOIN dw.dim_ubicacion foco ON foco.ubicacion_id=f.ubicacion_id
                       CROSS JOIN LATERAL (
                           SELECT p.precipitacion_id
                           FROM dw.dim_precipitacion p
                           JOIN dw.dim_fecha fecha_lluvia ON fecha_lluvia.fecha_id=p.fecha_id
                           JOIN dw.dim_ubicacion lluvia ON lluvia.ubicacion_id=p.ubicacion_id
                           WHERE lluvia.pais_codigo=foco.pais_codigo
                             AND fecha_lluvia.anio=fecha_foco.anio AND fecha_lluvia.mes=fecha_foco.mes
                             AND dw.distancia_haversine_km(
                                 foco.latitud::double precision, foco.longitud::double precision,
                                 lluvia.latitud::double precision, lluvia.longitud::double precision
                             ) <= %s
                           ORDER BY dw.distancia_haversine_km(
                                        foco.latitud::double precision, foco.longitud::double precision,
                                        lluvia.latitud::double precision, lluvia.longitud::double precision
                                    ), p.precipitacion_id
                           LIMIT 1
                       ) chosen
                       WHERE f.fecha_id=%s
                   )
                   UPDATE dw.fact_incendio f SET precipitacion_id=m.precipitacion_id, actualizado_en=NOW()
                   FROM matches m WHERE f.incendio_id=m.incendio_id""",
                (SPATIAL_THRESHOLDS_KM["CHIRPS"], date_id),
            )
            updates["precipitacion"] += cur.rowcount
            cur.execute(
                """WITH matches AS (
                       SELECT f.incendio_id, chosen.cobertura_id
                       FROM dw.fact_incendio f
                       JOIN dw.dim_fecha fecha_foco ON fecha_foco.fecha_id=f.fecha_id
                       JOIN dw.dim_ubicacion foco ON foco.ubicacion_id=f.ubicacion_id
                       CROSS JOIN LATERAL (
                           SELECT c.cobertura_id
                           FROM dw.dim_cobertura_vegetal c
                           JOIN dw.dim_ubicacion cobertura ON cobertura.ubicacion_id=c.ubicacion_id
                           WHERE cobertura.pais_codigo=foco.pais_codigo
                             AND c.anio=fecha_foco.anio
                             AND dw.distancia_haversine_km(
                                 foco.latitud::double precision, foco.longitud::double precision,
                                 cobertura.latitud::double precision, cobertura.longitud::double precision
                             ) <= %s
                           ORDER BY dw.distancia_haversine_km(
                                        foco.latitud::double precision, foco.longitud::double precision,
                                        cobertura.latitud::double precision, cobertura.longitud::double precision
                                    ), c.cobertura_id
                           LIMIT 1
                       ) chosen
                       WHERE f.fecha_id=%s
                   )
                   UPDATE dw.fact_incendio f SET cobertura_id=m.cobertura_id, actualizado_en=NOW()
                   FROM matches m WHERE f.incendio_id=m.incendio_id""",
                (SPATIAL_THRESHOLDS_KM["MODIS"], date_id),
            )
            updates["cobertura"] += cur.rowcount
            conn.commit()

        metrics = {}
        distance_queries = {
            "clima": """SELECT MAX(dw.distancia_haversine_km(
                           foco.latitud::double precision, foco.longitud::double precision,
                           ambiente.latitud::double precision, ambiente.longitud::double precision))
                       FROM dw.fact_incendio f
                       JOIN dw.dim_ubicacion foco ON foco.ubicacion_id=f.ubicacion_id
                       JOIN dw.dim_clima c ON c.clima_id=f.clima_id
                       JOIN dw.dim_ubicacion ambiente ON ambiente.ubicacion_id=c.ubicacion_id""",
            "precipitacion": """SELECT MAX(dw.distancia_haversine_km(
                                   foco.latitud::double precision, foco.longitud::double precision,
                                   ambiente.latitud::double precision, ambiente.longitud::double precision))
                               FROM dw.fact_incendio f
                               JOIN dw.dim_ubicacion foco ON foco.ubicacion_id=f.ubicacion_id
                               JOIN dw.dim_precipitacion p ON p.precipitacion_id=f.precipitacion_id
                               JOIN dw.dim_ubicacion ambiente ON ambiente.ubicacion_id=p.ubicacion_id""",
            "cobertura": """SELECT MAX(dw.distancia_haversine_km(
                                foco.latitud::double precision, foco.longitud::double precision,
                                ambiente.latitud::double precision, ambiente.longitud::double precision))
                            FROM dw.fact_incendio f
                            JOIN dw.dim_ubicacion foco ON foco.ubicacion_id=f.ubicacion_id
                            JOIN dw.dim_cobertura_vegetal c ON c.cobertura_id=f.cobertura_id
                            JOIN dw.dim_ubicacion ambiente ON ambiente.ubicacion_id=c.ubicacion_id""",
        }
        for dimension, threshold in (
            ("clima", SPATIAL_THRESHOLDS_KM["INUMET"]),
            ("precipitacion", SPATIAL_THRESHOLDS_KM["CHIRPS"]),
            ("cobertura", SPATIAL_THRESHOLDS_KM["MODIS"]),
        ):
            cur.execute(
                sql.SQL(
                    """SELECT COUNT(*)::bigint, COUNT(f.{field})::bigint
                       FROM dw.fact_incendio f"""
                ).format(field=sql.Identifier(dimension + "_id"))
            )
            total, associated = cur.fetchone()
            cur.execute(distance_queries[dimension])
            maximum_distance = cur.fetchone()[0]
            metrics[dimension] = {
                "total_hechos": total,
                "asociados": associated,
                "sin_asociar": total - associated,
                "umbral_km": threshold,
                "distancia_maxima_km": float(maximum_distance) if maximum_distance is not None else None,
                "updates": updates[dimension],
            }
            cur.execute(
                """INSERT INTO audit.asociacion_espacial_runs
                   (asociacion_id, variable, umbral_km, total_hechos, asociados, sin_asociar,
                    distancia_maxima_km, detalle)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    association_id, dimension, threshold, total, associated, total - associated,
                    maximum_distance,
                    Json({
                        "metodo": "nearest_neighbor_haversine",
                        "regla_temporal": {
                            "clima": "misma_fecha_y_hora_mas_cercana",
                            "precipitacion": "mismo_anio_mes",
                            "cobertura": "mismo_anio",
                        }[dimension],
                        "umbrales_fuente_km": SPATIAL_THRESHOLDS_KM,
                    }),
                ),
            )
        conn.commit()
    return {
        "asociacion_id": association_id,
        "duracion_segundos": round(time.perf_counter() - started, 3),
        "metricas": metrics,
    }
