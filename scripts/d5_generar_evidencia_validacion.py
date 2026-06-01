#!/usr/bin/env python3
"""Genera evidencia D5 de testing y validacion consolidada.

Pensado para Jupyter/UTEC: ejecuta Python, SQL via psql y validaciones directas
contra PostgreSQL. MongoDB se valida si `MONGO_URI` esta definida.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import psycopg2
except ImportError as exc:  # pragma: no cover
    raise SystemExit("ERROR: psycopg2 no esta instalado.") from exc


SMOKE_COMMAND = [
    "python",
    "-u",
    "etl/main.py",
    "--smoke",
    "--start-date",
    "2025-01-01",
    "--end-date",
    "2025-01-07",
    "--countries",
    "URY",
    "--max-records-per-source",
    "1000",
    "--skip-mongo",
]

EXPECTED_DASHBOARD_VIEWS = [
    "dw.v_incendios_pais_periodo",
    "dw.v_incendios_region",
    "dw.v_incendios_clima",
    "dw.v_incendios_precipitacion",
    "dw.v_incendios_cobertura",
    "dw.v_calidad_aire_alta_actividad",
    "dw.v_calidad_pipeline",
]


def root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=json_default))


def section(title: str) -> None:
    print(f"\n## {title}")


def run_command(command: list[str], cwd: Path, timeout: int | None = None) -> dict[str, Any]:
    started = datetime.now(UTC)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(cwd) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "started_at": started.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def write_command_result(result: dict[str, Any]) -> None:
    print(f"$ {' '.join(result['command'])}")
    print(f"returncode={result['returncode']}")
    if result["stdout"]:
        print("\n[stdout]")
        print(result["stdout"])
    if result["stderr"]:
        print("\n[stderr]")
        print(result["stderr"])


def fetch_dicts(cursor) -> list[dict[str, Any]]:
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def scalar(cursor, statement: str, params: tuple[Any, ...] = ()) -> Any:
    cursor.execute(statement, params)
    return cursor.fetchone()[0]


def duplicate_counts(cursor) -> dict[str, int]:
    tables = [
        ("staging", "stg_firms"),
        ("staging", "stg_meteo"),
        ("staging", "stg_chirps"),
        ("staging", "stg_modis"),
        ("staging", "stg_calidad_aire"),
        ("dw", "fact_incendio"),
    ]
    counts: dict[str, int] = {}
    for schema, table in tables:
        exists = scalar(cursor, "SELECT to_regclass(%s) IS NOT NULL", (f"{schema}.{table}",))
        if not exists:
            counts[f"{schema}.{table}"] = -1
            continue
        has_key = scalar(
            cursor,
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.columns
              WHERE table_schema=%s AND table_name=%s AND column_name='natural_key'
            )
            """,
            (schema, table),
        )
        if not has_key:
            counts[f"{schema}.{table}"] = -1
            continue
        cursor.execute(
            f'''
            SELECT COUNT(*)::bigint
            FROM (
              SELECT natural_key FROM "{schema}"."{table}"
              GROUP BY natural_key HAVING COUNT(*) > 1
            ) d
            '''
        )
        counts[f"{schema}.{table}"] = int(cursor.fetchone()[0])
    return counts


def row_counts(cursor) -> dict[str, int]:
    tables = [
        ("staging", "stg_firms"),
        ("staging", "stg_meteo"),
        ("staging", "stg_chirps"),
        ("staging", "stg_modis"),
        ("staging", "stg_calidad_aire"),
        ("dw", "fact_incendio"),
        ("audit", "etl_runs"),
        ("audit", "cdc_eventos"),
    ]
    result: dict[str, int] = {}
    for schema, table in tables:
        exists = scalar(cursor, "SELECT to_regclass(%s) IS NOT NULL", (f"{schema}.{table}",))
        if not exists:
            result[f"{schema}.{table}"] = -1
            continue
        cursor.execute(f'SELECT COUNT(*)::bigint FROM "{schema}"."{table}"')
        result[f"{schema}.{table}"] = int(cursor.fetchone()[0])
    return result


def snapshot(database_url: str) -> dict[str, Any]:
    with psycopg2.connect(database_url) as conn, conn.cursor() as cursor:
        return {
            "row_counts": row_counts(cursor),
            "duplicate_natural_keys": duplicate_counts(cursor),
            "captured_at": datetime.now(UTC).isoformat(),
        }


