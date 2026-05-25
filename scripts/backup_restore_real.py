from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / "config" / ".env"
BACKUPS = ROOT / "backups"
REPORTS = ROOT / "reports"


COMMON_PG_DUMP = [
    Path(r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"),
    Path(r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"),
]
COMMON_PG_RESTORE = [
    Path(r"C:\Program Files\PostgreSQL\18\bin\pg_restore.exe"),
    Path(r"C:\Program Files\PostgreSQL\16\bin\pg_restore.exe"),
]


def _which(name: str, common_paths: list[Path] | None = None) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for candidate in common_paths or []:
        if candidate.exists():
            return str(candidate)
    return None


def _json_default(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "binary"):
        return str(value)
    return str(value)


def _mask_env_line(line: str) -> str:
    upper = line.upper()
    if any(token in upper for token in ["PASSWORD=", "PASS=", "KEY=", "SECRET=", "TOKEN="]):
        key = line.split("=", 1)[0]
        return f"{key}=***REDACTED***"
    return line


def _load_env() -> None:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)


def _pg_counts() -> dict[str, int]:
    import psycopg2

    conn = psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
        dbname=os.getenv("PG_DATABASE", "sinia_uy"),
        user=os.getenv("PG_USER", "sinia_etl_user"),
        password=os.getenv("PG_PASSWORD", ""),
        connect_timeout=5,
    )
    tables = [
        "puntos_monitoreo",
        "focos_calor",
        "meteo_diario",
        "calidad_aire_diario",
        "precipitacion_mensual",
        "cobertura_vegetal",
        "etl_ejecuciones",
    ]
    counts: dict[str, int] = {}
    with conn, conn.cursor() as cur:
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = int(cur.fetchone()[0])
    conn.close()
    return counts


def _mongo_counts() -> dict[str, int]:
    from pymongo import MongoClient

    client = MongoClient(
        f"mongodb://{os.getenv('MONGO_HOST', 'localhost')}:{int(os.getenv('MONGO_PORT', '27017'))}/",
        serverSelectionTimeoutMS=5000,
    )
    db = client[os.getenv("MONGO_DATABASE", "sinia_uy")]
    counts = {name: db[name].count_documents({}) for name in sorted(db.list_collection_names())}
    client.close()
    return counts


