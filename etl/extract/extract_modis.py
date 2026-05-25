# =============================================================================
# SINIA-SA — Extractor MODIS Land Cover (MCD12Q1) vía NASA AppEEARS
# =============================================================================
# MODIS MCD12Q1 = MODIS/Terra+Aqua Land Cover Type Yearly L3 Global 500m
# Clasificación anual de uso/cobertura del suelo desde 2001 al presente.
#
# NASA AppEEARS (Application for Extracting and Exploring Analysis Ready Samples)
# permite solicitar series temporales de MODIS por punto sin procesar archivos HDF.
# URL: https://appeears.earthdatacloud.nasa.gov/api
# Requiere cuenta NASA Earthdata: https://urs.earthdata.nasa.gov/
#
# Integración con el modelo de datos:
#   - Se guarda en tabla cobertura_vegetal (PostgreSQL)
#   - Permite clasificar el combustible potencial de incendio por tipo de cobertura
#   - Tipo LC_Type1: escala IGBP (1=bosque siempreverde, 10=pastizales, etc.)
# =============================================================================

import time
from pathlib import Path

import pandas as pd
import requests

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.settings import (
    PUNTOS_METEO_SA,
    APPEEARS_BASE_URL,
    APPEEARS_USER,
    APPEEARS_PASSWORD,
    DIR_CRUDO,
)
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.extract.modis")

# Producto MODIS a extraer
MODIS_PRODUCTO  = "MCD12Q1.061"   # Version 6.1, disponible desde 2001
MODIS_VARIABLE  = "LC_Type1"      # Clasificación IGBP (International Geosphere-Biosphere Programme)

# Mapeo IGBP -> descripción legible para el dashboard
IGBP_LABELS = {
    1:  "Bosque siempreverde de coníferas",
    2:  "Bosque caducifolio de coníferas",
    3:  "Bosque siempreverde de hoja ancha",
    4:  "Bosque caducifolio de hoja ancha",
    5:  "Bosque mixto",
    6:  "Arbustal cerrado",
    7:  "Arbustal abierto",
    8:  "Sabana arbolada",
    9:  "Sabana",
    10: "Pastizal",
    11: "Humedal permanente",
    12: "Tierra de cultivo",
    13: "Zona urbana",
    14: "Cultivo/Vegetación natural mosaico",
    15: "Nieve y hielo",
    16: "Suelo desnudo / Vegetación escasa",
    17: "Cuerpo de agua",
    255: "Sin clasificar",
}


# =============================================================================
# FUNCIÓN 1: Autenticación con AppEEARS
# =============================================================================

