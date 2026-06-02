#!/usr/bin/env python3
"""Genera evidencia D2 NoSQL para Proyecto LIDIA usando MongoDB.

Uso:
    MONGO_URI definida en el entorno python scripts/d2_generar_evidencia_nosql.py

El script es de solo lectura: no inserta, actualiza ni elimina documentos.
"""

from __future__ import annotations

import json
import os
import re
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from pymongo import MongoClient
except ImportError as exc:  # pragma: no cover - depende del entorno Jupyter.
    raise SystemExit(
        "ERROR: pymongo no esta instalado. Instalarlo o usar el entorno del proyecto."
    ) from exc


EXPECTED_COLLECTIONS = [
    "ingesta_metadata",
    "rechazos_etl",
    "raw_payloads",
    "pipeline_logs",
    "snapshots_firms",
]

REQUIRED_FIELDS = {
    "ingesta_metadata": ["run_id", "fuente", "estado", "metricas", "registrado_en"],
    "rechazos_etl": ["run_id", "fuente", "motivo", "registro", "registrado_en"],
    "raw_payloads": ["run_id", "fuente", "payload", "registrado_en"],
    "pipeline_logs": ["run_id", "fuente", "estado", "mensaje", "registrado_en"],
    "snapshots_firms": ["fecha", "pais_codigo", "total_focos", "resumen"],
}

SENSITIVE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        "password",
        "passwd",
        "token",
        "secret",
        r"api[_-]?key",
        "authorization",
        "credential",
    )
]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=json_default))


def section(title: str) -> None:
    print(f"\n## {title}")


def sanitize_value(key: str, value: Any, depth: int = 0) -> Any:
    if any(pattern.search(str(key)) for pattern in SENSITIVE_PATTERNS):
        return "[REDACTED]"
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        if depth >= 3:
            return f"[Array({len(value)})]"
        return [sanitize_value(key, item, depth + 1) for item in value[:10]]
    if isinstance(value, dict):
        if depth >= 3:
            return "[Object]"
        return {
            child_key: sanitize_value(child_key, child_value, depth + 1)
            for child_key, child_value in list(value.items())[:30]
        }
    return value


def collection_count(db, collection: str) -> int:
    return db[collection].count_documents({})


def missing_required_count(db, collection: str, fields: list[str]) -> int:
    if not fields:
        return 0
    return db[collection].count_documents({"$or": [{field: {"$exists": False}} for field in fields]})


def field_exists_count(db, collection: str, field: str) -> int:
    return db[collection].count_documents({field: {"$exists": True, "$ne": None}})


