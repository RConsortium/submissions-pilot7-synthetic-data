#!/usr/bin/env python3
"""Write the PHMPT pages of the Pilot 7 site from data/reproduction/*.json.

    python scripts/site/build_pages.py [DIR]    # default: ../docs/phmpt

scripts/site/publish.py runs this and writes docs/phmpt/evidence.json with
it; run that instead. Generated, never edited by hand (DIR is docs/phmpt/):

    index.md                     the overview: what was done and found, in charts
    results.md                   key findings, the analysis set, results by study and by cut
    glossary.md                  the terms the pages use
    findings/index.md            how the reproduction is organised
    findings/<study>.md          one page per study with specs
    findings/inputs.md           what the analysis set leaves out: absent and problem inputs
    findings/define-data.md      the received defines checked against the submitted datasets
    coverage.md                  what Module 5 holds for all 22 studies

The review page (docs/phmpt/review/) is written by hand. Inputs:
data/reproduction/adam.json and define.json (scripts/site/collect_results.py),
module5.json (scripts/site/inventory_module5.py), define_data.json
(scripts/define/check_define_data.py) and data/differences.yaml, whose absent
inputs fix the analysis set (input_scope). The pages are ASCII (Pilot 7's
rule) and name no PHMPT file content. How to rerun a study from PHMPT is
phmpt/reproduce.sh, which the pages link to.

The pages read the specs' `parent:` and `input:` blocks directly (not through
yamaa) to name the files each dataset reads: what to fetch for a cut, and
which results depend on a file PHMPT released only as a JMP table.
"""
from __future__ import annotations

import argparse
import csv
import functools
import html
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = ROOT.parent / "docs/phmpt"
YAMAA = "https://github.com/elong0527/yamaa"
PILOT7 = "https://github.com/RConsortium/submissions-pilot7-synthetic-data"
BLOB = f"{PILOT7}/blob/main/phmpt"
TREE = f"{PILOT7}/tree/main/phmpt"
# The public pages are ASCII (Pilot 7's rule); these are the only non-ASCII
# characters the builder writes itself. Anything else fails the bundle check.
ASCII = str.maketrans({"\u00d7": "x", "\u00b7": "-", "\u2013": "-", "\u2014": "-", "\u2026": "..."})

# Defects of the submitted define (scripts/define/compare_define.py DEFECTS): id -> (short label,
# what it is, the yamaa issue that holds the owner's decision). Glossary: #define-defect.
DEFECTS = {
    "repeated-order": ("Repeated codelist `OrderNumber`",
                       "A received codelist gives two items the same `OrderNumber`, which the ODM 1.3.2 schema "
                       "forbids (`xs:unique` UC-CL-2 and UC-CL-4). yamaa writes no schema-invalid document, so the "
                       "codelist is written without `OrderNumber`.", 5022),
    "arm-terms": ("Nonstandard analysis-results metadata",
                  "A received `AnalysisReason` or `AnalysisPurpose` that is not a published ARM 1.0 term "
                  "(such as `SAP`, `Primary Endpoints`, or `PRIMARY OUTCOME MEASURE` broken by a line feed), or "
                  "an empty `arm:Documentation` or `arm:ProgrammingCode`. yamaa writes the published term the "
                  "value names and no empty element.", 4824),
    "method-oid-nbsp": ("Method OID with a non-breaking space",
                        "A received method OID ends in an invisible non-breaking space (U+00A0), which is not an "
                        "identifier character (owner decision D398). yamaa writes the OID without it.", 4935),
}
CLASS_LABELS = {
    "ItemGroupDef": "Datasets (ItemGroupDef)",
    "ItemDef": "Variables (ItemDef)",
    "MethodDef": "Methods (MethodDef)",
    "def:CommentDef": "Comments (CommentDef)",
    "CodeList": "Codelists (CodeList)",
    "def:ValueListDef": "Value lists (ValueListDef)",
    "def:WhereClauseDef": "Where clauses (WhereClauseDef)",
    "def:leaf": "Documents (leaf)",
    "def:SupplementalDoc": "Supplemental documents",
    "arm:ResultDisplay": "Result displays (ARM)",
}
PAGES = {k: k for k in ("mrna-1273-p201", "mrna-1273-p301", "bnt162-01", "c4591001")}  # study folder = page name


def runner() -> str:
    """A link to the bundle's script that reruns a study from PHMPT (public pages only)."""
    return f"[`phmpt/reproduce.sh`]({BLOB}/reproduce.sh)"


def pct(a: int, b: int) -> str:
    if not b:
        return "n/a"
    v = 100 * a / b
    return f"{v:.0f}%" if a in (0, b) else f"{min(v, 99.9):.1f}%"


def millions(n: int) -> str:
    return f"{n / 1e6:,.2f}M" if n >= 1e5 else f"{n:,}"


def issue(n: int) -> str:
    return f"[yamaa#{n}]({YAMAA}/issues/{n})"


def defect_label(g: str) -> str:
    """A defect's short label inside a sentence: lower-case first letter only (`OrderNumber`, OID stay)."""
    label = DEFECTS[g][0]
    return label[0].lower() + label[1:]


def adam_summary(rows: list) -> dict:
    checked = [r for r in rows if r["verdict"] != "not checkable"]
    exact = [r for r in checked if r["verdict"].startswith("exact")]
    accepted = [r for r in checked if r["verdict"] == "matches except missing input"]
    substituted = [r for r in checked if r["verdict"] == "reproduced on a substitute input"]
    # A submitted-file defect, alone or beside missing input (data/differences.yaml `submitted_defect`).
    defect = [r for r in checked if r["verdict"].startswith("matches except") and r not in accepted]
    return {
        "specs": len(rows), "checked": len(checked), "exact": len(exact), "accepted": len(accepted),
        "substituted": len(substituted), "defect": len(defect),
        "cells": sum(r["cells"] for r in checked), "cells_exact": sum(r["cells"] for r in exact),
        "lines": sum(r["spec_lines"] for r in rows),
    }


def define_summary(rep: dict) -> dict:
    t = rep["totals"]
    nospec = sum(rep.get("no_spec_elements", {}).values())
    return {"received": t["sub"], "identical": t["match"], "gap_only": t.get("gap_only", 0),
            "nospec": nospec, "nospec_datasets": rep.get("datasets_without_spec", []),
            "unexplained": len(rep["unexplained"]),
            "gaps": {g: v["count"] for g, v in rep["gaps"].items()}}


def cut_rows(adam: dict):
    for key, st in adam["studies"].items():
        for cut, rows in st["cuts"].items():
            yield key, st, cut, rows


# ---------------------------------------------------------------- what each dataset reads
@functools.lru_cache(maxsize=None)
def studies_info() -> dict:
    return yaml.safe_load((ROOT / "studies.yaml").read_text())


@functools.lru_cache(maxsize=None)
def sources() -> tuple:
    """data/sources.csv: every file fetch provides, with its PHMPT zip and member."""
    with open(ROOT / "data/sources.csv", newline="") as f:
        return tuple(csv.DictReader(f))


@functools.lru_cache(maxsize=None)
def _top(path: Path, key: str):
    """One top-level key of a spec file, parsed on its own (the specs are large)."""
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            j = i + 1
            while j < len(lines) and (not lines[j] or lines[j][0] in " #-"):
                j += 1
            return (yaml.safe_load("\n".join(lines[i:j])) or {}).get(key)
    return None


def spec_chain(spec: Path) -> list[Path]:
    """A spec and the layers it builds on (`parent:`, one path or a list), parents first."""
    par = _top(spec, "parent") or []
    out: list[Path] = []
    for p in [par] if isinstance(par, str) else par:
        for f in spec_chain((spec.parent / p).resolve()):
            if f not in out:
                out.append(f)
    return out + [spec]


def declared_inputs(spec: Path) -> list[str]:
    """The input paths a spec reads, as written, and those of the helper specs it reads through a
    `schema:` link. A layer's input replaces its parent's input of the same name."""
    merged: dict = {}
    for f in spec_chain(spec):
        for name, v in (_top(f, "input") or {}).items():
            merged[name] = (v, f)
    out: list[str] = []
    for v, f in merged.values():
        out.append(v["path"] if isinstance(v, dict) else v)
        if isinstance(v, dict) and v.get("schema"):
            out += declared_inputs((f.parent / v["schema"]).resolve())
    return out


def input_file(study: str, cut: str, declared: str) -> str | None:
    """The file a declared input names when the cut runs (scripts/reproduce.py input_path): a
    cut that resends only some domains reads the others from the cut it supplements."""
    known = {r["path"] for r in sources()}
    for ph, base in (("<sdtm-dir>/", f"{study}/{cut}/data/sdtm/"), ("<adam-dir>/", f"{study}/{cut}/data/adam/"),
                     ("<list-dir>/", f"{study}/data/lists/"), ("<study-dir>/", f"{study}/")):
        if ph in declared:
            p = base + declared.split(ph, 1)[1]
            fb = studies_info()[study]["cuts"][cut].get("sdtm_from")
            if fb and p not in known and ph in ("<sdtm-dir>/", "<adam-dir>/"):
                alt = f"{study}/{fb}/data/{ph[1:5]}/{p.rsplit('/', 1)[1]}"
                if alt in known:
                    return alt
            return p
    return None  # <work-dir>: a helper spec's output


def dataset_files(study: str, cut: str, r: dict) -> dict[str, str]:
    """{file: "reference" or "input"} for one dataset: the submitted dataset it is compared with
    and every file it, or a helper spec it reads, takes as input."""
    out = {}
    for d in declared_inputs(ROOT / r["spec"]):
        p = input_file(study, cut, d)
        if p:
            out[p] = "input"
    if r.get("expected"):
        out[r["expected"]] = "reference"
    return out


def fetch_plan(study: str, cut: str, rows: list) -> list[str]:
    """Kit commands that fetch what these datasets of the cut read: the cut itself, the cut it
    supplements (`sdtm_from`), single files of other cuts (<study-dir>), and the study-level lists."""
    base = studies_info()[study]["cuts"][cut].get("sdtm_from")
    other: set[tuple[str, str]] = set()
    lists = False
    for r in rows:
        for p in dataset_files(study, cut, r):
            parts = p.split("/")
            if parts[1] == "data":  # <study>/data/lists/
                lists = True
            elif parts[1] not in (cut, base):
                other.add((parts[1], Path(p).stem))
    cmds = [f"python scripts/reproduce.py fetch  --study {study} --cut {c}" for c in ([base] if base else []) + [cut]]
    cmds += [f"python scripts/reproduce.py fetch  --study {study} --cut {c} --dataset {d}" for c, d in sorted(other)]
    if lists:
        cmds.append("python scripts/convert_lists.py")
    return cmds


# ---------------------------------------------------------------- verdict words
RESULT_DEFECT = ("matches except a submitted-file defect", "matches except missing input and a submitted-file defect")
RESULT = {"exact": "Exact", "exact under comparison rules": "Exact under the comparison rules",
          "matches except missing input": "Matches except missing input",
          "reproduced on a substitute input": "Reproduced on a substitute input",
          "matches except a submitted-file defect": "Matches except a defect of the submitted file",
          "matches except missing input and a submitted-file defect": "Matches except missing input and a defect of the submitted file",
          "not checkable": "Not checked"}
TERM = {"exact": "exact", "exact under comparison rules": "exact-under-rules",
        "matches except missing input": "missing-input", "reproduced on a substitute input": "substitute-input",
        "matches except a submitted-file defect": "submitted-defect", "matches except missing input and a submitted-file defect": "submitted-defect",
        "mismatch": "open", "not checkable": "not-checked"}
LEGEND = {
    "exact": "equal to the submitted dataset, cell for cell",
    "exact under comparison rules": "equal once the study's comparison rules are applied (see above)",
    "matches except missing input": "every difference comes from an input the release lacks; every "
                                    "other cell is reproduced",
    "reproduced on a substitute input": "the release lacks a domain, so the spec reads another release's "
                                        "snapshot of it",
    "matches except a submitted-file defect": "every difference comes from the submitted file itself, which is defective or was not "
                "produced by its released program; the spec follows the program",
    "matches except missing input and a submitted-file defect": "every difference comes from an input the release lacks or from a defect of the "
                "submitted file itself",
    "mismatch": "an open difference, still to fix; its cause is given below",
    "not checkable": "the spec could not be checked; the note says why",
}


def rules_text(compare: dict) -> str:
    """A study's comparison rules (studies.yaml `compare`) in words."""
    tol = float(compare.get("numeric_tolerance", 0))
    num = f"numbers are equal within {tol:g}" if tol else "numbers must be equal"
    txt = ("strings are compared with spaces removed" if compare.get("string_remove_spaces")
           else "strings must be equal, spaces included")
    return f"{num}, {txt}, and submitted cells FDA redacted to `(b)(6)` are not compared"


SCOPE_HEAD = ("Datasets reproduced | Columns reproduced | Cells reproduced | Define-XML elements reproduced | "
              "Define vs data findings")


def scope_row(items: list, reps: list, findings: list, link_prefix: str, anchor: str = "") -> str:
    """The analysis-set cells of one results row: datasets, columns and cells reproduced of those in the
    analysis set, the received define's elements reproduced, and the define-vs-data findings."""
    t = scope_totals(items)
    ds = f"**{t['reproduced']} / {t['in']}** ({pct(t['reproduced'], t['in'])})"
    notes = [f"{t['defect']} match{'es' if t['defect'] == 1 else ''} except a submitted-file defect" if t["defect"] else "",
             f"{t['open']} still differ{'s' if t['open'] == 1 else ''}" if t["open"] else "",
             f"{t['not compared']} not compared cell by cell" if t["not compared"] else "",
             f"{t['out']} outside the analysis set" if t["out"] else "",
             f"{t['unchecked']} not checked" if t["unchecked"] else ""]
    ds += "".join(f"<br>{n}" for n in notes if n)
    cols = f"**{t['cols_rep']:,} / {t['cols_in']:,}** ({pct(t['cols_rep'], t['cols_in'])})"
    if t["cols_nc"]:
        cols += f"<br>{t['cols_nc']:,} not fully compared"
    if t["cols_lack"] + t["cols_out"]:
        cols += f"<br>{t['cols_lack'] + t['cols_out']:,} without input"
    cells = f"**{millions(t['cells_rep'])} / {millions(t['cells_in'])}** ({pct(t['cells_rep'], t['cells_in'])})"
    if t["cells_diff"]:
        cells += f"<br>{t['cells_diff']:,} differ"
    if t["cells_nc"]:
        cells += f"<br>{millions(t['cells_nc'])} not fully compared"
    if not reps:
        return f"{ds} | {cols} | {cells} | No define | No define"
    d = define_totals(reps)
    defects = ", ".join(f"{defect_label(g)} ({d['gaps'][g]:,})" for g in DEFECTS if g in d["gaps"])
    dfn = (f"**{d['reproduced']:,} / {d['scoped']:,}** ({pct(d['reproduced'], d['scoped'])}), "
           f"{d['unexplained']} unexplained" + (f"<br>submitted-define defects: {defects}" if defects else ""))
    nds = len({(f["cut"], f["dataset"]) for f in findings})
    dd = (f"[{len(findings):,} in {nds} dataset{'s' if nds != 1 else ''}]({link_prefix}define-data.md{anchor})"
          if findings else "0")
    return f"{ds} | {cols} | {cells} | {dfn} | {dd}"


