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


def test_extract_inumet_une_csv_reales_y_filtra_periodo(tmp_path, monkeypatch):
    from etl.extract import extract_inumet

    temperature = tmp_path / "temperatura.csv"
    humidity = tmp_path / "humedad.csv"
    temperature.write_text(
        "fecha;estacion_id;temp_aire\n"
        "2025-01-01 00:00:00;Prueba G3;19.4\n"
        "2026-01-01 00:00:00;Prueba G3;20.0\n",
        encoding="utf-8",
    )
    humidity.write_text(
        "fecha;estacion_id;hum_relativa\n"
        "2025-01-01 00:00:00;Prueba G3;71\n"
        "2026-01-01 00:00:00;Prueba G3;72\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(extract_inumet, "INUMET_TEMPERATURA_FILE", str(temperature))
    monkeypatch.setattr(extract_inumet, "INUMET_HUMEDAD_FILE", str(humidity))
    monkeypatch.setattr(
        extract_inumet,
        "STATIONS",
        {"Prueba G3": {"departamento": "Montevideo", "lat": -34.79, "lon": -56.26}},
    )

    frame = extract_inumet.extract()
    accepted, rejected = normalize("INUMET", frame)
    assert len(frame) == 1
    assert rejected == []
    assert accepted[0]["pais_codigo"] == "URY"
    assert accepted[0]["temperatura_c"] == 19.4
    assert accepted[0]["humedad_pct"] == 71


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


def test_chirps_conserva_coordenadas_para_dimension_precipitacion():
    accepted, rejected = normalize("CHIRPS", pd.DataFrame([
        {"fecha": "2024-01-01", "pais": "BRA", "punto": "Porto_Alegre",
         "lat": -30.03, "lon": -51.23, "precipitacion_mm": 42.5}
    ]))
    assert rejected == []
    assert accepted[0]["latitud"] == -30.03
    assert accepted[0]["longitud"] == -51.23


def test_modis_serializa_nulos_como_json_valido():
    accepted, rejected = normalize("MODIS", pd.DataFrame([
        {"anio": 2024, "pais": "URY", "punto": "Rocha G3", "lat": -34.49, "lon": -54.31,
         "valor": 10, "descripcion_cobertura": float("nan")}
    ]))
    assert rejected == []
    assert accepted[0]["raw_payload"]["descripcion_cobertura"] is None


def test_extract_meteo_api_conserva_variables_y_pais(monkeypatch):
    from etl.extract import extract_meteo

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"hourly": {
                "time": ["2024-01-01T00:00"], "temperature_2m": [20.0],
                "relative_humidity_2m": [50], "wind_speed_10m": [5.0],
                "wind_direction_10m": [90], "rain": [0.0], "surface_pressure": [1000],
            }}

    monkeypatch.setattr(extract_meteo, "PUNTOS_MONITOREO", {"Montevideo": {"lat": -34.9, "lon": -56.2, "pais": "URY"}})
    monkeypatch.setattr(extract_meteo.requests, "get", lambda *args, **kwargs: Response())
    frame = extract_meteo.extract()
    accepted, rejected = normalize("METEO", frame)
    assert rejected == []
    assert accepted[0]["pais_codigo"] == "URY"
    assert accepted[0]["temperatura_c"] == 20.0


def test_extract_forecast_queda_identificado_como_forecast(monkeypatch):
    from etl.extract import extract_forecast

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"hourly": {
                "time": ["2026-05-27T00:00"], "temperature_2m": [18.0],
                "relative_humidity_2m": [65], "wind_speed_10m": [8.0],
                "wind_direction_10m": [180], "rain": [1.0], "surface_pressure": [1005],
            }}

    monkeypatch.setattr(extract_forecast, "PUNTOS_MONITOREO", {"Rivera": {"lat": -30.9, "lon": -55.5, "pais": "URY"}})
    monkeypatch.setattr(extract_forecast.requests, "get", lambda *args, **kwargs: Response())
    frame = extract_forecast.extract()
    accepted, rejected = normalize("FORECAST", frame)
    assert rejected == []
    assert accepted[0]["fuente"] == "FORECAST"


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


def test_asociacion_ambiental_usa_haversine_pais_y_periodos():
    root = Path(__file__).parents[1]
    ddl = (root / "sql" / "ddl" / "02_Schema.sql").read_text(encoding="utf-8")
    loader = (root / "etl" / "load" / "postgres.py").read_text(encoding="utf-8")
    assert "dw.distancia_haversine_km" in ddl
    assert "nearest_neighbor_haversine" in loader
    assert "ambiente.pais_codigo=foco.pais_codigo" in loader
    assert "lluvia.pais_codigo=foco.pais_codigo" in loader
    assert "cobertura.pais_codigo=foco.pais_codigo" in loader
    assert "fecha_lluvia.anio=fecha_foco.anio AND fecha_lluvia.mes=fecha_foco.mes" in loader
    assert "c.anio=fecha_foco.anio" in loader
    assert '"INUMET": 150.0' in loader
