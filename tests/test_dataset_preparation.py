from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from scripts.preparar_datasets_2018_2025 import prepare_source
from scripts.auditar_firms_historico_2018_2025 import validate_firms_principal_profile


def test_preparador_filtra_periodo_y_paises(tmp_path):
    source = tmp_path / "chirps_sa.parquet"
    output = tmp_path / "chirps_2018_2025.parquet"
    pd.DataFrame(
        [
            {"fecha": "2017-12-01", "pais": "URY", "punto": "Montevideo", "precipitacion_mm": 1.0},
            {"fecha": "2018-01-01", "pais": "URY", "punto": "Montevideo", "precipitacion_mm": 2.0},
            {"fecha": "2025-12-31", "pais": "ARG", "punto": "Buenos_Aires", "precipitacion_mm": 3.0},
            {"fecha": "2026-01-01", "pais": "BRA", "punto": "Porto_Alegre", "precipitacion_mm": 4.0},
            {"fecha": "2024-01-01", "pais": "CHL", "punto": "Santiago", "precipitacion_mm": 5.0},
        ]
    ).to_parquet(source, index=False)

    result = prepare_source("CHIRPS", source, output, ["fecha"])
    prepared = pd.read_parquet(output)

    assert result.rows_in == 5
    assert result.rows_out == 2
    assert set(prepared["pais_codigo"]) == {"URY", "ARG"}
    assert prepared["fecha"].astype(str).tolist() == ["2018-01-01", "2025-12-31"]


def test_preparador_inumet_solo_uruguay(tmp_path):
    source = tmp_path / "inumet_procesado.parquet"
    output = tmp_path / "inumet_2018_2025.parquet"
    pd.DataFrame(
        [
            {"fecha_hora_utc": "2020-01-01T00:00:00Z", "pais_codigo": "URY", "ubicacion": "Carrasco"},
            {"fecha_hora_utc": "2020-01-01T01:00:00Z", "pais_codigo": "ARG", "ubicacion": "Exterior"},
        ]
    ).to_parquet(source, index=False)

    result = prepare_source("INUMET", source, output, ["fecha_hora_utc"])
    prepared = pd.read_parquet(output)

    assert result.rows_out == 1
    assert prepared.loc[0, "pais_codigo"] == "URY"


def test_preparador_marca_firms_nrt_como_parcial(tmp_path):
    source = tmp_path / "firms_nrt_procesado.parquet"
    output = tmp_path / "firms_2018_2025.parquet"
    pd.DataFrame(
        [
            {
                "fecha_adq": "2025-05-01",
                "pais": "URY",
                "latitud": -34.0,
                "longitud": -56.0,
                "brillo_ti4": 320.0,
            }
        ]
    ).to_parquet(source, index=False)

    result = prepare_source("FIRMS", source, output, ["fecha_adq"])

    assert result.rows_out == 1
    assert result.status == "parcial"
    assert "origen_nrt_no_recomendado_como_principal" in result.notes


def test_preparador_no_trata_brightness_como_temperatura(tmp_path):
    source = tmp_path / "firms_procesado.parquet"
    output = tmp_path / "firms_2018_2025.parquet"
    pd.DataFrame(
        [
            {
                "fecha_adq": "2024-01-01",
                "pais": "BRA",
                "latitud": -30.0,
                "longitud": -51.0,
                "brightness": 333.3,
                "frp": 10.0,
            }
        ]
    ).to_parquet(source, index=False)

    prepare_source("FIRMS", source, output, ["fecha_adq"])
    prepared = pd.read_parquet(output)

    assert "brightness" in prepared.columns
    assert "temperatura_c" not in prepared.columns


def test_validador_firms_rechaza_principal_solo_2024():
    profile = {
        "fecha_min": "2024-01-01",
        "fecha_max": "2024-12-31",
        "paises_detectados": {"URY": 10, "ARG": 20, "BRA": 30},
        "contiene_chl": False,
        "es_nrt": False,
    }

    errors = validate_firms_principal_profile(profile)

    assert "fecha_minima_posterior_a_2018_01_01" in errors
    assert "fecha_maxima_anterior_a_2025_01_01" in errors


def test_validador_firms_rechaza_chile_y_paises_faltantes():
    profile = {
        "fecha_min": "2018-01-01",
        "fecha_max": "2025-01-15",
        "paises_detectados": {"URY": 10, "CHL": 5},
        "contiene_chl": True,
        "es_nrt": False,
    }

    errors = validate_firms_principal_profile(profile)

    assert "contiene_chl" in errors
    assert "faltan_paises_ARG_BRA" in errors


