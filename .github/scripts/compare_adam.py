#!/usr/bin/env python3
"""Compare derived ADaM datasets against the official ones, cell by cell.

Numeric cells match when both are null, both are NaN, or
``abs(derived - official) <= tolerance`` (default 1e-10, absolute).
Every non-numeric cell must match exactly: null equals null only, and by
default an empty string is NOT equal to null (pass --null-empty-equal to
normalize "" to null first, e.g. for XPT-sourced flag columns where a blank
is stored as "").

Arrow schema metadata (e.g. SAS column labels stored as ``yamaa:label``) is
ignored; only field names, row order, and values are compared. Columns are
aligned by name -- a different column order is reported as a warning, not a
failure.

Rows are compared positionally by default. Pass --keys (or --keys-file) to
sort both tables by key columns first and verify the keys align; without
this, differing row order shows up as cell mismatches.

Usage:
    python3 compare_adam.py --official submission-pilot5/data/adam \
        --derived /path/to/derived/adam [--tolerance 1e-10] \
        [--datasets adsl,adae] \
        --keys-file keys.json

keys.json maps dataset names to key column lists, with an optional
"default" entry, e.g.:
    {"default": ["STUDYID", "USUBJID"],
     "adlbc": ["STUDYID", "USUBJID", "PARAMCD", "AVISIT", "LBSEQ"]}

Exit code 0 when every dataset present in both locations passes, 1 otherwise.
"""

import argparse
import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


def _is_numeric(t):
    return (
        pa.types.is_integer(t)
        or pa.types.is_floating(t)
        or pa.types.is_decimal(t)
    )


def _numeric_match(a, b, tol):
    """Boolean mask: null==null, NaN==NaN, a==b, or |a-b| <= tol."""
    af = a.cast(pa.float64())
    bf = b.cast(pa.float64())
    both_null = pc.and_(pc.is_null(a), pc.is_null(b))
    # is_nan(null) is null, so fill it: NaN==NaN only when both are real NaNs.
    both_nan = pc.fill_null(pc.and_(pc.is_nan(af), pc.is_nan(bf)), False)
    eq = pc.fill_null(pc.equal(af, bf), False)
    # Integers wider than 2**53 lose precision in float64, but any two
    # distinct integers already differ by >= 1 >> tol, so the float64
    # subtraction only decides the near-equal case.
    close = pc.fill_null(
        pc.less_equal(pc.abs(pc.subtract(af, bf)), tol), False
    )
    return pc.or_(pc.or_(eq, close), pc.or_(both_null, both_nan))


def _exact_match(a, b, null_empty_equal=False):
    """Boolean mask: null==null or exact equality (empty string != null).

    With null_empty_equal, "" is normalized to null first (string columns).
    """
    if pa.types.is_string(a.type) or pa.types.is_large_string(a.type):
        # Unify string widths (official parquets use large_string).
        a = a.cast(pa.large_string())
        b = b.cast(pa.large_string())
    if null_empty_equal and pa.types.is_large_string(a.type):
        a = pc.if_else(pc.equal(a, ""), None, a)
        b = pc.if_else(pc.equal(b, ""), None, b)
    both_null = pc.and_(pc.is_null(a), pc.is_null(b))
    eq = pc.fill_null(pc.equal(a, b), False)
    return pc.or_(eq, both_null)


def _max_abs_deviation(a, b, mask):
    """Largest |a-b| among mismatched numeric cells (None if not numeric)."""
    if not _is_numeric(a.type):
        return None
    af = a.cast(pa.float64())
    bf = b.cast(pa.float64())
    dev = pc.abs(pc.subtract(af, bf))
    dev = pc.if_else(pc.is_nan(dev), None, dev)
    bad = pc.if_else(mask, None, dev)
    val = pc.max(bad).as_py()
    return val


def align_rows(name, official, derived, keys):
    """Sort both tables by keys and verify the key tuples align.

    Returns (official_sorted, derived_sorted, ok, report_lines).
    """
    if official.num_rows != derived.num_rows:
        return (official, derived, False,
                [f"  row count differs: official={official.num_rows} "
                 f"derived={derived.num_rows}"])
    missing = [k for k in keys if k not in official.schema.names
               or k not in derived.schema.names]
    if missing:
        return (official, derived, False,
                [f"  key columns missing: {missing}"])
    off_s = official.sort_by([(k, "ascending") for k in keys])
    der_s = derived.sort_by([(k, "ascending") for k in keys])
    lines = []
    ok = True
    for k in keys:
        mask = _exact_match(off_s.column(k), der_s.column(k))
        n_bad = official.num_rows - pc.sum(mask).as_py()
        if n_bad:
            ok = False
            bad_idx = pc.indices_nonzero(pc.invert(mask)).to_pylist()[:3]
            lines.append(f"  key {k}: {n_bad}/{official.num_rows} keys "
                         f"do not align, e.g. rows {bad_idx}")
    return off_s, der_s, ok, lines


