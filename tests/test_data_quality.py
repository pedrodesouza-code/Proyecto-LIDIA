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


def test_firms_descarta_chile_fuera_del_alcance():
    raw = pd.DataFrame([
        {"fecha_adq": "2026-05-11", "latitud": -32.0, "longitud": -56.0, "pais": "URY", "potencia_radiativa": 11.2},
        {"fecha_adq": "2026-05-11", "latitud": -33.4, "longitud": -70.6, "pais": "CHL", "potencia_radiativa": 8.1},
    ])
    accepted, rejected = normalize("FIRMS", raw)
    assert len(accepted) == 1
    assert accepted[0]["pais_codigo"] == "URY"
    assert len(rejected) == 1
    assert rejected[0]["motivo"] == "pais fuera del alcance URY/ARG/BRA"


def test_firms_solo_acepta_paises_del_alcance_lidia():
    raw = pd.DataFrame([
        {"fecha_adq": "2026-05-11", "latitud": -30.0, "longitud": -51.0, "pais": "BRA", "potencia_radiativa": 5.0},
        {"fecha_adq": "2026-05-11", "latitud": -31.0, "longitud": -58.0, "pais": "ARG", "potencia_radiativa": 6.0},
        {"fecha_adq": "2026-05-11", "latitud": -34.0, "longitud": -56.0, "pais": "URY", "potencia_radiativa": 7.0},
        {"fecha_adq": "2026-05-11", "latitud": -25.0, "longitud": -57.0, "pais": "PRY", "potencia_radiativa": 8.0},
    ])
    accepted, rejected = normalize("FIRMS", raw)
    assert {row["pais_codigo"] for row in accepted} == {"BRA", "ARG", "URY"}
    assert len(rejected) == 1


def test_inumet_restringido_a_uruguay():
    raw = pd.DataFrame([
        {"fecha": "2023-01-01", "estacion": "Carrasco", "pais": "URY", "temperatura_c": 20},
        {"fecha": "2023-01-01", "estacion": "Exterior", "pais": "ARG", "temperatura_c": 20},
    ])
    accepted, rejected = normalize("INUMET", raw)
    assert (len(accepted), len(rejected)) == (1, 1)


def test_extract_inumet_une_csv_reales_y_filtra_periodo(tmp_path, monkeypatch):
    from etl.extract import base
    from etl.extract import extract_inumet

    source = tmp_path / "inumet.csv"
    source.write_text(
        "fecha,estacion,pais,temperatura_c,humedad_pct,latitud,longitud\n"
        "2025-01-01 00:00:00,Carrasco,URY,19.4,71,-34.79,-56.26\n",
        encoding="utf-8",
    )
    monkeypatch.setitem(base.SOURCE_FILES, "INUMET", str(source))

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
    invalid, rejected = normalize("METEO", pd.DataFrame([
        {"datetime": "2024-07-10T09:00:00Z", "pais": "BRA", "ubicacion": "Porto Alegre",
         "wind_direction_10m": 361, "surface_pressure": 1010},
        {"datetime": "2024-07-10T10:00:00Z", "pais": "BRA", "ubicacion": "Porto Alegre",
         "wind_direction_10m": 10, "surface_pressure": 0},
    ]))
    assert invalid == []
    assert len(rejected) == 2


def test_pronostico_no_es_fuente_habilitada():
    source = "FORE" + "CAST"
    try:
        normalize(source, pd.DataFrame())
    except ValueError as exc:
        assert "Fuente no habilitada" in str(exc)
    else:
        raise AssertionError("El pronostico meteorologico no debe estar habilitado como fuente EC3")


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


def test_extract_meteo_api_conserva_variables_y_pais(tmp_path, monkeypatch):
    from etl.extract import base
    from etl.extract import extract_meteo

    source = tmp_path / "meteo.csv"
    source.write_text(
        "time,pais,ubicacion,temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,rain,surface_pressure\n"
        "2024-01-01T00:00,URY,Montevideo,20.0,50,5.0,90,0.0,1000\n",
        encoding="utf-8",
    )
    monkeypatch.setitem(base.SOURCE_FILES, "METEO", str(source))
    frame = extract_meteo.extract()
    accepted, rejected = normalize("METEO", frame)
    assert rejected == []
    assert accepted[0]["pais_codigo"] == "URY"
    assert accepted[0]["temperatura_c"] == 20.0