def test_validador_firms_acepta_historico_ury_arg_bra_sin_chl():
    profile = {
        "fecha_min": "2018-01-01",
        "fecha_max": "2025-01-15",
        "paises_detectados": {"URY": 10, "ARG": 20, "BRA": 30},
        "contiene_chl": False,
        "es_nrt": False,
    }

    assert validate_firms_principal_profile(profile) == []


def test_firms_principal_local_cubre_2018_y_2025_si_existe():
    path = Path("data/processed/firms_2018_2025.parquet")
    if not path.exists():
        return

    parquet = pq.ParquetFile(path)
    columns = set(parquet.schema_arrow.names)
    date_column = "fecha_adq" if "fecha_adq" in columns else "acq_date"
    required = [date_column, "pais_codigo"]
    min_date = None
    max_date = None
    countries = set()

    for batch in parquet.iter_batches(batch_size=100_000, columns=required):
        chunk = batch.to_pandas()
        dates = pd.to_datetime(chunk[date_column], errors="coerce", utc=True).dropna()
        if not dates.empty:
            batch_min = dates.min()
            batch_max = dates.max()
            min_date = batch_min if min_date is None or batch_min < min_date else min_date
            max_date = batch_max if max_date is None or batch_max > max_date else max_date
        countries.update(chunk["pais_codigo"].astype(str).str.upper().dropna())

    assert min_date is not None
    assert max_date is not None
    assert min_date.date().isoformat() == "2018-01-01"
    assert max_date >= pd.Timestamp("2025-01-02", tz="UTC")
    assert {"URY", "ARG", "BRA"}.issubset(countries)
    assert "CHL" not in countries
    assert "temperatura_c" not in columns
    assert any(column in columns for column in ("brillo_ti4", "brightness", "brillo_termico"))


def test_meteo_principal_local_llega_a_2025_si_existe():
    path = Path("data/processed/meteo_2018_2025.parquet")
    if not path.exists():
        return

    parquet = pq.ParquetFile(path)
    columns = set(parquet.schema_arrow.names)
    date_columns = [column for column in ("fecha_hora_utc", "fecha") if column in columns]
    assert date_columns
    batch_columns = date_columns + ["pais_codigo"]
    min_date = None
    max_date = None
    countries = set()

    for batch in parquet.iter_batches(batch_size=100_000, columns=batch_columns):
        chunk = batch.to_pandas()
        dates = pd.Series(pd.NaT, index=chunk.index, dtype="datetime64[ns, UTC]")
        for column in date_columns:
            parsed = pd.to_datetime(chunk[column], errors="coerce", utc=True)
            dates = dates.fillna(parsed)
        dates = dates.dropna()
        if not dates.empty:
            batch_min = dates.min()
            batch_max = dates.max()
            min_date = batch_min if min_date is None or batch_min < min_date else min_date
            max_date = batch_max if max_date is None or batch_max > max_date else max_date
        countries.update(chunk["pais_codigo"].astype(str).str.upper().dropna())

    assert min_date is not None
    assert max_date is not None
    assert min_date.date().isoformat() == "2018-01-01"
    assert max_date >= pd.Timestamp("2025-12-31", tz="UTC")
    assert {"URY", "ARG", "BRA"}.issubset(countries)
    assert countries <= {"URY", "ARG", "BRA"}
    assert {"temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_direction_10m", "rain", "surface_pressure"}.issubset(columns)


def test_modis_principal_local_usa_solo_anios_y_paises_validos_si_existe():
    path = Path("data/processed/modis_2018_2025.parquet")
    if not path.exists():
        return

    frame = pd.read_parquet(path)
    years = set(pd.to_numeric(frame["anio"], errors="coerce").dropna().astype(int))
    countries = set(frame["pais_codigo"].astype(str).str.upper())

    assert years
    assert min(years) >= 2018
    assert max(years) <= 2025
    assert countries <= {"URY", "ARG", "BRA"}
    assert {"anio", "pais_codigo", "ubicacion", "codigo_cobertura", "descripcion_cobertura"}.issubset(frame.columns)


def test_chirps_principal_local_llega_a_2025_sin_chile_si_existe():
    path = Path("data/processed/chirps_2018_2025.parquet")
    if not path.exists():
        return

    frame = pd.read_parquet(path)
    dates = pd.to_datetime(frame["fecha"], errors="coerce", utc=True)
    countries = set(frame["pais_codigo"].astype(str).str.upper())

    assert dates.min().date().isoformat() == "2018-01-01"
    assert dates.max() >= pd.Timestamp("2025-12-01", tz="UTC")
    assert countries <= {"URY", "ARG", "BRA"}
    assert "CHL" not in countries
    assert (pd.to_numeric(frame["precipitacion_mm"], errors="coerce") >= 0).all()
