# =============================================================================
# SINIA-SA — Extractor NASA FIRMS
# =============================================================================
# Este módulo descarga focos de calor (puntos donde un satélite detectó
# temperatura anormalmente alta, indicando posible incendio) para Sudamérica
# desde la API gratuita de NASA FIRMS.
#
# FIRMS = Fire Information for Resource Management System
# Satélites usados: VIIRS (Suomi NPP y NOAA-20) y MODIS (Terra/Aqua)
#
# Dos modos de descarga:
#   - NRT (Near Real-Time): datos de las últimas horas (hasta 10 días atrás)
#   - Archive: datos históricos con mayor precisión (usando bounding box + chunks)
#
# Requiere MAP_KEY gratuita en: https://firms.modaps.eosdis.nasa.gov/api/area/
# =============================================================================

import io        # Para convertir texto descargado de la API en objeto archivo legible por pandas
import time      # Para agregar pausas entre requests y no saturar la API
from datetime import datetime, date, timedelta   # Para manejar fechas y calcular rangos
from pathlib import Path   # Para manejar rutas de archivos de forma multiplataforma

import pandas as pd   # Para manipular los datos en tablas (DataFrames)
import requests       # Para hacer las peticiones HTTP a la API de NASA

# Agregamos la raíz del proyecto al path de Python para que encuentre los módulos internos
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Importamos configuración central del proyecto
from config.settings import (
    FIRMS_MAP_KEY,    # Clave de acceso a la API de FIRMS
    FIRMS_BASE_URL,   # URL base de la API
    FIRMS_SHAPEFILE_PATH,
    SA_BBOX,          # Bounding box de Sudamérica: "lon_min,lat_min,lon_max,lat_max"
    DIR_CRUDO,        # Carpeta data/raw/ donde guardamos los datos sin procesar
)
from etl.utils.logger import setup_logger   # Sistema de logging del proyecto

# Creamos el logger específico para este módulo
# El nombre jerárquico "sinia.extract.firms" ayuda a filtrar logs por módulo
logger = setup_logger("sinia.extract.firms")

# -----------------------------------------------------------------------------
# CONSTANTES DEL EXTRACTOR
# -----------------------------------------------------------------------------

# Bounding box de Sudamérica importado desde settings.
# Formato requerido por la API de FIRMS: "lon_min,lat_min,lon_max,lat_max"
# Cubre los 6 países núcleo: Brasil, Bolivia, Paraguay, Argentina, Chile, Perú.
FIRMS_BBOX = SA_BBOX   # "-82.0,-56.0,-34.0,13.0"

# Máximo de días por request que acepta el endpoint de archivo de FIRMS
# Si pedimos un rango mayor, debemos dividirlo en chunks de este tamaño
FIRMS_DIAS_POR_CHUNK = 5


# =============================================================================
# FUNCIÓN 0: Lectura de shapefile histórico local
# =============================================================================

def extraer_firms_shapefile(
    ruta_shapefile: str | Path | None = None,
    guardar: bool = True,
    max_features: int | None = None,
    skip_features: int = 0,
) -> pd.DataFrame:
    """
    Lee un shapefile histórico FIRMS descargado desde NASA.

    Esta es la ruta de extracción que corresponde al dataset real pesado del
    proyecto cuando los archivos .shp/.shx/.dbf/.prj ya están disponibles en el
    servidor o en la máquina local. Devuelve un GeoDataFrame/DataFrame con las
    columnas originales de FIRMS; la normalización se hace en transform_firms.

    Args:
        ruta_shapefile: Ruta al .shp. Si no se indica, usa FIRMS_SHAPEFILE_PATH.
        guardar: Guarda una copia raw en Parquet para reproducibilidad.
        max_features: Límite opcional para pruebas/muestras.
        skip_features: Offset opcional para lectura por bloques.

    Returns:
        DataFrame con columnas FIRMS originales y geometry en EPSG:4326.
    """
    ruta = Path(ruta_shapefile or FIRMS_SHAPEFILE_PATH).expanduser()
    if not ruta.exists():
        raise FileNotFoundError(
            f"Shapefile FIRMS no encontrado: {ruta}. "
            "Configurá FIRMS_SHAPEFILE_PATH en config/.env o docker/.env."
        )

    logger.info(
        f"Leyendo shapefile FIRMS: {ruta}",
        extra={"etl_stage": "extract", "source": "firms_shapefile"},
    )

    try:
        import pyogrio
        df = pyogrio.read_dataframe(
            ruta,
            max_features=max_features,
            skip_features=skip_features,
        )
    except ImportError as exc:
        raise ImportError(
            "Para leer shapefiles FIRMS instalá dependencias geoespaciales: "
            "geopandas y pyogrio."
        ) from exc

    logger.info(
        f"FIRMS shapefile: {len(df)} registros leídos",
        extra={"etl_stage": "extract", "source": "firms_shapefile", "rows_count": len(df)},
    )

    if guardar and not df.empty:
        sufijo = "sample" if max_features else "full"
        ruta_salida = DIR_CRUDO / "firms" / f"firms_shapefile_{sufijo}.parquet"
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(ruta_salida, index=False)
        logger.info(f"Parquet raw shapefile guardado en: {ruta_salida}")

    return df


