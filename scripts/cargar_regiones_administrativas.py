"""Carga regiones administrativas reales y asigna `dw.dim_ubicacion.region`.

Uso previsto:

    PYTHONPATH=. python3 scripts/cargar_regiones_administrativas.py \
        --file data/reference/departamentos_uruguay.geojson \
        --pais URY \
        --nivel departamento \
        --region-column NOMBRE \
        --fuente-cartografica "Fuente oficial ..."

El script no inventa geometrías ni usa bounding boxes. Si no existe una capa
cartográfica real, falla con un mensaje claro y no actualiza departamentos.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2 import Binary

from config.settings import PG_CONFIG


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DDL = ROOT / "sql" / "ddl" / "06_regiones_administrativas.sql"
DEFAULT_OFFICIAL_OUTPUT = ROOT / "data" / "reference" / "uruguay_departamentos" / "departamentos_uruguay.geojson"
IDE_UY_DEPARTAMENTOS_URL = (
    "https://lastmile.presidencia.gub.uy/arcgis/rest/services/Hosted/"
    "Departamentos/FeatureServer/0/query"
    "?where=1%3D1&outFields=*&returnGeometry=true&f=geojson&outSR=4326"
)


def _candidate_region_column(columns: list[str]) -> str | None:
    preferred = [
        "region",
        "departamento",
        "nombre",
        "name",
        "nam",
        "depto",
        "nomdep",
        "nombre_departamento",
        "admlnm",
        "departamen",
        "departamento_nombre",
    ]
    lookup = {column.lower(): column for column in columns}
    for name in preferred:
        if name in lookup:
            return lookup[name]
    return None


def _read_layer(path: Path):
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise RuntimeError(
            "geopandas no está instalado. Instale requirements.txt para cargar capas geográficas."
        ) from exc

    frame = gpd.read_file(path)
    if frame.empty:
        raise ValueError(f"La capa geográfica no tiene registros: {path}")
    if frame.crs is None:
        raise ValueError("La capa no declara CRS. Se requiere CRS conocido para reproyectar a EPSG:4326.")
    return frame.to_crs(4326)


def download_official_departments(output: Path) -> Path:
    """Descarga una capa poligonal oficial si el servicio IDE/ArcGIS responde.

    La descarga es opcional y controlada: si el servicio no devuelve GeoJSON
    válido, el script falla y no crea geometrías alternativas.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        IDE_UY_DEPARTAMENTOS_URL,
        headers={"Accept": "application/geo+json, application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "No se pudo descargar la capa oficial de departamentos desde IDE/ArcGIS. "
            "Descargue manualmente una capa Polygon/MultiPolygon real y use --file."
        ) from exc

    try:
        data = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "El servicio oficial no devolvió GeoJSON válido. "
            "Descargue manualmente una capa Polygon/MultiPolygon real y use --file."
        ) from exc

    if data.get("type") != "FeatureCollection" or not data.get("features"):
        raise RuntimeError(
            "La descarga oficial no contiene una FeatureCollection con departamentos. "
            "No se carga ninguna región."
        )
    output.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return output


def _ensure_postgis(cur) -> None:
    cur.execute(DEFAULT_DDL.read_text(encoding="utf-8"))
    cur.execute("SELECT to_regclass('dw.ref_region_administrativa') IS NOT NULL")
    if not cur.fetchone()[0]:
        raise RuntimeError("PostGIS no está disponible o no se pudo crear dw.ref_region_administrativa.")


def _normalize_geometry(geometry: Any):
    try:
        from shapely.geometry import MultiPolygon
    except ImportError as exc:
        raise RuntimeError("shapely no está instalado. Instale requirements.txt.") from exc

    if geometry is None or geometry.is_empty:
        return None
    if geometry.geom_type == "Polygon":
        return MultiPolygon([geometry])
    if geometry.geom_type == "MultiPolygon":
        return geometry
    return None


def _geometry_types(frame) -> dict[str, int]:
    return {str(key): int(value) for key, value in frame.geometry.geom_type.value_counts().to_dict().items()}


