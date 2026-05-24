from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from devops.common import ROOT, load_env, new_run_id, run_cmd, streamlit_config, timed_check


def check_installation() -> dict:
    result = run_cmd([sys.executable, "-m", "streamlit", "version"], timeout=15)
    if result["returncode"] != 0:
        raise RuntimeError(result["stderr"] or result["stdout"])
    return result


def free_port(preferred: int) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"No hay puertos libres entre {preferred} y {preferred + 19}")


def launch_and_probe() -> dict:
    cfg = streamlit_config(load_env())
    port = free_port(cfg["port"])
    app = ROOT / "dashboard" / "utec_dashboard.py"
    if not app.exists():
        raise FileNotFoundError(str(app))
    log_path = ROOT / "logs" / "devops" / f"streamlit_{port}.log"
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [
                sys.executable, "-m", "streamlit", "run", str(app),
                "--server.address", "0.0.0.0",
                "--server.port", str(port),
                "--server.headless", "true",
            ],
            cwd=str(ROOT),
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
    try:
        url = f"http://127.0.0.1:{port}"
        last_error = ""
        for _ in range(30):
            if proc.poll() is not None:
                raise RuntimeError(f"Streamlit termino antes de responder. Ver {log_path}")
            try:
                with urllib.request.urlopen(url, timeout=2) as resp:
                    html = resp.read(200).decode("utf-8", errors="ignore")
                    return {
                        "url_local": url,
                        "port": port,
                        "pid": proc.pid,
                        "status": resp.status,
                        "html_prefix": html,
                        "log": str(log_path),
                    }
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                time.sleep(1)
        raise RuntimeError(f"Streamlit no respondio en puerto {port}: {last_error}. Ver {log_path}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    run_id = new_run_id()
    print(f"run_id={run_id}")
    checks = [
        ("streamlit_installation", check_installation),
        ("streamlit_launch_http", launch_and_probe),
    ]
    results = [timed_check(run_id, name, fn) for name, fn in checks]
    fails = sum(1 for r in results if r.status != "PASS")
    print(f"SUMMARY: {len(results)-fails} PASS / {fails} FAIL")
    print(f"log=logs/devops/{run_id}.jsonl")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
