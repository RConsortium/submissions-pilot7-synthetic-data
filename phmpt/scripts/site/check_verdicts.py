#!/usr/bin/env python3
"""Fail when a fresh verification run disagrees with the committed results.

    python scripts/site/check_verdicts.py --reports .local-run/reports \
        --study mrna-1273-p201 --cut s3-d57 [--study ... --cut ...]

Compares each report scripts/reproduce.py verify wrote for the given cuts with the verdict recorded in
data/reproduction/adam.json (exact / exact under comparison rules /
mismatch, and the mismatched-cell count). A dataset recorded as checkable
that has no fresh report also fails. Used by CI (.github/workflows/verify.yml).

    python scripts/site/check_verdicts.py --evidence ../docs/phmpt/evidence.json [--study S [--cut C]]

does the same against the published results (Pilot 7's docs/phmpt/evidence.json),
from the kit in phmpt/: a reviewer who reran part of a cut checks what they
ran, so a dataset with no report is skipped there. Without --cut, every cut
of the given studies (or of all studies) is in scope. A define report
(define-<study>-<cut>.json, from `reproduce.py define`) in --reports is checked
too: its verdict, unexplained differences and identical elements.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def verdict(r: dict) -> tuple[str, int]:
    cells = sum(c.get("mismatches", 0) for c in r.get("columns", {}).values())
    v = ("exact" if r.get("strict_exact_match") else
         "exact under comparison rules" if r.get("exact_match") else "mismatch")
    return v, cells


def recorded(evidence: Path | None) -> tuple[dict, dict]:
    """{study: {cut: [dataset rows]}} and {study: {cut: (verdict, unexplained, identical)}}."""
    if evidence:
        ev = json.loads(evidence.read_text())["studies"]
        adam = {s: {c: v["datasets"] for c, v in st["cuts"].items()} for s, st in ev.items()}
        define = {s: {c: (v["define"]["verdict"], v["define"]["unexplained"], v["define"]["identical"])
                      for c, v in st["cuts"].items() if v.get("define")} for s, st in ev.items()}
        return adam, define
    a = json.loads((ROOT / "data/reproduction/adam.json").read_text())["studies"]
    d = json.loads((ROOT / "data/reproduction/define.json").read_text())["studies"]
    adam = {s: dict(st["cuts"]) for s, st in a.items()}
    define = {s: {c: (v["verdict"], len(v["unexplained"]), v["totals"]["match"]) for c, v in st.items()}
              for s, st in d.items()}
    return adam, define


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reports", type=Path, default=ROOT / ".local-run/reports")
    ap.add_argument("--evidence", type=Path,
                    help="compare with a published evidence.json instead of data/reproduction/*.json")
    ap.add_argument("--study", action="append", default=[])
    ap.add_argument("--cut", action="append", default=[])
    a = ap.parse_args()
    adam, define = recorded(a.evidence)
    if a.cut:
        if len(a.cut) != len(a.study):
            ap.error("give one --study for each --cut")
        pairs = list(zip(a.study, a.cut))
    else:
        pairs = [(s, c) for s in (a.study or adam) for c in adam[s]]
    bad = skipped = 0
    for study, cut in pairs:
        for row in adam[study][cut]:
            if row["verdict"] == "not checkable":
                continue
            stem = Path(row["spec"]).stem
            rep = a.reports / f"{study}-{cut}-{stem}.json"
            if not rep.exists():
                if a.evidence:
                    skipped += 1
                    continue
                print(f"FAIL {study} {cut} {stem}: no fresh report")
                bad += 1
                continue
            got = verdict(json.loads(rep.read_text()))
            # A missing-input match is a mismatch whose input the release lacks (data/differences.yaml).
            want = ("mismatch" if row["verdict"] in ("matches except missing input", "reproduced on a substitute input")
                    else row["verdict"], row.get("mismatched_cells", 0))
            ok = got == want
            bad += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {study} {cut} {stem}: {got[0]} ({got[1]} cells)"
                  + ("" if ok else f", recorded {want[0]} ({want[1]} cells)")
                  + (f" [{row['verdict']}]" if row["verdict"] != want[0] else ""))
        rep = a.reports / f"define-{study}-{cut}.json"
        if rep.exists() and cut in define.get(study, {}):
            r = json.loads(rep.read_text())
            got = (r["verdict"], len(r["unexplained"]), r["totals"]["match"])
            want = define[study][cut]
            ok = got == want
            bad += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {study} {cut} define: {got[0]}, {got[1]} unexplained, "
                  f"{got[2]:,} identical" + ("" if ok else f"; recorded {want[0]}, {want[1]} unexplained, "
                                                           f"{want[2]:,} identical"))
    print(f"{bad} disagreement(s)" + (f", {skipped} dataset(s) with no report skipped" if skipped else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