def load_regions(
    path: Path,
    pais: str,
    nivel: str,
    region_column: str | None,
    fuente_cartografica: str,
) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"No existe la capa geográfica: {path}. "
            "Suba un GeoJSON/Shapefile/GPKG real de departamentos antes de ejecutar."
        )

    frame = _read_layer(path)
    geometry_types = _geometry_types(frame)
    if not any(kind in geometry_types for kind in ("Polygon", "MultiPolygon")):
        raise ValueError(
            "La capa geográfica no contiene polígonos. "
            f"Tipos encontrados: {geometry_types}. "
            "Para asignar departamentos por point-in-polygon se requiere Polygon/MultiPolygon; "
            "no se usan límites lineales ni bounding boxes."
        )
    column = region_column or _candidate_region_column([str(column) for column in frame.columns])
    if not column or column not in frame.columns:
        raise ValueError(
            "No se pudo detectar columna de región/departamento. "
            f"Columnas disponibles: {list(map(str, frame.columns))}"
        )

    loaded = 0
    skipped = 0
    updated_locations = 0
    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            _ensure_postgis(cur)
            for _, row in frame.iterrows():
                region = str(row[column] or "").strip()
                geometry = _normalize_geometry(row.geometry)
                if not region or geometry is None:
                    skipped += 1
                    continue
                cur.execute(
                    """
                    INSERT INTO dw.ref_region_administrativa
                        (pais_codigo, region, nivel_administrativo, fuente_cartografica, geom)
                    VALUES (%s, %s, %s, %s, ST_GeomFromWKB(%s, 4326))
                    ON CONFLICT (pais_codigo, region, nivel_administrativo) DO UPDATE
                    SET fuente_cartografica = EXCLUDED.fuente_cartografica,
                        geom = EXCLUDED.geom
                    """,
                    (pais, region, nivel, fuente_cartografica, Binary(geometry.wkb)),
                )
                loaded += 1
            if loaded == 0:
                raise ValueError(
                    "No se cargó ninguna región administrativa. "
                    f"Tipos de geometría encontrados: {geometry_types}. "
                    "Verifique que la capa tenga polígonos y nombres de departamento."
                )
            cur.execute("SELECT ubicaciones_actualizadas FROM dw.actualizar_region_ubicacion_desde_poligonos()")
            updated_locations = int(cur.fetchone()[0])
        conn.commit()
    return {
        "archivo": str(path),
        "pais_codigo": pais,
        "nivel_administrativo": nivel,
        "columna_region": column,
        "regiones_cargadas": loaded,
        "geometrias_omitidas": skipped,
        "ubicaciones_actualizadas": updated_locations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga regiones administrativas reales en PostGIS.")
    parser.add_argument("--file", default=os.getenv("LIDIA_REGION_ADMIN_FILE", ""))
    parser.add_argument(
        "--download-ide-uy",
        action="store_true",
        help="Descarga la capa oficial poligonal de departamentos si el servicio IDE/ArcGIS responde.",
    )
    parser.add_argument(
        "--download-output",
        default=os.getenv("LIDIA_REGION_ADMIN_DOWNLOAD_OUTPUT", str(DEFAULT_OFFICIAL_OUTPUT)),
    )
    parser.add_argument("--pais", default=os.getenv("LIDIA_REGION_ADMIN_PAIS", "URY"))
    parser.add_argument("--nivel", default=os.getenv("LIDIA_REGION_ADMIN_NIVEL", "departamento"))
    parser.add_argument("--region-column", default=os.getenv("LIDIA_REGION_ADMIN_COLUMN", ""))
    parser.add_argument(
        "--fuente-cartografica",
        default=os.getenv("LIDIA_REGION_ADMIN_FUENTE", "Capa administrativa real provista localmente"),
    )
    parser.add_argument(
        "--log",
        default=str(ROOT / "evidencia" / "logs" / "carga_regiones_administrativas.log"),
    )
    args = parser.parse_args()

    selected_file = args.file
    if args.download_ide_uy:
        selected_file = str(download_official_departments(Path(args.download_output).expanduser()))

    if not selected_file:
        raise SystemExit(
            "Falta LIDIA_REGION_ADMIN_FILE o --file. "
            "No se encontró una capa real de departamentos; no se asignan regiones por coordenadas."
        )

    result = load_regions(
        Path(selected_file).expanduser(),
        args.pais.strip().upper(),
        args.nivel.strip().lower(),
        args.region_column.strip() or None,
        args.fuente_cartografica.strip(),
    )
    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
