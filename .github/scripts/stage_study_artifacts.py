#!/usr/bin/env python3
"""Transfer verified generated outputs between validation and publication jobs."""

import argparse
import json
from pathlib import Path
import shutil

from study_artifacts import verify_artifacts


def stage(root, study, destination, report):
    """Keep repository-relative paths and exact bytes; never recompute results."""
    if report["status"] == "pending":
        return
    if report["status"] != "succeeded":
        raise ValueError(f"{study}: cannot stage failed validation")
    verify_artifacts(root, study, report)
    for relative in report["artifacts"]["files"]:
        path = Path(relative)
        if path.parts[:3] == (study, "data", "adam") and path.name.endswith(
            "-yamaa.parquet"
        ):
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / path, target)
    verify_artifacts(root, study, report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    report = json.loads((root / ".build/validation" / f"{args.study}.json").read_text())
    stage(root, args.study, root / ".build/derived", report)
