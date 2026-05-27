from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient

from config.settings import MONGO_CONFIG


def database():
    auth = ""
    if MONGO_CONFIG["user"] and MONGO_CONFIG["password"]:
        auth = f"{MONGO_CONFIG['user']}:{MONGO_CONFIG['password']}@"
    uri = f"mongodb://{auth}{MONGO_CONFIG['host']}:{MONGO_CONFIG['port']}/?authSource={MONGO_CONFIG['auth_source']}"
    return MongoClient(uri, serverSelectionTimeoutMS=5000)[MONGO_CONFIG["database"]]


def configure_collections() -> None:
    db = database()
    spec_path = Path(__file__).resolve().parents[2] / "nosql" / "mongo_schema.json"
    specs = json.loads(spec_path.read_text(encoding="utf-8"))["collections"]
    existing = set(db.list_collection_names())
    for name, validator in specs.items():
        if name not in existing:
            db.create_collection(name, validator=validator)
        else:
            db.command("collMod", name, validator=validator)
    db.ingesta_metadata.create_index([("fuente", 1), ("registrado_en", -1)])
    db.rechazos_etl.create_index([("run_id", 1), ("fuente", 1)])
    db.raw_payloads.create_index([("run_id", 1), ("fuente", 1)])
    db.pipeline_logs.create_index([("run_id", 1), ("registrado_en", -1)])
    db.snapshots_firms.create_index([("fecha", -1), ("pais_codigo", 1)], unique=True)


def save_run(source: str, result: dict) -> None:
    database().ingesta_metadata.replace_one(
        {"run_id": result["run_id"]},
        {"run_id": result["run_id"], "fuente": source, "estado": "ok",
         "metricas": result, "registrado_en": datetime.now(timezone.utc)},
        upsert=True,
    )


def save_trace(source: str, result: dict, accepted: list[dict], rejected: list[dict]) -> None:
    """Persiste trazabilidad documental; nunca reemplaza hechos del DW."""
    now = datetime.now(timezone.utc)
    db = database()
    save_run(source, result)
    if accepted:
        db.raw_payloads.insert_many([
            {"run_id": result["run_id"], "fuente": source, "payload": row["raw_payload"], "registrado_en": now}
            for row in accepted
        ])
    if rejected:
        db.rechazos_etl.insert_many([
            {"run_id": result["run_id"], "fuente": source, "motivo": row["motivo"],
             "registro": row["registro"], "registrado_en": now}
            for row in rejected
        ])
    db.pipeline_logs.insert_one(
        {"run_id": result["run_id"], "fuente": source, "estado": "ok",
         "mensaje": "Carga ETL registrada en PostgreSQL", "registrado_en": now}
    )
