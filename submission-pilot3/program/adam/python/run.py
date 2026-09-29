#!/usr/bin/env python3
"""Run the Pilot 3 ADaM yamaa specifications in dependency order."""

from pathlib import Path

from yamaa import yamaa_domain

here = Path.cwd()
project_root = here.parent.parent
specs = [here / f"{name}.yaml" for name in
         ("adsl", "adae", "adadas", "adtte", "adlbc")]

for spec in specs:
    yamaa_domain(spec, project_root=project_root).save()
