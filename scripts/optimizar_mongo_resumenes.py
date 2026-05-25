from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
PAISES_ALCANCE = ["CHL", "URY", "BRA", "ARG"]


def main() -> int:
    env_path = ROOT / "config" / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    from pymongo import MongoClient, ASCENDING

    mongo_uri = os.getenv("MONGO_URI")
    if mongo_uri:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    else:
        user = os.getenv("MONGO_USER", "")
        password = os.getenv("MONGO_PASSWORD", "")
        host = os.getenv("MONGO_HOST", "localhost")
        port = int(os.getenv("MONGO_PORT", "27017"))
        database = os.getenv("MONGO_DATABASE", "sinia_uy")
        auth_source = os.getenv("MONGO_AUTH_SOURCE", database)
        uri = (
            f"mongodb://{user}:{password}@{host}:{port}/{database}?authSource={auth_source}"
            if user and password
            else f"mongodb://{host}:{port}/"
        )
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[os.getenv("MONGO_DATABASE", "sinia_uy")]

    pais_pipeline = [
        {"$unwind": "$focos"},
        {"$match": {"focos.pais": {"$in": PAISES_ALCANCE}}},
        {
            "$group": {
                "_id": "$focos.pais",
                "total_focos": {"$sum": 1},
                "frp_promedio": {"$avg": "$focos.potencia_radiativa"},
                "frp_maximo": {"$max": "$focos.potencia_radiativa"},
                "focos_alta_confianza": {
                    "$sum": {"$cond": [{"$eq": ["$focos.confianza_num", 3]}, 1, 0]}
                },
            }
        },
        {"$project": {"_id": 0, "pais": "$_id", "total_focos": 1, "frp_promedio": 1, "frp_maximo": 1, "focos_alta_confianza": 1}},
        {"$sort": {"pais": 1}},
    ]

    mes_pipeline = [
        {"$unwind": "$focos"},
        {"$match": {"focos.pais": {"$in": PAISES_ALCANCE}}},
        {
            "$group": {
                "_id": {
                    "pais": "$focos.pais",
                    "mes": {"$dateToString": {"format": "%Y-%m", "date": "$fecha"}},
                },
                "total_focos": {"$sum": 1},
                "frp_promedio": {"$avg": "$focos.potencia_radiativa"},
                "frp_maximo": {"$max": "$focos.potencia_radiativa"},
            }
        },
        {"$project": {"_id": 0, "pais": "$_id.pais", "mes": "$_id.mes", "total_focos": 1, "frp_promedio": 1, "frp_maximo": 1}},
        {"$sort": {"pais": 1, "mes": 1}},
    ]

    pais_docs = list(db.focos_snapshots.aggregate(pais_pipeline, allowDiskUse=True))
    mes_docs = list(db.focos_snapshots.aggregate(mes_pipeline, allowDiskUse=True))

    db.focos_resumen_pais.drop()
    db.focos_resumen_mes.drop()
    if pais_docs:
        db.focos_resumen_pais.insert_many(pais_docs)
    if mes_docs:
        db.focos_resumen_mes.insert_many(mes_docs)
    db.focos_resumen_pais.create_index([("pais", ASCENDING)], unique=True)
    db.focos_resumen_mes.create_index([("pais", ASCENDING), ("mes", ASCENDING)], unique=True)

    report = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "colecciones_materializadas": {
            "focos_resumen_pais": db.focos_resumen_pais.count_documents({}),
            "focos_resumen_mes": db.focos_resumen_mes.count_documents({}),
        },
        "alcance": PAISES_ALCANCE,
    }
    REPORTS.mkdir(exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    (REPORTS / f"mongo_resumenes_{stamp}.json").write_text(text, encoding="utf-8")
    (REPORTS / "mongo_resumenes_ultimo.json").write_text(text, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
