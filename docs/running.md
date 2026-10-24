# Run the derivations

## Install the pinned engine

Use **Python 3.12 or later**, Rust/Cargo **1.82 or later**, and your
platform's C/C++ build tools. The current yamaa 1.0 interface is unreleased,
so the requirements install a specific source commit instead of the older
published 0.5.0 package. Installing from source compiles the Rust engine.

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\Activate.ps1` in PowerShell.

Each study pins its engine revision and comparison dependencies in its own
`program/adam/python/requirements.txt`. The root
[`requirements.txt`](https://github.com/RConsortium/submissions-pilot7-synthetic-data/blob/main/requirements.txt)
includes the three merged study files, so pip checks that their requirements agree.
Pilot 6 uses its own requirements file when its project is available.
Each study can be installed independently.

## Build and verify a study

```bash
python .github/scripts/validate_yamaa.py cdiscpilot01
python .github/scripts/validate_yamaa.py submission-pilot3
python .github/scripts/validate_yamaa.py submission-pilot5
python .github/scripts/validate_yamaa.py submission-pilot6
```

For a merged project, each command checks the study without data, builds and saves its
active datasets, and runs its existing official comparator when available.
Evidence is written to `.build/validation/<study>.json`. A check, build, or
comparison failure exits nonzero. Pilot 6 reports `pending` before its project is merged. Afterward, it reports
an unavailable reference explicitly and runs its comparator once a reference
Parquet file is present.

To build alone, use the study runner:

```bash
python submission-pilot3/program/adam/python/run.py
```

Runners resolve paths from their own files, so they work from the repository
root or any other working directory. Derived files are named
`<study>/data/adam/<dataset>-yamaa.parquet` and are ignored by Git. Official
reference files are preserved.

## Use the project API

```python
from pathlib import Path
import yamaa

project = yamaa.project(
    Path("submission-pilot3/spec/yamaa/project.yaml")
)
print(project.check())
runs = project.run("adam")
print(runs)
runs.save()
```

Project files list the specifications in dependency order. A derived input
names its producing specification through `schema`; project runs build
producers before consumers. Inputs and outputs are resolved relative to
their declaring YAML files.

## Build this website

First validate all four studies with the commands above. Then:

```bash
python -m pip install -r docs/requirements.txt
python .github/scripts/build_study_docs.py
python -m mkdocs build --strict
```

Generated study pages and JSON evidence come from those validation results.
They are not edited or committed. GitHub Actions performs the same checks,
builds the strict site, and uploads a `pilot7-site` artifact on pull requests.
On `main`, the workflow also deploys to GitHub Pages.

For the initial publication, a repository administrator must select
**Settings → Pages → Build and deployment → Source: GitHub Actions**.
No custom domain is needed. The target URL is
<https://rconsortium.github.io/submissions-pilot7-synthetic-data/>.
