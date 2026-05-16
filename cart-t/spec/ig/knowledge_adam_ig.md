# ADaM IG / ADaM Model — Knowledge Map for Spec Development

**Purpose.** Navigation index for ADaM standards. Unlike the SDTMIG, the
canonical ADaM IG documents are **not** publicly browsable as HTML — they
are PDFs/Word docs distributed through the CDISC Library (login required).
This file points at:

1. The local landing pages we did fetch.
2. The official authoritative documents and how to obtain them.
3. The fixed rules that drive every ADaM dataset, so an agent can build a
   spec correctly without dereferencing the PDFs for routine cases.

## Local files

| File | Standard | Content |
|---|---|---|
| `adamig_v1_3.html` | ADaMIG v1.3 landing page | Description + download links (links require CDISC sign-in) |
| `adam_v2_1.html`   | ADaM v2.1 model landing page | Same — landing page only |

**Base URLs:**

- ADaMIG v1.3: `https://www.cdisc.org/standards/foundational/adam/adamig-v1-3`
- ADaM v2.1: `https://www.cdisc.org/standards/foundational/adam/adam-v2-1`
- CDISC Library (login wall, HTML browser of all standards): `https://library.cdisc.org/browser/#/`
- CDISC Library API: `https://api.developer.library.cdisc.org/api-details`

When an agent needs a detail the local files can't answer, that's the
authoritative place to retrieve it (with credentials).

---

## The ADaM document family — what to consult for what

ADaM is a family, not a single book. Use the one that matches the
question, not just "the IG".

| Document | When to consult | Latest |
|---|---|---|
| **ADaM v2.1** (model) | Conceptual questions: what is a dataset structure, what are the four ADaM fundamental principles, what variable categories exist. | v2.1, 2009 |
| **ADaMIG v1.3** (implementation guide) | Default reference. Variable definitions, naming rules, ADSL contents, BDS contents, traceability requirements. | v1.3, 2021 |
| **ADaM OCCDS** | Occurrence-data datasets (`ADAE`, `ADCM`, `ADMH`, `ADDS`, `ADDV`). | v1.1, 2021 |
| **ADaM BDS for Time-to-Event** | Time-to-event analyses (`ADTTE`). | v1.0, 2012 |
| **ADaM Examples in Commonly Used Statistical Analysis Methods** | Worked examples for hypothesis tests, MMRM, etc. | v1.0, 2011 |
| **ADaM Continuous IG / Coding User Guide** | Edge cases in legacy continuous data. | v1.0 |
| **ADaM Oncology Examples** | Tumor response / oncology endpoints. | v1.0 |
| **ADaM Non-Compartmental Analysis Input Data** | PK datasets. | v1.0 |

`https://www.cdisc.org/kb/articles/making-sense-various-adam-documents`
explains how these relate.

**Forward look:** ADaM v3.0 (in development) will consolidate the model +
IG into a single document. Currently no public-review date set; ADaMIG
v1.3 + ADaM v2.1 remain authoritative.

---

## The fixed ADaM rules an agent should know without dereferencing a PDF

These do not change between domains. Cite "ADaMIG v1.3, §<n>" when
challenged; section numbers below are from ADaMIG v1.3 unless noted.

### Fundamental principles (ADaM v2.1, §2.1) — apply to every dataset

1. **Analysis-ready** — analysis must be reproducible with no additional
   programming on the dataset.
2. **Traceability** — every value traces back to its source in SDTM (or
   another ADaM dataset).
3. **Standardized for analysis** — same structure / variable names across
   sponsors and studies.
4. **Clear and unambiguous communication** — metadata fully described in
   define.xml, ADRG, define-XML-driven specs.

### Dataset structures (ADaMIG v1.3, §3)

| Structure | Use for | Dataset name pattern |
|---|---|---|
| **ADSL** | One row per subject; subject-level variables (demographics, treatment, populations, key dates) | Exactly `ADSL` |
| **BDS** (Basic Data Structure) | One row per subject per analysis parameter per analysis-relevant timepoint / criterion | `AD` + up to 6 chars; conventional: `ADaa` where `aa` is the parent SDTM (e.g., `ADLB`, `ADVS`, `ADQS`); `ADTTE` for time-to-event |
| **OCCDS** (covered by separate OCCDS IG) | One row per occurrence (AE, CM, etc.) | `AD` + 2-char SDTM domain (`ADAE`, `ADCM`, `ADMH`, `ADDS`, `ADDV`) |

