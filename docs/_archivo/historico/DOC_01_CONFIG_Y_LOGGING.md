# DOCUMENTACIÓN DETALLADA — MÓDULO 1: CONFIGURACIÓN Y LOGGING
## Proyecto SONIA-UY / SINIA-SA — Sistema de Monitoreo de Incendios

---

## ARCHIVO: `config/settings.py`

### ¿Qué hace este archivo?
Es el **corazón de la configuración del proyecto**. Se carga una sola vez al iniciar cualquier script. Define todas las constantes, rutas, credenciales y parámetros que usa el resto del sistema. Ningún otro módulo tiene valores hardcodeados: todo lo lee desde aquí.

---

### IMPORTACIONES

| Módulo | Para qué se usa |
|--------|-----------------|
| `os` | Leer variables de entorno del sistema operativo con `os.getenv()` |
| `pathlib.Path` | Manejar rutas de archivos de forma multiplataforma (funciona igual en Windows, Linux y Mac) |
| `dotenv.load_dotenv` | Cargar el archivo `.env` con las credenciales secretas |

---

### CARGA DEL ARCHIVO `.env`

```python
_raiz_proyecto = Path(__file__).resolve().parent.parent
_ruta_env = _raiz_proyecto / "config" / ".env"

if _ruta_env.exists():
    load_dotenv(_ruta_env)
else:
    load_dotenv()
```

**Variables privadas (con `_` al inicio — no se exportan):**

| Variable | Tipo | Valor | Descripción |
|----------|------|-------|-------------|
| `_raiz_proyecto` | `Path` | Ruta a `SONIA-UY/` | Sube dos niveles desde `settings.py`: `.parent` = `config/`, `.parent.parent` = `SONIA-UY/` |
| `_ruta_env` | `Path` | Ruta a `config/.env` | Concatenación de ruta raíz + nombre del archivo |

**Lógica:** Si `config/.env` existe, lo carga desde ahí. Si no, `load_dotenv()` busca un `.env` en el directorio de trabajo actual. Esto permite flexibilidad en diferentes entornos.

---

### VARIABLES DE RUTAS DEL PROYECTO

```python
RAIZ_PROYECTO = _raiz_proyecto
DIR_DATOS     = _raiz_proyecto / "data"
DIR_CRUDO     = DIR_DATOS / "raw"
DIR_PROCESADO = DIR_DATOS / "processed"
DIR_STAGING   = DIR_DATOS / "staging"
DIR_LOGS      = _raiz_proyecto / "logs"
```

| Variable | Tipo | Ruta relativa | Propósito |
|----------|------|---------------|-----------|
| `RAIZ_PROYECTO` | `Path` | `SONIA-UY/` | Carpeta raíz del proyecto |
| `DIR_DATOS` | `Path` | `SONIA-UY/data/` | Carpeta principal de datos |
| `DIR_CRUDO` | `Path` | `SONIA-UY/data/raw/` | Datos sin procesar descargados de las APIs |
| `DIR_PROCESADO` | `Path` | `SONIA-UY/data/processed/` | Datos limpios y transformados en formato Parquet |
| `DIR_STAGING` | `Path` | `SONIA-UY/data/staging/` | Datos intermedios entre pasos del pipeline |
| `DIR_LOGS` | `Path` | `SONIA-UY/logs/` | Archivos de log JSON diarios |

**Autocreación de carpetas:**
```python
for carpeta in [DIR_CRUDO, DIR_PROCESADO, DIR_STAGING, DIR_LOGS]:
    carpeta.mkdir(parents=True, exist_ok=True)
```
- `parents=True`: crea todas las carpetas intermedias necesarias
- `exist_ok=True`: no da error si la carpeta ya existe

---

### CONFIGURACIÓN DE NASA FIRMS

```python
FIRMS_MAP_KEY  = os.getenv("FIRMS_MAP_KEY", "")
FIRMS_BASE_URL = os.getenv("FIRMS_BASE_URL", "https://firms.modaps.eosdis.nasa.gov/api/area/csv")
```

| Variable | Tipo | Fuente | Descripción |
|----------|------|--------|-------------|
| `FIRMS_MAP_KEY` | `str` | `.env` | Clave de acceso a la API de NASA FIRMS. Vacía por defecto — el sistema fallará con error descriptivo si no está configurada |
| `FIRMS_BASE_URL` | `str` | `.env` o hardcoded | URL base de la API. Descarga datos en formato CSV por bounding box |

