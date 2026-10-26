#!/usr/bin/env python3
"""Generate the production study dashboard from fresh, artifact-bound evidence."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from study_evidence import (
    catalog,
    reviewed_datasets,
    validate_reports,
    validate_verifications,
)
from study_artifacts import verify_report_artifacts
from study_dashboard.artifacts import build_bundle
from study_dashboard.pages import report_page, study_page

ROOT = Path(__file__).resolve().parents[2]


def load_verifications(root, entries, reports, verification_dir):
    """Documented-rule reports for studies with reviewed datasets, as CI staged them."""
    found = {}
    for name in entries:
        if reports[name]["status"] == "pending" or not reviewed_datasets(root, name):
            continue
        path = verification_dir / name / "report.json"
        if path.is_file():
            found[name] = json.loads(path.read_text())
    return found


def generate(root, reports_dir, expected_commit=None, verification_dir=None):
    """Prepare everything before promoting any generated production content."""
    root, reports_dir = Path(root), Path(reports_dir)
    verification_dir = Path(verification_dir or root / ".build/verification")
    entries = catalog(root)
    revision = (
        expected_commit
        or subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
    )
    reports = {
        name: json.loads((reports_dir / f"{name}.json").read_text()) for name in entries
    }
    validate_reports(root, entries, reports, revision)
    verify_report_artifacts(root, entries, reports)
    verifications = load_verifications(root, entries, reports, verification_dir)
    validate_verifications(root, entries, reports, verifications, revision)
    work = root / ".build"
    work.mkdir(exist_ok=True)
    evidence = root / "docs/evidence"
    pages = root / "docs/studies"
    evidence.mkdir(parents=True, exist_ok=True)
    pages.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dashboard-", dir=work) as temporary:
        stage = Path(temporary)
        build_bundle(root, stage / "dashboard", entries, reports, revision, verifications)
        staged_pages = {
            name: study_page(name, entry, reports[name])
            for name, entry in entries.items()
        }
        index = report_page(stage / "dashboard")
        # Verify again after reading and rendering: mutable outputs cannot acquire
        # an old successful label, including when a file changes during export.
        verify_report_artifacts(root, entries, reports)
        current = evidence / "dashboard"
        backup = stage / "previous"
        if current.exists():
            current.rename(backup)
        try:
            (stage / "dashboard").rename(current)
        except OSError:
            if backup.exists():
                backup.rename(current)
            raise
        for name, page in staged_pages.items():
            (pages / f"{name}.md").write_text(page)
            shutil.copyfile(reports_dir / f"{name}.json", evidence / f"{name}.json")
        (pages / "index.md").write_text(index)
        for old in evidence.glob("*.json"):
            if old.stem not in entries:
                (pages / f"{old.stem}.md").unlink(missing_ok=True)
                old.unlink()
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=ROOT / ".build/validation")
    parser.add_argument("--verification", type=Path, default=ROOT / ".build/verification")
    args = parser.parse_args()
    result = generate(ROOT, args.reports, os.environ.get("GITHUB_SHA"), args.verification)
    print(f"Generated production study dashboard: {result}")


if __name__ == "__main__":
    main()
