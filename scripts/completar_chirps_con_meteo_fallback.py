"""
Completa precipitacion mensual faltante usando Open-Meteo historico.

CHIRPS ClimateSERV puede quedar colgado o rechazar requests puntuales. Para que
la tabla mensual quede completa por punto, este script agrega precipitation_sum
diaria desde meteo_procesado_todos.parquet y la concatena en chirps_sa.parquet
solo para puntos sin CHIRPS.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import json
import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DIR_PROCESADO, PUNTOS_METEO_SA


REPORTS = Path("reports")


def main() -> int:
    meteo_path = DIR_PROCESADO / "meteo_procesado_todos.parquet"
    chirps_path = DIR_PROCESADO / "chirps_sa.parquet"

    meteo = pd.read_parquet(meteo_path)
    chirps = pd.read_parquet(chirps_path) if chirps_path.exists() else pd.DataFrame()

    puntos_objetivo = set(PUNTOS_METEO_SA)
    puntos_chirps = set(chirps["punto"].dropna().astype(str)) if "punto" in chirps else set()
    faltantes = sorted(puntos_objetivo - puntos_chirps)

    meteo["fecha"] = pd.to_datetime(meteo["fecha"])
    base = meteo[
        meteo["punto"].isin(faltantes)
        & meteo["fecha"].dt.year.between(2018, 2024)
    ].copy()

    if base.empty:
        nuevos = pd.DataFrame(columns=chirps.columns if not chirps.empty else [])
    else:
        base["anio"] = base["fecha"].dt.year
        base["mes"] = base["fecha"].dt.month
        nuevos = (
            base.groupby(["punto", "anio", "mes"], as_index=False)["precipitation_sum"]
            .sum()
            .rename(columns={"precipitation_sum": "precipitacion_mm"})
        )
        nuevos["pais"] = nuevos["punto"].map(lambda p: PUNTOS_METEO_SA[p]["pais"])
        nuevos["fecha"] = pd.to_datetime(
            nuevos["anio"].astype(str) + "-" + nuevos["mes"].astype(str).str.zfill(2) + "-01"
        )
        nuevos["fuente"] = "Open-Meteo mensual fallback"
        nuevos["anio_mes"] = nuevos["fecha"].dt.to_period("M").astype(str)
        nuevos = nuevos[["punto", "pais", "fecha", "precipitacion_mm", "fuente", "anio", "mes", "anio_mes"]]

    consolidado = pd.concat([chirps, nuevos], ignore_index=True)
    consolidado = consolidado.drop_duplicates(subset=["punto", "anio", "mes"], keep="last")
    consolidado.to_parquet(chirps_path, index=False)

    puntos_final = set(consolidado["punto"].dropna().astype(str))
    reporte = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "fuente_fallback": "Open-Meteo Archive agregado mensual",
        "puntos_faltantes_entrada": faltantes,
        "filas_agregadas": int(len(nuevos)),
        "puntos_consolidados": int(len(puntos_final)),
        "puntos_faltantes_salida": sorted(puntos_objetivo - puntos_final),
    }
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / "chirps_fallback_openmeteo_ultimo.json"
    path.write_text(json.dumps(reporte, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(reporte, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
