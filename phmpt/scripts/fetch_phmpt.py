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
reviewed conversion (data/jmp-sources.md). With jmp=True (`fetch --jmp`) each
is saved unconverted, as <path>.jmp beside the Parquet path it belongs at, for
a conversion of your own.

A file already at its repository path is kept, so a rerun reads only what is
missing. A Parquet is kept when its row and column counts are the ones
data/sources.csv records; an interrupted conversion has fewer rows or no
footer and is fetched again. A define or a JMP original is kept when it
exists: each is written as <name>.part and renamed once complete.
refresh=True (`fetch --refresh`) fetches every file again; --out-data always
does.

Needs pyreadstat and zipfile-deflate64 (several zips use Deflate64).
"""
from __future__ import annotations

import collections
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


def dest_path(r, out_data=None) -> Path:
    dest = (Path(out_data) if out_data else ROOT) / r["path"]
    return dest.with_suffix(".jmp") if r["format"] == "jmp" else dest


def present(r, dest) -> bool:
    """True when dest already holds this source row's file (see the module docstring)."""
    if not dest.exists():
        return False
    if r["format"] != "xpt":
        return True
    import pyarrow.parquet as pq
    try:
        m = pq.ParquetFile(dest).metadata
    except (OSError, ValueError):  # no footer: an interrupted write, or a Git LFS pointer
        return False
    return (m.num_rows, m.num_columns) == (int(r["rows"]), int(r["columns"]))


def write_complete(dest, write):
    """Run write(path) on dest.part, then rename it to dest: dest exists only complete."""
    part = dest.with_name(dest.name + ".part")
    try:
        write(part)
        os.replace(part, dest)
    finally:
        part.unlink(missing_ok=True)


def fetch(scope, dataset=None, out_data=None, dry_run=False, jmp_files=False, refresh=False) -> int:
    rows = list(sources(scope, dataset))
    want = [r for r in rows if r["format"] in ("xpt", "xml") or (jmp_files and r["format"] == "jmp")]
    jmp = [r for r in rows if r["format"] == "jmp"]
    keep = set() if refresh or out_data else {r["path"] for r in want if present(r, dest_path(r))}
    todo = [r for r in want if r["path"] not in keep]
    n = collections.Counter(r["format"] for r in todo)
    print(f"{n['xpt']} SAS transport files and {n['xml']} defines to fetch, "
          + (f"{n['jmp']} JMP files to save unconverted (<path>.jmp)" if jmp_files else
             f"{len(jmp)} JMP files not fetched (no open reader; --jmp saves the originals)")
          + (f"; {len(keep)} files already present, kept (--refresh fetches them again)" if keep else ""))
    if dry_run:
        for r in rows:
            kept = "  present, kept" if r["path"] in keep else ""
            print(f"  {r['path']}  <-  {r['zip'].rsplit('/', 1)[-1]} : {r['member']}  ({r['format']}){kept}")
        return 0
    if not todo:
        return 0
    import zipfile_deflate64  # noqa: F401  registers Deflate64 with zipfile
    from convert_xpt import convert_file
    from httpzip import HTTPRangeFile
    import io

    def copy_member(z, member):
        def write(path):
            with z.open(member) as src, open(path, "wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 22)
        return write

    by_zip: dict[str, list] = {}
    for r in todo:
        by_zip.setdefault(r["zip"], []).append(r)
    bad = 0
    for url, items in by_zip.items():
        z = zipfile.ZipFile(io.BufferedReader(HTTPRangeFile(url), buffer_size=1 << 22))
        names = {norm(i.filename.rsplit("/", 1)[-1]): i.filename for i in z.infolist()}
        for r in items:
            member = names.get(norm(r["member"]))
            if member is None:
                print(f"  {r['path']}: {r['member']} is not in {url}"); bad += 1; continue
            dest = dest_path(r, out_data)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if r["format"] == "jmp":  # the original table, for a conversion of your own
                write_complete(dest, copy_member(z, member))
                print(f"  {dest.relative_to(Path(out_data) if out_data else ROOT)}: {dest.stat().st_size:,} bytes")
                continue
            if r["format"] == "xml":  # a received define: its bytes, unchanged
                write_complete(dest, copy_member(z, member))
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
                write_complete(dest, lambda path: convert_file(xpt_path, str(path), url.rsplit("/", 1)[-1]))
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
