# CAR-T for ALL: ODM to SDTM and ADaM with yamaa

This study rebuilds the archived CART2020 OpenClinica test export from its
original ODM XML. It produces ten SDTM datasets, nine exploratory ADaM datasets,
SAS XPT review exports, and separate SDTM and ADaM Define-XML 2.0 files.
The original `.archieve/cart-t/` is unchanged.

The package is a **review draft**, not a submission-ready study. The source
does not provide exposure records, treatment allocation, a full protocol/SAP,
country codes, or MedDRA preferred terms. The workflow exposes those gaps
instead of manufacturing values to pass a conformance check.

## Start a statistical review

On the pull request, open the `Validate cart-t` Actions job and download its
`cart-t-review` artifact. Extract the whole artifact, then open
`cart-t/tlf/review.html` in a browser. Keep the extracted folders together so
CSV, XPT, Define-XML and documentation links work. No web server is required.

The workbook provides searchable records, subject IDs, variable derivations,
SDTM-to-ADaM links, original CRF item values, review queries and archived row
counts. Human review starts as `not_reviewed`; automated checks do not approve
statistical decisions. Review [decisions.md](spec/review/decisions.md) before
interpreting population flags or analysis timing.

For local work, run the command below and open [the workbook](tlf/review.html).
Data are also available as CSV and typed Parquet. For example, in R:

```r
adsl <- read.csv("cart-t/data/adam/adsl-yamaa.csv", na.strings = "")
# Or, retaining analysis-date types:
adsl <- arrow::read_parquet("cart-t/data/adam/adsl-yamaa.parquet")
```

## Rebuild from a fresh clone

Run from the repository root. Python 3.12+ and a C compiler are required.
Install Rust 1.99.1 with `rustup toolchain install 1.99.1 --profile minimal`
before the source installation. All studies use the same exact yamaa source
pin; the Python requirements are under `program/adam/python/` for consistency
with the other pilot studies.

```bash
python3 -m venv .venv
RUSTUP_TOOLCHAIN=1.99.1 .venv/bin/python -m pip install \
  --config-settings build-args=--profile=dev \
  -r cart-t/program/adam/python/requirements.txt
.venv/bin/python cart-t/program/run.py
.venv/bin/python -m unittest discover -s cart-t/program -p 'test_*.py' -v
.venv/bin/python .github/scripts/validate_yamaa.py cart-t
```

No archived RDS, XPT or derived dataset is an input to a clinical derivation.
The audit reads archived XPT files only to report previous row counts.
The full build fails on extraction ambiguity, an unsuccessful yamaa run,
changed XPT values/labels/widths, invalid Define-XML, missing artifact links,
or failed source reconciliation. Clinical data queries remain visible even
when these execution and integrity checks pass.

Individual stages can be rerun in dependency order:

```bash
.venv/bin/python cart-t/program/odm/extract.py
.venv/bin/python cart-t/program/sdtm/run.py
.venv/bin/python cart-t/program/adam/run.py
```

Use the full runner after an edit to refresh XPT, Define-XML, the audit and
the workbook. `--build-only` omits HTML; `--review-only` renders the current
successful build for the CI review artifact.

The optional browser regression check uses Playwright and an installed
Chromium/Chrome (or Playwright's Chromium):

```bash
.venv/bin/python -m pip install -r .github/tests/dashboard/requirements.txt
.venv/bin/python cart-t/program/check_workbook.py
```

## Layout and traceability

```text
cart-t/
  data/
    odm/       original XML, generated item table and per-form CSV extracts
    sdtm/      generated DM, SUPPDM, AE, CM, LB, QS, MH, IE, CE, DS
    adam/      generated ADSL, ADAE, ADCM, ADLB, ADQS, ADMH, ADDS, ADIE, ADCE
  program/
    odm/       native yamaa ODM reader and lossless OpenClinica reshaping
    sdtm/      SDTM stage entry point
    adam/      ADaM stage entry point and pinned Python requirements
    run.py     complete build, export, audit and review rendering
  spec/
    yamaa/     project, terminology, and one executable YAML per dataset
    define/    schema sources and pointers to generated Define-XML packages
    source/    source provenance and form coverage
    review/    statistical decisions and human review checklist
  tlf/         generated standalone review workbook; no inferential TLFs
  log/         per-dataset logs/reports, source inventory, audit and run manifest
```

Each SDTM `--SPID` points to an original item `SourceOrdinal` (LB/QS), or to
the first ordinal of a complete item-group instance (other observation
domains). The group key retains study, metadata version, subject, event and
event repeat, form and form repeat/layout, and item group/repeat. ADaM carries
`SRCDOM`, `SRCSEQ` and `SRCVAR` for direct trace-back. ADSL obtains the phenotype
from `SUPPDM.RANDPROF`, so its inputs are SDTM rather than a separate raw-data
shortcut. `USUBJID` uses the unique ODM SubjectKey; `DM.SUBJID` retains the
human-readable study subject ID.

All clinical mappings are executable yamaa YAML. The extraction adapter only
reads metadata, preserves values and pivots complete source instances. The
Python orchestration/export layer does not calculate analysis variables.
The same YAML can be executed with the matching yamaa R host after extraction.

Generated data, XML definitions, HTML and logs are deliberately ignored by Git.
They are rebuilt in CI and included together in the review artifact. ADaM
Parquet files use `-yamaa.parquet`; no generated file is presented as an
independent reference.

## Define-XML and transport

Canonical definitions are [data/sdtm/define.xml](data/sdtm/define.xml) and
[data/adam/define.xml](data/adam/define.xml), beside their XPT datasets so
relative dataset links work. They are composed by yamaa from the executable
specifications, with target SDTMIG 3.3 and ADaMIG 1.3 metadata. See
[spec/define/README.md](spec/define/README.md) for the metadata mode and checks.

Reproducibility is assessed on values, types, labels and widths. yamaa uses
the snapshot creation time for the direct runner's Define-XML export;
ReadStat timestamps XPT headers when exporting. SAS fixed-width padding makes
trailing blanks indistinguishable; exact source strings remain in XML,
Parquet and CSV. Leading blanks and all other characters are checked.

## Responsibilities and tools

Biostatisticians approve populations, baseline, visits, endpoints and analysis
rules. Data stewards resolve source contradictions, coding and missing timing.
AI drafted the specifications and review materials. yamaa executes clinical
derivations and composes Define-XML. Independent Python/XML and ReadStat checks
test preservation, lineage, schema validity and transport round-trips.

There is no official reference comparison, independent CORE validation, or
human sign-off claim. The retained archive is historical implementation
evidence; count agreement is not data agreement or regulatory validation.
