from __future__ import annotations

import hashlib
import json
from typing import Any

import pandas as pd

from config.settings import FUENTES_VALIDAS, PAISES

LOCATION_COUNTRY = {
    "montevideo": "URY",
    "artigas": "URY",
    "canelones": "URY",
    "maldonado": "URY",
    "rocha": "URY",
    "treinta_y_tres": "URY",
    "cerro_largo": "URY",
    "rivera": "URY",
    "salto": "URY",
    "paysandu": "URY",
    "paysandú": "URY",
    "rio_negro": "URY",
    "fray_bentos": "URY",
    "soriano": "URY",
    "mercedes": "URY",
    "colonia": "URY",
    "colonia_del_sacramento": "URY",
    "san_jose": "URY",
    "san_josé": "URY",
    "san_jose_de_mayo": "URY",
    "flores": "URY",
    "trinidad": "URY",
    "florida": "URY",
    "durazno": "URY",
    "lavalleja": "URY",
    "minas": "URY",
    "melo": "URY",
    "tacuarembo": "URY",
    "tacuarembó": "URY",
    "buenos_aires": "ARG",
    "mendoza": "ARG",
    "posadas": "ARG",
    "salta": "ARG",
    "brasilia": "BRA",
    "brasília": "BRA",
    "campo_grande": "BRA",
    "cuiaba": "BRA",
    "cuiabá": "BRA",
    "manaus": "BRA",
    "porto_alegre": "BRA",
}

LOCATION_COORDS = {
    "montevideo": (-34.90, -56.16),
    "artigas": (-30.40, -56.47),
    "canelones": (-34.52, -56.28),
    "maldonado": (-34.90, -54.95),
    "rocha": (-34.48, -54.33),
    "treinta_y_tres": (-33.23, -54.38),
    "cerro_largo": (-32.37, -54.17),
    "rivera": (-30.90, -55.55),
    "salto": (-31.38, -57.97),
    "paysandu": (-32.32, -58.08),
    "paysandú": (-32.32, -58.08),
    "rio_negro": (-33.12, -58.31),
    "fray_bentos": (-33.12, -58.31),
    "soriano": (-33.25, -58.03),
    "mercedes": (-33.25, -58.03),
    "colonia": (-34.47, -57.84),
    "colonia_del_sacramento": (-34.47, -57.84),
    "san_jose": (-34.34, -56.71),
    "san_josé": (-34.34, -56.71),
    "san_jose_de_mayo": (-34.34, -56.71),
    "flores": (-33.54, -56.89),
    "trinidad": (-33.54, -56.89),
    "florida": (-34.10, -56.21),
    "durazno": (-33.41, -56.50),
    "lavalleja": (-34.37, -55.23),
    "minas": (-34.37, -55.23),
    "melo": (-32.37, -54.17),
    "tacuarembo": (-31.73, -55.98),
    "tacuarembó": (-31.73, -55.98),
    "buenos_aires": (-34.61, -58.37),
    "mendoza": (-32.89, -68.84),
    "posadas": (-27.37, -55.90),
    "salta": (-24.79, -65.41),
    "brasilia": (-15.78, -47.93),
    "brasília": (-15.78, -47.93),
    "campo_grande": (-20.47, -54.62),
    "cuiaba": (-15.60, -56.10),
    "cuiabá": (-15.60, -56.10),
    "manaus": (-3.12, -60.02),
    "porto_alegre": (-30.03, -51.23),
}


def _value(row: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in row and not pd.isna(row[name]):
            return row[name]
    return None


def _date(value: Any) -> str | None:
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed.date().isoformat()


def _datetime_utc(value: Any) -> str | None:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return None if pd.isna(parsed) else parsed.isoformat()


def _number(value: Any) -> float | None:
    parsed = pd.to_numeric(value, errors="coerce")
    return None if pd.isna(parsed) else float(parsed)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _jsonsafe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _jsonsafe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonsafe(item) for item in value]
    if pd.isna(value):
        return None
    return json.loads(json.dumps(value, default=str, allow_nan=False))


def _location(raw: dict[str, Any]) -> str:
    return str(_value(raw, "ubicacion", "punto", "location", "estacion") or "")


def _location_key(raw: dict[str, Any]) -> str:
    return _location(raw).strip().lower().replace(" ", "_")


