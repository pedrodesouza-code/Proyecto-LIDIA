"""Genera evidencia de refresh de materialized views del dashboard.

No modifica el modelo de datos. Solo ejecuta REFRESH MATERIALIZED VIEW sobre
objetos analiticos ya definidos en el esquema dw y registra duraciones.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import PG_CONFIG  # noqa: E402

LOG_PATH = ROOT / "evidencia" / "logs" / "refresh_materialized_views_final.log"
VIEWS = (
    "dw.mv_dashboard_focos_pais_periodo",
    "dw.mv_dashboard_incendios_precipitacion",
)


def log_line(lines: list[str], message: str, **payload: object) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
        **payload,
    }
    text = json.dumps(event, ensure_ascii=False, default=str)
    print(text, flush=True)
    lines.append(text)


def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    started = time.perf_counter()
    log_line(lines, "inicio_refresh_materialized_views", views=list(VIEWS))
    status = "OK"
    exit_code = 0
    try:
        with psycopg2.connect(**PG_CONFIG) as conn:
            with conn.cursor() as cur:
                for view in VIEWS:
                    view_start = time.perf_counter()
                    query = f"REFRESH MATERIALIZED VIEW {view}"
                    log_line(lines, "query_inicio", query=query)
                    cur.execute(query)
                    log_line(
                        lines,
                        "query_fin",
                        query=query,
                        duracion_segundos=round(time.perf_counter() - view_start, 4),
                    )
                cur.execute(
                    """
                    SELECT 'dw.mv_dashboard_focos_pais_periodo' AS objeto, COUNT(*)::bigint
                    FROM dw.mv_dashboard_focos_pais_periodo
                    UNION ALL
                    SELECT 'dw.mv_dashboard_incendios_precipitacion' AS objeto, COUNT(*)::bigint
                    FROM dw.mv_dashboard_incendios_precipitacion
                    ORDER BY objeto
                    """
                )
                for objeto, filas in cur.fetchall():
                    log_line(lines, "conteo_materialized_view", objeto=objeto, filas=filas)
    except Exception as exc:  # noqa: BLE001
        status = "ERROR"
        exit_code = 1
        log_line(lines, "error_refresh_materialized_views", error=f"{type(exc).__name__}: {exc}")
    total = round(time.perf_counter() - started, 4)
    log_line(lines, "fin_refresh_materialized_views", estado=status, duracion_total_segundos=total, exit_code=exit_code)
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