def metrics_table(adam: dict, define: dict, link_prefix: str) -> list[str]:
    """One row per cut: the analysis-set results (scope_row)."""
    out = [f"| Study and cut | {SCOPE_HEAD} |", "| --- | --- | --- | --- | --- | --- |"]
    for key, st, cut, rows in cut_rows(adam):
        rep = define["studies"][key].get(cut)
        out.append(f"| [{st['title']} {st['cut_titles'][cut]}]({link_prefix}{PAGES[key]}.md#{cut}) | "
                   + scope_row([(key, cut, r) for r in rows], [rep] if rep else [], dd_findings(key, cut),
                               link_prefix, f"#{key}-{cut}") + " |")
    return out


def spec_cell(r: dict) -> str:
    own = f"[{r['spec_lines']:,} lines]({BLOB}/{r['spec']})"
    cut = Path(r["spec"]).parts[1]
    others = [l for l in r.get("layers", [])[:-1] if "/spec/yamaa/" in l and "/base/" not in l and f"/{cut}/" not in l]
    if others:
        parent = Path(others[-1])
        return f"{own}, layer over `{parent.parts[1]}/{parent.name}`"
    return own


def cells_list(cells: dict) -> str:
    return ", ".join(f"`{c}` {n:,}" for c, n in cells.items())


def adam_notes(r: dict) -> str:
    """The short notes of a dataset's row: how it compared. Reasons for differences are listed
    under the table (difference_groups)."""
    notes = []
    if r.get("within_tolerance_cells"):
        notes.append(f"{r['within_tolerance_cells']:,} cells equal within 1e-10")
    if r.get("space_only_cells"):
        notes.append(f"{r['space_only_cells']:,} cell{'s differ' if r['space_only_cells'] > 1 else ' differs'} "
                     "only by spaces")
    if r.get("redacted_cells"):
        notes.append(f"{r['redacted_cells']:,} cells redacted to `(b)(6)` in the submitted file, not compared ("
                     + cells_list(r["redacted_columns"]) + ")")
    if r.get("adam_inputs"):
        notes.append("reads the submitted " + ", ".join(f"`{d}`" for d in r["adam_inputs"]) + " as input")
    if r.get("carried_columns"):
        notes.append(f"{len(r['carried_columns'])} columns carried from the submitted dataset, not derived")
    if r.get("multiset"):
        notes.append("no unique key: compared as multisets of rows"
                     + (f"; {r['rows_only_out']:,} rows differ, {r.get('rows_paired', 0):,} of them paired "
                        f"within their keys" if r["rows_only_out"] else ""))
        if r.get("rows_unpaired"):
            notes.append(f"{r['rows_unpaired']:,} rows with no partner on the other side")
    if r["verdict"] not in ("exact", "exact under comparison rules", "not checkable"):
        if r["out_rows"] != r["rows"]:
            notes.append(f"{r['out_rows']:,} rows derived, {r['rows']:,} submitted")
        if r.get("missing_columns"):
            notes.append("not derived: " + ", ".join(f"`{c}`" for c in r["missing_columns"][:8])
                         + (" ..." if len(r["missing_columns"]) > 8 else ""))
        if r.get("extra_columns"):
            notes.append("extra: " + ", ".join(f"`{c}`" for c in r["extra_columns"]))
    if r["verdict"] == "not checkable" and r.get("note"):
        notes.append(r["note"])
    return "<br>".join(notes) or "-"


DIFF_GROUPS = {  # heading, glossary anchor, what the group means
    "missing": ("Missing input", "missing-input",
                "The release lacks an input these values are derived from. The spec derives them as the "
                "program does; the listed cells cannot be recovered from the released data."),
    "substitute": ("Reproduced on a substitute input", "substitute-input",
                   "The release lacks a domain, so the spec reads another release's snapshot of it. The "
                   "differences are the subjects whose data differ between the two snapshots."),
    "defect": ("Defects of the submitted file", "submitted-defect",
               "The submitted file itself is defective or was not produced by its released program: a "
               "malformed cell, or rows the released program writes that the file lacks. The spec follows the "
               "program."),
    "carried": ("Columns carried from the submitted dataset", "carried",
                "These columns are copied from the submitted dataset, not derived, and are not counted as "
                "derived."),
    "open": ("Open", "open", "Differences still to fix, with their diagnosed cause."),
    "program": ("Program and submitted file disagree", "program-note",
                "The released program's text and the submitted file disagree. These notes do not change the "
                "verdict."),
    "hold": ("On hold", "hold", "Datasets the owner put on hold."),
}


def difference_groups(rows: list) -> dict[str, list[str]]:
    """Every difference of a cut's datasets and its recorded reason, by kind of reason."""
    g: dict[str, list[str]] = {k: [] for k in DIFF_GROUPS}
    subs: dict[tuple, list[str]] = {}
    for r in rows:
        ds, mi = r["dataset"], r.get("missing_input")
        if mi and mi.get("substitute"):
            sub = mi.get("subjects")
            n = sum((mi.get("cells") or {}).values())
            subs.setdefault((mi["missing"], mi["substitute"]), []).append(
                f"- **{ds}**: {n:,} cells differ, all on subjects whose input differs between the two snapshots"
                + (f"; {sub['exact']:,} of {sub['of']:,} subjects ({pct(sub['exact'], sub['of'])}) reproduce "
                   "exactly" if sub else "") + f". {mi['reason']}")
        elif mi:
            cells = mi.get("cells") or {}
            what = []
            if cells:
                what.append(f"{sum(cells.values()):,} cells differ ({cells_list(cells)})")
            if r.get("missing_columns"):
                what.append(f"{len(r['missing_columns'])} columns are not derived")
            if r["out_rows"] != r["rows"]:
                what.append(f"{r['out_rows']:,} rows derived, {r['rows']:,} submitted")
            done = (" The other columns were not compared cell by cell: the comparison stops when the column "
                    "sets differ." if (r.get("missing_columns") or r.get("extra_columns"))
                    and not r.get("common_columns_compared") else
                    "" if "every other cell" in mi["reason"].lower() else
                    " Every other cell is reproduced." if r["out_rows"] == r["rows"] else
                    " Every other cell of the rows derived is reproduced.")
            g["missing"].append(f"- **{ds}**: {'; '.join(what) or 'differs'}. *Missing:* {mi['missing']}. "
                                f"{mi['reason']}{done}")
        sd = r.get("submitted_defect")
        if sd:
            cells = sd.get("cells") or {}
            n = sum(cells.values())
            what = f"{n:,} cell{'s differ' if n != 1 else ' differs'} ({cells_list(cells)})" if cells else (
                f"{r['out_rows']:,} rows derived, {r['rows']:,} submitted" if r["out_rows"] != r["rows"]
                else "differs")
            g["defect"].append(f"- **{ds}**: {what}. *Defect:* {sd['defect']}. {sd['reason']}")
        for k in r.get("reasons", []):
            cells = f" ({cells_list(k['cells'])})" if k["cells"] else ""
            if k["kind"] == "a submitted-file defect":
                g["defect"].append(f"- **{ds}**{cells}: {k['reason']} The dataset also has an open "
                                   "difference (below).")
            elif k["kind"] == "missing input":
                g["missing"].append(f"- **{ds}**{cells}: {k['reason']} The dataset also has an open "
                                    "difference (below).")
            else:
                g["open"].append(f"- **{ds}**{cells}: {k['reason']}")
        if r["verdict"] == "mismatch":
            cols = r.get("mismatched_columns", {})
            left = {c: cols[c] for c in r.get("unexplained_columns", [])} if r.get("reasons") else cols
            if left or not r.get("reasons"):
                g["open"].append(f"- **{ds}**: no recorded reason yet"
                                 + (f" ({cells_list(left)})" if left else
                                    f" ({r['out_rows']:,} rows derived, {r['rows']:,} submitted)") + ".")
        if r.get("carried_columns"):
            g["carried"].append(f"- **{ds}**: {len(r['carried_columns'])} columns: "
                                + ", ".join(f"`{c}`" for c in r["carried_columns"]) + ".")
        for n in r.get("program_notes", []):
            g["program"].append(f"- **{ds}**: {n}")
        if r.get("hold"):
            g["hold"].append(f"- **{ds}** ({r['hold']['decided']}): {r['hold']['reason']}")
    for (missing, substitute), items in subs.items():
        g["substitute"] += [f"*Missing:* {missing}. *Read instead:* {substitute}.", ""] + items
    return {k: v for k, v in g.items() if v}


def cut_counts(rows: list) -> dict:
    a = adam_summary(rows)
    a["open"] = a["checked"] - a["exact"] - a["accepted"] - a["substituted"] - a["defect"]
    a["unchecked"] = a["specs"] - a["checked"]
    return a


# ---------------------------------------------------------------- analysis set
@functools.lru_cache(maxsize=None)
def differences() -> dict:
    return yaml.safe_load((ROOT / "data/differences.yaml").read_text())


@functools.lru_cache(maxsize=None)
def define_data() -> dict:
    """data/reproduction/define_data.json (scripts/define/check_define_data.py): the received defines
    checked against the submitted datasets."""
    p = ROOT / "data/reproduction/define_data.json"
    return json.loads(p.read_text()) if p.exists() else {"meta": {"collected": "never"}, "checks": {}, "cuts": {}}


def entries(kind: str, study: str, cut: str, ds: str) -> list[dict]:
    return [e for e in differences().get(kind) or [] if e["study"] == study and e["dataset"] == ds and cut in e["cuts"]]


def input_scope(study: str, cut: str, r: dict) -> dict:
    """What of one submitted dataset is in the analysis set: the part the release holds the input for.

    Fixed by the absent inputs recorded in data/differences.yaml, not by the comparison: a dataset whose
    rows are built from a domain the release lacks (`substitute` with `rows_differ`) is outside; a column
    is outside when its derivation reads an input the release does not hold (`columns`, `cells`) or it is
    carried from the submitted dataset; a submitted row is outside when the absent input decides whether
    it exists (`rows_differ`) and no derived row matches it. Submitted cells FDA redacted to (b)(6) have
    no value to compare with and leave the cells.

    Within the set a cell counts as reproduced only when the comparison accounted for it. Older reports
    did not when the column sets differ (scripts/verify_compare.py stopped before the rows and cells), nor
    for a dataset that still differs and was compared on keys in any partition (only the net row
    difference was recorded, not the keys on one side only). Such a dataset is `compared: False`
    and none of its columns or cells is counted as reproduced. `open` and `defect` count the differing
    cells and the submitted rows yamaa does not write, still to fix or from a defect of the file."""
    s = {"rows": r.get("rows", 0), "cols": r.get("cols", 0), "cells": r.get("cells", 0), "checked": True,
         "in": True, "compared": True, "lack_cols": [], "lack_rows": 0, "redacted": 0, "open_cols": [],
         "defect_cols": [], "open_cells": 0, "defect_cells": 0, "open_rows": 0, "defect_rows": 0,
         "status": "reproduced"}
    if r["verdict"] == "not checkable":
        s.update(checked=False, status="not checked")
        return s
    mi = entries("missing_input", study, cut, r["dataset"])
    if any(e.get("substitute") and e.get("rows_differ") for e in mi):
        s.update(**{"in": False}, status="outside")
        return s
    sd = entries("submitted_defect", study, cut, r["dataset"])
    lack = set(r.get("carried_columns") or [])
    for e in mi:
        lack |= set(e.get("columns") or []) & set(r.get("missing_columns") or [])
        lack |= set(e.get("cells") or {})
    # Submitted rows with no derived counterpart: as recorded (multiset comparisons), at least the net count.
    unpaired_x = max(r.get("rows_only_expected", 0) - r.get("rows_paired", 0), r["rows"] - r["out_rows"], 0)
    if any(e.get("rows_differ") for e in mi):
        s["lack_rows"] = unpaired_x
    elif any(e.get("rows_differ") for e in sd):
        s["defect_rows"] = unpaired_x
    else:
        s["open_rows"] = unpaired_x
    defect = set().union(*(set(e.get("cells") or {}) for e in sd))
    mm = {c: n for c, n in (r.get("mismatched_columns") or {}).items() if c not in lack}
    s["lack_cols"] = sorted(lack)
    s["defect_cols"] = sorted(c for c in mm if c in defect)
    s["open_cols"] = sorted(c for c in mm if c not in defect)
    s["defect_cells"] = sum(mm[c] for c in s["defect_cols"])
    s["open_cells"] = sum(mm[c] for c in s["open_cols"])
    s["redacted"] = sum(n for c, n in (r.get("redacted_columns") or {}).items() if c not in lack)
    s["status"] = ("open" if r["verdict"] == "mismatch" else
                   "defect" if r["verdict"] in RESULT_DEFECT else "reproduced")
    # Reports written before verify_compare.py compared the common columns and recorded keyed rows on one
    # side only lack `common_columns_compared` and `rows_recorded` (collect_results.py).
    keyed = not r.get("multiset") or r.get("partitions", 1) > 1
    cols_differ = (r.get("missing_columns") or r.get("extra_columns")) and not r.get("common_columns_compared")
    if cols_differ or (s["status"] == "open" and keyed and not r.get("rows_recorded")):
        s["compared"] = False
        if s["status"] == "reproduced":
            s["status"] = "not compared"
    return s


# ---------------------------------------------------------------- every column of a dataset
COLUMN_STATUS = {  # status -> label, in the order the review page lists them
    "differs": "Differs, cause to fix",
    "defect": "Submitted-file defect",
    "rows": "Rows differ",
    "not compared": "Not compared",
    "reproduced": "Reproduced",
    "absent": "Absent input",
    "carried": "Carried, not derived",
    "outside": "Dataset outside the set",
}


@functools.lru_cache(maxsize=None)
def submitted_columns() -> dict:
    """{study: {cut: {DATASET: [names]}}}: the submitted files' columns (scripts/site/inventory_columns.py)."""
    p = ROOT / "data/reproduction/columns.json"
    return json.loads(p.read_text())["studies"] if p.exists() else {}


@functools.lru_cache(maxsize=None)
def defined_columns(spec: Path) -> dict[str, int]:
    """{column: line} of the top-level `columns:` list of one spec file, read as text for the line numbers."""
    out: dict[str, int] = {}
    inside, indent = False, None
    for i, line in enumerate(spec.read_text().splitlines(), 1):
        if line.startswith("columns:"):
            inside = True
            continue
        if inside and line and line[0] not in " #-":
            break
        m = re.match(r"^( *)- name: *['\"]?([^'\"\s#]+)", line) if inside else None
        if m and (indent is None or len(m.group(1)) == indent):
            indent = len(m.group(1))
            out[m.group(2)] = i
    return out


