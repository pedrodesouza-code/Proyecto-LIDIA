"""Mide consultas agregadas usadas por el dashboard Streamlit.

No ejecuta ETL ni lee archivos crudos. Usa PostgreSQL mediante config.settings
y emite EXPLAIN ANALYZE para consultas representativas del tablero.
"""

from __future__ import annotations

import time
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import PG_CONFIG

QUERIES = {
    "q1_ury_mensual": """
        SELECT pais_codigo, pais_nombre, anio, mes, focos, frp_promedio_mw, frp_total_mw
        FROM dw.mv_dashboard_focos_pais_periodo
        WHERE pais_codigo = 'URY' AND anio BETWEEN 2018 AND 2025
        ORDER BY anio, mes
    """,
    "q2_region_pais_anio": """
        SELECT pais_codigo, pais_nombre, anio, mes, focos, frp_promedio_mw, frp_total_mw
        FROM dw.mv_dashboard_focos_pais_periodo
        WHERE pais_codigo = ANY(ARRAY['URY','ARG','BRA']) AND anio BETWEEN 2018 AND 2025
        ORDER BY anio, mes, pais_codigo
    """,
    "q3_clima_ury": """
        SELECT pais_codigo, fecha, focos, frp_promedio_mw, temperatura_media_c, humedad_media_pct
        FROM dw.v_incendios_clima
        WHERE pais_codigo = 'URY'
          AND EXTRACT(YEAR FROM fecha) BETWEEN 2018 AND 2025
          AND temperatura_media_c IS NOT NULL
        ORDER BY fecha
    """,
    "q6_precipitacion": """
        SELECT pais_codigo, anio, mes, focos, precipitacion_mm_promedio
        FROM dw.mv_dashboard_incendios_precipitacion
        WHERE pais_codigo = ANY(ARRAY['URY','ARG','BRA']) AND anio BETWEEN 2018 AND 2025
        ORDER BY anio, mes, pais_codigo
    """,
    "q8_zona_espacial_ury": """
        SELECT zona_espacial, latitud_grilla, longitud_grilla, cantidad_focos, frp_promedio_mw
        FROM dw.v_focos_zona_espacial_ury
        ORDER BY cantidad_focos DESC
        LIMIT 20
    """,
    "q10_rechazos": """
        SELECT fuente, motivo, COUNT(*)::bigint AS rechazos, MAX(rechazado_en) AS ultimo_rechazo
        FROM staging.rechazos_etl
        GROUP BY fuente, motivo
        ORDER BY rechazos DESC, fuente, motivo
        LIMIT 30
    """,
}


def main() -> int:
    output = []
    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '60s'")
            for name, sql in QUERIES.items():
                print(f"=== {name} ===", flush=True)
                output.append(f"=== {name} ===")
                start = time.perf_counter()
                try:
                    cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) " + sql)
                    elapsed = time.perf_counter() - start
                    lines = [row[0] for row in cur.fetchall()]
                    print(f"elapsed_python_seconds={elapsed:.4f}", flush=True)
                    output.append(f"elapsed_python_seconds={elapsed:.4f}")
                    output.extend(lines)
                except Exception as exc:
                    elapsed = time.perf_counter() - start
                    conn.rollback()
                    with conn.cursor() as reset_cur:
                        reset_cur.execute("SET statement_timeout = '60s'")
                    message = f"query_error={type(exc).__name__}: {exc}"
                    print(f"elapsed_python_seconds={elapsed:.4f}", flush=True)
                    print(message, flush=True)
                    output.append(f"elapsed_python_seconds={elapsed:.4f}")
                    output.append(message)
                output.append("")
    text = "\n".join(output)
    print(text)
    log = ROOT / "evidencia" / "logs" / "dashboard_performance_after.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
