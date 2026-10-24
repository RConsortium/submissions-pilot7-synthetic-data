#!/usr/bin/env python3
"""Generate study pages from the catalog and this build's validation reports."""

import argparse
import json
import os
from pathlib import Path
import shutil

from study_evidence import validate_reports

ROOT = Path(__file__).resolve().parents[2]
REPO = "https://github.com/RConsortium/submissions-pilot7-synthetic-data"
CATALOG = ROOT / ".github" / "yamaa-studies.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path,
                        default=ROOT / ".build" / "validation")
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text())
    target = ROOT / "docs" / "studies"
    target.mkdir(parents=True, exist_ok=True)
    evidence = ROOT / "docs" / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    index = ["# Study verification", "",
             "These results come from the checks that built this website. "
             "Each project is checked, run and saved before its existing "
             "comparator checks the derived data against the official files.", "",
             "| Study | Built datasets | Official comparison |",
             "| --- | ---: | --- |"]
    reports = {name: json.loads((args.reports / f"{name}.json").read_text())
               for name in catalog}
    validate_reports(ROOT, catalog, reports, os.environ.get("GITHUB_SHA"))
    for name, entry in catalog.items():
        report_file = args.reports / f"{name}.json"
        report = json.loads(report_file.read_text())
        source_ref = report.get("repository_commit") or "main"
        datasets = report["datasets"]
        if report['status'] == 'pending':
            index.append(f"| [{entry['title']}]({name}.md) | 0 | Project pending |")
            page = [f"# {entry['title']}", "", entry['description'], "",
                    "!!! note \"Project not yet merged\"", "",
                    "    The Pilot 6 ADSL proposal is still under review. "
                    "No Pilot 6 dataset was built or compared in this website run.", "",
                    f"[Study source]({entry['source']}) · "
                    f"[ADSL proposal]({REPO}/pull/104)", "",
                    "## Remaining coverage", "",
                    "ADSL reference validation and the other seven derivations "
                    "remain pending. The website will validate the project "
                    "automatically once it is merged.", "",
                    f"[Download the validation record](../evidence/{name}.json).", ""]
            (target / f"{name}.md").write_text("\n".join(page))
            shutil.copyfile(report_file, evidence / f"{name}.json")
            continue
        if any(d["build"] != "succeeded" or d["comparison"] == "failed"
               for d in datasets):
            raise ValueError(f"Cannot publish failed evidence: {report_file}")
        verified = sum(d["comparison"] == "passed" for d in datasets)
        status = f"{verified} passed" if verified else "Reference unavailable"
        index.append(f"| [{entry['title']}]({name}.md) | {len(datasets)} | {status} |")
        page = [f"# {entry['title']}", "", entry["description"], "",
                f"[Study source]({entry['source']}) · "
                f"[Repository folder]({REPO}/tree/{source_ref}/{name}) · "
                f"[Project specification]({REPO}/blob/{source_ref}/{name}/spec/yamaa/project.yaml)", ""]
        if any(d["comparison"] == "unavailable" for d in datasets):
            page += ["!!! warning \"Built, awaiting reference comparison\"", "",
                     "    ADSL passes the engine's checks and builds from SDTM. "
                     "It has **not** been compared with Pilot 6's production ADaM. "
                     "The other seven target datasets still need specifications.", "",
                     "    The initial ADSL adapts Pilot 3's shared study "
                     "derivations into a self-contained specification, reads Pilot 6 SDTM, "
                     "and adds COMPLFL from Pilot 6's workbook. "
                     "Review against the production programs and reference data "
                     "is still required.", ""]
        page += ["## Dataset results", "",
                 "| Dataset / specification | Rows | Columns | Build | Official comparison |",
                 "| --- | ---: | ---: | --- | --- |"]
        for d in datasets:
            comparison = "Passed" if d["comparison"] == "passed" else "Unavailable"
            page.append(
                f"| [{d['domain']}]({REPO}/blob/{source_ref}/{d['spec']}) | "
                f"{d['rows']:,} | {d['columns']} | Succeeded | {comparison} |"
            )
        cells = sum(d["rows"] * d["columns"] for d in datasets
                    if d["comparison"] == "passed")
        if cells:
            page += ["", f"**{cells:,} cells matched** under the "
                     "[established comparison policy](../verification.md)."]
        page += ["", "## Run this study", "", "From the repository root, "
                 "after [installing the pinned environment](../running.md):", "",
                 "```bash", f"python .github/scripts/validate_yamaa.py {name}", "```", ""]
        if entry["pending"]:
            page += ["## Remaining coverage", "",
                     ", ".join(entry["pending"]) + " are outside the active project.", ""]
        page += ["## Evidence", "",
                 f"Generated: `{report['created_utc']}`. "
                 f"Engine: `yamaa {report['yamaa_version']}` at "
                 f"[`{report['yamaa_revision'][:12]}`]"
                 f"(https://github.com/elong0527/yamaa/commit/{report['yamaa_revision']}).", ""]
        if report.get("repository_commit"):
            sha = report["repository_commit"]
            page += [f"Pilot 7 source: [`{sha[:12]}`]({REPO}/commit/{sha}).", ""]
        page += [f"[Download the validation record](../evidence/{name}.json).", ""]
        (target / f"{name}.md").write_text("\n".join(page))
        shutil.copyfile(report_file, evidence / f"{name}.json")
    index += ["", "A successful build establishes that the specification runs. "
              "Only a passed official comparison establishes agreement with "
              "the staged reference. See [comparison policy](../verification.md) "
              "for tolerance, labels, keys and missing-value handling.", ""]
    (target / "index.md").write_text("\n".join(index))


if __name__ == "__main__":
    main()
