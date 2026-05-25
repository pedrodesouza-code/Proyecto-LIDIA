from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv
from pymongo import MongoClient


ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _mongo_client() -> MongoClient:
    mongo_uri = os.getenv("MONGO_URI")
    if mongo_uri:
        return MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)

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
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def _postgres_report() -> dict[str, Any]:
    conn = psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
        dbname=os.getenv("PG_DATABASE", "sinia_uy"),
        user=os.getenv("PG_USER", "sinia_etl"),
        password=os.getenv("PG_PASSWORD", ""),
        connect_timeout=8,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, now()")
            database, user, checked_at = cur.fetchone()

            counts: dict[str, int | None] = {}
            for table in [
                "puntos_monitoreo",
                "focos_calor",
                "meteo_diario",
                "calidad_aire_diario",
                "precipitacion_mensual",
                "cobertura_vegetal",
                "etl_ejecuciones",
            ]:
                cur.execute("SELECT to_regclass(%s)", (table,))
                exists = cur.fetchone()[0] is not None
                if exists:
                    cur.execute(f"SELECT count(*) FROM {table}")
                    counts[table] = int(cur.fetchone()[0])
                else:
                    counts[table] = None

            cur.execute(
                """
                SELECT min(fecha_adq), max(fecha_adq),
                       count(*) FILTER (WHERE fecha_adq >= current_date - interval '7 days')
                FROM focos_calor
                """
            )
            focos_min, focos_max, focos_7d = cur.fetchone()

            cur.execute(
                """
                SELECT pais, count(*)
                FROM focos_calor
                GROUP BY pais
                ORDER BY pais
                """
            )
            focos_por_pais = {pais: int(total) for pais, total in cur.fetchall()}

            cur.execute(
                """
                SELECT tipo_dato, min(fecha), max(fecha), count(*)
                FROM meteo_diario
                GROUP BY tipo_dato
                ORDER BY tipo_dato
                """
            )
            meteo = [
                {"tipo_dato": row[0], "desde": row[1], "hasta": row[2], "filas": int(row[3])}
                for row in cur.fetchall()
            ]

            matviews: dict[str, int | None] = {}
            for view in ["mv_focos_por_pais", "mv_focos_por_pais_mes"]:
                cur.execute(
                    """
                    SELECT 1
                    FROM pg_matviews
                    WHERE schemaname = current_schema() AND matviewname = %s
                    """,
                    (view,),
                )
                if cur.fetchone():
                    cur.execute(f"SELECT count(*) FROM {view}")
                    matviews[view] = int(cur.fetchone()[0])
                else:
                    matviews[view] = None

        return {
            "conexion": {"database": database, "user": user, "checked_at": checked_at},
            "conteos": counts,
            "focos": {
                "desde": focos_min,
                "hasta": focos_max,
                "ultimos_7_dias": int(focos_7d or 0),
                "por_pais": focos_por_pais,
            },
            "meteo": meteo,
            "materializadas": matviews,
        }
    finally:
        conn.close()


def _mongo_report() -> dict[str, Any]:
    client = _mongo_client()
    try:
        database = os.getenv("MONGO_DATABASE", "sinia_uy")
        db = client[database]
        client.admin.command("ping")
        collections = sorted(db.list_collection_names())
        counts = {name: db[name].count_documents({}) for name in collections}
        last_snapshot = db.focos_snapshots.find_one(
            {},
            sort=[("fecha", -1)],
            projection={"_id": 0, "fecha": 1, "total_focos": 1},
        )
        snapshots_con_pais = db.focos_snapshots.count_documents({"focos.pais": {"$exists": True}})
        snapshots_sin_pais = db.focos_snapshots.count_documents(
            {"focos.0": {"$exists": True}, "focos.pais": {"$exists": False}}
        )
        last_execution = db.ejecuciones_etl.find_one(
            {},
            sort=[("iniciado_en", -1)],
            projection={"_id": 0, "fuente": 1, "etapa": 1, "estado": 1, "iniciado_en": 1},
        )
        return {
            "conexion": {"database": database},
            "colecciones": collections,
            "conteos": counts,
            "ultimo_snapshot": last_snapshot,
            "snapshots_con_pais": int(snapshots_con_pais),
            "snapshots_sin_pais": int(snapshots_sin_pais),
            "ultima_ejecucion": last_execution,
        }
    finally:
        client.close()


def main() -> int:
    env_path = ROOT / "config" / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    report = {
        "generado_en": datetime.now(timezone.utc),
        "postgres": _postgres_report(),
        "mongo": _mongo_report(),
    }

    REPORTS.mkdir(exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=2, default=_json_default)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    (REPORTS / f"utec_verificacion_{stamp}.json").write_text(text, encoding="utf-8")
    (REPORTS / "utec_verificacion_ultimo.json").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
