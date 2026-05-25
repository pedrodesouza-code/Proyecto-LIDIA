"""
Carga FIRMS desde shapefile local NASA.

Uso:
  python -m etl.cargar_firms_shapefile
  python -m etl.cargar_firms_shapefile --max-features 10000

La ruta por defecto se configura con FIRMS_SHAPEFILE_PATH en config/.env.
"""

from __future__ import annotations

import argparse
import time

from etl.extract.extract_firms import extraer_firms_shapefile
from etl.transform.transform_firms import transformar_firms
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.pipeline.firms_shapefile")


def ejecutar(max_features: int | None = None, cargar: bool = True, guardar: bool = True) -> None:
    t0 = time.perf_counter()
    df_raw = extraer_firms_shapefile(max_features=max_features, guardar=guardar)
    df_proc = transformar_firms(df_raw, guardar=guardar)

    if cargar:
        from etl.load.load_postgres import cargar_focos_calor

        metricas = cargar_focos_calor(df_proc)
        logger.info(
            f"FIRMS shapefile cargado: {metricas}",
            extra={"etl_stage": "load", "source": "firms_shapefile"},
        )
    else:
        logger.info(
            "FIRMS shapefile transformado sin carga a PostgreSQL",
            extra={"etl_stage": "pipeline", "source": "firms_shapefile"},
        )

    logger.info(
        f"Pipeline FIRMS shapefile finalizado en {time.perf_counter() - t0:.2f}s",
        extra={"etl_stage": "pipeline", "source": "firms_shapefile"},
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-features", type=int, default=None)
    parser.add_argument("--no-load", action="store_true")
    parser.add_argument("--save", action="store_true", help="Guarda Parquet aun si se usa --no-load")
    args = parser.parse_args()
    cargar = not args.no_load
    ejecutar(max_features=args.max_features, cargar=cargar, guardar=cargar or args.save)


if __name__ == "__main__":
    main()
