#!/usr/bin/env python3
"""Build and save this study's ADaM datasets with the pinned yamaa engine."""
from pathlib import Path

import yamaa

study = Path(__file__).resolve().parents[3]
runs = yamaa.project(study / "spec" / "yamaa" / "project.yaml").run("adam")
print(runs)
runs.save()
