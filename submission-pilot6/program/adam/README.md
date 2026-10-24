# Reproduce the upstream R derivations

`upstream/` contains the unchanged `.Rprofile` and complete `code/` tree from
Pilot 6 commit `a4f85c95cfef1f6aa27795362630f8ae43210185`: 10 ADaM programs,
3 TLF programs and 5 shared utilities. `spec/source-snapshot.json` records
each original path and SHA-256. The importer refreshes and verifies this
code together with the data and specifications.

Pilot 6 starts at SDTM: its repository carries 21 SDTM datasets, not ODM or
CRF-to-SDTM generation programs. TS is not among its tracked inputs.

## Run the verification

Install Python dependencies `pyarrow==26.0.0` and `PyYAML==6.0.3`, and use
R 4.5.1. Restore the R packages from `renv.lock` before running the programs.
From the repository root:

```bash
Rscript -e 'install.packages("renv", repos="https://cloud.r-project.org")'
Rscript -e 'renv::restore(project="submission-pilot6/program/adam", prompt=FALSE)'
python -m unittest discover -s submission-pilot6/program/adam -p 'test_*.py' -v
python submission-pilot6/program/adam/verify_upstream.py --rscript Rscript
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

The runner first verifies all dataset, specification and source-code hashes.
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
generation failure or reference mismatch exits nonzero. This R comparison
is separate from validating Pilot 7's YAMAA specifications.
