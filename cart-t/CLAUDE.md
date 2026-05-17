# CART-T Pilot — Project Conventions

Durable conventions for this submission-pilot project. Future sessions
should treat this file as the source of truth on **how** to do work here;
the IG knowledge files (`spec/ig/knowledge_sdtm_ig.md`,
`spec/ig/knowledge_adam_ig.md`) are the source of truth on **what** the
standards require.

## Project layout

```
cart-t/
├─ car-t-openclinica.xml          # Source ODM XML export from OpenClinica
├─ data/
│  ├─ raw/                        # One .rds per CRF form + flat.rds + README.md
│  ├─ sdtm/                       # One .rds per SDTM domain
│  └─ adam/                       # One .rds per ADaM dataset
├─ program/
│  ├─ raw/                        # XML loader + per-form split (load_xml.R, ut_load_xml.R, ut_load_xml_2.R)
│  ├─ sdtm/                       # SDTM domain build programs
│  └─ adam/                       # ADaM dataset build programs
└─ spec/
   ├─ ig/                         # Downloaded IGs + knowledge_*.md navigation maps
   ├─ sdtm/                       # YAML specs, one per domain + _index.yaml
   └─ adam/                       # YAML specs, one per dataset + _index.yaml
```

## Environment

- This is an **renv** project. `xml2`, `tibble`, `tidyr`, `dplyr` are
  already present; install any new package via `renv::install()` and
  snapshot with `renv::snapshot()`.
- R version is whatever `renv/activate.R` boots; do not change.
- Run scripts from the project root: `Rscript program/<area>/<file>.R`.

## Raw data flow

1. Source: `car-t-openclinica.xml` (OpenClinica ODM export).
2. `program/raw/ut_load_xml.R` defines the loader. `ut_load_xml_2.R` is
   the optimized drop-in replacement (single XPath + `xml_ns_strip` +
   vectorised attribute extraction).
3. `program/raw/load_xml.R` runs the loader, writes `data/raw/flat.rds`
   (48,557 rows × 34 cols, one row per `ItemData`), then splits by
   `formname` using the **short-slug map** in that script. Form
   long-name → slug is documented in `data/raw/README.md` and `_index.yaml`.

## Shared SDTM helpers — `program/sdtm/ut_visits.R`

Every SDTM (and ADSL) program sources this file. It centralises four
things that would otherwise drift if each program duplicated them.

| Helper | Purpose |
|---|---|
| `visit_map` (named vector) | `studyeventoid` → integer VISITNUM. Update this whenever a new OpenClinica event is added. |
| `derive_visitnum(studyeventoid)` | Vectorised lookup. **Do not** coerce `studyeventoid` to numeric directly — values are text like `"SE_BASELINE"`. |
| `make_usubjid(studysubjectid)` | Returns `"CART-T-PILOT-01-<studysubjectid>"`. Single source of truth for the USUBJID format. |
| `armcd_map(profile)` / `arm_map(profile)` | See "Study-specific decisions" below. |
| `phenotype_code(profile)` / `phenotype_label(profile)` | NHM / NHF / HM / HF for stratification — feeds `ADSL.STRAT1` / `STRAT1L`. |
| `normalize_iso_date(x)` | Coerces mixed raw date formats to ISO 8601 `yyyy-mm-dd`. **Required before passing dates into admiral** because the raw CRF mixes ISO (`2024-03-07`), US-format (`06/23/2025`, `3/13/24`), and year-only (`2026`). |

## Study-specific decisions

These are decisions the source data forced on us; they belong in this
file (not in any IG) so future sessions don't reopen them.

### `ARMCD` / `ARM` are not phenotype labels

The Randomize CRF's `PROFILE` item carries strings like
`"a non-Hispanic male"`. That is a **stratification phenotype**, not a
treatment arm. `Disposition.RECEIVEDINTERVENTION` is `Yes` for zero
subjects in the entire export, so this study has no treatment
administration at all.

Convention enforced across SDTM DM and every ADaM dataset:

- `ARMCD = "TREATMENT"` / `ARM = "Study Treatment"` for subjects who
  were randomized (have a PROFILE).
- `ARMCD = "SCRNFAIL"` / `ARM = "Screen Failure"` for subjects who were
  not.
