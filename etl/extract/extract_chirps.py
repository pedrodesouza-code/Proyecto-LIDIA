# =============================================================================
# SINIA-SA — Extractor CHIRPS (Precipitación Mensual)
# =============================================================================
# CHIRPS = Climate Hazards Group InfraRed Precipitation with Stations
# Producto de precipitación de alta resolución (0.05°) desarrollado por UCSB.
# Disponible desde 1981, sin registro ni API key.
#
# Usamos el endpoint de ClimateSERV (SERVIR Global / NASA) que expone CHIRPS
# como servicio de extracción por punto y devuelve series temporales en JSON.
# URL: https://climateserv.servirglobal.net/api
#
# Variables:
#   - Precipitación total mensual en mm por punto de monitoreo
#
# Integración con el modelo de datos:
#   - Se guarda en tabla precipitacion_mensual (PostgreSQL)
#   - Enriquece el análisis de sequía junto con et0_fao_evapotranspiration
# =============================================================================

import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.settings import PUNTOS_METEO_SA, CHIRPS_BASE_URL, DIR_CRUDO
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.extract.chirps")

# Tipo de dato CHIRPS disponible en ClimateSERV
# 26 = CHIRPS Precipitation (valor estándar del sistema ClimateSERV)
CHIRPS_DATASET_TYPE = 26

# Operación estadística: 5 = promedio (suma mensual de precipitación diaria)
CHIRPS_OPERATION = 5


# =============================================================================
# FUNCIÓN 1: Precipitación mensual para un punto
# =============================================================================

