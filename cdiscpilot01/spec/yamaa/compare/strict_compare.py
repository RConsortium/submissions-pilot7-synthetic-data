#!/usr/bin/env python3
"""Strict PyArrow comparison of a produced ADaM parquet against the official one.

Every check below must pass; anything less is FAIL. No silent normalization.

Checks:
  1. exact row count
  2. exact official column order (no extras, no missing, order identical)
  3. Arrow physical types identical per column, unless an explicit equivalence
     is declared via --equiv (e.g. large_string~string); declared equivalences
     are REPORTED, never silent
  4. yamaa:label field metadata identical per column
  5. rows in exactly the official file order (file order is the contract;
     no re-sorting, no key alignment)
  6. strict null-vs-empty: null masks compared exactly; "" is a value, not null
  7. exact type-aware values; float tolerance ONLY via explicit
     --tolerance COL:EPS, reported in the output

Usage:
  strict_compare.py <dataset> <produced.parquet> [--equiv A~B ...] [--tolerance COL:EPS ...]

Exit 0 on STRICT PASS, 1 on STRICT FAIL.
"""
import sys
from pathlib import Path
import pyarrow.parquet as pq
import pyarrow as pa
import pyarrow.compute as pc

MAX_EXAMPLES = 5


def parse_args(argv):
    ds = argv[1]
    produced = argv[2]
    equiv = {}
    tol = {}
    for a in argv[3:]:
        if a.startswith("--equiv="):
            k, v = a[len("--equiv="):].split("~")
            equiv[k] = v
        elif a.startswith("--tolerance="):
            c, e = a[len("--tolerance="):].split(":")
            tol[c] = float(e)
        else:
            raise SystemExit(f"unknown arg: {a}")
    return ds, produced, equiv, tol


def label_of(field):
    return ((field.metadata or {}).get(b"yamaa:label") or b"").decode()


def types_equivalent(te, tg, equiv):
    se, sg = str(te), str(tg)
    return se == sg or equiv.get(se) == sg or equiv.get(sg) == se


def column_equal(e, g, eps=None):
    """Null-safe exact equality of two same-typed ChunkedArrays.

    Returns (ok_count, bad_count, examples[(idx, exp, got)]).
    """
    e = e.combine_chunks() if isinstance(e, pa.ChunkedArray) else e
    g = g.combine_chunks() if isinstance(g, pa.ChunkedArray) else g
    n = len(e)
    both_null = pc.and_(pc.is_null(e), pc.is_null(g))
    if eps is not None and pa.types.is_floating(e.type):
        ev = pc.fill_null(e, float("nan"))
        gv = pc.fill_null(g, float("nan"))
        close = pc.less_equal(pc.abs(pc.subtract(ev, gv)), eps)
        ok = pc.or_(both_null, close)
    else:
        val_eq = pc.equal(e, g)  # null where either side null
        if pa.types.is_floating(e.type):
            both_nan = pc.and_(pc.is_nan(e), pc.is_nan(g))
            val_eq = pc.or_(val_eq, both_nan)
        ok = pc.or_(both_null, pc.fill_null(val_eq, False))
    bad_idx = pc.indices_nonzero(pc.invert(ok)).to_pylist()
    examples = []
    for i in bad_idx[:MAX_EXAMPLES]:
        examples.append((i, e[i].as_py(), g[i].as_py()))
    return n - len(bad_idx), len(bad_idx), examples


def main():
    ds, produced, equiv, tol = parse_args(sys.argv)
    root = Path(__file__).resolve().parents[1]
    expected = str(root / "expected" / f"{ds}.parquet")
    fails = []

    exp_schema = pq.read_schema(expected)
    try:
        got_schema = pq.read_schema(produced)
    except Exception as e:
        print(f"STRICT FAIL: {ds}\n  - cannot read produced file: {e}")
        return 1

    exp_cols = exp_schema.names
    got_cols = got_schema.names
    if got_cols != exp_cols:
        only_got = [c for c in got_cols if c not in exp_cols]
        only_exp = [c for c in exp_cols if c not in got_cols]
        if only_got:
            fails.append(f"extra columns: {only_got}")
        if only_exp:
            fails.append(f"missing columns: {only_exp}")
        if not only_got and not only_exp:
            fails.append("column ORDER differs from official")
    exp_fields = {f.name: f for f in exp_schema}
    got_fields = {f.name: f for f in got_schema}

    # types + labels
    type_bad, label_bad = 0, 0
    for c in exp_cols:
        if c not in got_fields:
            continue
        fe, fg = exp_fields[c], got_fields[c]
        if not types_equivalent(fe.type, fg.type, equiv):
            type_bad += 1
            if type_bad <= MAX_EXAMPLES:
                fails.append(f"type {c}: got={fg.type} expected={fe.type}")
        le, lg = label_of(fe), label_of(fg)
        if le != lg:
            label_bad += 1
            if label_bad <= MAX_EXAMPLES:
                fails.append(f"label {c}: got={lg!r} expected={le!r}")
    if type_bad > MAX_EXAMPLES:
        fails.append(f"... {type_bad - MAX_EXAMPLES} more type mismatches")
    if label_bad > MAX_EXAMPLES:
        fails.append(f"... {label_bad - MAX_EXAMPLES} more label mismatches")

    # rows
    exp_n = pq.read_metadata(expected).num_rows
    got_n = pq.read_metadata(produced).num_rows
    if exp_n != got_n:
        fails.append(f"row count got={got_n} expected={exp_n}")

    if not fails or (len(fails) and exp_n == got_n and got_cols == exp_cols):
        exp_t = pq.read_table(expected)
        got_t = pq.read_table(produced)
        val_bad_cols = 0
        for c in exp_cols:
            if c not in got_fields:
                continue
            fe, fg = exp_fields[c], got_fields[c]
            if not types_equivalent(fe.type, fg.type, equiv):
                continue  # already reported; value compare would be meaningless
            eps = tol.get(c)
            ok_n, bad_n, examples = column_equal(exp_t.column(c), got_t.column(c), eps)
            if bad_n:
                val_bad_cols += 1
                fails.append(f"values {c}: {bad_n}/{ok_n + bad_n} differ "
                             f"(file order), e.g. {examples}")
        if val_bad_cols > 3:
            fails = [f for f in fails if not f.startswith("values ")]
            fails.append(f"{val_bad_cols} columns have value differences "
                         f"(details suppressed)")

    notes = []
    if equiv:
        notes.append(f"accepted type equivalences: {equiv} "
                     f"(declared, not silent)")
    if tol:
        notes.append(f"float tolerance applied: {tol} (declared, not silent)")

    if fails:
        print(f"STRICT FAIL: {ds}")
        for f in fails:
            print("  -", f)
        for n_ in notes:
            print("  note:", n_)
        return 1
    print(f"STRICT PASS: {ds} rows={got_n} cols={len(exp_cols)}")
    for n_ in notes:
        print("  note:", n_)
    return 0


if __name__ == "__main__":
    sys.exit(main())