def _country(raw: dict[str, Any], source: str) -> str:
    country = str(_value(raw, "pais_codigo", "pais", "country") or "").upper()
    if source == "INUMET" and country in {"", "UY", "URUGUAY"}:
        country = "URY"
    aliases = {"UY": "URY", "AR": "ARG", "BR": "BRA", "URUGUAY": "URY", "ARGENTINA": "ARG", "BRASIL": "BRA"}
    country = aliases.get(country, country)
    if country:
        return country
    return LOCATION_COUNTRY.get(_location_key(raw), "")


def _lat(raw: dict[str, Any]) -> float | None:
    explicit = _number(_value(raw, "latitud", "latitude", "lat"))
    if explicit is not None:
        return explicit
    coords = LOCATION_COORDS.get(_location_key(raw))
    return None if coords is None else coords[0]


def _lon(raw: dict[str, Any]) -> float | None:
    explicit = _number(_value(raw, "longitud", "longitude", "lon"))
    if explicit is not None:
        return explicit
    coords = LOCATION_COORDS.get(_location_key(raw))
    return None if coords is None else coords[1]


def _reject(raw: dict[str, Any], reason: str) -> dict[str, Any]:
    return {"motivo": reason, "registro": _jsonsafe(raw)}


def cdc_kind(previous_hash: str | None, current_hash: str) -> str:
    if previous_hash is None:
        return "alta"
    return "sin_cambio" if previous_hash == current_hash else "modificacion"


