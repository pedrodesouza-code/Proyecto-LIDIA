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
    assert "region VARCHAR(100)" in ddl
    assert "brillo_termico" in ddl


def test_region_se_puebla_solo_desde_departamento_trazable():
    root = Path(__file__).parents[1]
    loader = (root / "etl" / "load" / "postgres.py").read_text(encoding="utf-8")
    views = (root / "sql" / "ddl" / "04_vistas.sql").read_text(encoding="utf-8")
    indexes = (root / "sql" / "ddl" / "03_indices.sql").read_text(encoding="utf-8")

    assert "MIN(NULLIF(TRIM(departamento), '')) AS region" in loader
    assert "SET region=COALESCE(EXCLUDED.region, dw.dim_ubicacion.region)" in loader
    assert "NULLIF(TRIM(u.region), '')::VARCHAR AS region" in views
    assert "COALESCE(u.region, u.ubicacion" not in views
    assert "idx_ubicacion_pais_region" in indexes


def test_region_administrativa_usa_postgis_sin_bounding_boxes():
    root = Path(__file__).parents[1]
    ddl = (root / "sql" / "ddl" / "06_regiones_administrativas.sql").read_text(encoding="utf-8")
    script = (root / "scripts" / "cargar_regiones_administrativas.py").read_text(encoding="utf-8")

    assert "dw.ref_region_administrativa" in ddl
    assert "geometry(MultiPolygon, 4326)" in ddl
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in ddl
    assert "ST_Contains" in ddl
    assert "ST_SetSRID(ST_Point(u.longitud::double precision, u.latitud::double precision), 4326)" in ddl
    assert "(u.region IS NULL OR TRIM(u.region) = '')" in ddl
    assert "u.latitud BETWEEN" not in ddl
    assert "u.longitud BETWEEN" not in ddl
    assert "nearest" not in ddl.lower()
    assert "No se encontró una capa real" in script or "No se asignan regiones por coordenadas" in script
    assert "no contiene polígonos" in script
    assert "no se usan límites lineales ni bounding boxes" in script
    assert "IDE_UY_DEPARTAMENTOS_URL" in script
    assert "--download-ide-uy" in script


def test_vista_zona_espacial_no_fabrica_departamentos():
    root = Path(__file__).parents[1]
    views = (root / "sql" / "ddl" / "04_vistas.sql").read_text(encoding="utf-8")
    dashboard = (root / "dashboard" / "streamlit_app.py").read_text(encoding="utf-8")

    assert "dw.v_focos_zona_espacial" in views
    assert "dw.v_focos_zona_espacial_ury" in views
    assert "ROUND(u.latitud::numeric, 1) AS latitud_grilla" in views
    assert "ROUND(u.longitud::numeric, 1) AS longitud_grilla" in views
    assert "zona_espacial" in views
    assert "COALESCE(u.region, u.ubicacion" not in views
    assert "Zonas geográficas con mayor concentración de focos" in dashboard
    assert "Las celdas espaciales no representan departamentos administrativos" in dashboard
    assert "Focos FIRMS por departamento" in dashboard


def test_dashboard_responde_diez_preguntas_y_usa_consultas_agregadas():
    root = Path(__file__).parents[1]
    dashboard = (root / "dashboard" / "streamlit_app.py").read_text(encoding="utf-8")

    assert "@st.cache_data(ttl=300" in dashboard
    assert "def run_query" in dashboard
    assert "SELECT * FROM dw.fact_incendio" not in dashboard
    assert "brightness" not in dashboard.lower()
    assert "SECTION_OPTIONS" in dashboard
    assert "dw.mv_dashboard_focos_pais_periodo" in dashboard
    assert "dw.mv_dashboard_incendios_precipitacion" in dashboard
    assert "Baja (<40%%)" in dashboard
    assert "Media (40%%-70%%)" in dashboard
    assert "Alta (>70%%)" in dashboard
    assert "CREATE MATERIALIZED VIEW dw.mv_dashboard_focos_pais_periodo" in (root / "sql" / "ddl" / "04_vistas.sql").read_text(encoding="utf-8")
    assert "Sección A — Resumen ejecutivo" in dashboard
    assert "1. ¿Qué evolución temporal presentan los focos de calor en Uruguay?" in dashboard
    assert "2. ¿Qué diferencias descriptivas se observan entre Uruguay, Argentina y Brasil?" in dashboard
    assert "3. ¿Qué asociación se observa entre temperatura media diaria y cantidad de focos?" in dashboard
    assert "4. ¿Cómo varía la cantidad de focos en períodos con baja humedad relativa?" in dashboard
    assert "5. ¿Qué diferencias se observan en PM2.5 y PM10 durante mayor actividad de focos?" in dashboard
    assert "6. ¿Qué patrones se observan entre precipitación mensual CHIRPS y focos?" in dashboard
    assert "7. ¿Qué tipos de cobertura vegetal aparecen asociados a las zonas analizadas?" in dashboard
    assert "8. ¿Qué zonas geográficas de Uruguay presentan mayor concentración de focos?" in dashboard
    assert "9. ¿Qué porcentaje de cobertura de datos tiene calidad del aire por período?" in dashboard
    assert "10. ¿Qué registros deben ser rechazados o tratados por problemas de calidad ETL?" in dashboard
    assert "estación INUMET" not in dashboard
    assert "No representa incendios por departamento" not in dashboard


def test_docker_local_usa_postgis_para_regiones():
    root = Path(__file__).parents[1]
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    compose_legacy = (root / "docker" / "docker-compose.yml").read_text(encoding="utf-8")
    assert "postgis/postgis:16-3.4" in compose
    assert "./sql/ddl/06_regiones_administrativas.sql" in compose
    assert "postgis/postgis:16-3.4" in compose_legacy
    assert "../sql/ddl/06_regiones_administrativas.sql" in compose_legacy


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
