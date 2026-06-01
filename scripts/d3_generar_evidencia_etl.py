#!/usr/bin/env python3
"""Genera evidencia D3 del ETL Python para Proyecto LIDIA.

Pensado para Jupyter/UTEC: no requiere ejecutar archivos .sh.

Uso:
    DATABASE_URL='postgresql://...' python scripts/d3_generar_evidencia_etl.py

Opcional:
    D3_ETL_COMMAND='python -m etl.main --smoke --source FIRMS --skip-mongo' python scripts/d3_generar_evidencia_etl.py

El comando ETL por defecto usa `--smoke` para generar evidencia reproducible
sin ejecutar la carga historica completa.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import psycopg2
except ImportError as exc:  # pragma: no cover - depende del entorno.
    raise SystemExit("ERROR: psycopg2 no esta instalado en este entorno.") from exc


EXPECTED_TABLES = [
    ("staging", "stg_firms"),
    ("staging", "stg_meteo"),
    ("staging", "stg_chirps"),
    ("staging", "stg_modis"),
    ("staging", "stg_calidad_aire"),
    ("dw", "fact_incendio"),
]

DEFAULT_D3_ETL_COMMAND = (
    "python -u etl/main.py --smoke --start-date 2025-01-01 --end-date 2025-01-07 "
    "--countries URY --max-records-per-source 1000 --skip-mongo"
)


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


def table_exists(cursor, schema: str, table: str) -> bool:
    cursor.execute("SELECT to_regclass(%s)", (f"{schema}.{table}",))
    return cursor.fetchone()[0] is not None


def column_exists(cursor, schema: str, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema=%s AND table_name=%s AND column_name=%s
        )
        """,
        (schema, table, column),
    )
    return bool(cursor.fetchone()[0])


def count_table(cursor, schema: str, table: str) -> int:
    cursor.execute(f'SELECT COUNT(*)::bigint FROM "{schema}"."{table}"')
    return int(cursor.fetchone()[0])


