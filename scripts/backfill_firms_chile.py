"""
Backfill especifico de NASA FIRMS para Chile.

El historico principal ya tenia focos para BRA/ARG/URY. Este script descarga
FIRMS sobre un bbox chileno, transforma, consolida en firms_procesado.parquet
y carga PostgreSQL.
"""

from __future__ import annotations

import io
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DIR_PROCESADO, FIRMS_BASE_URL, FIRMS_MAP_KEY
from etl.load.load_postgres import cargar_focos_calor
from etl.transform.transform_firms import transformar_firms


CHILE_BBOX = "-75.7,-56.0,-66.4,-17.5"
SENSOR = "VIIRS_SNPP_SP"
FECHA_INICIO = "2024-01-01"
FECHA_FIN = "2026-05-15"
CHUNK_DIAS = 5
PAUSA_SEG = 0.35


def descargar_firms_chile() -> tuple[pd.DataFrame, dict[str, str]]:
    inicio = datetime.fromisoformat(FECHA_INICIO).date()
    fin = datetime.fromisoformat(FECHA_FIN).date()
    actual = inicio
    frames = []
    errores: dict[str, str] = {}

    while actual <= fin:
        dias = min(CHUNK_DIAS, (fin - actual).days + 1)
        url = f"{FIRMS_BASE_URL}/{FIRMS_MAP_KEY}/{SENSOR}/{CHILE_BBOX}/{dias}/{actual.isoformat()}"
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            texto = resp.text.strip()
            if texto and not texto.startswith("Invalid"):
                df = pd.read_csv(io.StringIO(texto))
                if not df.empty and "latitude" in df.columns:
                    frames.append(df)
                    print(f"{actual} +{dias}d -> {len(df)} filas")
        except Exception as exc:
            errores[f"{actual.isoformat()}:{dias}"] = str(exc)
            print(f"{actual} +{dias}d -> ERROR {exc}")
        actual += timedelta(days=dias)
        time.sleep(PAUSA_SEG)

    crudo = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return crudo, errores


def main() -> int:
    crudo, errores = descargar_firms_chile()
    procesado = transformar_firms(crudo, guardar=False) if not crudo.empty else pd.DataFrame()
    if not procesado.empty and "pais" in procesado.columns:
        procesado = procesado[procesado["pais"] == "CHL"].copy()

    path = DIR_PROCESADO / "firms_procesado.parquet"
    previo = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    consolidado = pd.concat([previo, procesado], ignore_index=True)
    claves = ["latitud", "longitud", "fecha_adq", "hora_adq_hhmm", "satelite"]
    consolidado = consolidado.drop_duplicates(subset=[c for c in claves if c in consolidado.columns], keep="last")
    consolidado.to_parquet(path, index=False)

    postgres = cargar_focos_calor(procesado) if not procesado.empty else {
        "insertados": 0,
        "actualizados": 0,
        "sin_cambio": 0,
        "errores": 0,
    }
    reporte = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "sensor": SENSOR,
        "bbox": CHILE_BBOX,
        "fecha_inicio": FECHA_INICIO,
        "fecha_fin": FECHA_FIN,
        "crudo_filas": int(len(crudo)),
        "chile_procesado_filas": int(len(procesado)),
        "consolidado_filas": int(len(consolidado)),
        "consolidado_por_pais": consolidado["pais"].value_counts(dropna=False).to_dict() if "pais" in consolidado.columns else {},
        "errores": errores,
        "postgres": postgres,
    }
    Path("reports").mkdir(exist_ok=True)
    for p in [Path("reports/firms_chile_backfill_ultimo.json"), Path("reports/firms_chile_backfill_20260519.json")]:
        p.write_text(json.dumps(reporte, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(reporte, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
