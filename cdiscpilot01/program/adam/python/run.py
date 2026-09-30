#!/usr/bin/env python3
"""Derive Pilot 1 ADaM datasets from SDTM with yamaa."""

import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from yamaa import yamaa_domain

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[2]
SPECS = STUDY / "spec" / "yamaa"
DATASETS = ("adsl", "adae", "adtte", "advs", "adlbc", "adlbh", "adlbhy", "adqsnipx")


def main():
    selected = tuple(sys.argv[1:]) or DATASETS
    if any(name not in DATASETS for name in selected):
        raise SystemExit(f"choose from: {', '.join(DATASETS)}")
    for name in selected:
        run = yamaa_domain(SPECS / f"{name}.yaml", project_root=STUDY)
        if len(run.issues):
            raise RuntimeError(f"{name}: {run.issues}")
        output = run.save()
        labels = {column.name: column.label for column in run.spec.columns}
        table = pq.read_table(output)
        fields = [
            field.with_metadata({
                **(field.metadata or {}),
                b"yamaa:label": labels[field.name].encode(),
            })
            for field in table.schema
        ]
        pq.write_table(table.cast(pa.schema(fields)), output, compression="none")
        print(f"{name}: {output}", flush=True)


if __name__ == "__main__":
    main()
