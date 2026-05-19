# =============================================================================
# SINIA-SA — Scheduler de Actualización en Tiempo Real (Sudamérica)
# =============================================================================
# Este script mantiene los datos del sistema siempre actualizados ejecutando
# los extractores y transformaciones automáticamente en segundo plano.
#
# Frecuencias de actualización:
#   - Cada 3 horas: FIRMS NRT — focos de calor de las últimas horas (Sudamérica)
#   - Cada 1 hora:  Pronóstico meteorológico — índice de riesgo futuro 7 días
#   - Cada 1 hora:  CAMS calidad del aire — PM10 y PM2.5 del día actual
#   - 1×/mes:       CHIRPS precipitación mensual (se actualiza con retraso ~1 mes)
#   - 1×/año:       MODIS Land Cover (dato anual, solo disponible al cierre de año)
#
# Al iniciarse, ejecuta todos los jobs INMEDIATAMENTE para tener datos frescos
# desde el primer momento, sin esperar al primer intervalo programado.
#
# Cómo ejecutar (desde la carpeta raíz del proyecto):
#   python etl/scheduler.py
#
# Para detener: Ctrl+C en la terminal
#
# El scheduler y el dashboard pueden correr en paralelo en terminales separadas.
# El dashboard lee los archivos Parquet que genera el scheduler.
# =============================================================================

import sys                   # Para manipular el path de importación
from datetime import datetime, date, timedelta   # Para marcas de tiempo en los logs
from pathlib import Path     # Para manejo de rutas

import pandas as pd   # Para manejar los DataFrames entre extracción y transformación

# APScheduler: librería para programar tareas periódicas en Python
# BlockingScheduler: bloquea el hilo principal (ideal para scripts independientes)
# IntervalTrigger: ejecuta jobs en intervalos de tiempo regulares (cada N horas)
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Agregamos la raíz del proyecto al path para que funcionen los imports internos
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Importamos configuración y logger del proyecto
from config.settings import LOG_LEVEL, DIR_PROCESADO, PG_CONFIG
from etl.utils.logger import setup_logger

# Logger específico para el scheduler
logger = setup_logger("sinia.scheduler", nivel=LOG_LEVEL)

# Nos aseguramos de que la carpeta de datos procesados exista
DIR_PROCESADO.mkdir(parents=True, exist_ok=True)


# =============================================================================
# WATERMARK — CDC incremental
# =============================================================================

def _get_watermark(tabla: str, campo_fecha: str, filtro: str = "") -> date:
    """
    Lee el último dato cargado en PostgreSQL para una tabla/campo dado.
    Si la tabla está vacía o PG no está disponible, devuelve ayer como fallback.

    Args:
        tabla:        Nombre de la tabla (ej: "focos_calor")
        campo_fecha:  Columna de fecha (ej: "fecha_adq")
        filtro:       Cláusula WHERE adicional (ej: "tipo_dato='forecast'")
    Returns:
        date con el último dato cargado (el job pedirá datos desde el día siguiente).
    """
    try:
        import psycopg2
        conn = psycopg2.connect(**PG_CONFIG, connect_timeout=5)
        where = f"WHERE {filtro}" if filtro else ""
        with conn.cursor() as cur:
            cur.execute(f"SELECT MAX({campo_fecha}) FROM {tabla} {where}")
            result = cur.fetchone()[0]
        conn.close()
        if result is not None:
            if hasattr(result, "date"):
                return result.date()
            return result
    except Exception as e:
        logger.warning(f"Watermark no disponible para {tabla}: {e}")

    # Fallback: ayer (al menos traemos un día)
    return date.today() - timedelta(days=1)


# =============================================================================
# JOB 1: Actualización de Focos de Calor NRT
# Frecuencia: cada 3 horas
# =============================================================================