# =============================================================================
# FUNCIÓN 1: Descarga NRT (Near Real-Time) — datos de las últimas horas
# =============================================================================

def extraer_firms_nrt(
    sensor: str = "VIIRS_SNPP_NRT",   # Sensor a usar (por defecto VIIRS en Suomi NPP)
    dias: int = 2,                      # Cuántos días hacia atrás descargar (máximo 10)
    guardar: bool = True,              # Si True, guarda el CSV en data/raw/firms/
) -> pd.DataFrame:
    """
    Descarga focos de calor en tiempo real (NRT) para Uruguay.

    La API de FIRMS NRT procesa las imágenes satelitales en minutos y
    las publica con una latencia de 1 a 3 horas respecto al paso del satélite.

    Args:
        sensor:   Código del sensor a usar. Opciones NRT:
                  "VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT"
        dias:     Días hacia atrás a incluir (1 = solo hoy, 2 = hoy y ayer, máx 10)
        guardar:  Si True, guarda el resultado como CSV en data/raw/firms/

    Returns:
        DataFrame con los focos detectados. Columnas principales:
        latitude, longitude, acq_date, acq_time, confidence, frp, satellite

    Raises:
        ValueError:           Si FIRMS_MAP_KEY no está configurada en el .env
        requests.HTTPError:   Si la API responde con un código de error HTTP
    """
    # Verificamos que la MAP_KEY esté configurada antes de intentar la descarga
    if not FIRMS_MAP_KEY:
        raise ValueError(
            "FIRMS_MAP_KEY no configurada.\n"
            "1. Andá a: https://firms.modaps.eosdis.nasa.gov/api/area/\n"
            "2. Registrate y copiá tu MAP_KEY\n"
            "3. Agregala al archivo config/.env como: FIRMS_MAP_KEY=tu_key_aqui"
        )

    # Construimos la URL de la API para descarga NRT por bounding box (Sudamérica).
    # Usamos bbox en lugar de código de país porque cubrimos 6 países simultáneamente.
    # Formato: /area/csv/{key}/{sensor}/{bbox}/{días_hacia_atrás}
    url = f"{FIRMS_BASE_URL}/{FIRMS_MAP_KEY}/{sensor}/{FIRMS_BBOX}/{dias}"

    # Registramos en el log que vamos a iniciar la descarga
    logger.info(
        f"Descargando FIRMS NRT: sensor={sensor}, últimos {dias} días, bbox Sudamérica",
        extra={"etl_stage": "extract", "source": "firms_nrt"},  # Campos extra para el log JSON
    )

    # Hacemos la petición HTTP GET a la API de FIRMS
    # timeout=60 significa que si la API no responde en 60 segundos, da error
    respuesta = requests.get(url, timeout=60)

    # Si la API devolvió un error HTTP (404, 500, etc.), lanzamos una excepción
    respuesta.raise_for_status()

    # Convertimos el texto CSV de la respuesta en un DataFrame de pandas
    # io.StringIO convierte el string en un objeto que pandas puede leer como archivo
    df = pd.read_csv(io.StringIO(respuesta.text))

    # Registramos cuántos focos descargamos
    logger.info(
        f"FIRMS NRT: {len(df)} focos descargados",
        extra={"etl_stage": "extract", "source": "firms_nrt", "rows_count": len(df)},
    )

    # Si se pidió guardar Y el DataFrame no está vacío, lo guardamos como CSV
    if guardar and not df.empty:
        # Nombre del archivo incluye la fecha para no sobreescribir datos anteriores
        hoy = datetime.now().strftime("%Y%m%d")   # Formato: 20240115
        ruta_salida = DIR_CRUDO / "firms" / f"firms_nrt_{sensor}_{hoy}.csv"

        # Creamos la carpeta data/raw/firms/ si no existe
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)

        # Guardamos el DataFrame como CSV sin incluir el índice de fila de pandas
        df.to_csv(ruta_salida, index=False)
        logger.info(f"CSV guardado en: {ruta_salida}")

    return df   # Devolvemos el DataFrame para que el llamador pueda usarlo


