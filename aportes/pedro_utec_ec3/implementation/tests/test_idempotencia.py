import pandas as pd

from etl.transform.normalize import normalize


def test_dos_corridas_producen_las_mismas_claves_y_hashes():
    frame = pd.DataFrame([
        {"fecha": "2022-02-01", "pais": "ARG", "ubicacion": "Posadas", "precipitacion_mm": 10.2},
        {"fecha": "2022-03-01", "pais": "BRA", "ubicacion": "Porto_Alegre", "precipitacion_mm": 7.0},
    ])
    first, rejected_first = normalize("CHIRPS", frame)
    second, rejected_second = normalize("CHIRPS", frame.copy())
    hashes_first = {row["natural_key"]: row["record_hash"] for row in first}
    hashes_second = {row["natural_key"]: row["record_hash"] for row in second}
    metrics = {"antes": len(first), "despues": len(second), "duplicados_agregados": len(set(hashes_second) - set(hashes_first))}
    assert rejected_first == rejected_second == []
    assert metrics == {"antes": 2, "despues": 2, "duplicados_agregados": 0}
    assert hashes_first == hashes_second
