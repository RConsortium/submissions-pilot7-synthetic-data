#!/usr/bin/env python3
"""Inventory what PHMPT Module 5 holds for every study, without downloading it.

Reads the central directory of each Full Productions zip in data/zips.txt
with HTTP range requests (scripts/site/httpzip.py: a few hundred kB per
zip, never the archive), classifies every entry that names a study, and
writes data/reproduction/module5.json for the findings site:

    python scripts/site/inventory_module5.py            # network, ~1 minute

An entry is counted under the first study id its name contains (see
STUDIES). Kinds: ADaM / SDTM transport files (.xpt, .jmp), Define-XML,
programs (.sas, .txt in an _A_P_ program folder), and documents (.pdf,
.xlsx, other).
"""
from __future__ import annotations

import collections
import concurrent.futures as cf
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from httpzip import entries  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

# study id -> (sponsor, repo folder, name tokens). The four worked studies
# first; the rest are the stub folders of this repo.
STUDIES = {
    "mrna1273-p201": ("Moderna", "moderna/mrna-1273/p201", ["mrna-1273-p201", "1273p201", "mrna1273p201"]),
    "mrna1273-p301": ("Moderna", "moderna/mrna-1273/p301", ["mrna-1273-p301", "1273p301", "mrna1273p301"]),
    "bnt162-01": ("Pfizer/BioNTech", "pfizer/bnt162b2/bnt162-01", ["bnt162-01"]),
    "c4591001": ("Pfizer/BioNTech", "pfizer/bnt162b2/c4591001", ["c4591001"]),
}
for s in ["dmid-200003", "mrna1273-p901", "mrna1273-p902", "mrna1273-p903", "mrna1273-p904", "mrna1273-p905"]:
    tok = s.replace("mrna1273-", "")
    STUDIES[s] = ("Moderna", f"moderna/mrna-1273/{s}", [s, f"mrna-1273-{tok}", f"1273{tok}", f"mrna1273{tok}"] if s != "dmid-200003" else [s])
for s in ["c4591007", "c4591008", "c4591009", "c4591011", "c4591012", "c4591014", "c4591015",
          "c4591020", "c4591021", "c4591022", "wi235284", "wi255886"]:
    STUDIES[s] = ("Pfizer/BioNTech", f"pfizer/bnt162b2/{s}", [s])


def kind(name: str) -> str:
    low = name.lower()
    ext = low.rsplit(".", 1)[-1]
    if ext in ("xpt", "jmp", "sas7bdat"):
        if re.search(r"[_-]a[_-]", low):
            return "adam"
        if re.search(r"[_-]s[_-]", low):
            return "sdtm"
        return "dataset"
    if ext == "xml":  # every Module 5 XML is a define; P201 names are truncated (_A_D_de.xml)
        return "define"
    if ext == "xsl":
        return "stylesheet"
    if ext in ("sas", "txt") and re.search(r"[_-]a[_-]p[_-]|program", low):
        return "program"
    if ext == "pdf":
        return "pdf"
    return "other"


def study_of(name: str) -> str | None:
    low = name.lower()
    for sid, (_, _, toks) in STUDIES.items():
        if any(t in low for t in toks):
            return sid
    return None


def main() -> int:
    urls = [l.strip().split()[-1] for l in (ROOT / "data/zips.txt").read_text().splitlines() if "http" in l]

    def one(u):
        for _ in range(3):
            try:
                return u, entries(u)
            except Exception as e:  # noqa: BLE001
                err = e
        return u, (None, str(err))

    per = {sid: collections.Counter() for sid in STUDIES}
    zips_of = {sid: set() for sid in STUDIES}
    unread = []
    with cf.ThreadPoolExecutor(6) as ex:
        for u, (size, ents) in ex.map(one, urls):
            if size is None:
                unread.append(u)
                continue
            for name, _bytes in ents:
                sid = study_of(name)
                if sid:
                    per[sid][kind(name)] += 1
                    zips_of[sid].add(u.rsplit("/", 1)[-1])
    out = {"collected": dt.date.today().isoformat(), "zips": len(urls), "unread_zips": unread,
           "studies": {sid: {"sponsor": STUDIES[sid][0], "folder": STUDIES[sid][1],
                             "files": dict(per[sid]), "zips": sorted(zips_of[sid])} for sid in STUDIES}}
    path = ROOT / "data/reproduction/module5.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    for sid, c in per.items():
        print(f"{sid:16s} {dict(c)}")
    print(f"wrote {path.relative_to(ROOT)} ({len(unread)} zips unread)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
