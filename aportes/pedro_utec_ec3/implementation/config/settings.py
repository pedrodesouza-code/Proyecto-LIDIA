1# =============================================================================
# SINIA-SA — Configuración Central del Proyecto (Sudamérica)
# =============================================================================
# Este archivo es el corazón de la configuración. Define TODAS las constantes,
# URLs, credenciales y parámetros que usan el resto de los módulos.
# Se carga una sola vez al iniciar cualquier script del proyecto.
# =============================================================================

import os          # Para leer variables de entorno del sistema operativo
from pathlib import Path   # Para manejar rutas de archivos de forma multiplataforma
from dotenv import load_dotenv  # Para cargar el archivo .env con las credenciales

# -----------------------------------------------------------------------------
# CARGA DEL ARCHIVO DE ENTORNO (.env)
# El archivo .env guarda las claves secretas (API keys, contraseñas).
# Nunca se sube a GitHub porque está en el .gitignore.
# -----------------------------------------------------------------------------

# Calculamos la ruta raíz del proyecto subiendo dos niveles desde este archivo
# __file__ es la ruta de settings.py → .parent es config/ → .parent.parent es SONIA-UY/
_raiz_proyecto = Path(__file__).resolve().parent.parent

# Construimos la ruta esperada del archivo .env dentro de la carpeta config/
_ruta_env = _raiz_proyecto / "config" / ".env"
_ruta_env_utec = _raiz_proyecto / "config" / "utec.env"

# Si el archivo .env existe en config/, lo cargamos desde ahí
if _ruta_env.exists():
    load_dotenv(_ruta_env, override=True)   # Carga las variables del .env al entorno del sistema
elif _ruta_env_utec.exists():
    load_dotenv(_ruta_env_utec, override=True)
else:
    load_dotenv(override=True)  # Si no encuentra config/.env, busca un .env en el directorio actual


# -----------------------------------------------------------------------------
# RUTAS DEL PROYECTO
# Definimos todas las carpetas importantes usando Path para que funcione
# igual en Windows, Linux y Mac sin preocuparnos por las barras (\ vs /).
# -----------------------------------------------------------------------------

RAIZ_PROYECTO = _raiz_proyecto                        # Carpeta raíz: SONIA-UY/
DIR_DATOS     = _raiz_proyecto / "data"               # Carpeta de datos: data/
DIR_CRUDO     = DIR_DATOS / "raw"                     # Datos sin procesar: data/raw/
DIR_PROCESADO = DIR_DATOS / "processed"               # Datos limpios: data/processed/
DIR_STAGING   = DIR_DATOS / "staging"                 # Datos intermedios: data/staging/
DIR_LOGS      = _raiz_proyecto / "logs"               # Archivos de log: logs/

# Carpeta externa con datasets grandes. No se versiona en Git.
# En la máquina de trabajo actual contiene el shapefile FIRMS y fuentes auxiliares.
DIR_DATOS_EXTERNOS = Path(
    os.getenv("DIR_DATOS_EXTERNOS", str(_raiz_proyecto.parent))
).expanduser()

# Creamos las carpetas automáticamente si todavía no existen
# parents=True crea todas las carpetas intermedias necesarias
# exist_ok=True no da error si la carpeta ya existe
for carpeta in [DIR_CRUDO, DIR_PROCESADO, DIR_STAGING, DIR_LOGS]:
    carpeta.mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE NASA FIRMS (Fire Information for Resource Management System)
# API gratuita de NASA que provee focos de calor detectados por satélite.
# Requiere una MAP_KEY gratuita: https://firms.modaps.eosdis.nasa.gov/api/area/
# -----------------------------------------------------------------------------

# Clave de acceso a la API de FIRMS (se lee del .env, vacía por defecto)
FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "")

# URL base de la API de FIRMS para descargar datos en formato CSV por área
FIRMS_BASE_URL = os.getenv(
    "FIRMS_BASE_URL",
    "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
)

