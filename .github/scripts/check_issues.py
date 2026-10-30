#!/usr/bin/env python3
"""Check a study's authored issues against its local verification report.

The issue author (.automation/consistency_review/issues.md) runs this after
verify_derivations.py, instead of a full site build: a stale basis, an
unresolved selector, an ungrouped finding or an invalid file fails here as it
would fail publication.

Usage: python .github/scripts/check_issues.py cdiscpilot01 [--report PATH]
"""

import argparse
import json
from pathlib import Path

from study_dashboard.issues import Evidence, check_record, declaration_issues
from study_dashboard.rule_review import rule_findings

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("study")
    parser.add_argument("--report", type=Path, help="Default: .build/verification/<study>/report.json")
    args = parser.parse_args()
    path = args.report or ROOT / ".build/verification" / args.study / "report.json"
    verification = json.loads(path.read_text())
    pool, checks, selectors = Evidence(), [], {}
    for finding in rule_findings(args.study, verification, []):
        check, selection = check_record(finding, pool)
        checks.append(check)
        selectors[check["id"]] = selection
    # Only the report's datasets: a single-dataset run says nothing about the others.
    for dataset in verification["datasets"]:
        name = dataset["dataset"]
        path = ROOT / args.study / "spec/review" / f"{name.lower()}-issues.json"
        if not path.is_file():
            print(f"{name}: {len(dataset['findings'])} findings, no authored issues")
            continue
        issues, covered = declaration_issues(path, args.study, checks, selectors, pool)
        print(f"{name}: {len(covered)} of {len(dataset['findings'])} findings in {len(issues)} authored issues")


if __name__ == "__main__":
    main()
