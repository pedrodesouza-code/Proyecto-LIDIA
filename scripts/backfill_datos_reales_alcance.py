"""
Backfill real del alcance SINIA-UY.

Descarga y consolida datos faltantes para el alcance operativo:
Uruguay, Brasil, Argentina y Chile (36 puntos).

Fuentes:
  - Open-Meteo Archive: meteorologia historica.
  - Open-Meteo Air Quality/CAMS: calidad de aire horaria agregada a diaria.
  - CHIRPS ClimateSERV: precipitacion mensual.
  - NASA FIRMS MODIS: eventos volcanicos historicos de Chile.

El script es idempotente a nivel Parquet: concatena y deduplica por clave natural.
Si PostgreSQL esta disponible, tambien asegura paises/puntos y carga los nuevos
datos mediante los loaders existentes.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DIR_PROCESADO, PAISES_SA, PUNTOS_METEO_SA
from etl.extract.extract_cams import extraer_cams_historico
from etl.extract.extract_chirps import extraer_chirps_punto
from etl.extract.extract_firms import extraer_firms_archivo
from etl.extract.extract_meteo import extraer_meteo_historico
from etl.load.load_postgres import (
    cargar_calidad_aire,
    cargar_focos_calor,
    cargar_meteo_diario,
    cargar_precipitacion,
    get_connection,
)
from etl.transform.transform_cams import transformar_cams
from etl.transform.transform_chirps import transformar_chirps
from etl.transform.transform_firms import transformar_firms
from etl.transform.transform_meteo import transformar_meteo


REPORTS = Path("reports")
EVENTOS_VOLCANICOS = [
    {
        "id": "puyehue_2011",
        "nombre": "Puyehue-Cordon Caulle",
        "fecha_inicio": "2011-06-04",
        "fecha_fin": "2011-06-30",
        "pais_origen": "CHL",
        "fuente_evento": "NASA Earth Observatory / SINAE Uruguay",
    },
    {
        "id": "calbuco_2015",
        "nombre": "Calbuco",
        "fecha_inicio": "2015-04-22",
        "fecha_fin": "2015-05-10",
        "pais_origen": "CHL",
        "fuente_evento": "NASA Earth Observatory / SINAE Uruguay",
    },
]


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _leer_parquet(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


def _guardar_merge(path: Path, nuevo: pd.DataFrame, claves: list[str]) -> pd.DataFrame:
    previo = _leer_parquet(path)
    frames = [df for df in [previo, nuevo] if not df.empty]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    claves_presentes = [c for c in claves if c in df.columns]
    if claves_presentes:
        df = df.drop_duplicates(subset=claves_presentes, keep="last")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return df


def _puntos_presentes(path: Path) -> set[str]:
    df = _leer_parquet(path)
    if df.empty or "punto" not in df.columns:
        return set()
    return set(df["punto"].dropna().astype(str).unique())


def asegurar_dimensiones_postgres() -> bool:
    """Crea/actualiza paises y puntos del alcance en PostgreSQL."""
    try:
        conn = get_connection()
    except Exception as exc:
        _log(f"PostgreSQL no disponible para dimensiones: {exc}")
        return False

    try:
        with conn.cursor() as cur:
            for iso3, meta in PAISES_SA.items():
                cur.execute(
                    """
                    INSERT INTO paises_referencia (codigo_iso3, codigo_iso2, nombre, activo)
                    VALUES (%s, %s, %s, TRUE)
                    ON CONFLICT (codigo_iso3) DO UPDATE SET
                        codigo_iso2 = EXCLUDED.codigo_iso2,
                        nombre = EXCLUDED.nombre,
                        activo = TRUE
                    """,
                    (iso3, meta["codigo_iso2"], meta["nombre"]),
                )

            cur.execute("UPDATE puntos_monitoreo SET activo = FALSE")
            for nombre, info in PUNTOS_METEO_SA.items():
                region = _region_descriptiva(nombre, info["pais"])
                cur.execute(
                    "SELECT id FROM puntos_monitoreo WHERE nombre = %s ORDER BY id LIMIT 1",
                    (nombre,),
                )
                row = cur.fetchone()
                if row:
                    cur.execute(
                        """
                        UPDATE puntos_monitoreo
                        SET pais = %s,
                            region = %s,
                            latitud = %s,
                            longitud = %s,
                            activo = TRUE
                        WHERE id = %s
                        """,
                        (info["pais"], region, info["lat"], info["lon"], row[0]),
                    )
                    continue

                cur.execute(
                    """
                    INSERT INTO puntos_monitoreo
                        (nombre, pais, region, latitud, longitud, activo)
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    """,
                    (nombre, info["pais"], region, info["lat"], info["lon"]),
                )
        conn.commit()
        _log("PostgreSQL: dimensiones de paises y puntos actualizadas.")
        return True
    except Exception as exc:
        conn.rollback()
        _log(f"PostgreSQL: error actualizando dimensiones: {exc}")
        return False
    finally:
        conn.close()


def _region_descriptiva(nombre: str, pais: str) -> str:
    if pais == "URY":
        return "Uruguay - capital/departamental"
    if pais == "CHL" and nombre in {"Puyehue_Cordon_Caulle", "Calbuco"}:
        return "Chile - punto volcanico de impacto transfronterizo"
    if pais == "CHL":
        return "Chile - ciudad estrategica"
    if pais == "BRA":
        return "Brasil - ciudad estrategica"
    if pais == "ARG":
        return "Argentina - ciudad estrategica"
    return "Alcance regional"


def backfill_meteo(args: argparse.Namespace, load_db: bool) -> dict:
    path = DIR_PROCESADO / "meteo_procesado_todos.parquet"
    presentes = _puntos_presentes(path)
    faltantes = [p for p in PUNTOS_METEO_SA if args.force or p not in presentes]
    ventanas = [(args.meteo_start, args.meteo_end)]
    if args.event_windows:
        ventanas.extend((e["fecha_inicio"], e["fecha_fin"]) for e in EVENTOS_VOLCANICOS)

    frames = []
    errores = {}
    _log(f"METEO: {len(faltantes)} puntos faltantes/forzados, {len(ventanas)} ventanas.")
    for punto in faltantes:
        for inicio, fin in ventanas:
            try:
                df = extraer_meteo_historico(
                    punto=punto,
                    fecha_inicio=inicio,
                    fecha_fin=fin,
                    granularidad="daily",
                    guardar=False,
                )
                proc = transformar_meteo(df, guardar=False)
                if not proc.empty:
                    frames.append(proc)
            except Exception as exc:
                errores[f"{punto}:{inicio}:{fin}"] = str(exc)
            time.sleep(args.pause)

    nuevo = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    consolidado = _guardar_merge(path, nuevo, ["punto", "fecha"])
    metricas = {
        "nuevos": len(nuevo),
        "consolidado": len(consolidado),
        "puntos_consolidados": len(_puntos_presentes(path)),
        "errores": errores,
    }
    if load_db and not nuevo.empty:
        metricas["postgres"] = cargar_meteo_diario(nuevo, tipo_dato="historico")
    return metricas


def backfill_cams(args: argparse.Namespace, load_db: bool) -> dict:
    path = DIR_PROCESADO / "cams_procesado_todos.parquet"
    presentes = _puntos_presentes(path)
    faltantes = [p for p in PUNTOS_METEO_SA if args.force or p not in presentes]
    frames = []
    errores = {}
    _log(f"CAMS: {len(faltantes)} puntos faltantes/forzados.")
    for punto in faltantes:
        try:
            df = extraer_cams_historico(
                punto=punto,
                fecha_inicio=args.cams_start,
                fecha_fin=args.cams_end,
                guardar=False,
            )
            proc = transformar_cams(df, guardar=False)
            if not proc.empty:
                frames.append(proc)
        except Exception as exc:
            errores[punto] = str(exc)
        time.sleep(args.pause)

    nuevo = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    consolidado = _guardar_merge(path, nuevo, ["punto", "fecha"])
    metricas = {
        "nuevos": len(nuevo),
        "consolidado": len(consolidado),
        "puntos_consolidados": len(_puntos_presentes(path)),
        "errores": errores,
    }
    if load_db and not nuevo.empty:
        metricas["postgres"] = cargar_calidad_aire(nuevo)
    return metricas


def backfill_chirps(args: argparse.Namespace, load_db: bool) -> dict:
    path = DIR_PROCESADO / "chirps_sa.parquet"
    presentes = _puntos_presentes(path)
    faltantes = [p for p in PUNTOS_METEO_SA if args.force or p not in presentes]
    frames = []
    errores = {}
    _log(f"CHIRPS: {len(faltantes)} puntos faltantes/forzados.")
    for punto in faltantes:
        try:
            df = extraer_chirps_punto(
                punto=punto,
                anio_inicio=args.chirps_start_year,
                anio_fin=args.chirps_end_year,
                guardar=False,
            )
            if not df.empty:
                frames.append(df)
        except Exception as exc:
            errores[punto] = str(exc)
        time.sleep(max(args.pause, 1.0))

    nuevo = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    proc = transformar_chirps(nuevo, guardar=False) if not nuevo.empty else pd.DataFrame()
    consolidado = _guardar_merge(path, proc, ["punto", "anio", "mes"])
    metricas = {
        "nuevos": len(proc),
        "consolidado": len(consolidado),
        "puntos_consolidados": len(_puntos_presentes(path)),
        "errores": errores,
    }
    if load_db and not proc.empty:
        metricas["postgres"] = cargar_precipitacion(proc)
    return metricas


def backfill_eventos_firms(load_db: bool) -> dict:
    path = DIR_PROCESADO / "firms_eventos_volcanicos_chile.parquet"
    frames = []
    errores = {}
    for evento in EVENTOS_VOLCANICOS:
        try:
            df = extraer_firms_archivo(
                sensor="MODIS_SP",
                fecha_inicio=evento["fecha_inicio"],
                fecha_fin=evento["fecha_fin"],
                guardar=False,
            )
            proc = transformar_firms(df, guardar=False)
            if not proc.empty:
                proc["evento_id"] = evento["id"]
                proc["evento_nombre"] = evento["nombre"]
                frames.append(proc)
        except Exception as exc:
            errores[evento["id"]] = str(exc)

    nuevo = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    consolidado = _guardar_merge(
        path,
        nuevo,
        ["latitud", "longitud", "fecha_adq", "hora_adq_hhmm", "satelite", "evento_id"],
    )
    metricas = {
        "nuevos": len(nuevo),
        "consolidado": len(consolidado),
        "eventos": [e["id"] for e in EVENTOS_VOLCANICOS],
        "errores": errores,
    }
    if load_db and not nuevo.empty:
        metricas["postgres"] = cargar_focos_calor(nuevo)
    return metricas


def guardar_catalogo_eventos() -> None:
    path = DIR_PROCESADO / "eventos_volcanicos_impacto_uruguay.parquet"
    df = pd.DataFrame(EVENTOS_VOLCANICOS)
    df["afecto_uruguay_documentado"] = True
    df["fuente_uruguay"] = "SINAE Uruguay"
    df.to_parquet(path, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-meteo", action="store_true")
    parser.add_argument("--skip-cams", action="store_true")
    parser.add_argument("--skip-chirps", action="store_true")
    parser.add_argument("--skip-firms-events", action="store_true")
    parser.add_argument("--no-load-db", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--event-windows", action="store_true", default=True)
    parser.add_argument("--pause", type=float, default=0.25)
    parser.add_argument("--meteo-start", default="2018-01-01")
    parser.add_argument("--meteo-end", default="2024-12-31")
    parser.add_argument("--cams-start", default="2018-01-01")
    parser.add_argument("--cams-end", default="2026-03-29")
    parser.add_argument("--chirps-start-year", type=int, default=2018)
    parser.add_argument("--chirps-end-year", type=int, default=2024)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_db = not args.no_load_db
    reporte = {
        "inicio": datetime.now(timezone.utc).isoformat(),
        "alcance": {
            "paises": sorted(PAISES_SA.keys()),
            "puntos": len(PUNTOS_METEO_SA),
        },
        "fuentes": {},
    }

    if load_db:
        reporte["postgres_dimensiones"] = asegurar_dimensiones_postgres()

    guardar_catalogo_eventos()

    if not args.skip_meteo:
        reporte["fuentes"]["meteo"] = backfill_meteo(args, load_db)
    if not args.skip_cams:
        reporte["fuentes"]["cams"] = backfill_cams(args, load_db)
    if not args.skip_chirps:
        reporte["fuentes"]["chirps"] = backfill_chirps(args, load_db)
    if not args.skip_firms_events:
        reporte["fuentes"]["firms_eventos_volcanicos"] = backfill_eventos_firms(load_db)

    reporte["fin"] = datetime.now(timezone.utc).isoformat()
    REPORTS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS / f"backfill_datos_reales_{stamp}.json"
    latest = REPORTS / "backfill_datos_reales_ultimo.json"
    path.write_text(json.dumps(reporte, indent=2, ensure_ascii=False), encoding="utf-8")
    latest.write_text(json.dumps(reporte, indent=2, ensure_ascii=False), encoding="utf-8")
    _log(f"Reporte guardado: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