# Shapefile histórico FIRMS descargado desde NASA. Es la fuente local principal
# cuando se trabaja en el servidor/PC con los datasets pesados ya descargados.
FIRMS_SHAPEFILE_PATH = Path(
    os.getenv(
        "FIRMS_SHAPEFILE_PATH",
        str(DIR_DATOS_EXTERNOS / "DL_FIRE_M-C61_740435" / "fire_archive_M-C61_740435.shp"),
    )
).expanduser()

# Diccionario de sensores disponibles en FIRMS:
# NRT = Near Real-Time (datos de las últimas horas, procesamiento rápido)
# SP  = Standard Processing (datos históricos, mayor precisión)
FIRMS_SENSORES = {
    "VIIRS_SNPP_NRT":  "VIIRS Suomi NPP (Tiempo Real)",         # Satélite Suomi NPP - datos del día
    "VIIRS_NOAA20_NRT": "VIIRS NOAA-20 (Tiempo Real)",          # Satélite NOAA-20 - datos del día
    "MODIS_NRT":        "MODIS Terra+Aqua (Tiempo Real)",        # Sensor MODIS - datos del día
    "VIIRS_SNPP_SP":    "VIIRS Suomi NPP (Archivo Histórico)",   # Suomi NPP - datos históricos
    "VIIRS_NOAA20_SP":  "VIIRS NOAA-20 (Archivo Histórico)",    # NOAA-20 - datos históricos
}


# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE OPEN-METEO
# API meteorológica gratuita, sin necesidad de registro ni API key.
# Provee datos históricos y pronósticos para cualquier punto geográfico.
# -----------------------------------------------------------------------------

# URL base para el pronóstico meteorológico (datos actuales y futuros hasta 16 días)
OPENMETEO_BASE_URL = os.getenv(
    "OPENMETEO_BASE_URL",
    "https://api.open-meteo.com/v1"
)

# URL para datos meteorológicos históricos de archivo (desde 1940 hasta ayer)
OPENMETEO_ARCHIVE_URL = os.getenv(
    "OPENMETEO_ARCHIVE_URL",
    "https://archive-api.open-meteo.com/v1/archive"
)

# -----------------------------------------------------------------------------
# ALCANCE GEOGRÁFICO — SUDAMÉRICA
# 6 países núcleo con mayor actividad de incendios forestales (2018-2025).
# Formato PAISES_SA: código ISO 3166-1 alpha-3 → metadatos del país.
# -----------------------------------------------------------------------------

PAISES_SA = {
    "BRA": {"nombre": "Brasil",    "codigo_iso2": "BR"},
    "BOL": {"nombre": "Bolivia",   "codigo_iso2": "BO"},
    "PRY": {"nombre": "Paraguay",  "codigo_iso2": "PY"},
    "ARG": {"nombre": "Argentina", "codigo_iso2": "AR"},
    "CHL": {"nombre": "Chile",     "codigo_iso2": "CL"},
    "PER": {"nombre": "Perú",      "codigo_iso2": "PE"},
}

# Bounding box de Sudamérica para FIRMS y filtros espaciales
# Formato: "lon_min,lat_min,lon_max,lat_max"
SA_BBOX = "-82.0,-56.0,-34.0,13.0"

