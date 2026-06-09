from __future__ import annotations

import argparse
import importlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import pyarrow.parquet as pq

from config.settings import SOURCE_FILES
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


def _env_max_records() -> int | None:
    value = os.getenv("LIDIA_MAX_RECORDS_PER_SOURCE", "").strip()
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _firms_batch_size() -> int:
    value = os.getenv("FIRMS_BATCH_SIZE", "50000").strip()
    try:
        parsed = int(value)
    except ValueError:
        return 50000
    return parsed if parsed > 0 else 50000


def _date_column(frame):
    for column in ("fecha", "fecha_adq", "acq_date", "date", "time", "datetime", "fecha_hora", "fecha_hora_utc"):
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


def _firms_file() -> Path:
    configured = os.getenv("FIRMS_FILE", SOURCE_FILES.get("FIRMS", "")).strip().strip('"')
    if not configured:
        raise FileNotFoundError("FIRMS: configure FIRMS_FILE en config/.env")
    path = Path(configured).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"FIRMS: archivo no encontrado: {path}")
    if path.suffix.lower() not in {".parquet", ".pq"}:
        raise ValueError("FIRMS particionado requiere archivo Parquet")
    return path


def _firms_date_column(path: Path) -> str:
    available_columns = pq.ParquetFile(path).schema.names
    for column in ("fecha_adq", "acq_date", "fecha"):
        if column in available_columns:
            return column
    raise ValueError(
        "FIRMS particionado requiere una columna temporal: fecha_adq o acq_date"
    )


def _firms_years(path: Path, options: RunOptions) -> list[int]:
    date_column = _firms_date_column(path)
    dates = pd.read_parquet(path, columns=[date_column])
    parsed = pd.to_datetime(dates[date_column], errors="coerce", utc=True)
    if options.start_date:
        parsed = parsed.loc[parsed >= pd.Timestamp(options.start_date, tz="UTC")]
    if options.end_date:
        parsed = parsed.loc[parsed <= pd.Timestamp(options.end_date, tz="UTC")]
    years = sorted(parsed.dropna().dt.year.unique().tolist())
    return [int(year) for year in years]


def _firms_columns(path: Path) -> tuple[list[str], str]:
    wanted_columns = [
        # Esquema normalizado usado por los parquets preparados del proyecto.
        "latitud",
        "longitud",
        "brillo_ti4",
        "fecha_adq",
        "hora_adq_hhmm",
        "satelite",
        "instrumento",
        "confianza_raw",
        "potencia_radiativa",
        "dia_noche",
        "pais_codigo",
        "pais",
        # Esquema original NASA FIRMS exportado desde CSV/shapefile.
        "latitude",
        "longitude",
        "brightness",
        "scan",
        "track",
        "acq_date",
        "acq_time",
        "satellite",
        "instrument",
        "confidence",
        "version",
        "bright_t31",
        "frp",
        "daynight",
        "type",
        "geometry_wkt",
    ]
    available_columns = pq.ParquetFile(path).schema.names
    date_column = _firms_date_column(path)
    use_columns = [column for column in wanted_columns if column in available_columns]
    if date_column not in use_columns:
        use_columns.append(date_column)
    return use_columns, date_column


def _iter_firms_partitions(path: Path, options: RunOptions, batch_size: int):
    use_columns, date_column = _firms_columns(path)
    parquet_file = pq.ParquetFile(path)
    for record_batch in parquet_file.iter_batches(batch_size=batch_size, columns=use_columns):
        frame = record_batch.to_pandas()
        parsed = pd.to_datetime(frame[date_column], errors="coerce", utc=True)
        if options.start_date:
            keep = parsed >= pd.Timestamp(options.start_date, tz="UTC")
            frame = frame.loc[keep].copy()
            parsed = parsed.loc[frame.index]
        if options.end_date:
            keep = parsed <= pd.Timestamp(options.end_date, tz="UTC")
            frame = frame.loc[keep].copy()
            parsed = parsed.loc[frame.index]
        if frame.empty:
            continue
        years = parsed.dropna().dt.year
        for year in sorted(years.unique().tolist()):
            selected = years.eq(year)
            partition = frame.loc[selected].copy()
            partition = _filter_frame(partition, options)
            if not partition.empty:
                yield int(year), partition, date_column