### ADSL required-content checklist (ADaMIG v1.3, §3.1.1)

ADSL must (at minimum) contain:

- Identifiers: `STUDYID`, `USUBJID`, `SUBJID`, `SITEID`
- Demographics: `AGE`, `AGEU`, `SEX`, `RACE`, `ETHNIC`, `COUNTRY`
- Treatment per period: `TRT01P`, `TRT01A` (+ `TRTxxP`/`TRTxxA` for additional periods, plus matching numeric `xxN`s)
- Treatment dates: `TRTSDT`, `TRTEDT`, `TRTSDTM`, `TRTEDTM`, `TRTDURD`
- Randomization: `RANDDT`
- Population flags: `SAFFL`, `ITTFL`, `EFFFL`, `RANDFL`, `COMPLFL` (as applicable)
- Disposition reason: `DCSREAS` (or `DCDECOD`)

Add additional analysis stratifiers (`AGEGR1`, `AGEGR1N`, `RACEN`,
`STRAT1`, …) as required by the SAP.

### BDS variable categories (ADaMIG v1.3, §3.3) — the always-relevant ones

| Category | Variables |
|---|---|
| Identifiers | `STUDYID`, `USUBJID`, `SUBJID`, `SITEID`, `ASEQ` |
| Parameter | `PARAM`, `PARAMCD`, `PARAMN`, `PARCAT1`…`PARCATy`, `AVALCAT1`…`AVALCATy` |
| Analysis value | `AVAL`, `AVALC` |
| Baseline & change | `BASE`, `BASEC`, `CHG`, `PCHG`, `R2BASE`, `R2A1LO`, `R2A1HI`, `ABLFL` |
| Reference ranges | `ANRLO`, `ANRHI`, `ANRIND`, `BNRIND` |
| Analysis visit/timing | `AVISIT`, `AVISITN`, `AWRANGE`, `AWLO`, `AWHI`, `AWTARGET`, `AWTDIFF`, `AWU` |
| Analysis dates/times | `ADT`, `ADTM`, `ADTC`, `ADY`, `ATM`, `ATPT`, `ATPTN`, `ATPTREF` |
| Analysis intervals | `ASTDT`, `AENDT`, `ASTDY`, `AENDY` |
| Imputation | `DTYPE` (e.g., `LOCF`, `BOCF`, `WOC`, `AVERAGE`) |
| Selection / criterion flags | `ANLzzFL`, `CRITy`, `CRITyFL`, `CRITyFN`, `ONTRTFL`, `PREFL`, `POSTFL` |
| Treatment per record | `TRTP`, `TRTA`, `TRTPN`, `TRTAN` (period-1) plus `APERIOD`, `APERIODC`, `TRTSEQP`, `TRTSEQA` |
| Provenance | `SRCDOM`, `SRCVAR`, `SRCSEQ` |

### Time-to-event (ADaM BDS-for-TTE IG)

| Variable | Meaning |
|---|---|
| `PARAM`, `PARAMCD` | Endpoint (e.g., `OS`, `PFS`) |
| `AVAL` | Time to event / censoring (units per spec, typically days) |
| `STARTDT` | Time-origin date |
| `ADT` | Event-or-censoring date |
| `CNSR` | Censor flag (0 = event, ≥1 = censored, code per spec) |
| `EVNTDESC`, `CNSDTDSC` | Plain-language description of event / censoring |

### OCCDS (ADAE etc., from OCCDS IG)

- Carry over all SDTM occurrence variables (`AETERM`, `AEDECOD`, `AESEV`,
  `AESER`, `AEREL`, `AEOUT`, `AESTDTC`, `AEENDTC`, `AEACN`).
- Add analysis-side dates: `ASTDT`/`AENDT` numeric, `ASTDY`/`AENDY`.
- First-occurrence flags: `AOCCFL` (per subject), `AOCCPFL` (per PT),
  `AOCCSFL` (per SOC), `AOCC02FL`, `AOCC03FL`, … for analysis subsets.
- Treatment-emergent flag: `TRTEMFL` ("Y" / null).