# Puntos de monitoreo meteorológico — 18 ciudades en 6 países núcleo.
# Formato: "Nombre": {"lat": float, "lon": float, "pais": str (ISO 3166-1 alpha-3)}
# Se usa para extraer datos de Open-Meteo y CAMS por coordenada.
PUNTOS_METEO_SA = {
    # ── Brasil (5 puntos — mayor superficie de riesgo del continente) ──
    "Cuiabá":        {"lat": -15.60, "lon": -56.10, "pais": "BRA"},  # Capital de Mato Grosso, corazón del Cerrado
    "Porto_Alegre":  {"lat": -30.03, "lon": -51.23, "pais": "BRA"},  # Sur, frontera con AR/UY
    "Manaus":        {"lat":  -3.10, "lon": -60.02, "pais": "BRA"},  # Amazonia occidental
    "Campo_Grande":  {"lat": -20.47, "lon": -54.62, "pais": "BRA"},  # Mato Grosso do Sul, Pantanal
    "Brasília":      {"lat": -15.78, "lon": -47.93, "pais": "BRA"},  # Centro-oeste, Cerrado
    # ── Bolivia (3 puntos — Chiquitanía y amazonia boliviana) ──
    "Santa_Cruz":    {"lat": -17.80, "lon": -63.17, "pais": "BOL"},  # Chiquitanía — zona crítica de incendios
    "Trinidad":      {"lat": -14.83, "lon": -64.90, "pais": "BOL"},  # Beni — amazonia boliviana
    "La_Paz":        {"lat": -16.50, "lon": -68.15, "pais": "BOL"},  # Capital administrativa
    # ── Paraguay (2 puntos — Chaco y bosque atlántico) ──
    "Asunción":      {"lat": -25.29, "lon": -57.64, "pais": "PRY"},  # Capital, corredor de incendios
    "Concepción":    {"lat": -23.41, "lon": -57.43, "pais": "PRY"},  # Norte, Chaco paraguayo
    # ── Argentina (4 puntos — norte y centro) ──
    "Salta":         {"lat": -24.79, "lon": -65.41, "pais": "ARG"},  # NOA, yungas y chaco salteño
    "Posadas":       {"lat": -27.37, "lon": -55.90, "pais": "ARG"},  # Misiones, selva misionera
    "Buenos_Aires":  {"lat": -34.61, "lon": -58.37, "pais": "ARG"},  # Referencia sur
    "Mendoza":       {"lat": -32.89, "lon": -68.85, "pais": "ARG"},  # Cuyo, incendios de interfaz
    # ── Chile (2 puntos — zona de interfaz urbano-forestal) ──
    "Santiago":      {"lat": -33.46, "lon": -70.65, "pais": "CHL"},  # Región Metropolitana
    "Temuco":        {"lat": -38.74, "lon": -72.59, "pais": "CHL"},  # La Araucanía — zona forestal crítica
    # ── Perú (2 puntos — amazonia y altiplano) ──
    "Lima":          {"lat": -12.06, "lon": -77.04, "pais": "PER"},  # Capital costera
    "Cusco":         {"lat": -13.53, "lon": -71.97, "pais": "PER"},  # Sur andino, colindante con amazonia
}

# Alias de compatibilidad: código existente que itere PUNTOS_METEO como {nombre: (lat, lon)}
# sigue funcionando sin modificación durante la migración incremental.
PUNTOS_METEO = {
    nombre: (info["lat"], info["lon"])
    for nombre, info in PUNTOS_METEO_SA.items()
}


# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE CAMS (Copernicus Atmosphere Monitoring Service)
# Servicio europeo de monitoreo de calidad del aire.
# Lo usamos vía Open-Meteo Air Quality API (proxy gratuito, sin clave).
# Provee PM10, PM2.5, aerosoles y otros contaminantes.
# -----------------------------------------------------------------------------

# URL de la API oficial de CAMS (requiere cuenta, usada como fallback)
CAMS_API_URL = os.getenv(
    "CAMS_API_URL",
    "https://ads.atmosphere.copernicus.eu/api/v2"
)

# Clave de la API oficial de CAMS (opcional, solo si se usa la API directa)
CAMS_API_KEY = os.getenv("CAMS_API_KEY", "")


# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE POSTGRESQL
# Base de datos relacional para almacenar datos estructurados:
# focos de calor, meteorología diaria, índices de riesgo.
# -----------------------------------------------------------------------------

