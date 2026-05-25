"""
Medicion reproducible de rendimiento para SINIA-UY.

El script usa los Parquet procesados como fuente local estable. Si PostgreSQL o
MongoDB estan disponibles, el informe puede complementarse manualmente con las
consultas reales de motor, pero esta medicion permite defender tiempos de lectura,
agregacion analitica, carga incremental simulada e impacto de particionado logico.

Salida:
  reports/rendimiento_YYYYMMDD_HHMMSS.json
  reports/rendimiento_ultimo.json
"""

from __future__ import annotations

import json
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"


def _elapsed_ms(fn: Callable[[], Any], repeticiones: int = 3) -> dict[str, Any]:
    tiempos: list[float] = []
    resultado: Any = None
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        resultado = fn()
        tiempos.append((time.perf_counter() - inicio) * 1000)
    return {
        "ms_min": round(min(tiempos), 3),
        "ms_promedio": round(statistics.mean(tiempos), 3),
        "ms_max": round(max(tiempos), 3),
        "repeticiones": repeticiones,
        "resultado": resultado,
    }


def _leer_parquet(nombre: str) -> pd.DataFrame:
    return pd.read_parquet(DATA / nombre)


def medir() -> dict[str, Any]:
    REPORTS.mkdir(exist_ok=True)

    reporte: dict[str, Any] = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "entorno": {
            "python": platform.python_version(),
            "sistema": platform.platform(),
            "maquina": platform.machine(),
        },
        "archivos": {},
        "metricas": {},
        "sla": {
            "carga_completa_max_min": 15,
            "carga_incremental_max_min": 2,
            "consulta_analitica_max_ms": 3000,
            "actualizacion_minima": "diaria historica y cada 1-3 horas para NRT",
        },
    }

    for parquet in sorted(DATA.glob("*.parquet")):
        reporte["archivos"][parquet.name] = {
            "bytes": parquet.stat().st_size,
            "modificado": datetime.fromtimestamp(parquet.stat().st_mtime, timezone.utc).isoformat(),
        }

    dfs: dict[str, pd.DataFrame] = {}

    for nombre in [
        "firms_procesado.parquet",
        "meteo_procesado_todos.parquet",
        "cams_procesado_todos.parquet",
        "forecast_riesgo.parquet",
        "chirps_sa.parquet",
        "modis_lc.parquet",
    ]:
        clave = nombre.replace(".parquet", "")

        def cargar(nombre: str = nombre, clave: str = clave) -> int:
            dfs[clave] = _leer_parquet(nombre)
            return len(dfs[clave])

        reporte["metricas"][f"lectura_{clave}"] = _elapsed_ms(cargar, repeticiones=1)

    firms = dfs["firms_procesado"]
    meteo = dfs["meteo_procesado_todos"]
    cams = dfs["cams_procesado_todos"]

    reporte["metricas"]["q1_focos_por_mes"] = _elapsed_ms(
        lambda: int(
            firms.assign(mes=pd.to_datetime(firms["fecha_adq"]).dt.to_period("M"))
            .groupby("mes")
            .size()
            .shape[0]
        )
    )

    reporte["metricas"]["q2_ranking_dias_focos"] = _elapsed_ms(
        lambda: int(
            firms.groupby("fecha_adq")
            .size()
            .sort_values(ascending=False)
            .head(15)
            .sum()
        )
    )

    reporte["metricas"]["q3_riesgo_por_punto"] = _elapsed_ms(
        lambda: int(
            meteo[meteo["nivel_riesgo"].isin(["alto", "muy_alto"])]
            .groupby("punto")
            .size()
            .sum()
        )
    )

    reporte["metricas"]["q4_pm10_por_punto"] = _elapsed_ms(
        lambda: float(
            cams.groupby("punto")["pm10_media"]
            .mean()
            .sort_values(ascending=False)
            .head(1)
            .iloc[0]
        )
    )

    reporte["metricas"]["incremental_firms_ultimos_7_dias"] = _elapsed_ms(
        lambda: int(
            firms[
                pd.to_datetime(firms["fecha_adq"])
                >= (pd.to_datetime(firms["fecha_adq"]).max() - pd.Timedelta(days=7))
            ].drop_duplicates(["latitud", "longitud", "fecha_adq", "hora_adq_hhmm", "satelite"]).shape[0]
        )
    )

    reporte["metricas"]["simulacion_carga_doble_idempotente_firms"] = _elapsed_ms(
        lambda: int(
            pd.concat([firms.head(100_000), firms.head(100_000)], ignore_index=True)
            .drop_duplicates(["latitud", "longitud", "fecha_adq", "hora_adq_hhmm", "satelite"])
            .shape[0]
        )
    )

    return reporte


def main() -> None:
    reporte = medir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = REPORTS / f"rendimiento_{stamp}.json"
    ultimo = REPORTS / "rendimiento_ultimo.json"
    texto = json.dumps(reporte, ensure_ascii=False, indent=2)
    destino.write_text(texto, encoding="utf-8")
    ultimo.write_text(texto, encoding="utf-8")
    print(f"Reporte generado: {destino}")
    print(json.dumps({
        "consultas_medidas": len(reporte["metricas"]),
        "sla_consulta_ms": reporte["sla"]["consulta_analitica_max_ms"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
