import pandas as pd

from etl.main import RunOptions, _firms_date_column, _firms_years, _read_firms_partition


def test_firms_partition_reader_filters_by_year_and_limit(tmp_path):
    path = tmp_path / "firms.parquet"
    pd.DataFrame(
        [
            {"fecha_adq": "2024-01-01", "pais_codigo": "URY", "latitud": -34.0, "longitud": -56.0, "brillo_ti4": 300.0},
            {"fecha_adq": "2025-01-01", "pais_codigo": "URY", "latitud": -34.1, "longitud": -56.1, "brillo_ti4": 301.0},
            {"fecha_adq": "2025-01-02", "pais_codigo": "ARG", "latitud": -27.0, "longitud": -58.0, "brillo_ti4": 302.0},
        ]
    ).to_parquet(path, index=False)

    options = RunOptions(start_date="2025-01-01", end_date="2025-12-31", max_records_per_source=1)
    years = _firms_years(path, options)
    frame, date_column = _read_firms_partition(path, 2025, options, remaining=1)

    assert _firms_date_column(path) == "fecha_adq"
    assert date_column == "fecha_adq"
    assert years == [2025]
    assert len(frame) == 1
    assert pd.to_datetime(frame["fecha_adq"]).dt.year.eq(2025).all()


def test_firms_partition_reader_respects_country_filter(tmp_path):
    path = tmp_path / "firms.parquet"
    pd.DataFrame(
        [
            {"fecha_adq": "2025-01-01", "pais_codigo": "URY", "latitud": -34.0, "longitud": -56.0, "brillo_ti4": 300.0},
            {"fecha_adq": "2025-01-01", "pais_codigo": "CHL", "latitud": -33.0, "longitud": -70.0, "brillo_ti4": 300.0},
        ]
    ).to_parquet(path, index=False)

    options = RunOptions(start_date="2025-01-01", end_date="2025-12-31", countries=("URY",))
    frame, date_column = _read_firms_partition(path, 2025, options, remaining=None)

    assert date_column == "fecha_adq"
    assert len(frame) == 1
    assert frame.iloc[0]["pais_codigo"] == "URY"


def test_firms_partition_reader_supports_raw_acq_date_schema(tmp_path):
    path = tmp_path / "firms_raw.parquet"
    pd.DataFrame(
        [
            {
                "acq_date": "2024-12-31",
                "acq_time": 2350,
                "latitude": -34.0,
                "longitude": -56.0,
                "brightness": 300.0,
                "frp": 4.2,
                "confidence": 80,
                "satellite": "Aqua",
                "instrument": "MODIS",
                "daynight": "N",
                "type": 0,
            },
            {
                "acq_date": "2025-01-01",
                "acq_time": 10,
                "latitude": -34.1,
                "longitude": -56.1,
                "brightness": 301.0,
                "frp": 5.2,
                "confidence": 85,
                "satellite": "Aqua",
                "instrument": "MODIS",
                "daynight": "D",
                "type": 0,
            },
        ]
    ).to_parquet(path, index=False)

    options = RunOptions(start_date="2025-01-01", end_date="2025-12-31")
    years = _firms_years(path, options)
    frame, date_column = _read_firms_partition(path, 2025, options, remaining=None)

    assert _firms_date_column(path) == "acq_date"
    assert date_column == "acq_date"
    assert years == [2025]
    assert len(frame) == 1
    assert {"acq_date", "latitude", "longitude", "brightness", "frp", "confidence"}.issubset(frame.columns)
    assert "fecha_adq" not in frame.columns
    assert pd.to_datetime(frame["acq_date"]).dt.year.eq(2025).all()