### Naming rules — quick recap (ADaMIG v1.3, §3.2)

- Variable names ≤ 8 chars, uppercase A–Z 0–9 + `_`, must start with a
  letter.
- Labels ≤ 40 chars.
- Flag variables follow `xxxxFL` ("Y" or null — never "N", never blank).
- Numeric companions to character variables end in `N` (e.g., `RACEN`,
  `AGEGR1N`, `PARAMN`, `TRT01PN`).
- Date variables: `--DT` (SAS num date), `--DTM` (SAS num datetime),
  `--TM` (SAS num time), `--DTC` (ISO 8601 char), `--DY` (study day,
  integer, no day 0).
- Conventions for "Period" `xx` and "Analysis Subset" `zz`: zero-padded,
  `01`–`99`.
- ADaM variable names that overlap SDTM **keep the SDTM meaning** (e.g.,
  `STUDYID`, `USUBJID`, `SEX`, `RACE`, `AGE`, `AESEV` in ADAE).

### Traceability — what every BDS record must carry

- **Metadata traceability** in define.xml: each ADaM variable lists its
  origin (Predecessor / Assigned / Derived).
- **Record traceability** in the dataset: `SRCDOM`, `SRCVAR`, `SRCSEQ` (the
  source SDTM domain, variable, and record sequence number).
- For derived rows (`DTYPE` not null), the source row(s) must still be
  identifiable via the predecessor record(s) being present and flagged.

### Populations and flags — fixed patterns

| Flag | Meaning | Population denominator |
|---|---|---|
| `SAFFL` | Safety population (received ≥ 1 dose) | Safety analyses |
| `ITTFL` | Intent-to-treat | ITT analyses |
| `EFFFL` | Per-protocol / Efficacy-evaluable | Efficacy analyses |
| `RANDFL` | Randomized | Randomization-based analyses |
| `COMPLFL` | Study completer | Completer analyses |
| `mITTFL`, `PPSFL`, `FASFL` | Modified ITT / Per-protocol Set / Full Analysis Set (per SAP) | Per protocol |
| `ANLzzFL` | Record-level inclusion in analysis subset `zz` | BDS / OCCDS subset selections |

**Cardinal rule:** flag = "Y" → include; otherwise null. Never `"N"`.

### CRITy / CRITyFL / CRITyFN

- `CRITy` (≤ 40 chars) = plain-language description of an analysis
  criterion (e.g., `"≥ 30% reduction from baseline"`).
- `CRITyFL` = "Y" / null on records meeting `CRITy`.
- `CRITyFN` = numeric companion (1 / null).
- `y` is `1`..`n`; use `01`..`99` if more than 9 criteria are needed (per
  ADaMIG examples).

---

## How to use this map when developing an ADaM dataset spec

1. **Identify the structure** (ADSL / BDS / OCCDS) from the SAP.
2. **Pick the dataset name** following the rules above.
3. **List required content** from the appropriate section:
   - ADSL → ADaMIG §3.1.1 (see "ADSL required-content checklist" above).
   - BDS → ADaMIG §3.3 (variable categories above).
   - OCCDS → OCCDS IG (start from the SDTM parent and add the analysis
     overlays listed above).
   - TTE → BDS-for-TTE IG.
4. **Resolve naming** using the rules in "Naming rules — quick recap"
   above.
5. **Define traceability** — every variable in the spec needs `Origin`
   metadata; every derived dataset needs `SRCDOM`/`SRCVAR`/`SRCSEQ`.
6. **For anything not covered here**, consult the actual ADaMIG v1.3 PDF
   (CDISC Library, login required) or the relevant supplement.

## What's *not* in the local files

We did not download the IG PDFs themselves (paywall). If the agent needs
canonical wording or exact tables (e.g., the full BDS variable table with
Core designations), the options are:

1. Authenticate to CDISC Library and pull from the Data Standards Browser.
2. Use the CDISC Library API
   (`https://api.developer.library.cdisc.org/api-details`) with credentials.
3. Cross-check against the OpenCDISC / `pinnacle21` validator rule
   metadata, which encodes most rules.

Until then, the rules summarized in this file are sufficient for
first-draft spec authoring; final reviewers will need the PDF for sign-off.
