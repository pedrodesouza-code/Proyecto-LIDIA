from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "data", "logs", ".venv", "venv"}
SKIP_FILES = {".env"}


def request(method: str, url: str, token: str, payload: dict | None = None) -> tuple[int, str]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        if exc.code == 409:
            return exc.code, body
        raise RuntimeError(f"HTTP {exc.code} {url}: {body}") from exc


def api_url(base_url: str, remote_path: str) -> str:
    base = base_url.rstrip("/")
    encoded = "/".join(urllib.parse.quote(part) for part in remote_path.strip("/").split("/") if part)
    return f"{base}/api/contents/{encoded}" if encoded else f"{base}/api/contents"


def ensure_dir(base_url: str, token: str, remote_dir: str) -> None:
    parts = [p for p in remote_dir.strip("/").split("/") if p]
    current = ""
    for part in parts:
        current = f"{current}/{part}".strip("/")
        status, _ = request("PUT", api_url(base_url, current), token, {"type": "directory"})
        if status not in (201, 200, 409):
            raise RuntimeError(f"No se pudo crear directorio remoto {current}: HTTP {status}")


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if any(part.startswith(".") for part in rel.parts):
            continue
        if path.name in SKIP_FILES:
            continue
        if path.is_file():
            files.append(path)
    return sorted(files)


def upload_file(base_url: str, token: str, local: Path, remote: str) -> None:
    content = base64.b64encode(local.read_bytes()).decode("ascii")
    payload = {
        "type": "file",
        "format": "base64",
        "content": content,
    }
    request("PUT", api_url(base_url, remote), token, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sube el repo al workspace Jupyter por API Contents.")
    parser.add_argument("--url", default=os.getenv("JUPYTER_URL", "http://10.200.245.40:18803"))
    parser.add_argument("--token", default=os.getenv("JUPYTER_TOKEN", ""))
    parser.add_argument("--remote-dir", default=os.getenv("JUPYTER_REMOTE_DIR", "Proyecto-LIDIA"))
    args = parser.parse_args()

    if not args.token:
        raise SystemExit("Falta JUPYTER_TOKEN. Copialo desde la URL de Jupyter (?token=...) o desde el panel.")

    files = iter_files()
    ensure_dir(args.url, args.token, args.remote_dir)
    dirs = sorted({str(p.relative_to(ROOT).parent) for p in files if str(p.relative_to(ROOT).parent) != "."})
    for d in dirs:
        ensure_dir(args.url, args.token, f"{args.remote_dir}/{d}")

    for i, path in enumerate(files, 1):
        rel = path.relative_to(ROOT).as_posix()
        remote = f"{args.remote_dir}/{rel}"
        upload_file(args.url, args.token, path, remote)
        print(f"[{i}/{len(files)}] uploaded {remote}")

    print(f"Deploy completo en Jupyter: {args.url}/lab/tree/{urllib.parse.quote(args.remote_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
