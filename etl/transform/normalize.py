from __future__ import annotations

import hashlib
import json
from typing import Any

import pandas as pd

from config.settings import FUENTES_VALIDAS, PAISES


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
    return json.loads(json.dumps(value, default=str))


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
    country = str(_value(raw, "pais_codigo", "pais", "country") or "").upper()
    if source == "INUMET" and country in {"", "UY", "URUGUAY"}:
        country = "URY"
    aliases = {"UY": "URY", "AR": "ARG", "BR": "BRA", "URUGUAY": "URY", "ARGENTINA": "ARG", "BRASIL": "BRA"}
    country = aliases.get(country, country)
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
        confidence = _number(_value(raw, "confianza", "confidence"))
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
            "brillo_termico": _number(_value(raw, "brillo_termico", "brightness", "bright_ti4")),
            "confianza": confidence,
            "satelite": _value(raw, "satelite", "satellite"),
            "instrumento": _value(raw, "instrumento", "instrument"),
            "dia_noche": daynight,
        }
    elif source in {"METEO", "FORECAST", "INUMET"}:
        fecha_hora_utc = _datetime_utc(
            _value(raw, "fecha_hora_utc", "time", "datetime", "fecha_hora", "fecha", "date")
        )
        fecha = _date(fecha_hora_utc)
        location = str(_value(raw, "ubicacion", "punto", "estacion") or "")
        if not fecha_hora_utc or not location:
            raise ValueError(f"{source} requiere fecha_hora_utc y ubicacion/estacion")
        natural = "|".join([source, fecha_hora_utc, country, location])
        record = {
            "natural_key": natural, "fuente": source, "fecha": fecha, "pais_codigo": country,
            "fecha_hora_utc": fecha_hora_utc, "ubicacion": location,
            "departamento": _value(raw, "departamento"),
            "latitud": _number(_value(raw, "latitud", "latitude", "lat")),
            "longitud": _number(_value(raw, "longitud", "longitude", "lon")),
            "temperatura_c": _number(_value(raw, "temperatura_c", "temperature_2m", "temperature")),
            "humedad_pct": _number(_value(raw, "humedad_pct", "relative_humidity_2m", "humidity")),
            "viento_kmh": _number(_value(raw, "viento_kmh", "wind_speed_10m", "wind_speed")),
            "direccion_viento_grados": _number(_value(raw, "direccion_viento_grados", "wind_direction_10m")),
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
        location = str(_value(raw, "ubicacion", "punto") or "")
        precip = _number(_value(raw, "precipitacion_mm", "precipitation", "rain"))
        if not fecha or not location or precip is None or precip < 0:
            raise ValueError("CHIRPS requiere fecha, ubicacion y precipitacion no negativa")
        natural = "|".join([fecha, country, location])
        record = {"natural_key": natural, "fecha": fecha, "pais_codigo": country, "ubicacion": location, "precipitacion_mm": precip}
    else:  # MODIS
        year = _value(raw, "anio", "year")
        location = str(_value(raw, "ubicacion", "punto") or "")
        try:
            year = int(year)
        except (TypeError, ValueError):
            raise ValueError("MODIS requiere anio")
        if not 2018 <= year <= 2025 or not location:
            raise ValueError("MODIS requiere anio 2018-2025 y ubicacion")
        natural = "|".join([str(year), country, location])
        record = {
            "natural_key": natural, "anio": year, "pais_codigo": country, "ubicacion": location,
            "codigo_cobertura": _value(raw, "codigo_cobertura", "valor", "lc_type1"),
            "descripcion_cobertura": _value(raw, "descripcion_cobertura", "lc_descripcion"),
        }
    record["record_hash"] = _digest(record)
    record["raw_payload"] = _jsonsafe(raw)
    return record
