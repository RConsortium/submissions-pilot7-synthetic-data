#!/usr/bin/env python3
"""Make numeric widths fit the derived values (yamaa SUB-29 / SUB-7).

yamaa checks that an int or float column's completed values fit its
declared `length` and `significant_digits`, and that a `w.d`
`display_format` has room for them (SUB-29, yamaa #4820). Specs transcribed
from a Pinnacle 21 define carry its storage widths (Length="8" for every
numeric, formats such as `3.`), which the data does not always fit.

For one dataset spec this tool repeats, until the run is clean:

  1. run the spec through scripts/reproduce.py verify (the cut's inputs and
     the study's partitions apply);
  2. read the SUB-29 / SUB-7 findings the run reports;
  3. edit the layer that declares the field (yamaa provenance): drop a
     display_format that has no room, and set length / significant_digits
     to the widths the submitted values need (SUB-29's measure: canonical
     text, minus sign counted, decimal point not), widening further when
     the derived values still do not fit.

A changed column gets one comment saying the received widths live in the
reproduced define layer (<cut>/define/), where SUB-29 does not apply.

    python scripts/specs/fix_numeric_widths.py --study c4591001 --cut s1 \
        --dataset admh [--partitions 4]
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTE = ["    # SUB-29 (yamaa #4820): numeric widths here fit the derived values. The received",
        "    # define's Pinnacle 21 widths stay in the reproduced define layer (define/)."]


def canonical(v) -> str:
    if isinstance(v, bool):
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    if math.isfinite(v) and v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return repr(float(v))


def widths(values) -> tuple[int, int]:
    length = decimals = 0
    for v in values:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        t = canonical(v)
        length = max(length, len(t.replace(".", "")))
        if "." in t:
            decimals = max(decimals, len(t.split(".")[1]))
    return length, decimals


def run_once(study, cut, dataset, partitions, out, spec: Path) -> tuple[list, Path | None]:
    cmd = [sys.executable, str(ROOT / "scripts/reproduce.py"), "verify", "--study", study, "--cut", cut,
           "--dataset", dataset, "--out", str(out), "--partitions", str(partitions)]
    subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    rep = json.loads((Path(out) / f"{study}-{cut}-{dataset}.json").read_text())
    expected = ROOT / rep["expected"] if rep.get("expected") else None
    issues = [i for i in rep.get("issues", []) if i["rule"] in ("SUB-29", "SUB-7")
              and Path(i["file"]).resolve() == spec.resolve()]
    return issues, expected


def declaring_layer(spec: Path, col: str, field: str) -> Path:
    import yamaa

    entry = yamaa.spec(str(spec)).resolve()["entries"][0]
    names = [c["name"] for c in entry["specification"]["columns"]]
    idx = names.index(col)
    o = (entry["origins"].get(f"/columns/{idx}/submission/{field}")
         or entry["origins"].get(f"/columns/{idx}/submission"))
    return Path(o["declaring_source"]) if o else spec


def current(file: Path, col: str, field: str):
    cur = None
    for line in file.read_text().splitlines():
        m = re.match(r"^- name: (\S+)", line)
        if m:
            cur = m.group(1)
        f = re.match(rf"^    {field}: (\S+)", line)
        if cur == col and f:
            try:
                return int(f.group(1))
            except ValueError:
                return None
    return None


def edit(file: Path, col: str, field: str, value) -> bool:
    """Set (or with value None, drop) columns[col].submission.field."""
    lines = file.read_text().split("\n")
    out, cur, in_sub, done = [], None, False, False

    def put():
        nonlocal done
        if value is not None and not done:
            out.append(f"    {field}: {value}")
        done = True

    for n, line in enumerate(lines):
        m = re.match(r"^- name: (\S+)\s*$", line)
        if (m or re.match(r"^\S", line)) and cur == col and in_sub:
            put()
            in_sub = False
        if m:
            cur = m.group(1)
        elif re.match(r"^\S", line):
            cur = None
        if cur == col and re.match(r"^  submission:\s*$", line):
            in_sub = True
            out.append(line)
            if n + 1 >= len(lines) or "SUB-29 (yamaa #4820)" not in lines[n + 1]:
                out.extend(NOTE)
            continue
        if cur == col and in_sub and re.match(r"^  \S", line):
            put()
            in_sub = False
        fm = re.match(r"^    ([a-z_]+): ", line)
        if cur == col and in_sub and fm and fm.group(1) == field:
            put()
            continue
        out.append(line)
    if not done:
        return False
    file.write_text("\n".join(out))
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--study", required=True)
    ap.add_argument("--cut", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--partitions", type=int, default=1)
    ap.add_argument("--out", type=Path, default=ROOT / ".local-run")
    ap.add_argument("--rounds", type=int, default=12)
    args = ap.parse_args()

    spec = ROOT / args.study / args.cut / "spec" / "yamaa" / f"{args.dataset}.yaml"
    import pyarrow.parquet as pq

    for _ in range(args.rounds):
        issues, expected = run_once(args.study, args.cut, args.dataset, args.partitions, args.out, spec)
        if not issues:
            print(f"{args.cut}/{args.dataset}: clean")
            return 0
        for i in issues:
            path = i["spec_paths"][0]
            col = json.loads(i["context"] or "{}").get("column") or path.split(".")[1]
            field = path.rsplit(".", 1)[-1]
            if field not in ("length", "significant_digits", "display_format"):
                field = "significant_digits" if "significant_digits" in i["message"] else "length"
            layer = declaring_layer(spec, col, field)
            if field == "display_format":
                print(f"  {layer.name} {col}: drop display_format", edit(layer, col, field, None))
                continue
            need_len, need_dec = widths(pq.read_table(expected, columns=[col]).column(0).to_pylist()) \
                if expected else (0, 0)
            want = need_len if field == "length" else max(need_dec, 1)
            have = current(layer, col, field)
            if have is not None and want <= have:
                want = have + 2  # the derived values need more than the submitted ones show
            print(f"  {layer.name} {col}: {field} {have} -> {want}", edit(layer, col, field, want))
    print(f"{args.cut}/{args.dataset}: still failing after {args.rounds} rounds")
    return 1


if __name__ == "__main__":
    sys.exit(main())
