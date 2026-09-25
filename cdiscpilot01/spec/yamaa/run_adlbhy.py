#!/usr/bin/env python3
"""ADLBHY full-data native pipeline runner.

Requires output/adlbc.parquet (run run_adlbc.py first).

1. Python recast (no derivation): large_string -> string copy of the ADLBC
   output, because the yamaa reader needs plain-string input columns.
   -> upstream/adlbc.parquet
2. adlbhy.yaml (native yamaa): Hy's Law parameters from ADLBC --
   BILIHY/TRANSHY/HYLAW plus BASE/CHG/PCHG/SHIFT. -> output/adlbhy.parquet
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stageutil import BASE, promote, run_yamaa


def main() -> None:
    promote("adlbc")
    run_yamaa("adlbhy.yaml")


if __name__ == "__main__":
    main()
