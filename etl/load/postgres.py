from __future__ import annotations

import json
import time
import uuid
from datetime import date

import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json

from config.settings import PG_CONFIG

TABLES = {
    "FIRMS": ("stg_firms", ["record_hash", "natural_key", "fecha_adq", "hora_adq_hhmm", "latitud", "longitud", "pais_codigo", "frp_mw", "brillo_termico", "confianza", "satelite", "instrumento", "dia_noche", "raw_payload"]),
    "METEO": ("stg_meteo", ["record_hash", "natural_key", "fuente", "fecha", "fecha_hora_utc", "pais_codigo", "ubicacion", "departamento", "latitud", "longitud", "temperatura_c", "humedad_pct", "viento_kmh", "direccion_viento_grados", "presion_superficie_hpa", "precipitacion_mm", "raw_payload"]),
    "FORECAST": ("stg_meteo", ["record_hash", "natural_key", "fuente", "fecha", "fecha_hora_utc", "pais_codigo", "ubicacion", "departamento", "latitud", "longitud", "temperatura_c", "humedad_pct", "viento_kmh", "direccion_viento_grados", "presion_superficie_hpa", "precipitacion_mm", "raw_payload"]),
    "INUMET": ("stg_meteo", ["record_hash", "natural_key", "fuente", "fecha", "fecha_hora_utc", "pais_codigo", "ubicacion", "departamento", "latitud", "longitud", "temperatura_c", "humedad_pct", "viento_kmh", "direccion_viento_grados", "presion_superficie_hpa", "precipitacion_mm", "raw_payload"]),
    "CHIRPS": ("stg_chirps", ["record_hash", "natural_key", "fecha", "pais_codigo", "ubicacion", "precipitacion_mm", "raw_payload"]),
    "MODIS": ("stg_modis", ["record_hash", "natural_key", "anio", "pais_codigo", "ubicacion", "codigo_cobertura", "descripcion_cobertura", "raw_payload"]),
}


def connect():
    return psycopg2.connect(**PG_CONFIG)


def _event(cur, run_id, source, hash_value, kind, detail=None):
    cur.execute(
        "INSERT INTO audit.cdc_eventos (run_id, fuente, record_hash, tipo_evento, detalle) VALUES (%s,%s,%s,%s,%s)",
        (run_id, source, hash_value, kind, Json(detail or {})),
    )


def load_staging(source: str, accepted: list[dict], rejected: list[dict]) -> dict[str, int]:
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
    elif source in {"METEO", "FORECAST", "INUMET"}:
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
        cur.execute("""UPDATE dw.fact_incendio f SET clima_id=c.clima_id, actualizado_en=NOW()
            FROM dw.dim_clima c
            WHERE c.fuente=%s AND c.fecha_id=f.fecha_id AND c.ubicacion_id=f.ubicacion_id
              AND (f.clima_id IS NULL OR %s = 'INUMET')""", (source, source))
    elif source == "CHIRPS":
        cur.execute("""INSERT INTO dw.dim_fecha (fecha, anio, mes, trimestre)
            SELECT DISTINCT fecha, EXTRACT(YEAR FROM fecha), EXTRACT(MONTH FROM fecha), EXTRACT(QUARTER FROM fecha)
            FROM staging.stg_chirps ON CONFLICT (fecha) DO NOTHING""")
        cur.execute("""INSERT INTO dw.dim_precipitacion (fecha_id,ubicacion_id,precipitacion_mm)
            SELECT d.fecha_id,u.ubicacion_id,s.precipitacion_mm FROM staging.stg_chirps s
            JOIN dw.dim_fecha d ON d.fecha=s.fecha JOIN dw.dim_ubicacion u ON u.pais_codigo=s.pais_codigo AND u.ubicacion=s.ubicacion
            ON CONFLICT (fecha_id,ubicacion_id,fuente) DO UPDATE SET precipitacion_mm=EXCLUDED.precipitacion_mm""")
        cur.execute("""UPDATE dw.fact_incendio f SET precipitacion_id=p.precipitacion_id, actualizado_en=NOW()
            FROM dw.dim_precipitacion p
            JOIN dw.dim_fecha dp ON dp.fecha_id=p.fecha_id
            JOIN dw.dim_fecha df ON df.anio=dp.anio AND df.mes=dp.mes
            WHERE df.fecha_id=f.fecha_id AND p.ubicacion_id=f.ubicacion_id""")
    elif source == "MODIS":
        cur.execute("""INSERT INTO dw.dim_cobertura_vegetal (anio,ubicacion_id,codigo_cobertura,descripcion_cobertura)
            SELECT s.anio,u.ubicacion_id,s.codigo_cobertura,s.descripcion_cobertura FROM staging.stg_modis s
            JOIN dw.dim_ubicacion u ON u.pais_codigo=s.pais_codigo AND u.ubicacion=s.ubicacion
            ON CONFLICT (anio,ubicacion_id) DO UPDATE SET codigo_cobertura=EXCLUDED.codigo_cobertura, descripcion_cobertura=EXCLUDED.descripcion_cobertura""")
        cur.execute("""UPDATE dw.fact_incendio f SET cobertura_id=c.cobertura_id, actualizado_en=NOW()
            FROM dw.dim_cobertura_vegetal c
            JOIN dw.dim_fecha d ON d.anio=c.anio
            WHERE d.fecha_id=f.fecha_id AND c.ubicacion_id=f.ubicacion_id""")
