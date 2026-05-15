from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
VALIDOS = ("URY", "BRA", "ARG")
PUNTOS_VALIDOS = (
    "Cuiabá",
    "Porto_Alegre",
    "Manaus",
    "Campo_Grande",
    "Brasília",
    "Salta",
    "Posadas",
    "Buenos_Aires",
    "Mendoza",
    "Rivera",
    "Montevideo",
)


def _load_env() -> None:
    env_path = ROOT / "config" / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def _pg_connect():
    import psycopg2

    user = os.getenv("PG_SUPERUSER") or os.getenv("PG_USER") or "postgres"
    password = (
        os.getenv("PG_SUPERPASS")
        or os.getenv("PG_SUPER_PASSWORD")
        or os.getenv("PG_PASSWORD")
        or "postgres_super_2026"
    )
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
        dbname=os.getenv("PG_DATABASE", "sinia_uy"),
        user=user,
        password=password,
        connect_timeout=5,
    )


def _pg_distribution(cur) -> dict[str, Any]:
    cur.execute("SELECT pais, COUNT(*) FROM puntos_monitoreo GROUP BY pais ORDER BY pais")
    puntos = {pais or "(null)": int(total) for pais, total in cur.fetchall()}
    cur.execute("SELECT pais, COUNT(*) FROM focos_calor GROUP BY pais ORDER BY pais")
    focos = {pais or "(null)": int(total) for pais, total in cur.fetchall()}
    counts: dict[str, int] = {}
    for table in [
        "paises_referencia",
        "puntos_monitoreo",
        "focos_calor",
        "meteo_diario",
        "calidad_aire_diario",
        "precipitacion_mensual",
        "cobertura_vegetal",
    ]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = int(cur.fetchone()[0])
    return {"conteos": counts, "puntos_por_pais": puntos, "focos_por_pais": focos}


def limpiar_postgres() -> dict[str, Any]:
    conn = _pg_connect()
    result: dict[str, Any] = {}
    with conn:
        with conn.cursor() as cur:
            result["antes"] = _pg_distribution(cur)
            cur.execute(
                """
                DELETE FROM cobertura_vegetal
                WHERE id_punto IN (
                    SELECT id FROM puntos_monitoreo
                    WHERE pais NOT IN %s OR nombre NOT IN %s
                )
                """,
                (VALIDOS, PUNTOS_VALIDOS),
            )
            cobertura = cur.rowcount
            cur.execute(
                """
                DELETE FROM precipitacion_mensual
                WHERE id_punto IN (
                    SELECT id FROM puntos_monitoreo
                    WHERE pais NOT IN %s OR nombre NOT IN %s
                )
                """,
                (VALIDOS, PUNTOS_VALIDOS),
            )
            precipitacion = cur.rowcount
            cur.execute(
                """
                DELETE FROM calidad_aire_diario
                WHERE id_punto IN (
                    SELECT id FROM puntos_monitoreo
                    WHERE pais NOT IN %s OR nombre NOT IN %s
                )
                """,
                (VALIDOS, PUNTOS_VALIDOS),
            )
            calidad = cur.rowcount
            cur.execute(
                """
                DELETE FROM meteo_diario
                WHERE id_punto IN (
                    SELECT id FROM puntos_monitoreo
                    WHERE pais NOT IN %s OR nombre NOT IN %s
                )
                """,
                (VALIDOS, PUNTOS_VALIDOS),
            )
            meteo = cur.rowcount
            cur.execute("DELETE FROM focos_calor WHERE pais NOT IN %s OR pais IS NULL", (VALIDOS,))
            focos = cur.rowcount
            cur.execute(
                "DELETE FROM puntos_monitoreo WHERE pais NOT IN %s OR nombre NOT IN %s",
                (VALIDOS, PUNTOS_VALIDOS),
            )
            puntos = cur.rowcount
            cur.execute("DELETE FROM paises_referencia WHERE codigo_iso3 NOT IN %s", (VALIDOS,))
            paises = cur.rowcount
            cur.execute(
                """
                INSERT INTO paises_referencia (codigo_iso3, codigo_iso2, nombre) VALUES
                    ('URY', 'UY', 'Uruguay'),
                    ('BRA', 'BR', 'Brasil'),
                    ('ARG', 'AR', 'Argentina')
                ON CONFLICT (codigo_iso3) DO NOTHING
                """
            )
            result["eliminados"] = {
                "cobertura_vegetal": cobertura,
                "precipitacion_mensual": precipitacion,
                "calidad_aire_diario": calidad,
                "meteo_diario": meteo,
                "focos_calor": focos,
                "puntos_monitoreo": puntos,
                "paises_referencia": paises,
            }
            result["despues"] = _pg_distribution(cur)
    conn.close()
    return result


def _mongo_distribution(db) -> dict[str, Any]:
    pipeline = [
        {"$unwind": "$focos"},
        {"$group": {"_id": "$focos.pais", "total": {"$sum": 1}}},
        {"$sort": {"total": -1}},
    ]
    return {
        "conteos": {name: db[name].count_documents({}) for name in sorted(db.list_collection_names())},
        "focos_por_pais": {str(row["_id"]): int(row["total"]) for row in db.focos_snapshots.aggregate(pipeline)},
    }


def limpiar_mongo() -> dict[str, Any]:
    from pymongo import MongoClient

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
    result: dict[str, Any] = {"antes": _mongo_distribution(db)}
    res_alertas = db.alertas.delete_many({"pais": {"$exists": True, "$nin": list(VALIDOS)}})
    res_pull = db.focos_snapshots.update_many(
        {},
        {"$pull": {"focos": {"pais": {"$exists": True, "$nin": list(VALIDOS)}}}},
    )
    res_sin_pais = db.focos_snapshots.delete_many(
        {"focos.0": {"$exists": True}, "focos.pais": {"$exists": False}}
    )
    res_vacios = db.focos_snapshots.delete_many(
        {"$or": [{"focos": {"$size": 0}}, {"focos": {"$exists": False}}]}
    )
    result["eliminados"] = {
        "alertas": int(res_alertas.deleted_count),
        "snapshots_actualizados": int(res_pull.modified_count),
        "snapshots_sin_pais": int(res_sin_pais.deleted_count),
        "snapshots_vacios": int(res_vacios.deleted_count),
    }
    result["despues"] = _mongo_distribution(db)
    client.close()
    return result


def main() -> int:
    _load_env()
    REPORTS.mkdir(exist_ok=True)
    report = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "alcance_valido": list(VALIDOS),
        "puntos_validos": list(PUNTOS_VALIDOS),
        "postgres": limpiar_postgres(),
        "mongo": limpiar_mongo(),
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS / f"limpieza_alcance_{stamp}.json"
    latest = REPORTS / "limpieza_alcance_ultimo.json"
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    print(f"Reporte generado: {path}")
    print(json.dumps({
        "postgres_focos": report["postgres"]["despues"]["conteos"]["focos_calor"],
        "mongo_snapshots": report["mongo"]["despues"]["conteos"].get("focos_snapshots", 0),
        "alcance": list(VALIDOS),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
