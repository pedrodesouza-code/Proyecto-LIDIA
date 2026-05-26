from __future__ import annotations

import argparse
import importlib
import time

from etl.load.postgres import load_staging
from etl.transform.normalize import normalize
from etl.utils.logger import evento, setup_logger

SOURCES = ("FIRMS", "METEO", "FORECAST", "CHIRPS", "MODIS", "INUMET")
logger = setup_logger("lidia.etl")


def run_source(source: str) -> dict:
    started = time.perf_counter()
    try:
        module = importlib.import_module(f"etl.extract.extract_{source.lower()}")
        frame = module.extract()
        accepted, rejected = normalize(source, frame)
        result = load_staging(source, accepted, rejected)
        evento(logger, fuente=source, etapa="pipeline", estado="ok", filas_leidas=len(frame),
               filas_cargadas=result["insertadas"] + result["actualizadas"],
               filas_rechazadas=result["rechazadas"], duracion_segundos=round(time.perf_counter() - started, 3))
        return result
    except Exception as exc:
        evento(logger, fuente=source, etapa="pipeline", estado="error",
               filas_leidas=0, filas_cargadas=0, filas_rechazadas=0,
               duracion_segundos=round(time.perf_counter() - started, 3),
               error=f"{type(exc).__name__}: {exc}")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline EC3 Proyecto LIDIA")
    parser.add_argument("--source", choices=("ALL", *SOURCES), default="ALL")
    args = parser.parse_args()
    for source in SOURCES if args.source == "ALL" else (args.source,):
        run_source(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
