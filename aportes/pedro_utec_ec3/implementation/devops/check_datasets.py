from __future__ import annotations

from pathlib import Path

from devops.common import ROOT, load_env, new_run_id, timed_check


def check_paths() -> dict:
    env = load_env()
    default_external = ROOT.parent
    default_shp = default_external / "DL_FIRE_M-C61_740435" / "fire_archive_M-C61_740435.shp"
    candidates = {
        "project_data": ROOT / "data",
        "external_data": Path(env.get("DIR_DATOS_EXTERNOS", str(default_external))),
        "firms_shapefile": Path(env.get("FIRMS_SHAPEFILE_PATH", str(default_shp))),
    }
    detail = {}
    for name, path in candidates.items():
        if path is None:
            detail[name] = {"configured": False}
        else:
            detail[name] = {"path": str(path), "exists": path.exists(), "size": path.stat().st_size if path.is_file() else None}
    return detail


def check_parquet_csv() -> dict:
    env = load_env()
    roots = [ROOT / "data", Path(env.get("DIR_DATOS_EXTERNOS", str(ROOT.parent)))]
    files = []
    for root in roots:
        if root.exists():
            files.extend(list(root.rglob("*.parquet"))[:50])
            files.extend(list(root.rglob("*.csv"))[:50])
    return {"files_found": len(files), "sample": [str(p) for p in files[:80]]}


def check_read_sample() -> dict:
    import pandas as pd

    env = load_env()
    roots = [ROOT / "data", Path(env.get("DIR_DATOS_EXTERNOS", str(ROOT.parent)))]
    for root in roots:
        if not root.exists():
            continue
        for path in list(root.rglob("*.parquet")) + list(root.rglob("*.csv")):
            if path.suffix == ".parquet":
                df = pd.read_parquet(path)
            else:
                df = pd.read_csv(path, nrows=100)
            return {"path": str(path), "shape": df.shape, "columns": list(df.columns)}
    raise FileNotFoundError("No se encontraron CSV/Parquet en data o DIR_DATOS_EXTERNOS")


def check_firms_shapefile_sample() -> dict:
    env = load_env()
    shp = env.get("FIRMS_SHAPEFILE_PATH") or str(
        ROOT.parent / "DL_FIRE_M-C61_740435" / "fire_archive_M-C61_740435.shp"
    )
    path = Path(shp)
    if not path.exists():
        processed = Path(env.get("DIR_DATOS_EXTERNOS", str(ROOT.parent))) / "processed" / "firms_procesado.parquet"
        if processed.exists():
            import pandas as pd

            df = pd.read_parquet(processed)
            return {
                "mode": "processed_fallback",
                "reason": f"shapefile no disponible en {path}",
                "path": str(processed),
                "shape": df.shape,
                "columns": list(df.columns),
            }
        raise FileNotFoundError(str(path))
    import pyogrio

    info = pyogrio.read_info(path)
    df = pyogrio.read_dataframe(path, max_features=100)
    return {
        "path": str(path),
        "features": info.get("features"),
        "crs": str(info.get("crs")),
        "geometry_type": info.get("geometry_type"),
        "sample_shape": df.shape,
        "columns": list(df.columns),
    }


def main() -> int:
    run_id = new_run_id()
    print(f"run_id={run_id}")
    checks = [
        ("datasets_paths", check_paths),
        ("datasets_files", check_parquet_csv),
        ("datasets_read_sample", check_read_sample),
        ("firms_shapefile_sample", check_firms_shapefile_sample),
    ]
    results = [timed_check(run_id, name, fn) for name, fn in checks]
    fails = sum(1 for r in results if r.status != "PASS")
    print(f"SUMMARY: {len(results)-fails} PASS / {fails} FAIL")
    print(f"log=logs/devops/{run_id}.jsonl")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
