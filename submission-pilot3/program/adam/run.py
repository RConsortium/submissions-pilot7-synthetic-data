#!/usr/bin/env python3
"""Derive the Pilot 3 ADaM datasets from yamaa specs.

Stages the SDTM parquets from ../data/sdtm/ into a work/ directory, then
derives each dataset exactly like this:

    import yamaa
    adsl = yamaa.yamaa_domain("adsl.yaml").output

Specs run in dependency order (adsl first: the other four read their
subject-level variables from the derived adsl-yamaa.parquet instead of
re-deriving them) and persist to work/derived/ as *-yamaa.parquet with
variable labels. Derivation only -- use compare.py to verify against the
official ADaM in ../data/adam/.

Requires: the yamaa engine pinned in requirements.txt, polars, pyarrow.

Usage:
    python3 run.py
"""

import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
SDTM_SRC = STUDY / "data" / "sdtm"
WORK = HERE / "work"

# SDTM inputs staged verbatim from ../data/sdtm/.
SDTM_INPUTS = [
    "dm", "ds", "ex", "qs", "sv", "vs", "sc", "mh", "ae", "lb", "supplb",
]

# Run order: exdose staging, then the five datasets, dependencies first.
ORDER = ["adsl_exdose", "adsl", "adae", "adadas", "adtte", "adlbc"]
PERSISTED = {
    "adsl": "adsl-yamaa.parquet",
    "adae": "adae-yamaa.parquet",
    "adadas": "adadas-yamaa.parquet",
    "adtte": "adtte-yamaa.parquet",
    "adlbc": "adlbc-yamaa.parquet",
}


def stage(work):
    """Stage every input the specs resolve relative to their own directory."""
    import polars as pl

    sdtm = work / "sdtm"
    sdtm.mkdir(parents=True, exist_ok=True)
    for name in SDTM_INPUTS:
        shutil.copy2(SDTM_SRC / f"{name}.parquet", sdtm / f"{name}.parquet")

    # Hand-built planning relations (mirror the R program's tribbles; the
    # schema cannot generate these rows itself, REQ-0040/REQ-0041).
    inputs = work / "inputs"
    inputs.mkdir(exist_ok=True)
    pl.read_csv(
        HERE / "inputs" / "plan.csv",
        schema={"USUBJID": pl.String, "PARAMCD": pl.String,
                "AVISIT": pl.String, "AVISITN": pl.Int64},
    ).write_parquet(inputs / "plan.parquet")
    pl.read_csv(
        HERE / "inputs" / "aw_lookup.csv",
        schema={"AVISIT": pl.String, "AWRANGE": pl.String,
                "AWTARGET": pl.Int64, "AWLO": pl.Int64, "AWHI": pl.Int64},
        null_values=[""],
    ).write_parquet(inputs / "aw_lookup.parquet")

    # ADADAS reads QS.QSDTC_D: the planner's static gate currently rejects
    # ISO date text for to_date (REQ-0607, REQ-1107); staged QSDTC values
    # are all clean ISO dates.
    qs = pl.read_parquet(sdtm / "qs.parquet")
    qs.with_columns(
        pl.col("QSDTC").str.to_date("%Y-%m-%d", strict=True).alias("QSDTC_D")
    ).write_parquet(sdtm / "qs_str.parquet")

    (work / "derived").mkdir(exist_ok=True)
    for name in ORDER:
        shutil.copy2(HERE / f"{name}.yaml", work / f"{name}.yaml")
    print(f"staged {len(SDTM_INPUTS)} SDTM parquets + planning inputs")


def attach_labels(parquet_path, labels):
    """Stamp `yamaa:label` field metadata onto every labeled column.

    The engine's R020 parquet profile carries no field metadata of its own
    (REQ-0741), so labels declared the yamaa way (column-level `label:`)
    are stamped onto the artifact here, mirroring how the official ADaM
    staging preserved them as `yamaa:label` field metadata.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pq.read_table(parquet_path)
    fields = []
    for field in table.schema:
        metadata = dict(field.metadata or {})
        label = labels.get(field.name)
        if label:
            metadata[b"yamaa:label"] = label.encode("utf-8")
        fields.append(field.with_metadata(metadata) if metadata else field)
    labeled = table.cast(pa.schema(fields))
    # Keep the engine's uncompressed pages, but store the Arrow schema:
    # `store_schema=False` (the R020 engine profile) drops field metadata
    # on read-back, and the labels are the point of this step.
    pq.write_table(labeled, parquet_path, compression="none")


def derive(name, derived):
    """Run one spec and persist its output."""
    import yamaa

    run = yamaa.yamaa_domain(name + ".yaml")
    if len(run.issues):
        print(f"VALIDATION FAILED for {name}.yaml:")
        print(run.issues)
        sys.exit(1)
    frame = run.output
    if frame is None:
        sys.exit(f"ERROR: {name}.yaml produced no output")
    if name in PERSISTED:
        out = run.save(derived / PERSISTED[name])
        labels = {
            col.name: col.label for col in run.spec.columns if col.label
        }
        attach_labels(out, labels)
    else:
        out = run.save()
    print(f"  {name}.yaml: VALIDATION CLEAN, {frame.height} rows -> {out.name}")
    return frame


def main():
    try:
        import yamaa  # noqa: F401
    except ImportError:
        sys.exit(
            "yamaa engine is required: pip install -r "
            "submission-pilot3/program/adam/requirements.txt"
        )

    work, derived = WORK, WORK / "derived"
    stage(work)

    # Specs resolve input paths relative to their own directory, so run
    # from the specs directory: yamaa.yamaa_domain("<ds>.yaml").output.
    os.chdir(work)
    for name in ORDER:
        print(f"== {name} ==")
        derive(name, derived)
    print("DONE")


if __name__ == "__main__":
    main()
