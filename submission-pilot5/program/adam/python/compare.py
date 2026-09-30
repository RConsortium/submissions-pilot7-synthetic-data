#!/usr/bin/env python3
"""Compare derived Pilot 5 ADaM datasets against the official ADaM, cell by cell.

Reads ../work/adam/ (written by run.py) and the study's data/adam/. Reports
matched/total columns and matched/total cells; exits nonzero on any mismatch.

Semantics (standing tolerance): numeric cells match when
|derived - official| <= 1e-10 (absolute); non-numeric cells match exactly.
Row alignment is by the dataset keys. Missing or extra columns fail.

Null and empty text are distinct.
"""

import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
DERIVED = HERE.parent / "work" / "adam"
OFFICIAL_ADAM = HERE.parents[2] / "data" / "adam"

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
        ref_file = OFFICIAL_ADAM / f"{ds}.parquet"
        ref = pl.read_parquet(ref_file)
        new_schema, ref_schema = pq.read_schema(out_file), pq.read_schema(ref_file)
        bad_labels, bad_types = [], []
        for name in ref.columns:
            if name not in new.columns:
                continue
            got, expected = new_schema.field(name), ref_schema.field(name)
            if (got.metadata or {}).get(b"yamaa:label") != (expected.metadata or {}).get(b"yamaa:label"):
                bad_labels.append(name)
            got_text = pa.types.is_string(got.type) or pa.types.is_large_string(got.type)
            expected_text = pa.types.is_string(expected.type) or pa.types.is_large_string(expected.type)
            if not (got.type.equals(expected.type) or (got_text and expected_text)):
                bad_types.append(name)
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
                a = a.cast(pl.Float64)
                b = b.cast(pl.Float64)
                ok = ((a.is_null() & b.is_null()) | ((a - b).abs() <= TOLERANCE)).fill_null(
                    False
                )  # exactly-one-null is a mismatch, not ignored
            else:
                ok = ((a.is_null() & b.is_null()) | (a.cast(pl.String) == b.cast(pl.String))).fill_null(False)
            bad = (~ok).sum()
            if bad:
                mismatches.append((col, bad))
                dataset_bad += bad
        total_mismatch += dataset_bad
        failed |= bool(mismatches or uncovered or derived_only or bad_labels or bad_types)
        status = "FAIL" if mismatches or uncovered or derived_only or bad_labels or bad_types else "PASS"
        print(
            f"-- {ds}: {status} ({len(common) + len(keys)}/{len(ref.columns)} columns, "
            f"{dataset_cells - dataset_bad}/{dataset_cells} cells match)"
        )
        if derived_only:
            print(f"   derived-only columns (not in official): {derived_only}")
        if uncovered:
            print(f"   official columns not derived: {uncovered}")
        if mismatches:
            print(f"   mismatched cells by column: {mismatches}")
        if bad_labels:
            print(f"   mismatched labels: {bad_labels}")
        if bad_types:
            print(f"   mismatched types: {bad_types}")
    print(f"TOTAL: {total_cells - total_mismatch}/{total_cells} derived cells match")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
