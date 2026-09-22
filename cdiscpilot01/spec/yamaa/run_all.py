#!/usr/bin/env python3
"""End-to-end Pilot 01 SDTM -> ADaM driver (native yamaa).

Prerequisites (placed under this directory):
  sdtm/      the Pilot 01 SDTM parquet (dm, ex, ae, vs, lb, qs, ...)
  expected/  the official ADaM parquet (adsl, adae, ..., adqsnpix)

Runs every dataset in dependency order, promoting predecessor ADaM
outputs into upstream/ between steps. Python only orchestrates, recasts
Arrow string types between stages, joins the yamaa-derived PREV_AVAL map
back onto LB, and concatenates stage outputs -- no analysis variables
are derived in Python.

Usage:
  python run_all.py              # everything
  python run_all.py adlbhy       # one dataset (its prerequisites must exist)
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stageutil import BASE, PY, promote, run_yamaa  # noqa: F401

STEPS = [
    # (name, action)
    ("adsl", lambda: (run_yamaa("adsl.yaml"), promote("adsl"))),
    ("adae", lambda: (run_yamaa("adae.yaml"), promote("adae"))),
    ("adtte", lambda: run_yamaa("adtte.yaml")),
    ("advs", lambda: run_yamaa("advs.yaml")),
    ("adlbh", lambda: _run("run_adlbh.py")),
    ("adlbc", lambda: _run("run_adlbc.py")),
    ("adlbhy", lambda: _run("run_adlbhy.py")),
    ("adqsadas", lambda: _run("run_adqsadas.py")),
    ("adqscibc", lambda: _run("run_adqscibc.py")),
    ("adqsnpix", lambda: _run("run_adqsnpix.py")),
]


def _run(script: str) -> None:
    r = subprocess.run([str(PY), str(BASE / script)], cwd=BASE)
    if r.returncode != 0:
        raise SystemExit(f"{script} failed (rc={r.returncode})")


def main() -> None:
    only = [a.lower() for a in sys.argv[1:]]
    names = [name for name, _ in STEPS]
    for name in only:
        if name not in names:
            raise SystemExit(f"unknown dataset: {name} (choose from {', '.join(names)})")
    for name, action in STEPS:
        if only and name not in only:
            continue
        print(f"########## {name} ##########", flush=True)
        action()
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