def column_rows(key: str, cut: str, r: dict) -> tuple[list[dict], list[str]]:
    """Every submitted column of one dataset, in the file's order, with its status (COLUMN_STATUS), the cells
    that differ, the submitted cells FDA redacted, where the spec derives it (an index into `layers` and a
    line) and the recorded reason (an index into the returned notes). Raises when the names and the results
    disagree."""
    names = (submitted_columns().get(key, {}).get(cut, {}) or {}).get(r["dataset"])
    if names is None:
        return [], []
    s = input_scope(key, cut, r)
    where: dict[str, tuple[int, int]] = {}
    for i, layer in enumerate(r.get("layers") or []):
        for c, line in defined_columns(ROOT / layer).items():
            where[c] = (i, line)
    notes: list[str] = []

    def note(text: str | None) -> int | None:
        if not text:
            return None
        text = " ".join(text.split())
        if text not in notes:
            notes.append(text)
        return notes.index(text)

    mi = entries("missing_input", key, cut, r["dataset"])
    sd = entries("submitted_defect", key, cut, r["dataset"])

    def absent(c: str) -> str | None:
        e = next((e for e in mi if c in (e.get("columns") or []) or c in (e.get("cells") or {})), None)
        return f"Absent input: {e['missing']}" if e else None

    carried = set(r.get("carried_columns") or [])
    not_written = set(r.get("missing_columns") or [])
    rows_off = s["open_rows"] + s["defect_rows"]
    out = []
    for c in names:
        cells = (r.get("mismatched_columns") or {}).get(c, 0)
        if not s["in"]:
            e = next((e for e in mi if e.get("substitute")), {})
            status, why = "outside", f"The release lacks {e.get('missing', 'an input')}; the spec reads " \
                                     f"{e.get('substitute', 'another release')} instead."
        elif c in carried:
            status, why = "carried", absent(c)
        elif c in s["lack_cols"]:
            status, why = "absent", absent(c)
        elif c in s["defect_cols"]:
            status, why = "defect", next((f"Defect of the submitted file: {e['defect']}" for e in sd), None)
        elif c in s["open_cols"]:
            reason = next((x["reason"] for x in r.get("reasons") or [] if c in (x.get("cells") or {})), None)
            status, why = "differs", reason or "No recorded reason yet."
        elif c in not_written:
            raise ValueError(f"{key}/{cut}/{r['dataset']}: {c} is not written and has no absent input")
        elif not s["compared"]:
            status, why = "not compared", None
        elif rows_off:
            status, why = "rows", (f"{rows_off:,} submitted rows have no derived counterpart, so no column of "
                                   "this dataset counts as fully reproduced.")
        else:
            status, why = "reproduced", None
        layer, line = where.get(c, (None, None)) if c not in not_written else (None, None)
        out.append({"name": c, "status": status, "cells": cells,
                    "redacted": (r.get("redacted_columns") or {}).get(c, 0), "layer": layer, "line": line,
                    "note": note(why)})
    return out, notes


def scope_totals(items) -> dict:
    """Sum input_scope over (study, cut, row) triples. Within the analysis set (`cols_in`, `cells_in`),
    every column and cell is reproduced (`*_rep`), differs (`cells_diff`) or was not fully compared
    (`*_nc`)."""
    t = {k: 0 for k in ("datasets", "out", "unchecked", "in", "complete", "partial", "reproduced",
                        "reproduced_complete", "defect", "open", "not compared", "not_compared_any", "cols",
                        "cols_out", "cols_lack", "carried", "cols_in", "cols_rep", "cols_nc", "cells",
                        "cells_out", "cells_lack", "redacted", "cells_in", "cells_rep", "cells_nc",
                        "cells_diff", "rows_lack")}
    for study, cut, r in items:
        s = input_scope(study, cut, r)
        t["datasets"] += 1
        t["cols"] += s["cols"]
        t["cells"] += s["cells"]
        if not s["checked"]:
            t["unchecked"] += 1
            continue
        if not s["in"]:
            t["out"] += 1
            t["cols_out"] += s["cols"]
            t["cells_out"] += s["cells"]
            continue
        t["in"] += 1
        partial = bool(s["lack_cols"] or s["lack_rows"])
        t["partial" if partial else "complete"] += 1
        t[s["status"]] += 1
        if s["status"] == "reproduced" and not partial:
            t["reproduced_complete"] += 1
        cols_in = s["cols"] - len(s["lack_cols"])
        rows_in = s["rows"] - s["lack_rows"]
        cells_in = rows_in * cols_in - s["redacted"]
        t["carried"] += len(set(r.get("carried_columns") or []) & set(s["lack_cols"]))
        t["cols_lack"] += len(s["lack_cols"])
        t["rows_lack"] += s["lack_rows"]
        t["cols_in"] += cols_in
        t["cells_lack"] += s["cells"] - rows_in * cols_in
        t["redacted"] += s["redacted"]
        t["cells_in"] += cells_in
        if not s["compared"]:
            t["not_compared_any"] += 1
            t["cols_nc"] += cols_in
            t["cells_nc"] += cells_in
            continue
        missing_rows = s["open_rows"] + s["defect_rows"]
        diff = s["open_cells"] + s["defect_cells"] + missing_rows * cols_in
        # A submitted row yamaa does not write counts against every column it holds.
        t["cols_rep"] += 0 if missing_rows else cols_in - len(s["open_cols"]) - len(s["defect_cols"])
        t["cells_diff"] += diff
        t["cells_rep"] += cells_in - diff
    return t


def dd_findings(study: str, cut: str | None = None, artifacts: bool = False) -> list[dict]:
    """The define-vs-data findings of a study (or one cut): release artifacts only when asked."""
    out = []
    for key, c in define_data()["cuts"].items():
        k_study, k_cut = key.split("/", 1)
        if k_study == study and cut in (None, k_cut):
            out += [dict(f, cut=k_cut) for f in c["findings"] if bool(f.get("artifact")) == artifacts]
    return out


def ratio(a: int, b: int, fmt=lambda n: f"{n:,}") -> str:
    return f"{fmt(a)} / {fmt(b)} ({pct(a, b)})"


def define_brief(d: dict | None) -> str:
    """One cell: how much of a cut's received define is reproduced."""
    if d is None:
        return "No define in this deliverable"
    s = define_summary(d)
    scoped = s["received"] - s["nospec"]
    out = f"{s['identical'] + s['gap_only']:,} / {scoped:,} elements, {s['unexplained']} unexplained"
    if s["nospec_datasets"]:
        out += f"; no spec yet: {', '.join(s['nospec_datasets'])}"
    return out


def glossary_link(prefix: str, anchor: str, text: str) -> str:
    return f"[{text}]({prefix}glossary.md#{anchor})"


