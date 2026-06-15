"""Ejecuta y mide la carga completa oficial del ETL.

Por defecto ejecuta ``python3 -m etl.main --source ALL``. Se puede cambiar el
comando con LIDIA_FULL_LOAD_COMMAND. El script registra conteos antes/despues
cuando PostgreSQL esta disponible y deja log aun si el proceso falla.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import PG_CONFIG  # noqa: E402

LOG_PATH = ROOT / "evidencia" / "logs" / "carga_completa_oficial_tiempo.log"
COUNT_QUERIES = {
    "dw.fact_incendio": "SELECT COUNT(*) FROM dw.fact_incendio",
    "staging.stg_firms": "SELECT COUNT(*) FROM staging.stg_firms",
    "staging.stg_meteo": "SELECT COUNT(*) FROM staging.stg_meteo",
    "staging.stg_chirps": "SELECT COUNT(*) FROM staging.stg_chirps",
    "staging.stg_modis": "SELECT COUNT(*) FROM staging.stg_modis",
    "staging.stg_calidad_aire": "SELECT COUNT(*) FROM staging.stg_calidad_aire",
    "staging.rechazos_etl": "SELECT COUNT(*) FROM staging.rechazos_etl",
    "audit.etl_runs": "SELECT COUNT(*) FROM audit.etl_runs",
}


def emit(lines: list[str], message: str, **payload: object) -> None:
    event = {"timestamp": datetime.now(timezone.utc).isoformat(), "message": message, **payload}
    text = json.dumps(event, ensure_ascii=False, default=str)
    print(text, flush=True)
    lines.append(text)


def read_counts(lines: list[str], label: str) -> None:
    try:
        with psycopg2.connect(**PG_CONFIG) as conn:
            with conn.cursor() as cur:
                counts = {}
                for name, query in COUNT_QUERIES.items():
                    cur.execute(query)
                    counts[name] = int(cur.fetchone()[0] or 0)
                emit(lines, "conteos_postgres", momento=label, conteos=counts)
    except Exception as exc:  # noqa: BLE001
        emit(lines, "conteos_postgres_no_disponibles", momento=label, error=f"{type(exc).__name__}: {exc}")


def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    command = os.getenv("LIDIA_FULL_LOAD_COMMAND", "python3 -m etl.main --source ALL")
    emit(lines, "inicio_carga_completa", comando=command)
    read_counts(lines, "antes")
    started = time.perf_counter()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        shlex.split(command),
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    elapsed = round(time.perf_counter() - started, 4)
    emit(lines, "salida_pipeline", stdout=proc.stdout[-12000:])
    read_counts(lines, "despues")
    emit(lines, "fin_carga_completa", duracion_total_segundos=elapsed, exit_code=proc.returncode)
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
