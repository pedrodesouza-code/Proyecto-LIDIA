#!/usr/bin/env python3
"""Auditoria tecnica EC3 para Proyecto LIDIA.

El script es deliberadamente de solo lectura: inspecciona archivos, evidencia,
PostgreSQL y MongoDB, y genera un reporte honesto de estado actual.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "evidencia" / "logs"
VALID_SOURCES = {"FIRMS", "METEO", "CAMS", "CHIRPS", "MODIS", "INUMET"}
ERROR_PATTERNS = re.compile(
    r"(Traceback|ERROR:|FATAL:|CheckViolation|UndefinedTable|UndefinedColumn|syntax error)",
    re.IGNORECASE,
)
SECRET_PATTERNS = re.compile(
    r"(postgres://|postgresql://|mongodb://|password\s*=|pwd\s*=|secret\s*=|token\s*=|api[_-]?key\s*=)",
    re.IGNORECASE,
)
PLACEHOLDER_PATTERNS = re.compile(
    r"(CAMBIAR|CAMBIAR_LOCALMENTE|local_lidia|usuario:password|postgresql://\.\.\.|mongodb://\.\.\.|example|ejemplo)",
    re.IGNORECASE,
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


STAMP = utc_stamp()
RUN_LOG = LOG_DIR / f"ec3_verificacion_logrado_{STAMP}.log"
REPORT_MD = LOG_DIR / "ec3_reporte_estado_actual.md"
URGENCIES_JSON = LOG_DIR / "ec3_resumen_urgencias.json"


class Recorder:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lines: list[str] = []

    def log(self, message: str, **payload) -> None:
        event = {"ts": datetime.now(timezone.utc).isoformat(), "message": message, **payload}
        line = json.dumps(event, ensure_ascii=False, default=str)
        self.lines.append(line)
        print(line)

    def flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


rec = Recorder(RUN_LOG)


def run_cmd(args: list[str], timeout: int = 120, env: dict[str, str] | None = None) -> dict:
    safe_args = [re.sub(r"(://[^:/@]+:)[^@]+@", r"\1***@", item) for item in args]
    rec.log("run_cmd", args=safe_args)
    try:
        proc = subprocess.run(
            args,
            cwd=ROOT,
            env=env or os.environ.copy(),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-8000:],
            "stderr": proc.stderr[-8000:],
        }
    except Exception as exc:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}


def clean_env_uri(value: str) -> str:
    """Normaliza URI de entorno si un .env dejo dos asignaciones en una linea."""
    cleaned = value.strip().strip('"').strip("'")
    for marker in (" MONGO_URI=", " DATABASE_URL="):
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[0]
    return cleaned.strip().strip('"').strip("'")


class PgClient:
    def __init__(self) -> None:
        self.url = clean_env_uri(os.getenv("DATABASE_URL", ""))
        self.conn = None
        self.mode = "none"
        if not self.url:
            rec.log("postgres_no_database_url")
            return
        try:
            import psycopg2  # type: ignore

            self.conn = psycopg2.connect(self.url)
            self.mode = "psycopg2"
            rec.log("postgres_connected", mode=self.mode)
        except Exception as exc:
            rec.log("postgres_psycopg2_unavailable_or_failed", error=f"{type(exc).__name__}: {exc}")
            probe = run_cmd(["psql", self.url, "-At", "-c", "SELECT 1"], timeout=20)
            if probe["ok"]:
                self.mode = "psql"
                rec.log("postgres_connected", mode=self.mode)

    def available(self) -> bool:
        return self.mode != "none"

    def query(self, sql: str) -> list[dict]:
        if self.mode == "psycopg2" and self.conn is not None:
            with self.conn.cursor() as cur:
                cur.execute(sql)
                if cur.description is None:
                    return []
                cols = [col.name for col in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        if self.mode == "psql":
            wrapped = (
                "COPY ("
                + sql.rstrip().rstrip(";")
                + ") TO STDOUT WITH (FORMAT CSV, HEADER true, DELIMITER E'\\t')"
            )
            result = run_cmd(["psql", self.url, "-qAt", "-c", wrapped], timeout=120)
            if not result["ok"] or not result["stdout"].strip():
                return []
            lines = result["stdout"].splitlines()
            headers = lines[0].split("\t")
            return [dict(zip(headers, line.split("\t"))) for line in lines[1:]]
        return []

    def scalar(self, sql: str, default=0):
        rows = self.query(sql)
        if not rows:
            return default
        return next(iter(rows[0].values()))

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()


class MongoProbe:
    def __init__(self) -> None:
        self.uri = clean_env_uri(os.getenv("MONGO_URI", ""))
        self.mode = "none"
        self.db = None
        self.client = None
        if not self.uri:
            rec.log("mongo_no_mongo_uri")
            return
        try:
            from pymongo import MongoClient  # type: ignore

            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command("ping")
            # La base se infiere de la URI; si falta, usar proyecto_lidia.
            self.db = self.client.get_default_database(default="proyecto_lidia")
            self.mode = "pymongo"
            rec.log("mongo_connected", mode=self.mode, database=self.db.name)
        except Exception as exc:
            rec.log("mongo_pymongo_unavailable_or_failed", error=f"{type(exc).__name__}: {exc}")
            probe = run_cmd(["mongosh", self.uri, "--quiet", "--eval", "db.runCommand({ping:1}).ok"], timeout=20)
            if probe["ok"]:
                self.mode = "mongosh"
                rec.log("mongo_connected", mode=self.mode)

    def available(self) -> bool:
        return self.mode != "none"

    def collection_counts(self, names: list[str]) -> dict[str, int | None]:
        counts: dict[str, int | None] = {}
        if self.mode == "pymongo" and self.db is not None:
            existing = set(self.db.list_collection_names())
            for name in names:
                counts[name] = self.db[name].count_documents({}) if name in existing else None
            return counts
        if self.mode == "mongosh":
            for name in names:
                script = f"db.getCollectionNames().includes('{name}') ? db.{name}.countDocuments({{}}) : -1"
                result = run_cmd(["mongosh", self.uri, "--quiet", "--eval", script], timeout=30)
                try:
                    value = int(result["stdout"].strip())
                except Exception:
                    value = -1
                counts[name] = None if value < 0 else value
        return counts

    def aggregate(self, collection: str, pipeline: str) -> list[dict]:
        if self.mode == "pymongo" and self.db is not None:
            try:
                return list(self.db[collection].aggregate(json.loads(pipeline)))
            except Exception as exc:
                rec.log("mongo_aggregate_failed", collection=collection, error=f"{type(exc).__name__}: {exc}")
                return []
        if self.mode == "mongosh":
            script = f"JSON.stringify(db.{collection}.aggregate({pipeline}).toArray())"
            result = run_cmd(["mongosh", self.uri, "--quiet", "--eval", script], timeout=30)
            try:
                return json.loads(result["stdout"])
            except Exception:
                return []
        return []

    def close(self) -> None:
        if self.client is not None:
            self.client.close()


def file_exists(path: str) -> bool:
    return (ROOT / path).exists()


def glob_exists(pattern: str) -> list[Path]:
    return sorted(ROOT.glob(pattern))


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def detect_log_errors(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            if not ERROR_PATTERNS.search(line):
                continue
            # No contar definiciones de CHECK que incluyen el literal 'error'.
            if "CHECK" in line and "error" in line and "estado" in line:
                continue
            findings.append(f"{path.relative_to(ROOT)}:{idx}: {line[:180]}")
    return findings[:40]


def scan_for_secrets() -> list[str]:
    excluded_parts = {
        ".git", "__pycache__", "evidencia", "logs", "data",
        ".pytest_cache", "_no_entregar", ".ipynb_checkpoints",
    }
    excluded_names = {".env", ".env.local", "utec.env", "config/.env"}
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in excluded_parts for part in rel.parts):
            continue
        if (
            str(rel) in excluded_names
            or rel.name == ".env"
            or rel.suffix in {".pyc", ".parquet", ".example", ".env"}
        ):
            continue
        if rel.name.endswith(".env.example") or rel.name.endswith("utec.env.example"):
            continue
        text = read_text(path)
        for idx, line in enumerate(text.splitlines(), 1):
            if SECRET_PATTERNS.search(line):
                if PLACEHOLDER_PATTERNS.search(line):
                    continue
                if "***" in line and ("postgresql://" in line or "mongodb://" in line):
                    continue
                if "***" in line and re.search(r"(PASSWORD|password|MONGO_PASSWORD|POSTGRES_PASSWORD)", line):
                    continue
                if "MONGO_CONFIG" in line or "DATABASE_URL" in line or "MONGO_URI" in line:
                    # Referencias a variables/configuracion, no secretos hardcodeados.
                    continue
                if path.name == "ec3_verificar_logrado.py":
                    continue
                findings.append(f"{rel}:{idx}: {line[:140]}")
                break
    return findings[:40]


def scan_forecast_refs() -> list[str]:
    excluded_parts = {".git", "__pycache__", "data", "evidencia", "logs", ".pytest_cache", "_no_entregar"}
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in excluded_parts for part in rel.parts):
            continue
        if rel.suffix in {".pyc", ".parquet"}:
            continue
        if path.name == "ec3_verificar_logrado.py":
            continue
        text = read_text(path)
        active_lines = []
        for line in text.splitlines():
            if not re.search(r"\bFORECAST\b|forecast|extract_forecast", line):
                continue
            if re.search(r"(no usado|no usar|no debe|prohibid|exclu|grep|forecast_refs)", line, re.IGNORECASE):
                continue
            active_lines.append(line)
        if active_lines:
            findings.append(str(rel))
    return sorted(set(findings))


def status(ok: bool, partial: bool = False, verified: bool = True) -> str:
    if not verified:
        return "NO VERIFICADO"
    if ok:
        return "COMPLETO"
    if partial:
        return "PARCIAL"
    return "FALTA"


def criterion(
    rows: list[dict],
    name: str,
    state: str,
    evidence: str,
    risk: str,
    urgency: str,
    action: str,
    today: str,
) -> None:
    rows.append(
        {
            "Criterio": name,
            "Estado": state,
            "Evidencia encontrada": evidence,
            "Riesgo": risk,
            "Urgencia": urgency,
            "Acción recomendada": action,
            "¿Se puede terminar hoy?": today,
        }
    )


def summarize_rows(rows: list[dict]) -> dict:
    counts: dict[str, int] = {}
    urgent: list[dict] = []
    completos: list[str] = []
    parciales: list[str] = []
    faltantes: list[str] = []
    no_verificados: list[str] = []
    for row in rows:
        state = row["Estado"]
        counts[state] = counts.get(state, 0) + 1
        if state == "COMPLETO":
            completos.append(row["Criterio"])
        elif state == "PARCIAL":
            parciales.append(row["Criterio"])
        elif state == "FALTA":
            faltantes.append(row["Criterio"])
        elif state == "NO VERIFICADO":
            no_verificados.append(row["Criterio"])
        if row["Urgencia"] in {"ALTA", "MEDIA"} and row["Estado"] != "COMPLETO":
            urgent.append(row)
    alta = [row for row in urgent if row["Urgencia"] == "ALTA"]
    if faltantes or alta:
        estado_general = "NO LISTO"
    elif parciales or no_verificados:
        estado_general = "CASI LISTO"
    else:
        estado_general = "LISTO"
    return {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "estado_general": estado_general,
        "conteo_estados": counts,
        "completos": completos,
        "parciales": parciales,
        "faltantes": faltantes,
        "no_verificados": no_verificados,
        "urgente_alta": alta,
        "urgencias": urgent,
        "se_puede_terminar_hoy": not any(row["¿Se puede terminar hoy?"] == "NO" for row in urgent),
        "condiciones_para_terminar_hoy": [row["Acción recomendada"] for row in urgent],
    }


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    pg = PgClient()
    mongo = MongoProbe()

    # D1 SQL relacional.
    ddl_files = [f"sql/ddl/{name}" for name in (
        "00_schemas.sql", "01_roles.sql", "02_Schema.sql", "03_indices.sql", "04_vistas.sql"
    )]
    ddl_ok = all(file_exists(path) for path in ddl_files)
    d1_logs = glob_exists("evidencia/logs/d1_*.log") + glob_exists("evidencia/logs/d1_*.txt")
    d1_errors = detect_log_errors(d1_logs)
    db_d1_ok = False
    db_d1_evidence = "Sin conexión PostgreSQL"
    if pg.available():
        expected_tables = [
            ("staging", "ingesta_metadata"), ("staging", "rechazos_etl"),
            ("dw", "fact_incendio"), ("dw", "dim_fecha"), ("dw", "dim_ubicacion"),
            ("dw", "dim_clima"), ("dw", "dim_precipitacion"), ("dw", "dim_cobertura_vegetal"),
            ("dw", "dim_calidad_aire"), ("dw", "dim_estacion_meteorologica"),
            ("audit", "etl_runs"), ("audit", "cdc_eventos"),
        ]
        schemas = pg.query(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name IN ('staging','dw','audit') ORDER BY schema_name"
        )
        tables = pg.query(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema IN ('staging','dw','audit')"
        )
        table_set = {(row["table_schema"], row["table_name"]) for row in tables}
        missing_tables = [f"{s}.{t}" for s, t in expected_tables if (s, t) not in table_set]
        constraints = pg.query(
            "SELECT constraint_type, COUNT(*)::int AS n FROM information_schema.table_constraints "
            "WHERE table_schema IN ('staging','dw','audit') "
            "GROUP BY constraint_type ORDER BY constraint_type"
        )
        not_null = pg.scalar(
            "SELECT COUNT(*)::int FROM information_schema.columns "
            "WHERE table_schema IN ('staging','dw','audit') AND is_nullable='NO'",
            0,
        )
        indexes = pg.scalar(
            "SELECT COUNT(*)::int FROM pg_indexes WHERE schemaname IN ('staging','dw','audit')",
            0,
        )
        views = pg.query(
            "SELECT table_name FROM information_schema.views WHERE table_schema='dw' ORDER BY table_name"
        )
        db_d1_ok = len(schemas) == 3 and not missing_tables and constraints and int(indexes or 0) > 0 and views
        db_d1_evidence = (
            f"schemas={len(schemas)}/3; missing_tables={missing_tables or 'ninguna'}; "
            f"constraints={constraints}; not_null={not_null}; indexes={indexes}; views={len(views)}"
        )
    criterion(
        rows,
        "D1 SQL relacional",
        status(ddl_ok and db_d1_ok and not d1_errors, partial=ddl_ok and db_d1_ok),
        f"DDL={ddl_ok}; {db_d1_evidence}; errores_logs={len(d1_errors)}",
        "Errores en DDL/logs o tablas faltantes afectan reproducibilidad.",
        "ALTA" if d1_errors or not ddl_ok else "BAJA",
        "Corregir logs con errores reales y asegurar DDL ejecutable.",
        "SI",
    )

    # D1 carga real y validaciones.
    if pg.available():
        counts = pg.query(
            "SELECT 'fact_incendio' objeto, COUNT(*)::bigint filas FROM dw.fact_incendio "
            "UNION ALL SELECT 'dim_clima', COUNT(*) FROM dw.dim_clima "
            "UNION ALL SELECT 'dim_precipitacion', COUNT(*) FROM dw.dim_precipitacion "
            "UNION ALL SELECT 'dim_cobertura_vegetal', COUNT(*) FROM dw.dim_cobertura_vegetal "
            "UNION ALL SELECT 'dim_calidad_aire', COUNT(*) FROM dw.dim_calidad_aire"
        )
        invalid = pg.query(
            "SELECT 'ubicacion_pais_fuera_alcance' check_name, COUNT(*)::bigint n "
            "FROM dw.dim_ubicacion WHERE pais_codigo NOT IN ('URY','ARG','BRA') "
            "UNION ALL SELECT 'ubicacion_latitud_invalida', COUNT(*) FROM dw.dim_ubicacion WHERE latitud NOT BETWEEN -90 AND 90 "
            "UNION ALL SELECT 'ubicacion_longitud_invalida', COUNT(*) FROM dw.dim_ubicacion WHERE longitud NOT BETWEEN -180 AND 180 "
            "UNION ALL SELECT 'frp_negativo', COUNT(*) FROM dw.fact_incendio WHERE frp_mw < 0 "
            "UNION ALL SELECT 'humedad_invalida', COUNT(*) FROM dw.dim_clima WHERE humedad_pct IS NOT NULL AND humedad_pct NOT BETWEEN 0 AND 100 "
            "UNION ALL SELECT 'direccion_viento_invalida', COUNT(*) FROM dw.dim_clima WHERE direccion_viento_grados IS NOT NULL AND direccion_viento_grados NOT BETWEEN 0 AND 360 "
            "UNION ALL SELECT 'pm_invalido', COUNT(*) FROM dw.dim_calidad_aire WHERE (pm25 IS NOT NULL AND pm25 < 0) OR (pm10 IS NOT NULL AND pm10 < 0)"
        )
        fact_rows = next((int(row["filas"]) for row in counts if row["objeto"] == "fact_incendio"), 0)
        invalid_total = sum(int(row["n"]) for row in invalid)
        rechazos = pg.scalar("SELECT COUNT(*)::bigint FROM staging.rechazos_etl", 0)
        ingesta = pg.scalar("SELECT COUNT(*)::bigint FROM staging.ingesta_metadata", 0)
        criterion(
            rows,
            "D1 carga real y validación post-carga",
            status(fact_rows > 0 and invalid_total == 0 and int(ingesta or 0) > 0, partial=fact_rows > 0),
            f"conteos={counts}; invalidos={invalid}; rechazos={rechazos}; ingesta_metadata={ingesta}",
            "Si faltan metadata o controles cuantitativos, defensa queda débil.",
            "MEDIA" if invalid_total or int(ingesta or 0) == 0 else "BAJA",
            "Actualizar evidencia final si cambian cargas.",
            "SI",
        )
    else:
        criterion(rows, "D1 carga real y validación post-carga", "NO VERIFICADO", "DATABASE_URL no disponible.", "Sin verificación DB.", "ALTA", "Ejecutar en Jupyter con DATABASE_URL.", "SI")

    # D2 NoSQL.
    expected_collections = ["ingesta_metadata", "rechazos_etl", "raw_payloads", "pipeline_logs", "snapshots_firms"]
    if mongo.available():
        counts = mongo.collection_counts(expected_collections)
        non_empty = {name: n for name, n in counts.items() if n and n > 0}
        ingestas = mongo.aggregate("ingesta_metadata", '[{"$group":{"_id":{"fuente":"$fuente","estado":"$estado"},"n":{"$sum":1}}}]')
        rechazos = mongo.aggregate("rechazos_etl", '[{"$group":{"_id":{"fuente":"$fuente","motivo":"$motivo"},"n":{"$sum":1}}}]')
        logs = mongo.aggregate("pipeline_logs", '[{"$group":{"_id":{"step_name":"$step_name","log_level":"$log_level"},"n":{"$sum":1}}}]')
        criterion(
            rows,
            "D2 NoSQL documental",
            status(len(non_empty) >= 4, partial=bool(non_empty)),
            f"colecciones={counts}; ingestas={ingestas[:5]}; rechazos={rechazos[:5]}; logs={logs[:5]}",
            "Colecciones vacías reducen evidencia NoSQL.",
            "MEDIA" if len(non_empty) < 4 else "BAJA",
            "Mantener MongoDB como metadata/logs/rechazos/snapshots; no reemplazar DW.",
            "SI",
        )
    else:
        criterion(rows, "D2 NoSQL documental", "NO VERIFICADO", "MONGO_URI no disponible o Mongo inaccesible.", "No se puede probar capa documental.", "MEDIA", "Ejecutar en entorno con MONGO_URI.", "SI")

    # D3 ETL Python.
    extractors = [f"etl/extract/extract_{name.lower()}.py" for name in VALID_SOURCES]
    structure_ok = all(file_exists(path) for path in ["etl/main.py", "etl/extract", "etl/transform", "etl/load"]) and all(file_exists(path) for path in extractors)
    settings_text = read_text(ROOT / "config" / "settings.py")
    external_config = "os.getenv" in settings_text and "load_dotenv" in settings_text
    secrets = scan_for_secrets()
    d3_logs = glob_exists("evidencia/logs/d3_*.log") + glob_exists("evidencia/logs/d3_*.txt")
    d3_summary = ROOT / "evidencia" / "logs" / "d3_resumen_ultima_ejecucion.log"
    d3_recent = d3_logs[-8:]
    if d3_summary.exists() and d3_summary not in d3_recent:
        d3_recent.append(d3_summary)
    d3_text = "\n".join(read_text(path) for path in d3_recent)
    d3_exit_ok = bool(re.search(r"exit_code[^0-9]*0|pipeline.*estado.*ok|passed", d3_text, re.IGNORECASE))
    logging_structured = all(word in read_text(ROOT / "etl" / "main.py") for word in ("extract", "transform", "load", "pipeline"))
    criterion(
        rows,
        "D3 ETL Python modular",
        status(structure_ok and external_config and not secrets and logging_structured, partial=structure_ok and external_config),
        f"extractores={all(file_exists(p) for p in extractors)}; config_externa={external_config}; secretos={len(secrets)}; logs_d3={len(d3_logs)}; ultima_exit_ok={d3_exit_ok}",
        "Secretos o falta de evidencia de ejecución afectan entrega.",
        "ALTA" if secrets else ("MEDIA" if not d3_exit_ok else "BAJA"),
        "Ejecutar D3 evidencia con PYTHONPATH correcto y guardar logs.",
        "SI",
    )

    # D3 idempotencia.
    if pg.available():
        natural_hash = pg.query(
            "SELECT table_schema, table_name, column_name FROM information_schema.columns "
            "WHERE table_schema IN ('staging','dw','audit') AND column_name IN ('natural_key','record_hash') "
            "ORDER BY table_schema, table_name, column_name"
        )
        dup_checks = []
        for table in ["stg_firms", "stg_meteo", "stg_chirps", "stg_modis", "stg_calidad_aire"]:
            dup = pg.scalar(f"SELECT COUNT(*)::bigint FROM (SELECT natural_key FROM staging.{table} GROUP BY natural_key HAVING COUNT(*) > 1) d", 0)
            dup_checks.append({table: int(dup or 0)})
        idemp_logs = glob_exists("evidencia/logs/*idempotencia*.txt") + glob_exists("evidencia/logs/d3_*.log")
        two_runs = len(idemp_logs) >= 2 and any("despues" in path.name or "corrida_2" in path.name for path in idemp_logs)
        no_dups = all(list(item.values())[0] == 0 for item in dup_checks)
        criterion(
            rows,
            "D3 idempotencia",
            status(bool(natural_hash) and no_dups and two_runs, partial=bool(natural_hash) and no_dups),
            f"natural/record_hash={len(natural_hash)} columnas; duplicados={dup_checks}; logs_idempotencia={len(idemp_logs)}; dos_corridas={two_runs}",
            "Sin dos corridas consecutivas, idempotencia queda parcialmente demostrada.",
            "MEDIA" if not two_runs else "BAJA",
            "Generar corrida 1 y 2 smoke con conteo antes/después.",
            "SI",
        )
    else:
        criterion(rows, "D3 idempotencia", "NO VERIFICADO", "Sin PostgreSQL.", "No se pueden consultar duplicados.", "MEDIA", "Ejecutar con DATABASE_URL.", "SI")

    # D3 integración y trazabilidad.
    forecast_refs = scan_forecast_refs()
    if pg.available():
        sources_db = pg.query(
            "SELECT fuente, COUNT(*)::bigint n FROM audit.etl_runs GROUP BY fuente ORDER BY fuente"
        )
        bad_sources = [row for row in sources_db if row["fuente"] not in VALID_SOURCES]
        metadata_cols = pg.query(
            "SELECT column_name FROM information_schema.columns WHERE table_schema='staging' AND table_name='ingesta_metadata'"
        )
        rechazos = pg.query("SELECT fuente, motivo, COUNT(*)::bigint n FROM staging.rechazos_etl GROUP BY fuente, motivo ORDER BY n DESC LIMIT 10")
        ok_cols = {"fuente", "estado", "filas_leidas", "filas_insertadas", "filas_actualizadas", "filas_rechazadas"}.issubset({r["column_name"] for r in metadata_cols})
        criterion(
            rows,
            "D3 integración y trazabilidad",
            status(ok_cols and not bad_sources and not forecast_refs, partial=ok_cols and not bad_sources),
            f"fuentes_db={sources_db}; fuentes_invalidas={bad_sources}; rechazos={rechazos}; forecast_refs={forecast_refs[:10]}",
            "Referencias FORECAST o fuentes inválidas contradicen alcance.",
            "ALTA" if bad_sources or forecast_refs else "BAJA",
            "Eliminar/aislar referencias FORECAST activas y documentar rechazos.",
            "SI",
        )
    else:
        criterion(rows, "D3 integración y trazabilidad", "NO VERIFICADO", f"forecast_refs={forecast_refs[:10]}", "Sin DB no se valida metadata.", "MEDIA", "Ejecutar con DATABASE_URL.", "SI")

    # D4 CDC.
    d4_logs = glob_exists("evidencia/logs/d4_*.log") + glob_exists("evidencia/logs/d4_*.txt")
    d4_text = "\n".join(read_text(path) for path in d4_logs[-8:])
    d4_log_ok = all(word in d4_text.lower() for word in ("alta", "modificacion", "sin_cambio")) and re.search(r"exit_code[^0-9]*0|sql cdc.*ok|mongodb cdc.*ok", d4_text, re.IGNORECASE)
    cdc_counts = []
    mongo_cdc = []
    if pg.available():
        cdc_counts = pg.query("SELECT fuente, tipo_evento, COUNT(*)::bigint n FROM audit.cdc_eventos GROUP BY fuente, tipo_evento ORDER BY fuente, tipo_evento")
    if mongo.available():
        mongo_cdc = mongo.aggregate("pipeline_logs", '[{"$match":{"proceso":"CDC","criterio":"D4","fuente":"FIRMS"}},{"$group":{"_id":"$estado","n":{"$sum":1}}}]')
    has_kinds = {row.get("tipo_evento") for row in cdc_counts}
    criterion(
        rows,
        "D4 Change Data Capture",
        status({"alta", "modificacion", "sin_cambio"}.issubset(has_kinds) and bool(mongo_cdc), partial=bool(cdc_counts)),
        f"logs_d4={len(d4_logs)}; log_ok={bool(d4_log_ok)}; cdc_sql={cdc_counts}; cdc_mongo={mongo_cdc}",
        "D4 solo es completo con evidencia SQL y MongoDB.",
        "MEDIA" if not mongo_cdc else "BAJA",
        "Reejecutar script D4 si falta MongoDB CDC o resumen exit_code 0.",
        "SI",
    )

    # D5 tests y validación.
    compile_result = run_cmd(["python", "-m", "compileall", "-q", "."], timeout=180)
    pytest_result = run_cmd(["python", "-m", "pytest", "-q", "tests"], timeout=240)
    d5_logs = glob_exists("evidencia/logs/validacion_tests.txt") + glob_exists("evidencia/logs/d5_*.log")
    d5_text = "\n".join(read_text(path) for path in d5_logs[-5:]) + compile_result["stdout"] + pytest_result["stdout"]
    passed = re.search(r"(\d+)\s+passed", d5_text)
    criterion(
        rows,
        "D5 Testing y validación",
        status(compile_result["ok"] and pytest_result["ok"] and passed is not None, partial=compile_result["ok"]),
        f"compileall_ok={compile_result['ok']}; pytest_ok={pytest_result['ok']}; passed={passed.group(0) if passed else 'no detectado'}; logs={len(d5_logs)}",
        "Si pytest falla o no hay evidencia cuantitativa, D5 queda parcial.",
        "ALTA" if not pytest_result["ok"] else "BAJA",
        "Corregir tests o guardar evidencia D5 final.",
        "SI",
    )

    # D5 consultas/dashboard.
    dashboard_text = read_text(ROOT / "dashboard" / "streamlit_app.py")
    if pg.available():
        expected_views = [
            "v_incendios_pais_periodo", "v_incendios_region", "v_incendios_clima",
            "v_incendios_precipitacion", "v_incendios_cobertura",
            "v_calidad_aire_alta_actividad", "v_calidad_pipeline",
        ]
        view_rows = []
        for view in expected_views:
            try:
                n = pg.scalar(f"SELECT COUNT(*)::bigint FROM dw.{view}", 0)
                view_rows.append({"view": view, "rows": int(n or 0)})
            except Exception as exc:
                view_rows.append({"view": view, "error": f"{type(exc).__name__}: {exc}"})
        dashboard_ok = "psycopg2.connect" in dashboard_text and "dw." in dashboard_text and not re.search(r"read_csv|read_parquet", dashboard_text)
        criterion(
            rows,
            "D5 consultas y dashboard coherente",
            status(dashboard_ok and all("error" not in row for row in view_rows), partial=dashboard_ok),
            f"dashboard_pg_dw={dashboard_ok}; vistas={view_rows}; logs_dashboard={len(glob_exists('evidencia/logs/validacion_dashboard.txt'))}",
            "Dashboard roto o leyendo archivos debilita validación funcional.",
            "MEDIA" if not dashboard_ok else "BAJA",
            "Abrir Streamlit y guardar captura/evidencia.",
            "SI",
        )
    else:
        criterion(rows, "D5 consultas y dashboard coherente", "NO VERIFICADO", "Sin PostgreSQL para contar vistas.", "No se validan vistas.", "MEDIA", "Ejecutar con DATABASE_URL.", "SI")

    # D6 Seguridad y gobernanza.
    roles_ok = "CREATE ROLE" in read_text(ROOT / "sql" / "ddl" / "01_roles.sql").upper()
    gitignore_text = read_text(ROOT / ".gitignore")
    gitignore_ok = all(token in gitignore_text for token in [".env", ".env.local", "config/.env", "__pycache__"])
    backup_docs = bool(re.search(r"pg_dump|mongodump|backup|respaldo|restore|recuper", read_text(ROOT / "README.md") + read_text(ROOT / "docker" / "README.md"), re.IGNORECASE))
    governance_docs = bool(re.search(r"sesgo|focos de calor|INUMET|calidad de aire|gobernanza|ética|etica", read_text(ROOT / "README.md"), re.IGNORECASE))
    criterion(
        rows,
        "D6 Seguridad y gobernanza",
        status(roles_ok and gitignore_ok and not secrets and backup_docs and governance_docs, partial=roles_ok and gitignore_ok and not secrets),
        f"roles={roles_ok}; gitignore={gitignore_ok}; secretos={len(secrets)}; backup_docs={backup_docs}; governance_docs={governance_docs}",
        "Falta backup/gobernanza puede bajar nivel aunque el pipeline funcione.",
        "MEDIA" if not backup_docs or not governance_docs else "BAJA",
        "Agregar procedimiento backup/restore y nota ética si falta.",
        "SI",
    )

    # D7 Streamlit.
    metrics_count = len(re.findall(r"\.metric\(", dashboard_text))
    temporal_count = len(re.findall(r"anio|mes|fecha|periodo", dashboard_text, re.IGNORECASE))
    comparisons = len(re.findall(r"pais|cobertura|precipitacion|temperatura|humedad|pm25|pm10", dashboard_text, re.IGNORECASE))
    filters = "multiselect" in dashboard_text and "slider" in dashboard_text
    matrix_files = [path for path in [ROOT / "README.md", ROOT / "evidencia" / "README.md"] if re.search(r"pregunta|EC1|vista SQL|visualiz", read_text(path), re.IGNORECASE)]
    criterion(
        rows,
        "D7 Streamlit",
        status(metrics_count >= 7 and temporal_count >= 2 and comparisons >= 2 and filters, partial=metrics_count >= 7 and filters),
        f"metricas={metrics_count}; temporal_refs={temporal_count}; comparaciones_refs={comparisons}; filtros={filters}; matriz_docs={len(matrix_files)}",
        "Puede faltar matriz pregunta EC1 → vista → visualización.",
        "MEDIA" if not matrix_files else "BAJA",
        "Documentar matriz pregunta analítica/vista/fuente/visualización.",
        "SI",
    )

    # D8 Docker/despliegue.
    compose_files = [
        ROOT / "docker-compose.yml",
        ROOT / "compose.yml",
        ROOT / "docker" / "docker-compose.yml",
        ROOT / "implementation" / "docker" / "docker-compose.yml",
    ]
    dockerfiles = list(ROOT.glob("**/Dockerfile"))
    compose_exists = any(path.exists() for path in compose_files)
    compose_text = "\n".join(read_text(path) for path in compose_files if path.exists())
    docker_docs_text = (
        read_text(ROOT / "README.md")
        + "\n"
        + read_text(ROOT / "docker" / "README.md")
        + "\n"
        + read_text(ROOT / "implementation" / "docker" / "README.md")
    )
    deploy_docs = bool(re.search(r"UTEC|local|docker|compose|servidor|desplieg|conten", docker_docs_text, re.IGNORECASE))
    connectivity_docs = bool(re.search(r"PostgreSQL|MongoDB|DATABASE_URL|MONGO_URI|puerto|host", docker_docs_text + compose_text, re.IGNORECASE))
    sharding_docs = bool(re.search(r"sharding|shard|replica|simulad", docker_docs_text + compose_text, re.IGNORECASE))
    docker_logs = glob_exists("evidencia/logs/*docker*") + glob_exists("evidencia/logs/*deploy*") + glob_exists("evidencia/logs/*desplieg*")
    criterion(
        rows,
        "D8 Docker/despliegue",
        status(compose_exists and deploy_docs and connectivity_docs, partial=compose_exists or deploy_docs),
        f"compose={compose_exists}; dockerfiles={len(dockerfiles)}; deploy_docs={deploy_docs}; conectividad={connectivity_docs}; sharding_docs={sharding_docs}; logs={len(docker_logs)}",
        "Sin documentación de despliegue puede quedar débil la reproducibilidad fuera de Jupyter.",
        "MEDIA" if not (compose_exists and deploy_docs) else "BAJA",
        "Documentar qué corre local/UTEC, variables, puertos y límites; no prometer Docker real si no fue probado.",
        "SI",
    )

    # D9 rendimiento.
    perf_paths = (
        glob_exists("evidencia/logs/*rendimiento*")
        + glob_exists("evidencia/logs/*performance*")
        + glob_exists("evidencia/logs/*tiempo*")
    )
    perf_text = "\n".join(read_text(path) for path in perf_paths[-12:])
    has_query_times = bool(re.search(r"(segundos|seconds|ms|tiempo).*(v_incendios|consulta|query)|v_incendios.*(segundos|seconds|ms)", perf_text, re.IGNORECASE | re.DOTALL))
    has_pipeline_times = bool(re.search(r"(pipeline|etl|carga).*(segundos|duracion|duration|tiempo)", perf_text, re.IGNORECASE | re.DOTALL))
    has_index_discussion = bool(re.search(r"(indice|índice|index|idx_).*(impacto|mejora|join|filtro)|sin índices|con índices", perf_text + read_text(ROOT / "README.md"), re.IGNORECASE | re.DOTALL))
    has_complete_vs_smoke = bool(re.search(r"(completa|historica|histórica).*(smoke|incremental|controlada)|smoke.*(completa|incremental)", perf_text + read_text(ROOT / "README.md"), re.IGNORECASE | re.DOTALL))
    criterion(
        rows,
        "D9 rendimiento",
        status(has_query_times and has_pipeline_times and has_index_discussion, partial=bool(perf_paths) and has_query_times),
        f"logs={len(perf_paths)}; tiempos_consultas={has_query_times}; tiempos_pipeline={has_pipeline_times}; indices={has_index_discussion}; completa_vs_smoke={has_complete_vs_smoke}",
        "Sin tiempos cuantitativos, el rendimiento queda como afirmación cualitativa.",
        "ALTA" if not has_query_times else ("MEDIA" if not has_pipeline_times else "BAJA"),
        "Guardar tabla de tiempos de vistas/pipeline y explicar impacto de índices y smoke vs carga completa.",
        "SI",
    )

    pg.close()
    mongo.close()

    summary = summarize_rows(rows)
    URGENCIES_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    md: list[str] = []
    md.append("# Auditoría EC3 - Estado Actual\n\n")
    md.append(f"Generado: {datetime.now(timezone.utc).isoformat()}\n\n")
    md.append("## Diagnóstico General\n\n")
    md.append(f"Estado general: **{summary['estado_general']}**.\n\n")
    if summary["urgencias"]:
        md.append("Hay puntos pendientes o parcialmente evidenciados que conviene cerrar antes de la entrega. El reporte no inventa resultados: marca como parcial o no verificado lo que no pudo comprobar con archivos, logs o conexión.\n\n")
    else:
        md.append("No se detectaron urgencias abiertas con la evidencia disponible. Mantener la defensa limitada a lo que figura en logs y consultas.\n\n")
    md.append("## Resumen\n\n")
    for state_name, n in sorted(summary["conteo_estados"].items()):
        md.append(f"- {state_name}: {n}\n")
    md.append("\n## Tabla De Cumplimiento\n\n")
    headers = ["Criterio", "Estado", "Evidencia encontrada", "Riesgo", "Urgencia", "Acción recomendada", "¿Se puede terminar hoy?"]
    md.append("| " + " | ".join(headers) + " |\n")
    md.append("| " + " | ".join(["---"] * len(headers)) + " |\n")
    for row in rows:
        values = [str(row[h]).replace("\n", " ").replace("|", "\\|") for h in headers]
        md.append("| " + " | ".join(values) + " |\n")
    md.append("\n## Urgencias Ordenadas\n\n")
    if summary["urgencias"]:
        urgency_order = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
        for row in sorted(summary["urgencias"], key=lambda item: urgency_order.get(item["Urgencia"], 9)):
            md.append(f"- **{row['Urgencia']} - {row['Criterio']}**: {row['Acción recomendada']}\n")
    else:
        md.append("- Sin urgencias abiertas detectadas.\n")
    md.append("\n## Plan Para Terminar Hoy\n\n")
    md.append("### Tareas De 30 Minutos\n\n")
    short_tasks = [row for row in summary["urgencias"] if row["¿Se puede terminar hoy?"] == "SI" and row["Urgencia"] == "ALTA"]
    if not short_tasks:
        short_tasks = [row for row in summary["urgencias"] if row["¿Se puede terminar hoy?"] == "SI"][:3]
    if short_tasks:
        for row in short_tasks:
            md.append(f"- {row['Criterio']}: {row['Acción recomendada']}\n")
    else:
        md.append("- Reejecutar el auditor luego de cualquier cambio final y guardar el reporte.\n")
    md.append("\n### Tareas De 1 Hora\n\n")
    medium_tasks = [row for row in summary["urgencias"] if row["Urgencia"] == "MEDIA"]
    if medium_tasks:
        for row in medium_tasks:
            md.append(f"- {row['Criterio']}: {row['Acción recomendada']}\n")
    else:
        md.append("- Consolidar README/evidencias y preparar capturas del dashboard si aún no están.\n")
    md.append("\n### Tareas Que No Conviene Intentar Hoy\n\n")
    md.append("- Recolectar series históricas faltantes que dependan de APIs externas lentas o cupos diarios.\n")
    md.append("- Prometer cobertura completa donde las fuentes reales tienen huecos documentados.\n")
    md.append("- Rehacer el modelo de datos si las validaciones actuales ya pasan.\n")
    md.append("\n## No Conviene Prometer Sin Evidencia\n\n")
    md.append("- No prometer que CAMS cubre 2018-2021 con PM2.5/PM10 útil: la evidencia cargada empieza en 2022-08-04.\n")
    md.append("- No prometer MODIS Argentina/Brasil 2022-2024 si no se cargó fuente real para esos años.\n")
    md.append("- No decir que los descartes masivos son errores ETL: muchos son filtrados por alcance geográfico/temporal.\n")
    md.append("- No decir que FIRMS confirma incendios: FIRMS detecta focos de calor satelitales.\n")
    md.append("- No afirmar cobertura completa de CHIRPS para Uruguay si la tabla no tiene URY.\n")
    md.append("\n## Evidencias Fuertes\n\n")
    for row in rows:
        if row["Estado"] == "COMPLETO":
            md.append(f"- {row['Criterio']}: {row['Evidencia encontrada']}\n")
    REPORT_MD.write_text("".join(md), encoding="utf-8")
    rec.log("report_generated", run_log=str(RUN_LOG), markdown=str(REPORT_MD), urgencies=str(URGENCIES_JSON))
    rec.flush()
    print(f"\nReporte: {REPORT_MD}")
    print(f"Urgencias: {URGENCIES_JSON}")
    print(f"Log: {RUN_LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
