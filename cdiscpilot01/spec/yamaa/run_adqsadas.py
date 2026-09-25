#!/usr/bin/env python3
"""ADQSADAS full-data native staged pipeline runner.

Stages (all native yamaa; Python only orchestrates and normalizes):
  S1: window assignment + closest-to-target selection per QS record.
  S2: ACTOT forward-fill of the selected analysis value (_CARRIED/_DTYPE).
  S2SUBJ: per-subject latest-record keys + empty-window flags.
  S3: empty-window LOCF rows for ACTOT.
  final: union of item/ACTOT/LOCF rows with BASE/CHG/PCHG + ADSL covariates.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

BASE = Path(__file__).resolve().parent
VENV_PY = Path(sys.executable)

STAGES = [
    ("adqsadas-s1.yaml", "adqsadas_s1"),
    ("adqsadas-s2.yaml", "adqsadas_s2"),
    ("adqsadas-s2subj.yaml", "adqsadas_s2subj"),
    ("adqsadas-s3.yaml", "adqsadas_s3"),
    ("adqsadas-final.yaml", "adqsadas"),
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


def run_stage(spec: str, domain: str) -> None:
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
    out = BASE / "output" / f"{domain}.parquet"
    if not out.exists():
        raise SystemExit(f"stage {spec}: expected output {out} not found")
    if domain != "adqsadas":
        recast(out)
    t = pq.read_table(out)
    print(f"  -> {domain}: {t.num_rows} x {t.num_columns}", flush=True)


def main() -> None:
    only = sys.argv[1:]
    for spec, domain in STAGES:
        if only and spec not in only:
            continue
        run_stage(spec, domain)


if __name__ == "__main__":
    main()
