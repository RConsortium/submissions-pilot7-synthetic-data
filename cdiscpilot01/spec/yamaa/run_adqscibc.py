#!/usr/bin/env python3
"""ADQSCIBC full-data staged pipeline runner.

Runs each yamaa stage spec, recasts large_string -> string for stage
interoperability, unions natural + LOCF rows (pure UNION plumbing, no
derivation), and runs the final 36-column spec.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import polars as pl

BASE = Path(__file__).resolve().parent
VENV_PY = Path(sys.executable)

# (spec file, domain, staged output name)
STAGES = [
    ("adqscibc-s1.yaml", "adqscibc_s1", "adqscibc-s1.parquet"),
    ("adqscibc-s2.yaml", "adqscibc_s2", "adqscibc-s2.parquet"),
    ("adqscibc-s3a.yaml", "adqscibc_s3a", "adqscibc-s3a.parquet"),
    ("adqscibc-s3b.yaml", "adqscibc_s3b", "adqscibc-s3b.parquet"),
    ("adqscibc-s3c.yaml", "adqscibc_s3c", "adqscibc-s3c.parquet"),
    ("adqscibc-s3d.yaml", "adqscibc_s3d", "adqscibc-s3d.parquet"),
    ("adqscibc-s4j.yaml", "adqscibc_s4j", "adqscibc-s4j.parquet"),
    ("adqscibc-s4.yaml", "adqscibc_s4", "adqscibc-s4.parquet"),
    ("adqscibc-s5j.yaml", "adqscibc_s5j", "adqscibc-s5j.parquet"),
    ("adqscibc-s5.yaml", "adqscibc_s5", "adqscibc-s5.parquet"),
]


def recast(path: Path) -> None:
    """Cast large_string -> string in place (yamaa reader needs pa.string())."""
    t = pq.read_table(path)
    new_cols = []
    for f in t.schema:
        col = t.column(f.name)
        if pa.types.is_large_string(f.type):
            col = col.cast(pa.string())
        new_cols.append(col)
    t = pa.table(new_cols, names=t.schema.names)
    pq.write_table(t, path)


def run_stage(spec: str, domain: str, staged: str) -> None:
    print(f"=== {spec} ===", flush=True)
    r = subprocess.run(
        [str(VENV_PY), str(BASE / "run_spec.py"), str(BASE / spec)],
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=1200,
    )
    print(r.stdout[-2000:] if r.stdout else "")
    if r.returncode != 0:
        print(r.stderr[-3000:] if r.stderr else "")
        raise SystemExit(f"stage {spec} failed (rc={r.returncode})")
    src = BASE / "output" / f"{domain}.parquet"
    dst = BASE / staged
    if not src.exists():
        raise SystemExit(f"stage {spec}: expected output {src} not found")
    shutil.copy(src, dst)
    recast(dst)
    t = pq.read_table(dst)
    print(f"  -> {staged}: {t.num_rows} x {t.num_columns}", flush=True)


def main() -> None:
    only = sys.argv[1:]  # optional: run only named specs
    for spec, domain, staged in STAGES:
        if only and spec not in only:
            continue
        run_stage(spec, domain, staged)
    if only:
        return

    # UNION plumbing: natural + LOCF rows (no derivation, just concat).
    print("=== union ===", flush=True)
    s2 = pl.read_parquet(BASE / "adqscibc-s2.parquet")
    s4 = pl.read_parquet(BASE / "adqscibc-s4.parquet")
    s5 = pl.read_parquet(BASE / "adqscibc-s5.parquet")
    # Align: s4/s5 lack _RANK? ensure identical column sets.
    all_cols = s2.columns
    for name, df in [("s4", s4), ("s5", s5)]:
        missing = [c for c in all_cols if c not in df.columns]
        extra = [c for c in df.columns if c not in all_cols]
        if missing or extra:
            raise SystemExit(f"{name} schema mismatch: missing={missing} extra={extra}")
    comb = pl.concat([s2, s4.select(all_cols), s5.select(all_cols)], how="vertical")
    # Recast large_string -> string for the yamaa reader.
    comb_path = BASE / "adqscibc-combined.parquet"
    at = comb.to_arrow()
    new_cols = [c.cast(pa.string()) if pa.types.is_large_string(f.type) else c
                for f, c in zip(at.schema, at.columns)]
    pq.write_table(pa.table(new_cols, names=at.schema.names), comb_path)
    print(f"  -> adqscibc-combined.parquet: {comb.shape[0]} x {comb.shape[1]}", flush=True)

    run_stage("adqscibc-final.yaml", "adqscibc", "adqscibc-final.parquet")


if __name__ == "__main__":
    main()
