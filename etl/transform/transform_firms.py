# =============================================================================
# SINIA-UY — Transformación de Datos FIRMS
# =============================================================================
# Este módulo limpia y enriquece los datos crudos de focos de calor de NASA FIRMS.
#
# Los datos crudos tienen problemas típicos que hay que resolver:
#   - Tipos de datos incorrectos (fechas como strings, números como texto)
#   - Focos detectados fuera del alcance regional del proyecto
#   - Duplicados en los bordes entre chunks de descarga
#   - Confianza en formato texto (l/n/h) que dificulta el análisis numérico
#
# Después de la transformación, los datos quedan listos para cargar a la base
# de datos y para el dashboard de visualización.
# =============================================================================

from pathlib import Path

import pandas as pd   # Para manipular y transformar los datos

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.settings import DIR_PROCESADO, SA_BBOX, PAISES_SA   # Carpeta data/processed/ y alcance geográfico
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.transform.firms")

# -----------------------------------------------------------------------------
# CONSTANTES DE TRANSFORMACIÓN
# -----------------------------------------------------------------------------

# Límites geográficos regionales parseados desde SA_BBOX
# SA_BBOX formato: "lon_min,lat_min,lon_max,lat_max"
_bbox_vals = [float(v) for v in SA_BBOX.split(",")]
SA_LON_MIN, SA_LAT_MIN, SA_LON_MAX, SA_LAT_MAX = _bbox_vals

# Bounding boxes por país para asignar el campo pais durante la transformación.
# Permite filtrar explícitamente al alcance BRA/ARG/URY/CHL sin depender solo del bbox.
# Formato: código_iso3 -> (lat_min, lat_max, lon_min, lon_max)
_BBOX_PAISES = {
    "URY": (-34.9, -30.1, -58.4, -53.1),  # Primero para evitar absorción por ARG/BRA
    "CHL": (-56.0, -17.5, -75.7, -66.4),
    "ARG": (-55.1, -21.8, -73.6, -53.6),
    "BRA": (-34.0,   5.3, -73.9, -34.8),
}

# Mapeo del nivel de confianza de VIIRS a valor numérico
# l (low) = 1, n (nominal/normal) = 2, h (high) = 3
# Esto permite ordenar y filtrar por confianza numéricamente
MAPA_CONFIANZA = {"l": 1, "n": 2, "h": 3}


# =============================================================================
# FUNCIÓN PRINCIPAL DE TRANSFORMACIÓN
# =============================================================================

