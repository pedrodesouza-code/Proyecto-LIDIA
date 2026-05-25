from __future__ import annotations

import time

from devops.common import load_env, mongo_config, new_run_id, redact_dict, tcp_ping, timed_check


def client():
    from pymongo import MongoClient

    cfg = mongo_config(load_env())
    if cfg["user"] and cfg["password"]:
        uri = (
            f"mongodb://{cfg['user']}:{cfg['password']}@"
            f"{cfg['host']}:{cfg['port']}/{cfg['database']}?authSource={cfg['auth_source']}"
        )
    else:
        uri = f"mongodb://{cfg['host']}:{cfg['port']}"
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def check_tcp() -> dict:
    cfg = mongo_config(load_env())
    seconds = tcp_ping(cfg["host"], cfg["port"])
    return {"target": f"{cfg['host']}:{cfg['port']}", "seconds": seconds}


def check_connection() -> dict:
    cfg = mongo_config(load_env())
    c = client()
    info = c.admin.command("ping")
    return {"config": redact_dict(cfg), "ping": info}


def check_collections() -> dict:
    cfg = mongo_config(load_env())
    db = client()[cfg["database"]]
    return {"database": cfg["database"], "collections": sorted(db.list_collection_names())}


def check_read_write_delete() -> dict:
    cfg = mongo_config(load_env())
    db = client()[cfg["database"]]
    col = db["devops_probe"]
    marker = f"probe_{int(time.time())}"
    result = col.insert_one({"marker": marker, "created_at": time.time()})
    found = col.find_one({"_id": result.inserted_id}, {"_id": 0, "marker": 1})
    deleted = col.delete_one({"_id": result.inserted_id}).deleted_count
    return {"inserted": str(result.inserted_id), "found": found, "deleted_count": deleted}


def main() -> int:
    run_id = new_run_id()
    print(f"run_id={run_id}")
    checks = [
        ("mongo_tcp", check_tcp),
        ("mongo_connection_auth", check_connection),
        ("mongo_collections", check_collections),
        ("mongo_read_write_delete", check_read_write_delete),
    ]
    results = [timed_check(run_id, name, fn) for name, fn in checks]
    fails = sum(1 for r in results if r.status != "PASS")
    print(f"SUMMARY: {len(results)-fails} PASS / {fails} FAIL")
    print(f"log=logs/devops/{run_id}.jsonl")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
