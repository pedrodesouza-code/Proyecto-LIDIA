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


def test_meteo_normaliza_variables_horarias_y_preserva_instantes():
    raw = pd.DataFrame([
        {
            "time": "2024-07-10T09:00:00Z", "pais": "URY", "ubicacion": "Montevideo",
            "temperature_2m": 14.2, "relative_humidity_2m": 80,
            "wind_speed_10m": 9.5, "wind_direction_10m": 225,
            "rain": 1.2, "surface_pressure": 1014.3,
        },
        {
            "time": "2024-07-10T10:00:00Z", "pais": "URY", "ubicacion": "Montevideo",
            "temperature_2m": 15.0, "relative_humidity_2m": 77,
            "wind_speed_10m": 10.1, "wind_direction_10m": 230,
            "rain": 0, "surface_pressure": 1013.9,
        },
    ])
    accepted, rejected = normalize("METEO", raw)
    assert rejected == []
    assert accepted[0]["fecha_hora_utc"].startswith("2024-07-10T09:00:00")
    assert accepted[0]["temperatura_c"] == 14.2
    assert accepted[0]["humedad_pct"] == 80
    assert accepted[0]["viento_kmh"] == 9.5
    assert accepted[0]["direccion_viento_grados"] == 225
    assert accepted[0]["precipitacion_mm"] == 1.2
    assert accepted[0]["presion_superficie_hpa"] == 1014.3
    assert accepted[0]["natural_key"] != accepted[1]["natural_key"]


def test_meteo_rechaza_direccion_y_presion_invalidas():
    invalid, rejected = normalize("FORECAST", pd.DataFrame([
        {"datetime": "2024-07-10T09:00:00Z", "pais": "BRA", "ubicacion": "Porto Alegre",
         "wind_direction_10m": 361, "surface_pressure": 1010},
        {"datetime": "2024-07-10T10:00:00Z", "pais": "BRA", "ubicacion": "Porto Alegre",
         "wind_direction_10m": 10, "surface_pressure": 0},
    ]))
    assert invalid == []
    assert len(rejected) == 2


def test_firms_brightness_se_modela_como_brillo_termico():
    accepted, rejected = normalize("FIRMS", pd.DataFrame([
        {"fecha": "2024-01-01", "latitude": -32, "longitude": -56, "pais": "URY",
         "brightness": 335.4, "frp": 5.1}
    ]))
    assert rejected == []
    assert accepted[0]["brillo_termico"] == 335.4
    assert "temperatura_c" not in accepted[0]


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
    assert "fecha_hora_utc TIMESTAMPTZ" in ddl
    assert "direccion_viento_grados" in ddl
    assert "presion_superficie_hpa" in ddl
    assert "brillo_termico" in ddl