def job_firms_nrt():
    """
    Descarga focos NRT desde el último dato cargado en PG (watermark CDC).
    Guarda en parquet NRT Y carga en focos_calor (PostgreSQL) via upsert.
    """
    logger.info(
        "JOB FIRMS NRT — iniciando (CDC watermark)",
        extra={"etl_stage": "scheduler", "source": "firms_nrt"},
    )

    try:
        from etl.extract.extract_firms import extraer_firms_nrt
        from etl.transform.transform_firms import transformar_firms
        from etl.load.load_postgres import cargar_focos_calor

        # CDC: ¿hasta qué fecha ya cargamos en PG?
        ultimo_cargado = _get_watermark("focos_calor", "fecha_adq")
        dias_a_pedir   = (date.today() - ultimo_cargado).days + 1  # +1 para incluir hoy
        dias_a_pedir   = max(1, min(dias_a_pedir, 5))  # FIRMS NRT acepta rango [1..5]

        logger.info(
            f"JOB FIRMS NRT — watermark={ultimo_cargado}, pidiendo {dias_a_pedir} día(s)",
            extra={"etl_stage": "scheduler", "source": "firms_nrt"},
        )

        df_crudo = extraer_firms_nrt(sensor="VIIRS_SNPP_NRT", dias=dias_a_pedir, guardar=True)

        if not df_crudo.empty:
            df_nuevo = transformar_firms(df_crudo, guardar=False)

            # Acumular parquet NRT (para dashboard "Tiempo Real")
            ruta_nrt = DIR_PROCESADO / "firms_nrt_procesado.parquet"
            if ruta_nrt.exists():
                df_hist = pd.read_parquet(ruta_nrt)
                df_nrt  = pd.concat([df_hist, df_nuevo], ignore_index=True).drop_duplicates()
            else:
                df_nrt = df_nuevo
            df_nrt.to_parquet(ruta_nrt, index=False)

            # CDC: cargar en PostgreSQL (upsert — no genera duplicados)
            metricas = cargar_focos_calor(df_nuevo)
            logger.info(
                f"JOB FIRMS NRT — PG: {metricas['insertados']} nuevos, "
                f"{metricas['sin_cambio']} sin cambio | "
                f"Parquet: {len(df_nrt)} focos acumulados",
                extra={"etl_stage": "scheduler", "source": "firms_nrt"},
            )
        else:
            logger.info("JOB FIRMS NRT — sin focos detectados en el período")

    except Exception as error:
        logger.error(
            f"JOB FIRMS NRT — error: {error}",
            extra={"etl_stage": "scheduler", "source": "firms_nrt"},
        )


# =============================================================================
# JOB 2: Actualización del Pronóstico e Índice de Riesgo
# Frecuencia: cada 1 hora
# =============================================================================

def job_pronostico():
    """
    Descarga el pronóstico meteorológico de 7 días y calcula el índice de riesgo.
    Guarda en parquet Y carga en meteo_diario (tipo_dato='forecast') vía upsert CDC.
    """
    logger.info(
        "JOB PRONÓSTICO — iniciando (CDC watermark)",
        extra={"etl_stage": "scheduler", "source": "forecast"},
    )

    try:
        from etl.extract.extract_forecast import extraer_pronostico_todos
        from etl.transform.transform_meteo import transformar_meteo
        from etl.load.load_postgres import cargar_meteo_diario

        df_crudo = extraer_pronostico_todos(dias=7)

        if not df_crudo.empty:
            frames_procesados = []
            for punto in df_crudo["punto"].unique():
                df_punto    = df_crudo[df_crudo["punto"] == punto].copy()
                df_procesado = transformar_meteo(df_punto, guardar=False)
                frames_procesados.append(df_procesado)

            df_final = pd.concat(frames_procesados, ignore_index=True)

            # Parquet para dashboard
            ruta_salida = DIR_PROCESADO / "forecast_riesgo.parquet"
            df_final.to_parquet(ruta_salida, index=False)

            # CDC: upsert en PostgreSQL (tipo_dato='forecast', ON CONFLICT actualiza)
            metricas = cargar_meteo_diario(df_final, tipo_dato="forecast")
            logger.info(
                f"JOB PRONÓSTICO — {len(df_final)} registros | "
                f"PG: {metricas['insertados']} nuevos, {metricas['actualizados']} actualizados",
                extra={"etl_stage": "scheduler", "source": "forecast"},
            )

    except Exception as error:
        logger.error(
            f"JOB PRONÓSTICO — error: {error}",
            extra={"etl_stage": "scheduler", "source": "forecast"},
        )


