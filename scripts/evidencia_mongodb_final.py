"""Genera evidencia final de MongoDB como capa documental complementaria."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import MONGO_CONFIG  # noqa: E402

LOG_PATH = ROOT / "evidencia" / "logs" / "mongodb_evidencia_final.log"
EXPECTED = ("ingesta_metadata", "rechazos_etl", "pipeline_logs", "snapshots_firms", "raw_payloads")
SENSITIVE = ("password", "token", "secret", "key", "uri")


def mongo_uri() -> str:
    auth = ""
    if MONGO_CONFIG["user"] and MONGO_CONFIG["password"]:
        auth = f"{MONGO_CONFIG['user']}:{MONGO_CONFIG['password']}@"
    return f"mongodb://{auth}{MONGO_CONFIG['host']}:{MONGO_CONFIG['port']}/?authSource={MONGO_CONFIG['auth_source']}"


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("***OCULTO***" if any(s in k.lower() for s in SENSITIVE) else sanitize(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value[:5]]
    return value


def emit(lines: list[str], message: str, **payload: object) -> None:
    event = {"timestamp": datetime.now(timezone.utc).isoformat(), "message": message, **payload}
    text = json.dumps(event, ensure_ascii=False, default=str)
    print(text, flush=True)
    lines.append(text)


def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    emit(lines, "inicio_mongodb_evidencia", database=MONGO_CONFIG["database"], colecciones_esperadas=list(EXPECTED))
    try:
        client = MongoClient(mongo_uri(), serverSelectionTimeoutMS=5000, maxPoolSize=5)
        client.admin.command("ping")
        db = client[MONGO_CONFIG["database"]]
        collections = sorted(db.list_collection_names())
        emit(lines, "colecciones_existentes", colecciones=collections)
        for name in collections:
            count = db[name].count_documents({})
            sample = db[name].find_one({})
            emit(lines, "coleccion", nombre=name, documentos=count, ejemplo=sanitize(sample) if sample else None)
        for name in EXPECTED:
            if name not in collections:
                emit(lines, "coleccion_esperada_faltante", nombre=name)
        if "ingesta_metadata" in collections:
            rows = list(db.ingesta_metadata.aggregate([
                {"$group": {"_id": {"fuente": "$fuente", "estado": "$estado"}, "total": {"$sum": 1}}},
                {"$sort": {"_id.fuente": 1, "_id.estado": 1}},
            ]))
            emit(lines, "consulta_ingestas_por_fuente_estado", resultado=sanitize(rows))
        if "rechazos_etl" in collections:
            rows = list(db.rechazos_etl.aggregate([
                {"$group": {"_id": {"fuente": "$fuente", "motivo": "$motivo"}, "total": {"$sum": 1}}},
                {"$sort": {"total": -1}},
                {"$limit": 20},
            ]))
            emit(lines, "consulta_rechazos_por_fuente_motivo", resultado=sanitize(rows))
        if "pipeline_logs" in collections:
            rows = list(db.pipeline_logs.aggregate([
                {"$group": {"_id": {"fuente": "$fuente", "estado": "$estado"}, "total": {"$sum": 1}}},
                {"$sort": {"total": -1}},
                {"$limit": 20},
            ]))
            emit(lines, "consulta_pipeline_logs", resultado=sanitize(rows))
        if "snapshots_firms" in collections:
            rows = list(db.snapshots_firms.find({}, {"_id": 0}).sort("fecha", -1).limit(5))
            emit(lines, "consulta_snapshots_firms_recientes", resultado=sanitize(rows))
    except Exception as exc:  # noqa: BLE001
        emit(lines, "error_mongodb_evidencia", error=f"{type(exc).__name__}: {exc}")
        LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return 1
    emit(lines, "fin_mongodb_evidencia", estado="OK")
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
