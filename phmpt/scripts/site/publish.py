#!/usr/bin/env python3
"""Write docs/phmpt/ (evidence.json and the pages) from data/reproduction/*.json.

    python scripts/site/publish.py            # write ../docs/phmpt/
    python scripts/site/publish.py --check    # exit 1 if ../docs/phmpt/ differs from what this writes

The results come from scripts/site/collect_results.py after a run
(`python scripts/reproduce.py site` runs both). evidence.json is written field
by field through the gate's schema (EVIDENCE in
.github/scripts/check_phmpt_bundle.py), so a new field of a run report stays
out until it is added there. It holds counts, verdicts, column names and the
recorded reasons, never a cell value or a subject identifier. columns.json
lists every submitted column of each dataset with its status, for the review
page; its names come from data/reproduction/columns.json
(scripts/site/inventory_columns.py). The pages are
scripts/site/build_pages.py. docs/phmpt/review/ is written by hand and left
alone. CI runs --check on every pull request.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT.parent / "docs/phmpt"
HAND_WRITTEN = {"review"}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gate = _load("check_phmpt_bundle", ROOT.parent / ".github/scripts/check_phmpt_bundle.py")
pages = _load("build_pages", ROOT / "scripts/site/build_pages.py")
DATASET_FIELDS = [k for k in gate._DATASET if k not in ("source",)]


def sources() -> dict[str, dict]:
    with open(ROOT / "data/sources.csv", newline="") as f:
        return {r["path"]: {"zip": r["zip"], "member": r["member"]} for r in csv.DictReader(f)}


def dataset_record(r: dict, src: dict) -> dict:
    out = {}
    for k in DATASET_FIELDS:
        v = r.get(k)
        if k in ("missing_input", "submitted_defect") and v is not None:
            v = {f: v.get(f, [] if f == "columns" else {} if f == "cells" else "")
                 for f in gate._DATASET[k][0]}
        elif k == "reasons":
            v = [{"kind": x["kind"], "reason": x["reason"], "cells": x.get("cells", {})} for x in v or []]
        elif v is None:
            v = {"note": None, "missing_input": None, "submitted_defect": None}.get(
                k, [] if isinstance(gate._DATASET[k], list) else {} if isinstance(gate._DATASET[k], dict) else 0)
        out[k] = v
    out["source"] = src.get(r.get("expected"))
    return out


def define_record(d: dict, src: dict) -> dict:
    s = pages.define_summary(d)
    nospec = d.get("no_spec_elements", {})
    return {
        "verdict": d["verdict"], "received": s["received"], "identical": s["identical"],
        "gap_only": s["gap_only"], "no_spec": s["nospec"], "no_spec_datasets": s["nospec_datasets"],
        "unexplained": s["unexplained"], "gaps": s["gaps"],
        "classes": {c: {"submitted": v["submitted"], "generated": v["generated"], "match": v["match"],
                        "gap_only": v.get("gap_only", 0), "no_spec": nospec.get(c, 0)}
                    for c, v in d["classes"].items()},
        "source": src[d["received"]],
    }


def claim(r: dict) -> str:
    ds, v = r["dataset"], r["verdict"]
    shape = f"{r.get('rows', 0):,} rows x {r.get('cols', 0)} columns"
    missing = (r.get("missing_input") or {}).get("missing", "")
    defect = (r.get("submitted_defect") or {}).get("defect", "")
    cells = sum((r.get("mismatched_columns") or {}).values())
    text = {
        "exact": f"{ds} reproduces the submitted dataset cell for cell ({shape}).",
        "exact under comparison rules": f"{ds} reproduces the submitted dataset under the comparison rules ({shape}).",
        "matches except missing input": (f"{ds} matches the submitted dataset except where its input is not "
                                         f"in the release: {missing}."),
        "reproduced on a substitute input": (
            f"{ds} is reproduced on a substitute input: the release lacks {missing}, so the spec reads "
            f"{(r.get('missing_input') or {}).get('substitute', '')}; {cells:,} cells differ."),
        "matches except a submitted-file defect": (
            f"{ds} matches the submitted dataset except where the submitted file is defective: {defect}."),
        "matches except missing input and a submitted-file defect": (
            f"{ds} matches the submitted dataset except where its input is not in the release "
            f"({missing}) and where the submitted file is defective ({defect})."),
        "mismatch": (f"{ds} differs from the submitted dataset in {cells:,} cells; each has a recorded cause "
                     f"or is listed as unexplained."),
    }.get(v, f"{ds} is not checked here. {r.get('note', '')}".strip())
    if r.get("carried_columns"):
        text += f" {len(r['carried_columns'])} columns are carried from the submitted dataset, not derived."
    return text


def evidence() -> dict:
    adam = json.loads((ROOT / "data/reproduction/adam.json").read_text())
    define = json.loads((ROOT / "data/reproduction/define.json").read_text())
    info = yaml.safe_load((ROOT / "studies.yaml").read_text())
    src = sources()
    meta = adam["meta"]
    out = {"schema_version": gate.SCHEMA_VERSION,
           "meta": {"yamaa_commit": meta["yamaa_commit"], "source_commit": meta["source_commit"],
                    "collected": meta["collected"]},
           # Schema 1 keeps the key `gaps`; it holds the defects of the submitted define.
           "gaps": {g: {"title": f"{label}. {text}", "yamaa_issue": n} for g, (label, text, n) in pages.DEFECTS.items()},
           "studies": {}, "findings": []}
    for study, st in adam["studies"].items():
        si = info[study]
        cuts = {}
        for cut, rows in st["cuts"].items():
            c = si["cuts"][cut]
            d = define["studies"][study].get(cut)
            cuts[cut] = {"title": c["title"], "application": str(c["application"]), "sequence": c["sequence"],
                         "over": c.get("over"), "datasets": [dataset_record(r, src) for r in rows],
                         "define": define_record(d, src) if d else None}
            page = f"findings/{pages.PAGES[study]}/#{cut}"
            for r in rows:
                # What this dataset reads: the cut, the cut it supplements, other cuts' files, the lists.
                fetch = [" ".join(c.split()) for c in pages.fetch_plan(study, cut, [r])]
                out["findings"].append({
                    "id": f"phmpt/{study}/{cut}/{r['dataset']}", "kind": "dataset", "study": study, "cut": cut,
                    "dataset": r["dataset"], "verdict": r["verdict"], "claim": claim(r), "page": page,
                    "ci": bool(si.get("ci")),
                    "reproduce": fetch + [f"python scripts/reproduce.py verify --study {study} --cut {cut} "
                                          f"--dataset {Path(r['spec']).stem}"]})
            if d:
                rec = cuts[cut]["define"]
                scoped = rec["received"] - rec["no_spec"]
                define_cmds = [f"python scripts/reproduce.py fetch --study {study} --dataset define-adam",
                               f"python scripts/reproduce.py define --study {study} --transcribe"]
                out["findings"].append({
                    "id": f"phmpt/{study}/{cut}/define", "kind": "define", "study": study, "cut": cut,
                    "dataset": None, "verdict": rec["verdict"],
                    "claim": (f"The define yamaa composes reproduces {rec['identical'] + rec['gap_only']:,} of the "
                              f"{scoped:,} received elements of datasets with a spec, {rec['identical']:,} of them "
                              f"byte for byte; {rec['unexplained']} differ for a reason other than a named defect "
                              f"of the submitted define."),
                    "page": page, "ci": True, "reproduce": define_cmds})
                for g, n in sorted(rec["gaps"].items()):
                    out["findings"].append({
                        "id": f"phmpt/{study}/{cut}/define/{g}", "kind": "define-defect", "study": study,
                        "cut": cut, "dataset": None, "verdict": "submitted-define defect",
                        "claim": (f"{n:,} define differences come from a defect of the submitted define, which "
                                  f"yamaa does not copy: {pages.DEFECTS[g][1]}"),
                        "page": page, "ci": True, "reproduce": define_cmds})
        out["studies"][study] = {"title": si["title"], "sponsor": si["sponsor"], "product": si["product"],
                                 "cuts": cuts}
    return out


def columns() -> dict:
    """columns.json: every submitted column of every dataset finding, for the review page's drill-down.
    Compact, one dataset per line; names, statuses, counts, spec lines and recorded reasons only."""
    adam = json.loads((ROOT / "data/reproduction/adam.json").read_text())
    out = {"schema_version": gate.COLUMNS_VERSION, "fields": gate.COLUMN_FIELDS,
           "statuses": dict(pages.COLUMN_STATUS), "datasets": {}}
    for key, st, cut, r in pages.all_rows(adam):
        rows, notes = pages.column_rows(key, cut, r)
        if rows:
            out["datasets"][f"phmpt/{key}/{cut}/{r['dataset']}"] = {
                "layers": r.get("layers") or [], "notes": notes,
                "columns": [[c[f] for f in gate.COLUMN_FIELDS] for c in rows]}
    return out


def write(site: Path) -> dict:
    """Write evidence.json, columns.json and the pages into site, replacing what an earlier run wrote."""
    site.mkdir(parents=True, exist_ok=True)
    for p in site.rglob("*"):
        if p.is_file() and p.relative_to(site).parts[0] not in HAND_WRITTEN:
            p.unlink()
    ev = evidence()
    (site / "evidence.json").write_text(json.dumps(ev, indent=1, ensure_ascii=True) + "\n")
    cols = columns()
    (site / "columns.json").write_text(
        "{" + f'"schema_version": {cols["schema_version"]},\n"fields": {json.dumps(cols["fields"])},\n'
        + f'"statuses": {json.dumps(cols["statuses"])},\n'
        + '"datasets": {\n' + ",\n".join(f"{json.dumps(k)}: {json.dumps(v, separators=(',', ':'))}"
                                          for k, v in cols["datasets"].items()) + "\n}}\n")
    pages.public_profile(site)
    return ev


def generated(site: Path) -> dict[str, bytes]:
    return {str(p.relative_to(site)): p.read_bytes() for p in sorted(site.rglob("*"))
            if p.is_file() and p.relative_to(site).parts[0] not in HAND_WRITTEN}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="compare with docs/phmpt/ instead of writing it")
    args = ap.parse_args()
    if not args.check:
        ev = write(SITE)
        print(f"wrote {SITE}: evidence.json ({len(ev['findings'])} findings) and the pages")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        write(Path(tmp))
        want, have = generated(Path(tmp)), generated(SITE)
    stale = sorted(set(have) - set(want))
    differ = sorted(k for k in want if have.get(k) != want[k])
    for k in differ:
        print(f"differs from data/reproduction/: docs/phmpt/{k}")
    for k in stale:
        print(f"not written by publish.py: docs/phmpt/{k}")
    if differ or stale:
        print("run `python scripts/site/publish.py` in phmpt/ and commit docs/phmpt/")
        return 1
    print(f"docs/phmpt/ matches data/reproduction/ ({len(want)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