def _read_firms_partition(path: Path, year: int, options: RunOptions, remaining: int | None):
    chunks = []
    collected = 0
    for partition_year, frame, date_column in _iter_firms_partitions(path, options, _firms_batch_size()):
        if partition_year != year:
            continue
        if remaining is not None:
            take = max(remaining - collected, 0)
            if take <= 0:
                break
            frame = frame.head(take)
        chunks.append(frame)
        collected += len(frame)
        if remaining is not None and collected >= remaining:
            break
    if chunks:
        return pd.concat(chunks, ignore_index=True), _firms_date_column(path)
    return pd.DataFrame(columns=_firms_columns(path)[0]), _firms_date_column(path)


def _aggregate_counts(total: dict, result: dict) -> None:
    for key in ("leidas", "insertadas", "actualizadas", "sin_cambio", "rechazadas"):
        total[key] = total.get(key, 0) + int(result.get(key, 0))


def _frame_batches(frame, batch_size: int):
    for start in range(0, len(frame), batch_size):
        yield start // batch_size + 1, frame.iloc[start : start + batch_size].copy()


def run_firms_partitioned(options: RunOptions) -> dict:
    started = time.perf_counter()
    if options.max_records_per_source:
        os.environ["LIDIA_MAX_RECORDS_PER_SOURCE"] = str(options.max_records_per_source)
    path = _firms_file()
    date_column = _firms_date_column(path)
    evento(
        logger,
        fuente="FIRMS",
        etapa="inicio",
        estado="iniciado",
        particionado=True,
        columna_temporal=date_column,
        smoke=options.smoke,
    )
    total = {"leidas": 0, "insertadas": 0, "actualizadas": 0, "sin_cambio": 0, "rechazadas": 0, "particiones": 0}
    remaining = options.max_records_per_source
    batch_size = _firms_batch_size()
    year_counts: dict[int, dict] = {}
    year_batches: dict[int, int] = {}
    try:
        for year, frame, partition_date_column in _iter_firms_partitions(path, options, batch_size):
            if remaining is not None and remaining <= 0:
                break
            if remaining is not None:
                frame = frame.head(remaining)
            if frame.empty:
                continue
            if year not in year_counts:
                year_counts[year] = {
                    "inicio": time.perf_counter(),
                    "leidas": 0,
                    "insertadas": 0,
                    "actualizadas": 0,
                    "sin_cambio": 0,
                    "rechazadas": 0,
                }
                year_batches[year] = 0
                total["particiones"] += 1
                evento(
                    logger,
                    fuente="FIRMS",
                    etapa="extract",
                    estado="iniciado",
                    anio=year,
                    particionado=True,
                    columna_temporal=date_column,
                    smoke=options.smoke,
                )
            year_batches[year] += 1
            batch_number = year_batches[year]
            read_rows = len(frame)
            year_counts[year]["leidas"] += read_rows
            evento(
                logger,
                fuente="FIRMS",
                etapa="extract",
                estado="ok",
                anio=year,
                lote=batch_number,
                filas_leidas=read_rows,
                filas_filtradas=read_rows,
                particionado=True,
                columna_temporal=partition_date_column,
                smoke=options.smoke,
            )
            for inner_batch_number, batch in _frame_batches(frame, batch_size):
                batch_started = time.perf_counter()
                evento(
                    logger,
                    fuente="FIRMS",
                    etapa="transform",
                    estado="iniciado",
                    anio=year,
                    lote=batch_number,
                    sublote=inner_batch_number,
                    filas_leidas=len(batch),
                    particionado=True,
                    smoke=options.smoke,
                )
                accepted, rejected = normalize("FIRMS", batch)
                evento(
                    logger,
                    fuente="FIRMS",
                    etapa="transform",
                    estado="ok",
                    anio=year,
                    lote=batch_number,
                    sublote=inner_batch_number,
                    filas_aceptadas=len(accepted),
                    filas_rechazadas=len(rejected),
                    particionado=True,
                    smoke=options.smoke,
                )
                evento(
                    logger,
                    fuente="FIRMS",
                    etapa="load",
                    estado="iniciado",
                    anio=year,
                    lote=batch_number,
                    sublote=inner_batch_number,
                    filas_leidas=len(batch),
                    particionado=True,
                    smoke=options.smoke,
                )
                result = load_staging("FIRMS", accepted, rejected, promote=not options.smoke)
                _aggregate_counts(total, result)
                for key in ("insertadas", "actualizadas", "sin_cambio", "rechazadas"):
                    year_counts[year][key] += int(result.get(key, 0))
                evento(
                    logger,
                    fuente="FIRMS",
                    etapa="load",
                    estado="ok",
                    anio=year,
                    lote=batch_number,
                    sublote=inner_batch_number,
                    filas_leidas=len(batch),
                    filas_insertadas=result["insertadas"],
                    filas_actualizadas=result["actualizadas"],
                    filas_sin_cambio=result.get("sin_cambio", 0),
                    filas_rechazadas=result["rechazadas"],
                    duracion_segundos=round(time.perf_counter() - batch_started, 3),
                    particionado=True,
                    smoke=options.smoke,
                    promocion_dw=not options.smoke,
                )
                if MONGO_ENABLED and not options.skip_mongo:
                    configure_collections()
                    save_trace("FIRMS", result, accepted[:1000], rejected[:1000])
                elif options.skip_mongo:
                    evento(logger, fuente="FIRMS", etapa="mongo", estado="omitido", motivo="skip_mongo", anio=year, lote=batch_number, smoke=options.smoke)
            if remaining is not None:
                remaining -= read_rows
        for year, counts in sorted(year_counts.items()):
            evento(
                logger,
                fuente="FIRMS",
                etapa="particion",
                estado="ok",
                anio=year,
                filas_leidas=counts["leidas"],
                filas_insertadas=counts["insertadas"],
                filas_actualizadas=counts["actualizadas"],
                filas_sin_cambio=counts.get("sin_cambio", 0),
                filas_rechazadas=counts["rechazadas"],
                lotes=year_batches.get(year, 0),
                duracion_segundos=round(time.perf_counter() - counts["inicio"], 3),
                particionado=True,
                columna_temporal=date_column,
                smoke=options.smoke,
            )
        total["run_id"] = "partitioned"
        evento(
            logger,
            fuente="FIRMS",
            etapa="pipeline",
            estado="ok",
            filas_leidas=total["leidas"],
            filas_cargadas=total["insertadas"] + total["actualizadas"],
            filas_insertadas=total["insertadas"],
            filas_actualizadas=total["actualizadas"],
            filas_sin_cambio=total.get("sin_cambio", 0),
            filas_rechazadas=total["rechazadas"],
            particiones=total["particiones"],
            duracion_segundos=round(time.perf_counter() - started, 3),
            particionado=True,
            smoke=options.smoke,
        )
        return total
    except Exception as exc:
        evento(
            logger,
            fuente="FIRMS",
            etapa="pipeline",
            estado="error",
            filas_leidas=total.get("leidas", 0),
            filas_cargadas=total.get("insertadas", 0) + total.get("actualizadas", 0),
            filas_rechazadas=total.get("rechazadas", 0),
            duracion_segundos=round(time.perf_counter() - started, 3),
            error=f"{type(exc).__name__}: {exc}",
            particionado=True,
        )
        raise


def run_source(source: str, options: RunOptions | None = None) -> dict:
    options = options or RunOptions()
    if source == "FIRMS":
        return run_firms_partitioned(options)
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
        max_records_per_source=args.max_records_per_source or _env_max_records() or (1000 if args.smoke else None),
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
