#!/usr/bin/env python3
"""Record the column names of every submitted ADaM dataset in data/reproduction/columns.json.

    python scripts/site/inventory_columns.py                   # after scripts/reproduce.py fetch
    python scripts/site/inventory_columns.py --data-root DIR   # files fetched elsewhere

The review page lists every column of a dataset with its result
(scripts/site/build_pages.py, column_rows). The results in adam.json count the
columns but name only those that differ, so the names come from the submitted
files: the schema of each dataset's `expected` file, where `reproduce.py fetch`
puts it. Only names are read, never a value. Each list must hold as many names
as the results count (`cols`) and every column the results name, or nothing is
written.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root", type=Path, default=ROOT, help="folder holding <study>/<cut>/data/adam/")
    args = ap.parse_args()
    import pyarrow.parquet as pq

    adam = json.loads((ROOT / "data/reproduction/adam.json").read_text())
    out: dict = {}
    errors: list[str] = []
    for study, st in adam["studies"].items():
        for cut, rows in st["cuts"].items():
            for r in rows:
                if not r.get("expected"):
                    continue
                where = f"{study}/{cut}/{r['dataset']}"
                path = args.data_root / r["expected"]
                if not path.exists():
                    errors.append(f"{where}: {path} is not there; fetch the cut first")
                    continue
                names = pq.read_schema(path).names
                named = (set(r.get("missing_columns") or []) | set(r.get("mismatched_columns") or {})
                         | set(r.get("redacted_columns") or {}) | set(r.get("carried_columns") or []))
                if len(names) != r["cols"] or named - set(names):
                    errors.append(f"{where}: {len(names)} columns in the file, {r['cols']} in the results"
                                  + (f"; not in the file: {sorted(named - set(names))}" if named - set(names) else ""))
                    continue
                out.setdefault(study, {}).setdefault(cut, {})[r["dataset"]] = names
    if errors:
        print("\n".join(errors) + "\nnothing written", file=sys.stderr)
        return 1
    dest = ROOT / "data/reproduction/columns.json"
    dest.write_text(json.dumps({"studies": out}, indent=1) + "\n")
    print(f"wrote {dest}: {sum(len(c) for s in out.values() for d in s.values() for c in d.values()):,} column names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