def study_page(key: str, st: dict, define: dict, meta: dict) -> str:
    info = studies_info()[key]
    g = "../"  # the glossary, from findings/
    subst = any(r["verdict"] == "reproduced on a substitute input" for rows in st["cuts"].values() for r in rows)
    defect = any(r["verdict"] in (RESULT_DEFECT) for rows in st["cuts"].values() for r in rows)
    L = [f"# {st['title']}", "",
         f"**{st['sponsor']}**, {info['product']}. {' '.join(info.get('about', '').split())}", "",
         f"Specs: [`phmpt/{st['dir']}`]({TREE}/{st['dir']}) - yamaa `{meta['yamaa_commit']}` - "
         f"results collected {meta['collected']} - terms: [glossary]({g}glossary.md)", ""]
    L += ["Submitted data, programs and defines are not published here. To rerun this study from PHMPT, "
              f"follow {runner()}: `sh phmpt/reproduce.sh setup`, then `sh phmpt/reproduce.sh {key}`.", ""]
    L += [f"**How datasets are compared.** yamaa's output is matched to the submitted dataset row by row on the "
          f"dataset's keys and compared cell by cell. In this study {rules_text(info['compare'])} "
          f"({glossary_link(g, 'comparison-rules', 'comparison rules')}).", "",
          "## Results at a glance", "",
          "| Cut | Datasets with specs | Exact | Match except missing input | "
          + ("On a substitute input | " if subst else "") + ("Submitted-file defect | " if defect else "")
          + "Open | Define-XML |",
          "| --- | ---: | ---: | ---: | " + ("---: | " if subst else "") + ("---: | " if defect else "")
          + "---: | --- |"]
    for cut, rows in st["cuts"].items():
        a = cut_counts(rows)
        L.append(f"| [{st['cut_titles'][cut]}](#{cut}) | {a['specs']} | {a['exact']} | {a['accepted']} | "
                 + (f"{a['substituted']} | " if subst else "")
                 + (f"{a['defect']} | " if defect else "")
                 + f"{a['open']}" + (f" ({a['unchecked']} not checked)" if a["unchecked"] else "") + " | "
                 f"{define_brief(define['studies'][key].get(cut))} |")
    L += ["", "**Exact** counts datasets equal to the submitted one, strictly or under the comparison rules. "
          "**Open** counts datasets that still differ. Define-XML counts the received elements of datasets with "
          "a spec that are reproduced, exactly or apart from a "
          f"{glossary_link(g, 'define-defect', 'defect of the submitted define')}; *unexplained* would be any "
          "other difference.", ""]
    for cut, rows in st["cuts"].items():
        a = cut_counts(rows)
        c = info["cuts"][cut]
        d = define["studies"][key].get(cut)
        ds = define_summary(d) if d else None
        lead = (f"{a['exact']} of {a['checked']} datasets reproduce the submitted dataset "
                f"({millions(a['cells_exact'])} of {millions(a['cells'])} cells)")
        more = []
        if a["accepted"]:
            more.append(f"{a['accepted']} more match except missing input")
        if a["substituted"]:
            more.append(f"{a['substituted']} {'is' if a['substituted'] == 1 else 'are'} reproduced on a "
                        "substitute input")
        if a["defect"]:
            more.append(f"{a['defect']} more match{'es' if a['defect'] == 1 else ''} except a defect of the "
                        "submitted file")
        if a["open"]:
            more.append(f"{a['open']} still differ{'s' if a['open'] == 1 else ''}")
        if a["unchecked"]:
            more.append(f"{a['unchecked']} not checked")
        lead += (": " + ", ".join(more) if more else "") + "."
        how = f"{a['specs']} specs, {a['lines']:,} lines"
        if c.get("over"):
            how += (f"; where a dataset's derivation is unchanged, its spec is a layer over the "
                    f"[{st['cut_titles'][c['over']]}](#{c['over']}) spec")
        if c.get("sdtm_from"):
            how += (f"; this supplement resends only some domains and reads the others from "
                    f"[{st['cut_titles'][c['sdtm_from']]}](#{c['sdtm_from']})")
        L += [f"## {st['cut_titles'][cut]} {{#{cut}}}", "", lead + f" {how[0].upper()}{how[1:]}.", "",
              "### ADaM datasets", "",
              "| Dataset | Rows x columns | Result | Spec | Notes |", "| --- | --- | --- | --- | --- |"]
        for r in rows:
            if r["verdict"] == "not checkable":
                L.append(f"| {r['dataset']} | - | Not checked | {spec_cell(r)} | {adam_notes(r)} |")
                continue
            result = RESULT.get(r["verdict"]) or (
                f"{sum(r['mismatched_columns'].values()):,} cells differ"
                + (f", {r['rows_unpaired']:,} rows unpaired" if r.get("rows_unpaired") else "")
                if r["mismatched_columns"] else
                f"{r['rows_unpaired']:,} rows differ" if r.get("multiset") else "Shape differs")
            L.append(f"| {r['dataset']} | {r['rows']:,} x {r['cols']} | {result} | {spec_cell(r)} | "
                     f"{adam_notes(r)} |")
        seen = [v for v in LEGEND if any(r["verdict"] == v for r in rows)]
        L += ["", "Result: " + "; ".join(
            f"{glossary_link(g, TERM[v], RESULT.get(v, 'N cells differ'))}, {LEGEND[v]}" for v in seen) + ".", "",
              "### Differences and their reasons", ""]
        groups = difference_groups(rows)
        if not groups:
            L += ["None. Every dataset of this cut reproduces the submitted dataset, and no column is carried "
                  "from it.", ""]
        for k, items in groups.items():
            head, anchor, what = DIFF_GROUPS[k]
            L += [f"**{head}** ({glossary_link(g, anchor, 'glossary')}). {what}", "", *items, ""]
        if ds is None:
            L += ["### Define-XML", "", "This deliverable was submitted without a define.", ""]
            continue
        scoped = ds["received"] - ds["nospec"]
        layer = glossary_link(g, "reproduced-mode-layer", "reproduced-mode layer")
        source = (f"Composed from the cut's specs and its {layer} ({d['wrappers']} files, "
                  f"{d['wrapper_lines']:,} lines), which `scripts/define/transcribe_define.py` writes from the "
                  "received define. The layer holds the received define's text, so it is not published; "
                  "`reproduce.py define --transcribe` writes it again from PHMPT.")
        L += ["### Define-XML", "",
              f"{source} The composed define is compared element by element with the received "
              f"`{Path(d['received']).name}`. Of the {scoped:,} received elements "
              f"that belong to datasets with a spec, **{ds['identical']:,}** are identical and "
              f"**{ds['gap_only']:,}** differ only by the defects of the submitted define below; "
              f"{'none' if ds['unexplained'] == 0 else ds['unexplained']} differ otherwise.", ""]
        if ds["nospec_datasets"]:
            L += [f"The received define also describes {', '.join(ds['nospec_datasets'])}, which "
                  f"{'has' if len(ds['nospec_datasets']) == 1 else 'have'} "
                  f"{glossary_link(g, 'no-spec', 'no spec yet')} ({ds['nospec']:,} elements, not compared).", ""]
        L += ["| Element class | Received | Identical | Differ only by submitted-define defects | No spec yet | Other |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for cls, label in CLASS_LABELS.items():
            c = d["classes"].get(cls)
            if not c:
                continue
            nos = d.get("no_spec_elements", {}).get(cls, 0)
            other = max(c["submitted"] - c["match"] - c.get("gap_only", 0) - nos, 0)
            L.append(f"| {label} | {c['submitted']:,} | {c['match']:,} | {c.get('gap_only', 0):,} | {nos:,} | {other:,} |")
        if ds["gaps"]:
            L += ["", "| Defect of the submitted define | Differences | Owner decision |", "| --- | ---: | --- |"]
            for gap, (label, text, n) in DEFECTS.items():
                if gap in ds["gaps"]:
                    L.append(f"| {glossary_link(g, 'define-defect', label)} | {ds['gaps'][gap]:,} | {issue(n)} |")
            L += ["", "Differences count attributes or references, not elements: one codelist of ten items "
                  "differs ten times."]
        L.append("")
    return "\n".join(L)


def findings_index(adam: dict, define: dict) -> str:
    meta = adam["meta"]
    L = ["# Reproduction findings", "",
         f"yamaa `{meta['yamaa_commit']}` - collected {meta['collected']} - terms: [glossary](../glossary.md)", "",
         "Two questions, answered separately for every cut that has specs:", "",
         "- **ADaM datasets.** Does the yamaa spec, run on the submitted SDTM, reproduce the submitted "
         "ADaM dataset cell for cell? (`scripts/reproduce.py verify`, with `scripts/verify_compare.py`: rows keyed, "
         "numeric tolerance 1e-10, strings compared after removing spaces, and submitted cells FDA "
         "redacted to `(b)(6)` under FOIA exemption 6 not compared but counted.)",
         "- **Define-XML.** Does the define yamaa composes from those same specs, with a reproduced-mode "
         "metadata layer, match the received define element by element? "
         "(`scripts/define/compare_define.py`)", ""]
    L += metrics_table(adam, define, "")
    disagree = [(st, cut, r) for key, st, cut, rows in cut_rows(adam) for r in rows if r.get("program_notes")]
    if disagree:
        L += ["", "## Where the program and the submitted file disagree", "",
              "Each released program was ported as written. In these datasets the program's text and the "
              "submitted file disagree, which means the file was not produced by the program as released, "
              "or the program's code contradicts its own stated intent (the spec follows the intent):", "",
              "| Study and cut | Dataset | What disagrees |", "| --- | --- | --- |"]
        for st, cut, r in disagree:
            for n in r["program_notes"]:
                L.append(f"| {st['title']} {st['cut_titles'][cut]} | {r['dataset']} | {n} |")
    L += ["", "## How the specs are organised", "",
          "Each cut's spec is the executable reproduction. A later cut of a study is a **layer** over the "
          "earlier cut's spec (`parent:`) holding only what that cut changes; "
          "`scripts/specs/inherit_cut.py` writes a layer only when yamaa resolves it to the same "
          "specification as the standalone file it replaces.", "",
          "| Cut | Specs | Layers over another cut | Spec lines |", "| --- | ---: | ---: | ---: |"]
    for key, st, cut, rows in cut_rows(adam):
        n_layer = sum(1 for r in rows if any("/spec/yamaa/" in l and "/base/" not in l and f"/{cut}/" not in l
                                             for l in r.get("layers", [])[:-1]))
        L.append(f"| {st['title']} {cut} | {len(rows)} | {n_layer} | {sum(r['spec_lines'] for r in rows):,} |")
    L += ["", "Three tiers of inheritance keep each statement in one place:", "",
          "1. **Study base** (`<study>/spec/yamaa/base/`): the project settings, submission metadata and "
          "the columns every dataset of the study carries; every spec's chain starts there.",
          "2. **Earlier cut** (`parent: ../../../<cut>/spec/yamaa/<dataset>.yaml`): a later cut's spec "
          "states only what the cut changes.",
          "3. **Define layer** (`<cut>/spec/define/`): reproduced-mode metadata over the cut's spec; a "
          "later cut whose wrapper or codelists are identical points to the earlier cut's file.", "",
          "A yamaa layer can add or replace members but cannot remove a column or intermediate its "
          "parent declares, so a later spec that drops one stays standalone over the study base. "
          "These are recorded, with the reason, in `studies.yaml` (`standalone`):", "",
          "| Cut | Dataset | Why it is not a layer over the earlier cut |", "| --- | --- | --- |"]
    info = yaml.safe_load((ROOT / "studies.yaml").read_text())
    for key, st in info.items():
        for cut, c in st["cuts"].items():
            for ds, why in (c.get("standalone") or {}).items():
                L.append(f"| {st['title']} {cut} | {ds.upper()} | {why} |")
    L += ["", "**Helper specs.** Where the sponsor's program builds an intermediate table in several "
          "passes, a helper spec in `spec/yamaa/helper/` builds it and the dataset spec reads its output "
          "through a schema link (`<work-dir>/<file>`, `schema:`); `scripts/reproduce.py verify` runs the "
          "helper first. C4591001 ADSYMPT reads the visit-collapse walk "
          "(`adsympt_visits.yaml`, a calculated-history group over its own rows, and `adsympt_vismap.yaml`), "
          "and C4591001 ADSL reads the infection-evidence events behind EV1MD2FL (`adsl_ev1.yaml`). A "
          "later cut's spec that inherits the dataset spec inherits its helpers too: they run on that "
          "cut's data.", ""]
    L += ["", "Each cut's `spec/define/` folder holds the define layer: one reproduced-mode wrapper per dataset "
          "whose `parent` is the cut's spec, stating only the metadata the received define declares "
          "differently or that the spec does not carry (codelists, value-level metadata, received OIDs "
          "and orders, define-only columns). `scripts/define/transcribe_define.py` writes it from the "
          "received define; `scripts/define/compose_define.py` composes the cut's `define-adam-yamaa.xml`.", ""]
    return "\n".join(L)


def coverage_page(module5: dict, adam: dict) -> str:
    worked = {"mrna1273-p201": "mrna-1273-p201", "mrna1273-p301": "mrna-1273-p301", "bnt162-01": "bnt162-01",
              "c4591001": "c4591001"}
    L = ["# Module 5 coverage", "",
         f"What PHMPT's Full Productions release for each study, read from the {module5['zips']} zip "
         "archives' directories (`scripts/site/inventory_module5.py`, collected "
         f"{module5['collected']}), and what this repo reproduces.", "",
         "| Study | Sponsor | Module 5 holds | Status |",
         "| --- | --- | --- | --- |"]
    for sid, s in module5["studies"].items():
        f = s["files"]
        docs = f.get("pdf", 0) + f.get("other", 0)
        if sid in worked:
            st = adam["studies"][worked[sid]]
            cuts = ", ".join(st["cuts"])
            status = f"[Specs for {cuts}](findings/{PAGES[worked[sid]]}.md)"
        elif f.get("adam") or f.get("sdtm"):
            status = "Data released, no specs yet"
        else:
            status = "Documents only: nothing to reproduce"
        name = f"[{sid}]({TREE}/{worked[sid]})" if sid in worked else sid
        parts = [(f.get("adam", 0), "ADaM"), (f.get("sdtm", 0), "SDTM"), (f.get("define", 0), "defines"),
                 (f.get("program", 0), "programs"), (docs, "documents")]
        held = " - ".join(f"{n:,} {k}" for n, k in parts if n) or "nothing"
        L.append(f"| {name} | {s['sponsor']} | {held} | {status} |")
    L += ["", "Only four studies have analysis data in Module 5. For the other eighteen, PHMPT released "
          "protocols, consent forms and report sections, with no SDTM or ADaM datasets and no "
          "define.xml, so there is nothing for a specification to reproduce.", "",
          "## Cuts with data but no specs", ""]
    info = studies_info()
    data_only = [(info[k]["title"], c, sum(1 for r in sources() if r["study"] == k and r["cut"] == c))
                 for k in adam["studies"] for c in info[k].get("data_cuts", [])]
    if data_only:
        L += ["These released folders hold submitted data but no specs yet: "
              + "; ".join(f"{t} `{c}` ({n} files)" for t, c, n in data_only) + ".", ""]
    else:
        L += ["Every released folder with data has specs.", ""]
    return "\n".join(L)


def public_profile(docs_dir: Path) -> None:
    """Write every page into docs_dir (docs/phmpt/)."""
    adam = json.loads((ROOT / "data/reproduction/adam.json").read_text())
    define = json.loads((ROOT / "data/reproduction/define.json").read_text())
    module5 = json.loads((ROOT / "data/reproduction/module5.json").read_text())
    pages = {"index.md": index_page(adam, define, module5),
             "results.md": results_page(adam, define, module5),
             "glossary.md": glossary_page(),
             "findings/index.md": findings_index(adam, define),
             "findings/inputs.md": inputs_page(adam),
             "findings/define-data.md": define_data_page(adam),
             "coverage.md": coverage_page(module5, adam)}
    for key, st in adam["studies"].items():
        pages[f"findings/{PAGES[key]}.md"] = study_page(key, st, define, adam["meta"])
    (docs_dir / "findings").mkdir(parents=True, exist_ok=True)
    for old in (docs_dir / "findings").glob("*.md"):
        old.unlink()
    for name, text in pages.items():
        (docs_dir / name).write_text(text.translate(ASCII))


def all_rows(adam: dict) -> list[tuple[str, dict, str, dict]]:
    return [(key, st, cut, r) for key, st, cut, rows in cut_rows(adam) for r in rows]


def define_totals(reps: list) -> dict:
    out = {"received": 0, "identical": 0, "gap_only": 0, "nospec": 0, "unexplained": 0, "gaps": {}, "nospec_datasets": []}
    for rep in reps:
        s = define_summary(rep)
        for k in ("received", "identical", "gap_only", "nospec", "unexplained"):
            out[k] += s[k]
        for gap, n in s["gaps"].items():
            out["gaps"][gap] = out["gaps"].get(gap, 0) + n
        out["nospec_datasets"] += s["nospec_datasets"]
    out["scoped"] = out["received"] - out["nospec"]
    out["reproduced"] = out["identical"] + out["gap_only"]
    return out


DD_LABEL = {"mandatory": "mandatory variables with missing values", "key": "key sets that repeat",
            "type": "data types", "length": "lengths", "variable": "variables in only one of the two",
            "dataset label": "dataset labels", "codelist": "variables with values outside their codelist",
            "dataset": "datasets in only one of the two", "label": "variable labels"}
M5 = {"mrna-1273-p201": "mrna1273-p201", "mrna-1273-p301": "mrna1273-p301", "bnt162-01": "bnt162-01",
      "c4591001": "c4591001"}  # adam.json study -> module5.json study


def scope_items(adam: dict) -> list[tuple[str, str, dict]]:
    return [(key, cut, r) for key, st, cut, rows in cut_rows(adam) for r in rows]


def dd_summary(adam: dict) -> tuple[list, list, int]:
    """(findings, release artifacts, datasets checked) over every cut with a define."""
    f = [x for k in adam["studies"] for x in dd_findings(k)]
    art = [x for k in adam["studies"] for x in dd_findings(k, artifacts=True)]
    # The datasets the defines or the releases hold: those checked, and those in only one of the two.
    checked = sum(len(c["datasets"]) + sum(1 for x in c["findings"] if x["check"] == "dataset")
                  for c in define_data()["cuts"].values())
    return f, art, checked


def key_findings(adam: dict, define: dict, module5: dict) -> list[str]:
    items = scope_items(adam)
    t = scope_totals(items)
    with_data = sum(1 for s in module5["studies"].values() if s["files"].get("adam"))
    info = studies_info()
    strict_studies = [info[k]["title"] for k in adam["studies"]
                      if not float(info[k]["compare"].get("numeric_tolerance", 0))
                      and not info[k]["compare"].get("string_remove_spaces")]
    L = [f"- **Analysis set: {t['in']} of {t['datasets']} ADaM datasets, {t['cols_in']:,} of {t['cols']:,} columns and "
         f"{millions(t['cells_in'])} of {millions(t['cells'])} cells**, in the {with_data} of the "
         f"{len(module5['studies'])} PHMPT studies that released ADaM datasets. The analysis set is the part of the "
         "release that holds every input its values are derived from; it is fixed from the release, before any "
         "comparison ([analysis set](#analysis-set)). What it leaves out is listed with the absent input "
         "([inputs outside the analysis set](findings/inputs.md)).",
         f"- **Fully reproduced: {t['reproduced']} of {t['in']} datasets, {t['cols_rep']:,} of {t['cols_in']:,} columns "
         f"and {millions(t['cells_rep'])} of {millions(t['cells_in'])} cells**, equal to the submitted values under the "
         "comparison rules (numbers within 1e-10, spaces ignored"
         + (f"; {', '.join(strict_studies)} is compared strictly" if strict_studies else "") + "). "
         f"{t['reproduced_complete']} of these datasets hold every input; the other "
         f"{t['reproduced'] - t['reproduced_complete']} reproduce every value that has one. Of the rest, "
         f"{t['cells_diff']:,} cell{'s differ' if t['cells_diff'] != 1 else ' differs'}"
         + (f", and {t['cols_nc']:,} columns and {millions(t['cells_nc'])} cells were not fully compared (next point)"
            if t["cols_nc"] or t["cells_nc"] else "") + "."]
    rows = all_rows(adam)
    uncompared = [(key, st, cut, r) for key, st, cut, r in rows if input_scope(key, cut, r)["status"] == "not compared"]
    defects = [(key, st, cut, r) for key, st, cut, r in rows if input_scope(key, cut, r)["status"] == "defect"]
    opened = [(key, st, cut, r) for key, st, cut, r in rows if input_scope(key, cut, r)["status"] == "open"]
    link = lambda key, st, cut, r: f"[{st['title']} `{cut}` {r['dataset']}](findings/{PAGES[key]}.md#{cut})"
    if uncompared or defects or opened:
        parts = []
        if uncompared:
            parts.append(f"{len(uncompared)} not compared cell by cell, because the release cannot supply some of "
                         "their columns and `scripts/verify_compare.py` stops when the column sets differ ("
                         + ", ".join(link(*x) for x in uncompared) + ")")
        if defects:
            parts.append(f"{len(defects)} only where the submitted file is defective ("
                         + ", ".join(link(*x) for x in defects) + ")")
        if opened:
            noreason = [f"`{c}` ({st['title']} `{cut}` {r['dataset']})" for key, st, cut, r in opened
                        for c in r.get("unexplained_columns") or ([] if r.get("reasons") else r["mismatched_columns"])]
            parts.append(f"{len(opened)} with a diagnosed cause still to fix (" + ", ".join(link(*x) for x in opened)
                         + ")" + (f"; {len(noreason)} differing column{'s have' if len(noreason) > 1 else ' has'} "
                                  f"no recorded reason yet: {', '.join(noreason)}" if noreason else ""))
        L.append(f"- **{len(uncompared) + len(defects) + len(opened)} datasets in the analysis set are not counted as "
                 "fully reproduced:** " + "; ".join(parts) + "."
                 + (" The datasets that still differ were compared on keys, which did not record the rows on one "
                    "side only, so none of their cells is counted as reproduced either."
                    if any(not input_scope(key, cut, r)["compared"] for key, st, cut, r in opened) else ""))
    reps = [rep for key in adam["studies"] for rep in define["studies"][key].values()]
    d = define_totals(reps)
    gaps = ", ".join(f"{d['gaps'][g]:,} {defect_label(g)}" for g in DEFECTS if g in d["gaps"]) or "none"
    nospec = [f"{st['title']} `{cut}` {ds}" for key, st in adam["studies"].items()
              for cut, rep in define["studies"][key].items() for ds in rep.get("datasets_without_spec", [])]
    L.append(f"- **Define-XML: {d['reproduced']:,} of {d['scoped']:,} received elements reproduced** in the "
             f"{len(reps)} deliverables with a define, {d['identical']:,} of them byte for byte; the other "
             f"{d['gap_only']:,} differ only by "
             f"[defects of the submitted define](glossary.md#define-defect), which yamaa does not copy "
             f"(differences: {gaps}). "
             f"**{d['unexplained']} differences are unexplained.**"
             + (f" {d['nospec']:,} more elements describe {len(nospec)} datasets with no spec yet "
                f"({', '.join(nospec)})." if d["nospec"] else ""))
    f, art, checked = dd_summary(adam)
    if define_data()["cuts"]:
        by = {}
        for x in f:
            by[x["check"]] = by.get(x["check"], 0) + 1
        nds = len({(x["cut"], x["dataset"]) for x in f})
        L.append(f"- **Define-XML against the data: {len(f):,} findings in {nds} of the {checked} datasets** in the "
                 f"{len(define_data()['cuts'])} deliverables with a define, where the sponsor's received define and "
                 "its submitted datasets disagree: " + ", ".join(f"{n:,} {DD_LABEL[k]}" for k, n in
                                                                 sorted(by.items(), key=lambda kv: -kv[1]))
                 + f". {len(art):,} more, types and labels in files FDA redacted or released as JMP tables, may come from the "
                 "release and are set apart ([define vs data](findings/define-data.md)).")
    data_cuts = [f"{info[k]['title']} `{c}`" for k in adam["studies"] for c in info[k].get("data_cuts", [])]
    work = [f"the {len(opened)} datasets that still differ with a cause to fix"] if opened else []
    if uncompared:
        work.append(f"a cell-by-cell comparison of the {len(uncompared)} datasets whose column sets differ")
    if nospec:
        work.append(f"{len(nospec)} received datasets with no spec yet ({', '.join(nospec)})")
    if data_cuts:
        work.append(f"{len(data_cuts)} released folders with SDTM but no ADaM datasets and no specs "
                    f"({', '.join(data_cuts)})")
    jmp = sum(1 for r in sources() if r["format"] == "jmp")
    work.append(f"{jmp} input files PHMPT released only as JMP tables, which the kit cannot fetch "
                    f"({runner()} says how to supply a conversion)")
    L.append("- **Still open:** " + "; ".join(work) + ".")
    return L


def studies_table(adam: dict, define: dict, module5: dict) -> list[str]:
    """One row per study and a total: the analysis-set results (scope_row)."""
    L = [f"| Study | Sponsor | Program files released | Deliverables | {SCOPE_HEAD} |",
         "| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |"]
    items_all, reps_all, f_all, progs_all = [], [], [], 0
    for key, st in adam["studies"].items():
        items = [(key, cut, r) for cut, rows in st["cuts"].items() for r in rows]
        reps = list(define["studies"][key].values())
        f = dd_findings(key)
        progs = module5["studies"][M5[key]]["files"].get("program", 0)
        L.append(f"| [{st['title']}](findings/{PAGES[key]}.md) | {st['sponsor']} | {progs or 'none'} | "
                 f"{len(st['cuts'])} | " + scope_row(items, reps, f, "findings/") + " |")
        items_all += items
        reps_all += reps
        f_all += f
        progs_all += progs
    L.append(f"| **All** | | {progs_all} | {sum(len(st['cuts']) for st in adam['studies'].values())} | "
             + scope_row(items_all, reps_all, f_all, "findings/") + " |")
    return L


def outside_datasets(adam: dict) -> list[tuple[str, list[str], list[str], str]]:
    """[(study title, cuts, datasets, absent input)]: the datasets outside the analysis set."""
    by: dict = {}
    for key, st, cut, r in all_rows(adam):
        if not input_scope(key, cut, r)["in"]:
            mi = next(e for e in entries("missing_input", key, cut, r["dataset"]) if e.get("substitute"))
            g = by.setdefault((st["title"], " ".join(mi["missing"].split())), {"cuts": [], "datasets": []})
            for k, v in (("cuts", cut.upper()), ("datasets", r["dataset"])):
                if v not in g[k]:
                    g[k].append(v)
    return [(title, g["cuts"], g["datasets"], missing) for (title, missing), g in by.items()]


def analysis_set_section(adam: dict, module5: dict) -> list[str]:
    t = scope_totals(scope_items(adam))
    n = len(module5["studies"])
    data = [k for k, s in module5["studies"].items() if s["files"].get("adam")]
    progs = [k for k in data if module5["studies"][k]["files"].get("program")]
    no_prog = [adam["studies"][a]["title"] for a, m in M5.items() if m in data and m not in progs]
    ncuts = sum(1 for _ in cut_rows(adam))
    out = outside_datasets(adam)
    out_txt = "; ".join(f"{title} {' and '.join(cuts)}: {', '.join(ds)}" for title, cuts, ds, _ in out)
    absent = " ".join(f"For {title} {' and '.join(cuts)} it is {missing}." for title, cuts, _, missing in out)
    cols_absent = t["cols_lack"] - t["carried"]
    return [
        "## Analysis set", "",
        "Results are counted on an analysis set fixed from the release before any comparison: a value is in it "
        "when the release holds every input the value is derived from and a submitted value to compare it with. "
        "Whether a value reproduces plays no part. Everything outside the set is listed with its absent input on "
        "[Inputs outside the analysis set](findings/inputs.md).", "",
        '<div class="pilot-metrics" markdown="1" role="region" aria-label="Analysis set" tabindex="0">', "",
        "| Level | Released | Outside the analysis set | Analysis set | Fully reproduced |",
        "| --- | --- | --- | --- | --- |",
        f"| Studies | {n} on PHMPT | {n - len(data)} released documents only, no ADaM datasets "
        f"([coverage](coverage.md)) | **{len(data)}**, {len(progs)} of them with the sponsor's ADaM programs | - |",
        f"| ADaM datasets | {t['datasets']} in {ncuts} deliverables, all with a spec | {t['out']} built from a domain "
        f"the release lacks ({out_txt}) | **{t['in']}** ({pct(t['in'], t['datasets'])}) | "
        f"**{t['reproduced']}** ({pct(t['reproduced'], t['in'])}) |",
        f"| Columns | {t['cols']:,} | {t['cols_out'] + t['cols_lack']:,}: {t['cols_out']:,} in those {t['out']} "
        f"datasets, {cols_absent:,} that read an absent input, {t['carried']:,} carried from the submitted dataset | "
        f"**{t['cols_in']:,}** ({pct(t['cols_in'], t['cols'])}) | **{t['cols_rep']:,}** ({pct(t['cols_rep'], t['cols_in'])}) |",
        f"| Cells | {millions(t['cells'])} | {millions(t['cells'] - t['cells_in'])}: {millions(t['cells_out'])} in "
        f"those {t['out']} datasets, {millions(t['cells_lack'])} in columns and rows without input, "
        f"{t['redacted']:,} submitted cells FDA redacted to `(b)(6)` | **{millions(t['cells_in'])}** "
        f"({pct(t['cells_in'], t['cells'])}) | **{millions(t['cells_rep'])}** ({pct(t['cells_rep'], t['cells_in'])}) |",
        "", "</div>", "",
        f"- **Studies.** Only {len(data)} of the {n} studies released ADaM datasets in Module 5. "
        + (f"{', '.join(no_prog)} released datasets and defines but no programs; its specs follow the define and "
           "the data. " if no_prog else "")
        + "The others released documents only.",
        f"- **Datasets.** Every released ADaM dataset has a spec. A dataset is outside when the release lacks the "
        f"domain its rows are built from. {absent} The spec reads another release's snapshot instead; the study "
        "page reports that result, but it is not counted here.",
        f"- **Columns.** A column is outside when its derivation reads an input the release does not hold: a "
        "licensed dictionary or a sponsor file that was not submitted, SDTM values FDA redacted, or records the "
        "released SDTM does not carry. Each absent input is recorded, with the owner's decision, in "
        f"`data/differences.yaml`. The {t['carried']} carried columns are copied from the submitted dataset because "
        "their input is absent.",
        f"- **Rows and cells.** Where an absent input decides whether a row exists (the WHODRUG ATC expansion of "
        f"C4591001 ADCM, records the released EUA SDTM lacks), the submitted rows with no derived counterpart are "
        f"outside: {t['rows_lack']:,} rows. The cells are those of the analysis-set columns on the analysis-set "
        "rows, less the submitted cells FDA redacted, which have no value to compare with.",
        f"- **Fully reproduced** means equal to the submitted value under the study's comparison rules, as the "
        f"comparison recorded it. A column counts when all of its analysis-set cells do, so a submitted row yamaa "
        f"does not write counts against every column. A dataset counts when all of its analysis-set cells do and "
        f"yamaa writes no row the submitted dataset lacks, apart from rows an absent input explains. Only what the "
        f"comparison accounted for counts: where the column sets differ, `scripts/verify_compare.py` compares the "
        f"columns both datasets have, and a comparison on keys records the rows on one side only."
        + (f" {t['not_compared_any']} datasets were verified before it did, and none of their {t['cols_nc']:,} "
           f"columns and {millions(t['cells_nc'])} cells is counted as reproduced." if t["not_compared_any"] else "")
        + f" {t['reproduced_complete']} of the {t['reproduced']} hold every input. "
        f"Of the other {t['in'] - t['reproduced']}, "
        + " and ".join(p for p in (f"{t['not compared']} were not compared cell by cell" if t["not compared"] else "",
                                   f"{t['defect']} differ only where the submitted file is defective"
                                   if t["defect"] else "",
                                   f"{t['open']} still differ" if t["open"] else "") if p)
        + " ([key findings](#key-findings)).", ""]


def inputs_page(adam: dict) -> str:
    """findings/inputs.md: what the analysis set leaves out, and the problems of the submitted files."""
    items = all_rows(adam)
    t = scope_totals(scope_items(adam))
    g = "../"
    L = ["# Inputs outside the analysis set", "",
         f"The [analysis set]({g}results.md#analysis-set) holds the part of the release that has every input its values "
         "are derived from. This page lists what it leaves out and why: datasets built from a domain the release "
         "lacks, columns and rows that read an absent input, columns carried from the submitted dataset, and "
         "submitted cells FDA redacted. It then lists the problems of the submitted files themselves, which stay "
         "in the analysis set. Each absent input is recorded, with the owner's decision and the reason, in "
         "`data/differences.yaml`; terms: [glossary](../glossary.md).", ""]
    cat = {k: [0, 0, 0, 0] for k in ("domain", "absent", "carried", "rows", "redacted")}  # datasets, columns, rows, cells
    for key, st, cut, r in items:
        s = input_scope(key, cut, r)
        if not s["checked"]:
            continue
        if not s["in"]:
            cat["domain"][0] += 1
            cat["domain"][1] += s["cols"]
            cat["domain"][2] += s["rows"]
            cat["domain"][3] += s["cells"]
            continue
        carried = set(r.get("carried_columns") or [])
        absent = [c for c in s["lack_cols"] if c not in carried]
        for k, cols in (("absent", absent), ("carried", [c for c in s["lack_cols"] if c in carried])):
            if cols:
                cat[k][0] += 1
                cat[k][1] += len(cols)
                cat[k][3] += s["rows"] * len(cols)
        if s["lack_rows"]:
            cat["rows"][0] += 1
            cat["rows"][2] += s["lack_rows"]
            cat["rows"][3] += s["lack_rows"] * (s["cols"] - len(s["lack_cols"]))
        if s["redacted"]:
            cat["redacted"][0] += 1
            cat["redacted"][3] += s["redacted"]
    label = {"domain": "[Datasets built from a domain the release lacks](#domain)",
             "absent": "[Columns that read an absent input](#absent)",
             "carried": "[Columns carried from the submitted dataset](#carried)",
             "rows": "[Rows an absent input decides](#absent)",
             "redacted": "[Submitted cells FDA redacted](#redacted)"}
    L += ["## Summary", "",
          "| Outside the analysis set | Datasets | Columns | Rows | Cells |", "| --- | ---: | ---: | ---: | ---: |"]
    for k, (nd, nc, nr, ncell) in cat.items():
        L.append(f"| {label[k]} | {nd} | {nc:,} | {nr:,} | {ncell:,} |")
    L += ["", f"A dataset can appear in more than one row. Together they leave {t['cols_out'] + t['cols_lack']:,} of "
          f"{t['cols']:,} columns and {millions(t['cells'] - t['cells_in'])} of {millions(t['cells'])} cells outside "
          "the analysis set.", ""]

    L += ["## Datasets built from a domain the release lacks {#domain}", "",
          "The release lacks the domain these datasets' rows are built from, so the spec reads another release's "
          "snapshot of it. The study page reports how far that reproduces; none of it is counted in the analysis set.",
          "", "| Study and cut | Dataset | Rows x columns | Absent input | Read instead | Subjects reproduced exactly |",
          "| --- | --- | --- | --- | --- | --- |"]
    for key, st, cut, r in items:
        if input_scope(key, cut, r)["in"] or r["verdict"] == "not checkable":
            continue
        mi = next(e for e in entries("missing_input", key, cut, r["dataset"]) if e.get("substitute"))
        sub = mi.get("subjects")
        L.append(f"| [{st['title']} {st['cut_titles'][cut]}]({PAGES[key]}.md#{cut}) | {r['dataset']} | "
                 f"{r['rows']:,} x {r['cols']} | {mi['missing']} | {mi['substitute']} | "
                 + (f"{sub['exact']:,} of {sub['of']:,} ({pct(sub['exact'], sub['of'])})" if sub else "-") + " |")

    L += ["", "## Columns and rows without input {#absent}", "",
          "Each row names the absent input and what of the dataset it leaves out: the columns whose derivation reads "
          "it and, where it decides whether a row exists, the submitted rows with no derived counterpart. The rest of "
          "the dataset is in the analysis set.", ""]
    for key, st in adam["studies"].items():
        rows = []
        for cut, rs in st["cuts"].items():
            for r in rs:
                s = input_scope(key, cut, r)
                carried = set(r.get("carried_columns") or [])
                absent = [c for c in s["lack_cols"] if c not in carried]
                if not s["in"] or not (absent or s["lack_rows"]):
                    continue
                miss = "; ".join(dict.fromkeys(" ".join(e["missing"].split())
                                               for e in entries("missing_input", key, cut, r["dataset"])))
                rows.append(f"| [{st['cut_titles'][cut]}]({PAGES[key]}.md#{cut}) | {r['dataset']} | {miss} | "
                            + (", ".join(f"`{c}`" for c in absent) or "-") + " | "
                            + (f"{s['lack_rows']:,} of {s['rows']:,}" if s["lack_rows"] else "-") + " |")
        if rows:
            L += [f"### {st['title']}", "", "| Cut | Dataset | Absent input | Columns outside | Rows outside |",
                  "| --- | --- | --- | --- | --- |", *rows, ""]

    L += ["## Columns carried from the submitted dataset {#carried}", ""]
    carried = [(st, cut, r) for key, st, cut, r in items if r.get("carried_columns")]
    if carried:
        L += ["These columns are copied from the submitted dataset, not derived, because the input they are derived "
              "from is not in the release. They are outside the analysis set.", "",
              "| Study and cut | Dataset | Columns |", "| --- | --- | --- |"]
        L += [f"| {st['title']} {st['cut_titles'][cut]} | {r['dataset']} | "
              + ", ".join(f"`{c}`" for c in r["carried_columns"]) + " |" for st, cut, r in carried]
    else:
        L.append("None.")

    L += ["", "## Submitted cells FDA redacted {#redacted}", "",
          "FDA replaced these submitted ADaM values with `(b)(6)` (FOIA exemption 6) before release, so there is no "
          "value to compare the derived one with. They are left out of the analysis-set cells. (Redacted SDTM values "
          "are absent inputs, above.)", "",
          "| Study and cut | Dataset | Cells | Columns |", "| --- | --- | ---: | --- |"]
    for key, st, cut, r in items:
        s = input_scope(key, cut, r)
        if s["in"] and s["redacted"]:
            L.append(f"| {st['title']} {st['cut_titles'][cut]} | {r['dataset']} | {s['redacted']:,} | "
                     + ", ".join(f"`{c}` {n:,}" for c, n in r["redacted_columns"].items() if c not in s["lack_cols"])
                     + " |")

    L += ["", "## Problems of the submitted files", "",
          "These stay in the analysis set: the inputs are there, but the submitted files disagree with each other or "
          "with themselves.", "", "### Defects of the submitted files", ""]
    defects = differences().get("submitted_defect") or []
    if defects:
        L += ["The submitted dataset is malformed or was not produced by its released program; the spec follows "
              "the program, and the dataset is counted as differing only where the file is defective.", "",
              "| Study | Cuts | Dataset | Defect |", "| --- | --- | --- | --- |"]
        L += [f"| {adam['studies'][e['study']]['title']} | {', '.join(e['cuts'])} | {e['dataset']} | "
              f"{' '.join(e['defect'].split())} |" for e in defects]
    else:
        L.append("None recorded.")
    L += ["", "### Program and submitted file disagree", ""]
    notes = differences().get("program_notes") or []
    if notes:
        L += ["The released program's text and the submitted dataset disagree. The note does not change the result.",
              "", "| Study | Cuts | Dataset | What disagrees |", "| --- | --- | --- | --- |"]
        L += [f"| {adam['studies'][e['study']]['title']} | {', '.join(e['cuts'])} | {e['dataset']} | "
              f"{' '.join(e['note'].split())} |" for e in notes]
    else:
        L.append("None recorded.")
    f, art, checked = dd_summary(adam)
    L += ["", "### Define-XML and data disagree", "",
          f"{len(f):,} findings where a received define and its submitted datasets disagree: see "
          "[Define-XML against the data](define-data.md).", ""]
    return "\n".join(L)


DD_TEXT = {  # check: (heading, what the define and the data say)
    "dataset": ("Datasets in only one of the two", "A dataset the define describes that the release lacks, or one "
                "the release has that the define does not describe."),
    "variable": ("Variables in only one of the two", "A variable the define lists that the dataset lacks, or a "
                 "column of the dataset the define does not list."),
    "type": ("Data type", "The define says text and the column is numeric, or the define says integer or float and "
             "the column is character."),
    "length": ("Length", "A text value longer than the define's Length."),
    "codelist": ("Codelist", "Values outside the variable's enumerated codelist (its coded values and decodes); "
                 "dictionaries and other external codelists are not checked."),
    "mandatory": ("Mandatory", "The define marks the variable Mandatory=\"Yes\" (a value on every record) and some "
                  "records have none."),
    "key": ("Keys", "The define's key variables do not identify one record: some records repeat a key."),
    "label": ("Variable label", "The column's label differs from the variable's Description."),
    "dataset label": ("Dataset label", "The dataset's label differs from the dataset's Description."),
}
ARTIFACT = {"redaction": "column types or labels, or dataset labels, in files FDA redacted (they hold `(b)(6)` values), "
                         "which FDA's rewrite of the file may have changed (C4591001 ADMH stores its dates as text "
                         "and has file names as labels), and a redacted variable FDA renamed (`BRTHDT` to `BRTHDT_2`)",
            "jmp": "types, lengths or labels of files PHMPT released only as JMP tables, which come from the "
                   "conversion"}


def dd_detail(check: str, fs: list) -> str:
    """One table cell: the findings of one check in one dataset."""
    if check == "dataset":
        return "; ".join("in the define, not released" if x["side"] == "define only" else "released, not in the define"
                         for x in fs)
    if check == "variable":
        parts = []
        for side, text in (("define only", "in the define only"), ("data only", "in the data only")):
            v = [f"`{x['variable']}`" for x in fs if x["side"] == side]
            if v:
                parts.append(f"{text}: {', '.join(v)}")
        return "; ".join(parts)
    if check == "type":
        by: dict = {}
        for x in fs:
            by.setdefault((x["define"], x["data"]), []).append(f"`{x['variable']}`")
        return "; ".join(f"define {d}, data {a}: {', '.join(v)}" for (d, a), v in by.items())
    if check == "length":
        return ", ".join(f"`{x['variable']}` {x['define']} < {x['data']}" for x in fs)
    if check == "codelist":
        return ", ".join(f"`{x['variable']}` {x['values']} of {x['of']} values" for x in fs)
    if check == "mandatory":
        return ", ".join(f"`{x['variable']}` {x['count']:,} of {x['rows']:,}" for x in fs)
    if check == "key":
        return "; ".join(f"`{x['variable']}`: {x['count']:,} of {x['rows']:,} records repeat a key" for x in fs)
    if check == "label":
        return ", ".join(f"`{x['variable']}`" for x in fs)
    return "differs"


def define_data_page(adam: dict) -> str:
    """findings/define-data.md: the received defines against the submitted datasets."""
    dd = define_data()
    f, art, checked = dd_summary(adam)
    nds = len({(x["cut"], x["dataset"]) for x in f})
    nodef = [f"{st['title']} {st['cut_titles'][cut]}" for key, st, cut, _ in cut_rows(adam)
             if f"{key}/{cut}" not in dd["cuts"]]
    L = ["# Define-XML against the submitted data", "",
         "Each received define is checked against the ADaM datasets PHMPT released for the same deliverable. Both are "
         "the sponsor's files and yamaa is not involved: a finding is a place where the sponsor's define and its "
         "datasets disagree. `scripts/define/check_define_data.py` writes the findings "
         f"(`data/reproduction/define_data.json`, collected {dd['meta']['collected']}); terms: "
         "[glossary](../glossary.md).", "",
         f"**{len(f):,} findings in {nds} of the {checked} datasets**, in the {len(dd['cuts'])} deliverables "
         "with a define. " + (f"{' and '.join(nodef)} {'was' if len(nodef) == 1 else 'were'} released without a define "
                              "and are not checked. " if nodef else "")
         + "A finding is one variable, or one dataset for the dataset-level checks.", "",
         "## Findings by check", "",
         "| Check | What it finds | Findings | Datasets |", "| --- | --- | ---: | ---: |"]
    for check, (head, what) in DD_TEXT.items():
        xs = [x for x in f if x["check"] == check]
        L.append(f"| {head} | {what} | {len(xs):,} | {len({(x['cut'], x['dataset']) for x in xs})} |")
    L.append(f"| **All** | | **{len(f):,}** | **{nds}** |")
    L += ["", f"**Set apart as possible release artifacts, not counted: {len(art):,}.** "
          + "; ".join(f"{sum(1 for x in art if x['artifact'] == a):,} are {text}" for a, text in ARTIFACT.items())
          + ". Whether the sponsor or the release made them cannot be told from the files, so they are listed by "
          "deliverable but not counted. The checks on values (variables, lengths, codelists, mandatory values, "
          "keys) are counted in every file; redacted values are never counted as codelist or length findings.", "",
          "## By deliverable", ""]
    for key, st in adam["studies"].items():
        for cut in st["cuts"]:
            c = dd["cuts"].get(f"{key}/{cut}")
            if not c:
                continue
            fs = [x for x in c["findings"] if not x.get("artifact")]
            a = [x for x in c["findings"] if x.get("artifact")]
            L += [f"### {st['title']} {st['cut_titles'][cut]} {{#{key}-{cut}}}", "",
                  f"{len(c['datasets'])} datasets checked against the define"
                  + (f", {k} in only one of the two" if (k := sum(1 for x in c["findings"] if x["check"] == "dataset"))
                     else "") + f"; {len(fs):,} findings"
                  + (f"; {len(a)} more set apart as possible release artifacts" if a else "") + ".", ""]
            if not fs and not a:
                continue
            L += ["| Dataset | Check | Where |", "| --- | --- | --- |"]
            by: dict = {}
            for x in fs + a:
                by.setdefault((x["dataset"], x["check"], x.get("artifact") or ""), []).append(x)
            order = list(DD_TEXT)
            for (ds, check, art_), xs in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][2], order.index(kv[0][1]))):
                head = DD_TEXT[check][0] + (f" (set apart: {'FDA redaction' if art_ == 'redaction' else 'JMP'})"
                                            if art_ else "")
                L.append(f"| {ds} | {head} | {dd_detail(check, xs)} |")
            L.append("")
    return "\n".join(L)


