#!/usr/bin/env python3
"""Cut every text value of a JMP conversion at its first NUL byte.

JMP keeps text in fixed-width buffers that end at the first NUL byte; JMP
itself shows only what comes before it. FDA's redaction wrote "(b)(6)" and a
NUL over the start of a buffer and left the rest, so the original value's
tail sits behind the NUL ("(b)(6)\\x00" followed by the rest of the original
value). The JMP-to-Parquet conversion kept the whole buffer. This tool
applies JMP's own rule to the committed conversions, which both matches what
JMP shows and drops the leftover text of redacted values.

Only JMP conversions are touched: the files data/sources.csv lists with
format jmp. XPT conversions have no such rule and are left alone. A file not
fetched from Git LFS is reported and skipped.

    python scripts/cut_jmp_strings.py           # rewrite in place, print counts
    python scripts/cut_jmp_strings.py --check   # exit 1 if any value still has a NUL
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
def jmp_files() -> list[Path]:
    rows = csv.DictReader(open(ROOT / "data/sources.csv"))
    return sorted(ROOT / r["path"] for r in rows if r["format"] == "jmp" and (ROOT / r["path"]).exists())


def fetched(path: Path) -> bool:
    with open(path, "rb") as fh:
        return fh.read(4) == b"PAR1"


def cut(path: Path, write: bool) -> dict:
    t = pq.read_table(path)
    counts, cols = {}, []
    for i, field in enumerate(t.schema):
        c = t.column(i)
        if pa.types.is_string(field.type) or pa.types.is_large_string(field.type):
            has = pc.match_substring(c, "\x00")
            n = pc.sum(pc.cast(has, pa.int64())).as_py() or 0
            if n:
                counts[field.name] = n
                c = pa.array([v.split("\x00", 1)[0] if v is not None else None for v in c.to_pylist()],
                             field.type)
        cols.append(c)
    if counts and write:
        meta = pq.read_metadata(path)
        compression = meta.row_group(0).column(0).compression if meta.num_row_groups else "SNAPPY"
        pq.write_table(pa.table(cols, schema=t.schema), path, compression=compression.lower())
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report only; exit 1 if any NUL is left")
    args = ap.parse_args()
    left = 0
    for f in jmp_files():
        if not fetched(f):
            print(f"skipped (not fetched from Git LFS): {f.relative_to(ROOT)}")
            continue
        counts = cut(f, write=not args.check)
        if counts:
            left += sum(counts.values())
            print(f"{f.relative_to(ROOT)}: {counts}")
    if args.check:
        return 1 if left else 0
    print(f"cut {left} values at their first NUL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