# =============================================================================
# FUNCIÓN 2: Descarga de Archivo Histórico — rango de fechas libre
# =============================================================================

def extraer_firms_archivo(
    sensor: str = "VIIRS_SNPP_SP",     # Sensor de archivo (SP = Standard Processing)
    fecha_inicio: str = "2024-01-01",  # Fecha de inicio en formato YYYY-MM-DD
    fecha_fin: str = "2024-12-31",     # Fecha de fin en formato YYYY-MM-DD
    guardar: bool = True,              # Si True, guarda el CSV consolidado
    dias_por_chunk: int = FIRMS_DIAS_POR_CHUNK,  # Días por request (máximo 5)
) -> pd.DataFrame:
    """
    Descarga focos históricos de FIRMS para Uruguay en un rango de fechas libre.

    La API de FIRMS solo acepta hasta 5 días por request en modo archivo.
    Esta función divide automáticamente el rango en chunks de 5 días y los
    concatena al final para obtener el período completo solicitado.

    Args:
        sensor:         Código del sensor de archivo. Opciones:
                        "VIIRS_SNPP_SP" (Suomi NPP), "VIIRS_NOAA20_SP" (NOAA-20)
        fecha_inicio:   Fecha de inicio del período (formato YYYY-MM-DD)
        fecha_fin:      Fecha de fin del período (formato YYYY-MM-DD)
        guardar:        Si True, guarda un CSV consolidado con todos los chunks
        dias_por_chunk: Días por request HTTP. Máximo 5 según límite de la API.

    Returns:
        DataFrame consolidado con todos los focos del período solicitado.
        Columnas: latitude, longitude, acq_date, acq_time, confidence, frp, satellite, etc.
    """
    # Verificamos que la MAP_KEY esté configurada
    if not FIRMS_MAP_KEY:
        raise ValueError(
            "FIRMS_MAP_KEY no configurada.\n"
            "Creá tu key en: https://firms.modaps.eosdis.nasa.gov/api/area/"
        )

    # Nos aseguramos de no pedir más de 5 días por chunk (límite de la API)
    dias_por_chunk = min(dias_por_chunk, 5)

    # Convertimos los strings de fecha a objetos date para poder operar con ellos
    inicio = date.fromisoformat(fecha_inicio)   # "2024-01-01" -> date(2024, 1, 1)
    fin    = date.fromisoformat(fecha_fin)       # "2024-12-31" -> date(2024, 12, 31)

    # Calculamos el total de días en el período para mostrarlo en el log
    total_dias = (fin - inicio).days + 1

    # Registramos el inicio de la descarga con todos sus parámetros
    logger.info(
        f"Descargando FIRMS Archivo: sensor={sensor}, {fecha_inicio} -> {fecha_fin} "
        f"({total_dias} días en chunks de {dias_por_chunk})",
        extra={"etl_stage": "extract", "source": "firms_archivo"},
    )

    frames = []       # Lista donde acumulamos los DataFrames de cada chunk
    cursor = inicio   # Puntero de fecha que avanza de a chunks

    # Iteramos mientras el cursor no haya superado la fecha de fin
    while cursor <= fin:
        # Calculamos cuántos días quedan desde el cursor hasta el fin
        dias_restantes = (fin - cursor).days + 1

        # Pedimos el mínimo entre los días disponibles y el tamaño del chunk
        # Esto evita pedir más días de los que hay en el período
        dias_pedidos = min(dias_por_chunk, dias_restantes)

        # Fecha de inicio de este chunk en formato YYYY-MM-DD
        fecha_chunk = cursor.isoformat()

        # Construimos la URL del chunk
        # Formato correcto de la API: /area/csv/{key}/{sensor}/{bbox}/{días}/{fecha_inicio}
        url = (
            f"{FIRMS_BASE_URL}/{FIRMS_MAP_KEY}/{sensor}"
            f"/{FIRMS_BBOX}/{dias_pedidos}/{fecha_chunk}"
        )

        try:
            # Hacemos la petición HTTP para este chunk
            respuesta = requests.get(url, timeout=60)
            respuesta.raise_for_status()   # Error si el HTTP devuelve código de error

            # Limpiamos el texto de espacios al inicio/fin
            texto = respuesta.text.strip()

            # Verificamos que la respuesta sea datos reales y no un mensaje de error
            # La API de FIRMS devuelve texto de error que empieza con "Invalid"
            if texto and not texto.startswith("Invalid"):
                # Convertimos el CSV a DataFrame
                chunk_df = pd.read_csv(io.StringIO(texto))

                # Solo guardamos si tiene datos y tiene la columna de latitud (es válido)
                if not chunk_df.empty and "latitude" in chunk_df.columns:
                    frames.append(chunk_df)   # Agregamos a la lista de frames
                    logger.info(
                        f"  {fecha_chunk} +{dias_pedidos}d -> {len(chunk_df)} focos",
                        extra={"etl_stage": "extract", "source": "firms_archivo"},
                    )

        except Exception as error:
            # Si un chunk falla, registramos el error pero seguimos con el siguiente
            # Esto evita que un error puntual cancele toda la descarga
            logger.warning(
                f"  Error en chunk {fecha_chunk}: {error}",
                extra={"etl_stage": "extract", "source": "firms_archivo"},
            )

        # Avanzamos el cursor al primer día después de este chunk
        cursor += timedelta(days=dias_pedidos)

        # Pausa de 0.3 segundos entre requests para no saturar la API de NASA
        time.sleep(0.3)

    # Si no obtuvimos ningún dato en todo el período, retornamos DataFrame vacío
    if not frames:
        logger.info(
            "FIRMS Archivo: sin focos en el período solicitado",
            extra={"etl_stage": "extract", "source": "firms_archivo", "rows_count": 0},
        )
        return pd.DataFrame()

    # Concatenamos todos los chunks en un único DataFrame
    df = pd.concat(frames, ignore_index=True)

    # Eliminamos duplicados que puedan existir en los bordes entre chunks
    df = df.drop_duplicates()

    logger.info(
        f"FIRMS Archivo total: {len(df)} focos descargados",
        extra={"etl_stage": "extract", "source": "firms_archivo", "rows_count": len(df)},
    )

    # Guardamos el archivo consolidado si se pidió
    if guardar:
        ruta_salida = (
            DIR_CRUDO / "firms"
            / f"firms_archivo_{sensor}_{fecha_inicio}_{fecha_fin}.csv"
        )
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(ruta_salida, index=False)
        logger.info(f"CSV consolidado guardado en: {ruta_salida}")

    return df