```python
FIRMS_SENSORES = {
    "VIIRS_SNPP_NRT":   "VIIRS Suomi NPP (Tiempo Real)",
    "VIIRS_NOAA20_NRT": "VIIRS NOAA-20 (Tiempo Real)",
    "MODIS_NRT":        "MODIS Terra+Aqua (Tiempo Real)",
    "VIIRS_SNPP_SP":    "VIIRS Suomi NPP (Archivo Histórico)",
    "VIIRS_NOAA20_SP":  "VIIRS NOAA-20 (Archivo Histórico)",
}
```

**Diccionario `FIRMS_SENSORES`:** Mapea código de sensor → descripción legible.
- Sufijo `NRT` = Near Real-Time (datos de las últimas horas, procesamiento rápido, latencia 1-3h)
- Sufijo `SP` = Standard Processing (datos históricos, mayor precisión geométrica y radiométrica)

---

### CONFIGURACIÓN DE OPEN-METEO

```python
OPENMETEO_BASE_URL    = os.getenv("OPENMETEO_BASE_URL",    "https://api.open-meteo.com/v1")
OPENMETEO_ARCHIVE_URL = os.getenv("OPENMETEO_ARCHIVE_URL", "https://archive-api.open-meteo.com/v1/archive")
```

| Variable | Uso |
|----------|-----|
| `OPENMETEO_BASE_URL` | Pronóstico meteorológico (datos actuales y futuros hasta 16 días) |
| `OPENMETEO_ARCHIVE_URL` | Datos históricos de archivo (desde 1940 hasta ayer) |

**Ventaja:** Open-Meteo es gratuito y no requiere API key. Ideal para proyectos académicos.

---

### CONFIGURACIÓN GEOGRÁFICA

```python
PAISES_SA = {
    "BRA": {"nombre": "Brasil",    "codigo_iso2": "BR"},
    "BOL": {"nombre": "Bolivia",   "codigo_iso2": "BO"},
    "PRY": {"nombre": "Paraguay",  "codigo_iso2": "PY"},
    "ARG": {"nombre": "Argentina", "codigo_iso2": "AR"},
    "CHL": {"nombre": "Chile",     "codigo_iso2": "CL"},
    "PER": {"nombre": "Perú",      "codigo_iso2": "PE"},
}

SA_BBOX = "-82.0,-56.0,-34.0,13.0"
```

| Variable | Tipo | Descripción |
|----------|------|-------------|
| `PAISES_SA` | `dict[str, dict]` | 6 países núcleo con mayor actividad de incendios. Clave = código ISO 3166-1 alpha-3 |
| `SA_BBOX` | `str` | Bounding box de Sudamérica en formato `"lon_min,lat_min,lon_max,lat_max"`. Usado en filtros geográficos y en las URLs de la API de FIRMS |

---

### PUNTOS DE MONITOREO METEOROLÓGICO

```python
PUNTOS_METEO_SA = {
    "Cuiabá":       {"lat": -15.60, "lon": -56.10, "pais": "BRA"},
    "Porto_Alegre": {"lat": -30.03, "lon": -51.23, "pais": "BRA"},
    "Manaus":       {"lat":  -3.10, "lon": -60.02, "pais": "BRA"},
    "Campo_Grande": {"lat": -20.47, "lon": -54.62, "pais": "BRA"},
    "Brasília":     {"lat": -15.78, "lon": -47.93, "pais": "BRA"},
    "Santa_Cruz":   {"lat": -17.80, "lon": -63.17, "pais": "BOL"},
    "Trinidad":     {"lat": -14.83, "lon": -64.90, "pais": "BOL"},
    "La_Paz":       {"lat": -16.50, "lon": -68.15, "pais": "BOL"},
    "Asunción":     {"lat": -25.29, "lon": -57.64, "pais": "PRY"},
    "Concepción":   {"lat": -23.41, "lon": -57.43, "pais": "PRY"},
    "Salta":        {"lat": -24.79, "lon": -65.41, "pais": "ARG"},
    "Posadas":      {"lat": -27.37, "lon": -55.90, "pais": "ARG"},
    "Buenos_Aires": {"lat": -34.61, "lon": -58.37, "pais": "ARG"},
    "Mendoza":      {"lat": -32.89, "lon": -68.85, "pais": "ARG"},
    "Santiago":     {"lat": -33.46, "lon": -70.65, "pais": "CHL"},
    "Temuco":       {"lat": -38.74, "lon": -72.59, "pais": "CHL"},
    "Lima":         {"lat": -12.06, "lon": -77.04, "pais": "PER"},
    "Cusco":        {"lat": -13.53, "lon": -71.97, "pais": "PER"},
}
```

