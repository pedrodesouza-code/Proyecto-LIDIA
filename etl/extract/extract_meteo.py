# =============================================================================
# SINIA-SA — Extractor Meteorológico (Open-Meteo)
# =============================================================================
# Este módulo descarga datos meteorológicos históricos para los 36 puntos
# del alcance final desde la API gratuita de Open-Meteo.
#
# Open-Meteo es una API meteorológica de código abierto que no requiere
# registro ni API key. Provee datos desde 1940 hasta el presente.
#
# Los datos meteorológicos se usan para calcular el índice de riesgo de
# incendio: temperatura alta + humedad baja + viento fuerte + sequía = peligro.
#
# Modos de descarga:
#   - Histórico: datos pasados desde el archivo (archive API)
#   - Todos los puntos: descarga secuencial para los 36 puntos del alcance
# =============================================================================

import time   # Para agregar pausas entre requests y respetar el rate limiting
from datetime import datetime, date, timedelta   # Para manejar fechas
from pathlib import Path   # Para rutas de archivos multiplataforma

import pandas as pd   # Para manipular datos en tablas
import requests       # Para hacer peticiones HTTP a la API

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Importamos la configuración y el logger del proyecto
from config.settings import (
    OPENMETEO_BASE_URL,      # URL base para forecast (pronóstico)
    OPENMETEO_ARCHIVE_URL,   # URL para datos históricos de archivo
    PUNTOS_METEO,            # Diccionario con los 36 puntos del alcance y sus coordenadas
    DIR_CRUDO,               # Carpeta data/raw/ para guardar los CSVs descargados
)
from etl.utils.logger import setup_logger

# Logger específico para este módulo
logger = setup_logger("sinia.extract.meteo")

# -----------------------------------------------------------------------------
# VARIABLES METEOROLÓGICAS A DESCARGAR
# Open-Meteo organiza las variables en "daily" (una por día) y "hourly" (por hora)
# Seleccionamos las más relevantes para el cálculo del índice de riesgo de incendio
# -----------------------------------------------------------------------------

# Variables diarias — una observación por día para análisis de riesgo
VARIABLES_DIARIAS = [
    "temperature_2m_max",             # Temperatura máxima a 2m del suelo (°C) — calor del día
    "temperature_2m_min",             # Temperatura mínima a 2m del suelo (°C) — frescor nocturno
    "relative_humidity_2m_min",       # Humedad relativa mínima del día (%) — condición más seca
    "relative_humidity_2m_max",       # Humedad relativa máxima del día (%) — condición más húmeda
    "wind_speed_10m_max",             # Velocidad máxima del viento a 10m (km/h) — potencial propagación
    "wind_direction_10m_dominant",    # Dirección dominante del viento (grados) — de dónde viene
    "precipitation_sum",              # Precipitación total del día (mm) — lluvia caída
    "et0_fao_evapotranspiration",     # Evapotranspiración FAO (mm/día) — indicador de sequía acumulada
]

# Variables horarias — una observación por hora (para análisis más detallados)
VARIABLES_HORARIAS = [
    "temperature_2m",          # Temperatura horaria a 2m (°C)
    "relative_humidity_2m",    # Humedad relativa horaria (%)
    "wind_speed_10m",          # Velocidad del viento horaria a 10m (km/h)
    "wind_direction_10m",      # Dirección del viento horaria (grados)
    "precipitation",           # Precipitación horaria (mm)
]


# =============================================================================
# FUNCIÓN 1: Descarga histórica para un punto específico
# =============================================================================