- `ACTARMCD` / `ACTARM` mirror `ARMCD` / `ARM` (no exposure data exists
  to differentiate).
- Phenotype lives in **`ADSL.STRAT1`** (`NHM`/`NHF`/`HM`/`HF`) and
  **`ADSL.STRAT1L`** (long label). Downstream OCCDS datasets (ADAE,
  ADCM, ADMH, ADDS, ADIE, ADCE) carry `STRAT1` forward.

Counts for sanity: 530 SCRNFAIL, 280 TREATMENT (236 NHM, 27 NHF, 12 HM,
5 HF).

### `ADVS` is not buildable

The OpenClinica export contains no vital-signs items (no heart rate,
blood pressure, temperature, weight, or height anywhere outside the
Kitchen Sink demo form). VS SDTM and ADVS therefore cannot be generated
from this data. If a vital-signs CRF gets added to the export later,
add a `vs.yaml` spec + `vs.R` build, plus an `advs.yaml` + `advs.R`.

### Datasets in scope

SDTM (9): `DM`, `MH`, `IE`, `AE`, `CM`, `DS`, `LB`, `QS`, `CE`.
ADaM (9): `ADSL`, `ADAE`, `ADCM`, `ADLB`, `ADQS`, `ADMH`, `ADDS`,
`ADIE`, `ADCE`.

Not yet built but feasible: `SV` (subject visits — derive from
per-form `startdate`), trial-design datasets (`TS`, `TA`, `TI`, `TV` —
protocol metadata, not CRF), `ADTTE` (only meaningful if a SAP defines
a time-to-event endpoint; the data has 13 Suspected-MI events).

## Spec YAML format (binding)

Every SDTM and ADaM spec is a YAML file under `spec/sdtm/` or
`spec/adam/` with the same shape.

### Dataset-level keys (top of every file)

| Key | Required | Notes |
|---|---|---|
| `domain` / `dataset` | Yes | 2-char SDTM code or ADaM dataset name (`ADSL`, `ADAE`, …) |
| `label` | Yes | ≤ 40 chars |
| `class` / `structure` | Yes | e.g., `Events`, `BDS`, `OCCDS`, `One record per subject` |
| `purpose` | Yes | `Tabulation` (SDTM) / `Analysis` (ADaM) |
| `keys` | Yes | List of key variable names |
| `ig_anchor` | SDTM only | Anchor stem from `sdtmig_v3_3.html` (e.g., `"AE+Specification"`) |
| `sources` | Yes | List of `{form, item_groups}` or `{sdtm_domain, vars}` |
| `record_rule` | When non-trivial | Free text explaining what makes a row exist |

### Variable block (binding rule)

Variables are name-keyed under `variables:`. **Every** variable, in
**every** dataset, must have:

```yaml
variables:
  AETERM:
    label: Reported Term for the Adverse Event
    type: Char          # Char or Num
    length: 200         # SAS V5 transport limit: ≤ 200 char, ≤ 8 numeric
    role: Topic         # Identifier | Topic | Record/Grouping/Result/Synonym/Variable Qualifier | Timing
    core: Req           # Req | Exp | Perm  (SDTM core designation)
    origin: CRF         # CRF | Derived | Assigned | Sponsor Defined | Protocol | Predecessor
    derivation: |
      Copied verbatim from the AETERM item on the Adverse Event CRF form.
```

The seven mandatory fields are: **name** (the key), **label**, **type**,
**length**, **role**, **core**, **origin**, **derivation**.
`derivation` must always be populated — never empty. For constants write
e.g. `Constant value "DM"`; for variables sourced directly write e.g.
`Copied from <form>.<itemgroup>.<item>`.

### Optional variable fields

| Field | Use |
|---|---|
| `codelist` | CDISC CT codelist name (`SEX`, `NY`, `ACN`, `OUT`, …) |
| `value` | Constant value (alternative to spelling it in `derivation`) |
| `raw_item` / `raw_items` | Source CRF item name(s) — `flat.rds$itemname` |
| `raw_column` | Source column in `flat.rds` (e.g., `subjectkey`, `startdate`) |
| `source_form` | CRF form long-name (e.g., `"Adverse Event"`) |
| `source_item_group` | CRF item-group OID (`AE`, `INC1`, `group1`, `rand1`, ...) |
| `code_map` | Inline mapping of raw value → CT value |
| `notes` | Anything else worth capturing for spec readers |

