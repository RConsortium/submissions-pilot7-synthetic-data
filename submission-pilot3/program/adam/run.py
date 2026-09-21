#!/usr/bin/env python3
"""End-to-end regeneration of the Pilot 3 ADaM datasets from yamaa specs.

Stages the SDTM parquets from ../data/sdtm/ into a work/ directory, runs the
specs in dependency order (derived ADSL/ADAE are staged as predecessors
where downstream specs need them), writes the five derived datasets to
work/derived/, and compares every derived cell against the official ADaM in
../data/adam/.

Every derivation lives in the YAML specs (plus the hand-built planning
relations in inputs/, which mirror the R program's tribbles); run.py only
stages inputs, runs the specs, and verifies.

Requires: the yamaa engine pinned in requirements.txt, polars, pyarrow.

Usage:
    python3 run.py                          # all five datasets, then compare
    python3 run.py --datasets adsl,adtte   # subset (predecessors auto-included)
    python3 run.py --no-compare            # derive only
    python3 run.py --work /tmp/p3          # custom work directory
"""

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
SDTM_SRC = STUDY / "data" / "sdtm"
OFFICIAL_ADAM = STUDY / "data" / "adam"

# SDTM inputs staged verbatim from ../data/sdtm/.
SDTM_INPUTS = [
    "dm", "ds", "ex", "qs", "sv", "vs", "sc", "mh", "ae", "lb", "supplb",
]

# dataset -> (spec stages, predecessor datasets, derived file name, spec output)
STAGES = {
    "adsl": (
        ["adsl_exdose.yaml", "adsl.yaml"],
        [],
        "adsl.parquet",
        "adsl-out.parquet",
    ),
    "adae": (["adae.yaml"], ["adsl"], "adae.parquet", "adae-out.parquet"),
    "adadas": (["adadas.yaml"], ["adsl"], "adadas.parquet", "adadas-out.parquet"),
    "adtte": (
        ["adtte.yaml"],
        ["adsl", "adae"],
        "adtte.parquet",
        "adtte-out.parquet",
    ),
    "adlbc": (["adlbc.yaml"], ["adsl"], "adlbc.parquet", "adlbc-out.parquet"),
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


def ordered_datasets(selected):
    """Expand the selection with required predecessors, dependency-first."""
    order, seen = [], set()

    def visit(ds):
        if ds in seen:
            return
        seen.add(ds)
        for dep in STAGES[ds][1]:
            visit(dep)
        order.append(ds)

    for ds in selected:
        visit(ds)
    return order


def run_spec(spec_path, work):
    from yamaa import yamaa_domain

    run = yamaa_domain(str(spec_path), project_root=str(work))
    issues = run.issues
    if issues is not None and len(issues):
        print(f"VALIDATION FAILED for {spec_path.name}:")
        print(issues)
        sys.exit(1)
    frame = run.output
    if frame is None:
        print(f"ERROR: {spec_path.name} produced no output")
        sys.exit(1)
    out = run.save()
    print(f"  {spec_path.name}: VALIDATION CLEAN, {frame.height} rows -> {out}")
    return out


def derive(datasets, work):
    sdtm = work / "sdtm"
    sdtm.mkdir(parents=True, exist_ok=True)
    for name in SDTM_INPUTS:
        shutil.copy2(SDTM_SRC / f"{name}.parquet", sdtm / f"{name}.parquet")
    print(f"staged {len(SDTM_INPUTS)} SDTM parquets")

    inputs = work / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    for name in ["plan.parquet", "aw_lookup.parquet", "qs_str.parquet"]:
        shutil.copy2(HERE / "inputs" / name, inputs / name)
    shutil.copy2(HERE / "inputs" / "qs_str.parquet", sdtm / "qs_str.parquet")
    print("staged planning inputs (plan, aw_lookup, qs_str)")

    adam = work / "adam"
    adam.mkdir(parents=True, exist_ok=True)

    for spec_name in {s for ds in STAGES for s in STAGES[ds][0]}:
        shutil.copy2(HERE / spec_name, work / spec_name)

    derived = work / "derived"
    derived.mkdir(exist_ok=True)

    for ds in datasets:
        print(f"== {ds} ==")
        for stage in STAGES[ds][0]:
            run_spec(work / stage, work)
        _, _, canon_name, spec_out = STAGES[ds]
        shutil.copy2(work / spec_out, derived / canon_name)
        # Stage the derived dataset as a predecessor for downstream specs.
        if ds in ("adsl", "adae"):
            shutil.copy2(derived / canon_name, adam / canon_name)
        print(f"  wrote derived/{canon_name}")
    return derived


def compare(derived, datasets):
    """Verify every derived cell against the official ADaM.

    Semantics (standing tolerance): numeric cells match when
    |derived - official| <= 1e-10 (absolute); non-numeric cells match exactly
    with null/"" normalized (the official ADaM was produced by R, where a
    missing character value is ""). Key columns align with zero unmatched
    rows on either side and count as matched.
    """
    import polars as pl

    grand_cells, grand_mismatch = 0, 0
    for ds in datasets:
        keys = KEYS[ds]
        _, _, canon_name, _ = STAGES[ds]
        new = pl.read_parquet(derived / canon_name)
        ref = pl.read_parquet(OFFICIAL_ADAM / canon_name)
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
        status = "PASS" if not mismatches and not uncovered else (
            f"MISMATCH {mismatches}" if mismatches else f"UNCOVERED {uncovered}"
        )
        print(
            f"-- {ds}: {status} ({n_cols}/{len(ref.columns)} columns, "
            f"{total_cells - mismatch}/{total_cells} cells match)"
        )
        if derived_only:
            print(f"   derived-only columns (not in official): {derived_only}")
        grand_cells += total_cells
        grand_mismatch += mismatch
    print(
        f"TOTAL: {grand_cells - grand_mismatch}/{grand_cells} derived cells match"
    )
    if grand_mismatch:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--datasets",
        default=",".join(STAGES),
        help="comma-separated subset, e.g. adsl,adtte",
    )
    ap.add_argument("--no-compare", action="store_true")
    ap.add_argument("--work", default=str(HERE / "work"))
    args = ap.parse_args()

    selected = [d.strip() for d in args.datasets.split(",") if d.strip()]
    unknown = [d for d in selected if d not in STAGES]
    if unknown:
        sys.exit(f"unknown datasets: {unknown} (choose from {list(STAGES)})")
    datasets = ordered_datasets(selected)
    print("datasets:", ", ".join(datasets))

    try:
        import yamaa  # noqa: F401
    except ImportError:
        sys.exit(
            "yamaa engine is required: pip install -r "
            "submission-pilot3/program/adam/requirements.txt"
        )

    work = Path(args.work)
    derived = derive(datasets, work)
    if not args.no_compare:
        print("== comparison vs official ADaM ==")
        compare(derived, datasets)
    print("DONE")


if __name__ == "__main__":
    main()
