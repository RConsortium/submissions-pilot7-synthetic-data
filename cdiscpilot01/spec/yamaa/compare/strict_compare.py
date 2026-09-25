"""Strict compare: produced vs official ADaM parquet.

Checks (in file order, NO realignment):
 1. row count, column count, exact column order
 2. Arrow field types exact
 3. yamaa:label field metadata exact
 4. every cell value exact: null vs "" distinct; numerics exact;
    floats allow tiny relative tolerance (report count of inexact-but-close)
"""
import sys
from pathlib import Path
import pyarrow.parquet as pq
import pyarrow as pa

ds = sys.argv[1].lower()
produced_path = sys.argv[2]
# Official ADaM parquet, placed at expected/<ds>.parquet (project root).
expected_path = Path(__file__).resolve().parent.parent / "expected" / f"{ds}.parquet"

ok = True
def report(msg):
    global ok
    ok = False
    print("MISMATCH:", msg)

exp_t = pq.read_table(expected_path)
got_t = pq.read_table(produced_path)

if (exp_t.num_rows, exp_t.num_columns) != (got_t.num_rows, got_t.num_columns):
    report(f"shape exp={(exp_t.num_rows, exp_t.num_columns)} got={(got_t.num_rows, got_t.num_columns)}")

if exp_t.schema.names != got_t.schema.names:
    eg = set(exp_t.schema.names); gg = set(got_t.schema.names)
    report(f"column order differs; only-exp={sorted(eg-gg)} only-got={sorted(gg-eg)}")

# types + labels
for f in exp_t.schema:
    g = got_t.schema.field(f.name) if f.name in got_t.schema.names else None
    if g is None:
        continue
    if not f.type.equals(g.type):
        report(f"type {f.name}: exp={f.type} got={g.type}")
    el = (f.metadata or {}).get(b"yamaa:label", b"")
    gl = (g.metadata or {}).get(b"yamaa:label", b"")
    if el != gl:
        report(f"label {f.name}: exp={el!r} got={gl!r}")

# cell values, row order exact
n_bad_cols = 0
close_float_cells = 0
for f in exp_t.schema:
    name = f.name
    if name not in got_t.schema.names:
        continue
    e = exp_t.column(name).to_pylist()
    g = got_t.column(name).to_pylist()
    if len(e) != len(g):
        continue
    bad = 0; ex = []
    for i, (a, b) in enumerate(zip(e, g)):
        if a is None and b is None:
            continue
        if (a is None) != (b is None):
            bad += 1
            if len(ex) < 3: ex.append((i, a, b))
            continue
        if isinstance(a, float) or isinstance(b, float):
            if a == b:
                continue
            # tolerant-but-reported
            if abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b)):
                close_float_cells += 1
                continue
            bad += 1
            if len(ex) < 3: ex.append((i, a, b))
        elif a != b:
            bad += 1
            if len(ex) < 3: ex.append((i, a, b))
    if bad:
        n_bad_cols += 1
        report(f"col {name}: {bad}/{len(e)} cells differ, e.g. {ex}")

print(f"\n{'STRICT PASS' if ok else 'STRICT FAIL'}: {ds} rows={got_t.num_rows} cols={got_t.num_columns} "
      f"bad_cols={n_bad_cols} close_float_cells={close_float_cells}")