def extraer_chirps_punto(
    punto: str,
    anio_inicio: int = 2018,
    anio_fin: int = 2025,
    guardar: bool = True,
) -> pd.DataFrame:
    """
    Extrae precipitación mensual CHIRPS para un punto de monitoreo.

    Realiza una request al API de ClimateSERV con las coordenadas del punto
    y devuelve la serie temporal mensual de precipitación en mm.

    Args:
        punto:       Nombre del punto (debe estar en PUNTOS_METEO_SA)
        anio_inicio: Año de inicio del período (default 2018)
        anio_fin:    Año de fin del período (default 2025)
        guardar:     Si True, guarda el CSV en data/raw/chirps/

    Returns:
        DataFrame con columnas: punto, pais, fecha, precipitacion_mm, fuente
    """
    if punto not in PUNTOS_METEO_SA:
        raise ValueError(
            f"Punto '{punto}' no encontrado.\n"
            f"Opciones: {list(PUNTOS_METEO_SA.keys())}"
        )

    info = PUNTOS_METEO_SA[punto]
    lat, lon = info["lat"], info["lon"]
    pais = info["pais"]

    # ClimateSERV acepta el área como pequeño cuadrado alrededor del punto
    # (0.05° de lado, la resolución nativa de CHIRPS)
    delta = 0.025
    geometry = {
        "type": "Polygon",
        "coordinates": [[
            [lon - delta, lat - delta],
            [lon + delta, lat - delta],
            [lon + delta, lat + delta],
            [lon - delta, lat + delta],
            [lon - delta, lat - delta],
        ]],
    }

    # Período como strings MM/DD/YYYY que acepta ClimateSERV
    fecha_ini_str = f"01/01/{anio_inicio}"
    fecha_fin_str = f"12/31/{anio_fin}"

    import json
    payload = {
        "datatype":       CHIRPS_DATASET_TYPE,
        "begintime":      fecha_ini_str,
        "endtime":        fecha_fin_str,
        "intervaltype":   1,           # 1 = mensual
        "operationtype":  CHIRPS_OPERATION,
        "geometry":       json.dumps(geometry),
        "isZip_CurrentDataType": False,
    }

    logger.info(
        f"Descargando CHIRPS: {punto} ({lat}, {lon}), {anio_inicio}–{anio_fin}",
        extra={"etl_stage": "extract", "source": "chirps"},
    )

    try:
        resp = requests.get(
            f"{CHIRPS_BASE_URL}/submitDataRequest/",
            params=payload,
            timeout=30,
        )
        resp.raise_for_status()
        token = resp.json()   # Devuelve un token de request asíncrona
    except Exception as e:
        logger.warning(f"Error iniciando request CHIRPS para {punto}: {e}")
        return pd.DataFrame()

    # ClimateSERV es asíncrono: polling hasta que el resultado esté listo
    max_intentos = 40   # 40 × 5s = 200s máximo
    for intento in range(max_intentos):
        time.sleep(5)
        try:
            status_resp = requests.get(
                f"{CHIRPS_BASE_URL}/getDataRequestProgress/",
                params={"id": token},
                timeout=30,
            )
            status_resp.raise_for_status()
            progreso = status_resp.json()

            if isinstance(progreso, list) and len(progreso) > 0:
                p = progreso[0]
                # La API devuelve [100.0] (float) o [{"progress": 100, "status": "2"}]
                pct = p if isinstance(p, (int, float)) else p.get("progress", 0)
                estado = None if isinstance(p, (int, float)) else p.get("status")
                if pct >= 100 or estado == "2":
                    break
        except Exception:
            pass
    else:
        logger.warning(f"CHIRPS timeout para {punto} — sin datos")
        return pd.DataFrame()

    # Descarga del resultado
    try:
        result_resp = requests.get(
            f"{CHIRPS_BASE_URL}/getDataFromRequest/",
            params={"id": token},
            timeout=60,
        )
        result_resp.raise_for_status()
        payload_json = result_resp.json()
        # La API puede devolver {"data": [...]} o directamente [...]
        data = payload_json["data"] if isinstance(payload_json, dict) and "data" in payload_json else payload_json
    except Exception as e:
        logger.warning(f"Error descargando resultado CHIRPS para {punto}: {e}")
        return pd.DataFrame()

    # Parseo del resultado — ClimateSERV devuelve registros diarios
    # value puede ser float o {"avg": float}
    registros = []
    for item in data:
        try:
            fecha = pd.to_datetime(item["date"], format="%m/%d/%Y")
            raw = item.get("raw_value") or item.get("value")
            if isinstance(raw, dict):
                raw = raw.get("avg", raw.get("value", 0))
            valor = float(raw)
            registros.append({"fecha": fecha, "precipitacion_mm": valor})
        except Exception:
            continue

    if not registros:
        logger.warning(f"CHIRPS: sin registros parseados para {punto}")
        return pd.DataFrame()

    # Agregar de diario a mensual (suma de precipitación por mes)
    df_diario = pd.DataFrame(registros)
    df_diario["anio_mes"] = df_diario["fecha"].dt.to_period("M")
    df_mensual = (
        df_diario.groupby("anio_mes")["precipitacion_mm"]
        .sum()
        .reset_index()
    )
    df_mensual["fecha"] = df_mensual["anio_mes"].dt.to_timestamp()
    df = df_mensual[["fecha", "precipitacion_mm"]].copy()
    df["punto"] = punto
    df["pais"]  = pais
    df["fuente"] = "CHIRPS_ClimateSERV"
    df = df[["punto", "pais", "fecha", "precipitacion_mm", "fuente"]]

    logger.info(
        f"CHIRPS: {len(df)} meses descargados para {punto}",
        extra={"etl_stage": "extract", "source": "chirps", "rows_count": len(df)},
    )

    if guardar and not df.empty:
        ruta = DIR_CRUDO / "chirps" / f"chirps_{punto.lower()}_{anio_inicio}_{anio_fin}.csv"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(ruta, index=False)
        logger.info(f"CSV guardado en: {ruta}")

    return df


# =============================================================================
# FUNCIÓN 2: Precipitación para todos los puntos
# =============================================================================

