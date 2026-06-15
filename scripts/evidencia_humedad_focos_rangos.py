"""Genera evidencia de focos por rangos de humedad relativa en Uruguay."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import PG_CONFIG  # noqa: E402

LOG_PATH = ROOT / "evidencia" / "logs" / "humedad_focos_rangos_final.log"


def emit(lines: list[str], message: str, **payload: object) -> None:
    event = {"timestamp": datetime.now(timezone.utc).isoformat(), "message": message, **payload}
    text = json.dumps(event, ensure_ascii=False, default=str)
    print(text, flush=True)
    lines.append(text)


def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    emit(lines, "inicio_humedad_focos_rangos")
    try:
        with psycopg2.connect(**PG_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'dw'
                      AND table_name = 'v_incendios_clima'
                    ORDER BY ordinal_position
                    """
                )
                columns = [row[0] for row in cur.fetchall()]
                emit(lines, "columnas_v_incendios_clima", columnas=columns)
                required = {"pais_codigo", "humedad_media_pct", "focos"}
                missing = sorted(required - set(columns))
                if missing:
                    emit(lines, "error_columnas_faltantes", faltantes=missing)
                    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    return 1
                cur.execute(
                    """
                    WITH base AS (
                        SELECT
                            focos,
                            humedad_media_pct,
                            frp_promedio_mw,
                            CASE
                                WHEN humedad_media_pct IS NULL THEN 'Sin dato'
                                WHEN humedad_media_pct < 40 THEN 'Baja humedad (<40%)'
                                WHEN humedad_media_pct <= 70 THEN 'Humedad media (40%-70%)'
                                ELSE 'Alta humedad (>70%)'
                            END AS rango_humedad,
                            CASE
                                WHEN humedad_media_pct IS NULL THEN 4
                                WHEN humedad_media_pct < 40 THEN 1
                                WHEN humedad_media_pct <= 70 THEN 2
                                ELSE 3
                            END AS orden_rango
                        FROM dw.v_incendios_clima
                        WHERE pais_codigo = 'URY'
                    )
                    SELECT
                        rango_humedad,
                        COUNT(*)::bigint AS periodos,
                        COALESCE(SUM(focos), 0)::bigint AS focos,
                        ROUND(AVG(humedad_media_pct), 2) AS humedad_promedio_pct,
                        ROUND(AVG(frp_promedio_mw), 2) AS frp_promedio_mw
                    FROM base
                    GROUP BY rango_humedad, orden_rango
                    ORDER BY orden_rango
                    """
                )
                rows = [
                    {
                        "rango_humedad": row[0],
                        "periodos": row[1],
                        "focos": row[2],
                        "humedad_promedio_pct": row[3],
                        "frp_promedio_mw": row[4],
                    }
                    for row in cur.fetchall()
                ]
                emit(lines, "resultado_humedad_focos_rangos", filas=rows)
    except Exception as exc:  # noqa: BLE001
        emit(lines, "error_humedad_focos_rangos", error=f"{type(exc).__name__}: {exc}")
        LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return 1
    emit(lines, "fin_humedad_focos_rangos", estado="OK")
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
