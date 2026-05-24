from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs" / "devops"
LOG_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEYS = ("PASSWORD", "PASS", "TOKEN", "KEY", "SECRET")


@dataclass
class CheckResult:
    name: str
    status: str
    seconds: float
    detail: dict[str, Any]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def mask(key: str, value: Any) -> Any:
    if value is None:
        return None
    if any(part in key.upper() for part in SECRET_KEYS):
        return "***"
    return value


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    for rel in (".env", "config/.env", "config/utec.env", "docker/.env"):
        env.update(read_env_file(ROOT / rel))
    return env


def env_value(env: dict[str, str], *names: str, default: str = "") -> str:
    for name in names:
        val = env.get(name)
        if val not in (None, ""):
            return val
    return default


def pg_config(env: dict[str, str]) -> dict[str, Any]:
    return {
        "host": env_value(env, "POSTGRES_HOST", "PG_HOST", default="localhost"),
        "port": int(env_value(env, "POSTGRES_PORT", "PG_PORT", default="5432")),
        "database": env_value(env, "POSTGRES_DB", "PG_DATABASE", default="grp03db"),
        "user": env_value(env, "POSTGRES_USER", "PG_USER", default=""),
        "password": env_value(env, "POSTGRES_PASSWORD", "PG_PASSWORD", default=""),
    }


def mongo_config(env: dict[str, str]) -> dict[str, Any]:
    database = env_value(env, "MONGO_DB", "MONGO_DATABASE", default="grp03db")
    return {
        "host": env_value(env, "MONGO_HOST", default="localhost"),
        "port": int(env_value(env, "MONGO_PORT", default="27017")),
        "database": database,
        "user": env_value(env, "MONGO_USER", default=""),
        "password": env_value(env, "MONGO_PASSWORD", default=""),
        "auth_source": env_value(env, "MONGO_AUTH_SOURCE", default=database),
    }


def streamlit_config(env: dict[str, str]) -> dict[str, Any]:
    return {
        "host": env_value(env, "STREAMLIT_HOST", default="0.0.0.0"),
        "port": int(env_value(env, "STREAMLIT_PORT", default="8501")),
    }


def redact_dict(d: dict[str, Any]) -> dict[str, Any]:
    return {k: mask(k, v) for k, v in d.items()}


def log_event(run_id: str, event: str, status: str, detail: dict[str, Any]) -> None:
    record = {
        "ts": now_iso(),
        "run_id": run_id,
        "event": event,
        "status": status,
        "detail": detail,
    }
    with (LOG_DIR / f"{run_id}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def timed_check(run_id: str, name: str, fn) -> CheckResult:
    start = time.perf_counter()
    try:
        detail = fn()
        status = "PASS"
    except Exception as exc:
        detail = {"error": type(exc).__name__, "message": str(exc)}
        status = "FAIL"
    seconds = round(time.perf_counter() - start, 4)
    result = CheckResult(name=name, status=status, seconds=seconds, detail=detail)
    log_event(run_id, name, status, {"seconds": seconds, **detail})
    print_result(result)
    return result


def print_result(result: CheckResult) -> None:
    print(f"[{result.status}] {result.name} ({result.seconds}s)")
    if result.detail:
        print(json.dumps(result.detail, indent=2, ensure_ascii=False, default=str))


def run_cmd(cmd: list[str], timeout: int = 10) -> dict[str, Any]:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip()[-4000:],
        "stderr": proc.stderr.strip()[-4000:],
    }


def tcp_ping(host: str, port: int, timeout: float = 3.0) -> float:
    start = time.perf_counter()
    with socket.create_connection((host, port), timeout=timeout):
        return round(time.perf_counter() - start, 4)


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]


def require_vars(env: dict[str, str], groups: dict[str, tuple[str, ...]]) -> dict[str, Any]:
    missing = []
    resolved = {}
    for logical, names in groups.items():
        value = env_value(env, *names, default="")
        resolved[logical] = mask(logical, value)
        if value == "":
            missing.append({"logical": logical, "accepted_names": names})
    return {"missing": missing, "resolved": resolved}


def python_info() -> dict[str, Any]:
    return {
        "executable": sys.executable,
        "version": sys.version.split()[0],
        "prefix": sys.prefix,
        "cwd": str(Path.cwd()),
        "root": str(ROOT),
    }
