#!/usr/bin/env python3
"""Strict compare: derived vs official Pilot 01 ADaM parquet.

Compares output/<ds>.parquet against expected/<ds>.parquet for all ten
datasets, in file order with NO realignment. Checks:

 1. row count, column count, exact column order
 2. Arrow field types exact
 3. yamaa:label field metadata exact
 4. every cell value: null vs "" distinct; non-numerics exact; floats
    exact or within a tiny relative tolerance (reported as
    close_float_cells, not failures)

Exit code is nonzero on any mismatch.
"""
import sys
from pathlib import Path

import pyarrow.parquet as pq

BASE = Path(__file__).resolve().parent
DATASETS = ["adsl", "adae", "adtte", "advs", "adlbh", "adlbc",
            "adlbhy", "adqsadas", "adqscibc", "adqsnipx"]


def compare(ds: str) -> tuple[bool, int, int, int]:
    exp_t = pq.read_table(BASE / "expected" / f"{ds}.parquet")
    got_t = pq.read_table(BASE / "output" / f"{ds}.parquet")
    bad_cols = 0
    close_float_cells = 0
    ok = True

    def report(msg: str) -> None:
        nonlocal ok
        ok = False
        print(f"MISMATCH [{ds}]: {msg}")

    if (exp_t.num_rows, exp_t.num_columns) != (got_t.num_rows, got_t.num_columns):
        report(f"shape exp={(exp_t.num_rows, exp_t.num_columns)} "
               f"got={(got_t.num_rows, got_t.num_columns)}")
    if exp_t.schema.names != got_t.schema.names:
        eg, gg = set(exp_t.schema.names), set(got_t.schema.names)
        report(f"column order differs; only-exp={sorted(eg - gg)} "
               f"only-got={sorted(gg - eg)}")

    for f in exp_t.schema:
        if f.name not in got_t.schema.names:
            continue
        g = got_t.schema.field(f.name)
        if not f.type.equals(g.type):
            report(f"type {f.name}: exp={f.type} got={g.type}")
        el = (f.metadata or {}).get(b"yamaa:label", b"")
        gl = (g.metadata or {}).get(b"yamaa:label", b"")
        if el != gl:
            report(f"label {f.name}: exp={el!r} got={gl!r}")

    for f in exp_t.schema:
        name = f.name
        if name not in got_t.schema.names:
            continue
        e = exp_t.column(name).to_pylist()
        g = got_t.column(name).to_pylist()
        if len(e) != len(g):
            continue
        bad, ex = 0, []
        for i, (a, b) in enumerate(zip(e, g)):
            if a is None and b is None:
                continue
            if (a is None) != (b is None):
                bad += 1
                if len(ex) < 3:
                    ex.append((i, a, b))
                continue
            if isinstance(a, float) or isinstance(b, float):
                if a == b:
                    continue
                # inexact-but-close: reported, not counted as bad
                if abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b)):
                    close_float_cells += 1
                    continue
                bad += 1
                if len(ex) < 3:
                    ex.append((i, a, b))
            elif a != b:
                bad += 1
                if len(ex) < 3:
                    ex.append((i, a, b))
        if bad:
            bad_cols += 1
            report(f"col {name}: {bad}/{len(e)} cells differ, e.g. {ex}")

    print(f"{'STRICT PASS' if ok else 'STRICT FAIL'}: {ds} "
          f"{got_t.num_rows} x {got_t.num_columns} "
          f"bad_cols={bad_cols} close_float_cells={close_float_cells}")
    return ok, got_t.num_rows, got_t.num_columns, bad_cols


def main() -> None:
    only = [d.lower() for d in sys.argv[1:]] or DATASETS
    all_ok = True
    for ds in only:
        if ds not in DATASETS:
            raise SystemExit(f"unknown dataset: {ds}")
        ok, *_ = compare(ds)
        all_ok = all_ok and ok
    if not all_ok:
        raise SystemExit("STRICT FAIL: one or more datasets mismatched")


if __name__ == "__main__":
    main()