**18 ciudades** seleccionadas estratégicamente por:
- Proximidad a zonas de alta actividad de incendios históricamente
- Representatividad geográfica de cada país
- Cobertura de biomas importantes (Amazonia, Cerrado, Chaco, Patagonia, etc.)

Cada entrada tiene: `lat` (latitud decimal), `lon` (longitud decimal), `pais` (código ISO alpha-3)

```python
PUNTOS_METEO = {
    nombre: (info["lat"], info["lon"])
    for nombre, info in PUNTOS_METEO_SA.items()
}
```

**`PUNTOS_METEO`:** Alias de compatibilidad hacia atrás. Transforma `PUNTOS_METEO_SA` en un diccionario de formato `{nombre: (lat, lon)}` para código antiguo que espera esa estructura.

---

### CONFIGURACIÓN DE CAMS

```python
CAMS_API_URL = os.getenv("CAMS_API_URL", "https://ads.atmosphere.copernicus.eu/api/v2")
CAMS_API_KEY = os.getenv("CAMS_API_KEY", "")
```

| Variable | Descripción |
|----------|-------------|
| `CAMS_API_URL` | URL de la API oficial de CAMS (Copernicus). Requiere cuenta. Usado como fallback |
| `CAMS_API_KEY` | Clave de la API oficial. Vacía por defecto — el proyecto usa Open-Meteo Air Quality como proxy gratuito |

---

### CONFIGURACIÓN DE POSTGRESQL

```python
PG_CONFIG = {
    "host":     os.getenv("PG_HOST",     "localhost"),
    "port":     int(os.getenv("PG_PORT", "5432")),
    "database": os.getenv("PG_DATABASE", "sinia_uy"),
    "user":     os.getenv("PG_USER",     "sinia_etl"),
    "password": os.getenv("PG_PASSWORD", ""),
}
```

**Todas las claves del diccionario `PG_CONFIG`:**

| Clave | Tipo | Por defecto | Descripción |
|-------|------|-------------|-------------|
| `host` | `str` | `"localhost"` | Servidor donde corre PostgreSQL |
| `port` | `int` | `5432` | Puerto estándar de PostgreSQL |
| `database` | `str` | `"sinia_uy"` | Nombre de la base de datos del proyecto |
| `user` | `str` | `"sinia_etl"` | Usuario con permisos de lectura/escritura en las tablas del proyecto |
| `password` | `str` | `""` | Contraseña. Nunca hardcodeada, siempre desde `.env` |

---

### CONFIGURACIÓN DE MONGODB

```python
MONGO_CONFIG = {
    "host":     os.getenv("MONGO_HOST",     "localhost"),
    "port":     int(os.getenv("MONGO_PORT", "27017")),
    "database": os.getenv("MONGO_DATABASE", "sinia_uy"),
    "user":     os.getenv("MONGO_USER",     "sinia_etl"),
    "password": os.getenv("MONGO_PASSWORD", ""),
}
```

**Todas las claves del diccionario `MONGO_CONFIG`:**

| Clave | Tipo | Por defecto | Descripción |
|-------|------|-------------|-------------|
| `host` | `str` | `"localhost"` | Servidor donde corre MongoDB |
| `port` | `int` | `27017` | Puerto estándar de MongoDB |
| `database` | `str` | `"sinia_uy"` | Nombre de la base de datos MongoDB |
| `user` | `str` | `"sinia_etl"` | Usuario MongoDB con permisos |
| `password` | `str` | `""` | Contraseña desde `.env` |

---

### CONFIGURACIÓN GENERAL

```python
TIMEZONE  = os.getenv("TIMEZONE",  "UTC")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
```

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `TIMEZONE` | `"UTC"` | Zona horaria del sistema. UTC es neutro para un sistema multi-país que cubre UTC-3 a UTC-5 |
| `LOG_LEVEL` | `"INFO"` | Nivel de detalle de los logs. Opciones: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

