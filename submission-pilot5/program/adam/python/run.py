#!/usr/bin/env python3
"""Build and save this study's ADaM datasets with the pinned yamaa engine."""
from pathlib import Path
import sys

import yamaa

study = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(study.parent / ".github/scripts"))
from resolved_specs import execution_project, process_study

process_study(study.parent, study.name, check=True)
runs = yamaa.project(execution_project(study.parent, study.name)).run("adam")
print(runs)
runs.save()
