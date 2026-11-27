#!/usr/bin/env python3
"""Compose a cut's define.xml from its reproduced-mode project.

    python scripts/define/compose_define.py mrna-1273-p201/s3-d57/spec/define/project.yaml

Reads the creation time the received document carries from CREATED beside
the project file (Define-XML CreationDateTime; DEFINE-3 makes the bytes a
function of the inputs and this time), composes the `adam` section and saves
it to the project's `define:` path. Prints every issue and exits 1 if the
composition fails.
"""
import sys
from pathlib import Path


def main() -> int:
    import yamaa

    project = Path(sys.argv[1])
    created = (project.parent / "CREATED").read_text().strip()
    sub = yamaa.project(str(project)).submission("adam", created=created)
    issues = sub.issues.to_pylist()
    for i in issues:
        print(f"{i['severity']}: {i['rule']} {i['condition']} {i['spec_paths']} {i['message']}")
    if sub.status != "succeeded":
        print(f"submission {sub.status}: {len(issues)} issue(s)")
        return 1
    sub.save()
    print(f"saved ({len(issues)} issue(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
