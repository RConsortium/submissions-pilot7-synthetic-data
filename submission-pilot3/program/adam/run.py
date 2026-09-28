#!/usr/bin/env python3
"""Derive five Pilot 3 ADaM datasets from SDTM with yamaa."""

import shutil, subprocess, sys
from pathlib import Path

import polars as pl
import pyarrow as pa, pyarrow.parquet as pq
from yamaa import yamaa_domain

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
S, I = pl.String, pl.Int64
INPUT_SCHEMAS = {"plan": {"USUBJID": S, "PARAMCD": S, "AVISIT": S, "AVISITN": I},
                 "aw_lookup": {"AVISIT": S, "AWRANGE": S, "AWTARGET": I, "AWLO": I, "AWHI": I}}


def main():
    subprocess.run([sys.executable, HERE / "inputs" / "make_plan.py"], check=True)
    for name in ("sdtm", "inputs", "adam"): (WORK / name).mkdir(parents=True, exist_ok=True)
    for src in (HERE.parent.parent / "data" / "sdtm").glob("*.parquet"):
        shutil.copy2(src, WORK / "sdtm" / src.name)
    for name, schema in INPUT_SCHEMAS.items():
        pl.read_csv(HERE / "inputs" / f"{name}.csv", schema=schema, null_values=[""]).write_parquet(WORK / "inputs" / f"{name}.parquet")
    for spec in HERE.glob("*.yaml"): shutil.copy2(spec, WORK / spec.name)
    for name in ("adsl", "adae", "adadas", "adtte", "adlbc"):
        run = yamaa_domain(WORK / f"{name}.yaml", project_root=WORK)
        if len(run.issues): raise RuntimeError(f"{name}: {run.issues}")
        output = run.save()
        labels = {column.name: column.label for column in run.spec.columns}
        table = pq.read_table(output)
        fields = [field.with_metadata({**(field.metadata or {}), b"yamaa:label": labels[field.name].encode()}) for field in table.schema]
        pq.write_table(table.cast(pa.schema(fields)), output, compression="none")
        print(f"{name}: {output}", flush=True)


if __name__ == "__main__":
    main()