def extraer_chirps_todos_los_puntos(
    anio_inicio: int = 2018,
    anio_fin: int = 2025,
    pausa: float = 2.0,
) -> pd.DataFrame:
    """
    Extrae precipitación mensual CHIRPS para los 36 puntos del alcance final.

    Args:
        anio_inicio: Año de inicio
        anio_fin:    Año de fin
        pausa:       Segundos entre requests (ClimateSERV tolera llamadas seguidas)

    Returns:
        DataFrame unificado con datos de todos los puntos.
    """
    frames = []
    for punto in PUNTOS_METEO_SA:
        try:
            df = extraer_chirps_punto(
                punto=punto,
                anio_inicio=anio_inicio,
                anio_fin=anio_fin,
                guardar=True,
            )
            if not df.empty:
                frames.append(df)
        except Exception as e:
            logger.warning(f"Error en CHIRPS para {punto}: {e}")
        time.sleep(pausa)

    if not frames:
        return pd.DataFrame()

    resultado = pd.concat(frames, ignore_index=True)
    logger.info(
        f"CHIRPS todos los puntos: {len(resultado)} registros totales",
        extra={"etl_stage": "extract", "source": "chirps", "rows_count": len(resultado)},
    )
    return resultado


# =============================================================================
# BLOQUE DE EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SINIA-SA — Extractor CHIRPS Precipitación")
    print("=" * 60)
    print(f"Fuente      : CHIRPS vía ClimateSERV (SERVIR Global / NASA)")
    print(f"Endpoint    : {CHIRPS_BASE_URL}")
    print(f"Resolución  : 0.05° (~5 km), mensual agregado")
    print(f"Puntos conf : {list(PUNTOS_METEO_SA.keys())}")

    # ── Prueba 1: un punto específico ───────────────────────────────────
    print("\n" + "-" * 60)
    print("PRUEBA 1 — Precipitación mensual para Cuiabá (2018-2020)")
    print("-" * 60)
    print("Punto      : Cuiabá")
    print("Período    : 2018  →  2020")
    print("Descargando (puede tardar ~30s por el proceso asíncrono)...\n")

    df = extraer_chirps_punto(punto="Cuiabá", anio_inicio=2018, anio_fin=2020)

    if not df.empty:
        print(f"[OK] Meses descargados     : {len(df)}")
        print(f"     Columnas              : {list(df.columns)}")
        print(f"     Rango fechas          : {df['fecha'].min().date()}  →  {df['fecha'].max().date()}")
        print(f"     Precipitación total   : {df['precipitacion_mm'].sum():.1f} mm")
        print(f"     Precipitación promedio: {df['precipitacion_mm'].mean():.1f} mm/mes")
        print(f"     Mes más lluvioso      : {df.loc[df['precipitacion_mm'].idxmax(), 'fecha'].strftime('%Y-%m')} "
              f"({df['precipitacion_mm'].max():.1f} mm)")
        print(f"     Mes más seco          : {df.loc[df['precipitacion_mm'].idxmin(), 'fecha'].strftime('%Y-%m')} "
              f"({df['precipitacion_mm'].min():.1f} mm)")
        print(f"\nPrimeros 12 meses:")
        print(df.head(12).to_string(index=False))
    else:
        print("[ERROR] Sin datos — verificar conectividad con ClimateSERV.")

    # ── Prueba 2: segundo punto de control ──────────────────────────────
    SEGUNDO_PUNTO = list(PUNTOS_METEO_SA.keys())[1] if len(PUNTOS_METEO_SA) > 1 else None
    if SEGUNDO_PUNTO:
        print("\n" + "-" * 60)
        print(f"PRUEBA 2 — Control rápido para {SEGUNDO_PUNTO} (2023)")
        print("-" * 60)
        print("Descargando...\n")

        df2 = extraer_chirps_punto(punto=SEGUNDO_PUNTO, anio_inicio=2023, anio_fin=2023)
        if not df2.empty:
            print(f"[OK] Meses descargados : {len(df2)}")
            print(f"     Precipitación total: {df2['precipitacion_mm'].sum():.1f} mm (anual)")
        else:
            print("[INFO] Sin datos para este punto.")

    print("\n" + "=" * 60)
    print("Extractor CHIRPS finalizado.")
    print("=" * 60)
