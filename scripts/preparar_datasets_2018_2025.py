"""Prepara datasets procesados EC3 para el periodo 2018-2025.

El script no borra archivos originales. Lee fuentes locales disponibles,
filtra el periodo analitico 2018-01-01 a 2025-12-31 y restringe paises a
URY, ARG y BRA cuando puede inferir o leer el pais. Los archivos NRT se
excluyen como fuente principal.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
LOG_DIR = ROOT / "evidencia" / "logs"
START = pd.Timestamp("2018-01-01", tz="UTC")
END = pd.Timestamp("2025-12-31 23:59:59", tz="UTC")
ALLOWED_COUNTRIES = {"URY", "ARG", "BRA"}

COUNTRY_ALIASES = {
    "UY": "URY",
    "URUGUAY": "URY",
    "AR": "ARG",
    "ARGENTINA": "ARG",
    "BR": "BRA",
    "BRASIL": "BRA",
    "BRAZIL": "BRA",
}

POINT_COUNTRY = {
    # Uruguay
    "montevideo": "URY",
    "artigas": "URY",
    "canelones": "URY",
    "maldonado": "URY",
    "rocha": "URY",
    "treinta_y_tres": "URY",
    "cerro_largo": "URY",
    "rivera": "URY",
    "salto": "URY",
    "paysandu": "URY",
    "paysandú": "URY",
    "rio_negro": "URY",
    "soriano": "URY",
    "colonia": "URY",
    "colonia_del_sacramento": "URY",
    "san_jose": "URY",
    "san_josé": "URY",
    "flores": "URY",
    "florida": "URY",
    "durazno": "URY",
    "lavalleja": "URY",
    "tacuarembo": "URY",
    "tacuarembó": "URY",
    "melo": "URY",
    # Argentina
    "buenos_aires": "ARG",
    "mendoza": "ARG",
    "posadas": "ARG",
    "salta": "ARG",
    "misiones": "ARG",
    "corrientes": "ARG",
    "chaco": "ARG",
    "formosa": "ARG",
    "santiago_del_estero": "ARG",
    # Brasil
    "brasilia": "BRA",
    "brasília": "BRA",
    "campo_grande": "BRA",
    "cuiaba": "BRA",
    "cuiabá": "BRA",
    "manaus": "BRA",
    "porto_alegre": "BRA",
    "rio_grande_do_sul": "BRA",
    "santa_catarina": "BRA",
    "parana": "BRA",
    "paraná": "BRA",
    "uruguaiana": "BRA",
    "pelotas": "BRA",
    "caxias_do_sul": "BRA",
}


@dataclass
class PreparationResult:
    source: str
    input_file: str | None
    output_file: str | None
    rows_in: int
    rows_out: int
    date_min: str | None
    date_max: str | None
    countries: dict[str, int]
    status: str
    notes: list[str]


def point_key(value: object) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def normalize_country(value: object) -> str:
    raw = str(value or "").strip().upper()
    return COUNTRY_ALIASES.get(raw, raw)


def infer_country_frame(frame: pd.DataFrame) -> pd.Series:
    for column in ("pais_codigo", "pais", "country"):
        if column in frame.columns:
            return frame[column].map(normalize_country)
    for column in ("ubicacion", "punto", "location", "estacion"):
        if column in frame.columns:
            return frame[column].map(lambda value: POINT_COUNTRY.get(point_key(value), ""))
    return pd.Series([""] * len(frame), index=frame.index)


def date_series(frame: pd.DataFrame, candidates: Iterable[str]) -> tuple[str | None, pd.Series | None]:
    for column in candidates:
        if column in frame.columns:
            if column in {"anio", "year"}:
                values = pd.to_numeric(frame[column], errors="coerce")
                parsed = pd.to_datetime(values.astype("Int64").astype(str) + "-01-01", errors="coerce", utc=True)
            else:
                parsed = pd.to_datetime(frame[column], errors="coerce", utc=True)
            return column, parsed
    return None, None


def filter_period(frame: pd.DataFrame, candidates: Iterable[str]) -> tuple[pd.DataFrame, str | None, list[str]]:
    notes: list[str] = []
    column, parsed = date_series(frame, candidates)
    if column is None or parsed is None:
        notes.append("sin_columna_temporal_detectada")
        return frame.copy(), None, notes
    mask = parsed.between(START, END)
    filtered = frame.loc[mask].copy()
    notes.append(f"filtro_temporal_columna={column}")
    return filtered, column, notes


def filter_countries(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int], list[str]]:
    notes: list[str] = []
    countries = infer_country_frame(frame)
    counts_all = countries.value_counts(dropna=False).to_dict()
    if not len(frame):
        return frame.copy(), {}, notes
    if countries.eq("").all():
        notes.append("sin_pais_inferible_no_se_filtra_por_pais")
        return frame.copy(), {str(k): int(v) for k, v in counts_all.items()}, notes
    output = frame.loc[countries.isin(ALLOWED_COUNTRIES)].copy()
    output["pais_codigo"] = countries.loc[output.index].values
    removed = int(len(frame) - len(output))
    if removed:
        notes.append(f"paises_fuera_alcance_removidos={removed}")
    return output, {str(k): int(v) for k, v in countries.loc[output.index].value_counts().to_dict().items()}, notes


def filter_inumet_uruguay(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int], list[str]]:
    countries = infer_country_frame(frame)
    output = frame.loc[countries.eq("URY")].copy()
    if len(output):
        output["pais_codigo"] = "URY"
    removed = int(len(frame) - len(output))
    notes = [f"inumet_fuera_uruguay_removidos={removed}"] if removed else []
    return output, {"URY": int(len(output))} if len(output) else {}, notes


def read_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def summarize_dates(frame: pd.DataFrame, candidates: Iterable[str]) -> tuple[str | None, str | None]:
    _, parsed = date_series(frame, candidates)
    if parsed is None:
        return None, None
    valid = parsed.dropna()
    if valid.empty:
        return None, None
    return valid.min().date().isoformat(), valid.max().date().isoformat()


def find_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def maybe_env_path(name: str) -> Path | None:
    value = os.getenv(name, "").strip().strip('"')
    return Path(value).expanduser() if value else None


def firms_candidates() -> list[Path]:
    explicit = maybe_env_path("LIDIA_FIRMS_HISTORICO_FILE")
    candidates = []
    if explicit:
        candidates.append(explicit)
    candidates.extend(
        [
            ROOT / "data" / "raw" / "firms" / "firms_shapefile_2018_2025.parquet",
            DATA_DIR / "firms_shapefile_2018_2025.parquet",
            DATA_DIR / "firms_procesado.parquet",
            DATA_DIR / "firms_nrt_procesado.parquet",
        ]
    )
    candidates.extend(Path("/home/pepo").glob("**/*firms*2018*2025*.parquet"))
    return candidates


def prepare_source(source: str, input_path: Path | None, output_path: Path, date_candidates: list[str]) -> PreparationResult:
    if input_path is None or not input_path.exists():
        return PreparationResult(source, None, None, 0, 0, None, None, {}, "pendiente", ["archivo_base_no_disponible"])
    frame = read_parquet(input_path)
    rows_in = len(frame)
    filtered, _, notes = filter_period(frame, date_candidates)
    if source == "INUMET":
        filtered, countries, country_notes = filter_inumet_uruguay(filtered)
    else:
        filtered, countries, country_notes = filter_countries(filtered)
    notes.extend(country_notes)
    if source == "FIRMS" and "sin_pais_inferible_no_se_filtra_por_pais" in notes:
        return PreparationResult(
            source,
            str(input_path),
            None,
            rows_in,
            0,
            None,
            None,
            countries,
            "pendiente",
            notes + ["FIRMS_requiere_pais_codigo_o_clasificacion_geografica_para_filtrar_URY_ARG_BRA"],
        )
    date_min, date_max = summarize_dates(filtered, date_candidates)
    write_parquet(filtered, output_path)
    status = "ok" if len(filtered) else "sin_filas"
    if date_min and date_min > "2018-01-01":
        notes.append(f"{source}_incompleto_faltan_anios_iniciales")
        status = "parcial"
    if date_max and date_max < "2025-12-31":
        notes.append(f"{source}_incompleto_faltan_anios_finales")
        status = "parcial"
    if source == "MODIS" and "URY" not in countries:
        notes.append("MODIS_sin_uruguay_en_fuente_local")
        status = "parcial"
    if source == "FIRMS" and "nrt" in input_path.name.lower():
        notes.append("origen_nrt_no_recomendado_como_principal")
        status = "parcial"
    return PreparationResult(source, str(input_path), str(output_path), rows_in, len(filtered), date_min, date_max, countries, status, notes)


def update_env_file(results: list[PreparationResult]) -> None:
    env_path = ROOT / "config" / ".env"
    mapping = {
        "FIRMS": "FIRMS_FILE",
        "CAMS": "CAMS_FILE",
        "CHIRPS": "CHIRPS_FILE",
        "METEO": "METEO_FILE",
        "INUMET": "INUMET_FILE",
        "MODIS": "MODIS_FILE",
    }
    if not env_path.exists():
        return
    lines = env_path.read_text(encoding="utf-8").splitlines()
    values = {
        mapping[result.source]: result.output_file
        for result in results
        if result.output_file and result.rows_out > 0 and result.source in mapping
    }
    existing = {line.split("=", 1)[0] for line in lines if "=" in line}
    output_lines = []
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line else ""
        if key in values:
            output_lines.append(f'{key}="{values[key]}"')
        else:
            output_lines.append(line)
    for key, value in values.items():
        if key not in existing:
            output_lines.append(f'{key}="{value}"')
    env_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")


def result_to_dict(result: PreparationResult) -> dict:
    return {
        "source": result.source,
        "input_file": result.input_file,
        "output_file": result.output_file,
        "rows_in": result.rows_in,
        "rows_out": result.rows_out,
        "date_min": result.date_min,
        "date_max": result.date_max,
        "countries": result.countries,
        "status": result.status,
        "notes": result.notes,
    }


def write_log(results: list[PreparationResult], path: Path) -> None:
    lines = ["# Preparacion datasets 2018-2025", ""]
    lines.append("| fuente | estado | filas entrada | filas salida | desde | hasta | salida | notas |")
    lines.append("|---|---|---:|---:|---|---|---|---|")
    for result in results:
        lines.append(
            "| {source} | {status} | {rows_in} | {rows_out} | {date_min} | {date_max} | {output_file} | {notes} |".format(
                source=result.source,
                status=result.status,
                rows_in=result.rows_in,
                rows_out=result.rows_out,
                date_min=result.date_min or "-",
                date_max=result.date_max or "-",
                output_file=result.output_file or "-",
                notes=", ".join(result.notes) or "-",
            )
        )
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps([result_to_dict(result) for result in results], ensure_ascii=False, indent=2))
    lines.append("```")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare_all(update_env: bool = True) -> list[PreparationResult]:
    results = [
        prepare_source(
            "FIRMS",
            find_existing(firms_candidates()),
            DATA_DIR / "firms_2018_2025.parquet",
            ["fecha_adq", "acq_date", "fecha", "date"],
        ),
        prepare_source(
            "CAMS",
            find_existing([DATA_DIR / "cams_procesado_todos.parquet"]),
            DATA_DIR / "cams_2018_2025.parquet",
            ["fecha", "fecha_hora_utc", "date", "time"],
        ),
        prepare_source(
            "CHIRPS",
            find_existing([DATA_DIR / "chirps_sa.parquet"]),
            DATA_DIR / "chirps_2018_2025.parquet",
            ["fecha", "date", "anio"],
        ),
        prepare_source(
            "METEO",
            find_existing([DATA_DIR / "meteo_procesado_todos.parquet"]),
            DATA_DIR / "meteo_2018_2025.parquet",
            ["fecha", "fecha_hora_utc", "date", "time"],
        ),
        prepare_source(
            "INUMET",
            find_existing([DATA_DIR / "inumet_procesado.parquet"]),
            DATA_DIR / "inumet_2018_2025.parquet",
            ["fecha_hora_utc", "fecha", "date"],
        ),
        prepare_source(
            "MODIS",
            find_existing([DATA_DIR / "modis_lc.parquet"]),
            DATA_DIR / "modis_2018_2025.parquet",
            ["anio", "year"],
        ),
    ]
    if update_env:
        update_env_file(results)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara datasets Proyecto LIDIA EC3 2018-2025.")
    parser.add_argument("--no-update-env", action="store_true", help="No actualiza config/.env local.")
    parser.add_argument("--log", default=str(LOG_DIR / "preparacion_datasets_2018_2025.log"))
    args = parser.parse_args()
    results = prepare_all(update_env=not args.no_update_env)
    write_log(results, Path(args.log))
    print(json.dumps([result_to_dict(result) for result in results], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
