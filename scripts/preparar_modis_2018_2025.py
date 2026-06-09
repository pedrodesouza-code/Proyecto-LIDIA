"""Prepara MODIS cobertura vegetal/uso del suelo 2018-2025 con datos reales locales."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
LOG_DIR = ROOT / "evidencia" / "logs"
ALLOWED_COUNTRIES = {"URY", "ARG", "BRA"}

SOURCE_CANDIDATES = [
    Path("/home/pepo/Datos completos/MODIS/modis_lc_type1_lidia_ury_arg_bra.csv"),
    Path("/home/pepo/Datos completos/MODIS/modis_arg_bra_2018_2021_zenodo.csv"),
    Path("/home/pepo/Datos completos/MODIS/modis_todos.csv"),
    PROCESSED_DIR / "modis_lc.parquet",
]

LC_DESCRIPTIONS = {
    1: "Bosque perenne de coniferas",
    2: "Bosque perenne latifoliado",
    3: "Bosque deciduo de coniferas",
    4: "Bosque deciduo latifoliado",
    5: "Bosque mixto",
    6: "Matorral cerrado",
    7: "Matorral abierto",
    8: "Sabana lenosa",
    9: "Sabana",
    10: "Pastizal",
    11: "Humedal permanente",
    12: "Cultivos",
    13: "Urbano y construido",
    14: "Mosaico cultivos/vegetacion natural",
    15: "Nieve y hielo",
    16: "Suelo desnudo o vegetacion escasa",
    17: "Agua",
}


def read_source(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def infer_year_from_file(value: object) -> int | None:
    text = str(value or "")
    match = None
    import re

    for pattern in (r"doy(20\d{2})", r"(20\d{2})"):
        match = re.search(pattern, text)
        if match:
            break
    return int(match.group(1)) if match else None


def normalize_modis(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    if "anio" not in output.columns:
        output["anio"] = output.get("archivo", "").map(infer_year_from_file)
    if "pais_codigo" not in output.columns:
        if "pais" in output.columns:
            output["pais_codigo"] = output["pais"]
        else:
            output["pais_codigo"] = ""
    if "ubicacion" not in output.columns:
        output["ubicacion"] = output.get("punto", "")
    if "latitud" not in output.columns:
        output["latitud"] = output.get("lat")
    if "longitud" not in output.columns:
        output["longitud"] = output.get("lon")
    if "codigo_cobertura" not in output.columns:
        output["codigo_cobertura"] = output.get("lc_type1", output.get("valor"))
    if "descripcion_cobertura" not in output.columns:
        output["descripcion_cobertura"] = output.get("lc_descripcion")
    output["anio"] = pd.to_numeric(output["anio"], errors="coerce").astype("Int64")
    output["pais_codigo"] = output["pais_codigo"].astype(str).str.upper()
    output["ubicacion"] = output["ubicacion"].astype(str).str.replace(" ", "_")
    output["latitud"] = pd.to_numeric(output["latitud"], errors="coerce")
    output["longitud"] = pd.to_numeric(output["longitud"], errors="coerce")
    output["codigo_cobertura"] = pd.to_numeric(output["codigo_cobertura"], errors="coerce").astype("Int64")
    output["descripcion_cobertura"] = output["descripcion_cobertura"].fillna(
        output["codigo_cobertura"].map(lambda value: LC_DESCRIPTIONS.get(int(value), None) if pd.notna(value) else None)
    )
    output["fuente"] = "MODIS"
    cols = [
        "anio",
        "pais_codigo",
        "ubicacion",
        "latitud",
        "longitud",
        "codigo_cobertura",
        "descripcion_cobertura",
        "fuente",
    ]
    output = output[cols].copy()
    output = output[
        output["anio"].between(2018, 2025)
        & output["pais_codigo"].isin(ALLOWED_COUNTRIES)
        & output["ubicacion"].ne("")
    ].copy()
    return output.drop_duplicates(subset=["anio", "pais_codigo", "ubicacion", "latitud", "longitud"], keep="last")


def audit_frame(path: Path, frame: pd.DataFrame) -> dict[str, Any]:
    year_col = next((col for col in ("anio", "year") if col in frame.columns), None)
    country_col = next((col for col in ("pais_codigo", "pais", "country") if col in frame.columns), None)
    return {
        "ruta": str(path),
        "filas": int(len(frame)),
        "columnas": list(map(str, frame.columns)),
        "anio_min": int(pd.to_numeric(frame[year_col], errors="coerce").min()) if year_col else None,
        "anio_max": int(pd.to_numeric(frame[year_col], errors="coerce").max()) if year_col else None,
        "conteo_anios": {
            str(k): int(v) for k, v in pd.to_numeric(frame[year_col], errors="coerce").value_counts().sort_index().to_dict().items()
        }
        if year_col
        else {},
        "conteo_paises": {
            str(k).upper(): int(v)
            for k, v in frame[country_col].astype(str).str.upper().value_counts().sort_index().to_dict().items()
        }
        if country_col
        else {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara MODIS 2018-2025 desde archivos locales reales.")
    parser.add_argument("--output", default=str(PROCESSED_DIR / "modis_2018_2025.parquet"))
    parser.add_argument("--log", default=str(LOG_DIR / "preparacion_modis_2018_2025.log"))
    args = parser.parse_args()

    sources = [path for path in SOURCE_CANDIDATES if path.exists()]
    audits = []
    normalized_frames = []
    for path in sources:
        frame = read_source(path)
        audits.append(audit_frame(path, frame))
        normalized = normalize_modis(frame)
        if len(normalized):
            normalized_frames.append(normalized)

    if normalized_frames:
        combined = pd.concat(normalized_frames, ignore_index=True)
        combined = combined.drop_duplicates(subset=["anio", "pais_codigo", "ubicacion", "latitud", "longitud"], keep="first")
    else:
        combined = pd.DataFrame(
            columns=["anio", "pais_codigo", "ubicacion", "latitud", "longitud", "codigo_cobertura", "descripcion_cobertura", "fuente"]
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    backup = output.with_name("modis_2018_2025_before_review.parquet")
    if output.exists() and not backup.exists():
        pd.read_parquet(output).to_parquet(backup, index=False)
    combined.to_parquet(output, index=False)

    result = {
        "estado": "ok",
        "fuente": "MODIS",
        "archivos_modis_encontrados": [str(path) for path in sources],
        "auditorias": audits,
        "archivo_final": str(output),
        "filas_finales": int(len(combined)),
        "anios_finales": sorted(int(value) for value in combined["anio"].dropna().unique().tolist()),
        "conteo_anios_final": {str(k): int(v) for k, v in combined["anio"].value_counts().sort_index().to_dict().items()},
        "conteo_paises_final": {str(k): int(v) for k, v in combined["pais_codigo"].value_counts().sort_index().to_dict().items()},
        "hay_2025": bool((combined["anio"] == 2025).any()),
        "hay_uruguay": bool((combined["pais_codigo"] == "URY").any()),
        "pendientes_reales": [],
        "nota": "No se generan coberturas sinteticas; solo se consolidan archivos MODIS locales reales.",
    }
    if not result["hay_2025"]:
        result["pendientes_reales"].append("MODIS 2025 no disponible localmente")
    if not result["hay_uruguay"]:
        result["pendientes_reales"].append("MODIS Uruguay no disponible localmente")
    log = Path(args.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
