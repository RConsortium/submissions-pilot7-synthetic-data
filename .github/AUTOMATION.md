# Repository automation

| Workflow | Responsibility | Writes |
| --- | --- | --- |
| `ci.yml` | One shared check job on every PR; only affected studies get additional validation jobs. | Layout-preview and validation artifacts only. |
| `study-check.yml` | Reusable per-study yamaa, R, and/or CORE checks. Multiple checks for one study share one runner; CORE reads committed data before derivations run. | Validation artifacts only. |
| `adam-compare.yml` | Manual generic ADaM comparison using workflow inputs. | None. |
| `core-validate.yml` | Full CORE checks on relevant main pushes or manual runs. | Validation artifacts only. |
| `yamaa-site.yml` | Fresh validation of the full publication catalog, then website build. Runs on main or manually. | GitHub Pages on main in the upstream repository. |

## PR scope

`ci_scope.py` selects checks from the complete merge-base-to-head Git diff.
Renames include both paths, deleted inputs remain in scope, and selection has no
API file-count limit. The always-present `structure-check` job runs structure,
ASCII, tooling tests, and whitespace checks; optional small checks run as steps
in that same job.

| Changed files | Additional work | Runner jobs for a single-study PR |
| --- | --- | ---: |
| Prompts, READMEs, agent guides, generated CORE reports | None. | 1 |
| Site prose, general CSS, or MkDocs config | Strict layout/link preview in the shared job. | 1 |
| A study's yamaa specs or Python runner/comparator | Build and compare that study. | 2 |
| A study's SDTM/ADaM binary data | yamaa comparison and CORE in one study job. | 2 |
| A study's R program | Run R with the pinned engine and compare outputs. | 2 |
| Pilot 3 planning generator or its QS/EX/plan.csv inputs | Relevant Python/R plan reproduction steps in the shared job. Input data changes also select the study job. | 1 or 2 |
| Generic comparison tool or its keys | Comparator self-check in the shared job. | 1 |
| Dashboard code, tests, configuration, synthetic source archives, or study source documents | Full catalog validation, strict production build, module and browser tests. | Catalog + 2 |
| Shared execution code or the reusable worker | Every affected study; each study still uses one runner. | Depends on scope |

PR site previews use an isolated docs tree with explicit placeholders for study
results. They assert no dataset builds or comparisons and are never deployed.
Publication on main requires fresh reports and the exact validated output bytes
for the complete catalog from that same commit. The artifact inventory rejects
post-validation changes, additions, and deletions, including ignored outputs.
Changes to dashboard publication code, tests, source documents, or the shared study worker also run the complete
publication path on the PR using fresh study artifacts; allowed pending studies
get explicit pending records without installing an engine.
MkDocs renders the landing-page metrics from those same validated reports and
the staged reference Parquet dimensions. The source Markdown retains a link to
the live website, without a numeric snapshot. Layout previews omit metrics.
Planning checks compare against `data/mapping/plan.csv`; the separate
`analysis_window.csv` lookup selects study validation, not plan regeneration.

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
generic comparator's reference-versus-itself self-check, only when those
checks are in scope. These checks do not establish agreement between derived data and official references.

For study validation and website checks, follow root `AGENTS.md`. Keep each
study's pinned requirements and existing comparison policy. The publication
workflow checks ASCII again after generation and rejects incomplete, failed, stale,
or artifact-mismatched evidence. The production architecture and extension guide
is in `scripts/study_dashboard/README.md`.

## CORE runner and reports

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
Reports, dataset comments, and execution records stay in those artifacts.
CORE validation does not open report PRs, post comments, or add labels to issues.

Human review uses the downloaded reports and execution records. External agent
routines and their migration steps are documented in `.automation/README.md`.
