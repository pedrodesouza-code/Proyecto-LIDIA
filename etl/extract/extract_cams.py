# =============================================================================
# SINIA-SA — Extractor CAMS (Calidad del Aire)
# =============================================================================
# CAMS = Copernicus Atmosphere Monitoring Service
# Servicio europeo de monitoreo de la atmósfera que provee datos de
# contaminación del aire, aerosoles y partículas en suspensión.
#
# Contexto del proyecto:
# Usamos CAMS vía Open-Meteo Air Quality API (proxy gratuito, sin key)
# para los 36 puntos del alcance final: Uruguay completo + Brasil/Argentina estratégicos + Chile volcánico.
#
# Variables principales:
#   - PM10:  Partículas con diámetro ≤ 10 µm (humo de incendios)
#   - PM2.5: Partículas con diámetro ≤ 2.5 µm (más peligrosas para la salud)
#   - AOD:   Aerosol Optical Depth (opacidad atmosférica por partículas)
#   - AQI:   European Air Quality Index (índice de calidad del aire 0-500)
#
# NO requiere API key — usamos el proxy gratuito de Open-Meteo.
# URL: https://air-quality-api.open-meteo.com/v1/air-quality
# =============================================================================

import time   # Para pausas entre requests
from datetime import datetime   # Para fechas y marcas de tiempo
from pathlib import Path

import pandas as pd
import requests

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.settings import PUNTOS_METEO, DIR_CRUDO
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.extract.cams")

# URL de la API de Calidad del Aire de Open-Meteo (proxy gratuito de CAMS)
# Esta API no requiere registro ni clave de acceso
URL_CALIDAD_AIRE = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Variables horarias de calidad del aire disponibles en la API
# Todas se piden en una sola request como lista separada por comas
VARIABLES_HORARIAS_CALIDAD = [
    "pm10",                  # Material particulado ≤10µm (µg/m³) — humo, polvo grueso
    "pm2_5",                 # Material particulado ≤2.5µm (µg/m³) — partículas finas, más tóxicas
    "aerosol_optical_depth", # Profundidad óptica de aerosoles (0-1) — opacidad del aire
    "dust",                  # Polvo mineral en suspensión (µg/m³)
    "european_aqi",          # Índice de Calidad del Aire europeo (0-500, >50 = malo)
    "european_aqi_pm10",     # AQI europeo calculado solo con PM10
    "european_aqi_pm2_5",    # AQI europeo calculado solo con PM2.5
]


# =============================================================================
# FUNCIÓN 1: Descarga para un punto específico
# =============================================================================

