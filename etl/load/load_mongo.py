"""
SINIA-UY — Cargador de datos hacia MongoDB
==========================================
Justificación del caso de uso NoSQL:
  MongoDB almacena documentos auto-contenidos de naturaleza variable:
    1. ejecuciones_etl  -> logs flexibles del pipeline (esquema variable por etapa)
    2. alertas          -> eventos de alerta con estructura semi-estructurada
    3. focos_snapshots  -> snapshots diarios con array de focos embebido
                          (evita joins para consultas de estado de un día)

  Razón técnica: estos datos tienen esquemas que evolucionan, contienen arrays
  embebidos o requieren escritura rápida sin esquema rígido. PostgreSQL
  maneja los datos analíticos estructurados; MongoDB maneja los operacionales
  y flexibles. Complementación real, no redundancia.

Estrategia CDC:
  - update_one con upsert=True por campo _id compuesto (fecha + fuente)
  - Snapshots de focos: replace_one por fecha (idempotente)
  - Alertas: insert_one sin duplicate (se registran como eventos nuevos)
"""

from __future__ import annotations

import os
import socket
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.settings import MONGO_CONFIG
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.load.mongo")

VERSION_PIPELINE = "1.0.0"


# =============================================================================
# CONEXIÓN Y SETUP
# =============================================================================

def get_client() -> MongoClient:
    """Crea y devuelve un MongoClient según MONGO_CONFIG."""
    uri = (
        f"mongodb://{MONGO_CONFIG['user']}:{MONGO_CONFIG['password']}"
        f"@{MONGO_CONFIG['host']}:{MONGO_CONFIG['port']}"
        f"/{MONGO_CONFIG['database']}?authSource={os.getenv('MONGO_AUTH_SOURCE', MONGO_CONFIG['database'])}"
        if MONGO_CONFIG.get("user") and MONGO_CONFIG.get("password")
        else f"mongodb://{MONGO_CONFIG['host']}:{MONGO_CONFIG['port']}"
    )
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def get_db():
    """Devuelve la base de datos MongoDB configurada."""
    client = get_client()
    return client[MONGO_CONFIG["database"]]


def crear_colecciones_con_schema() -> None:
    """
    Crea las colecciones con validación JSON Schema si no existen.
    Crea también los índices operativos.
    Idempotente: no falla si ya existen.
    """
    import json

    db = get_db()
    schemas_dir = Path(__file__).resolve().parent.parent.parent / "nosql" / "schemas"

    colecciones_config = {
        "ejecuciones_etl":  "ejecuciones_etl_schema.json",
        "alertas":          "alertas_schema.json",
        "focos_snapshots":  "focos_snapshot_schema.json",
    }

    for nombre_col, archivo_schema in colecciones_config.items():
        ruta = schemas_dir / archivo_schema
        if not ruta.exists():
            logger.warning(f"Schema no encontrado: {ruta}")
            continue

        with open(ruta, encoding="utf-8") as f:
            schema = json.load(f)

        colecciones_existentes = db.list_collection_names()

        if nombre_col not in colecciones_existentes:
            db.create_collection(
                nombre_col,
                validator=schema,
                validationLevel="moderate",   # moderate: valida inserts y updates explícitos
                validationAction="warn",      # warn: registra violaciones pero no rechaza
            )
            logger.info(f"Colección creada: {nombre_col}")
        else:
            # Actualizar validador si ya existe. En servidores académicos puede
            # no haber permisos para collMod; en ese caso seguimos sin fallar.
            try:
                db.command(
                    "collMod",
                    nombre_col,
                    validator=schema,
                    validationLevel="moderate",
                    validationAction="warn",
                )
                logger.info(f"Colección ya existe, validador actualizado: {nombre_col}")
            except Exception as exc:
                logger.warning(
                    f"No se pudo actualizar el validador de {nombre_col}: {exc}"
                )

    # ── Índices ───────────────────────────────────────────────────────────────
    col_etl: Collection = db["ejecuciones_etl"]
    col_etl.create_index([("fuente", ASCENDING), ("iniciado_en", DESCENDING)],
                         name="idx_fuente_inicio")
    col_etl.create_index([("estado", ASCENDING)], name="idx_estado")

    col_alertas: Collection = db["alertas"]
    col_alertas.create_index([("fecha_generacion", DESCENDING)], name="idx_fecha_gen")
    col_alertas.create_index([("tipo_alerta", ASCENDING), ("nivel", ASCENDING)],
                              name="idx_tipo_nivel")
    col_alertas.create_index([("activa", ASCENDING)],
                              partialFilterExpression={"activa": True},
                              name="idx_activas")

    col_snap: Collection = db["focos_snapshots"]
    col_snap.create_index([("fecha", DESCENDING)], unique=True, name="idx_fecha_unico")

    logger.info("Colecciones e índices MongoDB configurados correctamente")


