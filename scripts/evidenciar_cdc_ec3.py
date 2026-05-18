from __future__ import annotations

import json
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RAIZ = Path(__file__).resolve().parent.parent
REPORTS = RAIZ / "reports"
OUT_ULTIMO = REPORTS / "cdc_ec3_ultimo.json"
OUT_HIST = REPORTS / f"cdc_ec3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

sys.path.insert(0, str(RAIZ))


def _json_default(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _guardar(reporte: dict[str, Any]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    for path in (OUT_ULTIMO, OUT_HIST):
        path.write_text(
            json.dumps(reporte, indent=2, ensure_ascii=False, default=_json_default),
            encoding="utf-8",
        )


def _probar_postgres() -> dict[str, Any]:
    import psycopg2

    from config.settings import PG_CONFIG

    resultado: dict[str, Any] = {
        "estado": "no_ejecutado",
        "objetivo": "Demostrar insercion, idempotencia, modificacion CDC y rollback en meteo_diario.",
        "conexion": {
            "host": PG_CONFIG.get("host"),
            "port": PG_CONFIG.get("port"),
            "database": PG_CONFIG.get("database"),
            "user": PG_CONFIG.get("user"),
        },
    }

    conn = psycopg2.connect(**PG_CONFIG, connect_timeout=5)
    conn.autocommit = False
    cur = conn.cursor()
    t0 = time.perf_counter()

    try:
        cur.execute("SELECT id, nombre FROM puntos_monitoreo WHERE activo = TRUE ORDER BY id LIMIT 1")
        punto = cur.fetchone()
        if not punto:
            raise RuntimeError("No hay puntos_monitoreo activos para ejecutar la prueba.")

        id_punto, nombre_punto = punto
        fecha_prueba = "2099-01-01"
        tipo_dato = "forecast"

        cur.execute(
            """
            SELECT COUNT(*)
            FROM meteo_diario
            WHERE fecha = %s AND id_punto = %s AND tipo_dato = %s
            """,
            (fecha_prueba, id_punto, tipo_dato),
        )
        antes = cur.fetchone()[0]

        sql_upsert = """
            INSERT INTO meteo_diario (
                fecha, id_punto, tipo_dato,
                temperature_2m_max, relative_humidity_2m_min,
                wind_speed_10m_max, et0_fao_evapotranspiration,
                riesgo_temp, riesgo_humedad, riesgo_viento, riesgo_sequia,
                indice_riesgo, nivel_riesgo, fuente
            ) VALUES (
                %(fecha)s, %(id_punto)s, %(tipo_dato)s,
                %(temp)s, %(humedad)s,
                %(viento)s, %(et0)s,
                %(riesgo_temp)s, %(riesgo_humedad)s, %(riesgo_viento)s, %(riesgo_sequia)s,
                %(indice)s, %(nivel)s, 'cdc_demo_ec3'
            )
            ON CONFLICT (fecha, id_punto, tipo_dato)
            DO UPDATE SET
                indice_riesgo = EXCLUDED.indice_riesgo,
                nivel_riesgo = EXCLUDED.nivel_riesgo,
                temperature_2m_max = EXCLUDED.temperature_2m_max,
                relative_humidity_2m_min = EXCLUDED.relative_humidity_2m_min,
                wind_speed_10m_max = EXCLUDED.wind_speed_10m_max,
                precipitation_sum = EXCLUDED.precipitation_sum,
                actualizado_en = NOW()
            WHERE
                meteo_diario.indice_riesgo IS DISTINCT FROM EXCLUDED.indice_riesgo
                OR meteo_diario.nivel_riesgo IS DISTINCT FROM EXCLUDED.nivel_riesgo
        """

        base = {
            "fecha": fecha_prueba,
            "id_punto": id_punto,
            "tipo_dato": tipo_dato,
            "temp": 30.0,
            "humedad": 40.0,
            "viento": 20.0,
            "et0": 4.0,
            "riesgo_temp": 0.50,
            "riesgo_humedad": 0.50,
            "riesgo_viento": 0.25,
            "riesgo_sequia": 0.50,
            "indice": 0.4000,
            "nivel": "moderado",
        }

        cur.execute(sql_upsert, base)
        rowcount_insert = cur.rowcount

        cur.execute(sql_upsert, base)
        rowcount_idempotente = cur.rowcount

        modificado = dict(base)
        modificado["indice"] = 0.8000
        modificado["nivel"] = "muy_alto"
        modificado["temp"] = 41.0

        cur.execute(sql_upsert, modificado)
        rowcount_update = cur.rowcount

        cur.execute(
            """
            SELECT indice_riesgo, nivel_riesgo, temperature_2m_max
            FROM meteo_diario
            WHERE fecha = %s AND id_punto = %s AND tipo_dato = %s
            """,
            (fecha_prueba, id_punto, tipo_dato),
        )
        fila_modificada = cur.fetchone()

        cur.execute(
            """
            SELECT COUNT(*)
            FROM meteo_diario
            WHERE fecha = %s AND id_punto = %s AND tipo_dato = %s
            """,
            (fecha_prueba, id_punto, tipo_dato),
        )
        durante = cur.fetchone()[0]

        conn.rollback()

        cur.execute(
            """
            SELECT COUNT(*)
            FROM meteo_diario
            WHERE fecha = %s AND id_punto = %s AND tipo_dato = %s
            """,
            (fecha_prueba, id_punto, tipo_dato),
        )
        despues_rollback = cur.fetchone()[0]

        resultado.update(
            {
                "estado": "ok",
                "punto_usado": {"id": id_punto, "nombre": nombre_punto},
                "clave_natural": {
                    "fecha": fecha_prueba,
                    "id_punto": id_punto,
                    "tipo_dato": tipo_dato,
                },
                "conteos": {
                    "antes": antes,
                    "durante_transaccion": durante,
                    "despues_rollback": despues_rollback,
                },
                "operaciones": {
                    "insert_inicial_rowcount": rowcount_insert,
                    "repeticion_idempotente_rowcount": rowcount_idempotente,
                    "modificacion_cdc_rowcount": rowcount_update,
                },
                "fila_modificada_en_transaccion": {
                    "indice_riesgo": float(fila_modificada[0]) if fila_modificada else None,
                    "nivel_riesgo": fila_modificada[1] if fila_modificada else None,
                    "temperature_2m_max": float(fila_modificada[2]) if fila_modificada else None,
                },
                "lectura_defensa": (
                    "La primera operacion inserta, la segunda no duplica y la tercera actualiza "
                    "porque detecta cambios. ROLLBACK deja la base como estaba."
                ),
                "duracion_segundos": round(time.perf_counter() - t0, 3),
            }
        )
    except Exception as exc:
        conn.rollback()
        resultado.update({"estado": "error", "error": f"{type(exc).__name__}: {exc}"})
    finally:
        cur.close()
        conn.close()

    return resultado


def _probar_mongo() -> dict[str, Any]:
    from config.settings import MONGO_CONFIG

    resultado: dict[str, Any] = {
        "estado": "no_ejecutado",
        "objetivo": "Demostrar insercion y limpieza controlada de una ejecucion ETL documental.",
        "conexion": {
            "host": MONGO_CONFIG.get("host"),
            "port": MONGO_CONFIG.get("port"),
            "database": MONGO_CONFIG.get("database"),
            "user": MONGO_CONFIG.get("user"),
        },
    }

    try:
        from pymongo import MongoClient
    except ImportError as exc:
        resultado.update({"estado": "error", "error": f"pymongo no disponible: {exc}"})
        return resultado

    host = MONGO_CONFIG.get("host", "localhost")
    port = int(MONGO_CONFIG.get("port", 27017))
    database = MONGO_CONFIG.get("database", "sinia_uy")
    user = MONGO_CONFIG.get("user", "")
    password = MONGO_CONFIG.get("password", "")

    if user and password:
        uri = f"mongodb://{user}:{password}@{host}:{port}/{database}?authSource={database}"
    else:
        uri = f"mongodb://{host}:{port}/"

    marca = f"cdc_demo_ec3_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    doc = {
        "fuente": "cdc_demo_ec3",
        "etapa": "testing",
        "tipo_carga": "test",
        "estado": "ok",
        "iniciado_en": datetime.now(timezone.utc),
        "host": socket.gethostname(),
        "marca_demo": marca,
        "metricas": {
            "registros_procesados": 1,
            "registros_insertados": 1,
            "registros_actualizados": 1,
            "registros_sin_cambio": 1,
        },
    }

    t0 = time.perf_counter()
    client = None
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        col = client[database]["ejecuciones_etl"]
        antes = col.count_documents({"fuente": "cdc_demo_ec3"})
        inserted = col.insert_one(doc)
        encontrado = col.find_one({"_id": inserted.inserted_id}, {"_id": 0, "fuente": 1, "etapa": 1, "marca_demo": 1})
        borrados = col.delete_one({"_id": inserted.inserted_id}).deleted_count
        despues = col.count_documents({"fuente": "cdc_demo_ec3"})
        resultado.update(
            {
                "estado": "ok",
                "conteos": {"antes": antes, "despues_limpieza": despues},
                "insertado": bool(inserted.inserted_id),
                "documento_encontrado": encontrado,
                "documentos_borrados_limpieza": borrados,
                "lectura_defensa": (
                    "MongoDB registra una ejecucion ETL flexible en formato documental. "
                    "La prueba inserta evidencia y la limpia para no dejar basura."
                ),
                "duracion_segundos": round(time.perf_counter() - t0, 3),
            }
        )
    except Exception as exc:
        resultado.update({"estado": "error", "error": f"{type(exc).__name__}: {exc}"})
    finally:
        if client is not None:
            client.close()

    return resultado


def main() -> int:
    reporte: dict[str, Any] = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "script": "scripts/evidenciar_cdc_ec3.py",
        "postgres": {},
        "mongo": {},
    }

    try:
        reporte["postgres"] = _probar_postgres()
    except Exception as exc:
        reporte["postgres"] = {"estado": "error", "error": f"{type(exc).__name__}: {exc}"}

    try:
        reporte["mongo"] = _probar_mongo()
    except Exception as exc:
        reporte["mongo"] = {"estado": "error", "error": f"{type(exc).__name__}: {exc}"}

    reporte["estado_general"] = (
        "ok"
        if reporte["postgres"].get("estado") == "ok"
        else "parcial"
    )
    reporte["nota"] = (
        "PostgreSQL es obligatorio para la evidencia CDC principal. MongoDB es evidencia "
        "complementaria y puede fallar si el servicio no esta activo localmente."
    )

    _guardar(reporte)
    print(json.dumps(reporte, indent=2, ensure_ascii=False, default=_json_default))
    print(f"\nReporte guardado en: {OUT_ULTIMO}")
    return 0 if reporte["estado_general"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
