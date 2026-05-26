import pandas as pd
from pathlib import Path

from etl.transform.normalize import normalize


def test_firms_completitud_duplicados_y_rangos():
    raw = pd.DataFrame([
        {"fecha": "2024-01-01", "latitude": -32.0, "longitude": -56.0, "pais": "URY", "frp": 11.2, "confidence": 80},
        {"fecha": "2024-01-02", "latitude": -31.0, "longitude": -55.0, "pais": "URY", "frp": 4.2, "confidence": 70},
        {"fecha": None, "latitude": -31.0, "longitude": -55.0, "pais": "URY", "frp": 4.2},
        {"fecha": "2024-01-03", "latitude": -31.0, "longitude": -55.0, "pais": "URY", "frp": -4.2}
    ])
    accepted, rejected = normalize("FIRMS", raw)
    metrics = {"leidas": len(raw), "validas": len(accepted), "rechazadas": len(rejected)}
    assert metrics == {"leidas": 4, "validas": 2, "rechazadas": 2}
    assert len({row["natural_key"] for row in accepted}) == 2


def test_inumet_restringido_a_uruguay():
    raw = pd.DataFrame([
        {"fecha": "2023-01-01", "estacion": "Carrasco", "pais": "URY", "temperatura_c": 20},
        {"fecha": "2023-01-01", "estacion": "Exterior", "pais": "ARG", "temperatura_c": 20},
    ])
    accepted, rejected = normalize("INUMET", raw)
    assert (len(accepted), len(rejected)) == (1, 1)


def test_modelo_declara_integridad_referencial_y_restricciones():
    ddl = (Path(__file__).parents[1] / "sql" / "ddl" / "02_Schema.sql").read_text(encoding="utf-8")
    metrics = {
        "foreign_keys": ddl.count("REFERENCES dw."),
        "unique_constraints": ddl.count("UNIQUE"),
        "check_constraints": ddl.count("CHECK"),
    }
    assert "CREATE TABLE IF NOT EXISTS dw.fact_incendio" in ddl
    assert metrics["foreign_keys"] >= 8
    assert metrics["unique_constraints"] >= 8
    assert metrics["check_constraints"] >= 12
