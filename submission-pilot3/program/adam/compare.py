#!/usr/bin/env python3
"""Compare the derived Pilot 3 ADaM datasets against the official ADaM.

Reads work/derived/*-yamaa.parquet (produced by run.py) and compares every
cell against ../data/adam/. Reports matched/total columns and cells per
dataset. Exits nonzero on any mismatch.

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
    python3 compare.py --work /tmp/p3         # custom work directory
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


def compare(derived, datasets):
    import polars as pl
    import pyarrow.parquet as pq

    grand_cols, grand_cols_bad = 0, 0
    grand_cells, grand_mismatch = 0, 0
    for ds in datasets:
        keys = KEYS[ds]
        derived_name, official_name = DATASETS[ds]
        new = pl.read_parquet(derived / derived_name)
        ref = pl.read_parquet(OFFICIAL_ADAM / official_name)
        assert new.height == ref.height, (
            f"{ds}: row count {new.height} != official {ref.height}"
        )
        joined = new.join(ref, on=keys, how="inner", suffix="_ref")
        assert joined.height == ref.height, f"{ds}: key mismatch vs official"

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
        new_fields = {
            f.name: dict(f.metadata or {})
            for f in pq.read_schema(derived / derived_name)
        }
        ref_fields = {
            f.name: dict(f.metadata or {})
            for f in pq.read_schema(OFFICIAL_ADAM / official_name)
        }
        label_bad = [
            c
            for c in new.columns
            if c in ref_fields
            and new_fields[c].get(b"yamaa:label")
            != ref_fields[c].get(b"yamaa:label")
        ]
        unlabeled = [
            c for c in new.columns if b"yamaa:label" not in new_fields[c]
        ]
        if label_bad:
            mismatches.append(("labels", label_bad))
        if unlabeled:
            mismatches.append(("unlabeled", unlabeled))

        col_ok = not mismatches and not uncovered
        status = "PASS" if col_ok else (
            f"MISMATCH {mismatches}" if mismatches else f"UNCOVERED {uncovered}"
        )
        print(
            f"-- {ds}: {status} "
            f"({n_cols}/{len(ref.columns)} columns, "
            f"{total_cells - mismatch}/{total_cells} cells match)"
        )
        if derived_only:
            print(f"   derived-only columns (not in official): {derived_only}")
        grand_cols += len(ref.columns)
        grand_cols_bad += 0 if col_ok else 1
        grand_cells += total_cells
        grand_mismatch += mismatch

    print(
        f"TOTAL: {grand_cells - grand_mismatch}/{grand_cells} derived cells match"
    )
    if grand_mismatch or grand_cols_bad:
        sys.exit(1)


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
    missing = [DATASETS[d][0] for d in selected if not (derived / DATASETS[d][0]).exists()]
    if missing:
        sys.exit(f"missing derived files in {derived}: {missing} (run run.py first)")
    compare(derived, selected)
    print("DONE")


if __name__ == "__main__":
    main()
