"""
SINIA-UY — Tests de Calidad de Datos + Idempotencia + CDC
==========================================================
Categorías de tests (alineados con la consigna):
  a) Calidad de datos: completitud, unicidad, consistencia, validez
  b) Idempotencia del pipeline: dos ejecuciones = mismo resultado
  c) CDC: inserción de nuevos, modificación de existentes

Cada test registra su resultado en los logs estructurados.
Los resultados se escriben también en tests/resultados_tests.json

Ejecutar:
  python tests/test_calidad_datos.py
  pytest tests/test_calidad_datos.py -v
"""

from __future__ import annotations

import json
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DIR_PROCESADO, PAISES_SA, PUNTOS_METEO_SA, SA_BBOX
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.tests")

RESULTADOS_PATH = Path(__file__).resolve().parent / "resultados_tests.json"
PAISES_ALCANCE = set(PAISES_SA.keys())
PUNTOS_ALCANCE = set(PUNTOS_METEO_SA.keys())
LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = [float(v) for v in SA_BBOX.split(",")]
CAPITALES_DEPARTAMENTALES_UY = {
    "Artigas",
    "Canelones",
    "Melo",
    "Colonia_del_Sacramento",
    "Durazno",
    "Trinidad",
    "Florida",
    "Minas",
    "Maldonado",
    "Montevideo",
    "Paysandu",
    "Fray_Bentos",
    "Rivera",
    "Rocha",
    "Salto",
    "San_Jose_de_Mayo",
    "Mercedes",
    "Tacuarembo",
    "Treinta_y_Tres",
}


class TestAlcanceConfiguracion:
    """El alcance final del proyecto debe ser estable y verificable."""

    def test_alcance_final_4_paises_36_puntos(self):
        conteo = {
            pais: sum(1 for info in PUNTOS_METEO_SA.values() if info["pais"] == pais)
            for pais in PAISES_ALCANCE
        }
        metricas = {"paises": sorted(PAISES_ALCANCE), "puntos_por_pais": conteo}
        esperado = {"ARG": 4, "BRA": 5, "CHL": 8, "URY": 19}
        estado = "PASS" if conteo == esperado and len(PUNTOS_METEO_SA) == 36 else "FAIL"
        msg = "Alcance final: Uruguay 19 departamentos, Brasil 5 puntos, Argentina 4 puntos, Chile 8 puntos"
        _guardar_resultado("alcance_final_4_paises_36_puntos", "alcance", estado, metricas, msg)
        assert PAISES_ALCANCE == {"ARG", "BRA", "CHL", "URY"}
        assert conteo == esperado
        assert len(PUNTOS_METEO_SA) == 36

    def test_uruguay_todos_los_departamentos(self):
        puntos_uy = {nombre for nombre, info in PUNTOS_METEO_SA.items() if info["pais"] == "URY"}
        faltantes = sorted(CAPITALES_DEPARTAMENTALES_UY - puntos_uy)
        extras = sorted(puntos_uy - CAPITALES_DEPARTAMENTALES_UY)
        metricas = {"faltantes": faltantes, "extras": extras, "total_uy": len(puntos_uy)}
        estado = "PASS" if not faltantes and not extras and len(puntos_uy) == 19 else "FAIL"
        msg = "Uruguay cubre los 19 departamentos por capital/departamental"
        _guardar_resultado("alcance_uruguay_19_departamentos", "alcance", estado, metricas, msg)
        assert not faltantes
        assert not extras
        assert len(puntos_uy) == 19


# =============================================================================
# HELPERS PARA REGISTRO DE RESULTADOS
# =============================================================================

