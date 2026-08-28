#!/usr/bin/env python3
"""Check the repository folder structure against .github/repo-structure.json.

Every study folder is expected to expose the same stage-based layout:

    <study>/data/{odm,sdtm,adam}      datasets, by stage
    <study>/program/{odm,sdtm,adam}   derivation code, by stage
    <study>/tlf                       reporting outputs

Studies are discovered, not listed: any top-level directory that does not
start with "." and is not named in `non_study_dirs` is treated as a study.
Adding a new study therefore needs no change to this script or the manifest.

Two severities:

  error   -- unambiguous breakage; fails the job.
             A missing required folder, an empty folder with no .gitkeep to
             keep git tracking it, a forbidden nesting such as data/data, a
             file extension outside its declared home, or a non-ASCII byte
             in a file listed as ASCII-only.

  warning -- annotated but does not fail. An unexpected extra folder is
             usually a deliberate new stage; when it becomes part of the
             template, add it to `study.required` in the manifest.

Usage:  python3 .github/scripts/check_structure.py [--repo-root .]
        Add --strict to fail on warnings too.
No third-party dependencies: standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

MANIFEST = os.path.join(".github", "repo-structure.json")

errors: list[tuple[str, str]] = []    # (path, message)
warnings: list[tuple[str, str]] = []


def error(path: str, message: str) -> None:
    errors.append((path, message))


def warn(path: str, message: str) -> None:
    warnings.append((path, message))


def annotate(level: str, path: str, message: str) -> None:
    """Emit a GitHub Actions annotation, or a plain line when run locally."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::{level} file={path}::{message}")
    else:
        print(f"{level:7} {path}: {message}")


def discover_studies(root: str, non_study_dirs: list[str]) -> list[str]:
    """Top-level directories that are not dot-directories and not excluded.

    Dot-directories (.github, .automation, .archieve, .git) are skipped by
    the leading-dot rule, so archiving a study by renaming it out of the way
    also removes it from this check.
    """
    skip = set(non_study_dirs)
    return sorted(
        name
        for name in os.listdir(root)
        if os.path.isdir(os.path.join(root, name))
        and not name.startswith(".")
        and name not in skip
    )


def is_effectively_empty(path: str) -> bool:
    """True when a directory holds nothing but placeholder/OS cruft."""
    ignorable = {".gitkeep", ".DS_Store"}
    return all(entry in ignorable for entry in os.listdir(path))


def check_study(root: str, study: str, spec: dict) -> None:
    required = spec["required"]
    forbidden = spec["forbidden"]

    for rel in required:
        path = os.path.join(study, rel)
        abspath = os.path.join(root, path)
        if not os.path.isdir(abspath):
            error(path, f"required folder is missing (expected {rel}/ in every study)")
            continue
        # Git does not track empty directories: without a .gitkeep the folder
        # disappears on a fresh clone, silently and invisibly in review.
        if is_effectively_empty(abspath) and not os.path.isfile(
            os.path.join(abspath, ".gitkeep")
        ):
            error(path, "folder is empty and has no .gitkeep, so git will not track it")

    for rel in forbidden:
        path = os.path.join(study, rel)
        if os.path.isdir(os.path.join(root, path)):
            error(path, f"forbidden nesting: {rel} duplicates its parent")

    # Anything outside the template is reported, not blocked -- a new stage
    # folder is a manifest change, not a mistake.
    expected_dirs = set(required)
    for rel in required:
        parts = rel.split("/")
        for i in range(1, len(parts)):
            expected_dirs.add("/".join(parts[:i]))

    for dirpath, dirnames, _ in os.walk(os.path.join(root, study)):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        rel_dir = os.path.relpath(dirpath, os.path.join(root, study))
        depth = 0 if rel_dir == "." else len(rel_dir.split("/"))
        if depth >= 2:  # only police the template's own two levels
            dirnames[:] = []
            continue
        for d in dirnames:
            rel = d if rel_dir == "." else f"{rel_dir}/{d}"
            if rel not in expected_dirs:
                warn(
                    f"{study}/{rel}",
                    "folder is not part of the study template; add it to "
                    "study.required in .github/repo-structure.json if it should be",
                )


def check_extension_locations(root: str, studies: list[str], rules: dict) -> None:
    """Datasets of a given extension must live in a declared folder."""
    for ext, allowed in rules.items():
        for study in studies:
            allowed_abs = {
                os.path.normpath(os.path.join(root, study, rel)) for rel in allowed
            }
            for dirpath, dirnames, filenames in os.walk(os.path.join(root, study)):
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                if os.path.normpath(dirpath) in allowed_abs:
                    continue
                for name in filenames:
                    if name.lower().endswith(ext):
                        rel = os.path.relpath(os.path.join(dirpath, name), root)
                        error(
                            rel,
                            f"{ext} files belong in "
                            + " or ".join(f"{study}/{a}/" for a in allowed),
                        )


def check_ascii(root: str, paths: list[str]) -> None:
    for rel in paths:
        abspath = os.path.join(root, rel)
        if not os.path.isfile(abspath):
            error(rel, "listed in ascii_only_files but does not exist")
            continue
        with open(abspath, "rb") as fh:
            data = fh.read()
        offenders = {}
        line = 1
        for byte in data:
            if byte == 0x0A:
                line += 1
            elif byte > 0x7F:
                offenders.setdefault(line, 0)
                offenders[line] += 1
        if offenders:
            shown = ", ".join(
                f"line {ln} ({n})" for ln, n in sorted(offenders.items())[:5]
            )
            more = "" if len(offenders) <= 5 else f" and {len(offenders) - 5} more"
            error(
                rel,
                f"must be ASCII only; non-ASCII bytes on {shown}{more}. "
                "Use +-- and | for trees, -> for arrows, - for dashes",
            )


def write_summary(studies: list[str], strict: bool) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("## Folder structure check\n\n")
        fh.write(f"Studies checked: {', '.join(f'`{s}`' for s in studies)}\n\n")
        if not errors and not warnings:
            fh.write("All checks passed.\n")
            return
        fh.write("| Severity | Path | Finding |\n|---|---|---|\n")
        for path_, msg in errors:
            fh.write(f"| error | `{path_}` | {msg} |\n")
        for path_, msg in warnings:
            fh.write(f"| warning | `{path_}` | {msg} |\n")
        fh.write("\n")
        if warnings and not strict:
            fh.write("Warnings do not fail this job.\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--strict", action="store_true", help="treat warnings as errors"
    )
    args = parser.parse_args()
    root = os.path.abspath(args.repo_root)

    manifest_path = os.path.join(root, MANIFEST)
    if not os.path.isfile(manifest_path):
        print(f"error: manifest not found at {MANIFEST}", file=sys.stderr)
        return 2
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)

    studies = discover_studies(root, manifest.get("non_study_dirs", []))
    if not studies:
        print(
            "error: no study folders discovered -- check non_study_dirs in "
            f"{MANIFEST}",
            file=sys.stderr,
        )
        return 2

    print(f"Studies discovered: {', '.join(studies)}")
    for study in studies:
        check_study(root, study, manifest["study"])
    check_extension_locations(
        root, studies, manifest.get("extension_locations", {})
    )
    check_ascii(root, manifest.get("ascii_only_files", []))

    for path_, msg in errors:
        annotate("error", path_, msg)
    for path_, msg in warnings:
        annotate("warning", path_, msg)

    write_summary(studies, args.strict)

    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    if errors or (args.strict and warnings):
        return 1
    print("Folder structure OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