def validate_postgres(database_url: str, output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as handle, redirect_stdout(handle), redirect_stderr(handle):
        section("Conexion PostgreSQL")
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT current_database(), current_user, now()")
                database, user, connected_at = cursor.fetchone()
                print_json({
                    "database": database,
                    "user": user,
                    "connected_at": connected_at,
                    "rol": "PostgreSQL es el Data Warehouse principal",
                })

                section("Tablas De Auditoria Y Metadata")
                catalog_rows = []
                for schema, table in [
                    ("audit", "etl_runs"),
                    ("staging", "ingesta_metadata"),
                    ("staging", "rechazos_etl"),
                    ("dw", "fact_incendio"),
                ]:
                    catalog_rows.append({
                        "table": f"{schema}.{table}",
                        "exists": table_exists(cursor, schema, table),
                    })
                print_json(catalog_rows)

                if table_exists(cursor, "audit", "etl_runs"):
                    section("Ultimas Corridas audit.etl_runs")
                    cursor.execute(
                        """
                        SELECT run_id::text, fuente, etapa, estado, iniciado_en, finalizado_en,
                               filas_leidas, filas_insertadas, filas_actualizadas,
                               filas_rechazadas, duracion_segundos
                        FROM audit.etl_runs
                        ORDER BY iniciado_en DESC NULLS LAST
                        LIMIT 20
                        """
                    )
                    print_json(fetch_dicts(cursor))

                    section("Resumen audit.etl_runs Por Fuente")
                    cursor.execute(
                        """
                        SELECT fuente, estado, COUNT(*)::bigint AS corridas,
                               COALESCE(SUM(filas_leidas),0)::bigint AS filas_leidas,
                               COALESCE(SUM(filas_insertadas),0)::bigint AS filas_insertadas,
                               COALESCE(SUM(filas_actualizadas),0)::bigint AS filas_actualizadas,
                               COALESCE(SUM(filas_rechazadas),0)::bigint AS filas_rechazadas,
                               MAX(iniciado_en) AS ultima_corrida
                        FROM audit.etl_runs
                        GROUP BY fuente, estado
                        ORDER BY fuente, estado
                        """
                    )
                    print_json(fetch_dicts(cursor))
                else:
                    print_json({"limitation": "audit.etl_runs no existe"})

                if table_exists(cursor, "staging", "ingesta_metadata"):
                    section("Metadata De Ingesta")
                    cursor.execute(
                        """
                        SELECT fuente, estado, COUNT(*)::bigint AS corridas,
                               COALESCE(SUM(filas_leidas),0)::bigint AS filas_leidas,
                               COALESCE(SUM(filas_insertadas),0)::bigint AS filas_insertadas,
                               COALESCE(SUM(filas_actualizadas),0)::bigint AS filas_actualizadas,
                               COALESCE(SUM(filas_rechazadas),0)::bigint AS filas_rechazadas,
                               MAX(ultima_fecha_procesada) AS ultima_fecha_procesada
                        FROM staging.ingesta_metadata
                        GROUP BY fuente, estado
                        ORDER BY fuente, estado
                        """
                    )
                    print_json(fetch_dicts(cursor))
                else:
                    print_json({"limitation": "staging.ingesta_metadata no existe"})

                if table_exists(cursor, "staging", "rechazos_etl"):
                    section("Rechazos Por Fuente Y Motivo")
                    cursor.execute(
                        """
                        SELECT fuente, motivo, COUNT(*)::bigint AS rechazos
                        FROM staging.rechazos_etl
                        GROUP BY fuente, motivo
                        ORDER BY fuente, rechazos DESC, motivo
                        """
                    )
                    print_json(fetch_dicts(cursor))
                else:
                    print_json({"limitation": "staging.rechazos_etl no existe"})

                section("Conteos Y Trazabilidad En Staging/DW")
                table_rows = []
                for schema, table in EXPECTED_TABLES:
                    if not table_exists(cursor, schema, table):
                        table_rows.append({"table": f"{schema}.{table}", "exists": False})
                        continue
                    row: dict[str, Any] = {
                        "table": f"{schema}.{table}",
                        "exists": True,
                        "rows": count_table(cursor, schema, table),
                        "has_natural_key": column_exists(cursor, schema, table, "natural_key"),
                        "has_record_hash": column_exists(cursor, schema, table, "record_hash"),
                        "has_fuente": column_exists(cursor, schema, table, "fuente"),
                    }
                    if row["has_natural_key"]:
                        cursor.execute(
                            f'''
                            SELECT COUNT(*)::bigint
                            FROM (
                                SELECT natural_key
                                FROM "{schema}"."{table}"
                                GROUP BY natural_key
                                HAVING COUNT(*) > 1
                            ) d
                            '''
                        )
                        row["duplicated_natural_keys"] = int(cursor.fetchone()[0])
                        cursor.execute(f'SELECT COUNT(*)::bigint FROM "{schema}"."{table}" WHERE natural_key IS NULL')
                        row["null_natural_key"] = int(cursor.fetchone()[0])
                    if row["has_record_hash"]:
                        cursor.execute(f'SELECT COUNT(*)::bigint FROM "{schema}"."{table}" WHERE record_hash IS NULL')
                        row["null_record_hash"] = int(cursor.fetchone()[0])
                    table_rows.append(row)
                print_json(table_rows)

                section("Trazabilidad De Fuente")
                source_rows = []
                for schema, table in EXPECTED_TABLES:
                    if table_exists(cursor, schema, table) and column_exists(cursor, schema, table, "fuente"):
                        cursor.execute(f'SELECT fuente, COUNT(*)::bigint AS filas FROM "{schema}"."{table}" GROUP BY fuente ORDER BY fuente')
                        source_rows.append({"table": f"{schema}.{table}", "fuentes": fetch_dicts(cursor)})
                    elif schema == "dw" and table == "fact_incendio":
                        source_rows.append({
                            "table": "dw.fact_incendio",
                            "fuentes": "Hechos FIRMS; trazabilidad por staging.stg_firms/audit.",
                        })
                print_json(source_rows)

                if table_exists(cursor, "dw", "fact_incendio"):
                    section("dw.fact_incendio")
                    cursor.execute(
                        """
                        SELECT COUNT(*)::bigint AS total,
                               COUNT(DISTINCT natural_key)::bigint AS natural_keys_distintas,
                               COUNT(*) FILTER (WHERE record_hash IS NULL)::bigint AS record_hash_nulos,
                               COUNT(brillo_termico)::bigint AS brillo_termico_no_nulo,
                               COUNT(*) FILTER (WHERE frp_mw < 0)::bigint AS frp_invalidos
                        FROM dw.fact_incendio
                        """
                    )
                    print_json(fetch_dicts(cursor))


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL no esta definida.", file=sys.stderr)
        print("Ejemplo: export DATABASE_URL='postgresql://usuario:password@host:5432/proyecto_lidia'", file=sys.stderr)
        return 1

    mongo_enabled = os.getenv("MONGO_ENABLED", "false").lower() in {"1", "true", "yes"}
    if mongo_enabled and not os.getenv("MONGO_URI"):
        print("ERROR: MONGO_ENABLED esta activo pero MONGO_URI no esta definida.", file=sys.stderr)
        return 1

    root = root_dir()
    log_dir = root / "evidencia" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    run_ts = utc_stamp()

    structure_log = log_dir / f"d3_estructura_etl_{run_ts}.log"
    tests_log = log_dir / f"d3_compile_tests_{run_ts}.log"
    pipeline_log = log_dir / f"d3_pipeline_{run_ts}.log"
    sql_log = log_dir / f"d3_validacion_etl_{run_ts}.log"
    summary_log = log_dir / "d3_resumen_ultima_ejecucion.log"

    with structure_log.open("w", encoding="utf-8") as handle, redirect_stdout(handle), redirect_stderr(handle):
        section("Estructura ETL")
        print("Carpetas etl/")
        for path in sorted((root / "etl").rglob("*")):
            if path.is_dir() and "__pycache__" not in path.parts and ".ipynb_checkpoints" not in path.parts:
                print(path.relative_to(root))
        print("\nArchivos principales ETL")
        for path in sorted((root / "etl").rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and ".ipynb_checkpoints" not in path.parts:
                print(path.relative_to(root))
        print("\nFuentes esperadas: FIRMS, Open-Meteo historico, CAMS/Open-Meteo Air Quality, CHIRPS, MODIS, INUMET.")
        print("Configuracion externa: variables de entorno y ejemplos .env; no se imprime contenido .env.")
        print(f"Comando pipeline: {os.getenv('D3_ETL_COMMAND', DEFAULT_D3_ETL_COMMAND)}")
        help_result = run_command([sys.executable, "-m", "etl.main", "--help"], root, timeout=60)
        write_command_result(help_result)

    with tests_log.open("w", encoding="utf-8") as handle, redirect_stdout(handle), redirect_stderr(handle):
        section("compileall")
        compile_result = run_command([sys.executable, "-m", "compileall", "-q", "."], root, timeout=120)
        write_command_result(compile_result)
        if compile_result["returncode"] != 0:
            raise SystemExit(compile_result["returncode"])
        section("pytest")
        if (root / "tests").exists():
            pytest_result = run_command([sys.executable, "-m", "pytest", "-q", "tests"], root, timeout=120)
            write_command_result(pytest_result)
            if pytest_result["returncode"] != 0:
                raise SystemExit(pytest_result["returncode"])
        else:
            print("No existe carpeta tests; se registra limitacion.")

    pipeline_command = shlex.split(os.getenv("D3_ETL_COMMAND", DEFAULT_D3_ETL_COMMAND))
    pipeline_returncode = 0
    with pipeline_log.open("w", encoding="utf-8") as handle, redirect_stdout(handle), redirect_stderr(handle):
        section("Pipeline")
        print(f"Comando: {' '.join(pipeline_command)}")
        print("Nota: no se imprime contenido de .env ni secretos.")
        pipeline_result = run_command(pipeline_command, root, timeout=None)
        pipeline_returncode = pipeline_result["returncode"]
        write_command_result(pipeline_result)
        if pipeline_result["returncode"] != 0:
            print("\n[limitacion]")
            if pipeline_result["returncode"] in (-9, 137):
                print("El proceso fue matado por recursos. Recomendacion: usar --smoke, acotar fechas/paises y bajar --max-records-per-source.")
            else:
                print("El pipeline finalizo con error; revisar stdout/stderr anteriores.")

    validate_postgres(database_url, sql_log)

    summary_log.write_text(
        "\n".join([
            "D3 ultima ejecucion",
            f"Fecha UTC: {run_ts}",
            f"Estructura ETL log: {structure_log}",
            f"Compile/tests log: {tests_log}",
            f"Pipeline log: {pipeline_log}",
            f"Validacion SQL/Python log: {sql_log}",
            f"Comando pipeline: {' '.join(pipeline_command)}",
            f"Exit code pipeline: {pipeline_returncode}",
            "Limitacion: si el exit code es -9 o 137, el proceso fue matado por recursos; usar corrida smoke acotada.",
            "PostgreSQL es el Data Warehouse principal; MongoDB queda como complemento documental.",
            "",
        ]),
        encoding="utf-8",
    )
    print("D3 ETL evidencia generada:")
    for path in (structure_log, tests_log, pipeline_log, sql_log, summary_log):
        print(f"- {path}")
    return 0 if pipeline_returncode == 0 else pipeline_returncode


if __name__ == "__main__":
    raise SystemExit(main())
