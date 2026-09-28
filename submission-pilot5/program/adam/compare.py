#!/usr/bin/env python3
"""Compare derived Pilot 5 ADaM datasets against the official ADaM, cell by cell.

Reads work/adam/ (written by run.py) and ../data/adam/. Per dataset reports
matched/total columns and matched/total cells; exits nonzero on any mismatch.

Semantics (standing tolerance): numeric cells match when
|derived - official| <= 1e-10 (absolute); non-numeric cells match exactly.
Row alignment is by the dataset keys. Missing or extra columns fail.

Missing-value representation: the official ADaM was produced by R, where a
missing character value is ""; yamaa represents missing as null. Verified
2026-09-21 on all five official datasets (string "" cells / string nulls):
adadas 21257/0, adae 10234/0, adlbc 120776/0, adsl 634/0, adtte 0/0 --
the official files carry zero string nulls anywhere. Derived "" cells are
explicit values (e.g. ADSL DCSREAS 110 "" == official 110 ""), so "" and
null are normalized for comparison on that basis only.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DERIVED = HERE / "work" / "adam"
OFFICIAL_ADAM = HERE.parent.parent / "data" / "adam"

# dataset -> (derived file name, row-alignment keys); matches
# submission-pilot5/program/adam/adam-compare-keys.json.
DATASETS = {
    "adsl": ("adsl-yamaa.parquet", ["STUDYID", "USUBJID"]),
    "adae": ("adae-yamaa.parquet", ["STUDYID", "USUBJID", "AESEQ"]),
    "adadas": ("adadas-yamaa.parquet", ["STUDYID", "USUBJID", "PARAMCD", "AVISITN", "QSSEQ"]),
    "adtte": ("adtte-yamaa.parquet", ["STUDYID", "USUBJID", "PARAMCD"]),
    "adlbc": ("adlbc-yamaa.parquet", ["STUDYID", "USUBJID", "PARAMCD", "AVISIT", "LBSEQ"]),
}

TOLERANCE = 1e-10


def main():
    import polars as pl

    total_cells, total_mismatch, failed = 0, 0, False
    selected = sys.argv[1].split(",") if len(sys.argv) > 1 else list(DATASETS)
    for ds in selected:
        fname, keys = DATASETS[ds]
        out_file = DERIVED / fname
        if not out_file.exists():
            raise FileNotFoundError(f"{ds}: missing {out_file}; run run.py first")
        new = pl.read_parquet(out_file)
        ref = pl.read_parquet(OFFICIAL_ADAM / f"{ds}.parquet")
        assert new.height == ref.height, f"{ds}: row count {new.height} != {ref.height}"
        assert new.select(keys).is_unique().all() and ref.select(keys).is_unique().all(), f"{ds}: duplicate keys"
        joined = new.join(ref, on=keys, how="inner", suffix="_ref")
        assert joined.height == ref.height, f"{ds}: key mismatch"
        # Pair columns explicitly by name: a derived column is comparable only
        # when the official dataset carries the same column name.
        common = [c for c in new.columns if c not in keys and c in ref.columns]
        derived_only = [c for c in new.columns if c not in keys and c not in ref.columns]
        uncovered = [c for c in ref.columns if c not in keys and c not in new.columns]
        dataset_cells = ref.height * len(ref.columns)
        dataset_bad = ref.height * len(uncovered)
        total_cells += dataset_cells
        mismatches = []
        for col in common:
            a, b = joined[col], joined[col + "_ref"]
            if a.dtype.is_numeric() and b.dtype.is_numeric():
                a = a.fill_nan(None).cast(pl.Float64)
                b = b.fill_nan(None).cast(pl.Float64)
                ok = ((a.is_null() & b.is_null()) | ((a - b).abs() <= TOLERANCE)).fill_null(
                    False
                )  # exactly-one-null is a mismatch, not ignored
            else:
                ok = a.cast(pl.String).fill_null("") == b.cast(pl.String).fill_null("")
            bad = (~ok).sum()
            if bad:
                mismatches.append((col, bad))
                dataset_bad += bad
        total_mismatch += dataset_bad
        failed |= bool(mismatches or uncovered or derived_only)
        status = "FAIL" if mismatches or uncovered or derived_only else "PASS"
        print(
            f"-- {ds}: {status} ({len(common) + len(keys)}/{len(ref.columns)} columns, "
            f"{dataset_cells - dataset_bad}/{dataset_cells} cells match)"
        )
        if derived_only:
            print(f"   derived-only columns (not in official): {derived_only}")
        if uncovered:
            print(f"   official columns not derived: {uncovered}")
    print(f"TOTAL: {total_cells - total_mismatch}/{total_cells} derived cells match")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
