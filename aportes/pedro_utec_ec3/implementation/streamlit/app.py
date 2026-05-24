from __future__ import annotations

from pathlib import Path
import runpy
import sys
import traceback

import streamlit as st

PROJECT_ROOT = Path("/app/Proyecto-LIDIA")
if not PROJECT_ROOT.exists():
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    for module_name in list(sys.modules):
        if module_name == "dashboard" or module_name.startswith("dashboard."):
            del sys.modules[module_name]
    runpy.run_path(str(PROJECT_ROOT / "dashboard" / "utec_dashboard.py"), run_name="__main__")
except Exception as exc:
    st.error("No se pudo cargar el dashboard EC3.")
    st.exception(exc)
    st.code(traceback.format_exc())
