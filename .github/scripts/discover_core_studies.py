#!/usr/bin/env python3
"""Discover studies that have datasets CORE can validate, for the matrix.

Mirrors the discovery rule used by check_structure.py: any top-level
directory that does not start with "." and is not in `non_study_dirs`
(from .github/repo-structure.json) is a study. A study is included here
only if it actually holds a validatable dataset -- a `.parquet` or `.xpt`
file under `data/sdtm` or `data/adam` -- so empty scaffolds (kn189, kn564,
which carry only .gitkeep) are skipped and never spawn an empty matrix leg.

Emits `studies=<json-array>` to $GITHUB_OUTPUT (and prints it) so a matrix
job can `fromJSON` it. Adding a new study needs no change here.

Usage:  python3 .github/scripts/discover_core_studies.py [--repo-root .]
No third-party dependencies: standard library only.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

MANIFEST = os.path.join(".github", "repo-structure.json")
DATA_DIRS = ("data/sdtm", "data/adam")
DATA_EXTS = (".parquet", ".xpt")


def discover_studies(root: str, non_study_dirs: list[str]) -> list[str]:
    skip = set(non_study_dirs)
    return sorted(
        name
        for name in os.listdir(root)
        if os.path.isdir(os.path.join(root, name))
        and not name.startswith(".")
        and name not in skip
    )


def has_validatable_data(root: str, study: str) -> bool:
    for rel in DATA_DIRS:
        d = os.path.join(root, study, rel)
        if not os.path.isdir(d):
            continue
        for ext in DATA_EXTS:
            if glob.glob(os.path.join(d, f"*{ext}")):
                return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    root = os.path.abspath(args.repo_root)

    manifest_path = os.path.join(root, MANIFEST)
    non_study_dirs: list[str] = []
    if os.path.isfile(manifest_path):
        with open(manifest_path, encoding="utf-8") as fh:
            non_study_dirs = json.load(fh).get("non_study_dirs", [])

    studies = [
        s for s in discover_studies(root, non_study_dirs)
        if has_validatable_data(root, s)
    ]

    payload = json.dumps(studies)
    print(f"Studies with CORE-validatable data: {studies}")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"studies={payload}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
