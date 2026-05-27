"""Carga real controlada de FIRMS y CHIRPS para el DW Proyecto LIDIA."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import uuid
from collections import Counter
from io import StringIO
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely
from psycopg2.extras import Json

from config.settings import FIRMS_COUNTRY_BOUNDARIES_FILE, ROOT, SOURCE_FILES
from etl.extract.extract_chirps import extract as extract_chirps
from etl.load.postgres import _promote, connect, load_staging
from etl.transform.normalize import normalize

COUNTRIES = ("URY", "ARG", "BRA")
FIRMS_COLUMNS = [
    "record_hash", "natural_key", "fecha_adq", "hora_adq_hhmm", "latitud",
    "longitud", "pais_codigo", "frp_mw", "brillo_termico", "confianza",
    "satelite", "instrumento", "dia_noche",
]


def _configured_path(value: str, label: str) -> Path:
    path = Path(value).expanduser()
    if not value.strip():
        raise FileNotFoundError(f"Configure {label} antes de la carga real.")
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise FileNotFoundError(f"{label}: archivo no encontrado: {path}")
    return path


def _boundaries() -> list[tuple[str, object]]:
    path = _configured_path(FIRMS_COUNTRY_BOUNDARIES_FILE, "FIRMS_COUNTRY_BOUNDARIES_FILE")
    boundaries = gpd.read_file(path)
    code_column = "ADM0_A3" if "ADM0_A3" in boundaries.columns else "ISO_A3"
    selected = boundaries[boundaries[code_column].isin(COUNTRIES)]
    missing = sorted(set(COUNTRIES) - set(selected[code_column]))
    if missing:
        raise ValueError(f"La geometria territorial no contiene: {missing}")
    return [(row[code_column], row.geometry) for _, row in selected.iterrows()]


def _sha256_series(values: pd.Series) -> pd.Series:
    return values.map(lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest())


def _transform_firms(frame: pd.DataFrame, boundaries: list[tuple[str, object]]) -> tuple[pd.DataFrame, Counter]:
    result = pd.DataFrame(index=frame.index)
    result["fecha_adq"] = pd.to_datetime(frame.get("acq_date"), errors="coerce").dt.date
    result["hora_adq_hhmm"] = pd.to_numeric(frame.get("acq_time"), errors="coerce").astype("Int64")
    result["latitud"] = pd.to_numeric(frame.get("latitude"), errors="coerce")
    result["longitud"] = pd.to_numeric(frame.get("longitude"), errors="coerce")
    result["frp_mw"] = pd.to_numeric(frame.get("frp"), errors="coerce")
    result["brillo_termico"] = pd.to_numeric(frame.get("brightness"), errors="coerce")
    result["confianza"] = pd.to_numeric(frame.get("confidence"), errors="coerce")
    result["satelite"] = frame.get("satellite")
    result["instrumento"] = frame.get("instrument")
    result["dia_noche"] = frame.get("daynight")

    country = pd.Series("", index=frame.index, dtype="object")
    lat = result["latitud"].to_numpy()
    lon = result["longitud"].to_numpy()
    finite = result["latitud"].notna() & result["longitud"].notna()
    for code, geometry in boundaries:
        inside = finite & shapely.contains_xy(geometry, lon, lat)
        country.loc[inside] = code
    result["pais_codigo"] = country

    in_period = result["fecha_adq"].map(lambda value: value is not pd.NaT and value is not None and 2018 <= value.year <= 2025)
    valid = (
        in_period
        & finite
        & result["frp_mw"].ge(0)
        & result["confianza"].between(0, 100)
        & result["dia_noche"].isin(["D", "N"])
    )
    outside = valid & ~result["pais_codigo"].isin(COUNTRIES)
    invalid = ~valid
    accepted = result.loc[valid & ~outside].copy()

    accepted["natural_key"] = (
        accepted["fecha_adq"].astype(str) + "|" + accepted["latitud"].astype(str) + "|"
        + accepted["longitud"].astype(str) + "|" + accepted["hora_adq_hhmm"].astype(str)
        + "|" + accepted["satelite"].fillna("").astype(str)
    )
    hash_value = (
        accepted["natural_key"] + "|" + accepted["frp_mw"].astype(str) + "|"
        + accepted["brillo_termico"].astype(str) + "|" + accepted["confianza"].astype(str)
    )
    accepted["record_hash"] = _sha256_series(hash_value)
    counts = Counter(
        {
            "fuera_alcance_geografico": int(outside.sum()),
            "registro_invalido_o_fuera_periodo": int(invalid.sum()),
        }
    )
    return accepted[FIRMS_COLUMNS], counts


def _run_started(cur, source: str) -> str:
    run_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO audit.etl_runs (run_id, fuente, etapa, estado) VALUES (%s,%s,'load','iniciado')",
        (run_id, source),
    )
    return run_id


def _summarize_rejections(cur, run_id: str, source: str, counts: Counter, detail: dict) -> None:
    for reason, count in counts.items():
        if not count:
            continue
        payload = {**detail, "cantidad": int(count), "registro_nivel": "resumen"}
        cur.execute(
            "INSERT INTO staging.rechazos_etl (run_id, fuente, motivo, registro) VALUES (%s,%s,%s,%s)",
            (run_id, source, reason, Json(payload)),
        )
        cur.execute(
            """INSERT INTO audit.cdc_eventos (run_id, fuente, record_hash, tipo_evento, detalle)
               VALUES (%s,%s,%s,'rechazo',%s)""",
            (run_id, source, "0" * 64, Json(payload)),
        )


def load_real_firms(chunksize: int = 100_000) -> dict:
    path = _configured_path(SOURCE_FILES["FIRMS"], "FIRMS_FILE")
    boundaries = _boundaries()
    start = time.perf_counter()
    read_rows = inserted = 0
    rejected = Counter()
    with connect() as connection:
        with connection.cursor() as cur:
            run_id = _run_started(cur, "FIRMS")
            connection.commit()
        for frame in pd.read_csv(path, chunksize=chunksize):
            transformed, chunk_rejected = _transform_firms(frame, boundaries)
            read_rows += len(frame)
            rejected.update(chunk_rejected)
            with connection.cursor() as cur:
                cur.execute("CREATE TEMP TABLE tmp_firms_load (LIKE staging.stg_firms INCLUDING DEFAULTS) ON COMMIT DROP")
                output = StringIO()
                transformed.to_csv(output, index=False, header=False, na_rep="")
                output.seek(0)
                cur.copy_expert(
                    """COPY tmp_firms_load
                       (record_hash,natural_key,fecha_adq,hora_adq_hhmm,latitud,longitud,
                        pais_codigo,frp_mw,brillo_termico,confianza,satelite,instrumento,dia_noche)
                       FROM STDIN WITH (FORMAT CSV, NULL '')""",
                    output,
                )
                cur.execute(
                    """INSERT INTO staging.stg_firms
                       (record_hash,natural_key,fecha_adq,hora_adq_hhmm,latitud,longitud,
                        pais_codigo,frp_mw,brillo_termico,confianza,satelite,instrumento,dia_noche)
                       SELECT DISTINCT ON (natural_key)
                        record_hash,natural_key,fecha_adq,hora_adq_hhmm,latitud,longitud,
                        pais_codigo,frp_mw,brillo_termico,confianza,satelite,instrumento,dia_noche
                       FROM tmp_firms_load ORDER BY natural_key
                       ON CONFLICT (natural_key) DO NOTHING"""
                )
                inserted += cur.rowcount
            connection.commit()
            print(json.dumps({"fuente": "FIRMS", "leidas": read_rows, "insertadas": inserted}))
        valid_rows = read_rows - sum(rejected.values())
        rejected["duplicado_clave_natural"] += valid_rows - inserted
        with connection.cursor() as cur:
            _summarize_rejections(
                cur,
                run_id,
                "FIRMS",
                rejected,
                {"criterio": "punto_en_limite_territorial_URY_ARG_BRA", "archivo": path.name},
            )
            _promote(cur, "FIRMS")
            cur.execute(
                """INSERT INTO audit.cdc_eventos (run_id,fuente,record_hash,tipo_evento,detalle)
                   VALUES (%s,'FIRMS',%s,'alta',%s)""",
                (run_id, "0" * 64, Json({"cantidad": inserted, "modo": "carga_masiva_controlada"})),
            )
            cur.execute(
                """UPDATE audit.etl_runs SET estado='ok', ultima_fecha_procesada=(SELECT MAX(fecha_adq) FROM staging.stg_firms),
                   filas_leidas=%s, filas_insertadas=%s, filas_rechazadas=%s,
                   duracion_segundos=%s, finalizado_en=NOW() WHERE run_id=%s""",
                (read_rows, inserted, sum(rejected.values()), round(time.perf_counter() - start, 3), run_id),
            )
            cur.execute(
                "ANALYZE staging.stg_firms, dw.dim_fecha, dw.dim_ubicacion, dw.fact_incendio"
            )
        connection.commit()
    return {"fuente": "FIRMS", "leidas": read_rows, "insertadas": inserted, "rechazadas": dict(rejected), "run_id": run_id}


def load_real_chirps() -> dict:
    frame = extract_chirps()
    accepted, rejected = normalize("CHIRPS", frame)
    result = load_staging("CHIRPS", accepted, rejected)
    paises = Counter(row["pais_codigo"] for row in accepted)
    return {
        "fuente": "CHIRPS",
        "leidas": len(frame),
        "insertadas": result["insertadas"],
        "rechazadas": result["rechazadas"],
        "aceptadas_por_pais": dict(paises),
        "nota": "No hay filas URY en el archivo real." if paises.get("URY", 0) == 0 else "",
        "run_id": result["run_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga real controlada FIRMS/CHIRPS")
    parser.add_argument("--source", choices=("FIRMS", "CHIRPS", "BOTH"), default="BOTH")
    parser.add_argument("--chunksize", type=int, default=100_000)
    args = parser.parse_args()
    results = []
    if args.source in {"FIRMS", "BOTH"}:
        results.append(load_real_firms(args.chunksize))
    if args.source in {"CHIRPS", "BOTH"}:
        results.append(load_real_chirps())
    print("CARGA_REAL_RESULTADO=" + json.dumps(results, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