def _obtener_token_appeears() -> str:
    """
    Obtiene un token Bearer de la API de AppEEARS mediante credenciales Earthdata.

    Returns:
        Token de autenticación como string.

    Raises:
        ValueError:  Si las credenciales no están configuradas en el .env
        HTTPError:   Si la autenticación falla
    """
    if not APPEEARS_USER or not APPEEARS_PASSWORD:
        raise ValueError(
            "Credenciales AppEEARS no configuradas.\n"
            "1. Crear cuenta en: https://urs.earthdata.nasa.gov/\n"
            "2. Agregar a config/.env:\n"
            "   APPEEARS_USER=tu_usuario\n"
            "   APPEEARS_PASSWORD=tu_password"
        )

    resp = requests.post(
        f"{APPEEARS_BASE_URL}/login",
        auth=(APPEEARS_USER, APPEEARS_PASSWORD),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["token"]


# =============================================================================
# FUNCIÓN 2: Solicitar serie temporal para múltiples puntos
# =============================================================================

def solicitar_cobertura_vegetal(
    anio_inicio: int = 2018,
    anio_fin: int = 2024,
    token: str = None,
) -> str:
    """
    Envía una solicitud de extracción de LC_Type1 a AppEEARS para los 36 puntos.

    AppEEARS trabaja de forma asíncrona: esta función envía la solicitud y
    devuelve el task_id para consultarlo más tarde con descargar_resultado().

    Args:
        anio_inicio: Primer año a extraer (mínimo 2001)
        anio_fin:    Último año a extraer
        token:       Token Bearer. Si None, se obtiene automáticamente.

    Returns:
        task_id: ID de la tarea en AppEEARS para usar en descargar_resultado()
    """
    if token is None:
        token = _obtener_token_appeears()

    # Construimos la lista de puntos en formato AppEEARS
    puntos_appeears = [
        {
            "id":        nombre,
            "longitude": info["lon"],
            "latitude":  info["lat"],
            "category":  info["pais"],
        }
        for nombre, info in PUNTOS_METEO_SA.items()
    ]

    payload = {
        "task_type":    "point",
        "task_name":    f"SINIA_SA_LandCover_{anio_inicio}_{anio_fin}",
        "params": {
            "dates": [
                {
                    "startDate": f"01-01-{anio_inicio}",
                    "endDate":   f"12-31-{anio_fin}",
                }
            ],
            "layers": [
                {"product": MODIS_PRODUCTO, "layer": MODIS_VARIABLE}
            ],
            "coordinates": puntos_appeears,
            "output": {
                "format":     {"type": "csv"},
                "projection": "geographic",
            },
        },
    }

    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(
        f"{APPEEARS_BASE_URL}/task",
        json=payload,
        headers=headers,
        timeout=60,
    )
    resp.raise_for_status()
    task_id = resp.json()["task_id"]

    logger.info(
        f"AppEEARS solicitud enviada: task_id={task_id}, "
        f"período={anio_inicio}–{anio_fin}, n_puntos={len(puntos_appeears)}",
        extra={"etl_stage": "extract", "source": "modis_appeears"},
    )

    return task_id


# =============================================================================
# FUNCIÓN 3: Polling y descarga del resultado
# =============================================================================

def descargar_resultado_appeears(
    task_id: str,
    token: str = None,
    max_minutos: int = 60,
    guardar: bool = True,
) -> pd.DataFrame:
    """
    Espera a que la tarea de AppEEARS termine y descarga el resultado.

    Args:
        task_id:     ID de tarea devuelto por solicitar_cobertura_vegetal()
        token:       Token Bearer. Si None, se obtiene automáticamente.
        max_minutos: Tiempo máximo de espera en minutos (default 60)
        guardar:     Si True, guarda el CSV en data/raw/modis/

    Returns:
        DataFrame con columnas: punto, pais, anio, lc_type1, lc_descripcion, fuente
    """
    if token is None:
        token = _obtener_token_appeears()

    headers = {"Authorization": f"Bearer {token}"}
    max_intentos = max_minutos * 2   # Chequeamos cada 30 segundos

    logger.info(f"Esperando resultado AppEEARS task_id={task_id}...")

    for _ in range(max_intentos):
        time.sleep(30)
        resp = requests.get(
            f"{APPEEARS_BASE_URL}/task/{task_id}",
            headers=headers,
            timeout=30,
        )
        status = resp.json().get("status", "")
        if status == "done":
            break
        if status == "error":
            logger.error(f"AppEEARS tarea fallida: {resp.json()}")
            return pd.DataFrame()
    else:
        logger.warning(f"AppEEARS timeout después de {max_minutos} minutos")
        return pd.DataFrame()

    # Listamos los archivos del resultado
    files_resp = requests.get(
        f"{APPEEARS_BASE_URL}/bundle/{task_id}",
        headers=headers,
        timeout=30,
    )
    archivos = files_resp.json().get("files", [])

    # Descargamos el archivo CSV con los datos (no el de calidad)
    csv_file = next(
        (f for f in archivos if f["file_name"].endswith(".csv")
         and "request" not in f["file_name"].lower()),
        None,
    )

    if not csv_file:
        logger.warning("AppEEARS: no se encontró archivo CSV en el bundle")
        return pd.DataFrame()

    dl_resp = requests.get(
        f"{APPEEARS_BASE_URL}/bundle/{task_id}/{csv_file['file_id']}",
        headers=headers,
        stream=True,
        timeout=120,
    )
    dl_resp.raise_for_status()

    # Guardamos y parseamos
    if guardar:
        ruta = DIR_CRUDO / "modis" / f"modis_lc_{task_id}.csv"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "wb") as f:
            for chunk in dl_resp.iter_content(chunk_size=8192):
                f.write(chunk)
        df = pd.read_csv(ruta)
    else:
        import io
        df = pd.read_csv(io.BytesIO(dl_resp.content))

    df = _parsear_resultado_appeears(df)

    logger.info(
        f"AppEEARS descarga completa: {len(df)} registros",
        extra={"etl_stage": "extract", "source": "modis_appeears", "rows_count": len(df)},
    )

    return df


