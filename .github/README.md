# Repository automation

| Workflow | Responsibility | Writes |
| --- | --- | --- |
| `ci.yml` | Structure, ASCII, all tooling tests, Pilot 3 plan reproducibility, comparator self-check. Runs on every PR and push to main. | None. |
| `adam-compare.yml` | Manual generic ADaM comparison using workflow inputs. | None. |
| `core-validate.yml` | CORE checks on committed study datasets; report artifacts and issue findings. | On main only: a `core/reports` PR and issue comments. |
| `yamaa-site.yml` | Build the cataloged studies, compare against independent references, validate evidence, and build the website. | GitHub Pages on main in the upstream repository. |

The folder template is `repo-structure.json`. `check_structure.py` owns directory
discovery, reused by CORE discovery; empty study scaffolds remain structure-only.
`yamaa-studies.json` defines the publication catalog and supplies the yamaa matrix.
The dedicated `check_ascii.py` owns ASCII policy and reference exceptions.

## Local checks

Use Python 3.12 or newer, PyYAML, and `jq` for the tooling test suite:

```bash
python3 .github/scripts/check_structure.py
python3 .github/scripts/check_ascii.py
python3 -m unittest discover -s .github/scripts -p 'test_*.py' -v
git diff --check
```

CI also installs Polars for the Pilot 3 plan reproduction and PyArrow for the
generic comparator's reference-versus-itself self-check. These checks do not
establish agreement between derived data and official references.

For study validation and website checks, follow root `AGENTS.md`. Keep each
study's pinned requirements and existing comparison policy. The website checks
ASCII again after generation and rejects incomplete, failed, or stale evidence.

## CORE runner and delivery

On Linux, install `pyarrow`, `pandas`, `pyreadstat`, and `jq`, then run:

```bash
python3 .github/scripts/run_core.py cdiscpilot01
```

The runner downloads the pinned Linux release into `.build/core-bin`. Engine,
standard, and CT settings live at the top of `scripts/run_core.py`; the CI cache
key includes that file. The runner retains the existing CT fallback policy and
records the actual packages used. `--core-dir` accepts an existing engine cache;
`--output` changes the report staging directory (default `.build/core-reports`).

Each `core-reports-<study>` artifact contains:

```text
<study>/data/{sdtm,adam}/
  core-report-<SDTM|ADAM>.json
  core-report-<SDTM|ADAM>.xlsx
  dataset_comment.md
  core-execution.json
```

Execution records include input, prepared, skipped, and report-covered datasets,
CT packages, rule count, and engine exit status. No-rules reports remain
conformance UNVERIFIED. Nonzero engine exit status is recorded separately from
report generation; findings alone do not fail this workflow. Missing or invalid
expected JSON reports and total conversion failures fail the job. Partial
conversion remains explicit and does not become a clean pass.

Artifacts are retained for 90 days, including available records on failed runs.
Only successful validation jobs can deliver reports. The report PR copies only
XLSX and `dataset_comment.md`; JSON stays artifact-only. The issue-comment job
uses the same renderer and keys deduplication on the workflow run ID.

Report PRs require the repository setting that allows Actions to create PRs.
Human review and merge remain separate from engine execution and automated
checks. External agent routines and their migration steps are documented in
`.automation/README.md`.
