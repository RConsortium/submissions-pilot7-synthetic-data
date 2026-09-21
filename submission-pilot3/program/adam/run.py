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
        "adsl-yamaa.parquet",
        "adsl-yamaa.parquet",
    ),
    "adae": (["adae.yaml"], ["adsl"], "adae-yamaa.parquet", "adae-yamaa.parquet"),
    "adadas": (
        ["adadas.yaml"],
        ["adsl"],
        "adadas-yamaa.parquet",
        "adadas-yamaa.parquet",
    ),
    "adtte": (
        ["adtte.yaml"],
        ["adsl", "adae"],
        "adtte-yamaa.parquet",
        "adtte-yamaa.parquet",
    ),
    "adlbc": (["adlbc.yaml"], ["adsl"], "adlbc-yamaa.parquet", "adlbc-yamaa.parquet"),
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


def stage_planning_inputs(inputs):
    """Materialize the hand-built planning relations as parquets.

    The CSVs committed under inputs/ mirror the R program's tribbles (the
    schema cannot generate these rows itself, REQ-0040/REQ-0041); dtypes are
    pinned so the staged parquets are identical on every run.
    """
    import polars as pl

    plan = pl.read_csv(
        HERE / "inputs" / "plan.csv",
        schema={"USUBJID": pl.String, "PARAMCD": pl.String,
                "AVISIT": pl.String, "AVISITN": pl.Int64},
    )
    plan.write_parquet(inputs / "plan.parquet")

    aw = pl.read_csv(
        HERE / "inputs" / "aw_lookup.csv",
        schema={"AVISIT": pl.String, "AWRANGE": pl.String,
                "AWTARGET": pl.Int64, "AWLO": pl.Int64, "AWHI": pl.Int64},
        null_values=[""],
    )
    aw.write_parquet(inputs / "aw_lookup.parquet")


def build_qs_str(qs_path, out_path):
    """QS input for ADADAS: staged QS plus a QSDTC_D date column.

    The spec reads QS.QSDTC_D because the planner's static gate currently
    rejects ISO date text for to_date (REQ-0607, REQ-1107); all staged
    QSDTC values are clean ISO dates.
    """
    import polars as pl

    df = pl.read_parquet(qs_path)
    df = df.with_columns(
        pl.col("QSDTC").str.to_date("%Y-%m-%d", strict=True).alias("QSDTC_D")
    )
    df.write_parquet(out_path)


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


def spec_labels(spec_path):
    """Parse name -> label for every column block in a spec.

    The engine's R020 parquet profile carries no field metadata of its own
    (REQ-0741), so labels declared the yamaa way (column-level `label:`)
    are stamped onto the artifact here, mirroring how the official ADaM
    staging preserved them as `yamaa:label` field metadata.
    """
    import re

    labels, name = {}, None
    for line in Path(spec_path).read_text().splitlines():
        m = re.match(r"  - name: (\w+)$", line)
        if m:
            name = m.group(1)
            continue
        if name is None:
            continue
        if re.match(r"  - (name|id): |^[a-z_]+:", line):
            name = None
            continue
        lm = re.match(r"    label: (.*)$", line)
        if lm:
            labels[name] = lm.group(1).strip()
    return labels


def attach_labels(parquet_path, labels):
    """Stamp `yamaa:label` field metadata onto every labeled column."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pq.read_table(parquet_path)
    fields = []
    for field in table.schema:
        label = labels.get(field.name)
        metadata = dict(field.metadata or {})
        if label:
            metadata[b"yamaa:label"] = label.encode("utf-8")
        fields.append(
            field.with_metadata(metadata) if metadata else field
        )
    labeled = table.cast(pa.schema(fields))
    # Keep the engine's uncompressed pages, but store the Arrow schema:
    # `store_schema=False` (the R020 engine profile) drops field metadata
    # on read-back, and the labels are the point of this step.
    pq.write_table(labeled, parquet_path, compression="none")


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
    attach_labels(out, spec_labels(spec_path))
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
    stage_planning_inputs(inputs)

    sdtm_qs = sdtm / "qs.parquet"
    build_qs_str(sdtm_qs, sdtm / "qs_str.parquet")
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
        _, _, derived_name, _ = STAGES[ds]
        # Official datasets keep their canonical names; ours are -yamaa.
        official_name = derived_name.replace("-yamaa", "")
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
        import pyarrow.parquet as pq

        new_fields = {f.name: dict(f.metadata or {}) for f in pq.read_schema(derived / derived_name)}
        ref_fields = {f.name: dict(f.metadata or {}) for f in pq.read_schema(OFFICIAL_ADAM / official_name)}
        label_bad = [
            c
            for c in new.columns
            if c in ref_fields
            and new_fields[c].get(b"yamaa:label") != ref_fields[c].get(b"yamaa:label")
        ]
        unlabeled = [
            c
            for c in new.columns
            if b"yamaa:label" not in new_fields[c]
        ]
        if label_bad:
            mismatches.append(("labels", label_bad))
        if unlabeled:
            mismatches.append(("unlabeled", unlabeled))

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