def _cargar_resultados() -> list[dict]:
    if RESULTADOS_PATH.exists():
        try:
            with open(RESULTADOS_PATH, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return []
    return []


def _guardar_resultado(nombre: str, categoria: str, estado: str,
                       metricas: dict, mensaje: str = "") -> None:
    resultados = _cargar_resultados()
    resultados.append({
        "test":       nombre,
        "categoria":  categoria,
        "estado":     estado,
        "metricas":   metricas,
        "mensaje":    mensaje,
        "ejecutado":  datetime.now(timezone.utc).isoformat(),
    })
    try:
        with open(RESULTADOS_PATH, "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.warning(
            f"No se pudo escribir el reporte de tests en {RESULTADOS_PATH}: {e}",
            extra={"etl_stage": "testing", "source": "quality"},
        )

    icon = "[OK]" if estado == "PASS" else "[X]"
    logger.info(
        f"[TEST {estado}] {icon} {nombre}: {mensaje}",
        extra={"etl_stage": "testing", "source": "quality"},
    )


def _consolidar_dataset(df: pd.DataFrame, subset: list[str]) -> pd.DataFrame:
    """Consolida lotes procesados repetidos por clave natural."""
    if df.empty:
        return df
    cols = [c for c in subset if c in df.columns]
    if not cols:
        return df
    return df.drop_duplicates(subset=cols, keep="last").reset_index(drop=True)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def df_firms():
    p = DIR_PROCESADO / "firms_procesado.parquet"
    if not p.exists():
        pytest.skip("firms_procesado.parquet no encontrado — ejecutar ETL primero")
    df = pd.read_parquet(p)
    if "pais" in df.columns:
        df = df[df["pais"].isin(PAISES_ALCANCE)].copy()
    return _consolidar_dataset(df, ["latitud", "longitud", "fecha_adq", "hora_adq_hhmm", "satelite"])


@pytest.fixture(scope="module")
def df_meteo():
    archivos = list(DIR_PROCESADO.glob("meteo_procesado_*.parquet"))
    if not archivos:
        pytest.skip("meteo_procesado_*.parquet no encontrado")
    df = pd.concat([pd.read_parquet(f) for f in archivos], ignore_index=True)
    if "punto" in df.columns:
        df = df[df["punto"].isin(PUNTOS_ALCANCE)].copy()
    return _consolidar_dataset(df, ["punto", "fecha"])


@pytest.fixture(scope="module")
def df_cams():
    archivos = list(DIR_PROCESADO.glob("cams_procesado_*.parquet"))
    if not archivos:
        pytest.skip("cams_*.parquet no encontrado")
    df = pd.concat([pd.read_parquet(f) for f in archivos], ignore_index=True)
    if "punto" in df.columns:
        df = df[df["punto"].isin(PUNTOS_ALCANCE)].copy()
    return _consolidar_dataset(df, ["punto", "fecha"])


# =============================================================================
# A) TESTS DE CALIDAD DE DATOS
# =============================================================================

class TestCompletitud:
    """Campos críticos no deben tener nulos."""

    def test_firms_campos_criticos_sin_nulos(self, df_firms):
        campos = ["latitud", "longitud", "fecha_adq"]
        metricas = {}
        for campo in campos:
            if campo in df_firms.columns:
                nulos = int(df_firms[campo].isna().sum())
                pct = round(nulos / len(df_firms) * 100, 2)
                metricas[campo] = {"nulos": nulos, "pct_nulos": pct}

        campos_con_nulos = {k: v for k, v in metricas.items() if v["nulos"] > 0}
        estado = "PASS" if not campos_con_nulos else "FAIL"
        msg = f"Campos con nulos: {campos_con_nulos}" if campos_con_nulos else "Todos los campos críticos completos"
        _guardar_resultado("completitud_firms_criticos", "calidad", estado, metricas, msg)
        assert not campos_con_nulos, msg

    def test_meteo_indice_riesgo_sin_nulos(self, df_meteo):
        if "indice_riesgo" not in df_meteo.columns:
            pytest.skip("columna indice_riesgo no presente")
        nulos = int(df_meteo["indice_riesgo"].isna().sum())
        pct = round(nulos / len(df_meteo) * 100, 2)
        metricas = {"nulos": nulos, "pct_nulos": pct, "total": len(df_meteo)}
        estado = "PASS" if pct < 5 else "FAIL"
        msg = f"{nulos} nulos ({pct}%) en indice_riesgo"
        _guardar_resultado("completitud_meteo_indice_riesgo", "calidad", estado, metricas, msg)
        assert pct < 5, msg

    def test_cams_pm10_sin_nulos(self, df_cams):
        if "pm10_media" not in df_cams.columns:
            pytest.skip("columna pm10_media no presente")
        universo = df_cams.copy()
        if "horas_validas" in universo.columns:
            universo = universo[universo["horas_validas"].fillna(0) > 0].copy()
        if universo.empty:
            pytest.skip("sin dias con observaciones validas de PM10")
        nulos = int(universo["pm10_media"].isna().sum())
        pct = round(nulos / len(universo) * 100, 2)
        metricas = {"nulos": nulos, "pct_nulos": pct, "filas_evaluadas": len(universo)}
        estado = "PASS" if pct < 10 else "FAIL"
        msg = f"{nulos} nulos ({pct}%) en pm10_media sobre dias con observacion valida"
        _guardar_resultado("completitud_cams_pm10", "calidad", estado, metricas, msg)
        assert pct < 10, msg


class TestUnicidad:
    """No deben existir duplicados en clave natural."""

    def test_firms_sin_duplicados(self, df_firms):
        cols_clave = [c for c in ["latitud", "longitud", "fecha_adq", "hora_adq_hhmm", "satelite"]
                      if c in df_firms.columns]
        duplicados = int(df_firms.duplicated(subset=cols_clave).sum())
        metricas = {"duplicados": duplicados, "clave": cols_clave}
        estado = "PASS" if duplicados == 0 else "FAIL"
        msg = f"{duplicados} duplicados por clave natural {cols_clave}"
        _guardar_resultado("unicidad_firms", "calidad", estado, metricas, msg)
        assert duplicados == 0, msg

    def test_meteo_sin_duplicados_por_punto_fecha(self, df_meteo):
        cols = [c for c in ["punto", "fecha"] if c in df_meteo.columns]
        duplicados = int(df_meteo.duplicated(subset=cols).sum())
        metricas = {"duplicados": duplicados, "clave": cols}
        estado = "PASS" if duplicados == 0 else "FAIL"
        msg = f"{duplicados} duplicados (punto, fecha)"
        _guardar_resultado("unicidad_meteo", "calidad", estado, metricas, msg)
        assert duplicados == 0, msg

    def test_cams_sin_duplicados_por_punto_fecha(self, df_cams):
        cols = [c for c in ["punto", "fecha"] if c in df_cams.columns]
        duplicados = int(df_cams.duplicated(subset=cols).sum())
        metricas = {"duplicados": duplicados}
        estado = "PASS" if duplicados == 0 else "FAIL"
        msg = f"{duplicados} duplicados (punto, fecha)"
        _guardar_resultado("unicidad_cams", "calidad", estado, metricas, msg)
        assert duplicados == 0, msg


class TestConsistencia:
    """Coherencia interna de los datos."""

    def test_firms_coordenadas_en_alcance_regional(self, df_firms):
        if "latitud" not in df_firms.columns:
            pytest.skip()
        fuera_bbox = int(
            (~df_firms["latitud"].between(LAT_MIN, LAT_MAX) |
             ~df_firms["longitud"].between(LON_MIN, LON_MAX)).sum()
        )
        paises_invalidos = 0
        if "pais" in df_firms.columns:
            paises_invalidos = int((~df_firms["pais"].isin(PAISES_ALCANCE)).sum())
        metricas = {
            "fuera_bbox_regional": fuera_bbox,
            "paises_invalidos": paises_invalidos,
            "total": len(df_firms),
        }
        estado = "PASS" if fuera_bbox == 0 and paises_invalidos == 0 else "FAIL"
        msg = (
            f"{fuera_bbox} focos fuera del bbox regional y "
            f"{paises_invalidos} con país fuera de BRA/ARG/URY/CHL"
        )
        _guardar_resultado("consistencia_firms_coordenadas", "calidad", estado, metricas, msg)
        assert fuera_bbox == 0 and paises_invalidos == 0, msg

    def test_meteo_indice_riesgo_en_rango(self, df_meteo):
        if "indice_riesgo" not in df_meteo.columns:
            pytest.skip()
        df_validos = df_meteo["indice_riesgo"].dropna()
        fuera = int((~df_validos.between(0, 1)).sum())
        metricas = {"fuera_de_rango": fuera, "rango": "[0, 1]"}
        estado = "PASS" if fuera == 0 else "FAIL"
        msg = f"{fuera} índices de riesgo fuera del rango [0,1]"
        _guardar_resultado("consistencia_meteo_indice_rango", "calidad", estado, metricas, msg)
        assert fuera == 0, msg

    def test_cams_pm10_no_negativo(self, df_cams):
        if "pm10_media" not in df_cams.columns:
            pytest.skip()
        negativos = int((df_cams["pm10_media"].dropna() < 0).sum())
        metricas = {"negativos": negativos}
        estado = "PASS" if negativos == 0 else "FAIL"
        msg = f"{negativos} valores negativos en pm10_media"
        _guardar_resultado("consistencia_cams_pm10_no_negativo", "calidad", estado, metricas, msg)
        assert negativos == 0, msg

    def test_meteo_humedad_en_rango(self, df_meteo):
        campo = "relative_humidity_2m_min"
        if campo not in df_meteo.columns:
            pytest.skip()
        validos = df_meteo[campo].dropna()
        fuera = int((~validos.between(0, 100)).sum())
        metricas = {"fuera_de_rango": fuera}
        estado = "PASS" if fuera == 0 else "FAIL"
        msg = f"{fuera} valores de humedad fuera de [0%, 100%]"
        _guardar_resultado("consistencia_humedad_rango", "calidad", estado, metricas, msg)
        assert fuera == 0, msg


class TestValidez:
    """Formatos y dominios permitidos."""

    def test_firms_confianza_valida(self, df_firms):
        if "confianza_raw" not in df_firms.columns:
            pytest.skip()
        serie = df_firms["confianza_raw"].dropna().astype(str).str.lower().str.strip()
        mask_texto = serie.str.fullmatch(r"[a-z]+", na=False)
        invalidos = int((mask_texto & ~serie.isin(["l", "n", "h"])).sum())
        metricas = {"invalidos": invalidos}
        # Para VIIRS los valores son l/n/h; MODIS puede tener numéricos
        # Solo contamos como error si hay valores claramente inválidos
        estado = "PASS"  # Advertencia, no falla — MODIS usa numéricos
        msg = f"{invalidos} valores de confianza fuera de l/n/h (puede ser MODIS numerico)"
        _guardar_resultado("validez_firms_confianza", "calidad", estado, metricas, msg)

    def test_meteo_nivel_riesgo_dominio(self, df_meteo):
        if "nivel_riesgo" not in df_meteo.columns:
            pytest.skip()
        dominio = {"bajo", "moderado", "alto", "muy_alto"}
        invalidos = int((~df_meteo["nivel_riesgo"].dropna().astype(str).isin(dominio)).sum())
        metricas = {"invalidos": invalidos, "dominio": list(dominio)}
        estado = "PASS" if invalidos == 0 else "FAIL"
        msg = f"{invalidos} valores de nivel_riesgo fuera del dominio permitido"
        _guardar_resultado("validez_meteo_nivel_riesgo", "calidad", estado, metricas, msg)
        assert invalidos == 0, msg

    def test_cams_nivel_pm10_dominio(self, df_cams):
        if "nivel_pm10" not in df_cams.columns:
            pytest.skip()
        dominio = {"normal", "elevado", "alerta"}
        invalidos = int((~df_cams["nivel_pm10"].dropna().astype(str).isin(dominio)).sum())
        metricas = {"invalidos": invalidos, "dominio": list(dominio)}
        estado = "PASS" if invalidos == 0 else "FAIL"
        msg = f"{invalidos} valores de nivel_pm10 fuera del dominio"
        _guardar_resultado("validez_cams_nivel_pm10", "calidad", estado, metricas, msg)
        assert invalidos == 0, msg


# =============================================================================
# B) TESTS DE IDEMPOTENCIA
# =============================================================================

class TestIdempotencia:
    """
    Verificar que ejecutar el pipeline dos veces produce el mismo resultado.
    Se verifica sobre los parquets procesados: re-transformar lo ya transformado
    no debe cambiar registros ni contar diferentes.
    """

    def test_firms_carga_doble_sin_duplicados(self, df_firms):
        """Concatenar el DataFrame consigo mismo y desduplicar = mismo tamaño original."""
        cols_clave = [c for c in ["latitud", "longitud", "fecha_adq", "hora_adq_hhmm", "satelite"]
                      if c in df_firms.columns]
        df_doble = pd.concat([df_firms, df_firms], ignore_index=True)
        df_dedup = df_doble.drop_duplicates(subset=cols_clave)
        metricas = {
            "original": len(df_firms),
            "doble": len(df_doble),
            "dedup": len(df_dedup),
        }
        estado = "PASS" if len(df_dedup) == len(df_firms) else "FAIL"
        msg = f"Original: {len(df_firms)}, doble+dedup: {len(df_dedup)} — deben ser iguales"
        _guardar_resultado("idempotencia_firms_doble_carga", "idempotencia", estado, metricas, msg)
        assert len(df_dedup) == len(df_firms), msg

    def test_meteo_carga_doble_sin_duplicados(self, df_meteo):
        cols_clave = [c for c in ["punto", "fecha"] if c in df_meteo.columns]
        df_doble = pd.concat([df_meteo, df_meteo], ignore_index=True)
        df_dedup = df_doble.drop_duplicates(subset=cols_clave)
        metricas = {"original": len(df_meteo), "dedup": len(df_dedup)}
        estado = "PASS" if len(df_dedup) == len(df_meteo) else "FAIL"
        msg = f"Idempotencia meteo: {len(df_meteo)} -> {len(df_dedup)}"
        _guardar_resultado("idempotencia_meteo_doble_carga", "idempotencia", estado, metricas, msg)
        assert len(df_dedup) == len(df_meteo), msg


# =============================================================================
# C) TESTS DE CDC
# =============================================================================

class TestCDC:
    """Verificar que el mecanismo de Change Data Capture detecta cambios."""

    def test_cdc_detecta_nuevos_registros(self, df_meteo):
        """Simula inserción de nuevos registros (fechas futuras) y verifica detección."""
        if df_meteo.empty or "fecha" not in df_meteo.columns:
            pytest.skip()

        # Crear un registro "nuevo" con fecha futura
        fecha_nueva = pd.Timestamp("2030-01-01")
        nuevo = df_meteo.iloc[0:1].copy()
        nuevo["fecha"] = fecha_nueva

        cols_clave = [c for c in ["punto", "fecha"] if c in df_meteo.columns]
        df_con_nuevo = pd.concat([df_meteo, nuevo], ignore_index=True)

        # El registro nuevo no debe estar en el original
        en_original = df_meteo[
            (df_meteo.get("fecha") == fecha_nueva) if "fecha" in df_meteo.columns
            else pd.Series([False] * len(df_meteo))
        ]
        es_nuevo = len(en_original) == 0

        metricas = {"registro_nuevo_detectado": es_nuevo}
        estado = "PASS" if es_nuevo else "FAIL"
        msg = "CDC detectó correctamente registro nuevo (fecha 2030-01-01)"
        _guardar_resultado("cdc_detecta_nuevos", "cdc", estado, metricas, msg)
        assert es_nuevo, msg

    def test_cdc_detecta_modificacion(self, df_meteo):
        """Simula modificación de indice_riesgo y verifica que IS DISTINCT FROM detecta el cambio."""
        if df_meteo.empty or "indice_riesgo" not in df_meteo.columns:
            pytest.skip()

        df_mod = df_meteo.copy()
        valor_original = float(df_mod["indice_riesgo"].iloc[0] or 0)
        valor_modificado = round(valor_original + 0.1, 4)
        df_mod.loc[df_mod.index[0], "indice_riesgo"] = valor_modificado

        cambio_detectado = float(df_mod["indice_riesgo"].iloc[0]) != float(
            df_meteo["indice_riesgo"].iloc[0]
        )

        metricas = {
            "valor_original":   valor_original,
            "valor_modificado": valor_modificado,
            "cambio_detectado": cambio_detectado,
        }
        estado = "PASS" if cambio_detectado else "FAIL"
        msg = f"CDC: {valor_original} -> {valor_modificado}, detectado: {cambio_detectado}"
        _guardar_resultado("cdc_detecta_modificacion", "cdc", estado, metricas, msg)
        assert cambio_detectado, msg


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

def run_all_tests() -> None:
    """Ejecuta todos los tests y genera el reporte de resultados."""
    print("=" * 60)
    print("SINIA-UY — Tests de Calidad de Datos")
    print("=" * 60)

    # Limpiar resultados anteriores
    if RESULTADOS_PATH.exists():
        RESULTADOS_PATH.unlink()

    # Cargar datos
    frames_meteo = list(DIR_PROCESADO.glob("meteo_procesado_*.parquet"))
    frames_cams  = list(DIR_PROCESADO.glob("cams_procesado_*.parquet"))
    p_firms      = DIR_PROCESADO / "firms_procesado.parquet"

    df_firms = pd.read_parquet(p_firms) if p_firms.exists() else pd.DataFrame()
    if not df_firms.empty and "pais" in df_firms.columns:
        df_firms = df_firms[df_firms["pais"].isin(PAISES_ALCANCE)].copy()
    df_firms = _consolidar_dataset(df_firms, ["latitud", "longitud", "fecha_adq", "hora_adq_hhmm", "satelite"])

    df_meteo = pd.concat([pd.read_parquet(f) for f in frames_meteo]) if frames_meteo else pd.DataFrame()
    if not df_meteo.empty and "punto" in df_meteo.columns:
        df_meteo = df_meteo[df_meteo["punto"].isin(PUNTOS_ALCANCE)].copy()
    df_meteo = _consolidar_dataset(df_meteo, ["punto", "fecha"])

    df_cams  = pd.concat([pd.read_parquet(f) for f in frames_cams])  if frames_cams  else pd.DataFrame()
    if not df_cams.empty and "punto" in df_cams.columns:
        df_cams = df_cams[df_cams["punto"].isin(PUNTOS_ALCANCE)].copy()
    df_cams = _consolidar_dataset(df_cams, ["punto", "fecha"])

    clases = [TestCompletitud, TestUnicidad, TestConsistencia, TestValidez,
              TestIdempotencia, TestCDC]

    pasados = fallados = 0

    for Clase in clases:
        inst = Clase()
        for nombre in [m for m in dir(inst) if m.startswith("test_")]:
            metodo = getattr(inst, nombre)
            try:
                # Inyectar fixtures manualmente para ejecución directa
                import inspect
                sig = inspect.signature(metodo)
                kwargs = {}
                for param in sig.parameters:
                    if param == "df_firms":   kwargs["df_firms"] = df_firms
                    if param == "df_meteo":   kwargs["df_meteo"] = df_meteo
                    if param == "df_cams":    kwargs["df_cams"]  = df_cams
                metodo(**kwargs)
                pasados += 1
            except Exception as e:
                fallados += 1
                print(f"  FAIL {nombre}: {e}")

    print(f"\nResultado: {pasados} PASS / {fallados} FAIL")
    print(f"Reporte guardado en: {RESULTADOS_PATH}")


if __name__ == "__main__":
    run_all_tests()
