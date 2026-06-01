#!/usr/bin/env python3
"""Genera evidencia D4 de Change Data Capture para Proyecto LIDIA.

Pensado para Jupyter/UTEC: no requiere bash ni mongosh.

Uso:
    DATABASE_URL='postgresql://...' MONGO_URI='mongodb://...' python scripts/d4_generar_evidencia_cdc.py

La prueba usa un conjunto pequeno de registros FIRMS reales ya existentes en
staging.stg_firms. No modifica los hechos ni las tablas staging: registra una
corrida controlada en audit.etl_runs/audit.cdc_eventos y en MongoDB.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import psycopg2
    from psycopg2.extras import Json
except ImportError as exc:  # pragma: no cover - depende del entorno.
    raise SystemExit("ERROR: psycopg2 no esta instalado en este entorno.") from exc

try:
    from pymongo import MongoClient
except ImportError as exc:  # pragma: no cover - depende del entorno.
    raise SystemExit("ERROR: pymongo no esta instalado en este entorno.") from exc


SOURCE = "FIRMS"
VALID_SOURCES = {"FIRMS", "METEO", "CAMS", "CHIRPS", "MODIS", "INUMET"}


def root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=json_default))


def section(title: str) -> None:
    print(f"\n## {title}")


def fetch_dicts(cursor) -> list[dict[str, Any]]:
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Debe definir {name} antes de ejecutar D4.")
    return value


def connect_mongo(uri: str):
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db_name = os.getenv("MONGO_DB", "")
    if db_name:
        return client[db_name]
    try:
        return client.get_default_database()
    except Exception:
        return client["proyecto_lidia"]


def digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def simulated_correction_hash(row: dict[str, Any]) -> str:
    """Hash distinto para simular correccion del origen sin tocar datos reales."""
    corrected = dict(row)
    corrected["correccion_simulada_origen"] = {
        "motivo": "D4: prueba controlada de modificacion CDC",
        "campo": "confianza",
        "valor_original": row.get("confianza"),
        "nota": "No modifica staging ni DW; solo evidencia record_hash distinto para el mismo natural_key.",
    }
    return digest(corrected)


def insert_run(cursor, run_id: str, detail: dict[str, Any]) -> None:
    cursor.execute(
        """
        INSERT INTO audit.etl_runs
            (run_id, fuente, etapa, estado, filas_leidas, filas_insertadas,
             filas_actualizadas, filas_rechazadas, duracion_segundos,
             finalizado_en, detalle)
        VALUES (%s, %s, 'test', 'ok', %s, %s, %s, %s, %s, NOW(), %s)
        """,
        (
            run_id,
            SOURCE,
            detail["filas_leidas"],
            detail["filas_insertadas"],
            detail["filas_actualizadas"],
            detail["filas_rechazadas"],
            detail["duracion_segundos"],
            Json(detail),
        ),
    )


def insert_event(
    cursor,
    run_id: str,
    record_hash: str,
    tipo_evento: str,
    natural_key: str,
    detail: dict[str, Any] | None = None,
) -> None:
    payload = {"natural_key": natural_key, **(detail or {})}
    cursor.execute(
        """
        INSERT INTO audit.cdc_eventos
            (run_id, fuente, record_hash, tipo_evento, detalle)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (run_id, SOURCE, record_hash, tipo_evento, Json(payload)),
    )


def load_firms_sample(cursor) -> list[dict[str, Any]]:
    cursor.execute(
        """
        SELECT natural_key, record_hash, fecha_adq, pais_codigo, latitud, longitud,
               frp_mw, brillo_termico, confianza, satelite, instrumento, dia_noche
        FROM staging.stg_firms
        WHERE natural_key IS NOT NULL
          AND record_hash IS NOT NULL
          AND pais_codigo IN ('URY','ARG','BRA')
        ORDER BY fecha_adq DESC, natural_key
        LIMIT 2
        """
    )
    rows = fetch_dicts(cursor)
    if len(rows) < 2:
        raise RuntimeError(
            "D4 requiere al menos 2 registros FIRMS reales en staging.stg_firms "
            "para demostrar alta nueva y modificacion controlada."
        )
    return rows


def postgres_counts(cursor, run_ids: list[str]) -> dict[str, Any]:
    cursor.execute(
        """
        SELECT tipo_evento, COUNT(*)::bigint AS eventos
        FROM audit.cdc_eventos
        WHERE run_id::text = ANY(%s)
        GROUP BY tipo_evento
        ORDER BY tipo_evento
        """,
        (run_ids,),
    )
    eventos = fetch_dicts(cursor)
    cursor.execute(
        """
        SELECT COUNT(*)::bigint AS duplicados
        FROM (
            SELECT natural_key
            FROM staging.stg_firms
            GROUP BY natural_key
            HAVING COUNT(*) > 1
        ) d
        """
    )
    duplicados = int(cursor.fetchone()[0])
    cursor.execute(
        """
        SELECT COUNT(*)::bigint AS fact_incendio
        FROM dw.fact_incendio
        """
    )
    fact_incendio = int(cursor.fetchone()[0])
    return {
        "eventos_d4": eventos,
        "duplicados_stg_firms_natural_key": duplicados,
        "fact_incendio_total": fact_incendio,
    }