def extraer_meteo_historico(
    punto: str = "Rivera",             # Nombre del punto de monitoreo
    fecha_inicio: str = "2024-01-01", # Inicio del período (YYYY-MM-DD)
    fecha_fin: str = "2024-12-31",    # Fin del período (YYYY-MM-DD)
    granularidad: str = "daily",      # "daily" para datos diarios, "hourly" para horarios
    guardar: bool = True,             # Si True, guarda el CSV en data/raw/meteo/
) -> pd.DataFrame:
    """
    Descarga datos meteorológicos históricos de Open-Meteo para un punto.

    Args:
        punto:        Nombre del departamento/ciudad. Debe estar en PUNTOS_METEO.
                      Opciones disponibles en config.settings.PUNTOS_METEO.
        fecha_inicio: Fecha de inicio del período histórico (formato YYYY-MM-DD)
        fecha_fin:    Fecha de fin del período (formato YYYY-MM-DD)
        granularidad: "daily" para análisis de riesgo (recomendado)
                      "hourly" para análisis detallado de eventos
        guardar:      Si True, guarda el resultado como CSV en data/raw/meteo/

    Returns:
        DataFrame con los datos meteorológicos. Para granularidad daily, contiene
        columnas como: fecha, temperature_2m_max, relative_humidity_2m_min, etc.
        Siempre incluye columnas: punto, latitud, longitud
    """
    # Verificamos que el punto solicitado exista en nuestra configuración
    if punto not in PUNTOS_METEO:
        raise ValueError(
            f"Punto '{punto}' no encontrado en PUNTOS_METEO.\n"
            f"Opciones disponibles: {list(PUNTOS_METEO.keys())}"
        )

    # Obtenemos las coordenadas del punto desde el diccionario de configuración
    latitud, longitud = PUNTOS_METEO[punto]

    # Construimos el diccionario de parámetros para la API de Open-Meteo
    parametros = {
        "latitude":   latitud,          # Latitud del punto en grados decimales
        "longitude":  longitud,         # Longitud del punto en grados decimales
        "start_date": fecha_inicio,     # Fecha de inicio del período solicitado
        "end_date":   fecha_fin,        # Fecha de fin del período solicitado
        "timezone":   "UTC",   # UTC — neutro para sistema multi-país en Sudamérica
    }

    # Según la granularidad, agregamos las variables correspondientes
    if granularidad == "daily":
        # Para datos diarios, usamos la clave "daily" con las variables separadas por coma
        parametros["daily"] = ",".join(VARIABLES_DIARIAS)
    else:
        # Para datos horarios, usamos la clave "hourly"
        parametros["hourly"] = ",".join(VARIABLES_HORARIAS)

    # Registramos el inicio de la descarga
    logger.info(
        f"Descargando meteo histórico: {punto} ({latitud}, {longitud}), "
        f"{fecha_inicio} -> {fecha_fin}, granularidad={granularidad}",
        extra={"etl_stage": "extract", "source": "openmeteo_archivo"},
    )

    # Hacemos la petición GET a la API de archivo de Open-Meteo
    # Los parámetros se envían en la URL automáticamente por requests
    respuesta = requests.get(OPENMETEO_ARCHIVE_URL, params=parametros, timeout=60)
    respuesta.raise_for_status()   # Error si HTTP devuelve código de error

    # La API de Open-Meteo devuelve JSON, no CSV
    datos = respuesta.json()

    # Parseamos el JSON según la granularidad solicitada
    if granularidad == "daily" and "daily" in datos:
        # Los datos diarios vienen en datos["daily"] como diccionario de listas
        df = pd.DataFrame(datos["daily"])
        # Renombramos "time" (nombre original de Open-Meteo) a "fecha" (nombre en español)
        df.rename(columns={"time": "fecha"}, inplace=True)

    elif granularidad == "hourly" and "hourly" in datos:
        # Los datos horarios vienen en datos["hourly"]
        df = pd.DataFrame(datos["hourly"])
        # Para horarios usamos "fecha_hora" para indicar que incluye hora
        df.rename(columns={"time": "fecha_hora"}, inplace=True)

    else:
        # Si la API no devolvió datos para el período solicitado
        logger.warning(f"Sin datos disponibles para {punto} en el período solicitado")
        return pd.DataFrame()   # Devolvemos DataFrame vacío

    # Agregamos columnas de metadata para saber a qué punto corresponde cada fila
    df["punto"]    = punto      # Nombre del punto (ej: "Rivera")
    df["latitud"]  = latitud    # Latitud del punto
    df["longitud"] = longitud   # Longitud del punto

    logger.info(
        f"Open-Meteo Archivo: {len(df)} registros descargados para {punto}",
        extra={"etl_stage": "extract", "source": "openmeteo_archivo", "rows_count": len(df)},
    )

    # Guardamos el CSV si se solicitó y el DataFrame tiene datos
    if guardar and not df.empty:
        # El nombre del archivo incluye punto, granularidad y período para identificarlo
        ruta_salida = (
            DIR_CRUDO / "meteo"
            / f"meteo_{punto.lower()}_{granularidad}_{fecha_inicio}_{fecha_fin}.csv"
        )
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(ruta_salida, index=False)   # Guardamos sin índice de fila
        logger.info(f"CSV guardado en: {ruta_salida}")

    return df


