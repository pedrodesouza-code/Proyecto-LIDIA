# =============================================================================
# SINIA-UY — Extractor de Pronóstico Meteorológico (Open-Meteo Forecast)
# =============================================================================
# Este módulo descarga el pronóstico meteorológico para los próximos 7 días
# para los 5 puntos de monitoreo de Uruguay.
#
# A diferencia del extractor histórico (extract_meteo.py) que usa el archivo
# de Open-Meteo, este usa el endpoint de FORECAST que provee:
#   - Datos actuales (hoy)
#   - Pronóstico hasta 16 días hacia adelante
#
# Esto permite al sistema calcular el ÍNDICE DE RIESGO FUTURO y mostrar
# en el dashboard si se esperan condiciones peligrosas en los próximos días.
#
# NO requiere API key — Open-Meteo es completamente gratuito.
# Se actualiza aproximadamente cada hora con nuevos modelos meteorológicos.
# =============================================================================

import time   # Para pausas entre requests
from datetime import datetime, timedelta   # Para manejar fechas
from pathlib import Path

import pandas as pd
import requests

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.settings import OPENMETEO_BASE_URL, PUNTOS_METEO, DIR_CRUDO
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.extract.forecast")

# Variables diarias a pedir en el pronóstico
# Son las mismas que en el histórico pero con una variable extra:
# precipitation_probability_max — probabilidad de lluvia (útil para planificación)
VARIABLES_PRONOSTICO_DIARIAS = [
    "temperature_2m_max",              # Temperatura máxima esperada (°C)
    "temperature_2m_min",              # Temperatura mínima esperada (°C)
    "relative_humidity_2m_min",        # Humedad mínima esperada (%)
    "relative_humidity_2m_max",        # Humedad máxima esperada (%)
    "wind_speed_10m_max",              # Viento máximo esperado (km/h)
    "wind_direction_10m_dominant",     # Dirección dominante del viento (grados)
    "precipitation_sum",               # Precipitación total esperada (mm)
    "et0_fao_evapotranspiration",      # Evapotranspiración estimada (mm/día)
    "precipitation_probability_max",   # Probabilidad máxima de lluvia (%)
    "weathercode",                     # Código WMO del tiempo (0=despejado, 95=tormenta)
]


# =============================================================================
# FUNCIÓN 1: Pronóstico para un punto específico
# =============================================================================

