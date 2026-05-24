from __future__ import annotations

import time

from devops.common import load_env, new_run_id, pg_config, redact_dict, tcp_ping, timed_check


def connect():
    import psycopg2

    cfg = pg_config(load_env())
    return psycopg2.connect(**cfg, connect_timeout=5)


def check_tcp() -> dict:
    cfg = pg_config(load_env())
    seconds = tcp_ping(cfg["host"], cfg["port"])
    return {"target": f"{cfg['host']}:{cfg['port']}", "seconds": seconds}


def check_connection() -> dict:
    cfg = pg_config(load_env())
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, version()")
            db, user, version = cur.fetchone()
    return {"config": redact_dict(cfg), "database": db, "user": user, "version": version}


def check_schemas_tables_indexes() -> dict:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
            schemas = [r[0] for r in cur.fetchall()]
            cur.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
            """)
            tables = [f"{s}.{t}" for s, t in cur.fetchall()]
            cur.execute("""
                SELECT schemaname, tablename, indexname
                FROM pg_indexes
                WHERE schemaname NOT IN ('pg_catalog')
                ORDER BY schemaname, tablename, indexname
            """)
            indexes = [f"{s}.{t}.{i}" for s, t, i in cur.fetchall()]
    expected = ["staging", "dw", "audit"]
    return {
        "schemas": schemas,
        "expected_schema_status": {s: s in schemas for s in expected},
        "tables": tables[:200],
        "index_count": len(indexes),
        "indexes_sample": indexes[:80],
    }


def check_read_write() -> dict:
    with connect() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS audit")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit.devops_probe (
                    id BIGSERIAL PRIMARY KEY,
                    run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    marker TEXT NOT NULL
                )
            """)
            marker = f"probe_{int(time.time())}"
            cur.execute("INSERT INTO audit.devops_probe(marker) VALUES (%s) RETURNING id", (marker,))
            inserted_id = cur.fetchone()[0]
            cur.execute("SELECT marker FROM audit.devops_probe WHERE id = %s", (inserted_id,))
            selected = cur.fetchone()[0]
            cur.execute("DELETE FROM audit.devops_probe WHERE id = %s", (inserted_id,))
    return {"inserted_id": inserted_id, "selected": selected, "deleted": True}


def benchmark() -> dict:
    queries = {
        "select_1": "SELECT 1",
        "schemas": "SELECT COUNT(*) FROM information_schema.schemata",
        "tables": "SELECT COUNT(*) FROM information_schema.tables",
    }
    out = {}
    with connect() as conn:
        with conn.cursor() as cur:
            for name, sql in queries.items():
                start = time.perf_counter()
                cur.execute(sql)
                cur.fetchone()
                out[name] = round(time.perf_counter() - start, 5)
    return out


def main() -> int:
    run_id = new_run_id()
    print(f"run_id={run_id}")
    checks = [
        ("postgres_tcp", check_tcp),
        ("postgres_connection", check_connection),
        ("postgres_schemas_tables_indexes", check_schemas_tables_indexes),
        ("postgres_read_write", check_read_write),
        ("postgres_benchmark", benchmark),
    ]
    results = [timed_check(run_id, name, fn) for name, fn in checks]
    fails = sum(1 for r in results if r.status != "PASS")
    print(f"SUMMARY: {len(results)-fails} PASS / {fails} FAIL")
    print(f"log=logs/devops/{run_id}.jsonl")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
