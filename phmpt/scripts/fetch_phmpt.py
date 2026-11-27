#!/usr/bin/env python3
"""Fetch a cut's submitted datasets from PHMPT (python scripts/reproduce.py fetch).

data/sources.csv lists every dataset file the repository holds, and each
cut's received define-adam.xml, with the PHMPT Full Productions zip and the
zip member it came from. For each file in scope this reads only that member
from the zip on PHMPT's storage, with HTTP range requests (the zips are up to
tens of GB; a member is read without the rest), and writes it at its
repository path, or under --out-data to compare with the repository copy: a
SAS transport file converted to Parquet (scripts/convert_xpt.py), a define
copied byte for byte.

Forty files exist on PHMPT only as JMP tables (P301 and C4591001); JMP has no
open reader, so they are listed and skipped: the repository copy is the
reviewed conversion (data/jmp-sources.md).

Needs pyreadstat and zipfile-deflate64 (several zips use Deflate64).
"""
from __future__ import annotations

import csv
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "site"))


def norm(name: str) -> str:
    return " ".join(name.lower().replace(" to -", "-").split())


def sources(scope, dataset):
    want = set(scope)
    for r in csv.DictReader(open(ROOT / "data/sources.csv")):
        if (r["study"], r["cut"]) in want and (not dataset or Path(r["path"]).stem == dataset):
            yield r


def fetch(scope, dataset=None, out_data=None, dry_run=False) -> int:
    rows = list(sources(scope, dataset))
    xpt = [r for r in rows if r["format"] in ("xpt", "xml")]
    jmp = [r for r in rows if r["format"] == "jmp"]
    n_xml = sum(r["format"] == "xml" for r in xpt)
    print(f"{len(xpt) - n_xml} SAS transport files and {n_xml} defines to fetch, "
          f"{len(jmp)} JMP files kept as reviewed conversions")
    if dry_run:
        for r in rows:
            print(f"  {r['path']}  <-  {r['zip'].rsplit('/', 1)[-1]} : {r['member']}  ({r['format']})")
        return 0
    import zipfile_deflate64  # noqa: F401  registers Deflate64 with zipfile
    from convert_xpt import convert_file
    from httpzip import HTTPRangeFile
    import io

    by_zip: dict[str, list] = {}
    for r in xpt:
        by_zip.setdefault(r["zip"], []).append(r)
    bad = 0
    for url, items in by_zip.items():
        z = zipfile.ZipFile(io.BufferedReader(HTTPRangeFile(url), buffer_size=1 << 22))
        names = {norm(i.filename.rsplit("/", 1)[-1]): i.filename for i in z.infolist()}
        for r in items:
            member = names.get(norm(r["member"]))
            if member is None:
                print(f"  {r['path']}: {r['member']} is not in {url}"); bad += 1; continue
            dest = Path(out_data) / r["path"] if out_data else ROOT / r["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            if r["format"] == "xml":  # a received define: its bytes, unchanged
                with z.open(member) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst, 1 << 22)
                note = ""
                if out_data and (ROOT / r["path"]).exists():
                    same = dest.read_bytes() == (ROOT / r["path"]).read_bytes()
                    note = "  equal to the repository copy" if same else "  DIFFERS from the repository copy"
                    bad += not same
                print(f"  {r['path']}: {dest.stat().st_size:,} bytes{note}")
                continue
            with tempfile.TemporaryDirectory() as tmp:
                xpt_path = os.path.join(tmp, "data.xpt")
                with z.open(member) as src, open(xpt_path, "wb") as dst:
                    shutil.copyfileobj(src, dst, 1 << 22)
                convert_file(xpt_path, str(dest), url.rsplit("/", 1)[-1])
            note = ""
            if out_data and (ROOT / r["path"]).exists():
                import pyarrow.parquet as pq
                a, b = pq.read_table(dest), pq.read_table(ROOT / r["path"])
                note = "  equal to the repository copy" if a.equals(b) else "  DIFFERS from the repository copy"
                bad += not a.equals(b)
            print(f"  {r['path']}: {pq_rows(dest):,} rows{note}")
    return 1 if bad else 0


def pq_rows(p) -> int:
    import pyarrow.parquet as pq
    return pq.ParquetFile(p).metadata.num_rows