### PESOS DEL ÍNDICE DE RIESGO

```python
PESOS_RIESGO = {
    "temperatura": 0.25,
    "humedad":     0.30,
    "viento":      0.20,
    "sequia":      0.25,
}
```

**Cada peso y su justificación científica:**

| Factor | Peso | Por qué |
|--------|------|---------|
| `temperatura` | 0.25 (25%) | Las temperaturas altas resecan la vegetación y facilitan la ignición |
| `humedad` | 0.30 (30%) | La baja humedad relativa es el factor más crítico para la propagación del fuego |
| `viento` | 0.20 (20%) | El viento propaga el fuego y lo aviva, aumentando su intensidad |
| `sequia` | 0.25 (25%) | La sequía acumulada (medida por ET0) determina el estado del combustible vegetal |

**Los pesos deben sumar exactamente 1.0.** Basados en la metodología del INIA (Instituto Nacional de Investigación Agropecuaria) de Uruguay.

---

### FUENTES ADICIONALES

```python
CHIRPS_BASE_URL   = os.getenv("CHIRPS_BASE_URL",   "https://climateserv.servirglobal.net/api")
APPEEARS_BASE_URL = os.getenv("APPEEARS_BASE_URL",  "https://appeears.earthdatacloud.nasa.gov/api")
APPEEARS_USER     = os.getenv("APPEEARS_USER",     "")
APPEEARS_PASSWORD = os.getenv("APPEEARS_PASSWORD", "")
```

| Variable | Descripción |
|----------|-------------|
| `CHIRPS_BASE_URL` | URL de ClimateSERV para descargar datos CHIRPS de precipitación mensual |
| `APPEEARS_BASE_URL` | URL de NASA AppEEARS para extraer series temporales de MODIS sin necesidad de procesar archivos HDF |
| `APPEEARS_USER` | Usuario de NASA Earthdata para autenticación en AppEEARS |
| `APPEEARS_PASSWORD` | Contraseña de NASA Earthdata |

---

---

## ARCHIVO: `etl/utils/logger.py`

### ¿Qué hace este archivo?
Configura el **sistema de registro de eventos (logging)** del proyecto. Cuando un script extrae, transforma o carga datos, usa este sistema para registrar qué hizo, cuándo, cuántas filas procesó y si hubo errores. Genera dos salidas simultáneas: consola (para el desarrollador) y archivo JSON (para análisis posterior).

---

### IMPORTACIONES

| Módulo | Para qué se usa |
|--------|-----------------|
| `logging` | Módulo estándar de Python para manejo de logs |
| `json` | Para serializar los eventos de log en formato JSON |
| `sys` | Para escribir en la salida estándar (consola) con `sys.stdout` |
| `datetime.datetime` | Para agregar marca de tiempo UTC a cada evento de log |
| `pathlib.Path` | Para manejar rutas de archivos de los logs |

---

### CLASE: `FormateadorJSON(logging.Formatter)`

**¿Qué es?** Un formateador personalizado que convierte cada evento de log (`LogRecord`) en una línea de texto JSON en lugar del formato de texto plano estándar de Python.

**¿Por qué JSON?** Permite analizar los logs automáticamente con herramientas como pandas, Elasticsearch o cualquier sistema de monitoreo. Cada log queda como un objeto estructurado.

#### MÉTODO: `format(self, registro: logging.LogRecord) -> str`

**Parámetros:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `registro` | `logging.LogRecord` | Objeto que Python crea automáticamente al llamar `logger.info()`, `logger.error()`, etc. Contiene toda la información del evento |

**Campos base del diccionario JSON (siempre presentes):**

| Campo JSON | Fuente | Descripción |
|------------|--------|-------------|
| `timestamp` | `datetime.utcnow().isoformat() + "Z"` | Fecha y hora en UTC, formato ISO 8601. El `"Z"` indica que es UTC |
| `nivel` | `registro.levelname` | Nivel del log: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `modulo` | `registro.module` | Nombre del archivo Python que generó el log (sin extensión) |
| `funcion` | `registro.funcName` | Nombre de la función donde se llamó al logger |
| `linea` | `registro.lineno` | Número de línea del código fuente donde ocurrió el evento |
| `mensaje` | `registro.getMessage()` | El texto del mensaje de log |

**Campos opcionales (solo si el código los envía con `extra={}`):**

