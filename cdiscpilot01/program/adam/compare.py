#!/usr/bin/env python3
"""Strict compare: derived vs official Pilot 1 ADaM parquet.

Compares adam/<ds>-yamaa.parquet against ../../data/adam/<ds>.parquet.
Checks: shape, column order, Arrow types, yamaa:label metadata,
and every cell. Numeric cells match when |derived - official| <= 1e-10
(absolute). Non-numeric cells must be exact. Null vs "" are distinct
(no normalization).

Exit code nonzero on any mismatch.
"""
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

BASE = Path(__file__).resolve().parent
EXPECTED = BASE.parent.parent / "data" / "adam"
DATASETS = ["adsl", "adae", "adtte", "advs", "adlbc", "adlbh",
            "adlbhy", "adqsnipx"]
# Official ADaM filenames; derived names match spec filenames.
EXPECTED_NAMES = {"adqsnipx": "adqsnpix"}
ABS_TOL = 1e-10


def compare(ds: str) -> bool:
    exp_t = pq.read_table(EXPECTED / f"{EXPECTED_NAMES.get(ds, ds)}.parquet")
    got_t = pq.read_table(BASE / "adam" / f"{ds}-yamaa.parquet")
    ok = True
    missing = set(exp_t.schema.names) - set(got_t.schema.names)
    bad_columns = set(missing)
    total_cells = exp_t.num_rows * exp_t.num_columns
    bad_cells = exp_t.num_rows * len(missing)

    def report(msg: str) -> None:
        nonlocal ok
        ok = False
        print(f"MISMATCH [{ds}]: {msg}")

    if (exp_t.num_rows, exp_t.num_columns) != (got_t.num_rows, got_t.num_columns):
        report(f"shape exp={(exp_t.num_rows, exp_t.num_columns)} "
               f"got={(got_t.num_rows, got_t.num_columns)}")
    if exp_t.schema.names != got_t.schema.names:
        report("column order/names differ")

    for f in exp_t.schema:
        if f.name not in got_t.schema.names:
            continue
        g = got_t.schema.field(f.name)
        text_types = (pa.types.is_string(f.type) or pa.types.is_large_string(f.type)) and (
            pa.types.is_string(g.type) or pa.types.is_large_string(g.type)
        )
        if not (f.type.equals(g.type) or text_types):
            report(f"type {f.name}: exp={f.type} got={g.type}")
            bad_columns.add(f.name)
        el = (f.metadata or {}).get(b"yamaa:label", b"")
        gl = (g.metadata or {}).get(b"yamaa:label", b"")
        if el != gl:
            report(f"label {f.name}: exp={el!r} got={gl!r}")
            bad_columns.add(f.name)

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
            elif isinstance(a, float) or isinstance(b, float):
                if not (a == b or abs(a - b) <= ABS_TOL):
                    bad += 1
            elif a != b:
                bad += 1
            if bad and len(ex) < 3:
                ex.append((i, a, b))
        if bad:
            report(f"col {name}: {bad}/{len(e)} cells differ, e.g. {ex}")
            bad_columns.add(name)
            bad_cells += bad

    print(f"{'PASS' if ok else 'FAIL'}: {ds} "
          f"{exp_t.num_columns - len(bad_columns)}/{exp_t.num_columns} columns, "
          f"{total_cells - bad_cells}/{total_cells} cells")
    return ok


def main() -> None:
    only = [d.lower() for d in sys.argv[1:]] or DATASETS
    all_ok = True
    for ds in only:
        if ds not in DATASETS:
            raise SystemExit(f"unknown dataset: {ds}")
        all_ok = compare(ds) and all_ok
    if not all_ok:
        raise SystemExit("FAIL: one or more datasets mismatched")


if __name__ == "__main__":
    main()