def extraer_pronostico_punto(
    punto: str = "Rivera",   # Punto de monitoreo a descargar
    dias: int = 7,           # Días de pronóstico (1-16 disponibles en Open-Meteo)
    guardar: bool = True,    # Si True, guarda el CSV en data/raw/meteo/
) -> pd.DataFrame:
    """
    Descarga el pronóstico meteorológico para un punto de Uruguay.

    Los datos son estimaciones del modelo meteorológico GFS/ECMWF y se
    actualizan aproximadamente cada hora. La precisión disminuye a medida
    que nos alejamos en el tiempo (los primeros 3 días son más confiables).

    Args:
        punto:   Nombre del punto de monitoreo (debe estar en PUNTOS_METEO)
        dias:    Cantidad de días de pronóstico hacia adelante (máximo 16)
        guardar: Si True, guarda el resultado como CSV

    Returns:
        DataFrame con el pronóstico diario. Incluye columnas de temperatura,
        humedad, viento, precipitación y probabilidad de lluvia.
        Columna "extraido_en" indica cuándo se descargó el pronóstico.
    """
    # Verificamos que el punto existe
    if punto not in PUNTOS_METEO:
        raise ValueError(
            f"Punto '{punto}' no encontrado.\n"
            f"Opciones: {list(PUNTOS_METEO.keys())}"
        )

    latitud, longitud = PUNTOS_METEO[punto]   # Coordenadas del punto

    # Parámetros para la API de pronóstico de Open-Meteo
    parametros = {
        "latitude":      latitud,                              # Latitud del punto
        "longitude":     longitud,                             # Longitud del punto
        "daily":         ",".join(VARIABLES_PRONOSTICO_DIARIAS),  # Variables a descargar
        "timezone":      "America/Montevideo",                 # Zona horaria
        "forecast_days": dias,                                 # Días de pronóstico
    }

    logger.info(
        f"Descargando pronóstico: {punto} ({latitud}, {longitud}), {dias} días adelante",
        extra={"etl_stage": "extract", "source": "openmeteo_forecast"},
    )

    # La URL del forecast es el BASE_URL + "/forecast"
    url_forecast = f"{OPENMETEO_BASE_URL}/forecast"

    # Hacemos la petición HTTP a la API de pronóstico
    respuesta = requests.get(url_forecast, params=parametros, timeout=30)
    respuesta.raise_for_status()
    datos = respuesta.json()

    # Verificamos que la respuesta tenga datos diarios
    if "daily" not in datos:
        logger.warning(f"Sin datos de pronóstico disponibles para {punto}")
        return pd.DataFrame()

    # Convertimos los datos diarios del JSON a DataFrame
    df = pd.DataFrame(datos["daily"])

    # Renombramos "time" (Open-Meteo) a "fecha" (español)
    df.rename(columns={"time": "fecha"}, inplace=True)

    # Convertimos la columna fecha a tipo datetime para facilitar operaciones
    df["fecha"] = pd.to_datetime(df["fecha"])

    # Agregamos metadata del punto y marca de tiempo de la descarga
    df["punto"]        = punto                         # Nombre del punto
    df["latitud"]      = latitud                       # Coordenada latitud
    df["longitud"]     = longitud                      # Coordenada longitud
    df["extraido_en"]  = datetime.now().isoformat()    # Cuándo se descargó este pronóstico

    logger.info(
        f"Pronóstico: {len(df)} días descargados para {punto}",
        extra={"etl_stage": "extract", "source": "openmeteo_forecast", "rows_count": len(df)},
    )

    # Guardamos el CSV con timestamp en el nombre para no sobreescribir pronósticos anteriores
    if guardar and not df.empty:
        marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M")   # Ej: 20240115_1430
        ruta_salida = DIR_CRUDO / "meteo" / f"forecast_{punto.lower()}_{marca_tiempo}.csv"
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(ruta_salida, index=False)
        logger.info(f"CSV guardado en: {ruta_salida}")

    return df


# =============================================================================
# FUNCIÓN 2: Pronóstico para todos los puntos
# =============================================================================

def extraer_pronostico_todos(
    dias: int = 7,       # Días de pronóstico
    pausa: float = 0.3,  # Segundos entre requests
) -> pd.DataFrame:
    """
    Descarga el pronóstico para los 5 puntos de monitoreo de Uruguay.

    Llama a extraer_pronostico_punto() para cada departamento y concatena
    los resultados en un único DataFrame consolidado.

    Args:
        dias:  Días de pronóstico hacia adelante (1-16)
        pausa: Segundos de espera entre requests para no saturar la API

    Returns:
        DataFrame con el pronóstico de todos los puntos.
        Se puede filtrar por la columna "punto" para ver cada departamento.
    """
    frames = []   # Lista para acumular los DataFrames de cada punto

    for punto in PUNTOS_METEO:
        try:
            df = extraer_pronostico_punto(punto=punto, dias=dias, guardar=True)
            frames.append(df)
            time.sleep(pausa)   # Pausa para respetar el servidor de Open-Meteo

        except Exception as error:
            logger.error(
                f"Error en pronóstico para {punto}: {error}",
                extra={"etl_stage": "extract", "source": "openmeteo_forecast"},
            )

    if not frames:
        return pd.DataFrame()   # Si todo falló, devolvemos vacío

    # Concatenamos todos los puntos en un único DataFrame
    resultado = pd.concat(frames, ignore_index=True)

    # Guardamos también un archivo consolidado con todos los puntos
    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M")
    ruta_consolidado = DIR_CRUDO / "meteo" / f"forecast_todos_{marca_tiempo}.csv"
    resultado.to_csv(ruta_consolidado, index=False)

    logger.info(
        f"Pronóstico consolidado: {len(resultado)} registros ({len(frames)} puntos)",
        extra={"etl_stage": "extract", "source": "openmeteo_forecast", "rows_count": len(resultado)},
    )
    return resultado


