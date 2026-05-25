"""
Simulacion de sharding para SINIA-UY.

La consigna permite simular un escenario de alto volumen cuando el volumen real
no justifica sharding operativo. Este script toma FIRMS procesado y calcula dos
estrategias defendibles:

1. SQL/Data Warehouse: shard temporal por trimestre de `fecha_adq`.
2. MongoDB: shard compuesto por `fecha` mensual + hash conceptual de `pais`.

Salida:
  reports/sharding_simulado_YYYYMMDD_HHMMSS.json
  reports/sharding_simulado_ultimo.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"


def _bucket_pais(pais: str, buckets: int = 4) -> int:
    digest = hashlib.sha256(str(pais).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % buckets


def simular() -> dict:
    firms = pd.read_parquet(DATA / "firms_procesado.parquet")
    fechas = pd.to_datetime(firms["fecha_adq"])
    trabajo = firms[["pais", "fecha_adq"]].copy()
    trabajo["fecha"] = fechas
    trabajo["shard_sql_trimestre"] = fechas.dt.to_period("Q").astype(str)
    trabajo["shard_mongo_mes"] = fechas.dt.to_period("M").astype(str)
    trabajo["bucket_pais_hash"] = trabajo["pais"].map(_bucket_pais)
    trabajo["shard_mongo_compuesto"] = (
        trabajo["shard_mongo_mes"] + "_b" + trabajo["bucket_pais_hash"].astype(str)
    )

    sql_dist = trabajo.groupby("shard_sql_trimestre").size().sort_index()
    mongo_dist = trabajo.groupby("shard_mongo_compuesto").size().sort_values(ascending=False)

    def resumen(serie: pd.Series) -> dict:
        return {
            "shards": int(serie.shape[0]),
            "registros_total": int(serie.sum()),
            "min_registros": int(serie.min()),
            "max_registros": int(serie.max()),
            "promedio_registros": round(float(serie.mean()), 2),
            "desbalance_max_promedio": round(float(serie.max() / serie.mean()), 3),
        }

    ejemplo_rango = trabajo[
        (trabajo["fecha"] >= "2024-01-01") & (trabajo["fecha"] <= "2024-03-31")
    ]

    return {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "fuente": "data/processed/firms_procesado.parquet",
        "filas_firms": int(len(trabajo)),
        "sql_sharding": {
            "tabla_candidata": "focos_calor",
            "shard_key": "fecha_adq",
            "estrategia": "particionamiento por rango trimestral",
            "justificacion": (
                "La mayoria de consultas analiticas filtran o agregan por fecha; "
                "la clave permite pruning temporal y mantiene alta cardinalidad."
            ),
            "resumen_distribucion": resumen(sql_dist),
            "top_5_shards_mas_grandes": sql_dist.sort_values(ascending=False).head(5).to_dict(),
            "shards_consultados_ejemplo_2024_Q1": sorted(ejemplo_rango["shard_sql_trimestre"].unique().tolist()),
        },
        "mongo_sharding": {
            "coleccion_candidata": "focos_snapshots",
            "shard_key": "{ fecha: 1, pais: 'hashed' }",
            "estrategia": "rango temporal mensual + hash conceptual de pais",
            "justificacion": (
                "La fecha permite consultas por ventana temporal y el hash de pais "
                "reduce concentracion de escrituras en un unico shard reciente."
            ),
            "resumen_distribucion": resumen(mongo_dist),
            "top_5_shards_mas_grandes": mongo_dist.head(5).to_dict(),
        },
        "decision_operativa": (
            "No se activa sharding real en el entorno local porque el volumen cabe en "
            "un nodo y agregaria complejidad operativa. La simulacion deja elegidas "
            "tabla/coleccion, shard key, distribucion esperada y patron de consulta."
        ),
    }


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    reporte = simular()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = REPORTS / f"sharding_simulado_{stamp}.json"
    ultimo = REPORTS / "sharding_simulado_ultimo.json"
    texto = json.dumps(reporte, ensure_ascii=False, indent=2, default=str)
    destino.write_text(texto, encoding="utf-8")
    ultimo.write_text(texto, encoding="utf-8")
    print(f"Reporte generado: {destino}")
    print(json.dumps({
        "filas_firms": reporte["filas_firms"],
        "sql_shards": reporte["sql_sharding"]["resumen_distribucion"]["shards"],
        "mongo_shards_logicos": reporte["mongo_sharding"]["resumen_distribucion"]["shards"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
