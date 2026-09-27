#!/usr/bin/env python3
"""Derive-only driver: run the yamaa engine on each single-spec YAML.

No joins, unions, sorting, recasting, shaping, comparison, or
derivation happens here. Staged pipelines (adqsadas x5, adqscibc x11)
stay pending yamaa fixes (#1148, validator hang); not run here.
"""
from pathlib import Path

from yamaa import yamaa_domain

BASE = Path(__file__).resolve().parent

SPECS = ["adsl.yaml", "adae.yaml", "adtte.yaml", "advs.yaml",
         "adlbc.yaml", "adlbh.yaml", "adlbhy.yaml", "adqsnipx.yaml"]


def main() -> None:
    for spec in SPECS:
        print(f"=== {spec} ===", flush=True)
        yamaa_domain(str(BASE / spec), project_root=str(BASE))
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
