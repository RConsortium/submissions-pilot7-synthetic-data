#!/usr/bin/env python3
"""Check, build and compare one study; write evidence for the documentation.

Uses the study's existing strict comparator, including its established
null/empty-string, label, type, alignment and numeric tolerance policies.
An unavailable reference is reported as unavailable, never as a match.
"""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re

import yaml
import yamaa

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / ".github" / "yamaa-studies.json"


def main():
    catalog = json.loads(CATALOG.read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", choices=catalog)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    study = ROOT / args.study
    project_file = study / "spec" / "yamaa" / "project.yaml"
    project = yamaa.project(project_file)
    check = project.check()
    print(check, flush=True)
    if check.status != "succeeded":
        print(check.issues.to_pylist())
        return 1
    runs = project.run("adam")
    print(runs, flush=True)
    if runs.status != "succeeded":
        print(runs.issues.to_pylist())
        return 1
    runs.save()

    comparator = None
    if catalog[args.study]["comparison"] == "official":
        path = study / "program" / "adam" / "python" / "compare.py"
        spec = importlib.util.spec_from_file_location("study_compare", path)
        comparator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(comparator)

    rows = []
    specs = yaml.safe_load(project_file.read_text())["adam"]["specs"]
    for relative in specs:
        spec_file = project_file.parent / relative
        declaration = yaml.safe_load(spec_file.read_text())
        domain = declaration["domain"]
        output = runs[domain].output
        matched = None
        if comparator is not None:
            if hasattr(comparator, "compare_domain"):
                matched = comparator.compare_domain(spec_file.stem)["ok"]
            else:
                matched = comparator.compare(spec_file.stem)
        rows.append({
            "domain": domain,
            "spec": spec_file.relative_to(ROOT).as_posix(),
            "rows": output.num_rows,
            "columns": len(output.column_names),
            "build": "succeeded",
            "comparison": ("unavailable" if matched is None else
                           "passed" if matched else "failed"),
        })

    requirements = study / "program" / "adam" / "python" / "requirements.txt"
    revision = re.search(
        r"yamaa\.git@([0-9a-f]{40})", requirements.read_text()
    ).group(1)
    report = {
        "study": args.study,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repository_commit": os.environ.get("GITHUB_SHA"),
        "yamaa_revision": revision,
        "yamaa_version": yamaa.__version__,
        "datasets": rows,
    }
    destination = args.report or (
        ROOT / ".build" / "validation" / f"{args.study}.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Evidence: {destination}")
    return int(any(row["comparison"] == "failed" for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
