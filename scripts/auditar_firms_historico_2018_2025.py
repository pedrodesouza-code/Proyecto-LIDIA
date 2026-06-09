"""Audita candidatos FIRMS historicos para EC3 2018-2025.

El script no modifica datos. Busca Parquet FIRMS disponibles, resume cobertura
temporal y paises, y marca si sirven como fuente principal del periodo EC3.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.preparar_datasets_2018_2025 import ALLOWED_COUNTRIES, infer_country_frame

START_REQUIRED = pd.Timestamp("2018-01-01", tz="UTC")
MIN_2025 = pd.Timestamp("2025-01-01", tz="UTC")
DATE_CANDIDATES = ["fecha_adq", "acq_date", "fecha", "date", "fecha_hora_utc", "time", "datetime"]


def _safe_file_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def find_firms_candidates(extra_roots: list[Path] | None = None) -> list[Path]:
    roots = [
        Path("/app/Proyecto-LIDIA"),
        Path("/home/pepo"),
        ROOT / "data",
    ]
    if extra_roots:
        roots.extend(extra_roots)

    candidates: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        try:
            iterator = root.rglob("*firms*.parquet")
            for path in iterator:
                key = str(path.resolve())
                if key not in seen:
                    seen.add(key)
                    candidates.append(path)
        except OSError:
            continue
    return sorted(candidates, key=lambda p: str(p))


def detect_date_column(frame: pd.DataFrame) -> tuple[str | None, pd.Series | None]:
    for column in DATE_CANDIDATES:
        if column in frame.columns:
            parsed = pd.to_datetime(frame[column], errors="coerce", utc=True)
            return column, parsed
    return None, None


def normalize_country_counts(frame: pd.DataFrame) -> dict[str, int]:
    countries = infer_country_frame(frame)
    if not len(countries):
        return {}
    counts = countries.value_counts(dropna=False).to_dict()
    return {str(country): int(count) for country, count in counts.items()}


def validate_firms_principal_profile(profile: dict[str, Any]) -> list[str]:
    """Devuelve errores que impiden usar un FIRMS como fuente principal EC3."""

    errors: list[str] = []
    min_date = profile.get("fecha_min")
    max_date = profile.get("fecha_max")
    countries = set(profile.get("paises_detectados", {}).keys())

    if min_date is None:
        errors.append("sin_fecha_minima")
    elif pd.Timestamp(min_date, tz="UTC") > START_REQUIRED:
        errors.append("fecha_minima_posterior_a_2018_01_01")

    if max_date is None:
        errors.append("sin_fecha_maxima")
    elif pd.Timestamp(max_date, tz="UTC") < MIN_2025:
        errors.append("fecha_maxima_anterior_a_2025_01_01")

    if profile.get("contiene_chl"):
        errors.append("contiene_chl")

    missing = sorted(ALLOWED_COUNTRIES - countries)
    if missing:
        errors.append("faltan_paises_" + "_".join(missing))

    if profile.get("es_nrt"):
        errors.append("archivo_nrt_no_valido_como_principal")

    return errors


def audit_firms_file(path: Path) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "ruta": str(path),
        "size_bytes": _safe_file_size(path),
        "es_nrt": "nrt" in path.name.lower(),
    }
    try:
        frame = pd.read_parquet(path)
    except Exception as exc:
        profile["error"] = f"{type(exc).__name__}: {exc}"
        profile["sirve_como_principal_ec3"] = False
        profile["errores_principal"] = ["no_se_pudo_leer"]
        return profile

    profile["filas"] = int(len(frame))
    profile["columnas"] = list(map(str, frame.columns))
    date_column, parsed = detect_date_column(frame)
    profile["columna_temporal_detectada"] = date_column
    if parsed is not None:
        valid = parsed.dropna()
        profile["nulos_temporales"] = int(parsed.isna().sum())
        if not valid.empty:
            profile["fecha_min"] = valid.min().date().isoformat()
            profile["fecha_max"] = valid.max().date().isoformat()
        else:
            profile["fecha_min"] = None
            profile["fecha_max"] = None
    else:
        profile["fecha_min"] = None
        profile["fecha_max"] = None
        profile["nulos_temporales"] = None

    countries = normalize_country_counts(frame)
    profile["paises_detectados"] = countries
    profile["contiene_chl"] = any(country in {"CHL", "CHILE"} for country in countries)
    profile["tiene_ury_arg_bra"] = ALLOWED_COUNTRIES.issubset(set(countries))
    profile["contiene_brightness"] = any(
        column.lower() in {"brightness", "brillo_termico", "brillo_ti4", "bright_ti4"}
        for column in frame.columns
    )
    profile["brightness_descripcion"] = "brillo_termico_pixel_satelital"

    errors = validate_firms_principal_profile(profile)
    profile["errores_principal"] = errors
    profile["sirve_como_principal_ec3"] = not errors
    return profile


def choose_best_candidate(profiles: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [profile for profile in profiles if profile.get("sirve_como_principal_ec3")]
    if not valid:
        return None
    return sorted(valid, key=lambda item: (item.get("fecha_max") or "", item.get("filas") or 0), reverse=True)[0]


def write_report(profiles: list[dict[str, Any]], selected: dict[str, Any] | None, log_path: Path) -> None:
    lines = ["# Auditoria FIRMS historico 2018-2025", ""]
    lines.append("| ruta | filas | desde | hasta | paises | CHL | principal EC3 | errores |")
    lines.append("|---|---:|---|---|---|---|---|---|")
    for profile in profiles:
        countries = ", ".join(f"{k}:{v}" for k, v in profile.get("paises_detectados", {}).items()) or "-"
        errors = ", ".join(profile.get("errores_principal", [])) or "-"
        lines.append(
            "| {path} | {rows} | {min_date} | {max_date} | {countries} | {chl} | {ok} | {errors} |".format(
                path=profile.get("ruta", "-"),
                rows=profile.get("filas", "ERROR"),
                min_date=profile.get("fecha_min", "-"),
                max_date=profile.get("fecha_max", "-"),
                countries=countries,
                chl=profile.get("contiene_chl", "-"),
                ok=profile.get("sirve_como_principal_ec3", False),
                errors=errors,
            )
        )
    lines.append("")
    if selected:
        lines.append(f"Seleccionado: `{selected['ruta']}`")
    else:
        lines.append("Seleccionado: ninguno. No hay FIRMS local valido como principal EC3 2018-2025.")
    lines.append("")
    lines.append("Nota: si el historico remoto `/app/Proyecto-LIDIA/data/raw/firms/firms_shapefile_2018_2025.parquet` no aparece en este log, no era accesible desde el entorno local durante la auditoria.")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps({"selected": selected, "profiles": profiles}, ensure_ascii=False, indent=2, default=str))
    lines.append("```")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita candidatos FIRMS historicos 2018-2025.")
    parser.add_argument("--log", default=str(ROOT / "evidencia" / "logs" / "auditoria_firms_historico_2018_2025.log"))
    args = parser.parse_args()

    candidates = find_firms_candidates()
    profiles = [audit_firms_file(path) for path in candidates]
    selected = choose_best_candidate(profiles)
    write_report(profiles, selected, Path(args.log))
    print(json.dumps({"selected": selected, "profiles": profiles}, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
