#!/usr/bin/env python3
"""Compare the derived Pilot 3 ADaM datasets against the official ADaM.

Reusable entry points:

    from compare import compare, compare_domain
    compare("../../data/adam/adsl-yamaa.parquet", "../../data/adam/adsl.parquet",
            "adsl", spec="../../spec/yamaa/adsl.yaml")
    compare_domain("adsl")   # resolves the standard paths and compares

Reports matched/total columns and cells per dataset. Exits nonzero on any
mismatch when run as a script.

Numeric cells match exactly or within absolute tolerance 1e-10, reported
separately. Text/null values match exactly; blank/null differences are
reported separately and fail. Keys must be unique and have identical sets.
Saved field labels and, when supplied, declared labels are checked.

Requires: polars, pyarrow, PyYAML.

Usage:
    python3 compare.py                        # all five datasets
    python3 compare.py --datasets adsl,adtte  # subset
    python3 compare.py --data-root /tmp/p3/data  # custom data directory
"""

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
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


def _spec_labels(spec):
    """Declared labels from a yamaa YAML specification."""
    import yaml

    columns = yaml.safe_load(Path(spec).read_text(encoding="utf-8"))["columns"]
    return {column["name"]: column.get("label") for column in columns}


def compare(output, reference, name, spec=None):
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
    assert not new.select(keys).is_duplicated().any(), f"{name}: duplicate derived keys"
    assert not ref.select(keys).is_duplicated().any(), f"{name}: duplicate reference keys"
    assert new.join(ref.select(keys), on=keys, how="anti", nulls_equal=True).height == 0, (
        f"{name}: extra derived keys"
    )
    assert ref.join(new.select(keys), on=keys, how="anti", nulls_equal=True).height == 0, (
        f"{name}: missing derived keys"
    )
    joined = new.join(ref, on=keys, how="inner", suffix="_ref", nulls_equal=True)
    assert joined.height == ref.height, f"{name}: key mismatch vs official"

    common = [c for c in new.columns if c not in keys and c in ref.columns]
    derived_only = [
        c for c in new.columns if c not in keys and c not in ref.columns
    ]
    uncovered = [c for c in ref.columns if c not in keys and c not in new.columns]

    total_cells = ref.height * ref.width
    mismatch = ref.height * len(uncovered)
    exact_cells = ref.height * len(keys)
    tolerance_cells = 0
    blank_null_cells = 0
    mismatches = []
    for col in common:
        a, b = joined[col], joined[col + "_ref"]
        if a.dtype.is_numeric() and b.dtype.is_numeric():
            a = a.fill_nan(None).cast(pl.Float64)
            b = b.fill_nan(None).cast(pl.Float64)
            exact = ((a.is_null() & b.is_null()) | (a == b)).fill_null(False)
            close = (~exact & ((a - b).abs() <= TOLERANCE)).fill_null(False)
            ok = exact | close
            tolerance_cells += close.sum()
        else:
            a, b = a.cast(pl.String), b.cast(pl.String)
            exact = ((a.is_null() & b.is_null()) | (a == b)).fill_null(False)
            blank = ~exact & (a.fill_null("") == b.fill_null(""))
            blank_null_cells += blank.sum()
            ok = exact
        exact_cells += exact.sum()
        bad = (~ok).sum()
        if bad:
            mismatches.append((col, bad))
            mismatch += bad
    n_cols = len(common) + len(keys)

    # Verify the delivered artifact's metadata, not just the YAML declaration.
    new_labels = _labels(output)
    ref_labels = _labels(reference)
    if ref_labels:
        label_bad = [
            c
            for c in new.columns
            if c in ref_labels and (
                new_labels.get(c) != ref_labels[c]
            )
        ]
        unlabeled = [c for c in new.columns if not new_labels.get(c)]
        if label_bad:
            mismatches.append(("labels", label_bad))
        if unlabeled:
            mismatches.append(("unlabeled", unlabeled))
        if spec:
            declared = _spec_labels(spec)
            declared_bad = [c for c in ref.columns if (
                declared.get(c).encode() if declared.get(c) else None
            ) != ref_labels.get(c)]
            if declared_bad:
                mismatches.append(("declared_labels", declared_bad))

    if derived_only:
        mismatches.append(("extra_columns", derived_only))
    if new.columns != ref.columns:
        mismatches.append(("column_order", "differs"))
    ok = not mismatches and not uncovered
    status = "PASS" if ok else (
        f"MISMATCH {mismatches}" if mismatches else f"UNCOVERED {uncovered}"
    )
    report = (
        f"-- {name}: {status} "
        f"({n_cols}/{len(ref.columns)} columns, "
        f"{total_cells - mismatch}/{total_cells} cells match; "
        f"exact={exact_cells}, tolerance-only={tolerance_cells}, "
        f"blank/null={blank_null_cells})"
    )
    print(report)
    if derived_only:
        print(f"   derived-only columns (not in official): {derived_only}")
    return {
        "name": name,
        "columns": (n_cols, len(ref.columns)),
        "cells": (total_cells - mismatch, total_cells),
        "exact_cells": exact_cells,
        "tolerance_cells": tolerance_cells,
        "blank_null_cells": blank_null_cells,
        "ok": ok,
        "report": report,
    }


def compare_domain(name, data_root=None):
    """Compare one dataset using the standard pipeline paths.

    Loads data/adam/<name>-yamaa.parquet (produced by run.py) against
    data/adam/<name>.parquet.
    """
    data_root = Path(data_root) if data_root else STUDY / "data"
    derived_name, official_name = DATASETS[name]
    return compare(data_root / "adam" / derived_name, OFFICIAL_ADAM / official_name,
                   name, STUDY / "spec" / "yamaa" / f"{name}.yaml")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--datasets",
        default=",".join(DATASETS),
        help="comma-separated subset, e.g. adsl,adtte",
    )
    ap.add_argument("--data-root", default=str(STUDY / "data"))
    args = ap.parse_args()

    selected = [d.strip() for d in args.datasets.split(",") if d.strip()]
    unknown = [d for d in selected if d not in DATASETS]
    if unknown:
        sys.exit(f"unknown datasets: {unknown} (choose from {list(DATASETS)})")

    derived = Path(args.data_root) / "adam"
    missing = [
        DATASETS[d][0] for d in selected if not (derived / DATASETS[d][0]).exists()
    ]
    if missing:
        sys.exit(f"missing derived files in {derived}: {missing} (run run.py first)")

    results = [compare_domain(ds, args.data_root) for ds in selected]
    total_cells = sum(r["cells"][1] for r in results)
    matched_cells = sum(r["cells"][0] for r in results)
    print(f"TOTAL: {matched_cells}/{total_cells} derived cells match")
    if not all(r["ok"] for r in results):
        sys.exit(1)
    print("DONE")


if __name__ == "__main__":
    main()