def run_validation(mongo_uri: str) -> dict[str, Path]:
    root = project_root()
    log_dir = root / "evidencia" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    run_ts = timestamp()
    connection_log = log_dir / f"d2_mongodb_conexion_{run_ts}.log"
    validation_log = log_dir / f"d2_validacion_mongodb_{run_ts}.log"
    summary_log = log_dir / "d2_resumen_ultima_ejecucion.log"

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)

    with connection_log.open("w", encoding="utf-8") as handle, redirect_stdout(handle), redirect_stderr(handle):
        section("Conexion")
        ping = client.admin.command("ping")
        db = client.get_default_database()
        if db is None:
            raise RuntimeError("MONGO_URI debe incluir nombre de base de datos.")
        print_json({
            "database": db.name,
            "ping": ping,
            "timestamp": datetime.now(UTC).isoformat(),
            "rol_mongodb": "Complementario documental; PostgreSQL sigue siendo el Data Warehouse principal",
        })

    db = client.get_default_database()
    existing = sorted(db.list_collection_names())

    with validation_log.open("w", encoding="utf-8") as handle, redirect_stdout(handle), redirect_stderr(handle):
        section("Colecciones Esperadas")
        print_json([
            {"collection": name, "exists": name in existing}
            for name in EXPECTED_COLLECTIONS
        ])

        section("Conteos Por Coleccion")
        counts = []
        for name in EXPECTED_COLLECTIONS:
            if name not in existing:
                counts.append({"collection": name, "count": None, "limitation": "Coleccion no existe"})
                continue
            count = collection_count(db, name)
            counts.append({
                "collection": name,
                "count": count,
                "limitation": "Coleccion existente sin documentos; no se inventan datos" if count == 0 else "",
            })
        print_json(counts)

        section("Muestra De Documentos Sanitizada")
        for name in EXPECTED_COLLECTIONS:
            print(f"\n### {name}")
            if name not in existing:
                print_json({"collection": name, "exists": False, "sample": []})
                continue
            sample = [sanitize_value("document", doc) for doc in db[name].find({}).limit(3)]
            print_json({"collection": name, "sample_count": len(sample), "sample": sample})

        section("Agrupacion Ingestas Por Fuente Y Estado")
        if "ingesta_metadata" in existing:
            print_json(list(db.ingesta_metadata.aggregate([
                {"$group": {"_id": {"fuente": "$fuente", "estado": "$estado"}, "documentos": {"$sum": 1}}},
                {"$sort": {"_id.fuente": 1, "_id.estado": 1}},
            ])))
        else:
            print_json({"limitation": "ingesta_metadata no existe"})

        section("Agrupacion Rechazos Por Fuente Y Motivo")
        if "rechazos_etl" in existing:
            print_json(list(db.rechazos_etl.aggregate([
                {"$group": {"_id": {"fuente": "$fuente", "motivo": "$motivo"}, "documentos": {"$sum": 1}}},
                {"$sort": {"documentos": -1, "_id.fuente": 1}},
            ])))
        else:
            print_json({"limitation": "rechazos_etl no existe"})

        section("Agrupacion Logs Por Etapa Y Severidad")
        if "pipeline_logs" in existing:
            print_json(list(db.pipeline_logs.aggregate([
                {
                    "$group": {
                        "_id": {
                            "etapa": {"$ifNull": ["$etapa", "sin_etapa"]},
                            "severidad": {"$ifNull": ["$severidad", "$estado"]},
                        },
                        "documentos": {"$sum": 1},
                    }
                },
                {"$sort": {"_id.etapa": 1, "_id.severidad": 1}},
            ])))
        else:
            print_json({"limitation": "pipeline_logs no existe"})

        section("Snapshots FIRMS Por Periodo Y Pais")
        if "snapshots_firms" in existing:
            print_json(list(db.snapshots_firms.aggregate([
                {
                    "$group": {
                        "_id": {"pais_codigo": "$pais_codigo", "anio": {"$year": "$fecha"}},
                        "snapshots": {"$sum": 1},
                        "total_focos": {"$sum": "$total_focos"},
                        "primera_fecha": {"$min": "$fecha"},
                        "ultima_fecha": {"$max": "$fecha"},
                    }
                },
                {"$sort": {"_id.anio": 1, "_id.pais_codigo": 1}},
            ])))
        else:
            print_json({"limitation": "snapshots_firms no existe"})

        section("Validacion De Campos Minimos")
        print_json([
            {
                "collection": name,
                "exists": name in existing,
                "required_fields": REQUIRED_FIELDS[name],
                "documents_missing_required_fields": missing_required_count(db, name, REQUIRED_FIELDS[name])
                if name in existing else None,
            }
            for name in EXPECTED_COLLECTIONS
        ])

        section("Validacion De Timestamps O Fecha De Ejecucion")
        timestamp_rows = []
        for name in ("ingesta_metadata", "rechazos_etl", "raw_payloads", "pipeline_logs"):
            timestamp_rows.append({
                "collection": name,
                "documents_with_timestamp": field_exists_count(db, name, "registrado_en") if name in existing else None,
            })
        timestamp_rows.append({
            "collection": "snapshots_firms",
            "documents_with_fecha": field_exists_count(db, "snapshots_firms", "fecha") if "snapshots_firms" in existing else None,
        })
        print_json(timestamp_rows)

        section("Limitaciones Detectadas")
        limitations = [
            {"collection": item["collection"], "limitation": item["limitation"]}
            for item in counts if item["limitation"]
        ]
        print_json(limitations or [{"estado": "Sin limitaciones de existencia/conteo detectadas"}])

        section("Fin D2")

    summary_log.write_text(
        "\n".join([
            "D2 ultima ejecucion",
            f"Fecha UTC: {run_ts}",
            f"Conexion log: {connection_log}",
            f"Validacion log: {validation_log}",
            "Nota: MongoDB se valida como capa documental complementaria; PostgreSQL conserva el Data Warehouse principal.",
            "",
        ]),
        encoding="utf-8",
    )
    client.close()
    return {
        "connection_log": connection_log,
        "validation_log": validation_log,
        "summary_log": summary_log,
    }


def main() -> int:
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("ERROR: MONGO_URI no esta definida.", file=sys.stderr)
        print(
            "Definir MONGO_URI como variable de entorno antes de ejecutar.",
            file=sys.stderr,
        )
        return 1
    paths = run_validation(mongo_uri)
    print("D2 NoSQL evidencia generada:")
    for name, path in paths.items():
        print(f"- {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