# =============================================================================
# JOB 3: Actualización de Calidad del Aire
# Frecuencia: cada 1 hora
# =============================================================================

def job_cams():
    """
    Descarga calidad del aire desde el último dato cargado en PG (watermark CDC).
    Guarda en parquet NRT Y carga en calidad_aire_diario (PostgreSQL) vía upsert.
    """
    logger.info(
        "JOB CAMS — iniciando (CDC watermark)",
        extra={"etl_stage": "scheduler", "source": "cams"},
    )

    try:
        from etl.extract.extract_cams import extraer_cams_todos_los_puntos
        from etl.transform.transform_cams import transformar_cams
        from etl.load.load_postgres import cargar_calidad_aire

        # CDC watermark: último dato CAMS cargado en PG
        ultimo_cams  = _get_watermark("calidad_aire_diario", "fecha")
        fecha_inicio = (ultimo_cams + timedelta(days=1)).strftime("%Y-%m-%d")
        fecha_fin    = date.today().strftime("%Y-%m-%d")

        if fecha_inicio > fecha_fin:
            logger.info("JOB CAMS — ya está al día, nada nuevo que cargar")
            return

        logger.info(
            f"JOB CAMS — watermark={ultimo_cams}, pidiendo {fecha_inicio} -> {fecha_fin}",
            extra={"etl_stage": "scheduler", "source": "cams"},
        )

        df_crudo = extraer_cams_todos_los_puntos(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

        if not df_crudo.empty:
            df_nuevo = transformar_cams(df_crudo, guardar=False)

            # Parquet NRT acumulativo
            ruta_cams_nrt = DIR_PROCESADO / "cams_nrt_procesado.parquet"
            if ruta_cams_nrt.exists():
                df_hist = pd.read_parquet(ruta_cams_nrt)
                df_cams = pd.concat([df_hist, df_nuevo], ignore_index=True)
                dedup   = [c for c in ["fecha", "punto"] if c in df_cams.columns]
                df_cams = df_cams.drop_duplicates(subset=dedup, keep="last")
            else:
                df_cams = df_nuevo
            df_cams.to_parquet(ruta_cams_nrt, index=False)

            # CDC: upsert en PostgreSQL
            metricas = cargar_calidad_aire(df_nuevo)
            logger.info(
                f"JOB CAMS — PG: {metricas['insertados']} nuevos, "
                f"{metricas['sin_cambio']} sin cambio | "
                f"Parquet: {len(df_cams)} registros acumulados",
                extra={"etl_stage": "scheduler", "source": "cams"},
            )
        else:
            logger.info("JOB CAMS — sin datos nuevos en el período")

    except Exception as error:
        logger.error(
            f"JOB CAMS — error: {error}",
            extra={"etl_stage": "scheduler", "source": "cams"},
        )


# =============================================================================
# JOB 4: Precipitación Mensual CHIRPS
# Frecuencia: cada 30 días (CHIRPS se actualiza con ~1 mes de retraso)
# =============================================================================

def job_chirps_mensual():
    """
    Descarga precipitación mensual CHIRPS para los 36 puntos del alcance final y
    la carga en precipitacion_mensual (PostgreSQL).

    Se ejecuta mensualmente porque CHIRPS tiene latencia de ~1 mes.
    """
    logger.info(
        "JOB CHIRPS — descargando precipitación mensual para todos los puntos SA",
        extra={"etl_stage": "scheduler", "source": "chirps"},
    )

    try:
        from datetime import date
        from etl.extract.extract_chirps import extraer_chirps_todos_los_puntos
        from etl.load.load_postgres import cargar_precipitacion

        anio_actual = date.today().year

        # Descargamos el último año completo disponible
        df = extraer_chirps_todos_los_puntos(
            anio_inicio=anio_actual - 1,
            anio_fin=anio_actual,
        )

        if not df.empty:
            # Guardamos parquet para fallback del dashboard
            ruta = DIR_PROCESADO / "chirps_sa.parquet"
            if ruta.exists():
                df_prev = pd.read_parquet(ruta)
                df = pd.concat([df_prev, df], ignore_index=True).drop_duplicates(
                    subset=["punto", "fecha"]
                )
            df.to_parquet(ruta, index=False)

            # Cargamos en PostgreSQL
            cargar_precipitacion(df)
            logger.info(
                f"JOB CHIRPS — completado: {len(df)} registros mensuales",
                extra={"etl_stage": "scheduler", "source": "chirps", "rows_count": len(df)},
            )

    except Exception as error:
        logger.error(
            f"JOB CHIRPS — error inesperado: {error}",
            extra={"etl_stage": "scheduler", "source": "chirps"},
        )


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    """
    Punto de entrada del scheduler.
    Configura los jobs, los ejecuta inmediatamente y luego los programa
    para correr en intervalos regulares indefinidamente.
    """
    # Encabezado informativo en la consola
    print("=" * 60)
    print("SINIA-SA — Scheduler de Actualización en Tiempo Real")
    print("=" * 60)
    print(f"  Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("  Frecuencias de actualización:")
    print("    Focos FIRMS NRT  -> cada 3 horas")
    print("    Pronóstico       -> cada 1 hora")
    print("    Calidad del Aire -> cada 1 hora")
    print()
    print("  Ejecutando todos los jobs ahora (descarga inicial)...")
    print("  Presioná Ctrl+C para detener el scheduler.")
    print("=" * 60)

    # ── Ejecución inmediata al arrancar ───────────────────────────────────────
    # Ejecutamos todos los jobs una vez al inicio para tener datos frescos
    # sin tener que esperar al primer intervalo programado

    print("\n[1/3] Descargando pronóstico meteorológico...")
    job_pronostico()   # Primero el pronóstico (sin límites de API)

    print("[2/3] Descargando focos de calor NRT...")
    job_firms_nrt()    # Luego FIRMS NRT

    print("[3/3] Descargando calidad del aire...")
    job_cams()         # Finalmente CAMS

    print("\nDescarga inicial completada. Scheduler programado.")

    # ── Configuración del scheduler periódico ────────────────────────────────
    # BlockingScheduler ocupa el hilo principal — el script no termina hasta Ctrl+C
    planificador = BlockingScheduler(
        timezone="UTC"   # UTC — neutro para sistema multi-país en Sudamérica
    )

    # Job FIRMS NRT: se ejecuta cada 3 horas
    planificador.add_job(
        job_firms_nrt,                          # Función a ejecutar
        trigger=IntervalTrigger(hours=3),       # Cada 3 horas
        id="firms_nrt",                         # Identificador único del job
        name="FIRMS NRT — focos últimas 3h",    # Nombre descriptivo
        misfire_grace_time=300,                 # Si se perdió el tiempo por 5 min, igual ejecuta
    )

    # Job Pronóstico: se ejecuta cada 1 hora
    planificador.add_job(
        job_pronostico,
        trigger=IntervalTrigger(hours=1),
        id="pronostico",
        name="Pronóstico meteorológico 7 días",
        misfire_grace_time=120,
    )

    # Job CAMS: se ejecuta cada 1 hora
    planificador.add_job(
        job_cams,
        trigger=IntervalTrigger(hours=1),
        id="cams",
        name="CAMS calidad del aire",
        misfire_grace_time=120,
    )

    # Job CHIRPS: mensual (CHIRPS se actualiza con ~1 mes de retraso)
    planificador.add_job(
        job_chirps_mensual,
        trigger=IntervalTrigger(days=30),
        id="chirps",
        name="CHIRPS precipitación mensual",
        misfire_grace_time=3600,
    )

    # Registramos en el log que el scheduler quedó activo
    logger.info("Scheduler iniciado y corriendo")

    # Mostramos los próximos horarios de ejecución
    print("\nJobs programados:")
    for job in planificador.get_jobs():
        print(f"  • {job.name}")

    try:
        # Iniciamos el scheduler — bloquea aquí hasta que el usuario presione Ctrl+C
        planificador.start()
    except KeyboardInterrupt:
        # El usuario presionó Ctrl+C — detenemos limpiamente
        print("\n\nScheduler detenido por el usuario.")
        logger.info("Scheduler detenido correctamente por el usuario")


# =============================================================================
# PUNTO DE ENTRADA
# Este bloque solo se ejecuta cuando corremos el script directamente:
#   python etl/scheduler.py
# =============================================================================

if __name__ == "__main__":
    main()