# =============================================================================
# FUNCIÓN 2: Descarga para todos los puntos de monitoreo
# =============================================================================

def extraer_meteo_todos_los_puntos(
    fecha_inicio: str = "2024-01-01",   # Período de descarga
    fecha_fin: str = "2024-12-31",
    granularidad: str = "daily",         # Granularidad de los datos
    pausa: float = 0.5,                  # Segundos de pausa entre requests
) -> pd.DataFrame:
    """
    Descarga datos meteorológicos para los 36 puntos del alcance final.

    Llama a extraer_meteo_historico() en secuencia para cada punto y agrega
    una pausa entre requests para respetar el rate limiting de la API.

    Args:
        fecha_inicio: Inicio del período (YYYY-MM-DD)
        fecha_fin:    Fin del período (YYYY-MM-DD)
        granularidad: "daily" o "hourly"
        pausa:        Segundos entre requests (0.5 por defecto para no saturar la API)

    Returns:
        DataFrame unificado con datos de todos los puntos.
        La columna "punto" indica a qué departamento pertenece cada fila.
    """
    frames = []   # Lista para acumular los DataFrames de cada punto

    # Iteramos sobre cada punto configurado en PUNTOS_METEO
    for punto in PUNTOS_METEO:
        try:
            # Descargamos los datos para este punto
            df = extraer_meteo_historico(
                punto=punto,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                granularidad=granularidad,
                guardar=True,   # Guardamos cada punto individualmente también
            )
            frames.append(df)   # Agregamos el resultado a la lista

            # Pausa entre requests para no sobrecargar el servidor de Open-Meteo
            time.sleep(pausa)

        except Exception as error:
            # Si un punto falla, registramos el error y continuamos con el siguiente
            # Esto evita que un error puntual cancele toda la descarga
            logger.error(
                f"Error extrayendo meteo para {punto}: {error}",
                extra={"etl_stage": "extract", "source": "openmeteo"},
            )
            continue   # Pasamos al siguiente punto

    # Si obtuvimos datos de al menos un punto, los concatenamos
    if frames:
        resultado = pd.concat(frames, ignore_index=True)   # Une todos los DataFrames en uno
        logger.info(
            f"Meteo total: {len(resultado)} registros de {len(frames)} puntos",
            extra={"etl_stage": "extract", "source": "openmeteo", "rows_count": len(resultado)},
        )
        return resultado

    return pd.DataFrame()   # Si ningún punto funcionó, devolvemos vacío


# =============================================================================
# FUNCIÓN 3: Exploración de calidad de los datos meteorológicos
# =============================================================================

