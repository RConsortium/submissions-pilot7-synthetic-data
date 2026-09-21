#!/usr/bin/env python3
"""Compare the derived Pilot 3 ADaM datasets against the official ADaM.

Reusable entry points:

    from compare import compare, compare_domain
    compare("work/derived/adsl-yamaa.parquet", "../data/adam/adsl.parquet", "adsl")
    compare_domain("adsl")   # resolves the standard paths and compares

Reports matched/total columns and cells per dataset. Exits nonzero on any
mismatch when run as a script.

Semantics (standing tolerance): numeric cells match when
|derived - official| <= 1e-10 (absolute); non-numeric cells match exactly
with null/"" normalized (the official ADaM was produced by R, where a
missing character value is ""). Key columns align with zero unmatched
rows on either side and count as matched. Variable labels must agree on
every column carrying the official `yamaa:label` field metadata.

Requires: polars, pyarrow.

Usage:
    python3 compare.py                        # all five datasets
    python3 compare.py --datasets adsl,adtte  # subset
    python3 compare.py --work /tmp/p3          # custom work directory
"""

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
OFFICIAL_ADAM = STUDY / "data" / "adam"

# dataset -> (derived file name, official file name)
DATASETS = {
    "adsl": ("adsl-yamaa.parquet", "adsl.parquet"),
    "adae": ("adae-yamaa.parquet", "adae.parquet"),
    "adadas": ("adadas-yamaa.parquet", "adadas.parquet"),
    "adtte": ("adtte-yamaa.parquet", "adtte.parquet"),
    "adlbc": ("adlbc-yamaa.parquet", "adlbc.parquet"),
}

# Row-alignment keys for the comparison (unique in both derived and official).
KEYS = {
    "adsl": ["STUDYID", "USUBJID"],
    "adae": ["STUDYID", "USUBJID", "AESEQ"],
    "adadas": ["STUDYID", "USUBJID", "PARAMCD", "AVISIT", "ADT"],
    "adtte": ["STUDYID", "USUBJID"],
    "adlbc": ["STUDYID", "USUBJID", "PARAMCD", "AVISIT", "LBSEQ"],
}

TOLERANCE = 1e-10


def _as_frame(source):
    """Accept a parquet path or an in-memory polars frame."""
    import polars as pl

    return source if isinstance(source, pl.DataFrame) else pl.read_parquet(source)


def _labels(source):
    """`yamaa:label` field metadata per column (paths only; frames carry none)."""
    if isinstance(source, (str, Path)):
        import pyarrow.parquet as pq

        return {
            field.name: dict(field.metadata or {}).get(b"yamaa:label")
            for field in pq.read_schema(source)
        }
    return {}


def compare(output, reference, name):
    """Compare one derived dataset against its official reference.

    `output`/`reference` are parquet paths (or polars DataFrames).
    Prints a one-line report and returns a dict with matched/total
    columns and cells plus an `ok` flag.
    """
    import polars as pl

    keys = KEYS[name]
    new, ref = _as_frame(output), _as_frame(reference)
    assert new.height == ref.height, (
        f"{name}: row count {new.height} != official {ref.height}"
    )
    joined = new.join(ref, on=keys, how="inner", suffix="_ref")
    assert joined.height == ref.height, f"{name}: key mismatch vs official"

    common = [c for c in new.columns if c not in keys and c in ref.columns]
    derived_only = [
        c for c in new.columns if c not in keys and c not in ref.columns
    ]
    uncovered = [c for c in ref.columns if c not in keys and c not in new.columns]

    total_cells = new.height * (len(common) + len(keys))
    mismatch = 0
    mismatches = []
    for col in common:
        a, b = joined[col], joined[col + "_ref"]
        if a.dtype.is_numeric() and b.dtype.is_numeric():
            a = a.fill_nan(None).cast(pl.Float64)
            b = b.fill_nan(None).cast(pl.Float64)
            ok = (
                (a.is_null() & b.is_null()) | ((a - b).abs() <= TOLERANCE)
            ).fill_null(False)  # exactly-one-null is a mismatch
        else:
            ok = a.cast(pl.String).fill_null("") == b.cast(pl.String).fill_null("")
        bad = (~ok).sum()
        if bad:
            mismatches.append((col, bad))
            mismatch += bad
    n_cols = len(common) + len(keys)

    # Labels: every derived field must carry the official yamaa:label.
    new_labels, ref_labels = _labels(output), _labels(reference)
    if new_labels and ref_labels:
        label_bad = [
            c
            for c in new.columns
            if c in ref_labels and new_labels.get(c) != ref_labels[c]
        ]
        unlabeled = [c for c in new.columns if c not in new_labels]
        if label_bad:
            mismatches.append(("labels", label_bad))
        if unlabeled:
            mismatches.append(("unlabeled", unlabeled))

    ok = not mismatches and not uncovered
    status = "PASS" if ok else (
        f"MISMATCH {mismatches}" if mismatches else f"UNCOVERED {uncovered}"
    )
    report = (
        f"-- {name}: {status} "
        f"({n_cols}/{len(ref.columns)} columns, "
        f"{total_cells - mismatch}/{total_cells} cells match)"
    )
    print(report)
    if derived_only:
        print(f"   derived-only columns (not in official): {derived_only}")
    return {
        "name": name,
        "columns": (n_cols, len(ref.columns)),
        "cells": (total_cells - mismatch, total_cells),
        "ok": ok,
        "report": report,
    }


def compare_domain(name, work=None):
    """Compare one dataset using the standard pipeline paths.

    Loads work/derived/<name>-yamaa.parquet (produced by run.py) against
    ../data/adam/<name>.parquet.
    """
    work = Path(work) if work else HERE / "work"
    derived_name, official_name = DATASETS[name]
    return compare(work / "derived" / derived_name, OFFICIAL_ADAM / official_name, name)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--datasets",
        default=",".join(DATASETS),
        help="comma-separated subset, e.g. adsl,adtte",
    )
    ap.add_argument("--work", default=str(HERE / "work"))
    args = ap.parse_args()

    selected = [d.strip() for d in args.datasets.split(",") if d.strip()]
    unknown = [d for d in selected if d not in DATASETS]
    if unknown:
        sys.exit(f"unknown datasets: {unknown} (choose from {list(DATASETS)})")

    derived = Path(args.work) / "derived"
    missing = [
        DATASETS[d][0] for d in selected if not (derived / DATASETS[d][0]).exists()
    ]
    if missing:
        sys.exit(f"missing derived files in {derived}: {missing} (run run.py first)")

    results = [compare_domain(ds, args.work) for ds in selected]
    total_cells = sum(r["cells"][1] for r in results)
    matched_cells = sum(r["cells"][0] for r in results)
    print(f"TOTAL: {matched_cells}/{total_cells} derived cells match")
    if not all(r["ok"] for r in results):
        sys.exit(1)
    print("DONE")


if __name__ == "__main__":
    main()