def responsibilities_and_tools(meta: dict) -> list[str]:
    return [
        "## Responsibilities", "",
        "| Role | Responsibility |", "| --- | --- |",
        "| Human review | The project owner sets the scope and the comparison rules, decides how each kind of "
        f"difference is reported ([owner decisions]({BLOB}/DECISIONS.md)), and reviews and merges every change "
        "in Pilot 7 through a pull request. Reviewers check single findings and record their assessment on the "
        "[review page](review/index.md). |",
        "| AI drafting | AI agents (Claude) drafted the specifications, the fetch, verify and define scripts, the "
        "recorded reason for each difference and these pages: until 2026-11-27 in a private development "
        "repository, now frozen, and since then in Pilot 7. Their output is a draft until a person reviews it. |",
        f"| Engine execution | yamaa, at the commit pinned in `yamaa.lock` (`{meta['yamaa_commit']}`), executes each "
        "specification on the submitted SDTM and composes each define from the specifications and the "
        "reproduced-mode layer. |",
        "| Automated checks | Scripts compare every output with the submitted dataset or the received define and "
        "record the result; the publication gate checks every PHMPT file in Pilot 7; CI reruns part of the "
        "reproduction from PHMPT on each change. |", "",
        "## Tools", "",
        "| Tool | Purpose |", "| --- | --- |",
        "| [yamaa](https://elong0527.github.io/yamaa/) | Resolve and execute the YAML specifications; compose "
        "Define-XML in reproduced mode. |",
        "| `scripts/reproduce.py fetch` | Read only the needed members of the PHMPT zips over HTTP range requests and "
        "convert SAS transport files to Parquet. |",
        "| `scripts/reproduce.py verify`, `scripts/verify_compare.py` | Run each spec, in USUBJID partitions where "
        "a dataset is large, and compare the output with the submitted dataset under the study's comparison "
        "rules. |",
        "| `scripts/reproduce.py define`: `transcribe_define.py`, `compose_define.py`, `compare_define.py` | "
        "Transcribe the received define into the reproduced-mode layer, compose the define, and compare it "
        "element by element, attributing each difference to a defect of the submitted define or a dataset "
        "with no spec. |",
        "| `scripts/site/collect_results.py`, `scripts/site/publish.py` | Collect the run reports into "
        "`data/reproduction/`, then write `evidence.json` and these pages from them. |",
        "| `scripts/site/check_verdicts.py` | Compare a fresh run's reports with the recorded verdicts. |",
        "| Publication gate: `.github/scripts/check_phmpt_bundle.py` | Check every PHMPT file in Pilot 7: an "
        "allowlist, ASCII text, the closed evidence schema, the placeholder for every submission method and "
        "description in a spec, no subject identifier, and, run with the fetched inputs, no 12-word run copied "
        "from them. |",
        "| GitHub Actions | On each pull request: run the gate, check that the pages match `data/reproduction/`, "
        f"and rerun every define and the {' and '.join(ci_titles())} datasets from PHMPT (`ci` in `studies.yaml`). |",
        "| GitHub Discussions | Record review assessments. |", ""]


