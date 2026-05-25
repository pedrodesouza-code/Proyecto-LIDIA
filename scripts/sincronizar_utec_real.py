from __future__ import annotations

import json
import os
import sys
from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg2
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
PROCESSED = ROOT / "data" / "processed"
PAISES_ALCANCE = ("CHL", "URY", "BRA", "ARG")

sys.path.insert(0, str(ROOT))


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _read_parquet(name: str) -> pd.DataFrame:
    path = PROCESSED / name
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_parquet(path)


def _materializar_postgres() -> dict[str, int]:
    sql = """
    DROP MATERIALIZED VIEW IF EXISTS mv_focos_por_pais_mes;
    DROP MATERIALIZED VIEW IF EXISTS mv_focos_por_pais;

    CREATE MATERIALIZED VIEW mv_focos_por_pais AS
    SELECT
        pais,
        count(*)::bigint AS total_focos,
        avg(potencia_radiativa)::numeric(12, 3) AS frp_promedio,
        max(potencia_radiativa)::numeric(12, 3) AS frp_maximo,
        count(*) FILTER (WHERE confianza_num = 3)::bigint AS focos_alta_confianza
    FROM focos_calor
    WHERE pais IN ('CHL', 'URY', 'BRA', 'ARG')
    GROUP BY pais;

    CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_focos_por_pais_pais
        ON mv_focos_por_pais (pais);

    CREATE MATERIALIZED VIEW mv_focos_por_pais_mes AS
    SELECT
        pais,
        date_trunc('month', fecha_adq)::date AS mes,
        count(*)::bigint AS total_focos,
        avg(potencia_radiativa)::numeric(12, 3) AS frp_promedio,
        max(potencia_radiativa)::numeric(12, 3) AS frp_maximo
    FROM focos_calor
    WHERE pais IN ('CHL', 'URY', 'BRA', 'ARG')
    GROUP BY pais, date_trunc('month', fecha_adq)::date;

    CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_focos_por_pais_mes_pk
        ON mv_focos_por_pais_mes (pais, mes);
    """
    conn = psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
        dbname=os.getenv("PG_DATABASE", "sinia_uy"),
        user=os.getenv("PG_USER", "sinia_etl"),
        password=os.getenv("PG_PASSWORD", ""),
        connect_timeout=8,
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute("SELECT count(*) FROM mv_focos_por_pais")
                por_pais = int(cur.fetchone()[0])
                cur.execute("SELECT count(*) FROM mv_focos_por_pais_mes")
                por_mes = int(cur.fetchone()[0])
        return {"mv_focos_por_pais": por_pais, "mv_focos_por_pais_mes": por_mes}
    finally:
        conn.close()


def _cargar_postgres() -> dict[str, Any]:
    from etl.load.load_postgres import (
        cargar_calidad_aire,
        cargar_cobertura_vegetal,
        cargar_focos_calor,
        cargar_meteo_diario,
        cargar_precipitacion,
    )

    results: dict[str, Any] = {}

    df_firms = _read_parquet("firms_procesado.parquet")
    results["firms_procesado"] = cargar_focos_calor(df_firms)

    df_firms_nrt = _read_parquet("firms_nrt_procesado.parquet")
    results["firms_nrt_procesado"] = cargar_focos_calor(df_firms_nrt)

    df_meteo = _read_parquet("meteo_procesado_todos.parquet")
    results["meteo_procesado_todos"] = cargar_meteo_diario(df_meteo, tipo_dato="historico")

    df_forecast = _read_parquet("forecast_riesgo.parquet")
    results["forecast_riesgo"] = cargar_meteo_diario(df_forecast, tipo_dato="forecast")

    df_cams = _read_parquet("cams_procesado_todos.parquet")
    results["cams_procesado_todos"] = cargar_calidad_aire(df_cams)

    df_cams_nrt = _read_parquet("cams_nrt_procesado.parquet")
    results["cams_nrt_procesado"] = cargar_calidad_aire(df_cams_nrt)

    df_chirps = _read_parquet("chirps_sa.parquet")
    results["chirps_sa"] = cargar_precipitacion(df_chirps)

    df_modis = _read_parquet("modis_lc.parquet")
    results["modis_lc"] = cargar_cobertura_vegetal(df_modis)

    results["materializadas"] = _materializar_postgres()
    return results


def _cargar_mongo_nrt() -> dict[str, Any]:
    from etl.load.load_mongo import (
        crear_colecciones_con_schema,
        guardar_snapshot_focos,
        registrar_ejecucion_etl,
    )
    from scripts.optimizar_mongo_resumenes import main as optimizar_mongo

    crear_colecciones_con_schema()
    df_firms = _read_parquet("firms_procesado.parquet")
    df_meteo = _read_parquet("forecast_riesgo.parquet")
    snapshots_historicos = guardar_snapshot_focos(df_firms, df_meteo)

    df_firms_nrt = _read_parquet("firms_nrt_procesado.parquet")
    snapshots_nrt = guardar_snapshot_focos(df_firms_nrt, df_meteo)
    snapshots = int(snapshots_historicos + snapshots_nrt)
    registrar_ejecucion_etl(
        fuente="firms_nrt",
        etapa="load",
        tipo_carga="incremental",
        estado="ok",
        metricas={
            "filas_procesadas": int(len(df_firms_nrt)),
            "snapshots_guardados": snapshots,
            "snapshots_historicos": int(snapshots_historicos),
            "snapshots_nrt": int(snapshots_nrt),
            "destino": "utec_mongodb",
        },
    )
    optimizar_mongo()
    return {
        "snapshots_guardados": snapshots,
        "snapshots_historicos": int(snapshots_historicos),
        "snapshots_nrt": int(snapshots_nrt),
        "filas_firms_historico": int(len(df_firms)),
        "filas_firms_nrt": int(len(df_firms_nrt)),
    }


def main() -> int:
    parser = ArgumentParser(description="Sincroniza datos reales contra las bases UTEC configuradas por entorno.")
    parser.add_argument(
        "--fase",
        choices=["todo", "postgres", "mongo", "materializadas"],
        default="todo",
        help="Limita la sincronizacion a una fase.",
    )
    args = parser.parse_args()

    env_path = ROOT / "config" / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    report = {
        "generado_en": datetime.now(timezone.utc),
        "destino": {
            "pg_host": os.getenv("PG_HOST"),
            "pg_database": os.getenv("PG_DATABASE"),
            "mongo_host": os.getenv("MONGO_HOST"),
            "mongo_database": os.getenv("MONGO_DATABASE"),
        },
    }

    if args.fase in {"todo", "postgres"}:
        report["postgres"] = _cargar_postgres()
    if args.fase == "materializadas":
        report["postgres"] = {"materializadas": _materializar_postgres()}
    if args.fase in {"todo", "mongo"}:
        report["mongo"] = _cargar_mongo_nrt()

    REPORTS.mkdir(exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=2, default=_json_default)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    (REPORTS / f"utec_sync_{stamp}.json").write_text(text, encoding="utf-8")
    (REPORTS / "utec_sync_ultimo.json").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
