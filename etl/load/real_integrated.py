"""Orquestacion de carga real integrada para Proyecto LIDIA EC3."""

from __future__ import annotations

import importlib
import json
import time
import uuid
from io import StringIO

import pandas as pd
from psycopg2 import sql
from psycopg2.extras import Json

from config.settings import SOURCE_FILES
from etl.load.postgres import (
    TABLES,
    _latest_date,
    _promote,
    associate_environmental_dimensions,
    connect,
    load_staging,
)
from etl.load.real_firms_chirps import load_real_chirps, load_real_firms
from etl.transform.normalize import normalize


def _bulk_load(source: str, frame: pd.DataFrame, promote: bool = True) -> dict:
    """Carga un frame real voluminoso; la base inicial limpia implica altas."""
    accepted, rejected = normalize(source, frame)
    table, columns = TABLES[source]
    run_id = str(uuid.uuid4())
    start = time.perf_counter()
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO audit.etl_runs (run_id, fuente, etapa, estado) VALUES (%s,%s,'load','iniciado')",
            (run_id, source),
        )
        for row in rejected:
            cur.execute(
                "INSERT INTO staging.rechazos_etl (run_id, fuente, motivo, registro) VALUES (%s,%s,%s,%s)",
                (run_id, source, row["motivo"], Json(row["registro"])),
            )
        output_frame = pd.DataFrame(accepted)
        if output_frame.empty:
            inserted = 0
        else:
            output_frame["raw_payload"] = output_frame["raw_payload"].map(
                lambda value: json.dumps(value, default=str, ensure_ascii=True)
            )
            output = StringIO()
            output_frame[columns].to_csv(output, index=False, header=False, na_rep="")
            output.seek(0)
            cur.execute(
                sql.SQL("CREATE TEMP TABLE tmp_real_load (LIKE staging.{} INCLUDING DEFAULTS) ON COMMIT DROP").format(
                    sql.Identifier(table)
                )
            )
            cur.copy_expert(
                sql.SQL("COPY tmp_real_load ({}) FROM STDIN WITH (FORMAT CSV, NULL '')").format(
                    sql.SQL(",").join(map(sql.Identifier, columns))
                ).as_string(conn),
                output,
            )
            cur.execute(
                sql.SQL("INSERT INTO staging.{} ({}) SELECT {} FROM tmp_real_load ON CONFLICT (natural_key) DO NOTHING").format(
                    sql.Identifier(table),
                    sql.SQL(",").join(map(sql.Identifier, columns)),
                    sql.SQL(",").join(map(sql.Identifier, columns)),
                )
            )
            inserted = cur.rowcount
        if promote:
            _promote(cur, source)
        cur.execute(
            """INSERT INTO audit.cdc_eventos (run_id, fuente, record_hash, tipo_evento, detalle)
               VALUES (%s,%s,%s,'alta',%s)""",
            (run_id, source, "0" * 64, Json({"cantidad": inserted, "modo": "carga_real_integrada"})),
        )
        cur.execute(
            """UPDATE audit.etl_runs SET estado='ok', ultima_fecha_procesada=%s,
               filas_leidas=%s, filas_insertadas=%s, filas_actualizadas=0,
               filas_rechazadas=%s, duracion_segundos=%s, finalizado_en=NOW()
               WHERE run_id=%s""",
            (
                _latest_date(accepted),
                len(frame),
                inserted,
                len(rejected),
                round(time.perf_counter() - start, 3),
                run_id,
            ),
        )
    return {
        "fuente": source, "leidas": len(frame), "insertadas": inserted,
        "rechazadas": len(rejected), "run_id": run_id,
    }


def _load_bulk_chunks(source: str, frames, chunksize: int = 25_000) -> dict:
    """Carga observaciones horarias en lotes y promueve una vez al finalizar."""
    totals = {"fuente": source, "leidas": 0, "insertadas": 0, "rechazadas": 0, "run_ids": []}
    for frame in frames:
        for offset in range(0, len(frame), chunksize):
            result = _bulk_load(source, frame.iloc[offset : offset + chunksize], promote=False)
            for key in ("leidas", "insertadas", "rechazadas"):
                totals[key] += result[key]
            totals["run_ids"].append(result["run_id"])
    with connect() as conn, conn.cursor() as cur:
        _promote(cur, source)
    return totals


def _extract_and_load(source: str, bulk: bool = False) -> dict:
    module = importlib.import_module(f"etl.extract.extract_{source.lower()}")
    started = time.perf_counter()
    try:
        if bulk and source == "METEO":
            result = _load_bulk_chunks(source, module.extract_batches())
        else:
            frame = module.extract()
            result = _load_bulk_chunks(source, [frame]) if bulk else _load_regular(source, frame)
        result["extraccion_segundos"] = round(time.perf_counter() - started, 3)
        result["estado"] = "cargado"
        return result
    except Exception as exc:
        return {
            "fuente": source, "estado": "pendiente_error_concreto",
            "error": f"{type(exc).__name__}: {exc}",
        }


def _load_regular(source: str, frame: pd.DataFrame) -> dict:
    accepted, rejected = normalize(source, frame)
    result = load_staging(source, accepted, rejected)
    return {
        "fuente": source, "leidas": len(frame), "insertadas": result["insertadas"],
        "actualizadas": result["actualizadas"], "rechazadas": result["rechazadas"],
        "run_id": result["run_id"],
    }


def run_integrated() -> list[dict]:
    results = [load_real_firms(), load_real_chirps()]
    results.append(_extract_and_load("METEO", bulk=True))
    results.append(_extract_and_load("FORECAST", bulk=True))
    results.append(_extract_and_load("MODIS"))
    results.append(_extract_and_load("INUMET", bulk=True))
    results.append({"asociacion_espacial": associate_environmental_dimensions()})
    return results


if __name__ == "__main__":
    print("CARGA_REAL_INTEGRADA=" + json.dumps(run_integrated(), ensure_ascii=True, sort_keys=True))
