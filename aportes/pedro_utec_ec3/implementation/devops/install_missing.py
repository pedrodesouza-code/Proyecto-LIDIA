from __future__ import annotations

import importlib.util
import subprocess
import sys

REQUIRED = {
    "dotenv": "python-dotenv",
    "psycopg2": "psycopg2-binary",
    "pymongo": "pymongo",
    "pandas": "pandas",
    "pyarrow": "pyarrow",
    "requests": "requests",
    "streamlit": "streamlit",
}


def main() -> int:
    missing = [pkg for module, pkg in REQUIRED.items() if importlib.util.find_spec(module) is None]
    if not missing:
        print("Todas las dependencias minimas estan instaladas.")
        return 0
    print("Instalando faltantes:", ", ".join(missing))
    cmd = [sys.executable, "-m", "pip", "install", "--user", *missing]
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
