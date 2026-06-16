from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import requests


BASE_URL = "http://10.200.245.40:18803"
TOKEN = "8b2090d80b6154830e6eba877b34495c"
REPO_ROOT = Path("/home/pepo/Datos completos/Proyecto-LIDIA-ec3-pedro")
REMOTE_ROOT = "Proyecto-LIDIA"

SYNC_PATHS = [
    "README.md",
    "config/.env.example",
    "config/settings.py",
    "config/utec.env.example",
    "dashboard/streamlit_app.py",
    "docker/.env.example",
    "docker/README.md",
    "docker/docker-compose.yml",
    "docker/init_roles.sh",
    "docs/D8_entorno_local_docker.md",
    "docs/ejecucion_local.md",
    "docs/arquitectura_integrada_lidia.mmd",
    "docs/arquitectura_integrada_lidia.png",
    "etl/README.md",
    "etl/extract/extract_modis.py",
    "nosql/README.md",
    "scripts/aplicar_sharding_mongo_compose.sh",
    "scripts/auditar_parquets_2018_2025.py",
    "scripts/cargar_bases_local_docker.sh",
    "scripts/cargar_firms_smoke_local.sh",
    "scripts/cargar_todos_datos_locales.sh",
    "scripts/d8_generar_evidencia_docker.sh",
    "scripts/ec3_preparar_datos_locales.sh",
    "scripts/ec3_validar_cdc_local.sh",
    "scripts/ec3_verificar_logrado.py",
    "scripts/export_state_from_jupyter.sh",
    "scripts/import_mongo_jsonl_to_local.sh",
    "scripts/import_state_to_local.sh",
    "scripts/integrar_firms_2025_complemento.py",
    "scripts/local_load_all.sh",
    "scripts/local_reset_and_load.sh",
    "scripts/local_validate_state.sh",
    "scripts/preparar_chirps_2025.py",
    "scripts/preparar_firms_historico_desde_shapefile.py",
    "scripts/preparar_inumet_file_local.py",
    "scripts/preparar_meteo_2025.py",
    "scripts/preparar_modis_2018_2025.py",
    "sql/ddl/02_Schema.sql",
    "sql/validation/d1_validacion_modelo_relacional.sql",
]

DELETE_PATHS = [
    "config/env_editable.txt",
    "config/untitled.txt",
    "etl/main.py.backup_partitioned_firms",
    "scripts/export_mongo_jsonl_from_jupyter.sh",
    "scripts/sql/ddl/00_schemas.sql",
    "scripts/sql/ddl/01_roles.sql",
    "scripts/sql/ddl/02_Schema.sql",
    "scripts/sql/ddl/03_indices.sql",
    "scripts/sql/ddl/04_vistas.sql",
    "scripts/sql/ddl/05_migracion_Sa.sql",
    "scripts/sql/validation/d1_validacion_modelo_relacional.sql",
]


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Authorization": f"token {TOKEN}"})
    return s


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ensure_directory(s: requests.Session, path: str) -> None:
    parts = path.split("/")
    for i in range(1, len(parts) + 1):
        sub = "/".join(parts[:i])
        url = f"{BASE_URL}/api/contents/{REMOTE_ROOT}/{sub}"
        r = s.get(url, timeout=20)
        if r.status_code == 404:
            rr = s.put(url, json={"type": "directory"}, timeout=20)
            rr.raise_for_status()
        elif r.status_code != 200:
            r.raise_for_status()


def upload_file(s: requests.Session, rel: str) -> str:
    local = REPO_ROOT / rel
    data = local.read_bytes()
    remote_path = f"{REMOTE_ROOT}/{rel}"
    ensure_directory(s, str(Path(rel).parent).replace(".", "").strip("/"))
    if local.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif"}:
        payload = {
            "type": "file",
            "format": "base64",
            "content": base64.b64encode(data).decode("ascii"),
        }
    else:
        payload = {
            "type": "file",
            "format": "text",
            "content": data.decode("utf-8"),
        }
    r = s.put(f"{BASE_URL}/api/contents/{remote_path}", json=payload, timeout=60)
    r.raise_for_status()
    return sha256_bytes(data)


def remote_sha(s: requests.Session, rel: str) -> str | None:
    r = s.get(f"{BASE_URL}/files/{REMOTE_ROOT}/{rel}", timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return sha256_bytes(r.content)


def delete_path(s: requests.Session, rel: str) -> str:
    remote_path = f"{REMOTE_ROOT}/{rel}"
    r = s.delete(f"{BASE_URL}/api/contents/{remote_path}", json={"path": remote_path}, timeout=30)
    if r.status_code in {204, 404}:
        return "deleted" if r.status_code == 204 else "absent"
    r.raise_for_status()
    return "deleted"


def main() -> None:
    s = session()
    uploaded = []
    unchanged = []
    failed = []
    for rel in SYNC_PATHS:
        local = REPO_ROOT / rel
        if not local.exists():
            continue
        lsha = sha256_bytes(local.read_bytes())
        try:
            rsha = remote_sha(s, rel)
            if lsha == rsha:
                unchanged.append(rel)
                continue
            upload_file(s, rel)
            uploaded.append(rel)
        except Exception as exc:  # pragma: no cover - operational sync report
            failed.append(f"{rel}: {exc}")

    deleted = []
    for rel in DELETE_PATHS:
        try:
            result = delete_path(s, rel)
            if result == "deleted":
                deleted.append(rel)
        except Exception as exc:  # pragma: no cover - operational sync report
            failed.append(f"{rel}: {exc}")

    print("uploaded", len(uploaded))
    for rel in uploaded:
        print("UP", rel)
    print("unchanged", len(unchanged))
    print("deleted", len(deleted))
    for rel in deleted:
        print("DEL", rel)
    print("failed", len(failed))
    for rel in failed:
        print("FAIL", rel)


if __name__ == "__main__":
    main()
