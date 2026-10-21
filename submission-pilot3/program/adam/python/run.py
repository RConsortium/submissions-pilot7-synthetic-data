#!/usr/bin/env python3
"""Run the same released-package project and explicit export as the R runner."""

from importlib.metadata import version
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import yaml
import yamaa

STUDY = Path(__file__).resolve().parents[3]
DATASETS = ("adsl", "adae", "adadas", "adtte", "adlbc")


def main():
    if version("yamaa") != "0.5.0":
        raise RuntimeError("This study is qualified with released yamaa 0.5.0")
    (STUDY / "log").mkdir(parents=True, exist_ok=True)
    for name in DATASETS:
        (STUDY / "data/adam" / f"{name}-yamaa.parquet").unlink(missing_ok=True)
    run = yamaa.project(STUDY / "project.yaml").run("adam")
    if run.issues.height:
        raise RuntimeError(str(run.issues))
    run.save()

    # Cell values come only from the raw engine artifacts. Apply the explicit
    # XPT-derived blank-character convention and declared variable labels.
    for name in DATASETS:
        raw = pq.read_table(STUDY / "data/adam" / f"{name}-yamaa-raw.parquet")
        spec = yaml.safe_load((STUDY / "spec/yamaa" / f"{name}.yaml").read_text())
        labels = {column["name"]: column["label"] for column in spec["columns"]}
        columns, fields = [], []
        for field, column in zip(raw.schema, raw.columns):
            if pa.types.is_string(field.type) or pa.types.is_large_string(field.type):
                column = pc.fill_null(column, "")
            columns.append(column)
            fields.append(field.with_metadata({b"yamaa:label": labels[field.name].encode()}))
        pq.write_table(pa.Table.from_arrays(columns, schema=pa.schema(fields)),
                       STUDY / "data/adam" / f"{name}-yamaa.parquet")
    print("Built and exported five datasets with zero issues.")


if __name__ == "__main__":
    main()
