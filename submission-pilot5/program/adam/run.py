#!/usr/bin/env python3
"""End-to-end SDTM -> ADaM derivation for submission-pilot5.

Stages the SDTM parquets from ../data/sdtm/, runs the yamaa derivation specs
in dependency order, and writes the five derived ADaM datasets to
work/derived/. By default the derived datasets are then compared cell by
cell against the official ADaM in ../data/adam/.

Requires: the yamaa engine (pip install from https://github.com/elong0527/yamaa),
polars, pyarrow.

Usage:
    python3 run.py                          # everything, then compare
    python3 run.py --datasets adsl,adtte    # subset (predecessors auto-included)
    python3 run.py --no-compare            # derive only
    python3 run.py --work /tmp/p5          # custom work directory
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
SDTM_SRC = STUDY / "data" / "sdtm"
OFFICIAL_ADAM = STUDY / "data" / "adam"

# dataset -> (spec stages, predecessor datasets, derived file name)
STAGES = {
    "adsl": (["adsl.yaml"], [], "adsl.parquet"),
    "adae": (["adae.yaml"], ["adsl"], "adae.parquet"),
    "adadas": (
        ["adadas-obs.yaml", "adadas-actot.yaml", "adadas-locf.yaml"],
        ["adsl"],
        "adadas.parquet",
    ),
    "adtte": (["adtte.yaml"], ["adsl", "adae"], "adtte.parquet"),
    "adlbc": (
        ["stage-adlbc-lb.py", "adlbc-eot-rn.yaml", "adlbc-eot.yaml", "adlbc.yaml"],
        ["adsl"],
        "adlbc.parquet",
    ),
}

# spec output file -> canonical derived name, per dataset
SPEC_OUTPUTS = {
    "adsl.yaml": ("adsl-dryrun.parquet", "adsl.parquet"),
    "adae.yaml": ("adae-dryrun.parquet", "adae.parquet"),
    "adadas-locf.yaml": ("adadas-out.parquet", "adadas.parquet"),
    "adtte.yaml": ("adtte-out.parquet", "adtte.parquet"),
    "adlbc.yaml": ("adlbc-out.parquet", "adlbc.parquet"),
}

# Row-alignment keys for the comparison (match adam-compare-keys.json).
KEYS = {
    "adsl": ["STUDYID", "USUBJID"],
    "adae": ["STUDYID", "USUBJID", "AESEQ"],
    "adadas": ["STUDYID", "USUBJID", "PARAMCD", "AVISITN", "QSSEQ"],
    "adtte": ["STUDYID", "USUBJID", "PARAMCD"],
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

    run = yamaa_domain(spec_path, project_root=work)
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
    for src in sorted(SDTM_SRC.glob("*.parquet")):
        shutil.copy2(src, sdtm / src.name)
    print(f"staged {len(list(sdtm.glob('*.parquet')))} SDTM parquets")

    for spec_name in [
        s for ds in STAGES for s in STAGES[ds][0] if s.endswith(".yaml")
    ] + ["stage-adlbc-lb.py"]:
        shutil.copy2(HERE / spec_name, work / spec_name)

    derived = work / "derived"
    derived.mkdir(exist_ok=True)

    for ds in datasets:
        print(f"== {ds} ==")
        for stage in STAGES[ds][0]:
            if stage == "stage-adlbc-lb.py":
                subprocess.run(
                    [sys.executable, "stage-adlbc-lb.py"],
                    cwd=work,
                    check=True,
                )
                print("  stage-adlbc-lb.py: adlbc-lb.parquet staged")
            else:
                run_spec(work / stage, work)
        out_name, canon_name = SPEC_OUTPUTS[
            next(s for s in STAGES[ds][0] if s in SPEC_OUTPUTS)
        ]
        shutil.copy2(work / out_name, derived / canon_name)
        # Stage the derived dataset as a predecessor for downstream specs,
        # which read it from sdtm/adsl.parquet / sdtm/adae.parquet.
        if ds in ("adsl", "adae"):
            shutil.copy2(derived / canon_name, sdtm / canon_name)
        print(f"  wrote derived/{canon_name}")
    return derived


def compare(derived):
    """Verify every derived column against the official ADaM.

    Semantics (standing tolerance): numeric cells match when
    |derived - official| <= 1e-10 (absolute); non-numeric cells match exactly
    with null/"" normalized. Row alignment is by the dataset keys. Official
    columns the spec does not derive are reported as uncovered, not failures.
    """
    import polars as pl

    total_cells, total_mismatch = 0, 0
    for ds, keys in KEYS.items():
        out_file = derived / STAGES[ds][2]
        if not out_file.exists():
            print(f"-- {ds}: not derived, skipped")
            continue
        new = pl.read_parquet(out_file)
        ref = pl.read_parquet(OFFICIAL_ADAM / STAGES[ds][2])
        assert new.height == ref.height, f"{ds}: row count {new.height} != {ref.height}"
        joined = new.join(ref, on=keys, how="inner", suffix="_ref")
        assert joined.height == ref.height, f"{ds}: key mismatch"
        common = [
            c for c in new.columns if c not in keys and c + "_ref" in joined.columns
        ]
        derived_only = [
            c for c in new.columns if c not in keys and c + "_ref" not in joined.columns
        ]
        uncovered = [c for c in ref.columns if c not in keys and c not in new.columns]
        mismatches = []
        for col in common:
            a, b = joined[col], joined[col + "_ref"]
            if a.dtype.is_numeric() and b.dtype.is_numeric():
                a = a.fill_nan(None).cast(pl.Float64)
                b = b.fill_nan(None).cast(pl.Float64)
                ok = (a.is_null() & b.is_null()) | ((a - b).abs() <= TOLERANCE)
            else:
                ok = a.cast(pl.String).fill_null("") == b.cast(pl.String).fill_null("")
            bad = (~ok).sum()
            total_cells += new.height
            if bad:
                mismatches.append((col, bad))
                total_mismatch += bad
        status = "PASS" if not mismatches else f"MISMATCH {mismatches}"
        print(
            f"-- {ds}: {status} ({len(common)} derived cols, "
            f"{new.height * len(common)} cells checked)"
        )
        if derived_only:
            print(f"   derived-only columns (not in official): {derived_only}")
        if uncovered:
            print(f"   official columns not derived: {uncovered}")
    print(f"TOTAL: {total_cells - total_mismatch}/{total_cells} derived cells match")
    if total_mismatch:
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
            "yamaa engine is required: pip install from https://github.com/elong0527/yamaa"
        )

    work = Path(args.work)
    derived = derive(datasets, work)
    if not args.no_compare:
        print("== comparison vs official ADaM ==")
        compare(derived)
    print("DONE")


if __name__ == "__main__":
    main()
