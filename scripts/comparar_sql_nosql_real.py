from __future__ import annotations

import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"


def _load_env() -> None:
    env_path = ROOT / "config" / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def _timed(fn: Callable[[], Any], repeticiones: int = 3) -> dict[str, Any]:
    tiempos: list[float] = []
    resultado: Any = None
    for _ in range(repeticiones):
        start = time.perf_counter()
        resultado = fn()
        tiempos.append((time.perf_counter() - start) * 1000)
    return {
        "ms_min": round(min(tiempos), 3),
        "ms_promedio": round(statistics.mean(tiempos), 3),
        "ms_max": round(max(tiempos), 3),
        "repeticiones": repeticiones,
        "resultado": resultado,
    }


def _pg_connect():
    import psycopg2

    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
        dbname=os.getenv("PG_DATABASE", "sinia_uy"),
        user=os.getenv("PG_USER", "sinia_etl_user"),
        password=os.getenv("PG_PASSWORD", ""),
        connect_timeout=5,
    )


def medir_postgres() -> dict[str, Any]:
    conn = _pg_connect()

    def query(sql: str) -> list[tuple[Any, ...]]:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()

    metricas = {
        "focos_por_pais": _timed(
            lambda: {pais: int(total) for pais, total in query(
                """
                SELECT pais, total_focos
                FROM mv_focos_por_pais
                ORDER BY pais
                """
            )}
        ),
        "focos_por_mes": _timed(
            lambda: len(query(
                """
                SELECT pais, mes, total_focos
                FROM mv_focos_por_pais_mes
                ORDER BY pais, mes
                """
            ))
        ),
        "ejecuciones_etl": _timed(
            lambda: int(query("SELECT COUNT(*) FROM etl_ejecuciones")[0][0])
        ),
        "riesgo_por_pais": _timed(
            lambda: {pais: float(valor) for pais, valor in query(
                """
                SELECT p.pais, AVG(m.indice_riesgo)::float
                FROM meteo_diario m
                JOIN puntos_monitoreo p ON p.id = m.id_punto
                WHERE p.pais IN ('URY','BRA','ARG')
                GROUP BY p.pais
                ORDER BY p.pais
                """
            )}
        ),
    }
    conn.close()
    return metricas


def medir_mongo() -> dict[str, Any]:
    from pymongo import MongoClient

    client = MongoClient(
        f"mongodb://{os.getenv('MONGO_HOST', 'localhost')}:{int(os.getenv('MONGO_PORT', '27017'))}/",
        serverSelectionTimeoutMS=5000,
    )
    db = client[os.getenv("MONGO_DATABASE", "sinia_uy")]

    def focos_por_pais() -> dict[str, int]:
        rows = db.focos_snapshots.aggregate([
            {"$unwind": "$focos"},
            {"$match": {"focos.pais": {"$in": ["URY", "BRA", "ARG"]}}},
            {"$group": {"_id": "$focos.pais", "total": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ])
        return {str(row["_id"]): int(row["total"]) for row in rows}

    def snapshots_por_mes() -> int:
        rows = db.focos_snapshots.aggregate([
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m", "date": "$fecha"}}, "total": {"$sum": 1}}},
        ])
        return len(list(rows))

    metricas = {
        "focos_por_pais_embebidos": _timed(focos_por_pais),
        "focos_por_pais_materializado": _timed(
            lambda: {
                doc["pais"]: int(doc["total_focos"])
                for doc in db.focos_resumen_pais.find({}, {"_id": 0, "pais": 1, "total_focos": 1}).sort("pais", 1)
            }
        ),
        "snapshots_por_mes": _timed(snapshots_por_mes),
        "focos_por_mes_materializado": _timed(
            lambda: db.focos_resumen_mes.count_documents({})
        ),
        "ejecuciones_etl": _timed(lambda: db.ejecuciones_etl.count_documents({})),
        "snapshots_totales": _timed(lambda: db.focos_snapshots.count_documents({})),
    }
    client.close()
    return metricas


def main() -> int:
    _load_env()
    REPORTS.mkdir(exist_ok=True)
    report = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "alcance": ["URY", "BRA", "ARG"],
        "postgres": medir_postgres(),
        "mongo": medir_mongo(),
        "lectura": "PostgreSQL mide hechos normalizados; MongoDB mide documentos/snapshots embebidos y trazabilidad.",
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS / f"sql_vs_nosql_real_{stamp}.json"
    latest = REPORTS / "sql_vs_nosql_real_ultimo.json"
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    print(f"Reporte generado: {path}")
    print(json.dumps({
        "postgres_metricas": len(report["postgres"]),
        "mongo_metricas": len(report["mongo"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