# Diccionario con todos los parámetros de conexión a PostgreSQL
# os.getenv("VARIABLE", "valor_por_defecto") lee la variable del .env
PG_CONFIG = {
    "host":     os.getenv("POSTGRES_HOST", os.getenv("PG_HOST", "localhost")),
    "port":     int(os.getenv("POSTGRES_PORT", os.getenv("PG_PORT", "5432"))),
    "database": os.getenv("POSTGRES_DB",   os.getenv("PG_DATABASE", "sinia_uy")),
    "user":     os.getenv("POSTGRES_USER", os.getenv("PG_USER", "sinia_etl")),
    "password": os.getenv("POSTGRES_PASSWORD", os.getenv("PG_PASSWORD", "")),
}


# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE MONGODB
# Base de datos NoSQL para almacenar documentos JSON flexibles:
# logs de ejecución, métricas de calidad, alertas históricas.
# -----------------------------------------------------------------------------

# Diccionario con todos los parámetros de conexión a MongoDB
MONGO_CONFIG = {
    "host":     os.getenv("MONGO_HOST", "localhost"),
    "port":     int(os.getenv("MONGO_PORT", "27017")),
    "database": os.getenv("MONGO_DB", os.getenv("MONGO_DATABASE", "sinia_uy")),
    "user":     os.getenv("MONGO_USER", "sinia_etl"),
    "password": os.getenv("MONGO_PASSWORD", ""),
}
MONGO_CONFIG["auth_source"] = os.getenv("MONGO_AUTH_SOURCE", MONGO_CONFIG["database"])


# -----------------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# -----------------------------------------------------------------------------

# Zona horaria del proyecto — UTC es neutro para un sistema multi-país en Sudamérica.
# Los 6 países núcleo cubren UTC-3 a UTC-5, así que usamos UTC como referencia.
TIMEZONE  = os.getenv("TIMEZONE",  "UTC")

# Nivel de detalle de los logs: DEBUG muestra todo, INFO solo lo importante,
# WARNING solo advertencias, ERROR solo errores críticos
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


# -----------------------------------------------------------------------------
# PESOS DEL ÍNDICE DE RIESGO DE INCENDIO
# El índice se calcula como una suma ponderada de 4 factores.
# Cada peso indica qué tan importante es ese factor (deben sumar 1.0).
# Basado en metodología del INIA (Instituto Nacional de Investigación Agropecuaria).
# -----------------------------------------------------------------------------

PESOS_RIESGO = {
    "temperatura": 0.25,   # 25% — temperaturas altas resecan la vegetación
    "humedad":     0.30,   # 30% — la baja humedad es el factor más crítico
    "viento":      0.20,   # 20% — el viento propaga y aviva los incendios
    "sequia":      0.25,   # 25% — la sequía acumulada determina el estado del combustible
}

# -----------------------------------------------------------------------------
# FUENTES DE DATOS ADICIONALES — CHIRPS y MODIS
# CHIRPS: precipitación mensual en punto desde 1981 (UCSB, acceso público).
# AppEEARS: portal NASA para extraer series temporales de MODIS sin procesar HDF.
# -----------------------------------------------------------------------------

# CHIRPS — Climate Hazards Group InfraRed Precipitation with Stations
# Endpoint de extracción por punto: devuelve CSV con precipitación mensual.
CHIRPS_BASE_URL = os.getenv(
    "CHIRPS_BASE_URL",
    "https://climateserv.servirglobal.net/api",
)

# NASA AppEEARS — Application for Extracting and Exploring Analysis Ready Samples
# Permite solicitar series temporales de MODIS MCD12Q1 (Land Cover) sin HDF.
APPEEARS_BASE_URL = os.getenv(
    "APPEEARS_BASE_URL",
    "https://appeears.earthdatacloud.nasa.gov/api",
)
APPEEARS_USER     = os.getenv("APPEEARS_USER",     "")
APPEEARS_PASSWORD = os.getenv("APPEEARS_PASSWORD", "")