def what_it_shows(adam: dict) -> list[str]:
    carried = [(st["title"], st["cut_titles"][cut], r["dataset"], len(r["carried_columns"]))
               for key, st, cut, r in all_rows(adam) if r.get("carried_columns")]
    jmp = sum(1 for r in sources() if r["format"] == "jmp")
    L = ["## What this shows and what it does not", "",
         "- **Agreement is not validation.** A verdict compares yamaa's output with the dataset the sponsor "
         "submitted. Agreement shows that the specification reproduces the submitted values from the released "
         "inputs. It is not regulatory validation, and it does not show that a derivation follows the analysis "
         "plan.",
         "- **Not every match is exact.** *Matches except missing input*, *reproduced on a substitute input* and "
         "*matches except a defect of the submitted file* are reported apart from exact, with the absent input "
         "or the defect named and every differing cell counted.",
         "- **Carried columns are not derived.** "
         + (" ".join(f"In {t} {c}, " + " and ".join(f"{n} {d} columns" for t2, c2, d, n in carried
                                                       if (t2, c2) == (t, c)) + " are copied from the submitted "
                     "datasets, because the input they are derived from is not in the release."
                     for t, c in dict.fromkeys((t, c) for t, c, d, n in carried)) + " " if carried else "")
         + "Some specs also read another submitted ADaM dataset as input where the program does; the dataset's "
         "notes name it.",
         "- **The define text was transcribed, not authored.** The labels, methods, comments and origins in the "
         "composed defines come from the received defines through the reproduced-mode layer. Define agreement "
         "shows that yamaa can express and write every element of those documents, apart from the named defects "
         "of the submitted define, which yamaa does not copy; it does not show that yamaa authored that text."]
    L.append(f"- **Some inputs are not in an open format.** {jmp} input files are on PHMPT only as JMP tables. "
                 "The published results used reviewed conversions kept in the frozen development repository; to rerun "
                 f"a dataset that reads one, you supply your own conversion (steps in {runner()}).")
    L += ["- **A successful run is not a review.** Every result is a draft until a person reviews it.", ""]
    return L


# ---------------------------------------------------------------- the overview: a story told in charts
# The charts are plain HTML written here: no script and no chart library. A stacked bar is a flex row whose
# segments grow with their counts, and the heatmap is a table. docs/stylesheets/phmpt.css colors them in both
# themes (palette checked for color-vision deficiency and contrast on each surface). Every chart prints its
# numbers beside the marks, has a legend, and has its full table on results.md.

REPO_ACTIONS = f"{PILOT7}/blob/main/.github/workflows/phmpt-check.yml"
STATUS = {  # dataset_status -> (css class, legend label)
    "full": ("phmpt-c-full", "Fully reproduced, every input released"),
    "partial": ("phmpt-c-partial", "Fully reproduced where its input was released"),
    "defect": ("phmpt-c-defect", "Differs only where the submitted file is defective"),
    "open": ("phmpt-c-open", "Still differs, cause to fix"),
    "not compared": ("phmpt-c-nc", "Not fully compared"),
    "outside": ("phmpt-c-out", "Outside the analysis set"),
    "not checked": ("phmpt-c-nc", "Not checked"),
}
DD_SHORT = {"dataset": "Dataset in one only", "variable": "Variable in one only", "dataset label": "Dataset label",
            "label": "Variable label", "type": "Data type"}
HEAT = ((1, 4, 1), (5, 19, 2), (20, 99, 3), (100, None, 4))  # (from, to, step) for the define-vs-data heatmap


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def inline(text: str) -> str:
    """Escaped text whose `code` spans render as code (defect labels are written that way)."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(text))


def dataset_status(key: str, cut: str, r: dict) -> str:
    """input_scope's status, with a reproduced dataset split by whether the release holds every input."""
    s = input_scope(key, cut, r)
    if s["status"] == "reproduced":
        return "partial" if s["lack_cols"] or s["lack_rows"] else "full"
    return s["status"]


def bar(parts: list[tuple[str, float, str]], label: str, width: float = 1.0) -> str:
    """One stacked bar: parts are (css class, amount, tooltip); width is the bar's share of its track."""
    total = sum(n for _, n, _ in parts) or 1
    segs = "".join(f'<span class="phmpt-seg {cls}" style="flex-grow:{n / total:.6f}" title="{esc(tip)}"></span>'
                   for cls, n, tip in parts if n)
    return (f'<span class="phmpt-bar" role="img" aria-label="{esc(label)}" style="width:{100 * width:.2f}%">'
            f"{segs}</span>")


def legend(items: list[tuple[str, str]]) -> str:
    return ('<div class="phmpt-legend" role="list">'
            + "".join(f'<span role="listitem"><span class="phmpt-key {cls}"></span>{inline(text)}</span>'
                      for cls, text in items) + "</div>")


def chart_row(label: str, bar_html: str, value: str) -> str:
    return (f'<div class="phmpt-row"><span class="phmpt-row-label">{label}</span>'
            f'<span class="phmpt-track">{bar_html}</span><span class="phmpt-row-value">{value}</span></div>')


def figure(title: str, body: list[str], note: str = "") -> list[str]:
    """A chart as one raw HTML block (no blank line inside, so Markdown leaves it alone). Plain elements with
    roles, not figure and ul: the theme's typeset rules would center and restyle those."""
    return [f'<div class="phmpt-viz" role="figure" aria-label="{esc(title)}">',
            f'<p class="phmpt-viz-title">{esc(title)}</p>', *body,
            *([f'<p class="phmpt-viz-note">{note}</p>'] if note else []), "</div>", ""]


