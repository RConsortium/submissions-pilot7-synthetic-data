#!/usr/bin/env python3
"""Derive Pilot 5 ADaM datasets; pass comma-separated names to select a subset."""

import shutil
import subprocess
import sys
from pathlib import Path

from yamaa import yamaa_domain

HERE = Path(__file__).resolve().parent
DEPS = {"adsl": (), "adae": ("adsl",), "adadas": ("adsl",),
        "adtte": ("adsl", "adae"), "adlbc": ("adsl",)}


def main():
    work, order = HERE / "work", []
    requested = sys.argv[1].split(",") if len(sys.argv) > 1 else ["adsl", "adae", "adtte"]
    def visit(ds):
        if ds not in DEPS: raise ValueError(f"unknown dataset: {ds}")
        for dep in DEPS[ds]: visit(dep)
        if ds not in order: order.append(ds)
    for ds in requested: visit(ds)
    for name in ("sdtm", "adam"): (work / name).mkdir(parents=True, exist_ok=True)
    for src in (HERE.parent.parent / "data" / "sdtm").glob("*.parquet"):
        shutil.copy2(src, work / "sdtm" / src.name)
    for src in HERE.glob("*.yaml"): shutil.copy2(src, work / src.name)
    for ds in order:
        if ds == "adlbc": subprocess.run([sys.executable, str(HERE / "stage-adlbc-lb.py")], cwd=work, check=True)
        run = yamaa_domain(work / f"{ds}.yaml", project_root=work)
        if len(run.issues): raise RuntimeError(f"{ds}: {run.issues}")
        print(f"{ds}: {run.save()}", flush=True)
        if ds in ("adsl", "adae"):
            shutil.copy2(work / "adam" / f"{ds}-yamaa.parquet", work / "sdtm" / f"{ds}.parquet")


if __name__ == "__main__":
    main()
