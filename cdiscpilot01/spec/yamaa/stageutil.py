#!/usr/bin/env python3
"""Shared helpers for the Pilot 01 yamaa orchestration runners.

Python's role here is orchestration only: run yamaa specs in order,
recast Arrow string types between stages, join the yamaa-derived
PREV_AVAL map back onto LB, and concatenate stage outputs. No analysis
variables are derived in Python.
"""
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

BASE = Path(__file__).resolve().parent
PY = Path(sys.executable)


def recast(path: Path) -> None:
    """Cast large_string -> string in place (the yamaa reader needs pa.string())."""
    t = pq.read_table(path)
    new_cols = []
    for f in t.schema:
        col = t.column(f.name)
        if pa.types.is_large_string(f.type):
            col = col.cast(pa.string())
        new_cols.append(col)
    pq.write_table(pa.table(new_cols, names=t.schema.names), path)


def run_yamaa(spec: str, timeout: int = 1800) -> Path:
    """Run one spec with run_spec.py; return its output parquet path."""
    import yaml

    print(f"=== {spec} ===", flush=True)
    r = subprocess.run(
        [str(PY), str(BASE / "run_spec.py"), str(BASE / spec)],
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    print(r.stdout[-2000:] if r.stdout else "")
    if r.returncode != 0:
        print(r.stderr[-3000:] if r.stderr else "")
        raise SystemExit(f"spec {spec} failed (rc={r.returncode})")
    # run_spec.py writes output/<domain>.parquet (domain lowercased).
    with open(BASE / spec) as f:
        domain = yaml.safe_load(f)["domain"].lower()
    out = BASE / "output" / f"{domain}.parquet"
    if not out.exists():
        raise SystemExit(f"spec {spec}: expected output {out} not found")
    return out


def promote(domain: str) -> Path:
    """Copy output/<domain>.parquet to upstream/<domain>.parquet (plain strings)."""
    src = BASE / "output" / f"{domain}.parquet"
    dst = BASE / "upstream" / f"{domain}.parquet"
    if not src.exists():
        raise SystemExit(f"promote: expected output {src} not found")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
    recast(dst)
    t = pq.read_table(dst)
    print(f"  -> upstream/{domain}.parquet: {t.num_rows} x {t.num_columns}", flush=True)
    return dst