# =============================================================================
# BLOQUE DE EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    import json

    print("=" * 60)
    print("SINIA-SA — Extractor Pronóstico Meteorológico (Open-Meteo Forecast)")
    print("=" * 60)
    print(f"Fuente      : Open-Meteo Forecast API (sin registro, sin key)")
    print(f"Endpoint    : {OPENMETEO_BASE_URL}/forecast")
    print(f"Actualiz.   : cada ~1 hora (modelo GFS/ECMWF)")
    print(f"Variables   : {VARIABLES_PRONOSTICO_DIARIAS}")
    print(f"Puntos conf : {list(PUNTOS_METEO.keys())}")

    # ── Prueba 1: pronóstico para un punto ──────────────────────────────
    PUNTO_PRUEBA = list(PUNTOS_METEO.keys())[0]
    print("\n" + "-" * 60)
    print(f"PRUEBA 1 — Pronóstico 7 días para {PUNTO_PRUEBA}")
    print("-" * 60)
    print(f"Punto      : {PUNTO_PRUEBA}")
    print(f"Días       : 7 (hacia adelante desde hoy)")
    print("Descargando...\n")

    df_punto = extraer_pronostico_punto(punto=PUNTO_PRUEBA, dias=7)

    if not df_punto.empty:
        print(f"[OK] Días de pronóstico    : {len(df_punto)}")
        print(f"     Columnas              : {list(df_punto.columns)}")
        print(f"\nPronóstico completo:")
        columnas_mostrar = [
            "fecha", "temperature_2m_max", "temperature_2m_min",
            "relative_humidity_2m_min", "wind_speed_10m_max",
            "precipitation_sum", "precipitation_probability_max",
        ]
        columnas_presentes = [c for c in columnas_mostrar if c in df_punto.columns]
        print(df_punto[columnas_presentes].to_string(index=False))
    else:
        print(f"[ERROR] Sin datos de pronóstico para {PUNTO_PRUEBA}.")

    # ── Prueba 2: pronóstico para todos los puntos ──────────────────────
    print("\n" + "-" * 60)
    print("PRUEBA 2 — Pronóstico 7 días para todos los puntos")
    print("-" * 60)
    print("Descargando...\n")

    df = extraer_pronostico_todos(dias=7)

    if not df.empty:
        print(f"[OK] Total registros       : {len(df)}")
        print(f"     Puntos incluidos      : {sorted(df['punto'].unique().tolist())}")
        print(f"\nResumen por punto (temperatura máx promedio del pronóstico):")
        for punto, grupo in df.groupby("punto"):
            if "temperature_2m_max" in grupo.columns:
                tmax_prom = grupo["temperature_2m_max"].mean()
                lluvia_tot = grupo["precipitation_sum"].sum() if "precipitation_sum" in grupo.columns else 0
                print(f"  {punto:<20}  T_max_prom={tmax_prom:.1f}°C   lluvia_total={lluvia_tot:.1f}mm")
        print(f"\nPrimeras 7 filas del consolidado:")
        columnas_resumen = [
            "fecha", "punto", "temperature_2m_max", "relative_humidity_2m_min",
            "wind_speed_10m_max", "precipitation_sum", "precipitation_probability_max",
        ]
        cols_presentes = [c for c in columnas_resumen if c in df.columns]
        print(df[cols_presentes].head(7).to_string(index=False))
    else:
        print("[ERROR] Sin datos de pronóstico.")

    print("\n" + "=" * 60)
    print("Extractor Pronóstico finalizado.")
    print("=" * 60)