def explorar_muestra_meteo(df: pd.DataFrame) -> dict:
    """
    Analiza la calidad de un DataFrame meteorológico.

    Calcula completitud, rangos estadísticos y detecta valores anómalos.
    Útil para el informe de calidad de datos (EC1).

    Args:
        df: DataFrame de datos meteorológicos crudos.

    Returns:
        Diccionario con métricas de calidad del dataset.
    """
    if df.empty:
        return {"error": "DataFrame vacío — no hay datos para analizar"}

    # Determinamos qué campos críticos revisar según la granularidad
    # Si hay columna "fecha" es diario, si hay "fecha_hora" es horario
    if "fecha" in df.columns:
        # Campos críticos para datos diarios
        campos_criticos = [
            "fecha", "temperature_2m_max", "relative_humidity_2m_min",
            "wind_speed_10m_max", "precipitation_sum",
        ]
    else:
        # Campos críticos para datos horarios
        campos_criticos = [
            "fecha_hora", "temperature_2m", "relative_humidity_2m",
            "wind_speed_10m", "precipitation",
        ]

    # Solo revisamos los campos que realmente existen en el DataFrame
    campos_presentes = [c for c in campos_criticos if c in df.columns]

    # Calculamos el % de valores no nulos (completitud) para cada campo
    completitud = {
        campo: round((1 - df[campo].isna().mean()) * 100, 2)
        for campo in campos_presentes
    }

    # Calculamos estadísticas de rango para todas las columnas numéricas
    rangos = {}
    for campo in df.select_dtypes(include=["number"]).columns:
        # Excluimos las columnas de coordenadas (no tienen interés estadístico)
        if campo in ["latitud", "longitud"]:
            continue
        rangos[campo] = {
            "min":       round(float(df[campo].min()), 2),              # Mínimo
            "max":       round(float(df[campo].max()), 2),              # Máximo
            "media":     round(float(df[campo].mean()), 2),             # Promedio
            "nulos_pct": round(float(df[campo].isna().mean()) * 100, 2), # % de nulos
        }

    return {
        "total_registros": len(df),
        "columnas":        list(df.columns),
        "puntos":          list(df["punto"].unique()) if "punto" in df.columns else [],
        "completitud_pct": completitud,
        "rangos_numericos": rangos,
    }


# =============================================================================
# BLOQUE DE EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    import json

    print("=" * 60)
    print("SINIA-SA — Extractor Meteorológico (Open-Meteo)")
    print("=" * 60)
    print(f"Fuente      : Open-Meteo Archive API (sin registro, sin key)")
    print(f"Endpoint    : {OPENMETEO_ARCHIVE_URL}")
    print(f"Puntos conf : {list(PUNTOS_METEO.keys())}")
    print(f"Variables   : {VARIABLES_DIARIAS}")

    # ── Prueba 1: datos diarios para un punto ───────────────────────────
    print("\n" + "-" * 60)
    print("PRUEBA 1 — Datos diarios para Rivera (enero-marzo 2024)")
    print("-" * 60)
    print("Punto      : Rivera")
    print("Período    : 2024-01-01  →  2024-03-31")
    print("Granular.  : daily")
    print("Descargando...\n")

    df = extraer_meteo_historico(
        punto="Rivera",
        fecha_inicio="2024-01-01",
        fecha_fin="2024-03-31",
        granularidad="daily",
    )

    if not df.empty:
        print(f"[OK] Registros descargados : {len(df)}")
        print(f"     Columnas              : {list(df.columns)}")
        print(f"\nPrimeras 5 filas:")
        print(df.head().to_string())
        print(f"\nMétricas de calidad:")
        metricas = explorar_muestra_meteo(df)
        print(json.dumps(metricas, indent=2, ensure_ascii=False))
    else:
        print("[ERROR] Sin datos — verificar conectividad con Open-Meteo.")

    # ── Prueba 2: resumen de todos los puntos (solo enero 2024) ─────────
    print("\n" + "-" * 60)
    print("PRUEBA 2 — Todos los puntos configurados (enero 2024)")
    print("-" * 60)
    print("Período    : 2024-01-01  →  2024-01-31")
    print("Descargando...\n")

    df_todos = extraer_meteo_todos_los_puntos(
        fecha_inicio="2024-01-01",
        fecha_fin="2024-01-31",
        granularidad="daily",
    )

    if not df_todos.empty:
        print(f"[OK] Total registros       : {len(df_todos)}")
        print(f"     Puntos descargados    : {sorted(df_todos['punto'].unique().tolist())}")
        print(f"     Registros por punto   :")
        for p, cnt in df_todos.groupby("punto").size().items():
            print(f"       {p:<20} {cnt} filas")
    else:
        print("[ERROR] Sin datos para ningún punto.")

    print("\n" + "=" * 60)
    print("Extractor Open-Meteo finalizado.")
    print("=" * 60)