# =============================================================================
# FUNCIÓN 3: Exploración de datos descargados (para análisis de calidad)
# =============================================================================

def explorar_muestra_firms(df: pd.DataFrame) -> dict:
    """
    Analiza la calidad de un DataFrame de focos FIRMS.

    Calcula métricas de completitud, unicidad y consistencia geográfica.
    Útil para el informe de Entrega de Código 1 (EC1) del proyecto.

    Args:
        df: DataFrame con datos crudos de FIRMS.

    Returns:
        Diccionario con métricas de calidad:
        - total_registros: cantidad de filas
        - completitud_pct: % de valores no nulos por campo crítico
        - duplicados_clave_natural: cantidad de filas duplicadas
        - rangos_numericos: min/max/media de columnas numéricas
        - focos_fuera_uruguay: focos con coordenadas fuera del territorio
        - distribucion_confianza: cantidad de focos por nivel de confianza
    """
    # Si el DataFrame está vacío, devolvemos un error descriptivo
    if df.empty:
        return {"error": "DataFrame vacío — no hay datos para explorar"}

    # Campos que deberían estar presentes en todo registro válido de FIRMS
    campos_criticos = [
        "latitude",    # Latitud del foco (coordenada geográfica)
        "longitude",   # Longitud del foco (coordenada geográfica)
        "acq_date",    # Fecha de adquisición de la imagen satelital
        "acq_time",    # Hora de adquisición (formato HHMM)
        "confidence",  # Nivel de confianza del detector (l=bajo, n=normal, h=alto)
        "frp",         # Fire Radiative Power en MW (intensidad del fuego)
        "brightness",  # Temperatura de brillo en Kelvin (calor detectado)
        "satellite",   # Identificador del satélite (N=NOAA, T=Terra, A=Aqua)
    ]

    # Calculamos completitud: % de valores no nulos para cada campo crítico
    # Solo para los campos que realmente existen en el DataFrame
    completitud = {
        campo: round((1 - df[campo].isna().mean()) * 100, 2)   # % de valores no nulos
        for campo in campos_criticos
        if campo in df.columns   # Solo procesamos campos que existen
    }

    # Calculamos duplicados usando la clave natural (combinación única de campos)
    # Dos focos son duplicados si tienen la misma posición, fecha, hora y satélite
    columnas_clave = ["latitude", "longitude", "acq_date", "acq_time", "satellite"]
    columnas_presentes = [c for c in columnas_clave if c in df.columns]   # Solo las que existen
    duplicados = df.duplicated(subset=columnas_presentes).sum()            # Contamos duplicados

    # Calculamos rangos estadísticos para columnas numéricas importantes
    rangos = {}
    for campo in ["latitude", "longitude", "frp", "brightness"]:
        if campo in df.columns:
            rangos[campo] = {
                "min":   float(df[campo].min()),                    # Valor mínimo
                "max":   float(df[campo].max()),                    # Valor máximo
                "media": round(float(df[campo].mean()), 2),        # Promedio
            }

    # Verificamos consistencia geográfica: focos dentro del bounding box de Sudamérica
    # SA_BBOX = "lon_min,lat_min,lon_max,lat_max" -> "-82.0,-56.0,-34.0,13.0"
    if "latitude" in df.columns and "longitude" in df.columns:
        focos_fuera = (
            (df["latitude"]  < -56.0) |   # Más al sur que el extremo sur de SA
            (df["latitude"]  >  13.0) |   # Más al norte que el extremo norte de SA
            (df["longitude"] < -82.0) |   # Más al oeste que el extremo oeste de SA
            (df["longitude"] > -34.0)     # Más al este que el extremo este de SA
        ).sum()
    else:
        focos_fuera = None   # No podemos calcular si no hay coordenadas

    # Armamos el diccionario resultado con todas las métricas calculadas
    resultado = {
        "total_registros":        len(df),              # Total de filas en el DataFrame
        "columnas":               list(df.columns),     # Lista de nombres de columnas
        "completitud_pct":        completitud,           # % completitud por campo
        "duplicados_clave_natural": int(duplicados),    # Cantidad de duplicados
        "unicidad_pct":           round((1 - duplicados / len(df)) * 100, 2) if len(df) > 0 else 0,
        "rangos_numericos":       rangos,               # Estadísticas por campo numérico
        "focos_fuera_sa_bbox":    int(focos_fuera) if focos_fuera is not None else None,
        "rango_fechas": {
            "min": str(df["acq_date"].min()) if "acq_date" in df.columns else None,
            "max": str(df["acq_date"].max()) if "acq_date" in df.columns else None,
        },
        "distribucion_satelite":  (
            df["satellite"].value_counts().to_dict()
            if "satellite" in df.columns else None
        ),
        "distribucion_confianza": (
            df["confidence"].value_counts().to_dict()
            if "confidence" in df.columns else None
        ),
    }

    # Calculamos el promedio de completitud para el log
    promedio_completitud = sum(completitud.values()) / len(completitud) if completitud else 0

    logger.info(
        f"Exploración FIRMS: {len(df)} registros, "
        f"completitud promedio: {promedio_completitud:.1f}%",
        extra={"etl_stage": "explore", "source": "firms"},
    )

    return resultado   # Devolvemos el diccionario con todas las métricas


