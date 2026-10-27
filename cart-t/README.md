# CAR-T for ALL: ODM to SDTM and ADaM with yamaa

This study standardizes the archived CART2020 OpenClinica test export from its
original ODM XML. It produces ten SDTM datasets, nine exploratory ADaM datasets,
SAS XPT exports, separate SDTM and ADaM Define-XML 2.0 files, and dataset QC
logs. The original `.archieve/cart-t/` is unchanged.

SDTM specifications read ODM XML directly. Native yamaa row grouping and
item expressions perform the clinical reshaping. No per-form staging tables
or CSV dataset exports are generated.

Scope is data standardization, metadata and dataset quality checks. Tables,
listings, figures, analysis displays and TLF programs are outside this package.

The datasets are a **review draft**, not submission-ready data. The source
does not provide exposure records, treatment allocation, a full protocol/SAP,
country codes, or MedDRA preferred terms. The workflow exposes these gaps.

## Review the standardized data

On the pull request, open the `Validate cart-t` Actions job and download its
`cart-t-standardization` artifact. Extract the whole artifact to retain the
relative links from Define-XML to its XPT datasets.

Start with [decisions.md](spec/review/decisions.md), executable specifications
under `spec/yamaa/`, and `log/audit.json`. The audit contains source and lineage
checks, unresolved clinical-data queries, and archived row-count differences.
Human review starts as `not_reviewed`; automated checks do not approve
statistical decisions. [The issue #98 assessment](spec/review/issue-98.md)
separates corrected standardization defects from unresolved source gaps.

Data are available as typed Parquet and XPT. For example, in R:

```r
adsl <- arrow::read_parquet("cart-t/data/adam/adsl-yamaa.parquet")
items <- arrow::read_parquet("cart-t/data/odm/items.parquet")
```

## Rebuild from a fresh clone

Run from the repository root. Python 3.12+ and a C compiler are required.
Install Rust 1.99.1 with `rustup toolchain install 1.99.1 --profile minimal`
before the source installation. All pilot studies use the same exact yamaa
source pin; requirements are under `program/adam/python/` for consistency
with the other pilots.

```bash
python3 -m venv .venv
RUSTUP_TOOLCHAIN=1.99.1 .venv/bin/python -m pip install \
  --config-settings build-args=--profile=dev \
  -r cart-t/program/adam/python/requirements.txt
git clone --filter=blob:none --no-checkout \
  https://github.com/elong0527/yamaa.git .build/define-engine
git -C .build/define-engine sparse-checkout set rust/tests/schemas
git -C .build/define-engine checkout --detach \
  1d78496c0cbd4fe89462596a738db3adbd72c8ad
.venv/bin/python cart-t/program/run.py
.venv/bin/python -m unittest discover -s cart-t/program -p 'test_*.py' -v
.venv/bin/python .github/scripts/validate_yamaa.py cart-t
```

No archived RDS, XPT or derived dataset is an input to a clinical derivation.
The audit reads archived XPT only for previous row counts; the issue verifier
reads them only to reproduce the reported data-quality findings.
The build fails on ambiguous ODM scopes, an unsuccessful yamaa run, changed
XPT values/labels/widths, invalid Define-XML, missing artifact links, or failed
source reconciliation. Clinical queries remain unresolved when these
execution and integrity checks pass.

The schema checkout follows the pilot studies' Define-XML validation workflow.
No CDISC schema files are copied into this study. An existing checkout can be
used by setting `YAMAA_XML_SCHEMAS` to its `rust/tests/schemas` directory.

Individual stages can be rerun in dependency order:

```bash
.venv/bin/python cart-t/program/odm/prepare.py
.venv/bin/python cart-t/program/sdtm/run.py
.venv/bin/python cart-t/program/adam/run.py
```

Use the full runner after an edit to refresh XPT, Define-XML and all QC evidence.
To repeat the issue assessment against an existing build:

```bash
.venv/bin/python cart-t/program/verify_issue_98.py
```

## Layout and traceability

```text
cart-t/
  data/
    odm/       staged original XML, reader copy and native item Parquet for QC
    sdtm/      generated DM, SUPPDM, AE, CM, LB, QS, MH, IE, CE, DS
    adam/      generated ADSL, ADAE, ADCM, ADLB, ADQS, ADMH, ADDS, ADIE, ADCE
  program/
    odm/       source staging, encoding compatibility and native item QC inventory
    sdtm/      SDTM stage entry point
    adam/      ADaM stage entry point and pinned Python requirements
    run.py     complete standardization, export and audit
    audit.py   independent source/lineage checks and data-quality queries
    verify_issue_98.py  reproducible assessment of the reported findings
  spec/
    yamaa/     project, terminology, and one executable YAML per dataset
    define/    schema sources and pointers to generated Define-XML packages
    source/    source provenance and form coverage
    review/    standardization decisions and issue assessment
  log/         execution logs, source inventory, audit and issue evidence
```

Each SDTM `--SPID` points to an original item `SourceOrdinal` (LB/QS), or to
the first ordinal of a complete item-group instance (other observation
domains). The group key retains study, metadata version, subject, event and
event repeat, form and form repeat/layout, and item group/repeat. Find an
observation's original values in `data/odm/items.parquet` and the original XML.
ADaM carries `SRCDOM`, `SRCSEQ` and `SRCVAR` for direct trace-back. ADSL obtains
the phenotype from `SUPPDM.RANDPROF`; its inputs are SDTM. `USUBJID` uses the
unique ODM SubjectKey; `DM.SUBJID` retains the study subject ID.

Clinical mappings and reshaping are executable yamaa YAML. The preparation
step stages the unchanged archived XML and creates a reader copy with only
its ASCII encoding declaration normalized to UTF-8. The native item Parquet
is independent QC evidence; no SDTM specification reads it. Subject/site
metadata mappings are checked independently against XML attributes.
The same YAML can execute with the matching yamaa R host after preparation.

Generated data, staged XML and logs are ignored by Git. CI rebuilds and packages
them with the source and specifications. ADaM Parquet files use
`-yamaa.parquet`; generated files are not independent references.

## Define-XML and transport

Canonical definitions are [data/sdtm/define.xml](data/sdtm/define.xml) and
[data/adam/define.xml](data/adam/define.xml), beside their XPT datasets so
relative links work. yamaa composes them from the executable specifications,
with target SDTMIG 3.3 and ADaMIG 1.3 metadata. See
[spec/define/README.md](spec/define/README.md) for the metadata mode and checks.

Reproducibility checks cover values, types, labels and widths. yamaa uses
the snapshot creation time for the direct runner's Define-XML export;
ReadStat timestamps XPT headers when exporting. SAS fixed-width padding makes
trailing blanks indistinguishable; exact source strings remain in XML,
Parquet. Leading blanks and all other characters are checked.

## Responsibilities and tools

Biostatisticians approve populations, baseline, visits, endpoints and analysis
rules. Data stewards resolve source contradictions, coding and missing timing.
AI drafted the specifications and review documentation. yamaa executes clinical
derivations and composes Define-XML. Independent Python/XML and ReadStat checks
test preservation, lineage, schema validity and transport round-trips.

There is no official CAR-T reference comparison, external CDISC conformance
validation, or human statistical sign-off. See the decisions and audit for
remaining work.
