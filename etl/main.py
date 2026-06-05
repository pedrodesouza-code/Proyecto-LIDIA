from __future__ import annotations

import argparse
import importlib
import os
import time
from dataclasses import dataclass
from typing import Iterable

from config.settings import MONGO_ENABLED
from etl.load.mongo import configure_collections, save_trace
from etl.load.postgres import load_staging
from etl.transform.normalize import normalize
from etl.utils.logger import evento, setup_logger

SOURCES = ("FIRMS", "METEO", "CAMS", "CHIRPS", "MODIS", "INUMET")
logger = setup_logger("lidia.etl")


@dataclass(frozen=True)
class RunOptions:
    smoke: bool = False
    start_date: str | None = None
    end_date: str | None = None
    countries: tuple[str, ...] = ()
    max_records_per_source: int | None = None
    skip_mongo: bool = False


def _split_countries(value: str | list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if not value:
        return ()
    aliases = {"UY": "URY", "AR": "ARG", "BR": "BRA", "URUGUAY": "URY", "ARGENTINA": "ARG", "BRASIL": "BRA"}
    countries = []
    raw_items = value if isinstance(value, (list, tuple)) else [value]
    for raw_item in raw_items:
        for item in str(raw_item).split(","):
            country = aliases.get(item.strip().upper(), item.strip().upper())
            if country:
                countries.append(country)
    return tuple(countries)


def _date_column(frame):
    for column in ("fecha", "fecha_adq", "date", "time", "datetime", "fecha_hora", "fecha_hora_utc"):
        if column in frame.columns:
            return column
    return None


def _country_column(frame):
    for column in ("pais_codigo", "pais", "country"):
        if column in frame.columns:
            return column
    return None


def _filter_frame(frame, options: RunOptions):
    if frame.empty:
        return frame
    filtered = frame
    date_column = _date_column(filtered)
    if date_column and (options.start_date or options.end_date):
        import pandas as pd
        parsed = pd.to_datetime(filtered[date_column], errors="coerce", utc=True)
        if options.start_date:
            filtered = filtered.loc[parsed >= pd.Timestamp(options.start_date, tz="UTC")]
            parsed = parsed.loc[filtered.index]
        if options.end_date:
            filtered = filtered.loc[parsed <= pd.Timestamp(options.end_date, tz="UTC")]
    country_column = _country_column(filtered)
    if country_column and options.countries:
        aliases = {"UY": "URY", "AR": "ARG", "BR": "BRA", "URUGUAY": "URY", "ARGENTINA": "ARG", "BRASIL": "BRA"}
        countries = filtered[country_column].astype(str).str.upper().map(lambda value: aliases.get(value, value))
        filtered = filtered.loc[countries.isin(options.countries)]
    if options.max_records_per_source:
        filtered = filtered.head(options.max_records_per_source)
    return filtered


def _source_iter(selected: str) -> Iterable[str]:
    return SOURCES if selected == "ALL" else (selected,)


def run_source(source: str, options: RunOptions | None = None) -> dict:
    options = options or RunOptions()
    started = time.perf_counter()
    if options.max_records_per_source:
        os.environ["LIDIA_MAX_RECORDS_PER_SOURCE"] = str(options.max_records_per_source)
    try:
        evento(logger, fuente=source, etapa="inicio", estado="iniciado", smoke=options.smoke)
        module = importlib.import_module(f"etl.extract.extract_{source.lower()}")
        evento(logger, fuente=source, etapa="extract", estado="iniciado", smoke=options.smoke)
        frame = module.extract()
        read_rows = len(frame)
        frame = _filter_frame(frame, options)
        evento(logger, fuente=source, etapa="extract", estado="ok", filas_leidas=read_rows,
               filas_filtradas=len(frame), smoke=options.smoke)
        evento(logger, fuente=source, etapa="transform", estado="iniciado", filas_leidas=len(frame),
               smoke=options.smoke)
        accepted, rejected = normalize(source, frame)
        evento(logger, fuente=source, etapa="transform", estado="ok", filas_aceptadas=len(accepted),
               filas_rechazadas=len(rejected), smoke=options.smoke)
        evento(logger, fuente=source, etapa="load", estado="iniciado", filas_leidas=len(frame),
               smoke=options.smoke)
        result = load_staging(source, accepted, rejected, promote=not options.smoke)
        evento(logger, fuente=source, etapa="load", estado="ok", filas_leidas=len(frame),
               filas_insertadas=result["insertadas"], filas_actualizadas=result["actualizadas"],
               filas_sin_cambio=result.get("sin_cambio", 0), filas_rechazadas=result["rechazadas"], smoke=options.smoke,
               promocion_dw=not options.smoke)
        if MONGO_ENABLED and not options.skip_mongo:
            configure_collections()
            save_trace(source, result, accepted, rejected)
        elif options.skip_mongo:
            evento(logger, fuente=source, etapa="mongo", estado="omitido", motivo="skip_mongo", smoke=options.smoke)
        evento(logger, fuente=source, etapa="pipeline", estado="ok", filas_leidas=len(frame),
               filas_cargadas=result["insertadas"] + result["actualizadas"],
               filas_insertadas=result["insertadas"], filas_actualizadas=result["actualizadas"],
               filas_sin_cambio=result.get("sin_cambio", 0), filas_rechazadas=result["rechazadas"], duracion_segundos=round(time.perf_counter() - started, 3),
               smoke=options.smoke)
        return result
    except FileNotFoundError as exc:
        if options.smoke:
            result = {"source": source, "estado": "omitida_sin_configuracion", "error": str(exc)}
            evento(logger, fuente=source, etapa="pipeline", estado="omitida_sin_configuracion",
                   error=str(exc), smoke=True, duracion_segundos=round(time.perf_counter() - started, 3))
            return result
        raise
    except Exception as exc:
        evento(logger, fuente=source, etapa="pipeline", estado="error",
               filas_leidas=0, filas_cargadas=0, filas_rechazadas=0,
               duracion_segundos=round(time.perf_counter() - started, 3),
               error=f"{type(exc).__name__}: {exc}")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline EC3 Proyecto LIDIA")
    parser.add_argument("--source", choices=("ALL", *SOURCES), default="ALL")
    parser.add_argument("--smoke", action="store_true", help="Corrida controlada de evidencia; no es carga historica completa.")
    parser.add_argument("--start-date", help="Fecha inicial inclusiva para recorte de evidencia, formato YYYY-MM-DD.")
    parser.add_argument("--end-date", help="Fecha final inclusiva para recorte de evidencia, formato YYYY-MM-DD.")
    parser.add_argument("--countries", nargs="*", help="Paises separados por coma o espacios, por ejemplo URY,ARG,BRA o URY ARG BRA.")
    parser.add_argument("--max-records-per-source", type=int, help="Limite maximo de registros por fuente.")
    parser.add_argument("--skip-mongo", action="store_true", help="Omite persistencia documental MongoDB en esta corrida.")
    args = parser.parse_args()
    options = RunOptions(
        smoke=args.smoke,
        start_date=args.start_date or ("2025-01-01" if args.smoke else None),
        end_date=args.end_date or ("2025-01-07" if args.smoke else None),
        countries=_split_countries(args.countries or ("URY" if args.smoke else "")),
        max_records_per_source=args.max_records_per_source or (1000 if args.smoke else None),
        skip_mongo=args.skip_mongo,
    )
    evento(logger, etapa="pipeline", estado="inicio", fuente=args.source,
           smoke=options.smoke, start_date=options.start_date, end_date=options.end_date,
           countries=options.countries, max_records_per_source=options.max_records_per_source,
           skip_mongo=options.skip_mongo,
           nota="corrida controlada de evidencia; no es carga historica completa" if options.smoke else "carga solicitada")
    for source in _source_iter(args.source):
        run_source(source, options)
    evento(logger, etapa="pipeline", estado="fin", fuente=args.source, smoke=options.smoke)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
