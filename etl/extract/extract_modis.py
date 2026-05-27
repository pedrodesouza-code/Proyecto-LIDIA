"""Extraccion MODIS desde una exportacion real configurada."""

from __future__ import annotations

import pandas as pd
import geopandas as gpd
import shapely

from config.settings import FIRMS_COUNTRY_BOUNDARIES_FILE, ROOT
from etl.extract.base import read_source

IGBP_LABELS = {
    1: "Bosque siempreverde de coniferas", 2: "Bosque caducifolio de coniferas",
    3: "Bosque siempreverde de hoja ancha", 4: "Bosque caducifolio de hoja ancha",
    5: "Bosque mixto", 6: "Arbustal cerrado", 7: "Arbustal abierto",
    8: "Sabana arbolada", 9: "Sabana", 10: "Pastizal", 11: "Humedal permanente",
    12: "Tierra de cultivo", 13: "Zona urbana", 14: "Cultivo y vegetacion natural",
    15: "Nieve y hielo", 16: "Suelo desnudo o vegetacion escasa",
    17: "Cuerpo de agua", 255: "Sin clasificar",
}


def extract(path=None) -> pd.DataFrame:
    """Normaliza un archivo MODIS anual real; requiere MODIS_FILE."""
    frame = read_source("MODIS", path).copy()
    if "anio" not in frame.columns and "archivo" in frame.columns:
        frame["anio"] = frame["archivo"].astype(str).str.extract(r"(20\d{2})", expand=False)
    if "codigo_cobertura" not in frame.columns:
        source = "valor" if "valor" in frame.columns else "lc_type1"
        if source in frame.columns:
            frame["codigo_cobertura"] = pd.to_numeric(frame[source], errors="coerce")
    if "descripcion_cobertura" not in frame.columns and "codigo_cobertura" in frame.columns:
        frame["descripcion_cobertura"] = frame["codigo_cobertura"].map(IGBP_LABELS)
    if "pais" not in frame.columns and {"lat", "lon"}.issubset(frame.columns):
        boundary_path = (ROOT / FIRMS_COUNTRY_BOUNDARIES_FILE).resolve()
        countries = gpd.read_file(boundary_path)
        code = "ADM0_A3" if "ADM0_A3" in countries.columns else "ISO_A3"
        selected = countries[countries[code].isin(["URY", "ARG", "BRA"])]
        frame["pais"] = ""
        for _, country in selected.iterrows():
            inside = shapely.contains_xy(country.geometry, frame["lon"], frame["lat"])
            frame.loc[inside, "pais"] = country[code]
    return frame