def extraer_cams_historico(
    punto: str = "Rivera",             # Punto de monitoreo a descargar
    fecha_inicio: str = "2024-01-01", # Fecha de inicio
    fecha_fin: str = "2024-12-31",    # Fecha de fin
    granularidad: str = "hourly",     # Solo "hourly" está disponible en esta API
    guardar: bool = True,             # Si True, guarda el CSV
) -> pd.DataFrame:
    """
    Descarga datos de calidad del aire (CAMS) para un punto de Uruguay.

    Los datos están disponibles desde 2022 hasta el presente, con resolución
    horaria. Para períodos largos, la API puede tardar varios segundos.

    Args:
        punto:        Punto de monitoreo (debe estar en PUNTOS_METEO)
        fecha_inicio: Fecha de inicio (YYYY-MM-DD)
        fecha_fin:    Fecha de fin (YYYY-MM-DD)
        granularidad: Solo "hourly" disponible en esta API
        guardar:      Si True, guarda el CSV en data/raw/cams/

    Returns:
        DataFrame con datos horarios de calidad del aire.
        Columnas: fecha_hora, pm10, pm2_5, aerosol_optical_depth, dust,
                  european_aqi, european_aqi_pm10, european_aqi_pm2_5,
                  punto, latitud, longitud, fuente
    """
    # Verificamos que el punto existe en nuestra configuración
    if punto not in PUNTOS_METEO:
        raise ValueError(
            f"Punto '{punto}' no encontrado.\n"
            f"Opciones disponibles: {list(PUNTOS_METEO.keys())}"
        )

    # Obtenemos las coordenadas del punto
    latitud, longitud = PUNTOS_METEO[punto]

    # Construimos los parámetros de la request HTTP
    parametros = {
        "latitude":   latitud,            # Latitud del punto
        "longitude":  longitud,           # Longitud del punto
        "start_date": fecha_inicio,       # Inicio del período
        "end_date":   fecha_fin,          # Fin del período
        "timezone":   "UTC",  # UTC — neutro para sistema multi-país en Sudamérica
        "hourly":     ",".join(VARIABLES_HORARIAS_CALIDAD),  # Variables a descargar
    }

    logger.info(
        f"Descargando CAMS Calidad del Aire: {punto} ({latitud}, {longitud}), "
        f"{fecha_inicio} -> {fecha_fin}",
        extra={"etl_stage": "extract", "source": "cams_openmeteo"},
    )

    # Hacemos la petición a la API de calidad del aire de Open-Meteo
    respuesta = requests.get(URL_CALIDAD_AIRE, params=parametros, timeout=60)
    respuesta.raise_for_status()
    datos = respuesta.json()   # La respuesta es JSON

    # Verificamos que la respuesta contenga datos horarios
    if "hourly" in datos:
        # Convertimos el JSON a DataFrame
        df = pd.DataFrame(datos["hourly"])
        # Renombramos "time" a "fecha_hora" para claridad
        df.rename(columns={"time": "fecha_hora"}, inplace=True)
    else:
        logger.warning(f"Sin datos CAMS disponibles para {punto} en el período solicitado")
        return pd.DataFrame()

    # Agregamos metadata de identificación a cada fila
    df["punto"]    = punto                    # Nombre del punto de monitoreo
    df["latitud"]  = latitud                  # Coordenada latitud
    df["longitud"] = longitud                 # Coordenada longitud
    df["fuente"]   = "CAMS_via_OpenMeteo"     # Identificador de la fuente de datos

    logger.info(
        f"CAMS: {len(df)} registros horarios descargados para {punto}",
        extra={"etl_stage": "extract", "source": "cams_openmeteo", "rows_count": len(df)},
    )

    # Guardamos el CSV si se solicitó
    if guardar and not df.empty:
        ruta_salida = (
            DIR_CRUDO / "cams"
            / f"cams_{punto.lower()}_{granularidad}_{fecha_inicio}_{fecha_fin}.csv"
        )
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(ruta_salida, index=False)
        logger.info(f"CSV guardado en: {ruta_salida}")

    return df


# =============================================================================
# FUNCIÓN 2: Descarga para todos los puntos
# =============================================================================

def extraer_cams_todos_los_puntos(
    fecha_inicio: str = "2024-01-01",
    fecha_fin: str = "2024-12-31",
    pausa: float = 0.5,   # Segundos entre requests para no saturar la API
) -> pd.DataFrame:
    """
    Descarga calidad del aire para todos los puntos de monitoreo de Sudamérica.

    Args:
        fecha_inicio: Inicio del período (YYYY-MM-DD)
        fecha_fin:    Fin del período (YYYY-MM-DD)
        pausa:        Segundos entre requests

    Returns:
        DataFrame concatenado con datos de todos los puntos.
    """
    frames = []

    for punto in PUNTOS_METEO:
        try:
            df = extraer_cams_historico(
                punto=punto,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                guardar=True,
            )
            frames.append(df)
            time.sleep(pausa)   # Pausa para respetar el rate limiting

        except Exception as error:
            logger.error(
                f"Error extrayendo CAMS para {punto}: {error}",
                extra={"etl_stage": "extract", "source": "cams"},
            )
            continue

    if frames:
        resultado = pd.concat(frames, ignore_index=True)
        logger.info(
            f"CAMS total: {len(resultado)} registros de {len(frames)} puntos",
            extra={"etl_stage": "extract", "source": "cams"},
        )
        return resultado
    return pd.DataFrame()


# =============================================================================
# FUNCIÓN 3: Exploración de calidad de los datos CAMS
# =============================================================================

