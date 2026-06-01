#!/usr/bin/env python3
"""Valida evidencia CDC D4 en MongoDB para el criterio D5."""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from pymongo import MongoClient
except ImportError as exc:  # pragma: no cover
    raise SystemExit("ERROR: pymongo no esta instalado.") from exc


def root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=json_default))


def redact(document: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(document)
    for key in ("password", "token", "secret", "api_key", "apikey"):
        if key in redacted:
            redacted[key] = "[REDACTADO]"
    redacted.pop("_id", None)
    return redacted


def connect(uri: str):
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db_name = os.getenv("MONGO_DB", "")
    if db_name:
        return client[db_name]
    try:
        return client.get_default_database()
    except Exception:
        return client["proyecto_lidia"]


def validate(mongo_uri: str, output_path: Path | None = None) -> int:
    db = connect(mongo_uri)
    docs = list(
        db.pipeline_logs.find(
            {"proceso": "CDC", "criterio": "D4", "fuente": "FIRMS"},
            {"_id": 0},
        )
        .sort([("created_at", -1), ("registrado_en", -1)])
        .limit(10)
    )
    latest = docs[0] if docs else {}
    eventos = latest.get("eventos", {}) if latest else {}
    result = {
        "mongo_database": db.name,
        "pipeline_logs_exists": "pipeline_logs" in db.list_collection_names(),
        "d4_cdc_documents": len(docs),
        "eventos": eventos,
        "cdc_ok": bool(docs)
        and eventos.get("altas", 0) >= 1
        and eventos.get("modificaciones", 0) >= 1
        and eventos.get("sin_cambios", 0) >= 1,
        "ultimos_documentos": [redact(doc) for doc in docs[:3]],
    }
    text = json.dumps(result, indent=2, ensure_ascii=False, default=json_default)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["cdc_ok"] else 1


def main() -> int:
    mongo_uri = os.getenv("MONGO_URI", "").strip()
    if not mongo_uri:
        print_json({"estado": "error", "mensaje": "Debe definir MONGO_URI."})
        return 1
    output = root_dir() / "evidencia" / "logs" / "d5_mongo_cdc_ultima_validacion.log"
    try:
        return validate(mongo_uri, output)
    except Exception as exc:
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "estado": "error",
            "mensaje": str(exc),
            "generated_at": datetime.now(UTC).isoformat(),
        }
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print_json(payload)
        return 1


if __name__ == "__main__":
    sys.exit(main())
