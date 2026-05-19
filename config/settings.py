# =============================================================================
# SINIA-UY — Configuración Central del Proyecto
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

# Si el archivo .env existe en config/, lo cargamos desde ahí
if _ruta_env.exists():
    load_dotenv(_ruta_env)   # Carga las variables del .env al entorno del sistema
else:
    load_dotenv()  # Si no encuentra config/.env, busca un .env en el directorio actual


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
# ALCANCE GEOGRÁFICO — URUGUAY, BRASIL, ARGENTINA Y CHILE
# 4 países: Uruguay (sede del proyecto), Brasil y Argentina como países
# limítrofes con mayor influencia sobre incendios en territorio uruguayo, y
# Chile como país fuente de eventos volcánicos/aerosoles transfronterizos.
# Justificación: los focos del sur de Brasil (RS), del norte argentino y las
# erupciones chilenas como Puyehue-Cordón Caulle (2011) o Calbuco (2015)
# pueden afectar la calidad del aire, la visibilidad y el transporte aéreo
# en Uruguay.
# Por compatibilidad mantenemos el nombre PAISES_SA aunque el alcance operativo
# actual sea de cuatro países.
# Formato PAISES_SA: código ISO 3166-1 alpha-3 → metadatos del país.
# -----------------------------------------------------------------------------

PAISES_SA = {
    "BRA": {"nombre": "Brasil",    "codigo_iso2": "BR"},
    "ARG": {"nombre": "Argentina", "codigo_iso2": "AR"},
    "URY": {"nombre": "Uruguay",   "codigo_iso2": "UY"},
    "CHL": {"nombre": "Chile",     "codigo_iso2": "CL"},
}

# Bounding box regional para FIRMS y filtros espaciales.
# Se mantiene amplio por compatibilidad con la extracción; el filtro definitivo
# a BRA/ARG/URY/CHL ocurre en la transformación.
# Formato: "lon_min,lat_min,lon_max,lat_max"
SA_BBOX = "-76.0,-56.0,-34.0,6.0"

