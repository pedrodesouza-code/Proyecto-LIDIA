"""Evidencia no destructiva de CDC incremental.

Este script no inserta datos nuevos ni modifica tablas productivas. Resume la
evidencia disponible en audit.cdc_eventos y valida duplicados por natural_key.
Si no hay eventos suficientes, lo deja documentado en el log.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import PG_CONFIG  # noqa: E402

LOG_PATH = ROOT / "evidencia" / "logs" / "cdc_smoke_incremental_final.log"


def emit(lines: list[str], message: str, **payload: object) -> None:
    event = {"timestamp": datetime.now(timezone.utc).isoformat(), "message": message, **payload}
    text = json.dumps(event, ensure_ascii=False, default=str)
    print(text, flush=True)
    lines.append(text)


def scalar(cur, query: str) -> int:
    cur.execute(query)
    row = cur.fetchone()
    return int(row[0] or 0)


def existing_column(cur, table_schema: str, table_name: str, candidates: tuple[str, ...]) -> str | None:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
          AND column_name = ANY(%s)
        """,
        (table_schema, table_name, list(candidates)),
    )
    existing = {row[0] for row in cur.fetchall()}
    for candidate in candidates:
        if candidate in existing:
            return candidate
    return None


def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    emit(lines, "inicio_cdc_smoke_incremental", modo="no_destructivo")
    try:
        with psycopg2.connect(**PG_CONFIG) as conn:
            with conn.cursor() as cur:
                fact_count = scalar(cur, "SELECT COUNT(*) FROM dw.fact_incendio")
                duplicate_count = scalar(
                    cur,
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT natural_key
                        FROM dw.fact_incendio
                        GROUP BY natural_key
                        HAVING COUNT(*) > 1
                    ) d
                    """,
                )
                emit(lines, "conteos_fact_incendio", total=fact_count, duplicados_natural_key=duplicate_count)
                cur.execute(
                    """
                    SELECT fuente, tipo_evento, COUNT(*)::bigint
                    FROM audit.cdc_eventos
                    GROUP BY fuente, tipo_evento
                    ORDER BY fuente, tipo_evento
                    """
                )
                rows = [{"fuente": r[0], "tipo_evento": r[1], "eventos": r[2]} for r in cur.fetchall()]
                emit(lines, "eventos_cdc_por_fuente_tipo", resultado=rows)
                timestamp_column = existing_column(
                    cur,
                    "audit",
                    "cdc_eventos",
                    ("creado_en", "registrado_en", "procesado_en", "created_at", "fecha_evento"),
                )
                order_expr = timestamp_column or "run_id"
                select_timestamp = timestamp_column or "NULL"
                cur.execute(
                    f"""
                    SELECT run_id, fuente, tipo_evento, record_hash, {select_timestamp} AS evento_ts
                    FROM audit.cdc_eventos
                    ORDER BY {order_expr} DESC
                    LIMIT 20
                    """
                )
                sample = [
                    {"run_id": r[0], "fuente": r[1], "tipo_evento": r[2], "record_hash": r[3], "evento_ts": r[4]}
                    for r in cur.fetchall()
                ]
                emit(lines, "ultimos_eventos_cdc", resultado=sample)
                observed = {row["tipo_evento"] for row in rows}
                required = {"alta", "modificacion", "sin_cambio"}
                missing = sorted(required - observed)
                if missing:
                    emit(lines, "cdc_evidencia_parcial", faltantes=missing)
                else:
                    emit(lines, "cdc_evidencia_completa", eventos_requeridos=sorted(required))
    except Exception as exc:  # noqa: BLE001
        emit(lines, "error_cdc_smoke_incremental", error=f"{type(exc).__name__}: {exc}")
        LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return 1
    emit(lines, "fin_cdc_smoke_incremental", estado="OK")
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
