from __future__ import annotations

import os
import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
ENV_PATH = RAIZ / "config" / ".env"

try:
    from dotenv import load_dotenv
except ImportError:
    print("[ERROR] Falta python-dotenv. Instala dependencias con pip install -r requirements.txt")
    sys.exit(1)

load_dotenv(ENV_PATH)


def revisar_postgres() -> bool:
    try:
        import psycopg2
    except ImportError:
        print("[ERROR] Falta psycopg2-binary para probar PostgreSQL.")
        return False

    try:
        conn = psycopg2.connect(
            host=os.getenv("PG_HOST", "localhost"),
            port=int(os.getenv("PG_PORT", "5432")),
            dbname=os.getenv("PG_DATABASE", "sinia_uy"),
            user=os.getenv("PG_USER", "sinia_etl_user"),
            password=os.getenv("PG_PASSWORD", ""),
            connect_timeout=5,
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE'"
        )
        tablas = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.views "
            "WHERE table_schema='public'"
        )
        vistas = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM puntos_monitoreo")
        puntos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM puntos_monitoreo WHERE activo = TRUE")
        puntos_activos = cur.fetchone()[0]
        print(f"[OK] PostgreSQL local conectado: {os.getenv('PG_DATABASE', 'sinia_uy')}")
        print(
            f"     tablas={tablas} vistas={vistas} "
            f"puntos_monitoreo={puntos} activos={puntos_activos}"
        )
        cur.close()
        conn.close()
        return True
    except Exception as exc:
        print(f"[ERROR] PostgreSQL local no responde: {type(exc).__name__}: {exc}")
        return False


def revisar_mongo() -> bool:
    try:
        from pymongo import MongoClient
    except ImportError:
        print("[ERROR] Falta pymongo para probar MongoDB.")
        return False

    host = os.getenv("MONGO_HOST", "localhost")
    port = int(os.getenv("MONGO_PORT", "27017"))
    database = os.getenv("MONGO_DATABASE", "sinia_uy")
    user = os.getenv("MONGO_USER", "")
    password = os.getenv("MONGO_PASSWORD", "")
    auth_source = os.getenv("MONGO_AUTH_SOURCE", database)

    if user and password:
        uri = f"mongodb://{user}:{password}@{host}:{port}/{database}?authSource={auth_source}"
    else:
        uri = f"mongodb://{host}:{port}/"

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        cols = sorted(client[database].list_collection_names())
        print(f"[OK] MongoDB local conectado: {database}")
        print(f"     colecciones={','.join(cols) if cols else '(ninguna)'}")
        client.close()
        return True
    except Exception as exc:
        print(f"[ERROR] MongoDB local no responde: {type(exc).__name__}: {exc}")
        print("        Si esta apagado, ejecuta scripts\\levantar_mongo_local.bat")
        return False


if __name__ == "__main__":
    print(f"Usando entorno: {ENV_PATH}")
    ok_pg = revisar_postgres()
    ok_mg = revisar_mongo()
    if ok_pg and ok_mg:
        print("\nTodo listo para trabajar local.")
        sys.exit(0)
    sys.exit(1)