# =============================================================================
# BLOQUE DE EJECUCIÓN DIRECTA
# Se ejecuta solo cuando corremos este archivo directamente:
#   python etl/extract/extract_firms.py
# No se ejecuta cuando el módulo es importado por otro script.
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SINIA-SA — Extractor NASA FIRMS (Sudamérica)")
    print("=" * 60)

    # Verificamos si la MAP_KEY está configurada antes de intentar descargar
    if not FIRMS_MAP_KEY:
        print(
            "\nMAP_KEY no configurada.\n"
            "1. Andá a: https://firms.modaps.eosdis.nasa.gov/api/area/\n"
            "2. Registrate y copiá tu MAP_KEY\n"
            "3. Agregá a config/.env: FIRMS_MAP_KEY=tu_key_aqui\n"
        )
    else:
        # Mostramos los primeros 8 caracteres de la key por seguridad
        print(f"\nMAP_KEY detectada: {FIRMS_MAP_KEY[:8]}...")
        print("Descargando focos NRT (últimos 2 días)...\n")

        # Ejecutamos la descarga NRT de prueba
        df = extraer_firms_nrt(dias=2)

        # Si obtuvimos datos, mostramos las métricas de calidad
        if not df.empty:
            metricas = explorar_muestra_firms(df)
            import json
            print(json.dumps(metricas, indent=2, ensure_ascii=False))