def tiles(adam: dict, define: dict) -> list[str]:
    t = scope_totals(scope_items(adam))
    d = define_totals([rep for key in adam["studies"] for rep in define["studies"][key].values()])
    f, _, checked = dd_summary(adam)
    nds = len({(x["cut"], x["dataset"]) for x in f})
    left = t["in"] - t["reproduced"]
    why = [f"{t['defect']} at a defect of the submitted file" if t["defect"] else "",
           f"{t['open']} with a cause to fix" if t["open"] else "",
           f"{t['not compared']} not fully compared" if t["not compared"] else ""]
    cards = [
        (f"{t['reproduced']}<small> / {t['in']}</small>", "ADaM datasets fully reproduced",
         f"{pct(t['cells_rep'], t['cells_in'])} of the {millions(t['cells_in'])} cells in the analysis set"),
        (f"{d['reproduced']:,}<small> / {d['scoped']:,}</small>", "Define-XML elements reproduced",
         f"{d['unexplained']} unexplained; {d['gap_only']} differ only by a defect of the submitted define"),
        (f"{left}", f"dataset{'s' if left != 1 else ''} not fully reproduced", "; ".join(w for w in why if w) or "none"),
        (f"{len(f):,}", "places a sponsor's define and data disagree", f"in {nds} of the {checked} datasets with a define"),
    ]
    # The landing page shows these tiles too (.github/scripts/phmpt_headline.py reads between the markers).
    return (["<!-- phmpt-headline:begin -->", '<div class="phmpt-tiles">']
            + [f'<div class="phmpt-tile"><p class="phmpt-tile-value">{v}</p><p class="phmpt-tile-label">{esc(lab)}</p>'
               f'<p class="phmpt-tile-note">{esc(note)}</p></div>' for v, lab, note in cards]
            + ["</div>", "<!-- phmpt-headline:end -->", ""])


def scope_chart(adam: dict) -> list[str]:
    """The analysis set at three levels: reproduced, in the set but not reproduced, outside the set."""
    t = scope_totals(scope_items(adam))
    levels = [("Datasets", t["datasets"], t["in"], t["reproduced"], str),
              ("Columns", t["cols"], t["cols_in"], t["cols_rep"], lambda n: f"{n:,}"),
              ("Cells", t["cells"], t["cells_in"], t["cells_rep"], millions)]
    rows = []
    for name, total, inn, rep, fmt in levels:
        parts = [("phmpt-c-full", rep, f"Fully reproduced: {fmt(rep)}"),
                 ("phmpt-c-open", inn - rep, f"In the analysis set, not fully reproduced: {fmt(inn - rep)}"),
                 ("phmpt-c-out", total - inn, f"Outside the analysis set: {fmt(total - inn)}")]
        label = f"{name}: {fmt(rep)} fully reproduced of {fmt(inn)} in the analysis set; {fmt(total)} released"
        rows.append(chart_row(name, bar(parts, label),
                              f"<strong>{fmt(rep)}</strong> of {fmt(inn)}<br><small>in the set; {fmt(total)} released"
                              "</small>"))
    return figure("The analysis set and what reproduces in it",
                  [legend([("phmpt-c-full", "Fully reproduced"), ("phmpt-c-open", "In the set, not fully reproduced"),
                           ("phmpt-c-out", "Outside the analysis set")]), '<div class="phmpt-rows phmpt-rows--short">',
                   *rows, "</div>"],
                  'Full table: <a href="results/#analysis-set">analysis set</a>. What is outside, and why: '
                  '<a href="findings/inputs/">inputs outside the analysis set</a>.')


def steps(adam: dict, module5: dict) -> list[str]:
    with_progs = sum(1 for k in adam["studies"] if module5["studies"][M5[k]]["files"].get("program"))
    progs = sum(module5["studies"][M5[k]]["files"].get("program", 0) for k in adam["studies"])
    items = [
        ("auto", "Script", "Fetch", "Read the released SDTM, ADaM datasets and Define-XML from the PHMPT zips, "
         "only the members needed."),
        ("ai", "AI drafting", "Specify", f"Write a yamaa spec for each ADaM dataset, porting the sponsor's SAS where "
         f"it was released ({progs} program files in {with_progs} of the {len(adam['studies'])} studies)."),
        ("engine", "Engine execution", "Execute", "yamaa runs each spec on the submitted SDTM and composes the "
         "define from the same specs."),
        ("auto", "Automated check", "Compare", "Cell by cell with the submitted dataset; element by element with the "
         "received define."),
        ("human", "Human review", "Decide and review", "Each difference gets a recorded reason and a dated owner "
         "decision; reviewers assess single findings."),
    ]
    return (['<div class="phmpt-steps" role="list" aria-label="How each dataset was reproduced">']
            + [f'<div class="phmpt-step" role="listitem"><span class="phmpt-role phmpt-role-{k}">{esc(role)}</span>'
               f"<strong>{i}. {esc(name)}</strong><span>{esc(text)}</span></div>"
               for i, (k, role, name, text) in enumerate(items, 1)]
            + ["</div>", ""])


def cuts_chart(adam: dict) -> list[str]:
    order = list(STATUS)
    present = set()
    groups = []
    biggest = max(len(rows) for *_, rows in cut_rows(adam))
    for key, st in adam["studies"].items():
        rows = []
        for cut, rs in st["cuts"].items():
            n = {k: 0 for k in order}
            for r in rs:
                n[dataset_status(key, cut, r)] += 1
            present |= {k for k, v in n.items() if v}
            t = scope_totals([(key, cut, r) for r in rs])
            parts = [(STATUS[k][0], n[k], f"{STATUS[k][1]}: {n[k]}") for k in order if n[k]]
            label = f"{st['title']} {st['cut_titles'][cut]}: " + ", ".join(f"{n[k]} {STATUS[k][1].lower()}"
                                                                           for k in order if n[k])
            value = f"<strong>{t['reproduced']}</strong> / {t['in']}" + (f"<br><small>+{t['out']} outside</small>"
                                                                        if t["out"] else "")
            explore = (f'<a class="phmpt-bar-link" href="review/#phmpt/{key}/{cut}/" '
                       f'aria-label="Review the findings of {esc(st["title"])} {esc(st["cut_titles"][cut])}">'
                       f'{bar(parts, label, len(rs) / biggest)}</a>')
            rows.append(chart_row(f'<a href="findings/{PAGES[key]}/#{cut}">{esc(st["cut_titles"][cut])}</a>',
                                  explore, value))
        groups += [f'<p class="phmpt-group">{esc(st["title"])} <small>{esc(st["sponsor"])}</small></p>', *rows]
    return figure("ADaM datasets by cut: fully reproduced of those in the analysis set",
                  [legend([STATUS[k] for k in order if k in present]), '<div class="phmpt-rows">', *groups, "</div>"],
                  "Bar length is the number of datasets in the cut. A cut's name opens its datasets and the reason "
                  "recorded for every difference; its bar opens its findings on the review page, down to every "
                  'column. The numbers are in the <a href="results/#results-by-cut">table by cut</a>.')


def define_chart(define: dict) -> list[str]:
    agg: dict = {}
    for cuts in define["studies"].values():
        for rep in cuts.values():
            nospec = rep.get("no_spec_elements", {})
            for cls, v in rep["classes"].items():
                a = agg.setdefault(cls, [0, 0])
                a[0] += v["submitted"] - nospec.get(cls, 0)
                a[1] += v["match"]
    biggest = max(a[0] for a in agg.values())
    rows = []
    for cls, (n, same) in sorted(agg.items(), key=lambda kv: -kv[1][0]):
        other = n - same
        parts = [("phmpt-c-full", same, f"Byte for byte: {same:,}"),
                 ("phmpt-c-defect", other, f"Differ only by a defect of the submitted define: {other:,}")]
        rows.append(chart_row(esc(CLASS_LABELS.get(cls, cls)),
                              bar(parts, f"{CLASS_LABELS.get(cls, cls)}: {same:,} of {n:,} byte for byte, {other:,} "
                                  "differ only by a defect of the submitted define", n / biggest),
                              f"<strong>{n:,}</strong>" + (f"<br><small>{other:,} by a defect</small>" if other else "")))
    return figure("Received Define-XML elements by class, all reproduced",
                  [legend([("phmpt-c-full", "Reproduced byte for byte"),
                           ("phmpt-c-defect", "Reproduced except a defect of the submitted define")]),
                   '<div class="phmpt-rows">', *rows, "</div>"],
                  "Bar length is the number of received elements of datasets with a spec, over every define.")


def define_data_chart(adam: dict) -> list[str]:
    cuts = [(key, st, cut) for key, st, cut, _ in cut_rows(adam) if f"{key}/{cut}" in define_data()["cuts"]]
    counts = {(key, cut): {} for key, _, cut in cuts}
    for key, _, cut in cuts:
        for x in dd_findings(key, cut):
            counts[(key, cut)][x["check"]] = counts[(key, cut)].get(x["check"], 0) + 1
    checks = [c for c in DD_TEXT if any(c in v for v in counts.values())]

    def cell(n: int) -> str:
        step = next((h for lo, hi, h in HEAT if n >= lo and (hi is None or n <= hi)), 0)
        return f'<td class="phmpt-heat-{step}">{n:,}</td>' if n else '<td class="phmpt-heat-0">-</td>'

    head = "".join(f'<th scope="col">{esc(DD_SHORT.get(c, DD_TEXT[c][0]))}</th>' for c in checks)
    body = []
    for key, st, cut in cuts:
        c = counts[(key, cut)]
        body.append(f'<tr><th scope="row"><a href="findings/define-data/#{key}-{cut}">{esc(st["title"])}</a>'
                    f'<br><small>{esc(st["cut_titles"][cut])}</small></th>'
                    + "".join(cell(c.get(k, 0)) for k in checks) + f"<td><strong>{sum(c.values()):,}</strong></td></tr>")
    steps_legend = [(f"phmpt-heat-{h}", f"{lo} or more" if hi is None else f"{lo} to {hi}") for lo, hi, h in HEAT]
    return figure("Where the sponsor's define and data disagree: findings by deliverable and check",
                  [legend(steps_legend), '<div class="phmpt-heatmap">', '<table class="phmpt-heat-table">',
                   f'<thead><tr><th scope="col">Deliverable</th>{head}<th scope="col">All</th></tr></thead>',
                   "<tbody>", *body, "</tbody>", "</table>", "</div>"],
                  'Each deliverable links to its findings. Checks with no finding are left out; '
                  '<a href="findings/define-data/">define vs data</a> lists them all.')


def open_items(adam: dict, define: dict) -> list[str]:
    info = studies_info()
    rows = all_rows(adam)
    link = lambda key, st, cut, r: f"[{st['title']} `{cut}` {r['dataset']}](findings/{PAGES[key]}.md#{cut})"
    status = {s: [x for x in rows if dataset_status(x[0], x[2], x[3]) == s] for s in ("open", "defect", "not compared")}
    nospec = [f"{st['title']} `{cut}` {ds}" for key, st in adam["studies"].items()
              for cut, rep in define["studies"][key].items() for ds in rep.get("datasets_without_spec", [])]
    data_cuts = [f"{info[k]['title']} `{c}`" for k in adam["studies"] for c in info[k].get("data_cuts", [])]
    jmp = sum(1 for r in sources() if r["format"] == "jmp")
    out = []
    if status["open"]:
        out.append(f"**{len(status['open'])} datasets still differ** with a diagnosed cause to fix: "
                   + ", ".join(link(*x) for x in status["open"]) + ".")
    if status["defect"]:
        out.append(f"**{len(status['defect'])} datasets differ only where the submitted file is defective**; "
                   "the spec follows the program: " + ", ".join(link(*x) for x in status["defect"]) + ".")
    if status["not compared"]:
        out.append(f"**{len(status['not compared'])} datasets are not fully compared**: "
                   + ", ".join(link(*x) for x in status["not compared"]) + ".")
    if nospec:
        out.append(f"**{len(nospec)} received datasets have no spec yet**: {', '.join(nospec)}.")
    if data_cuts:
        out.append(f"**{len(data_cuts)} released folders have SDTM but no ADaM datasets**, so nothing to reproduce: "
                   f"{', '.join(data_cuts)}.")
    out.append(f"**{jmp} input files are on PHMPT only as JMP tables**, which the kit cannot fetch; {runner()} says "
               "how to supply a conversion.")
    return [f"- {x}" for x in out] + [""]


def ci_titles() -> list[str]:
    """The studies whose datasets CI reruns from PHMPT (`ci: true` in studies.yaml)."""
    return [v["title"] for v in studies_info().values() if v.get("ci")]