# =============================================================================
# HELPERS
# =============================================================================

def _safe(v: Any) -> Any:
    """Convierte tipos numpy/pandas a tipos nativos Python para MongoDB."""
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, float) and np.isnan(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def _a_datetime(v: Any) -> datetime | None:
    """Convierte date/string a datetime UTC para MongoDB."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day, tzinfo=timezone.utc)
    try:
        return pd.to_datetime(v).to_pydatetime().replace(tzinfo=timezone.utc)
    except Exception:
        return None


# =============================================================================
# COLECCIÓN 1: ejecuciones_etl
# =============================================================================

def registrar_ejecucion_etl(
    fuente: str,
    etapa: str,
    tipo_carga: str,
    estado: str,
    metricas: dict | None = None,
    mensaje: str | None = None,
    duracion_segundos: float | None = None,
    rango_datos: dict | None = None,
) -> str:
    """
    Registra una ejecución ETL en MongoDB.

    Returns:
        ID del documento insertado (string).
    """
    db = get_db()
    doc = {
        "fuente":             fuente,
        "etapa":              etapa,
        "tipo_carga":         tipo_carga,
        "estado":             estado,
        "iniciado_en":        datetime.now(timezone.utc),
        "finalizado_en":      datetime.now(timezone.utc),
        "duracion_segundos":  duracion_segundos,
        "metricas":           metricas or {},
        "rango_datos":        rango_datos or {},
        "errores":            [] if estado == "ok" else [{"mensaje": mensaje}],
        "host":               socket.gethostname(),
        "version_pipeline":   VERSION_PIPELINE,
    }

    result = db["ejecuciones_etl"].insert_one(doc)
    logger.info(
        f"Ejecución ETL registrada en MongoDB: {fuente}/{etapa} [{estado}]",
        extra={"etl_stage": etapa, "source": fuente},
    )
    return str(result.inserted_id)


# =============================================================================
# COLECCIÓN 2: alertas
# =============================================================================

def registrar_alerta(
    tipo_alerta: str,
    nivel: str,
    fuente: str,
    puntos_afectados: list[dict],
    indicadores: dict | None = None,
    mensaje: str | None = None,
) -> str:
    """
    Registra un evento de alerta en MongoDB.
    Las alertas son inmutables: siempre se insertan como nuevos documentos.

    Returns:
        ID del documento insertado.
    """
    db = get_db()
    doc = {
        "tipo_alerta":       tipo_alerta,
        "fecha_generacion":  datetime.now(timezone.utc),
        "fuente":            fuente,
        "nivel":             nivel,
        "puntos_afectados":  puntos_afectados,
        "indicadores":       indicadores or {},
        "mensaje":           mensaje or "",
        "activa":            True,
        "resuelta_en":       None,
    }

    result = db["alertas"].insert_one(doc)
    logger.info(
        f"Alerta registrada: {tipo_alerta} [{nivel}] — {len(puntos_afectados)} punto(s)",
        extra={"etl_stage": "load", "source": "alertas"},
    )
    return str(result.inserted_id)


def evaluar_y_registrar_alertas(df_meteo: pd.DataFrame, df_focos: pd.DataFrame | None = None) -> int:
    """
    Evalúa condiciones de alerta a partir de los datos recientes y registra en MongoDB.

    Umbrales:
      - Alerta meteorológica: indice_riesgo >= 0.65 en cualquier punto
      - Alerta focos: 10 o más focos detectados en las últimas 24h

    Returns:
        Número de alertas generadas.
    """
    alertas_generadas = 0

    # ── Alerta meteorológica ──────────────────────────────────────────────────
    if not df_meteo.empty and "indice_riesgo" in df_meteo.columns:
        criticos = df_meteo[df_meteo["indice_riesgo"] >= 0.65]
        if not criticos.empty:
            puntos = [
                {
                    "nombre":          str(row.get("punto", "")),
                    "valor_indicador": float(_safe(row.get("indice_riesgo", 0)) or 0),
                    "nivel_punto":     str(row.get("nivel_riesgo", "")),
                }
                for _, row in criticos.iterrows()
            ]
            nivel = "muy_alto" if criticos["indice_riesgo"].max() >= 0.75 else "alto"
            registrar_alerta(
                tipo_alerta="riesgo_meteorologico",
                nivel=nivel,
                fuente="open-meteo",
                puntos_afectados=puntos,
                indicadores={
                    "indice_riesgo_max": float(criticos["indice_riesgo"].max()),
                    "temperatura_max":   float(criticos.get("temperature_2m_max", pd.Series([0])).max() or 0),
                },
                mensaje=f"Riesgo {nivel} en {len(puntos)} punto(s)",
            )
            alertas_generadas += 1

    # ── Alerta por focos ──────────────────────────────────────────────────────
    if df_focos is not None and not df_focos.empty:
        hoy = pd.Timestamp.now().date()
        if "fecha_adq" in df_focos.columns:
            focos_hoy = df_focos[pd.to_datetime(df_focos["fecha_adq"]).dt.date == hoy]
            if len(focos_hoy) >= 10:
                registrar_alerta(
                    tipo_alerta="focos_detectados",
                    nivel="alto",
                    fuente="firms",
                    puntos_afectados=[
                        {"nombre": "Sudamérica", "valor_indicador": float(len(focos_hoy))}
                    ],
                    indicadores={
                        "focos_detectados": int(len(focos_hoy)),
                        "frp_max": float(_safe(focos_hoy["potencia_radiativa"].max()) or 0),
                    },
                    mensaje=f"{len(focos_hoy)} focos detectados el {hoy}",
                )
                alertas_generadas += 1

    return alertas_generadas


# =============================================================================
# COLECCIÓN 3: focos_snapshots
# =============================================================================

def guardar_snapshot_focos(df_focos: pd.DataFrame, df_meteo: pd.DataFrame | None = None) -> int:
    """
    Guarda un snapshot diario de focos en MongoDB.
    Idempotente: replace_one por fecha.

    El snapshot es un documento auto-contenido con todos los focos del día
    más un resumen del riesgo meteorológico del mismo día.
    Este modelo evita joins para consultas como "¿qué pasó el día X?".

    Returns:
        Número de snapshots guardados (1 por día único).
    """
    if df_focos.empty:
        return 0

    db = get_db()
    col: Collection = db["focos_snapshots"]

    snapshots = 0

    if "fecha_adq" in df_focos.columns:
        df_focos = df_focos.copy()
        df_focos["fecha_adq"] = pd.to_datetime(df_focos["fecha_adq"])

        for fecha_dt, grupo in df_focos.groupby(df_focos["fecha_adq"].dt.date):
            focos_lista = []
            for _, row in grupo.iterrows():
                focos_lista.append({
                    "pais":               _safe(row.get("pais")),
                    "latitud":            _safe(row.get("latitud")),
                    "longitud":           _safe(row.get("longitud")),
                    "hora_adq_hhmm":      _safe(row.get("hora_adq_hhmm")),
                    "potencia_radiativa": _safe(row.get("potencia_radiativa")),
                    "confianza_raw":      _safe(row.get("confianza_raw")),
                    "confianza_num":      _safe(row.get("confianza_num")),
                    "satelite":           _safe(row.get("satelite")),
                    "es_diurno":          _safe(row.get("es_diurno")),
                })

            frp_vals = grupo["potencia_radiativa"].dropna() if "potencia_radiativa" in grupo else pd.Series()

            riesgo_dia = {}
            if df_meteo is not None and not df_meteo.empty and "indice_riesgo" in df_meteo.columns:
                subset = df_meteo[pd.to_datetime(df_meteo.get("fecha", pd.Series())).dt.date == fecha_dt] \
                    if "fecha" in df_meteo.columns else pd.DataFrame()
                if not subset.empty:
                    riesgo_dia = {
                        "indice_promedio_todos_puntos": float(subset["indice_riesgo"].mean()),
                        "nivel_maximo": str(subset["nivel_riesgo"].max()),
                        "puntos_en_alto_riesgo": int(
                            subset["nivel_riesgo"].isin(["alto", "muy_alto"]).sum()
                        ),
                    }

            doc = {
                "fecha":        datetime(fecha_dt.year, fecha_dt.month, fecha_dt.day, tzinfo=timezone.utc),
                "generado_en":  datetime.now(timezone.utc),
                "total_focos":  len(focos_lista),
                "resumen": {
                    "frp_promedio":         float(frp_vals.mean()) if not frp_vals.empty else None,
                    "frp_maximo":           float(frp_vals.max())  if not frp_vals.empty else None,
                    "focos_alta_confianza": int(grupo.get("confianza_num", pd.Series()).eq(3).sum()),
                    "focos_diurnos":        int(grupo.get("es_diurno", pd.Series(dtype=bool)).sum()),
                    "focos_nocturnos":      int((~grupo.get("es_diurno", pd.Series(dtype=bool))).sum()),
                },
                "focos":        focos_lista,
                "riesgo_del_dia": riesgo_dia,
            }

            col.replace_one({"fecha": doc["fecha"]}, doc, upsert=True)
            snapshots += 1

    logger.info(
        f"focos_snapshots: {snapshots} snapshots guardados en MongoDB",
        extra={"etl_stage": "load", "source": "firms"},
    )
    return snapshots


# =============================================================================
# PIPELINE COMPLETO MONGO
# =============================================================================

def ejecutar_carga_mongo() -> None:
    """Ejecuta setup de colecciones y carga de snapshots desde parquets procesados."""
    from config.settings import DIR_PROCESADO

    logger.info("=== INICIO CARGA MONGODB ===", extra={"etl_stage": "load", "source": "mongo"})

    # Setup inicial de colecciones y schemas
    crear_colecciones_con_schema()

    # Cargar snapshots de focos
    ruta_firms = DIR_PROCESADO / "firms_procesado.parquet"
    # Intentamos cargar meteo de cualquier punto disponible (primer parquet encontrado)
    _meteo_parquets = sorted(DIR_PROCESADO.glob("meteo_procesado_*.parquet"))
    ruta_meteo = _meteo_parquets[0] if _meteo_parquets else None

    df_focos = pd.read_parquet(ruta_firms) if ruta_firms.exists() else pd.DataFrame()
    df_meteo = pd.read_parquet(ruta_meteo) if ruta_meteo and Path(ruta_meteo).exists() else pd.DataFrame()

    if not df_focos.empty:
        n = guardar_snapshot_focos(df_focos, df_meteo)
        logger.info(f"Snapshots creados: {n}")

        # Registrar la ejecución
        registrar_ejecucion_etl(
            fuente="firms",
            etapa="load",
            tipo_carga="inicial" if n > 0 else "incremental",
            estado="ok",
            metricas={"registros_procesados": len(df_focos), "snapshots_generados": n},
        )

    logger.info("=== CARGA MONGODB COMPLETADA ===", extra={"etl_stage": "load", "source": "mongo"})


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SINIA-UY — Carga a MongoDB")
    print("=" * 60)
    ejecutar_carga_mongo()
    print("\nCarga completada. Revisá los logs para detalles.")
