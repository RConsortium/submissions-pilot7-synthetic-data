# Reproduce the upstream R derivations

`upstream/` contains 14 unchanged source files from Pilot 6 commit
`a4f85c95cfef1f6aa27795362630f8ae43210185`: the `.Rprofile`, all 10 ADaM
programs, and 3 utilities for dataset I/O and comparison.
`spec/source-snapshot.json` records each original path and SHA-256. The
importer refreshes and verifies this code with the data and specifications.
It selects data-standardization programs and utilities explicitly.

Pilot 6 starts at SDTM: its repository carries 21 SDTM datasets, not ODM or
CRF-to-SDTM generation programs. TS is not among its tracked inputs.

## Run the verification

Use the pinned Python dependencies in `python/requirements.txt` and R 4.5.1.
Restore the R packages from `renv.lock` before running the programs.
From the repository root:

```bash
python -m pip install -r submission-pilot6/program/adam/python/requirements.txt
Rscript -e 'install.packages("renv", repos="https://cloud.r-project.org")'
Rscript -e 'renv::restore(project="submission-pilot6/program/adam", prompt=FALSE)'
python -m unittest discover -s submission-pilot6/program/adam/python -p 'test_*.py' -v
python submission-pilot6/program/adam/python/verify_upstream.py --rscript Rscript
```

`Pilot 6 upstream R reproduction` GitHub Actions workflow installs the R
environment from the same lockfile and runs this verification on the
study's pull requests. Each fresh R process explicitly loads the restored
renv project. No Docker image is required.

The lockfile pins datasetjson's native reader to Git commit
`0d4a6ac11ac4224868a0c405ed52a8478cc4ec78` from
`atorus-research/datasetjson`. The startup script accepts the legacy
`decimals_as_floats = TRUE` argument used by upstream and delegates to the
native reader, which already decodes numeric columns as floating-point
values. An exact numeric precision probe runs before derivations. Upstream
does not provide its own lockfile; this repository records the tested environment.
CRAN package records use renv's `Repository` source without pak's `any`
remote metadata, so cold restores can retrieve the pinned versions.

As in Pilot 3, Python programs live in `python/`, R startup lives in `R/`,
and published Define-XML lives in `spec/define/` under the study root. The
unchanged imported source stays in `upstream/`; `renv.lock` stays at the
ADaM project root.

The runner requires all 21 named SDTM inputs, all 8 named ADaM references,
both upstream specifications, and all 14 retained source files before it
verifies their hashes. Missing or duplicate manifest entries fail verification.
It converts the staged SDTM Parquet files to Dataset-JSON for the R reader,
preserving values, blanks, nulls, types and labels; numeric columns use JSON
float metadata. It then creates a fresh sandbox with an empty ADaM folder.
Each program runs in a fresh R process after loading the upstream profile,
shared JSON writer, metatools and xportr. The latter two supply functions
some programs expect from a shared interactive R session. No upstream
derivation code is changed. The compatibility reader adapts the retired
argument only; it does not modify clinical values or derivation rules.

ADSL runs first. The other programs consume only freshly generated parent
datasets, with ADAE before ADTTE and ADLBC before ADLBHY. A failed parent
blocks its dependents. Official references are never copied into the
sandbox or substituted for failed outputs.

The runner compares generated data with all 8 staged ADaM references using
original row and column order, exact types, labels, text, dates and nulls,
and an absolute numeric tolerance of `1e-10`. ADCIBC and ADLBHY have
upstream programs but no stored upstream references, so successful builds
are reported as `reference_unavailable`, rather than matched.

Results go to `log/upstream-verification.json`; complete per-program logs
and generated files stay under ignored `.build/pilot6-upstream/`. GitHub
Actions uploads the report and logs as `pilot6-upstream-evidence`. Any
generation failure, missing required reference, or reference mismatch exits
nonzero. A derivation timeout saves partial stdout/stderr, marks the dataset
failed, blocks its children, and still writes the final report. This R comparison
is separate from validating Pilot 7's yamaa specifications.

## Recorded verification

[GitHub Actions run 40145768527](https://github.com/RConsortium/submissions-pilot7-synthetic-data/actions/runs/40145768527)
restored the committed lockfile and passed the exact input precision probe.
The [machine-readable report](../../log/upstream-verification.json) binds
these historical results to the source snapshot, R runner, bootstrap and
lockfile hashes tested at that commit. The report predates the Pilot 3 folder
layout and inventory/timeout safeguards; CI produces fresh evidence for the
updated runner without rewriting the historical report.
It also records the actual package versions. The run staged all 21 SDTM
inputs; individual programs select the domains they need.

Nine of the ten upstream programs generated output. Five of the eight
stored reference datasets matched. The remaining results require review:

| Dataset | Generated rows | Reference comparison |
| --- | ---: | --- |
| ADSL | 254 | Matched |
| ADAE | 1,191 | Matched |
| ADADAS | 12,463 | Matched |
| ADLBC | 37,132 | Matched |
| ADLBH | - | Export failed |
| ADNPIX | 2,360 | Different |
| ADVS | 32,139 | Matched |
| ADTTE | 254 | Different |
| ADLBHY | 9,954 | Reference unavailable |
| ADCIBC | 730 | Reference unavailable |

- ADLBH reaches export but produces NaN or infinite numeric values, which
  the Dataset-JSON writer rejects. Its reference comparison did not run.
- ADNPIX generates 2,360 rows; its stored reference contains 31,140.
- ADTTE differs in 152 EVNTDESC cells: the program writes
  `Dermatologic Event Occurred`, while the reference contains
  `Dematologic Event Occured`. The other columns match.
- Upstream has no stored ADLBHY or ADCIBC reference, so generation alone
  cannot establish reference agreement for those datasets.

The workflow exits nonzero for the export failure and reference differences.
Official references and upstream derivation programs have been preserved.
The CI artifact includes the full logs, report, lockfile and generated JSON.