def explorar_muestra_cams(df: pd.DataFrame) -> dict:
    """
    Analiza la calidad de un DataFrame de calidad del aire.

    Args:
        df: DataFrame crudo de datos CAMS.

    Returns:
        Diccionario con métricas de calidad.
    """
    if df.empty:
        return {"error": "DataFrame vacío — no hay datos para analizar"}

    # Campos críticos para calidad del aire
    campos_criticos = ["fecha_hora", "pm10", "pm2_5"]
    campos_presentes = [c for c in campos_criticos if c in df.columns]

    # Completitud de los campos críticos
    completitud = {
        campo: round((1 - df[campo].isna().mean()) * 100, 2)
        for campo in campos_presentes
    }

    # Rangos estadísticos de los contaminantes principales
    rangos = {}
    for campo in ["pm10", "pm2_5", "aerosol_optical_depth", "european_aqi"]:
        if campo in df.columns:
            rangos[campo] = {
                "min":       round(float(df[campo].min(skipna=True)), 2),
                "max":       round(float(df[campo].max(skipna=True)), 2),
                "media":     round(float(df[campo].mean(skipna=True)), 2),
                "nulos_pct": round(float(df[campo].isna().mean()) * 100, 2),
            }

    return {
        "total_registros": len(df),
        "columnas":        list(df.columns),
        "puntos":          list(df["punto"].unique()) if "punto" in df.columns else [],
        "completitud_pct": completitud,
        "rangos_numericos": rangos,
        "fuente":          "CAMS vía Open-Meteo Air Quality API (contingencia PM10)",
    }


# =============================================================================
# BLOQUE DE EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    import json

    print("=" * 60)
    print("SINIA-SA — Extractor CAMS (Calidad del Aire)")
    print("=" * 60)
    print(f"Fuente      : CAMS vía Open-Meteo Air Quality API (proxy gratuito)")
    print(f"Endpoint    : {URL_CALIDAD_AIRE}")
    print(f"Resolución  : horaria (datos desde 2022)")
    print(f"Variables   : {VARIABLES_HORARIAS_CALIDAD}")
    print(f"Puntos conf : {list(PUNTOS_METEO.keys())}")

    # ── Prueba 1: un punto, un mes ───────────────────────────────────────
    PUNTO_PRUEBA = list(PUNTOS_METEO.keys())[0]   # Primer punto configurado
    print("\n" + "-" * 60)
    print(f"PRUEBA 1 — Calidad del aire para {PUNTO_PRUEBA} (enero 2024)")
    print("-" * 60)
    print(f"Punto      : {PUNTO_PRUEBA}")
    print(f"Período    : 2024-01-01  →  2024-01-31")
    print(f"Granular.  : hourly")
    print("Descargando...\n")

    df = extraer_cams_historico(
        punto=PUNTO_PRUEBA,
        fecha_inicio="2024-01-01",
        fecha_fin="2024-01-31",
    )

    if not df.empty:
        print(f"[OK] Registros descargados : {len(df)}")
        print(f"     Columnas              : {list(df.columns)}")
        print(f"     Rango fechas          : {df['fecha_hora'].min()}  →  {df['fecha_hora'].max()}")
        print(f"\nPrimeras 5 filas:")
        print(df.head().to_string())
        print(f"\nMétricas de calidad:")
        metricas = explorar_muestra_cams(df)
        print(json.dumps(metricas, indent=2, ensure_ascii=False))
    else:
        print(f"[ERROR] Sin datos para {PUNTO_PRUEBA} — verificar conectividad.")

    # ── Prueba 2: segundo punto de control ──────────────────────────────
    if len(PUNTOS_METEO) > 1:
        PUNTO_PRUEBA_2 = list(PUNTOS_METEO.keys())[1]
        print("\n" + "-" * 60)
        print(f"PRUEBA 2 — Control rápido para {PUNTO_PRUEBA_2} (enero 2024)")
        print("-" * 60)
        print("Descargando...\n")

        df2 = extraer_cams_historico(
            punto=PUNTO_PRUEBA_2,
            fecha_inicio="2024-01-01",
            fecha_fin="2024-01-07",
        )
        if not df2.empty:
            print(f"[OK] Registros: {len(df2)}")
            for col in ["pm10", "pm2_5", "european_aqi"]:
                if col in df2.columns:
                    media = df2[col].mean(skipna=True)
                    print(f"     {col:<25} media = {media:.2f}")
        else:
            print(f"[INFO] Sin datos para {PUNTO_PRUEBA_2}.")

    print("\n" + "=" * 60)
    print("Extractor CAMS finalizado.")
    print("=" * 60)
1