def normalize(source: str, frame: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Valida filas y devuelve registros canonicos mas rechazos trazables."""
    if source not in FUENTES_VALIDAS:
        raise ValueError(f"Fuente no habilitada: {source}")
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for raw in frame.to_dict(orient="records"):
        try:
            record = _normalize_record(source, raw)
            accepted.append(record)
        except ValueError as exc:
            rejected.append(_reject(raw, str(exc)))
    return accepted, rejected


def _normalize_record(source: str, raw: dict[str, Any]) -> dict[str, Any]:
    country = _country(raw, source)
    if country not in PAISES:
        raise ValueError("pais fuera del alcance URY/ARG/BRA")

    if source == "FIRMS":
        fecha = _date(_value(raw, "fecha_adq", "acq_date", "fecha"))
        lat = _number(_value(raw, "latitud", "latitude"))
        lon = _number(_value(raw, "longitud", "longitude"))
        if not fecha or lat is None or lon is None:
            raise ValueError("FIRMS requiere fecha y coordenadas validas")
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("coordenadas fuera de rango")
        hour = _value(raw, "hora_adq_hhmm", "acq_time")
        natural = "|".join(map(str, [fecha, lat, lon, hour or "", _value(raw, "satelite", "satellite") or ""]))
        frp = _number(_value(raw, "frp_mw", "frp", "potencia_radiativa"))
        confidence = _number(_value(raw, "confianza", "confidence", "confianza_num"))
        daynight = _value(raw, "dia_noche", "daynight")
        if frp is not None and frp < 0:
            raise ValueError("FIRMS: FRP no puede ser negativo")
        if confidence is not None and not 0 <= confidence <= 100:
            raise ValueError("FIRMS: confianza fuera de rango")
        if daynight is not None and daynight not in {"D", "N"}:
            raise ValueError("FIRMS: dia_noche debe ser D o N")
        record = {
            "natural_key": natural, "fecha_adq": fecha, "hora_adq_hhmm": int(hour) if hour is not None else None,
            "latitud": lat, "longitud": lon, "pais_codigo": country,
            "frp_mw": frp,
            "brillo_termico": _number(_value(raw, "brillo_termico", "brightness", "bright_ti4", "brillo_ti4")),
            "confianza": confidence,
            "satelite": _value(raw, "satelite", "satellite"),
            "instrumento": _value(raw, "instrumento", "instrument"),
            "dia_noche": daynight,
        }
    elif source in {"METEO", "INUMET"}:
        fecha_hora_utc = _datetime_utc(
            _value(raw, "fecha_hora_utc", "time", "datetime", "fecha_hora", "fecha", "date")
        )
        fecha = _date(fecha_hora_utc)
        location = _location(raw)
        if not fecha_hora_utc or not location:
            raise ValueError(f"{source} requiere fecha_hora_utc y ubicacion/estacion")
        natural = "|".join([source, fecha_hora_utc, country, location])
        record = {
            "natural_key": natural, "fuente": source, "fecha": fecha, "pais_codigo": country,
            "fecha_hora_utc": fecha_hora_utc, "ubicacion": location,
            "departamento": _value(raw, "departamento"),
            "latitud": _lat(raw),
            "longitud": _lon(raw),
            "temperatura_c": _number(_value(raw, "temperatura_c", "temperature_2m", "temperature", "temperature_2m_max")),
            "humedad_pct": _number(_value(raw, "humedad_pct", "relative_humidity_2m", "humidity", "relative_humidity_2m_min")),
            "viento_kmh": _number(_value(raw, "viento_kmh", "wind_speed_10m", "wind_speed", "wind_speed_10m_max")),
            "direccion_viento_grados": _number(_value(raw, "direccion_viento_grados", "wind_direction_10m", "wind_direction_10m_dominant")),
            "presion_superficie_hpa": _number(_value(raw, "presion_superficie_hpa", "surface_pressure")),
            "precipitacion_mm": _number(_value(raw, "precipitacion_mm", "rain", "precipitation_sum")),
        }
        if record["humedad_pct"] is not None and not 0 <= record["humedad_pct"] <= 100:
            raise ValueError(f"{source}: humedad fuera de rango")
        if record["viento_kmh"] is not None and record["viento_kmh"] < 0:
            raise ValueError(f"{source}: viento negativo")
        if record["direccion_viento_grados"] is not None and not 0 <= record["direccion_viento_grados"] <= 360:
            raise ValueError(f"{source}: direccion de viento fuera de rango")
        if record["presion_superficie_hpa"] is not None and record["presion_superficie_hpa"] <= 0:
            raise ValueError(f"{source}: presion de superficie no positiva")
        if record["precipitacion_mm"] is not None and record["precipitacion_mm"] < 0:
            raise ValueError(f"{source}: precipitacion negativa")
        if source == "INUMET" and country != "URY":
            raise ValueError("INUMET solo aplica a Uruguay")
    elif source == "CHIRPS":
        fecha = _date(_value(raw, "fecha", "date"))
        location = _location(raw)
        precip = _number(_value(raw, "precipitacion_mm", "precipitation", "rain"))
        if not fecha or not location or precip is None or precip < 0:
            raise ValueError("CHIRPS requiere fecha, ubicacion y precipitacion no negativa")
        natural = "|".join([fecha, country, location])
        record = {
            "natural_key": natural, "fecha": fecha, "pais_codigo": country, "ubicacion": location,
            "latitud": _lat(raw),
            "longitud": _lon(raw),
            "precipitacion_mm": precip,
        }
    elif source == "MODIS":
        year = _value(raw, "anio", "year")
        location = _location(raw)
        try:
            year = int(year)
        except (TypeError, ValueError):
            raise ValueError("MODIS requiere anio")
        if not 2018 <= year <= 2025 or not location:
            raise ValueError("MODIS requiere anio 2018-2025 y ubicacion")
        natural = "|".join([str(year), country, location])
        record = {
            "natural_key": natural, "anio": year, "pais_codigo": country, "ubicacion": location,
            "latitud": _lat(raw),
            "longitud": _lon(raw),
            "codigo_cobertura": _value(raw, "codigo_cobertura", "valor", "lc_type1"),
            "descripcion_cobertura": _value(raw, "descripcion_cobertura", "lc_descripcion"),
        }
    else:  # CAMS / Open-Meteo Air Quality
        fecha_hora_utc = _datetime_utc(
            _value(raw, "fecha_hora_utc", "time", "datetime", "fecha_hora", "date", "fecha")
        )
        fecha = _date(fecha_hora_utc)
        location = _location(raw)
        pm25 = _number(_value(raw, "pm25", "pm2_5", "pm2.5", "pm2_5_media"))
        pm10 = _number(_value(raw, "pm10", "pm10_media"))
        if not fecha or not location:
            raise ValueError("CAMS requiere fecha y ubicacion")
        if pm25 is None and pm10 is None:
            raise ValueError("CAMS requiere pm25 o pm10")
        if (pm25 is not None and pm25 < 0) or (pm10 is not None and pm10 < 0):
            raise ValueError("CAMS: particulas no pueden ser negativas")
        natural = "|".join(["CAMS", fecha_hora_utc or fecha, country, location])
        record = {
            "natural_key": natural, "fecha": fecha, "fecha_hora_utc": fecha_hora_utc,
            "pais_codigo": country, "ubicacion": location,
            "latitud": _lat(raw),
            "longitud": _lon(raw),
            "pm25": pm25, "pm10": pm10, "fuente": "CAMS",
        }
    record["record_hash"] = _digest(record)
    record["raw_payload"] = _jsonsafe(raw)
    return record