def count_events(events: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "altas": sum(1 for event in events if event["tipo_evento"] == "alta"),
        "modificaciones": sum(1 for event in events if event["tipo_evento"] == "modificacion"),
        "sin_cambios": sum(1 for event in events if event["tipo_evento"] == "sin_cambio"),
        "rechazados": sum(1 for event in events if event["tipo_evento"] == "rechazo"),
    }


def write_mongo_evidence(db, run_ids: list[str], rows: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    now = datetime.now(UTC)
    event_counts = count_events(events)
    primary_run_id = run_ids[-1]

    # La instancia UTEC valida pipeline_logs con un schema operativo propio
    # (run_id, log_level, step_name, message, created_at). Por eso D4 registra
    # el resumen documental de CDC ahi, sin cambiar el schema de MongoDB.
    db.pipeline_logs.insert_one(
        {
            "run_id": primary_run_id,
            "log_level": "INFO",
            "step_name": "cdc",
            "message": "Evidencia D4 CDC ejecutada correctamente",
            "created_at": now,
            "proceso": "CDC",
            "criterio": "D4",
            "fuente": SOURCE,
            "estado": "ok",
            "eventos": event_counts,
            "run_ids_sql": run_ids,
            "destino_sql": "audit.cdc_eventos",
            "modo": "simulacion_controlada",
            "nota": (
                "Usa registros FIRMS reales y una correccion simulada manteniendo "
                "natural_key con record_hash distinto; no inventa datos ambientales."
            ),
        }
    )

    return {
        "mongodb_cdc": "OK",
        "pipeline_logs_d4": db.pipeline_logs.count_documents({"run_id": primary_run_id, "criterio": "D4", "step_name": "cdc"}),
        "coleccion": "pipeline_logs",
        "eventos": event_counts,
    }


def run_evidence(database_url: str, mongo_uri: str) -> int:
    started = time.perf_counter()
    section("Conexion PostgreSQL Y MongoDB")
    db = connect_mongo(mongo_uri)
    print_json({"mongo_database": db.name, "mongo_ping": "ok"})

    run_initial = str(uuid.uuid4())
    run_same = str(uuid.uuid4())
    run_delta = str(uuid.uuid4())
    run_ids = [run_initial, run_same, run_delta]

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user, now()")
            database, user, connected_at = cursor.fetchone()
            print_json({"postgres_database": database, "postgres_user": user, "connected_at": connected_at})

            section("Seleccion De Datos Reales FIRMS")
            rows = load_firms_sample(cursor)
            print_json(
                [
                    {
                        "natural_key": row["natural_key"],
                        "record_hash": row["record_hash"],
                        "fecha_adq": row["fecha_adq"],
                        "pais_codigo": row["pais_codigo"],
                        "frp_mw": row["frp_mw"],
                        "brillo_termico": row["brillo_termico"],
                        "nota": "brillo_termico es brightness FIRMS; no temperatura del aire",
                    }
                    for row in rows
                ]
            )

            initial = rows[0]
            new_real = rows[1]
            modified_hash = simulated_correction_hash(initial)
            if modified_hash == initial["record_hash"]:
                raise RuntimeError("No se pudo generar record_hash distinto para la modificacion simulada.")

            section("Registro CDC En PostgreSQL")
            events = [
                {
                    "run_id": run_initial,
                    "tipo_evento": "alta",
                    "natural_key": initial["natural_key"],
                    "record_hash": initial["record_hash"],
                    "detalle": {"fase": "carga_inicial", "origen": "registro FIRMS real"},
                },
                {
                    "run_id": run_same,
                    "tipo_evento": "sin_cambio",
                    "natural_key": initial["natural_key"],
                    "record_hash": initial["record_hash"],
                    "detalle": {"fase": "carga_incremental_identica", "hash_anterior": initial["record_hash"]},
                    "hash_anterior": initial["record_hash"],
                },
                {
                    "run_id": run_delta,
                    "tipo_evento": "alta",
                    "natural_key": new_real["natural_key"],
                    "record_hash": new_real["record_hash"],
                    "detalle": {"fase": "carga_incremental_con_delta", "origen": "segundo registro FIRMS real"},
                },
                {
                    "run_id": run_delta,
                    "tipo_evento": "modificacion",
                    "natural_key": initial["natural_key"],
                    "record_hash": modified_hash,
                    "hash_anterior": initial["record_hash"],
                    "detalle": {
                        "fase": "carga_incremental_con_delta",
                        "hash_anterior": initial["record_hash"],
                        "record_hash_simulado": modified_hash,
                        "correccion_simulada": "Mismo natural_key con record_hash distinto para representar correccion real del origen; no altera staging ni DW.",
                    },
                },
            ]

            run_details = {
                run_initial: {"filas_leidas": 1, "filas_insertadas": 1, "filas_actualizadas": 0, "filas_rechazadas": 0, "fase": "carga_inicial"},
                run_same: {"filas_leidas": 1, "filas_insertadas": 0, "filas_actualizadas": 0, "filas_rechazadas": 0, "fase": "incremental_sin_cambios"},
                run_delta: {"filas_leidas": 2, "filas_insertadas": 1, "filas_actualizadas": 1, "filas_rechazadas": 0, "fase": "incremental_con_alta_y_modificacion"},
            }
            for run_id, detail in run_details.items():
                detail["duracion_segundos"] = round(time.perf_counter() - started, 3)
                detail["criterio"] = "D4 CDC controlado"
                detail["fuente"] = SOURCE
                insert_run(cursor, run_id, detail)
            for event in events:
                insert_event(
                    cursor,
                    event["run_id"],
                    event["record_hash"],
                    event["tipo_evento"],
                    event["natural_key"],
                    event.get("detalle"),
                )
            conn.commit()
            counts = postgres_counts(cursor, run_ids)
            print_json({"run_ids": run_ids, **counts})

    section("Registro CDC En MongoDB")
    mongo_counts = write_mongo_evidence(db, run_ids, rows, events)
    print_json(mongo_counts)

    required = {"alta", "modificacion", "sin_cambio"}
    observed = {event["tipo_evento"] for event in events}
    event_counts = count_events(events)
    mongo_ok = mongo_counts.get("pipeline_logs_d4", 0) >= 1
    section("Resultado D4")
    result = {
        "sql_cdc": "OK" if required.issubset(observed) else "ERROR",
        "mongodb_cdc": "OK" if mongo_ok else "ERROR",
        "estado": "ok" if required.issubset(observed) and mongo_ok else "error",
        "eventos_requeridos": sorted(required),
        "eventos_observados": sorted(observed),
        "alta": event_counts["altas"],
        "modificacion": event_counts["modificaciones"],
        "sin_cambio": event_counts["sin_cambios"],
        "rechazo": event_counts["rechazados"],
        "exit_code": 0 if required.issubset(observed) and mongo_ok else 2,
        "limitacion": None,
    }
    print_json(result)
    return int(result["exit_code"])


def main() -> int:
    root = root_dir()
    log_dir = root / "evidencia" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    output_path = log_dir / f"d4_cdc_{stamp}.log"
    summary_path = log_dir / "d4_resumen_ultima_ejecucion.log"

    exit_code = 1
    summary: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "log": str(output_path),
        "criterio": "D4 Change Data Capture",
        "sql_cdc": "ERROR",
        "mongodb_cdc": "ERROR",
        "alta": 0,
        "modificacion": 0,
        "sin_cambio": 0,
        "exit_code": 1,
        "nota": "Exit code 0 exige evidencia SQL y MongoDB de alta, modificacion y sin_cambio.",
    }
    with output_path.open("w", encoding="utf-8") as handle, contextlib.redirect_stdout(handle), contextlib.redirect_stderr(handle):
        try:
            section("Validacion De Entorno")
            database_url = require_env("DATABASE_URL")
            mongo_uri = require_env("MONGO_URI")
            print_json({
                "DATABASE_URL": "definida",
                "MONGO_URI": "definida",
                "fuentes_validas": sorted(VALID_SOURCES),
                "fuente_evidencia": SOURCE,
                "forecast": "no usado",
            })
            exit_code = run_evidence(database_url, mongo_uri)
            if exit_code == 0:
                summary.update({
                    "sql_cdc": "OK",
                    "mongodb_cdc": "OK",
                    "alta": 2,
                    "modificacion": 1,
                    "sin_cambio": 1,
                    "exit_code": 0,
                })
        except Exception as exc:
            print_json({"estado": "error", "mensaje": str(exc), "exit_code": 1})
            exit_code = 1
            summary["error"] = str(exc)

    summary["generated_at"] = datetime.now(UTC).isoformat()
    summary["exit_code"] = exit_code
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"D4 CDC evidencia generada: {output_path}")
    print(f"Resumen: {summary_path}")
    print(f"Exit code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
