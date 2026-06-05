from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from etl.extract.extract_inumet import build_frame


def _default_raw_dir(root: Path) -> Path:
    candidates = [
        root / "Inumet",
        root.parent / "Inumet",
        root.parent / "datos-completos" / "inumet",
        root.parent / "Datos completos" / "Inumet",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return root.parent / "Inumet"


def _upsert_env(env_path: Path, key: str, value: Path) -> None:
    env_path.parent.mkdir(parents=True, exist_ok=True)
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    line = f'{key}="{value}"'
    lines = text.splitlines()
    replaced = False
    for index, current in enumerate(lines):
        if current.startswith(f"{key}="):
            lines[index] = line
            replaced = True
            break
    if not replaced:
        lines.append(line)
    env_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> int:
    root = ROOT
    raw_dir = _default_raw_dir(root)
    parser = argparse.ArgumentParser(description="Prepara INUMET local para Proyecto LIDIA.")
    parser.add_argument("--temperatura-file", default=str(raw_dir / "inumet_temperatura_del_aire.csv"))
    parser.add_argument("--humedad-file", default=str(raw_dir / "inumet_humedad_relativa.csv"))
    parser.add_argument("--output", default=str(root / "data" / "processed" / "inumet_procesado.parquet"))
    parser.add_argument("--env-file", default=str(root / "config" / ".env"))
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    temperatura_file = Path(args.temperatura_file).expanduser()
    humedad_file = Path(args.humedad_file).expanduser()
    output = Path(args.output).expanduser()
    env_file = Path(args.env_file).expanduser()
    if not temperatura_file.exists() or not humedad_file.exists():
        if not args.quiet:
            print(
                {
                    "estado": "omitido",
                    "motivo": "faltan_csv_inumet",
                    "temperatura_file": str(temperatura_file),
                    "humedad_file": str(humedad_file),
                }
            )
        return 2

    frame = build_frame(str(temperatura_file), str(humedad_file))
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    _upsert_env(env_file, "INUMET_FILE", output)
    _upsert_env(env_file, "INUMET_TEMPERATURA_FILE", temperatura_file)
    _upsert_env(env_file, "INUMET_HUMEDAD_FILE", humedad_file)
    if not args.quiet:
        print(
            {
                "estado": "ok",
                "output": str(output),
                "filas": int(len(frame)),
                "estaciones": sorted(frame["ubicacion"].dropna().unique().tolist()),
                "fecha_min": str(frame["fecha_hora_utc"].min()),
                "fecha_max": str(frame["fecha_hora_utc"].max()),
                "env_file": str(env_file),
            }
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
