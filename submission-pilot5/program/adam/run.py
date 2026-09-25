#!/usr/bin/env python3
"""Derive the five submission-pilot5 ADaM datasets (yamaa engine only).

Stages the SDTM parquets, runs the YAML specs in dependency order, and writes
the derived datasets to work/derived/. Cell-by-cell comparison against the
official ADaM lives in compare.py. Run with ~/workspace/pilot7-venv/bin/python.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SDTM = HERE.parent.parent / "data" / "sdtm"
# dataset -> (stages, predecessors, final spec output, derived file)
STAGES = {
    "adsl": (["adsl.yaml"], [], "adsl-dryrun.parquet", "adsl.parquet"),
    "adae": (["adae.yaml"], ["adsl"], "adae-dryrun.parquet", "adae.parquet"),
    "adadas": (
        ["adadas-obs.yaml", "adadas-actot.yaml", "adadas-locf.yaml"],
        ["adsl"],
        "adadas-out.parquet",
        "adadas.parquet",
    ),
    "adtte": (["adtte.yaml"], ["adsl", "adae"], "adtte-out.parquet", "adtte.parquet"),
    "adlbc": (
        ["stage-adlbc-lb.py", "adlbc-eot-rn.yaml", "adlbc-eot.yaml", "adlbc.yaml"],
        ["adsl"],
        "adlbc-out.parquet",
        "adlbc.parquet",
    ),
}


def run_spec(spec, work):
    from yamaa import yamaa_domain

    run = yamaa_domain(work / spec, project_root=work)
    issues = run.issues
    assert issues is None or len(issues) == 0, f"{spec}: VALIDATION FAILED\n{issues}"
    print(f"  {spec}: VALIDATION CLEAN -> {Path(run.save()).name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--datasets", default=",".join(STAGES))
    ap.add_argument("--work", default=str(HERE / "work"))
    args = ap.parse_args()
    order, seen = [], set()

    def visit(ds):
        if ds not in seen:
            seen.add(ds)
            for dep in STAGES[ds][1]:
                visit(dep)
            order.append(ds)

    for ds in [d.strip() for d in args.datasets.split(",") if d.strip()]:
        visit(ds)
    work = Path(args.work)
    (work / "sdtm").mkdir(parents=True, exist_ok=True)
    (work / "derived").mkdir(exist_ok=True)
    for src in sorted(SDTM.glob("*.parquet")):
        shutil.copy2(src, work / "sdtm" / src.name)
    for ds in STAGES:
        for s in STAGES[ds][0]:
            shutil.copy2(HERE / s, work / s)
    for ds in order:
        print(f"== {ds} ==")
        for s in STAGES[ds][0]:
            if s.endswith(".py"):
                subprocess.run([sys.executable, s], cwd=work, check=True)
            else:
                run_spec(s, work)
        shutil.copy2(work / STAGES[ds][2], work / "derived" / STAGES[ds][3])
        if ds in ("adsl", "adae"):  # stage as predecessors for downstream specs
            shutil.copy2(work / "derived" / STAGES[ds][3], work / "sdtm" / STAGES[ds][3])
    print("DONE")


if __name__ == "__main__":
    main()
