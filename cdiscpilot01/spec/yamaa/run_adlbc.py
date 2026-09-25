#!/usr/bin/env python3
"""ADLBC full-data native pipeline runner.

1. adlbc-prevmap.yaml (native yamaa): PREV_AVAL = the AVAL of the previous
   scheduled record within (USUBJID, LBTESTCD), ordered by AVISITN
   (SCREENING 1 -> 0, WEEK n -> n); raw BASELINE and unscheduled records
   excluded. -> output/adlbc-prevmap.parquet
2. Python join (no derivation): left-join PREV_AVAL back onto the original
   sdtm/lb.parquet by (USUBJID, LBTESTCD, LBSEQ).
   -> work/lb_with_prev.parquet
3. adlbc.yaml (native yamaa): full ADLBC. -> output/adlbc.parquet
"""
import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stageutil import BASE, run_yamaa

KEYS = ["USUBJID", "LBTESTCD", "LBSEQ"]


def main() -> None:
    out = run_yamaa("adlbc-prevmap.yaml")

    lb = pl.read_parquet(BASE / "sdtm" / "lb.parquet")
    prev = pl.read_parquet(out).select(KEYS + ["PREV_AVAL"])
    joined = lb.join(prev, on=KEYS, how="left")

    work = BASE / "work"
    work.mkdir(parents=True, exist_ok=True)
    staged = work / "lb_with_prev.parquet"
    joined.write_parquet(staged)
    print(f"  -> work/lb_with_prev.parquet: {joined.shape[0]} x {joined.shape[1]}",
          flush=True)

    run_yamaa("adlbc.yaml")


if __name__ == "__main__":
    main()