## R code conventions (binding)

Every SDTM/ADaM build program is a self-contained `.R` file that an
analyst can run with `Rscript program/<area>/<file>.R`, and every folder
has a batch runner that drives all programs in that folder plus emits a
log per program.

### File template

```r
## --------------------------------------------------------------------
## <DOMAIN/DATASET> — <full label>
## Spec: spec/<sdtm|adam>/<file>.yaml
## Input: data/raw/<form>.rds  (or data/sdtm/<dom>.rds for ADaM)
## Output: data/<sdtm|adam>/<lc>.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)
# SDTM: that's usually it.
# ADaM: also library(admiral) (and admiraldev / metacore where applicable).

raw <- readRDS("data/raw/<form>.rds")

<dom> <- raw |>
  ## ... dplyr/tidyr (or admiral::derive_*) pipeline implementing each
  ## derivation from the YAML
  arrange(USUBJID, ...) |>
  mutate(<DOM>SEQ = row_number(), .by = USUBJID) |>
  select(STUDYID, DOMAIN, USUBJID, <DOM>SEQ, ...)

saveRDS(<dom>, "data/<sdtm|adam>/<lc>.rds")
```

Conventions:
- Use **`dplyr`** and **`tidyr`** verbs (mutate, filter, transmute,
  pivot_*, unnest_*, etc.). Avoid base subsetting except for trivial
  vector ops.
- For ADaM, prefer **`{admiral}` series** (admiral / admiraldev /
  metacore / metatools / xportr) for ADSL building blocks, treatment
  variable derivation, BDS skeleton, time-to-event helpers, etc. Fall
  back to plain dplyr/tidyr when admiral does not cover the case.
- Use the **native pipe `|>`**, not `%>%`, unless the function being
  called only works with magrittr (rare).
- Read inputs from `data/raw/` (for SDTM) or `data/sdtm/` (for ADaM).
- Write the output as `<lowercase-name>.rds` into `data/sdtm/` or
  `data/adam/`.
- One program produces exactly one dataset.
- Header comment lists the spec file, inputs, and output.
- Load only the packages you actually use.
- Implement every variable in the spec; never silently omit one.

### Batch runners and logging

Every `program/<area>/` folder contains a `_run_all.R` that drives the
folder's programs in dependency order and writes one log per program
using `{logrx}`:

```r
## program/<area>/_run_all.R
library(logrx)

order  <- c("dm","mh","ie","ae","cm","ds","lb","qs","ce")   # adjust per area
log_dir <- file.path("logs", "<area>")
dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)

for (p in order) {
  axecute(
    file          = file.path("program", "<area>", paste0(p, ".R")),
    log_name      = paste0(p, ".log"),
    log_path      = log_dir,
    include_rds   = FALSE,   # see API quirk below
    quit_on_error = FALSE,
    show_repo_url = FALSE
  )
}
```

`logrx::axecute()` writes a structured log capturing R version, package
versions, the program path, console output, warnings, errors, and timing.
Logs land under `logs/<area>/<program>.log` (one file per program).
Single-program runs can still use `Rscript program/<area>/<file>.R`
without logrx; the batch runner is the audited path.

### Package API quirks (learned the hard way)

- `logrx::axecute()` — the `remove_log_object` argument was **deprecated
  and defunct** in logrx 0.3.0. Use `include_rds = FALSE` instead. Older
  examples and stack-overflow answers still show the old name; if you
  copy from one, fix it.
- `admiral::derive_var_chg()` and `derive_var_pchg()` take **only**
  `dataset` — no `new_var` argument. They always write to `CHG` /
  `PCHG`. Other admiral derive functions do take `new_var`, so the
  inconsistency is easy to miss.
- `admiral::derive_vars_dt()` strictly requires ISO 8601 input. Pass raw
  CRF dates through `normalize_iso_date()` (see ut_visits.R) first;
  otherwise non-ISO rows silently become `NA` and admiral prints a
  long-running warning block.