def backup() -> dict[str, Any]:
    _load_env()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUPS / f"real_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(exist_ok=True)

    manifest: dict[str, Any] = {
        "tipo": "backup_real",
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "directorio": str(backup_dir),
        "postgres": {"estado": "pendiente"},
        "mongo": {"estado": "pendiente"},
        "config": {"estado": "pendiente"},
    }

    manifest["postgres"]["conteos_antes"] = _pg_counts()
    pg_dump = _which("pg_dump", COMMON_PG_DUMP)
    if not pg_dump:
        raise RuntimeError("No se encontro pg_dump. Instala PostgreSQL client tools.")

    pg_file = backup_dir / f"postgres_{os.getenv('PG_DATABASE', 'sinia_uy')}_{stamp}.dump"
    env = os.environ.copy()
    env["PGPASSWORD"] = os.getenv("PG_PASSWORD", "")
    cmd = [
        pg_dump,
        "-h",
        os.getenv("PG_HOST", "localhost"),
        "-p",
        str(os.getenv("PG_PORT", "5432")),
        "-U",
        os.getenv("PG_USER", "sinia_etl_user"),
        "-d",
        os.getenv("PG_DATABASE", "sinia_uy"),
        "--format=custom",
        "--no-password",
        "-f",
        str(pg_file),
    ]
    subprocess.run(cmd, check=True, env=env)
    manifest["postgres"].update(
        {
            "estado": "ok",
            "herramienta": pg_dump,
            "archivo": str(pg_file),
            "bytes": pg_file.stat().st_size,
        }
    )

    manifest["mongo"]["conteos_antes"] = _mongo_counts()
    mongo_dir = backup_dir / "mongo_jsonl"
    mongo_dir.mkdir(exist_ok=True)

    from pymongo import MongoClient

    client = MongoClient(
        f"mongodb://{os.getenv('MONGO_HOST', 'localhost')}:{int(os.getenv('MONGO_PORT', '27017'))}/",
        serverSelectionTimeoutMS=5000,
    )
    db_name = os.getenv("MONGO_DATABASE", "sinia_uy")
    db = client[db_name]
    exported: dict[str, dict[str, Any]] = {}
    for collection in sorted(db.list_collection_names()):
        path = mongo_dir / f"{collection}.jsonl.gz"
        docs = 0
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            for doc in db[collection].find({}):
                fh.write(json.dumps(doc, ensure_ascii=False, default=_json_default))
                fh.write("\n")
                docs += 1
        exported[collection] = {"documentos": docs, "archivo": str(path), "bytes": path.stat().st_size}
    client.close()
    manifest["mongo"].update(
        {
            "estado": "ok",
            "metodo": "pymongo_jsonl_gzip",
            "database": db_name,
            "colecciones": exported,
        }
    )

    config_dir = backup_dir / "config"
    config_dir.mkdir(exist_ok=True)
    if ENV_PATH.exists():
        masked = [_mask_env_line(line) for line in ENV_PATH.read_text(encoding="utf-8").splitlines()]
        (config_dir / "env_masked.txt").write_text("\n".join(masked) + "\n", encoding="utf-8")
    shutil.copy2(ROOT / "config" / "settings.py", config_dir / "settings.py")
    manifest["config"].update({"estado": "ok", "directorio": str(config_dir)})

    manifest_path = backup_dir / "manifest.json"
    text = json.dumps(manifest, ensure_ascii=False, indent=2)
    manifest_path.write_text(text, encoding="utf-8")
    (REPORTS / "backup_restore_ultimo.json").write_text(text, encoding="utf-8")
    print(f"Backup real generado: {backup_dir}")
    print(f"Manifest: {manifest_path}")
    return manifest


def restore_mongo_jsonl(backup_dir: Path, drop: bool = False) -> dict[str, Any]:
    _load_env()
    from pymongo import MongoClient

    mongo_dir = backup_dir / "mongo_jsonl"
    if not mongo_dir.exists():
        raise FileNotFoundError(f"No existe {mongo_dir}")

    client = MongoClient(
        f"mongodb://{os.getenv('MONGO_HOST', 'localhost')}:{int(os.getenv('MONGO_PORT', '27017'))}/",
        serverSelectionTimeoutMS=5000,
    )
    db = client[os.getenv("MONGO_DATABASE", "sinia_uy")]
    restored: dict[str, int] = {}
    for file in sorted(mongo_dir.glob("*.jsonl.gz")):
        collection = file.name.replace(".jsonl.gz", "")
        if drop:
            db[collection].drop()
        batch: list[dict[str, Any]] = []
        with gzip.open(file, "rt", encoding="utf-8") as fh:
            for line in fh:
                batch.append(json.loads(line))
                if len(batch) >= 1000:
                    db[collection].insert_many(batch, ordered=False)
                    restored[collection] = restored.get(collection, 0) + len(batch)
                    batch = []
        if batch:
            db[collection].insert_many(batch, ordered=False)
            restored[collection] = restored.get(collection, 0) + len(batch)
    client.close()
    return restored


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup/restore real de SINIA-UY.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("backup", help="Genera backup real de PostgreSQL, MongoDB y config.")
    restore = sub.add_parser("restore-mongo", help="Restaura colecciones Mongo desde JSONL gzip.")
    restore.add_argument("backup_dir")
    restore.add_argument("--drop", action="store_true")
    args = parser.parse_args()

    if args.cmd == "backup":
        backup()
        return 0
    if args.cmd == "restore-mongo":
        result = restore_mongo_jsonl(Path(args.backup_dir), drop=args.drop)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
