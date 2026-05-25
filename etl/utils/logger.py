# =============================================================================
# SINIA-UY — Sistema de Logging Estructurado
# =============================================================================
# Este módulo configura el sistema de registro de eventos del proyecto.
# Cada vez que un script extrae, transforma o carga datos, registra lo que
# hizo, cuándo, cuántas filas procesó y si hubo algún error.
#
# Genera DOS tipos de salida simultáneamente:
#   1. Consola: formato legible para el desarrollador mientras trabaja
#   2. Archivo JSON: formato estructurado para análisis posterior
#
# Los archivos de log se guardan en logs/sinia_YYYY-MM-DD.json
# Un archivo nuevo por día.
# =============================================================================

import logging    # Módulo estándar de Python para manejo de logs
import json       # Para serializar los logs en formato JSON
import sys        # Para escribir en la salida estándar (consola)
from datetime import datetime, timezone   # Para agregar marca de tiempo a cada log
from pathlib import Path        # Para manejar rutas de archivos


# -----------------------------------------------------------------------------
# FORMATEADOR JSON
# Convierte cada evento de log en una línea de texto JSON.
# Esto permite analizar los logs con herramientas como pandas o Elasticsearch.
# -----------------------------------------------------------------------------

class FormateadorJSON(logging.Formatter):
    """
    Formateador personalizado que serializa cada evento de log como JSON.

    En lugar de producir texto plano como:
        2024-01-15 10:30:00 INFO: Se descargaron 500 focos

    Produce una línea JSON como:
        {"timestamp": "2024-01-15T10:30:00Z", "nivel": "INFO", "mensaje": "Se descargaron 500 focos"}

    Esto facilita el análisis automático de los logs.
    """

    def format(self, registro: logging.LogRecord) -> str:
        """
        Convierte un LogRecord (evento de log) en una cadena JSON.

        Args:
            registro: El objeto LogRecord generado por Python al llamar logger.info(), etc.

        Returns:
            Cadena de texto con el evento serializado en formato JSON.
        """
        # Construimos el diccionario base con los campos siempre presentes
        entrada_log = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "nivel":     registro.levelname,    # Nivel: DEBUG, INFO, WARNING, ERROR, CRITICAL
            "modulo":    registro.module,        # Nombre del archivo Python que generó el log
            "funcion":   registro.funcName,      # Nombre de la función donde se llamó al logger
            "linea":     registro.lineno,         # Número de línea del código fuente
            "mensaje":   registro.getMessage(),   # El texto del mensaje de log
        }

        # Campos opcionales — solo se agregan si el código los envía explícitamente
        # usando el parámetro extra={"campo": valor} al llamar al logger

        # Etapa del pipeline ETL donde ocurrió el evento (extract / transform / load)
        if hasattr(registro, "etl_stage"):
            entrada_log["etapa_etl"] = registro.etl_stage

        # Fuente de datos involucrada (firms_nrt, openmeteo_archive, cams, etc.)
        if hasattr(registro, "source"):
            entrada_log["fuente"] = registro.source

        # Cantidad de filas procesadas en esa operación
        if hasattr(registro, "rows_count"):
            entrada_log["filas_procesadas"] = registro.rows_count

        # Identificador del lote de procesamiento (para agrupar logs de una misma ejecución)
        if hasattr(registro, "batch_id"):
            entrada_log["id_lote"] = registro.batch_id

        # Si hubo una excepción, la agregamos como texto para facilitar el diagnóstico
        if registro.exc_info and registro.exc_info[1]:
            entrada_log["excepcion"] = str(registro.exc_info[1])

        # Serializamos el diccionario como JSON en una sola línea
        # ensure_ascii=False permite caracteres especiales como ñ, tildes, etc.
        return json.dumps(entrada_log, ensure_ascii=False)


# -----------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL — setup_logger
# Esta es la función que todos los módulos del proyecto llaman para obtener
# un logger configurado y listo para usar.
# -----------------------------------------------------------------------------

def setup_logger(
    nombre: str = "sinia",
    dir_logs: str | Path = "logs",
    nivel: str = "INFO",
) -> logging.Logger:
    """
    Crea y configura un logger con salida simultánea a consola y archivo JSON.

    Uso típico en cualquier módulo del proyecto:
        from etl.utils.logger import setup_logger
        logger = setup_logger("sinia.extract.firms")
        logger.info("Iniciando descarga", extra={"etl_stage": "extract"})

    Args:
        nombre:   Nombre jerárquico del logger (ej: "sinia.extract.firms").
                  Los loggers con el mismo prefijo comparten configuración.
        dir_logs: Carpeta donde se guardan los archivos JSON de log.
        nivel:    Nivel mínimo de eventos a registrar. Opciones:
                  "DEBUG"   -> registra absolutamente todo (muy verboso)
                  "INFO"    -> registra eventos normales de operación
                  "WARNING" -> solo advertencias y errores
                  "ERROR"   -> solo errores críticos

    Returns:
        Logger configurado con handler de consola y handler de archivo JSON.
    """
    # Convertimos dir_logs a objeto Path por si llegó como string
    dir_logs = Path(dir_logs)

    # Creamos la carpeta de logs si no existe (no da error si ya existe)
    dir_logs.mkdir(parents=True, exist_ok=True)

    # Obtenemos (o creamos) el logger con el nombre especificado
    # Python reutiliza loggers existentes con el mismo nombre (patrón singleton)
    logger = logging.getLogger(nombre)

    # Convertimos el string de nivel ("INFO") al valor numérico que usa Python (20)
    # getattr busca el atributo logging.INFO, logging.DEBUG, etc.
    logger.setLevel(getattr(logging, nivel.upper(), logging.INFO))

    # Si el logger ya tiene handlers configurados, lo devolvemos sin agregar más
    # Esto evita duplicar mensajes si setup_logger se llama varias veces con el mismo nombre
    if logger.handlers:
        return logger

    # ── Handler 1: Consola ────────────────────────────────────────────────────
    # Muestra los logs en la terminal mientras el script está corriendo.
    # Solo muestra nivel INFO o superior (no DEBUG) para no saturar la pantalla.

    handler_consola = logging.StreamHandler(sys.stdout)   # Escribe en la salida estándar
    handler_consola.setLevel(logging.INFO)                # Mínimo INFO en consola

    # Formato legible para humanos: fecha [NIVEL] módulo: mensaje
    formato_consola = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",   # Formato de fecha: 2024-01-15 10:30:00
    )
    handler_consola.setFormatter(formato_consola)   # Asociamos el formato al handler
    logger.addHandler(handler_consola)               # Registramos el handler en el logger

    # ── Handler 2: Archivo JSON ───────────────────────────────────────────────
    # Escribe TODOS los logs (desde DEBUG) en un archivo JSON diario.
    # El nombre incluye la fecha para tener un archivo por día: sinia_2024-01-15.json

    fecha_hoy = datetime.now().strftime("%Y-%m-%d")   # Fecha de hoy en formato YYYY-MM-DD
    ruta_archivo = dir_logs / f"sinia_{fecha_hoy}.json"   # Ruta completa del archivo de log

    handler_archivo = logging.FileHandler(
        ruta_archivo,        # Ruta donde se crea/abre el archivo
        encoding="utf-8",    # Codificación UTF-8 para soportar caracteres especiales
    )
    handler_archivo.setLevel(logging.DEBUG)           # DEBUG y superior van al archivo
    handler_archivo.setFormatter(FormateadorJSON())   # Usamos nuestro formateador JSON
    logger.addHandler(handler_archivo)                # Registramos el handler en el logger

    return logger   # Devolvemos el logger completamente configurado