def compare_tables(name, official, derived, tol, keys, null_empty_equal):
    """Return (ok, report_lines, cells, matched)."""
    lines = []
    ok = True

    off_cols = official.schema.names
    der_cols = derived.schema.names
    if off_cols != der_cols:
        if set(off_cols) != set(der_cols):
            only_off = [c for c in off_cols if c not in der_cols]
            only_der = [c for c in der_cols if c not in off_cols]
            lines.append(f"  column set differs: official-only={only_off} "
                         f"derived-only={only_der}")
            ok = False
        else:
            lines.append("  WARNING: column order differs from official")
    if official.num_rows != derived.num_rows:
        lines.append(f"  row count differs: official={official.num_rows} "
                     f"derived={derived.num_rows}")
        return False, lines, 0, 0

    if keys:
        official, derived, keys_ok, key_lines = align_rows(
            name, official, derived, keys)
        lines.extend(key_lines)
        if not keys_ok:
            return False, lines, 0, 0

    common = [c for c in off_cols if c in der_cols]
    total_cells = official.num_rows * len(common)
    matched_cells = 0
    for col in common:
        a = official.column(col)
        b = derived.column(col)
        a_num, b_num = _is_numeric(a.type), _is_numeric(b.type)
        if a_num != b_num:
            lines.append(f"  {col}: type kind differs "
                         f"(official={a.type}, derived={b.type})")
            ok = False
            continue
        mask = (_numeric_match(a, b, tol) if a_num
                else _exact_match(a, b, null_empty_equal))
        matched = pc.sum(mask).as_py()
        matched_cells += matched
        n_bad = official.num_rows - matched
        if n_bad:
            ok = False
            detail = f"  {col}: {n_bad}/{official.num_rows} cells differ"
            if a_num:
                dev = _max_abs_deviation(a, b, mask)
                detail += f", max |diff| = {dev}"
            # Show up to 3 example row indices.
            bad_idx = pc.indices_nonzero(pc.invert(mask)).to_pylist()[:3]
            detail += f", e.g. rows {bad_idx}"
            lines.append(detail)
    return ok, lines, total_cells, matched_cells


def discover(directory):
    return {
        p.stem: p for p in sorted(Path(directory).glob("*.parquet"))
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--official", required=True,
                    help="official ADaM parquet file or directory")
    ap.add_argument("--derived", required=True,
                    help="derived ADaM parquet file or directory")
    ap.add_argument("--tolerance", type=float, default=1e-10,
                    help="absolute numeric tolerance (default 1e-10)")
    ap.add_argument("--datasets", default="",
                    help="comma-separated dataset names to compare "
                         "(default: all present in both)")
    ap.add_argument("--keys", default="",
                    help="comma-separated key columns used to align rows "
                         "of every dataset before comparing")
    ap.add_argument("--keys-file", default="",
                    help="JSON file mapping dataset names to key column "
                         'lists, e.g. {"adlbc": ["STUDYID", "USUBJID", ...]}; '
                         'a "default" entry applies to unlisted datasets '
                         "(--keys wins over --keys-file)")
    ap.add_argument("--null-empty-equal", action="store_true",
                    help="treat empty string as null in string columns "
                         "(default: strict, \"\" != null)")
    args = ap.parse_args()

    keys_map = {}
    if args.keys_file:
        keys_map = json.loads(Path(args.keys_file).read_text())
    cli_keys = [k for k in args.keys.split(",") if k]

    def keys_for(name):
        if cli_keys:
            return cli_keys
        if name in keys_map:
            return keys_map[name]
        return keys_map.get("default", [])

    off_p = Path(args.official)
    der_p = Path(args.derived)
    if off_p.is_file() and der_p.is_file():
        # Single pair: compare directly regardless of file names.
        off_map = {off_p.stem: off_p}
        der_map = {off_p.stem: der_p}
    else:
        off_map = {off_p.stem: off_p} if off_p.is_file() else discover(off_p)
        der_map = {der_p.stem: der_p} if der_p.is_file() else discover(der_p)

    want = [d for d in args.datasets.split(",") if d] or None
    names = sorted(set(off_map) & set(der_map))
    if want:
        names = [n for n in names if n in want]

    only_off = sorted(set(off_map) - set(der_map))
    only_der = sorted(set(der_map) - set(off_map))

    all_ok = True
    grand_cells = grand_matched = 0
    for name in names:
        official = pq.read_table(off_map[name])
        derived = pq.read_table(der_map[name])
        ok, lines, cells, matched = compare_tables(
            name, official, derived, args.tolerance, keys_for(name),
            args.null_empty_equal)
        grand_cells += cells
        grand_matched += matched
        status = "PASS" if ok else "FAIL"
        print(f"{name}: {status} "
              f"({matched}/{cells} cells match, "
              f"{official.num_rows} rows x {official.num_columns} cols)")
        for line in lines:
            print(line)
        all_ok = all_ok and ok

    for name in only_off:
        print(f"{name}: SKIP (no derived dataset)")
    for name in only_der:
        print(f"{name}: SKIP (no official dataset)")
        all_ok = False

    print(f"\nTotal: {grand_matched}/{grand_cells} cells match "
          f"across {len(names)} datasets, tolerance={args.tolerance}")
    return 0 if all_ok and names else 1


if __name__ == "__main__":
    sys.exit(main())
