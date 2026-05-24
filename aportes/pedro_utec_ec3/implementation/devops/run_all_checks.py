from __future__ import annotations

from devops import check_datasets, check_mongo, check_postgres, check_streamlit, diagnose_env


def main() -> int:
    modules = [
        ("environment", diagnose_env.main),
        ("postgres", check_postgres.main),
        ("mongo", check_mongo.main),
        ("datasets", check_datasets.main),
        ("streamlit", check_streamlit.main),
    ]
    failures = 0
    for name, fn in modules:
        print("\n" + "=" * 80)
        print(f"RUNNING {name}")
        print("=" * 80)
        try:
            code = fn()
        except Exception as exc:
            code = 1
            print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
        failures += 1 if code else 0
    print("\n" + "=" * 80)
    print(f"GLOBAL SUMMARY: {len(modules)-failures} PASS / {failures} FAIL")
    print("=" * 80)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