def index_page(adam: dict, define: dict, module5: dict) -> str:
    meta = adam["meta"]
    ci = {k for k, v in studies_info().items() if v.get("ci")}
    ci_all = [(key, r) for key, st, cut, r in all_rows(adam)] + [
        (key, None) for key in adam["studies"] for rep in define["studies"][key].values()
        for _ in [None, *rep["gaps"]]]
    ci_n = sum(1 for key, r in ci_all if r is None or key in ci)
    t = scope_totals(scope_items(adam))
    n_studies = len(module5["studies"])
    with_data = sum(1 for s in module5["studies"].values() if s["files"].get("adam"))
    ncuts = sum(1 for _ in cut_rows(adam))
    done = lambda key, cut, rs: all(dataset_status(key, cut, r) in ("full", "partial", "outside") for r in rs)
    complete = [cut for key, st, cut, rs in cut_rows(adam) if done(key, cut, rs)]
    rest = [(key, st, cut) for key, st, cut, rs in cut_rows(adam) if not done(key, cut, rs)]
    partial = sum(1 for key, st, cut, r in all_rows(adam) if dataset_status(key, cut, r) == "partial")
    reps = [rep for key in adam["studies"] for rep in define["studies"][key].values()]
    d = define_totals(reps)
    f, art, checked = dd_summary(adam)
    by = {}
    for x in f:
        by[x["check"]] = by.get(x["check"], 0) + 1
    top = max(by, key=by.get) if by else None
    defects = ", ".join(f"{d['gaps'][g]:,} {defect_label(g)}" for g in DEFECTS if g in d["gaps"])
    L = ["# PHMPT reproduction with yamaa", "",
         f"FDA released the submitted SDTM, ADaM and Define-XML of {with_data} COVID-19 vaccine trials on "
         "[phmpt.org](https://phmpt.org/). AI agents wrote a [yamaa](https://elong0527.github.io/yamaa/) "
         "specification for each submitted ADaM dataset, yamaa ran it on the submitted SDTM, and scripts compared the "
         "result with what the sponsor submitted. This page tells what was done and what was found; each chart links "
         "to the evidence behind it. Every result is a draft pending human review.", "",
         *tiles(adam, define),
         f"yamaa `{meta['yamaa_commit']}`, results collected {meta['collected']}. Terms: [glossary](glossary.md).", "",
         "## What was attempted", "",
         f"Of the {n_studies} studies FDA released on PHMPT, {with_data} include ADaM datasets: {t['datasets']} datasets "
         f"in {ncuts} deliverables, each given a yamaa spec. Before any comparison, an "
         "[analysis set](glossary.md#analysis-set) fixes what the release can support: the datasets, columns and "
         "cells whose every input was released. Within it, "
         f"**{t['reproduced']} of {t['in']} datasets, {t['cols_rep']:,} of {t['cols_in']:,} columns and "
         f"{millions(t['cells_rep'])} of {millions(t['cells_in'])} cells are fully reproduced**.", "",
         *scope_chart(adam),
         "## How it was done", "",
         "Each dataset went through the same five steps. AI agents drafted, yamaa executed, scripts compared, and "
         "people decided how each difference is reported ([responsibilities](#responsibilities)).", "",
         *steps(adam, module5),
         "## ADaM datasets: results by cut", "",
         f"In {len(complete)} of the {ncuts} cuts every dataset in the analysis set is fully reproduced."
         + (" The datasets that are not are in " + ", ".join(f"[{st['title']} {st['cut_titles'][cut]}]"
                                                             f"(findings/{PAGES[k]}.md#{cut})" for k, st, cut in rest)
            + "." if rest else "")
         + f" {partial} of the {t['in']} reproduce only where their input was released: a licensed dictionary, a "
         "sponsor file or values FDA redacted are absent, and those columns are outside the analysis set.", "",
         *cuts_chart(adam),
         "## Define-XML", "",
         f"The defines yamaa composes from the same specs reproduce **all {d['scoped']:,} received elements** of the "
         f"{len(reps)} defines, {d['identical']:,} of them byte for byte. The other {d['gap_only']} differ only by "
         "[defects of the submitted define](glossary.md#define-defect), which yamaa does not copy "
         f"(differences: {defects}). **{d['unexplained']} differences are unexplained.** The define text itself was transcribed "
         "from the received define, not authored ([what this shows](#what-this-shows-and-what-it-does-not)).", "",
         *define_chart(define),
         "## Where the sponsor's own define and data disagree", "",
         f"Apart from yamaa, each received define was checked against the datasets released with it: "
         f"**{len(f):,} findings in {len({(x['cut'], x['dataset']) for x in f})} of the {checked} datasets**."
         + (f" {by[top]:,} of them are {DD_LABEL[top]}." if top else "")
         + f" {len(art):,} more may come from the release itself (FDA redaction, JMP conversion) and are set apart "
         "([define vs data](findings/define-data.md)).", "",
         *define_data_chart(adam),
         "## Still open", "",
         *open_items(adam, define),
         "## Confirm a finding", "",
         '<div class="grid cards" markdown>', "",
         "-   **Drill down**", "", "    ---", "",
         "    Open one finding: its counts, every column with its result and recorded reason, the spec line that "
         "derives it, and the PHMPT file it was compared with. Submit your assessment on GitHub.", "",
         "    [Review a finding](review/index.md)", "",
         "-   **Rerun in CI**", "", "    ---", "",
         f"    Each pull request that changes the reproduction fetches every received define and the "
         f"{' and '.join(ci_titles())} datasets from PHMPT, reruns them, and requires the published result: "
         f"{ci_n} of the {len(ci_all)} findings. The review page marks which.", "",
         f"    [`phmpt-check.yml`]({REPO_ACTIONS})", "",
         "-   **Rerun on your machine**", "", "    ---", "",
         "    Fetch a study from phmpt.org and rerun it with one script. Its header says what you need.", "",
         f"    {runner()}", "", "</div>", "",
         "## Go deeper", "",
         "- [Results tables](results.md): the analysis set, and results by study and by cut.",
         "- Results by study, with every dataset and every difference: "
         + ", ".join(f"[{st['title']}](findings/{PAGES[k]}.md)" for k, st in adam["studies"].items()) + ".",
         "- [Inputs outside the analysis set](findings/inputs.md): every absent or problem input and what it leaves "
         "out.",
         "- [Define-XML against the data](findings/define-data.md): every finding, by check and by deliverable.",
         f"- [Module 5 coverage](coverage.md): all {n_studies} studies and what PHMPT released for each.",
         "- [Glossary](glossary.md): cut, layer, exact, missing input, carried column, submitted-define defect and "
         "the other terms.", ""]
    L += what_it_shows(adam)
    L += responsibilities_and_tools(meta)
    return "\n".join(L)


def results_page(adam: dict, define: dict, module5: dict) -> str:
    """results.md: the overview's numbers as tables."""
    meta = adam["meta"]
    L = ["# Results tables", "",
         f"yamaa `{meta['yamaa_commit']}`, results collected {meta['collected']}. The [overview](index.md) shows "
         "these results as charts; terms are in the [glossary](glossary.md).", "",
         "## Key findings", "",
         *key_findings(adam, define, module5), "",
         *analysis_set_section(adam, module5),
         "## Results by study", "",
         '<div class="pilot-metrics" markdown="1" role="region" aria-label="Results by study" tabindex="0">', "",
         *studies_table(adam, define, module5), "", "</div>", "",
         "**Datasets**, **columns** and **cells reproduced** are counted within the [analysis set](#analysis-set): "
         "those equal to the submitted values under the comparison rules, of those in the set. A dataset counts "
         "when all of its analysis-set cells do. *Without input* counts the columns outside the set. The two "
         "define columns cover every dataset of a deliverable with a define. **Define-XML elements reproduced** "
         "counts the received elements of datasets with a spec that yamaa's composed define reproduces, exactly or "
         "apart from a [defect of the submitted define](glossary.md#define-defect). **Define vs data findings** counts "
         "where the sponsor's received define and submitted datasets disagree, release artifacts apart.", "",
         "## Results by cut", "",
         '<div class="pilot-metrics" markdown="1" role="region" aria-label="Results by cut" tabindex="0">', ""]
    L += metrics_table(adam, define, "findings/")
    L += ["", "</div>", "",
          "The columns mean what they mean in the table by study. A define's elements are its OID-bearing parts: "
          "datasets, variables, methods, comments, codelists, value lists, where clauses, documents and result "
          "displays.", ""]
    return "\n".join(L)


def glossary_terms() -> list:
    """(group, [(anchor, term, text)]), built when the profile is known."""
    return [
        ("Studies, cuts and specs", [
            ("cut", "Cut",
             "One analysis deliverable of a study as PHMPT released it: the SDTM, the ADaM datasets and usually the "
             "define.xml of one eCTD application and sequence, such as *Day 57 analysis (BLA 125752 S3)*. Each cut "
             "is a folder `<study>/<cut>/` named after its sequence (`s3-d57`)."),
            ("data-only-cut", "Data-only folder",
             "A released set of data with no specs yet (`data_cuts` in `studies.yaml`). No result is reported for it."),
            ("spec", "Spec",
             "The yamaa specification of one ADaM dataset (`<cut>/spec/yamaa/<dataset>.yaml`): its inputs, "
             "intermediate tables, keys and the derivation of every column. It is the executable reproduction."),
            ("layer", "Layer (parent)",
             "A spec can name another spec as its `parent:` and state only what differs. Every spec builds on the "
             "study's base layer (`spec/yamaa/base/`), and a later cut's spec is usually a layer over the earlier "
             "cut's spec of the same dataset. A layer can add or replace columns but cannot remove one, so a later "
             "spec that drops columns builds on the base layer only (`standalone` in `studies.yaml`)."),
            ("helper-spec", "Helper spec",
             "A spec for an intermediate table that a dataset spec reads (`spec/yamaa/helper/`). `verify` runs it first."),
            ("partition", "Partition",
             "A large dataset runs in USUBJID partitions streamed through disk, so that every spec runs in 15 GB of "
             "memory (`partitions` in `studies.yaml`). The spec is unchanged; each partition is compared with the "
             "same subjects of the submitted dataset, and together they count as verifying the whole spec."),
        ]),
        ("Analysis set", [
            ("analysis-set", "Analysis set",
             "The part of the release the results are counted on, fixed from the release before any comparison: the "
             "ADaM datasets, columns, rows and cells whose every input is in the release and whose submitted value "
             "can be compared. A dataset is outside when the release lacks the domain its rows are built from; a "
             "column when its derivation reads an absent input or it is carried; a row when an absent input decides "
             "whether it exists; a cell when FDA redacted the submitted value. Whether a value reproduces plays no "
             "part ([inputs outside the analysis set](findings/inputs.md))."),
            ("absent-input", "Absent input",
             "An input a derivation reads that the release does not hold: a licensed dictionary or sponsor file that "
             "was not submitted, SDTM values FDA redacted, or records the released SDTM snapshot does not carry. Each "
             "one is recorded with the columns and rows it affects and the owner's decision (`data/differences.yaml`)."),
            ("fully-reproduced", "Fully reproduced",
             "Equal to the submitted value under the study's comparison rules. A dataset is fully reproduced when all "
             "of its analysis-set cells are, and yamaa writes no row the submitted dataset lacks apart from rows an "
             "absent input explains."),
            ("define-data", "Define vs data finding",
             "A place where a received define and the submitted datasets it describes disagree: a dataset or variable "
             "in only one of them, a data type, a length, a codelist, a mandatory variable with missing values, keys "
             "that repeat, or a label. Both files are the sponsor's ([define vs data](findings/define-data.md))."),
            ("release-artifact", "Possible release artifact",
             "A define-vs-data difference the release may have made: a column type or label, or the dataset label, in "
             "a file FDA redacted and rewrote (it holds `(b)(6)` values), a redacted variable FDA renamed, or the type, "
             "length or label of a file PHMPT released only as a JMP table. Listed, not counted."),
        ]),
        ("Dataset results", [
            ("comparison-rules", "Comparison rules",
             "How a study's datasets are compared (`compare` in `studies.yaml`): rows are matched on the dataset's "
             "keys; numbers are equal within 1e-10 and strings are compared with spaces removed (every study but "
             "BNT162-01, which is compared strictly); a submitted cell redacted to `(b)(6)` is not compared."),
            ("exact", "Exact",
             "yamaa's output equals the submitted dataset cell for cell: same rows, same columns, same values."),
            ("exact-under-rules", "Exact under the comparison rules",
             "Equal once the comparison rules are applied, but not strictly equal: some numbers differ by less than "
             "1e-10, some strings only by spaces, or some submitted cells are redacted to `(b)(6)`. Counted as exact."),
            ("redacted", "(b)(6) redacted cell",
             "A submitted value FDA replaced with `(b)(6)` (FOIA exemption 6, personal privacy) before release. It is "
             "not compared and is counted per column. When FDA redacted an SDTM value, the ADaM values derived from "
             "it cannot be recovered: see missing input."),
            ("missing-input", "Matches except missing input",
             "Every difference comes from an input the release lacks: a licensed dictionary that was not submitted "
             "(WHODRUG), a sponsor file the program reads, or SDTM values FDA redacted. The spec derives the columns "
             "as the program does. The verdict holds only while the differences stay within the columns and cell "
             "counts recorded for that input (`data/differences.yaml`), and it is reported apart from exact."),
            ("substitute-input", "Reproduced on a substitute input",
             "The release lacks a domain, so the spec reads another release's snapshot of it. The differences are "
             "everything the two snapshots disagree on, so they are reported apart from missing input, with the "
             "number of subjects that reproduce exactly."),
            ("submitted-defect", "Matches except a defect of the submitted file",
             "Every difference comes from the submitted file itself: a malformed cell, or rows its released program "
             "writes that the file lacks, so the file was not produced by the program text as released. The spec "
             "follows the program. Recorded under `submitted_defect` in `data/differences.yaml`, and reported apart "
             "from exact; a dataset that also lacks an input reads \"matches except missing input and a defect of "
             "the submitted file\"."),
            ("open", "Open (N cells differ)",
             "The dataset still differs and the cause is still to fix. The study page gives the diagnosed cause of "
             "each difference."),
            ("no-reason", "No recorded reason yet",
             "A differing column that no entry of `data/differences.yaml` covers. It stays open until one does."),
            ("not-checked", "Not checked",
             "The spec could not be run or compared (for example, its submitted dataset is not in the release)."),
            ("carried", "Carried column",
             "A column copied from the submitted dataset instead of derived, because the input it is derived from is "
             "not in the release. Carried columns are listed on the study page and never counted as derived."),
            ("adam-input", "Submitted ADaM dataset as input",
             "A spec may read another submitted ADaM dataset where the program does, or where the released SDTM "
             "cannot supply the program's input. The dataset's notes name it."),
            ("program-note", "Program and submitted file disagree",
             "The released program's text and the submitted file disagree: the file was not produced by the program "
             "as released, or the program contradicts its own stated intent (the spec then follows the intent). "
             "Recorded as a note; it does not change the verdict."),
            ("hold", "On hold", "A dataset the owner has put on hold; its result is shown with the hold noted."),
        ]),
        ("Define-XML", [
            ("received-define", "Received define",
             "The `define-adam.xml` of a cut as PHMPT released it. It is not published; `fetch` reads it from PHMPT."),
            ("reproduced-mode-layer", "Reproduced-mode layer",
             "A metadata layer over a cut's specs (`<cut>/spec/define/`): what the received define declares that the "
             "specs do not carry, such as labels, methods, comments, codelists, value-level metadata, OIDs and order. "
             "`transcribe_define.py` writes it from the received define, so it holds only the received text and is "
             "not published; `define --transcribe` writes it again. yamaa composes the define from the specs and "
             "this layer."),
            ("element", "Element",
             "An OID-bearing part of a define: a dataset (ItemGroupDef), variable (ItemDef), method, comment, codelist, "
             "value list, where clause, document or result display. Defines are compared element by element."),
            ("define-defect", "Defect of the submitted define",
             "Received content that is invalid or nonstandard and that yamaa does not copy, by an owner decision "
             "recorded on a yamaa issue:\n\n"
             + "\n".join(f"- **{label}.** {text} ({issue(n)})" for label, text, n in DEFECTS.values())
             + "\n\nThe first breaks the ODM schema; the other two are nonstandard content that yamaa's owner "
             "decided not to copy. An element "
             "that differs only by these defects counts as reproduced apart from submitted-define defects, and each "
             "study page counts them per cut. Earlier results also named *engine gaps*, things yamaa could not "
             "declare yet; the last were fixed by yamaa#5055 and yamaa#5062."),
            ("no-spec", "No spec yet",
             "A dataset the received define describes but that has no spec here. Its elements are counted apart and "
             "are not compared."),
            ("unexplained", "Unexplained difference",
             "A define difference that is neither a defect of the submitted define nor an element of a dataset "
             "with no spec."),
        ]),
        ("Inputs", [
            ("jmp-only", "JMP-only input",
             "A file PHMPT released only as a JMP table, not as a SAS transport file. JMP's format has no open "
             "reader, so the kit cannot fetch it"
             + f" ({runner()} says how to supply a conversion)."),
            ("study-lists", "Study-level lists",
             "Spreadsheets the C4591001 programs read (subject lists, term lists, a BMI scale), released as .xlsx. "
             "`scripts/convert_lists.py` copies their cells to `c4591001/data/lists/`."),
        ]),
    ]


def glossary_page() -> str:
    L = ["# Glossary", "", "The terms the PHMPT reproduction pages use, grouped as a result is read.", ""]
    for group, terms in glossary_terms():
        L += [f"## {group}", ""]
        for anchor, term, text in terms:
            L += [f"### {term} {{#{anchor}}}", "", text, ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", nargs="?", type=Path, default=SITE_DIR, help="folder that receives the pages")
    args = ap.parse_args()
    public_profile(args.dir)
    print(f"wrote the PHMPT pages to {args.dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
