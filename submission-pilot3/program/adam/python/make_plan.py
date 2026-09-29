#!/usr/bin/env python3
"""Regenerate the ADADAS LOCF planning relation (data/mapping/plan.csv).

The reviewed artifact is this script, not the CSV. The CSV is the pinned,
byte-stable output of the rule below.

Rule (reverse-engineered from the reference derivation and verified
byte-identical against the committed plan.csv):
  1. Subject universe: every subject with an SDTM EX record (== ADSL here).
  2. TRTSDT per subject: earliest EXSTDTC (all full ISO dates in this study).
  3. Collected ACTOT records: QS rows with QSTESTCD='ACTOT', windowed to an
     analysis visit by study day (ADY = QSDTC - TRTSDT + 1):
       ADY <= 1   -> Baseline
       ADY <= 84  -> Week 8
       ADY <= 140 -> Week 16
       otherwise  -> Week 24
     (the same cut the ADADAS spec applies to QS records).
  4. Expected observations: ACTOT at Week 8 / Week 16 / Week 24 per subject.
  5. Plan rows: expected (subject, visit) pairs with no collected ACTOT
     record, ordered by (USUBJID, AVISITN). These are the slots where the
     reference derivation's derive_locf_records adds LOCF rows.

Per REQ-0040/REQ-0041 the yamaa spec cannot create rows, so this expansion
happens upstream. The checked-in data/mapping/plan.csv is verified for drift
in CI; the spec reads it directly as ordinary input.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

STUDY = Path(__file__).resolve().parents[3]
MAPPING = STUDY / "data" / "mapping"
DATA_SDTM = STUDY / "data" / "sdtm"

PARAMCD = "ACTOT"
# (AVISIT, AVISITN) in analysis order.
EXPECTED_VISITS = [("Week 8", 8), ("Week 16", 16), ("Week 24", 24)]
HEADER = "USUBJID,PARAMCD,AVISIT,AVISITN\n"


def build(qs_path: Path, ex_path: Path) -> str:
    qs = pl.read_parquet(qs_path)
    ex = pl.read_parquet(ex_path)

    # Earliest EXSTDTC per subject. ISO dates sort chronologically as text.
    trtsdt = ex.group_by("USUBJID").agg(
        pl.col("EXSTDTC").min().str.to_date("%Y-%m-%d", strict=True).alias("TRTSDT")
    )

    actot = (
        qs.filter(pl.col("QSTESTCD") == PARAMCD)
        .select(
            "USUBJID",
            pl.col("QSDTC").str.to_date("%Y-%m-%d", strict=True).alias("QSDTC_D"),
        )
        .join(trtsdt, on="USUBJID", how="left")
    )
    ady = (pl.col("QSDTC_D") - pl.col("TRTSDT")).dt.total_days() + 1
    collected = (
        actot.with_columns(
            pl.when(ady <= 1)
            .then(pl.lit("Baseline"))
            .when(ady <= 84)
            .then(pl.lit("Week 8"))
            .when(ady <= 140)
            .then(pl.lit("Week 16"))
            .otherwise(pl.lit("Week 24"))
            .alias("AVISIT")
        )
        .select("USUBJID", "AVISIT")
        .unique()
    )
    have = set(zip(collected["USUBJID"].to_list(), collected["AVISIT"].to_list()))

    rows = [
        f"{usubjid},{PARAMCD},{avisit},{avisitn}\n"
        for usubjid in sorted(trtsdt["USUBJID"].to_list())
        for avisit, avisitn in EXPECTED_VISITS
        if (usubjid, avisit) not in have
    ]
    return HEADER + "".join(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--qs", type=Path, default=DATA_SDTM / "qs.parquet")
    ap.add_argument("--ex", type=Path, default=DATA_SDTM / "ex.parquet")
    ap.add_argument("--out", type=Path, default=MAPPING / "plan.csv")
    args = ap.parse_args()
    args.out.write_text(build(args.qs, args.ex), encoding="utf-8", newline="")


if __name__ == "__main__":
    main()
