from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import socket
from pathlib import Path

from devops.common import (
    ROOT,
    load_env,
    new_run_id,
    python_info,
    require_vars,
    run_cmd,
    timed_check,
)


def check_os() -> dict:
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "hostname": socket.gethostname(),
    }


def check_paths() -> dict:
    paths = [ROOT, ROOT / "data", ROOT / "etl", ROOT / "sql", ROOT / "tests", ROOT / "logs"]
    detail = {}
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        ok = False
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            ok = True
        except Exception:
            ok = False
        detail[str(path)] = {"exists": path.exists(), "writable": ok}
    return detail


def check_commands() -> dict:
    names = ["python", "python3", "pip", "psql", "pg_isready", "mongosh", "mongo", "streamlit", "jupyter"]
    return {name: shutil.which(name) for name in names}


def check_imports() -> dict:
    modules = ["pandas", "pyarrow", "requests", "dotenv", "psycopg2", "pymongo", "streamlit"]
    return {m: bool(importlib.util.find_spec(m)) for m in modules}


def check_internet() -> dict:
    import urllib.request

    targets = ["https://open-meteo.com", "https://firms.modaps.eosdis.nasa.gov"]
    out = {}
    for url in targets:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                out[url] = {"ok": True, "status": resp.status}
        except Exception as exc:
            out[url] = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
    return out


def check_processes() -> dict:
    if shutil.which("ps") is None:
        return {
            "ps_available": False,
            "processes": [],
            "note": "El contenedor no expone el comando ps; se omite inspección de procesos.",
        }
    cmd = ["ps", "-eo", "pid,comm,args"]
    result = run_cmd(cmd, timeout=5)
    lines = [
        line for line in result["stdout"].splitlines()
        if any(token in line.lower() for token in ("postgres", "mongo", "streamlit", "jupyter"))
    ]
    return {"ps_available": True, "processes": lines[:80]}


def check_env_vars() -> dict:
    env = load_env()
    return require_vars(env, {
        "POSTGRES_HOST": ("POSTGRES_HOST", "PG_HOST"),
        "POSTGRES_PORT": ("POSTGRES_PORT", "PG_PORT"),
        "POSTGRES_DB": ("POSTGRES_DB", "PG_DATABASE"),
        "POSTGRES_USER": ("POSTGRES_USER", "PG_USER"),
        "POSTGRES_PASSWORD": ("POSTGRES_PASSWORD", "PG_PASSWORD"),
        "MONGO_HOST": ("MONGO_HOST",),
        "MONGO_PORT": ("MONGO_PORT",),
        "MONGO_DB": ("MONGO_DB", "MONGO_DATABASE"),
        "MONGO_USER": ("MONGO_USER",),
        "MONGO_PASSWORD": ("MONGO_PASSWORD",),
    })


def check_jupyter() -> dict:
    return {
        "workspace": str(Path.cwd()),
        "root": str(ROOT),
        "jupyter_env": {
            "JUPYTERHUB_USER": os.environ.get("JUPYTERHUB_USER"),
            "JUPYTERHUB_SERVICE_PREFIX": os.environ.get("JUPYTERHUB_SERVICE_PREFIX"),
            "JPY_SESSION_NAME": os.environ.get("JPY_SESSION_NAME"),
        },
        "notebook_import": bool(importlib.util.find_spec("notebook")),
        "jupyterlab_import": bool(importlib.util.find_spec("jupyterlab")),
    }


def main() -> int:
    run_id = new_run_id()
    print(f"run_id={run_id}")
    checks = [
        ("python", python_info),
        ("os", check_os),
        ("paths_permissions", check_paths),
        ("commands", check_commands),
        ("imports", check_imports),
        ("internet", check_internet),
        ("processes", check_processes),
        ("env_vars", check_env_vars),
        ("jupyter", check_jupyter),
    ]
    results = [timed_check(run_id, name, fn) for name, fn in checks]
    fails = sum(1 for r in results if r.status != "PASS")
    print(f"SUMMARY: {len(results)-fails} PASS / {fails} FAIL")
    print(f"log=logs/devops/{run_id}.jsonl")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