def test_extract_meteo_api_controlada(monkeypatch):
    from etl.extract import base
    from etl.extract import extract_meteo

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "hourly": {
                    "time": ["2025-01-01T00:00", "2025-01-01T01:00"],
                    "temperature_2m": [20.0, 21.0],
                    "relative_humidity_2m": [50, 51],
                    "wind_speed_10m": [5.0, 6.0],
                    "wind_direction_10m": [90, 95],
                    "rain": [0.0, 0.1],
                    "surface_pressure": [1000, 1001],
                }
            }

    monkeypatch.setitem(base.SOURCE_FILES, "METEO", "")
    monkeypatch.setattr(extract_meteo.requests, "get", lambda *args, **kwargs: Response())
    monkeypatch.setenv("METEO_API_ENABLED", "true")
    monkeypatch.setenv("METEO_POINTS", "UY_Montevideo")
    frame = extract_meteo.extract()
    assert len(frame) == 2
    assert frame.loc[0, "pais"] == "URY"
    assert frame.loc[0, "ubicacion"] == "Montevideo"
    assert {"temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_direction_10m", "rain", "surface_pressure"}.issubset(frame.columns)


def test_extract_cams_opcional_sin_config_no_inventa_datos(monkeypatch):
    from etl.extract import extract_cams

    monkeypatch.setattr(extract_cams, "read_source", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()))
    monkeypatch.delenv("CAMS_API_ENABLED", raising=False)
    frame = extract_cams.extract()
    assert frame.empty
    assert {"pm2_5", "pm10"}.issubset(frame.columns)


def test_extract_cams_api_controlada(monkeypatch):
    from etl.extract import extract_cams

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "hourly": {
                    "time": ["2025-01-01T00:00", "2025-01-01T01:00"],
                    "pm10": [11.0, 12.0],
                    "pm2_5": [4.0, 5.0],
                }
            }

    monkeypatch.setattr(extract_cams, "read_source", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()))
    monkeypatch.setattr(extract_cams.requests, "get", lambda *args, **kwargs: Response())
    monkeypatch.setenv("CAMS_API_ENABLED", "true")
    monkeypatch.setenv("LIDIA_MAX_RECORDS_PER_SOURCE", "2")
    frame = extract_cams.extract()
    assert len(frame) == 2
    assert frame.loc[0, "fuente"] == "CAMS"
    assert frame.loc[0, "pais_codigo"] in {"URY", "ARG", "BRA"}
    assert {"fecha_hora_utc", "pm2_5", "pm10", "latitud", "longitud"}.issubset(frame.columns)


def test_extract_cams_aplica_limite_despues_de_filtrar_pm(monkeypatch):
    from etl.extract import extract_cams

    raw = pd.DataFrame(
        [
            {"fecha": "2018-01-01", "punto": "Montevideo", "pais_codigo": "URY", "pm2_5_media": None, "pm10_media": None},
            {"fecha": "2022-08-04", "punto": "Montevideo", "pais_codigo": "URY", "pm2_5_media": 4.0, "pm10_media": 10.0},
            {"fecha": "2022-08-05", "punto": "Montevideo", "pais_codigo": "URY", "pm2_5_media": 5.0, "pm10_media": 11.0},
        ]
    )
    monkeypatch.setattr(extract_cams, "read_source", lambda *args, **kwargs: raw)
    monkeypatch.setenv("LIDIA_MAX_RECORDS_PER_SOURCE", "1")

    frame = extract_cams.extract()

    assert len(frame) == 1
    assert frame.iloc[0]["fecha"] == "2022-08-04"
    assert frame.iloc[0]["pm2_5_media"] == 4.0


def test_cams_normaliza_pm25_pm10():
    accepted, rejected = normalize("CAMS", pd.DataFrame([
        {"date": "2024-01-01T00:00:00Z", "pais": "URY", "location": "Montevideo",
         "lat": -34.9, "lon": -56.16, "pm2_5": 4.1, "pm10": 12.8}
    ]))
    assert rejected == []
    assert accepted[0]["fuente"] == "CAMS"
    assert accepted[0]["pm25"] == 4.1
    assert accepted[0]["pm10"] == 12.8


def test_cams_normaliza_esquema_agregado_real_2018_2025():
    accepted, rejected = normalize("CAMS", pd.DataFrame([
        {
            "fecha": "2022-08-04",
            "punto": "Buenos_Aires",
            "pais_codigo": "ARG",
            "latitud": -34.61,
            "longitud": -58.37,
            "pm2_5_media": 5.8875,
            "pm10_media": 8.795833,
        }
    ]))

    assert rejected == []
    assert accepted[0]["fuente"] == "CAMS"
    assert accepted[0]["fecha"] == "2022-08-04"
    assert accepted[0]["ubicacion"] == "Buenos_Aires"
    assert accepted[0]["pm25"] == 5.8875
    assert accepted[0]["pm10"] == 8.795833


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
    assert "dw.dim_calidad_aire" in ddl
    assert "staging.stg_calidad_aire" in ddl
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