- `admiral::convert_blanks_to_na()` should be the first step in every
  ADaM program — most admiral helpers branch on `NA`, not on empty
  strings.

### {admiral} usage notes (ADaM only)

- `derive_vars_dt()`, `derive_vars_dtm_to_dt()`, `derive_var_extreme_dt()`
  for date / datetime derivations.
- `derive_vars_merged()` for joining lookup info onto an analysis frame.
- `derive_var_trtdurd()`, `derive_var_atoxgr()`, `derive_var_anrind()` for
  common BDS derivations.
- `derive_param_*` family for synthesized parameters (e.g., BMI from
  height/weight, ratio params).
- `derive_extreme_records()`, `filter_extreme()` for first/last/min/max
  selections.
- `convert_blanks_to_na()` early in every program — admiral expects NA,
  not blanks.
- ADaM tutorials and templates are exposed by
  `admiral::use_ad_template()` — start there for ADSL / ADAE / ADTTE /
  ADLB skeletons rather than writing from scratch.

## Mapping authority

When the IG and the dataset disagree, the IG wins on variable definitions
(name, label, type, length, role, core, codelist); the CRF wins on the
**source** of the value. Mapping decisions should be defensible against
either:

- SDTM: `spec/ig/knowledge_sdtm_ig.md` → anchor in `sdtmig_v3_3.html`.
- ADaM: `spec/ig/knowledge_adam_ig.md` → CDISC Library (login wall) for
  canonical PDF, or the rules summarised in the knowledge file.

## Out-of-scope forms

The OpenClinica export contains seven forms that do **not** feed SDTM in
this pilot (operational, demo, read-only, or paired/coding):

- `Kitchen Sink` (CRF-builder demo page)
- `Source Document` (operational uploads)
- `In-clinic Photo`
- `4. View Randomization Assignment` (read-only view of the randomization)
- `RxNorm Coding` (coding workflow folded into CM)
- `Evaluator A` and `Committee Review` (adjudication — `EA` domain
  exists in SDTMIG v4.0 but not in v3.3; out of scope for this pilot)

Forms in the spec that are absent from the export: `ICF (eConsent)`,
`EQ-5D-5L`, `Skin Conditions Questionnaire`, `Evaluator B`.

## Versions targeted

| Standard | Version |
|---|---|
| SDTMIG | 3.3 |
| SDTM model | 1.7 |
| ADaMIG | 1.3 |
| ADaM model | 2.1 |
| OCCDS IG | 1.1 |
| ADaM BDS for TTE | 1.0 |

SDTMIG v4.0 / SDTM v2.0 are in public review through April 2026 — note in
agent output where a future v4.0 change would matter (EA, NSV/SUPP, MSI,
Variable Groups), but do **not** target v4.0 in this pilot.

## Validation workflow

After making non-trivial changes to specs or build programs, dispatch a
sub-agent to run the relevant batch runner and audit the outputs against
the specs. This catches regressions the in-line build script cannot.

What the validator should do:

1. Run `program/<area>/_run_all.R` from project root; capture stdout,
   stderr, and the per-program logs under `logs/<area>/`.
2. For each dataset built, compare its column set against the
   `variables:` keys in the corresponding YAML spec — flag missing
   variables and unexpected extras.
3. Confirm structural rules: USUBJID present and non-null;
   `<DOM>SEQ` / `ASEQ` unique within USUBJID; ABLFL unique within
   (USUBJID, PARAMCD); flag variables are `Y`/null only (never `N`,
   never blank); all USUBJIDs in OCCDS/BDS datasets appear in ADSL.
4. Flag every all-NA column — it usually means a missing derivation or
   sparse upstream data.

Two validation passes have already run during initial build:
- SDTM (after the initial build) — found DM dropping 31 subjects,
  VISITNUM all-NA via bad coercion, QSBLFL all-NA, ARMCD over-length.
  All fixed; the helpers in `ut_visits.R` exist because of these.
- ADaM (after the initial build) — surfaced upstream data sparsity
  (treatment dates absent, AE not coded, lab reference ranges absent)
  but no code defects. These remain limitations of the synthetic source,
  not bugs.
