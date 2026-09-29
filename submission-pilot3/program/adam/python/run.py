#!/usr/bin/env python3
"""Derive the Pilot 3 ADaM datasets from SDTM with yamaa."""

import shutil
import subprocess
import sys
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
from yamaa import yamaa_domain

HERE = Path(__file__).resolve().parent.parent
WORK = HERE / "work"
SPEC_ORDER = ("adsl.yaml", "adae.yaml", "adadas.yaml", "adtte.yaml", "adlbc.yaml")
S, I = pl.String, pl.Int64
INPUT_SCHEMAS = {"plan": {"USUBJID": S, "PARAMCD": S, "AVISIT": S, "AVISITN": I},
                 "aw_lookup": {"AVISIT": S, "AWRANGE": S, "AWTARGET": I, "AWLO": I, "AWHI": I}}


def main():
    subprocess.run([sys.executable, HERE / "python" / "make_plan.py"], check=True)
    for name in ("sdtm", "inputs", "adam"): (WORK / name).mkdir(parents=True, exist_ok=True)
    for src in (HERE.parent.parent / "data" / "sdtm").glob("*.parquet"):
        shutil.copy2(src, WORK / "sdtm" / src.name)
    for name, schema in INPUT_SCHEMAS.items():
        pl.read_csv(HERE / "inputs" / f"{name}.csv", schema=schema, null_values=[""]).write_parquet(WORK / "inputs" / f"{name}.parquet")
    for spec_name in SPEC_ORDER:
        shutil.copy2(HERE / spec_name, WORK / spec_name)
        run = yamaa_domain(WORK / spec_name, project_root=WORK)
        if len(run.issues):
            raise RuntimeError(f"{spec_name}: {run.issues}")
        output = run.save()
        labels = {column.name: column.label for column in run.spec.columns}
        table = pq.read_table(output)
        fields = [field.with_metadata({**(field.metadata or {}), b"yamaa:label": labels[field.name].encode()}) for field in table.schema]
        pq.write_table(table.cast(pa.schema(fields)), output, compression="none")
        print(f"{spec_name}: {output}", flush=True)


if __name__ == "__main__":
    main()