| Campo JSON | Atributo en `extra` | Descripción |
|------------|---------------------|-------------|
| `etapa_etl` | `etl_stage` | Etapa del pipeline: `"extract"`, `"transform"`, `"load"`, `"scheduler"` |
| `fuente` | `source` | Fuente de datos: `"firms_nrt"`, `"openmeteo_archivo"`, `"cams"`, etc. |
| `filas_procesadas` | `rows_count` | Cantidad de filas procesadas en esa operación |
| `id_lote` | `batch_id` | Identificador del lote de procesamiento |
| `excepcion` | `registro.exc_info` | Si hubo excepción, se incluye como string para diagnóstico |

**Retorna:** String JSON de una sola línea. Ejemplo:
```json
{"timestamp": "2024-01-15T10:30:00Z", "nivel": "INFO", "modulo": "extract_firms", "funcion": "extraer_firms_nrt", "linea": 118, "mensaje": "FIRMS NRT: 500 focos descargados", "etapa_etl": "extract", "fuente": "firms_nrt", "filas_procesadas": 500}
```

**Parámetro `ensure_ascii=False`:** Permite caracteres especiales como `ñ`, tildes, `ü` en el JSON sin necesidad de escape.

---

### FUNCIÓN: `setup_logger(nombre, dir_logs, nivel) -> logging.Logger`

**¿Qué hace?** Crea y configura un logger con salida simultánea a consola y archivo JSON. Es la función que todos los módulos del proyecto llaman al inicio para obtener su logger.

**Parámetros:**

| Parámetro | Tipo | Valor por defecto | Descripción |
|-----------|------|-------------------|-------------|
| `nombre` | `str` | `"sinia"` | Nombre jerárquico del logger. Los puntos crean jerarquía: `"sinia.extract.firms"` es hijo de `"sinia.extract"` que es hijo de `"sinia"` |
| `dir_logs` | `str \| Path` | `"logs"` | Carpeta donde se guardan los archivos JSON de log |
| `nivel` | `str` | `"INFO"` | Nivel mínimo de eventos a registrar. Valores posibles: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"` |

**Variables internas:**

| Variable | Tipo | Descripción |
|----------|------|-------------|
| `dir_logs` | `Path` | Conversión del parámetro a objeto `Path` para poder usar `.mkdir()` |
| `logger` | `Logger` | Objeto logger obtenido (o creado) por `logging.getLogger(nombre)` |
| `handler_consola` | `StreamHandler` | Handler que escribe en `sys.stdout` (la terminal) |
| `formato_consola` | `Formatter` | Formato legible: `"%(asctime)s [%(levelname)s] %(module)s: %(message)s"` |
| `fecha_hoy` | `str` | Fecha en formato `YYYY-MM-DD` para el nombre del archivo de log |
| `ruta_archivo` | `Path` | Ruta completa del archivo JSON: `logs/sinia_2024-01-15.json` |
| `handler_archivo` | `FileHandler` | Handler que escribe en el archivo JSON |

**Patrón singleton:** `logging.getLogger(nombre)` devuelve siempre el mismo objeto si ya existe un logger con ese nombre. La guarda `if logger.handlers: return logger` evita agregar handlers duplicados si se llama varias veces.

**Dos handlers configurados:**

**Handler 1 — Consola:**
- Escribe en `sys.stdout` (terminal visible)
- Nivel mínimo: `INFO` (no muestra DEBUG para no saturar)
- Formato: `"2024-01-15 10:30:00 [INFO] extract_firms: FIRMS NRT: 500 focos descargados"`

**Handler 2 — Archivo JSON:**
- Escribe en `logs/sinia_YYYY-MM-DD.json`
- Nivel mínimo: `DEBUG` (guarda absolutamente todo)
- Formato: JSON con `FormateadorJSON()`
- Codificación: `UTF-8` para soportar caracteres especiales
- Un archivo nuevo por día (el nombre incluye la fecha)

**Retorna:** Objeto `logging.Logger` completamente configurado.

**Uso típico en cada módulo:**
```python
from etl.utils.logger import setup_logger
logger = setup_logger("sinia.extract.firms")
logger.info("Iniciando descarga", extra={"etl_stage": "extract", "source": "firms_nrt"})
logger.warning("Solo 3 focos encontrados", extra={"rows_count": 3})
logger.error("Error de red", exc_info=True)
```