def quality_status(database_url: str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    with psycopg2.connect(database_url) as conn, conn.cursor() as cursor:
        queries = {
            "fact_incendio_natural_key_nulos": "SELECT COUNT(*) FROM dw.fact_incendio WHERE natural_key IS NULL",
            "fact_incendio_record_hash_nulos": "SELECT COUNT(*) FROM dw.fact_incendio WHERE record_hash IS NULL",
            "fact_incendio_fecha_id_nulos": "SELECT COUNT(*) FROM dw.fact_incendio WHERE fecha_id IS NULL",
            "fact_incendio_ubicacion_id_nulos": "SELECT COUNT(*) FROM dw.fact_incendio WHERE ubicacion_id IS NULL",
            "fact_incendio_frp_nulos": "SELECT COUNT(*) FROM dw.fact_incendio WHERE frp_mw IS NULL",
            "fact_incendio_brillo_termico_nulos": "SELECT COUNT(*) FROM dw.fact_incendio WHERE brillo_termico IS NULL",
            "fact_incendio_frp_negativo": "SELECT COUNT(*) FROM dw.fact_incendio WHERE frp_mw < 0",
            "dim_ubicacion_coord_invalidas": "SELECT COUNT(*) FROM dw.dim_ubicacion WHERE latitud NOT BETWEEN -90 AND 90 OR longitud NOT BETWEEN -180 AND 180",
            "dim_ubicacion_pais_invalido": "SELECT COUNT(*) FROM dw.dim_ubicacion WHERE pais_codigo NOT IN ('URY','ARG','BRA')",
            "dim_clima_humedad_invalida": "SELECT COUNT(*) FROM dw.dim_clima WHERE humedad_pct IS NOT NULL AND humedad_pct NOT BETWEEN 0 AND 100",
            "dim_clima_direccion_viento_invalida": "SELECT COUNT(*) FROM dw.dim_clima WHERE direccion_viento_grados IS NOT NULL AND direccion_viento_grados NOT BETWEEN 0 AND 360",
            "dim_precipitacion_negativa": "SELECT COUNT(*) FROM dw.dim_precipitacion WHERE precipitacion_mm < 0",
            "dim_calidad_aire_pm25_negativa": "SELECT COUNT(*) FROM dw.dim_calidad_aire WHERE pm25 IS NOT NULL AND pm25 < 0",
            "dim_calidad_aire_pm10_negativa": "SELECT COUNT(*) FROM dw.dim_calidad_aire WHERE pm10 IS NOT NULL AND pm10 < 0",
            "inumet_fuera_uruguay": "SELECT COUNT(*) FROM staging.stg_meteo WHERE fuente='INUMET' AND pais_codigo <> 'URY'",
            "estaciones_no_ury": "SELECT COUNT(*) FROM dw.dim_estacion_meteorologica WHERE pais_codigo <> 'URY'",
            "brightness_column_activa": """
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema IN ('staging','dw') AND column_name ILIKE '%brightness%'
            """,
            "fk_fecha_rotas": """
                SELECT COUNT(*) FROM dw.fact_incendio f
                LEFT JOIN dw.dim_fecha d ON d.fecha_id=f.fecha_id
                WHERE d.fecha_id IS NULL
            """,
            "fk_ubicacion_rotas": """
                SELECT COUNT(*) FROM dw.fact_incendio f
                LEFT JOIN dw.dim_ubicacion u ON u.ubicacion_id=f.ubicacion_id
                WHERE u.ubicacion_id IS NULL
            """,
        }
        for name, statement in queries.items():
            value = int(scalar(cursor, statement))
            checks.append({"check": name, "hallazgos": value, "ok": value == 0})
        duplicates = duplicate_counts(cursor)
        for table, value in duplicates.items():
            checks.append({"check": f"duplicados_{table}", "hallazgos": value, "ok": value == 0})
    return {"checks": checks, "ok": all(item["ok"] for item in checks)}


def cdc_status(database_url: str) -> dict[str, Any]:
    with psycopg2.connect(database_url) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT tipo_evento, COUNT(*)::bigint AS eventos
            FROM audit.cdc_eventos
            WHERE fuente IN ('FIRMS','METEO','CAMS','CHIRPS','MODIS','INUMET')
            GROUP BY tipo_evento
            """
        )
        counts = {row["tipo_evento"]: int(row["eventos"]) for row in fetch_dicts(cursor)}
    required = {"alta", "modificacion", "sin_cambio"}
    return {"eventos": counts, "ok": all(counts.get(kind, 0) > 0 for kind in required)}


def views_status(database_url: str) -> dict[str, Any]:
    rows = []
    with psycopg2.connect(database_url) as conn, conn.cursor() as cursor:
        for view in EXPECTED_DASHBOARD_VIEWS:
            exists = bool(scalar(cursor, "SELECT to_regclass(%s) IS NOT NULL", (view,)))
            row: dict[str, Any] = {"view": view, "exists": exists, "ok": False}
            if exists:
                cursor.execute(f"SELECT COUNT(*)::bigint AS rows FROM {view}")
                row["rows"] = int(cursor.fetchone()[0])
                cursor.execute(f"SELECT * FROM {view} LIMIT 1")
                row["query_ok"] = True
                row["ok"] = True
            else:
                row["estado"] = "FALTA"
            rows.append(row)
    return {"views": rows, "ok": all(row["ok"] for row in rows)}


def run_psql_file(database_url: str, sql_file: Path, output_path: Path) -> dict[str, Any]:
    if not shutil.which("psql"):
        payload = {
            "sql_file": str(sql_file),
            "returncode": 127,
            "stderr": "psql no esta disponible en el entorno.",
            "stdout": "",
        }
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return payload
    started = datetime.now(UTC)
    result = subprocess.run(
        ["psql", "-v", "ON_ERROR_STOP=1", database_url, "-f", str(sql_file)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
    )
    payload = {
        "sql_file": str(sql_file),
        "returncode": result.returncode,
        "started_at": started.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    output_path.write_text(
        f"SQL: {sql_file.name}\nreturncode={result.returncode}\n\n[stdout]\n{result.stdout}\n\n[stderr]\n{result.stderr}\n",
        encoding="utf-8",
    )
    return payload


def write_log(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    root = root_dir()
    log_dir = root / "evidencia" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    database_url = os.getenv("DATABASE_URL", "").strip()
    mongo_uri = os.getenv("MONGO_URI", "").strip()
    summary_path = log_dir / "d5_resumen_ultima_ejecucion.log"

    if not database_url:
        summary = {
            "generated_at": datetime.now(UTC).isoformat(),
            "exit_code": 1,
            "error": "Debe definir DATABASE_URL.",
        }
        write_log(summary_path, json.dumps(summary, indent=2, ensure_ascii=False))
        print_json(summary)
        return 1

    logs: dict[str, str] = {}
    statuses: dict[str, Any] = {}

    compile_path = log_dir / f"d5_compileall_{stamp}.log"
    compile_result = run_command(["python", "-m", "compileall", "-q", "."], root, timeout=300)
    write_log(compile_path, json.dumps(compile_result, indent=2, ensure_ascii=False))
    logs["compileall"] = str(compile_path)
    statuses["compileall_ok"] = compile_result["returncode"] == 0

    pytest_path = log_dir / f"d5_pytest_{stamp}.log"
    pytest_result = run_command(["python", "-m", "pytest", "-q", "tests"], root, timeout=300)
    write_log(pytest_path, json.dumps(pytest_result, indent=2, ensure_ascii=False))
    logs["pytest"] = str(pytest_path)
    statuses["pytest_ok"] = pytest_result["returncode"] == 0

    before = snapshot(database_url)
    smoke_logs = []
    smoke_results = []
    for index in (1, 2):
        path = log_dir / f"d5_smoke_corrida_{index}_{stamp}.log"
        result = run_command(SMOKE_COMMAND, root, timeout=900)
        with path.open("w", encoding="utf-8") as handle, redirect_stdout(handle), redirect_stderr(handle):
            write_command_result(result)
        smoke_logs.append(str(path))
        smoke_results.append(result)
        if index == 1:
            between = snapshot(database_url)
    after = snapshot(database_url)
    logs["smoke_corridas"] = smoke_logs

    idempotence_path = log_dir / f"d5_idempotencia_{stamp}.log"
    before_dups = before["duplicate_natural_keys"]
    between_dups = between["duplicate_natural_keys"]
    after_dups = after["duplicate_natural_keys"]
    idempotence = {
        "before": before,
        "between": between,
        "after": after,
        "smoke_returncodes": [result["returncode"] for result in smoke_results],
        "duplicados_no_aumentan_corrida_1": all(between_dups[key] <= before_dups.get(key, 0) for key in between_dups),
        "duplicados_no_aumentan_corrida_2": all(after_dups[key] <= between_dups.get(key, 0) for key in after_dups),
    }
    idempotence["ok"] = (
        all(result["returncode"] == 0 for result in smoke_results)
        and idempotence["duplicados_no_aumentan_corrida_1"]
        and idempotence["duplicados_no_aumentan_corrida_2"]
    )
    write_log(idempotence_path, json.dumps(idempotence, indent=2, ensure_ascii=False, default=json_default))
    logs["idempotencia"] = str(idempotence_path)
    statuses["idempotencia_ok"] = idempotence["ok"]

    quality_sql_path = log_dir / f"d5_validacion_calidad_sql_{stamp}.log"
    functional_sql_path = log_dir / f"d5_validacion_funcional_sql_{stamp}.log"
    quality_sql = run_psql_file(database_url, root / "sql" / "validation" / "d5_validacion_calidad.sql", quality_sql_path)
    functional_sql = run_psql_file(database_url, root / "sql" / "validation" / "d5_validacion_funcional.sql", functional_sql_path)
    logs["sql_calidad"] = str(quality_sql_path)
    logs["sql_funcional"] = str(functional_sql_path)

    quality = quality_status(database_url)
    views = views_status(database_url)
    cdc = cdc_status(database_url)
    quality_direct_path = log_dir / f"d5_calidad_directa_{stamp}.log"
    views_path = log_dir / f"d5_vistas_directa_{stamp}.log"
    cdc_path = log_dir / f"d5_cdc_directa_{stamp}.log"
    write_log(quality_direct_path, json.dumps(quality, indent=2, ensure_ascii=False, default=json_default))
    write_log(views_path, json.dumps(views, indent=2, ensure_ascii=False, default=json_default))
    write_log(cdc_path, json.dumps(cdc, indent=2, ensure_ascii=False, default=json_default))
    logs["calidad_directa"] = str(quality_direct_path)
    logs["vistas_directa"] = str(views_path)
    logs["cdc_directa"] = str(cdc_path)

    statuses["calidad_ok"] = quality["ok"] and quality_sql["returncode"] == 0
    statuses["vistas_ok"] = views["ok"] and functional_sql["returncode"] == 0
    statuses["cdc_ok"] = cdc["ok"]

    mongo_status: dict[str, Any] = {"consultado": False, "ok": None, "limitacion": "MONGO_URI no definida"}
    if mongo_uri:
        mongo_path = log_dir / f"d5_mongo_cdc_{stamp}.log"
        mongo_result = run_command(["python", "scripts/d5_validar_mongo_cdc.py"], root, timeout=120)
        write_log(mongo_path, json.dumps(mongo_result, indent=2, ensure_ascii=False))
        logs["mongo_cdc"] = str(mongo_path)
        mongo_status = {"consultado": True, "ok": mongo_result["returncode"] == 0, "returncode": mongo_result["returncode"]}
    statuses["mongo_cdc"] = mongo_status

    final_ok = all(
        [
            statuses["compileall_ok"],
            statuses["pytest_ok"],
            statuses["idempotencia_ok"],
            statuses["cdc_ok"],
            statuses["calidad_ok"],
            statuses["vistas_ok"],
        ]
    )
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "criterio": "D5 Testing y validacion del sistema consolidado",
        "compileall_ok": statuses["compileall_ok"],
        "pytest_ok": statuses["pytest_ok"],
        "idempotencia_ok": statuses["idempotencia_ok"],
        "cdc_ok": statuses["cdc_ok"],
        "calidad_ok": statuses["calidad_ok"],
        "vistas_ok": statuses["vistas_ok"],
        "mongo_cdc": mongo_status,
        "smoke_command": " ".join(SMOKE_COMMAND),
        "logs": logs,
        "exit_code": 0 if final_ok else 1,
        "nota": "MongoDB se valida cuando MONGO_URI esta definido; PostgreSQL sigue siendo el DW principal.",
    }
    write_log(summary_path, json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    print_json(summary)
    return int(summary["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