def transformar_firms(df: pd.DataFrame, guardar: bool = True) -> pd.DataFrame:
    """
    Limpia, valida y enriquece un DataFrame crudo de focos FIRMS.

    Pasos de transformación:
    1. Casteo de tipos de datos (strings -> datetime, strings -> float)
    2. Filtro geográfico preliminar por bbox regional
    3. Eliminación de duplicados por clave natural
    4. Normalización de confianza (l/n/h -> 1/2/3)
    5. Creación de columnas derivadas (hora de adquisición, es diurno)
    6. Renombrado de columnas al español para consistencia interna

    Args:
        df:       DataFrame crudo descargado por extract_firms.py
        guardar:  Si True, guarda el resultado como Parquet en data/processed/

    Returns:
        DataFrame transformado y enriquecido, listo para análisis o carga a BD.
    """
    # Si el DataFrame está vacío, no hay nada que transformar
    if df.empty:
        logger.warning("transformar_firms: DataFrame vacío, sin datos para transformar")
        return df

    # Guardamos la cantidad original para reportar cuántos se eliminaron
    cantidad_original = len(df)

    logger.info(
        f"Iniciando transformación FIRMS: {cantidad_original} registros crudos",
        extra={"etl_stage": "transform", "source": "firms"},
    )

    # Hacemos una copia para no modificar el DataFrame original
    df = df.copy()

    # ── Paso 1: Casteo de tipos de datos ─────────────────────────────────────
    # La API devuelve todo como texto. Debemos convertir cada columna al tipo correcto.

    # La fecha de adquisición viene como string "2024-01-15" -> la convertimos a datetime
    df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce")
    # errors="coerce" convierte valores inválidos a NaT (no date) en lugar de dar error

    # Convertimos columnas numéricas de texto a float64
    for columna in ["latitude", "longitude", "frp", "bright_ti4", "bright_ti5", "scan", "track"]:
        if columna in df.columns:   # Solo si la columna existe en este DataFrame
            df[columna] = pd.to_numeric(df[columna], errors="coerce")
            # errors="coerce" convierte valores no numéricos a NaN en lugar de error

    # ── Paso 2: Filtro geográfico ─────────────────────────────────────────────
    # Filtramos focos dentro del bounding box regional.
    # Esto elimina cualquier dato espurio fuera de la región de interés.

    mascara_geografica = (
        df["latitude"].between(SA_LAT_MIN, SA_LAT_MAX) &
        df["longitude"].between(SA_LON_MIN, SA_LON_MAX)
    )

    focos_fuera = (~mascara_geografica).sum()

    if focos_fuera > 0:
        logger.warning(
            f"  Eliminando {focos_fuera} focos con coordenadas fuera del bbox regional",
            extra={"etl_stage": "transform", "source": "firms"},
        )

    df = df[mascara_geografica].copy()

    # ── Paso 2b: Asignación de país por bounding box ──────────────────────────
    # Asignamos el código ISO del país a cada foco usando los bounding boxes.
    # Si un foco cae en zona de solapamiento (fronteras), gana el primero que coincida.
    # Para análisis académico es suficiente; para producción se usaría un polígono exacto.

    def _asignar_pais(lat: float, lon: float) -> str:
        for cod, (lat_min, lat_max, lon_min, lon_max) in _BBOX_PAISES.items():
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                return cod
        return "OTR"   # Otro (fuera del alcance BRA/ARG/URY/CHL pero dentro del bbox regional)

    df["pais"] = [
        _asignar_pais(lat, lon)
        for lat, lon in zip(df["latitude"], df["longitude"])
    ]

    paises_validos = set(PAISES_SA.keys())
    focos_fuera_alcance = int((~df["pais"].isin(paises_validos)).sum())
    if focos_fuera_alcance > 0:
        logger.info(
            f"  Eliminando {focos_fuera_alcance} focos fuera del alcance BRA/ARG/URY/CHL",
            extra={"etl_stage": "transform", "source": "firms"},
        )
    df = df[df["pais"].isin(paises_validos)].copy()

    # ── Paso 3: Eliminación de duplicados ────────────────────────────────────
    # Un foco es duplicado si tiene la misma posición, fecha, hora y satélite
    # Esto puede ocurrir en los bordes entre chunks de descarga

    columnas_clave = [c for c in ["latitude", "longitude", "acq_date", "acq_time", "satellite"]
                      if c in df.columns]   # Solo usamos las columnas que existen

    cantidad_antes = len(df)                              # Guardamos cantidad antes
    df = df.drop_duplicates(subset=columnas_clave)       # Eliminamos duplicados
    duplicados_eliminados = cantidad_antes - len(df)      # Calculamos cuántos se eliminaron

    if duplicados_eliminados > 0:
        logger.info(f"  Eliminados {duplicados_eliminados} registros duplicados")

    # ── Paso 4: Normalización de confianza ───────────────────────────────────
    # VIIRS usa un sistema de confianza en texto: l (bajo), n (nominal), h (alto)
    # Lo convertimos a número para poder hacer análisis cuantitativos

    if "confidence" in df.columns:
        df["confianza_num"] = (
            df["confidence"]
            .astype(str)          # Aseguramos que sea string
            .str.lower()          # Convertimos a minúsculas (por si viene en mayúsculas)
            .str.strip()          # Eliminamos espacios al inicio/fin
            .map(MAPA_CONFIANZA)  # Aplicamos el mapeo: "l"->1, "n"->2, "h"->3
            .fillna(             # Para MODIS que usa números directamente (0-100)
                pd.to_numeric(df["confidence"], errors="coerce")
            )
        )

    # ── Paso 5: Columnas derivadas ───────────────────────────────────────────
    # Creamos columnas nuevas calculadas a partir de las existentes

    if "acq_time" in df.columns:
        # acq_time viene en formato HHMM como entero (ej: 1430 = 14:30)
        # Dividimos por 100 para obtener solo la hora (1430 // 100 = 14)
        df["hora_adq"] = pd.to_numeric(df["acq_time"], errors="coerce") // 100

        # Determinamos si el foco fue detectado de día o de noche
        if "daynight" in df.columns:
            # FIRMS ya tiene una columna daynight: "D" = diurno, "N" = nocturno
            df["es_diurno"] = df["daynight"].eq("D")   # True si es "D"
        else:
            # Si no hay columna daynight, estimamos por la hora (6am-6pm = diurno)
            df["es_diurno"] = df["hora_adq"].between(6, 18)

    # ── Paso 6: Renombrado de columnas al español ────────────────────────────
    # Renombramos las columnas en inglés (de la API) a español para consistencia

    mapa_renombre = {
        "latitude":   "latitud",              # Coordenada latitud
        "longitude":  "longitud",             # Coordenada longitud
        "acq_date":   "fecha_adq",            # Fecha de adquisición satelital
        "acq_time":   "hora_adq_hhmm",        # Hora en formato HHMM
        "confidence": "confianza_raw",        # Confianza en formato original (l/n/h)
        "frp":        "potencia_radiativa",   # Fire Radiative Power en megawatts
        "bright_ti4": "brillo_ti4",           # Temperatura de brillo banda TI4 (Kelvin)
        "bright_ti5": "brillo_ti5",           # Temperatura de brillo banda TI5 (Kelvin)
        "satellite":  "satelite",             # Identificador del satélite
        "instrument": "instrumento",          # Instrumento sensor (VIIRS, MODIS)
        "daynight":   "dia_noche",            # D=diurno, N=nocturno
    }

    # Solo renombramos las columnas que realmente existen en el DataFrame
    df = df.rename(columns={k: v for k, v in mapa_renombre.items() if k in df.columns})

    # Reportamos el resultado final de la transformación
    cantidad_final = len(df)
    logger.info(
        f"Transformación FIRMS completa: {cantidad_original} -> {cantidad_final} registros",
        extra={"etl_stage": "transform", "source": "firms", "rows_count": cantidad_final},
    )

    # Guardamos como Parquet (formato columnar eficiente) si se solicitó
    if guardar and not df.empty:
        ruta_salida = DIR_PROCESADO / "firms_procesado.parquet"
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(ruta_salida, index=False)   # Parquet es más eficiente que CSV para análisis
        logger.info(f"Parquet guardado en: {ruta_salida}")

    return df


# =============================================================================
# BLOQUE DE EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    import glob

    print("=" * 60)
    print("SINIA-UY — Transformación de Datos FIRMS")
    print("=" * 60)

    # Buscamos el archivo CSV más reciente en data/raw/firms/
    archivos = sorted(glob.glob(str(
        Path(__file__).resolve().parent.parent.parent / "data/raw/firms/*.csv"
    )))

    if not archivos:
        print("No hay archivos en data/raw/firms/. Ejecutá primero extract_firms.py")
    else:
        archivo = archivos[-1]   # Tomamos el más reciente
        print(f"\nProcesando: {Path(archivo).name}\n")

        # Leemos el CSV crudo y aplicamos la transformación
        df_crudo = pd.read_csv(archivo)
        df_procesado = transformar_firms(df_crudo)

        print(f"Registros después de transformación: {len(df_procesado)}")
        if not df_procesado.empty:
            print(df_procesado.head().to_string())
