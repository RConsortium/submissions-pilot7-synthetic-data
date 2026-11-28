#!/usr/bin/env python3
"""Collect reproduction results into data/reproduction/*.json for the site.

    python scripts/site/collect_results.py --reports .local-run/reports

Reads, for every study and cut in studies.yaml:
  * the dataset reports scripts/reproduce.py verify writes
    (<study>-<cut>-<dataset>.json);
  * each spec, through yamaa, for its inheritance chain and the columns it
    carries from a submitted dataset (inputs named *_VO);
  * each cut's composed define against the received one
    (scripts/define/compare_define.py);
  * data/differences.yaml: differences from missing input, submitted-file defects, open differences and holds, each
    with its reason.
Writes data/reproduction/adam.json and define.json. Needs a python that
imports yamaa.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def spec_facts(spec: Path) -> dict:
    import yamaa

    entry = yamaa.spec(str(spec)).resolve()["entries"][0]
    s = entry["specification"]
    layers = [str(Path(l).resolve().relative_to(ROOT)) for l in entry["layers"]]
    out_cols = s["output"]["columns"]
    carried = [c["name"] for c in s.get("columns", [])
               if c["name"] in out_cols and "_VO." in json.dumps(c.get("derivation"))]
    # Submitted ADaM datasets (other than ADSL, which most specs read) the spec takes as input:
    # shown so that a value built on another submitted dataset is not taken for one built from SDTM.
    adam_inputs = sorted({Path(v["path"] if isinstance(v, dict) else v).stem.upper()
                          for v in (s.get("input") or {}).values()
                          if "/adam/" in (v["path"] if isinstance(v, dict) else v)
                          or "<adam-dir>/" in (v["path"] if isinstance(v, dict) else v)}
                         - {"ADSL", spec.stem.upper()})
    return {"layers": layers, "output_columns": len(out_cols), "carried_columns": carried,
            "adam_inputs": adam_inputs}


def count_lines(p: Path) -> int:
    return len(p.read_text(encoding="utf-8").splitlines())


# The accepted categories of data/differences.yaml: (key, verdict, field naming the cause).
ACCEPTED = [("missing_input", "matches except missing input", "missing"),
            ("submitted_defect", "matches except a submitted-file defect", "defect")]


def apply_differences(study: str, cut: str, row: dict, diffs: dict) -> dict:
    """data/differences.yaml: missing input, submitted-file defects, open differences (reasons), holds
    and notes where the program and the submitted dataset disagree."""
    def match(e):
        return e["study"] == study and e["dataset"] == row["dataset"] and cut in e["cuts"]

    def covers(entries):
        cells = {}
        for e in entries:
            for col, n in e.get("cells", {}).items():
                cells[col] = cells.get(col, 0) + n
        columns = set().union(*(set(e.get("columns", [])) for e in entries))
        return (not row.get("extra_columns")
                and set(row.get("missing_columns", [])) <= columns
                and (any(e.get("rows_differ") for e in entries)
                     or (row.get("out_rows") == row.get("rows") and not row.get("rows_unpaired")))
                and all(col in cells and n <= cells[col] for col, n in row.get("mismatched_columns", {}).items()))

    for e in diffs.get("hold", []):
        if match(e):
            row["hold"] = {"reason": e["reason"], "decided": e["decided"]}
    notes = [" ".join(e["note"].split()) for e in diffs.get("program_notes", []) if match(e)]
    if notes:
        row["program_notes"] = notes
    if row.get("verdict") != "mismatch":
        return row
    # The accepted entries together may explain every difference (C4591001 EUA
    # ADMH: redacted dates, and one defective cell of the submitted file).
    accepted = [(key, verdict, what, e) for key, verdict, what in ACCEPTED for e in diffs.get(key, []) if match(e)]
    if accepted and covers([e for *_, e in accepted]):
        kinds = []
        for key, verdict, what, e in accepted:
            kind = verdict.removeprefix("matches except ")
            if kind not in kinds:
                kinds.append(kind)
            g = row.setdefault(key, {"reason": "", what: e[what], "decided": e["decided"], "columns": [],
                                     "cells": {c: n for c, n in row["mismatched_columns"].items()
                                               if any(c in x.get("cells", {}) for k2, *_, x in accepted if k2 == key)}})
            g["reason"] = (g["reason"] + " " + " ".join(e["reason"].split())).strip()
            g["columns"] += e.get("columns", [])
            if e.get("substitute"):
                g.update(substitute=e["substitute"], subjects=e.get("subjects"))
        # A spec run on another release's snapshot in place of the absent input
        # reproduces the subjects the snapshots agree on, not "all but a few values".
        substitute = any(e.get("substitute") for key, *_, e in accepted if key == "missing_input")
        row["verdict"] = ("reproduced on a substitute input" if substitute
                          else "matches except " + " and ".join(kinds))
        return row
    # A dataset can carry an accepted difference and an open one at once
    # (C4591001 ADSL: the redacted birth date, and EV1MD2FL): both reasons show.
    reasons = []
    kinds = [(k, v.removeprefix("matches except ")) for k, v, _ in ACCEPTED] + [("open", "open")]
    for key, kind in kinds:
        for e in diffs.get(key, []):
            if match(e):
                reasons.append({"kind": kind, "reason": " ".join(e["reason"].split()),
                                "cells": {c: n for c, n in row["mismatched_columns"].items() if c in e.get("cells", {})}})
    if reasons:
        row["reasons"] = reasons
        covered = set().union(*(set(r["cells"]) for r in reasons))
        row["unexplained_columns"] = [c for c in row["mismatched_columns"] if c not in covered]
    return row


def dataset_row(study: str, cut: str, spec: Path, reports: Path, diffs: dict) -> dict:
    ds = spec.stem
    rep = reports / f"{study}-{cut}-{ds}.json"
    row = {"dataset": ds.upper(), "spec": str(spec.relative_to(ROOT)), "spec_lines": count_lines(spec)}
    try:
        row.update(spec_facts(spec))
    except Exception as e:  # noqa: BLE001
        row.update(layers=[str(spec.relative_to(ROOT))], output_columns=0, carried_columns=[],
                   resolve_error=str(e)[:300])
    if not rep.exists():
        row.update(verdict="not checkable", note="not run")
        return row
    r = json.loads(rep.read_text())
    if r["status"] in ("error", "no expected"):
        row.update(verdict="not checkable", note=r.get("reason", r["status"]))
        return row
    cols = r.get("columns", {})
    row.update(
        expected=r["expected"],
        rows=r["expected_rows"], cols=len(r["expected_cols"]), cells=r["expected_rows"] * len(r["expected_cols"]),
        out_rows=r["out_rows"], out_cols=len(r["out_cols"]),
        missing_columns=[c for c in r["expected_cols"] if c not in r["out_cols"]],
        extra_columns=[c for c in r["out_cols"] if c not in r["expected_cols"]],
        mismatched_cells=sum(c.get("mismatches", 0) for c in cols.values()),
        within_tolerance_cells=sum(c.get("within_tolerance", 0) for c in cols.values()),
        space_only_cells=sum(c.get("space_only_diffs", 0) for c in cols.values()),
        mismatched_columns={k: v["mismatches"] for k, v in cols.items() if v.get("mismatches")},
        # Submitted cells FDA redacted to (b)(6) (FOIA exemption 6) are not
        # compared (scripts/verify_compare.py, REDACTED); they are counted.
        redacted_cells=sum(c.get("redacted_skipped", 0) for c in cols.values()),
        redacted_columns={k: v["redacted_skipped"] for k, v in cols.items() if v.get("redacted_skipped")},
        shape_matches=r["out_rows"] == r["expected_rows"] and r["out_cols"] == r["expected_cols"],
        multiset=bool(r.get("multiset_comparison")),
        rows_only_out=r.get("rows_only_in_out", 0), rows_only_expected=r.get("rows_only_in_expected", 0),
        # Multiset comparison pairs unmatched rows within their keys; a row with
        # no partner is a whole-row difference.
        rows_paired=r.get("rows_paired", 0),
        rows_unpaired=(r.get("rows_unpaired_out", r.get("rows_only_in_out", 0))
                       + r.get("rows_unpaired_expected", r.get("rows_only_in_expected", 0))),
        partitions=r.get("partitions", 1),
        # Reports from scripts/verify_compare.py after it learned to compare the columns both sides have
        # when the column sets differ, and to record the keys on one side only in a keyed comparison.
        common_columns_compared="compared_cols" in r,
        rows_recorded="rows_only_in_expected" in r,
        verdict=r["status"] if r["status"] in ("exact", "exact under comparison rules") else "mismatch",
    )
    return apply_differences(study, cut, row, diffs)


def define_row(study: str, cut: str) -> dict:
    d = ROOT / study / cut / "spec" / "define"
    received, generated = d / "define-adam.xml", d / "define-adam-yamaa.xml"
    if not received.exists():  # a supplement without a define of its own
        return None
    out = ROOT / ".local-run" / f"define-{study}-{cut}.json"
    out.parent.mkdir(exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / "scripts/define/compare_define.py"), str(received),
                    str(generated), "--json", str(out)], capture_output=True, text=True)
    rep = json.loads(out.read_text())
    wrappers = sorted(d.glob("ad*.yaml"))
    rep.update(received=str(received.relative_to(ROOT)), generated=str(generated.relative_to(ROOT)),
               project=str((d / "project.yaml").relative_to(ROOT)),
               wrapper_lines=sum(count_lines(w) for w in wrappers), wrappers=len(wrappers))
    return rep


def yamaa_commit() -> str:
    for line in (ROOT / "yamaa.lock").read_text().splitlines():
        if line.startswith("commit:"):
            return line.split()[1][:7]
    return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", type=Path, default=ROOT / ".local-run/reports")
    ap.add_argument("--yamaa-commit", default=None, help="default: yamaa.lock")
    args = ap.parse_args()
    studies = yaml.safe_load((ROOT / "studies.yaml").read_text())
    diffs = yaml.safe_load((ROOT / "data/differences.yaml").read_text())
    adam, define = {}, {}
    for key, st in studies.items():
        adam[key] = {"title": st["title"], "sponsor": st["sponsor"], "dir": key,
                     "cut_titles": {c: v["title"] for c, v in st["cuts"].items()}, "cuts": {}}
        define[key] = {}
        for cut in st["cuts"]:
            specs = sorted((ROOT / key / cut / "spec/yamaa").glob("ad*.yaml"))
            adam[key]["cuts"][cut] = [dataset_row(key, cut, s, args.reports, diffs) for s in specs]
            row = define_row(key, cut)
            if row is not None:
                define[key][cut] = row
    meta = {"yamaa_commit": args.yamaa_commit or yamaa_commit(), "collected": dt.date.today().isoformat()}
    out = ROOT / "data" / "reproduction"
    out.mkdir(parents=True, exist_ok=True)
    (out / "adam.json").write_text(json.dumps({"meta": meta, "studies": adam}, indent=1) + "\n")
    (out / "define.json").write_text(json.dumps({"meta": meta, "studies": define}, indent=1) + "\n")
    print(f"wrote {out}/adam.json and define.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