# Puntos de monitoreo meteorologico — alcance final de 36 puntos:
# - Uruguay: los 19 departamentos, representados por su capital/departamental.
# - Brasil: 5 ciudades estrategicas.
# - Argentina: 4 ciudades estrategicas.
# - Chile: 6 ciudades estrategicas + 2 puntos volcanicos relevantes.
# Formato: "Nombre": {"lat": float, "lon": float, "pais": str (ISO 3166-1 alpha-3)}
# Se usa para extraer datos de Open-Meteo y CAMS por coordenada.
PUNTOS_METEO_SA = {
    # ── Brasil (5 puntos — mayor superficie de riesgo de la región y fuente
    #    principal de humo transfronterizo hacia Uruguay) ──
    "Cuiabá":        {"lat": -15.60, "lon": -56.10, "pais": "BRA"},  # Capital de Mato Grosso, corazón del Cerrado
    "Porto_Alegre":  {"lat": -30.03, "lon": -51.23, "pais": "BRA"},  # Sur, frontera con AR/UY
    "Manaus":        {"lat":  -3.10, "lon": -60.02, "pais": "BRA"},  # Amazonia occidental
    "Campo_Grande":  {"lat": -20.47, "lon": -54.62, "pais": "BRA"},  # Mato Grosso do Sul, Pantanal
    "Brasília":      {"lat": -15.78, "lon": -47.93, "pais": "BRA"},  # Centro-oeste, Cerrado
    # ── Argentina (4 puntos — norte y centro, frontera con Uruguay) ──
    "Salta":         {"lat": -24.79, "lon": -65.41, "pais": "ARG"},  # NOA, yungas y chaco salteño
    "Posadas":       {"lat": -27.37, "lon": -55.90, "pais": "ARG"},  # Misiones, selva misionera limítrofe
    "Buenos_Aires":  {"lat": -34.61, "lon": -58.37, "pais": "ARG"},  # AMBA, frontera oeste con UY
    "Mendoza":       {"lat": -32.89, "lon": -68.85, "pais": "ARG"},  # Cuyo, incendios de interfaz
    # ── Chile (8 puntos — ciudades estrategicas y volcanes con impacto regional) ──
    "Santiago":              {"lat": -33.45, "lon": -70.66, "pais": "CHL"},  # Referencia nacional y calidad de aire urbana
    "Temuco":                {"lat": -38.74, "lon": -72.59, "pais": "CHL"},  # Zona forestal critica
    "Valdivia":              {"lat": -39.82, "lon": -73.24, "pais": "CHL"},  # Sur de Chile, corredor volcanico
    "Osorno":                {"lat": -40.57, "lon": -73.13, "pais": "CHL"},  # Area afectada por Puyehue
    "Puerto_Montt":          {"lat": -41.47, "lon": -72.94, "pais": "CHL"},  # Area de influencia Calbuco
    "Coyhaique":             {"lat": -45.57, "lon": -72.07, "pais": "CHL"},  # Patagonia y calidad de aire
    "Puyehue_Cordon_Caulle": {"lat": -40.59, "lon": -72.12, "pais": "CHL"},  # Erupcion 2011, cenizas hacia Uruguay
    "Calbuco":               {"lat": -41.33, "lon": -72.61, "pais": "CHL"},  # Erupcion 2015, cenizas reportadas sobre Uruguay
    # ── Uruguay (19 departamentos — cobertura nacional completa) ──
    "Artigas":                  {"lat": -30.40, "lon": -56.47, "pais": "URY"},
    "Canelones":                {"lat": -34.52, "lon": -56.28, "pais": "URY"},
    "Melo":                     {"lat": -32.37, "lon": -54.18, "pais": "URY"},  # Cerro Largo
    "Colonia_del_Sacramento":   {"lat": -34.46, "lon": -57.84, "pais": "URY"},
    "Durazno":                  {"lat": -33.38, "lon": -56.52, "pais": "URY"},
    "Trinidad":                 {"lat": -33.52, "lon": -56.90, "pais": "URY"},  # Flores
    "Florida":                  {"lat": -34.10, "lon": -56.21, "pais": "URY"},
    "Minas":                    {"lat": -34.38, "lon": -55.24, "pais": "URY"},  # Lavalleja
    "Maldonado":                {"lat": -34.91, "lon": -54.96, "pais": "URY"},
    "Montevideo":               {"lat": -34.90, "lon": -56.19, "pais": "URY"},
    "Paysandu":                 {"lat": -32.32, "lon": -58.08, "pais": "URY"},
    "Fray_Bentos":              {"lat": -33.13, "lon": -58.30, "pais": "URY"},  # Rio Negro
    "Rivera":                   {"lat": -30.91, "lon": -55.55, "pais": "URY"},
    "Rocha":                    {"lat": -34.48, "lon": -54.33, "pais": "URY"},
    "Salto":                    {"lat": -31.38, "lon": -57.97, "pais": "URY"},
    "San_Jose_de_Mayo":         {"lat": -34.34, "lon": -56.71, "pais": "URY"},
    "Mercedes":                 {"lat": -33.25, "lon": -58.03, "pais": "URY"},  # Soriano
    "Tacuarembo":               {"lat": -31.73, "lon": -55.98, "pais": "URY"},
    "Treinta_y_Tres":           {"lat": -33.23, "lon": -54.38, "pais": "URY"},
}

# Alias de compatibilidad: código existente que itere PUNTOS_METEO como
# {nombre: (lat, lon)} sigue funcionando sin modificación.
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
    "host":     os.getenv("PG_HOST",     "localhost"),   # Servidor donde corre PostgreSQL
    "port":     int(os.getenv("PG_PORT", "5432")),       # Puerto de PostgreSQL (5432 es el estándar)
    "database": os.getenv("PG_DATABASE", "sinia_uy"),    # Nombre de la base de datos
    "user":     os.getenv("PG_USER",     "sinia_etl"),   # Usuario con permisos de lectura/escritura
    "password": os.getenv("PG_PASSWORD", ""),            # Contraseña (viene del .env, nunca hardcodeada)
}


# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE MONGODB
# Base de datos NoSQL para almacenar documentos JSON flexibles:
# logs de ejecución, métricas de calidad, alertas históricas.
# -----------------------------------------------------------------------------

# Diccionario con todos los parámetros de conexión a MongoDB
MONGO_CONFIG = {
    "host":     os.getenv("MONGO_HOST",     "localhost"),  # Servidor donde corre MongoDB
    "port":     int(os.getenv("MONGO_PORT", "27017")),     # Puerto de MongoDB (27017 es el estándar)
    "database": os.getenv("MONGO_DATABASE", "sinia_uy"),   # Nombre de la base de datos
    "user":     os.getenv("MONGO_USER",     "sinia_etl"),  # Usuario con permisos
    "password": os.getenv("MONGO_PASSWORD", ""),           # Contraseña (viene del .env)
}


# -----------------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# -----------------------------------------------------------------------------

# Zona horaria del proyecto — UTC es neutro para un sistema regional de cuatro países.
# Uruguay, Brasil, Argentina y Chile operan con husos cercanos, pero se mantiene UTC
# como referencia técnica común.
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