def _parsear_resultado_appeears(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza el DataFrame crudo de AppEEARS al esquema del proyecto.

    AppEEARS devuelve columnas con nombres técnicos. Los mapeamos a español
    y agregamos la descripción IGBP en texto legible.
    """
    if df_raw.empty:
        return df_raw

    # Las columnas varían según la versión pero suelen ser:
    # ID, Latitude, Longitude, Date, MCD12Q1_061_LC_Type1, Category
    col_lc = next(
        (c for c in df_raw.columns if "LC_Type1" in c),
        None,
    )
    col_date = next(
        (c for c in df_raw.columns if c.lower() in ("date", "fecha")),
        None,
    )
    # AppEEARS devuelve: Category=pais_enviado, ID=nombre_punto_enviado
    # Buscamos explícitamente la columna ID para el nombre de ciudad
    col_id = next(
        (c for c in df_raw.columns if c.upper() == "ID"),
        None,
    ) or next(
        (c for c in df_raw.columns if c.lower() in ("punto", "site", "name")),
        "ID",
    )
    col_pais = next(
        (c for c in df_raw.columns if c.lower() == "category"),
        None,
    )

    if not col_lc or not col_date:
        logger.warning("AppEEARS: columnas LC_Type1 o Date no encontradas en el CSV")
        return pd.DataFrame()

    df = df_raw[[col_id, col_date, col_lc]].copy()
    df.columns = ["punto", "fecha", "lc_type1"]

    df["fecha"]      = pd.to_datetime(df["fecha"], errors="coerce")
    df["anio"]       = df["fecha"].dt.year
    df["lc_type1"]   = pd.to_numeric(df["lc_type1"], errors="coerce").fillna(255).astype(int)
    df["lc_descripcion"] = df["lc_type1"].map(IGBP_LABELS).fillna("Sin clasificar")

    # País: tomamos de columna Category si existe, si no desde PUNTOS_METEO_SA
    if col_pais and col_pais in df_raw.columns:
        df["pais"] = df_raw[col_pais].values
    else:
        pais_map = {nombre: info["pais"] for nombre, info in PUNTOS_METEO_SA.items()}
        df["pais"] = df["punto"].map(pais_map).fillna("???")

    df["fuente"] = "MODIS_MCD12Q1_AppEEARS"

    return df[["punto", "pais", "anio", "lc_type1", "lc_descripcion", "fuente"]].drop_duplicates()


# =============================================================================
# BLOQUE DE EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SINIA-SA — Extractor MODIS Land Cover (NASA AppEEARS)")
    print("=" * 60)
    print(f"Fuente      : MODIS MCD12Q1 v6.1 vía NASA AppEEARS")
    print(f"Endpoint    : {APPEEARS_BASE_URL}")
    print(f"Producto    : {MODIS_PRODUCTO}  |  Variable: {MODIS_VARIABLE}")
    print(f"Resolución  : 500 m global, clasificación anual (IGBP)")
    print(f"Puntos conf : {list(PUNTOS_METEO_SA.keys())}")
    print(f"\nClases IGBP disponibles:")
    for codigo, descripcion in IGBP_LABELS.items():
        if codigo != 255:
            print(f"  {codigo:>3}  {descripcion}")

    if not APPEEARS_USER:
        print(
            "\n[ERROR] Credenciales AppEEARS no configuradas.\n"
            "  1. Crear cuenta en: https://urs.earthdata.nasa.gov/\n"
            "  2. Agregar a config/.env:\n"
            "       APPEEARS_USER=tu_usuario_earthdata\n"
            "       APPEEARS_PASSWORD=tu_password_earthdata\n"
        )
    else:
        print(f"\nUsuario AppEEARS : {APPEEARS_USER}")
        print(f"Período          : 2018  →  2024")
        print(f"N° puntos        : {len(PUNTOS_METEO_SA)}")
        print("\n" + "-" * 60)
        print("PASO 1 — Enviando solicitud de extracción a AppEEARS...")
        print("-" * 60)
        print("(AppEEARS es asíncrono: la solicitud se encola y procesa en segundo plano)\n")

        task_id = solicitar_cobertura_vegetal(anio_inicio=2018, anio_fin=2024)
        print(f"[OK] Solicitud enviada")
        print(f"     Task ID : {task_id}")
        print(f"\n" + "-" * 60)
        print("PASO 2 — Esperando resultado y descargando...")
        print("-" * 60)
        print("(Puede tardar entre 2 y 15 minutos según la carga del servidor)\n")

        df = descargar_resultado_appeears(task_id=task_id, max_minutos=30)

        if not df.empty:
            print(f"[OK] Registros descargados : {len(df)}")
            print(f"     Columnas              : {list(df.columns)}")
            print(f"     Puntos en resultado   : {sorted(df['punto'].unique().tolist())}")
            print(f"     Años en resultado     : {sorted(df['anio'].unique().tolist())}")
            print(f"\nDistribución de clases IGBP:")
            for lc, cnt in df["lc_descripcion"].value_counts().items():
                print(f"  {cnt:>5} registros  →  {lc}")
            print(f"\nPrimeras 10 filas:")
            print(df.head(10).to_string(index=False))
        else:
            print("[ERROR] Sin datos — revisar credenciales o el estado de la tarea.")
            print(f"  Para consultar manualmente: descargar_resultado_appeears('{task_id}')")

    print("\n" + "=" * 60)
    print("Extractor MODIS finalizado.")
    print("=" * 60)
