import pandas as pd

from etl.transform.normalize import cdc_kind, normalize


def test_cdc_detecta_alta_y_modificacion():
    original, _ = normalize("METEO", pd.DataFrame([
        {"fecha": "2024-08-01", "pais": "URY", "ubicacion": "Montevideo", "temperatura_c": 18.0}
    ]))
    modified, _ = normalize("METEO", pd.DataFrame([
        {"fecha": "2024-08-01", "pais": "URY", "ubicacion": "Montevideo", "temperatura_c": 21.0}
    ]))
    counts = {"alta": 0, "modificacion": 0, "sin_cambio": 0}
    counts[cdc_kind(None, original[0]["record_hash"])] += 1
    counts[cdc_kind(original[0]["record_hash"], modified[0]["record_hash"])] += 1
    assert counts == {"alta": 1, "modificacion": 1, "sin_cambio": 0}


def test_cdc_detecta_sin_cambio():
    rows, _ = normalize("MODIS", pd.DataFrame([
        {"anio": 2021, "pais": "BRA", "ubicacion": "Campo_Grande", "codigo_cobertura": 10}
    ]))
    assert cdc_kind(rows[0]["record_hash"], rows[0]["record_hash"]) == "sin_cambio"


def test_cdc_meteo_horario_no_colisiona_en_el_mismo_dia():
    rows, rejected = normalize("METEO", pd.DataFrame([
        {"time": "2024-08-01T01:00:00Z", "pais": "URY", "ubicacion": "Carrasco", "temperature_2m": 10},
        {"time": "2024-08-01T02:00:00Z", "pais": "URY", "ubicacion": "Carrasco", "temperature_2m": 11},
    ]))
    assert rejected == []
    assert len({row["natural_key"] for row in rows}) == 2
