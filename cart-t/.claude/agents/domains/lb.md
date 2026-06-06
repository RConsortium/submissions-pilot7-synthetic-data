# LB — Domain Knowledge

## Overview
LB (Laboratory Test Results) captures one record per lab test per timepoint
per subject. Two source forms feed it: "2. Baseline Labs and Imaging"
(itemgroups CHEMPANEL, NEPH) and the post-baseline "Lab Results" form
(itemgroup `labs`). The build deduplicates raw repeat submissions, joins
DM.RFSTDTC for LBDY, and writes CDISC-CT-compliant LBTESTCD / LBTEST /
LBORRESU values.

Current output: 950 rows × 23 cols, 169 unique subjects.

---

## Raw data sources

| File | Form / Event | Key items | Subject coverage |
|------|-------------|-----------|-----------------|
| `data/raw/lb_bl.rds` | "2. Baseline Labs and Imaging" (SE_BASELINE) | CHEMPANEL: AMYLASE, BUN, CHLORIDE, HOMOC; NEPH: CREAT, EGFR; date items date_of_blood_draw / DRAWDATE / SCANDATE | 159 subjects (CHEMPANEL+NEPH coverage) |
| `data/raw/lb.rds`    | "Lab Results" (SE_LABS) | labs: CHOLES, TRIG, HEMA, HEMO, RBC, WBC; date item LABDATE | 34 subjects |
| `data/sdtm/dm.rds`   | DM output | USUBJID, RFSTDTC (for LBDY) | 810 subjects; 713 with RFSTDTC |

**CRF noise items intentionally NOT in `test_map`** (filtered out):
- `NEPH.CREATR` — literal string `"(Normal range, Female: 0.5 - 1.1)"` etc.
  Used to be misclassified as "Creatinine (SI), umol/L" — it is a CRF help
  annotation, not a lab measurement.
- `CHEMPANEL.HOMOCRANGE` — same pattern: `"(Normal range, Male: 4 - 16)"`.

---

## Controlled terminology mappings

### `test_map` — CDISC-aligned LBTESTCD / LBTEST / LBORRESU triples

LBTESTCD must be in **C65047 'Laboratory Test Code'** and LBTEST must be in
**C67154 'Laboratory Test Name'**, and the two must share a single NCI
concept code (this is what P21 rule CT2003 checks).

| Itemgroup | Raw item | LBTESTCD | LBTEST                       | LBCAT      | LBORRESU         |
|-----------|----------|----------|------------------------------|------------|------------------|
| CHEMPANEL | AMYLASE  | AMYLASE  | Amylase                      | CHEMISTRY  | U/L              |
| CHEMPANEL | BUN      | UREAN    | Urea Nitrogen                | CHEMISTRY  | mg/dL            |
| CHEMPANEL | CHLORIDE | CL       | Chloride                     | CHEMISTRY  | mmol/L           |
| CHEMPANEL | HOMOC    | HOMOCY   | Homocysteine                 | CHEMISTRY  | umol/L           |
| NEPH      | CREAT    | CREAT    | Creatinine                   | CHEMISTRY  | mg/dL            |
| NEPH      | EGFR     | GFR      | Glomerular Filtration Rate   | CHEMISTRY  | mL/min/1.73 m2   |
| labs      | CHOLES   | CHOL     | Cholesterol                  | CHEMISTRY  | mg/dL            |
| labs      | TRIG     | TRIG     | Triglycerides                | CHEMISTRY  | mg/dL            |
| labs      | HEMA     | HCT      | Hematocrit                   | HEMATOLOGY | %                |
| labs      | HEMO     | HGB      | Hemoglobin                   | HEMATOLOGY | g/dL             |
| labs      | RBC      | RBC      | Erythrocytes                 | HEMATOLOGY | 10^12/L          |
| labs      | WBC      | WBC      | Leukocytes                   | HEMATOLOGY | 10^9/L           |

### Critical CDISC-CT pitfalls encountered

| Wrong (pre-fix)                 | Right (CDISC submission value) | Why |
|---------------------------------|--------------------------------|-----|
| `LBTESTCD = "BUN"`              | `UREAN` | `BUN` is not in C65047 |
| `LBTESTCD = "HCYS"`             | `HOMOCY` | `HCYS` is not in C65047 |
| `LBTESTCD = "EGFR"`             | `GFR`    | C65047 `EGFR` is **Epidermal Growth Factor Receptor**, not glomerular filtration rate |
| `LBTESTCD = "CREATSI"`          | drop     | Not in CT; it was the SI-unit mirror of CREAT, but CDISC CREAT is unit-agnostic |
| `LBTEST = "Estimated GFR"`      | `Glomerular Filtration Rate` | Canonical LBTEST for GFR |
| `LBTEST = "Erythrocytes (RBC)"` | `Erythrocytes` | parens/abbreviation make it a non-CT string |
| `LBTEST = "Leukocytes (WBC)"`   | `Leukocytes`   | same |
| `LBTEST = "Blood Urea Nitrogen"`| `Urea Nitrogen`| canonical name |
| `LBORRESU = "10^3/uL"`          | `10^9/L`       | `10^3/uL` is a CDISC synonym, not a submission value |
| `LBORRESU = "10^6/uL"`          | `10^12/L`      | same |
| `LBORRESU = "mL/min/1.73m2"`    | `mL/min/1.73 m2` | needs the space before `m2` |

---

## P21 rules and fixes

### Resolved rules

#### SD1117 — Duplicate records (110 instances)
**Root cause**: The raw `data/raw/lb.rds` (Lab Results follow-up form) emits
the same `(subjectkey, studyeventoid, itemgrouprepeatkey, itemname)` tuple
multiple times. Sometimes the value is identical (clean repeat
submissions); sometimes it varies (e.g. CNH-001 HEMA values 666 then 44 at
the same visit; CNH-006 CHOLES repeated 6 times). The legacy build did not
deduplicate, so 218 raw duplicate rows (≈109 pairs) became 110 P21
SD1117 findings.

**Fix** (`program/sdtm/lb.R`): After joining and deriving LBDTC, sort by
the natural keys and slice the last row per group:
```r
arrange(USUBJID, LBTESTCD, VISITNUM, LBDTC, itemgrouprepeatkey) |>
group_by(USUBJID, LBTESTCD, VISITNUM, LBDTC) |>
slice_tail(n = 1) |>
ungroup()
```
The "last wins" choice models the export as "most recent data-entry
correction supersedes earlier values" — defensible for synthetic data
where no audit trail is provided.

**Coverage after fix**: 0 residual duplicates on the natural key.

---

#### SD1084 — LBDY not populated (7 instances)
**Root cause**: LBDY was hard-coded `NA_integer_` because the legacy build
predated the DM.RFSTDTC fix.

**Fix** (`program/sdtm/lb.R`): Read `data/sdtm/dm.rds`, join on USUBJID, then
compute study day with the standard skip-day-0 convention. Only full ISO
yyyy-mm-dd LBDTC values yield non-NA LBDY (year-only LABDATE entries
remain NA):
```r
dm_ref <- dm |> select(USUBJID, RFSTDTC)
...
mutate(
  .lbdtc_iso = ifelse(grepl("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", LBDTC), LBDTC, NA_character_),
  .rfstd_iso = ifelse(grepl("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", RFSTDTC), RFSTDTC, NA_character_),
  .lbdtc_d   = suppressWarnings(as.Date(.lbdtc_iso)),
  .rfstd_d   = suppressWarnings(as.Date(.rfstd_iso)),
  LBDY = dplyr::if_else(
    !is.na(.lbdtc_d) & !is.na(.rfstd_d),
    as.integer(.lbdtc_d - .rfstd_d) +
      as.integer(ifelse(.lbdtc_d >= .rfstd_d, 1L, 0L)),
    NA_integer_
  )
)
```
**Coverage after fix**: 889 / 950 rows have non-null LBDY.

---

#### CT2002 — LBTESTCD / LBTEST / LBORRESU not in CDISC CT (11 instances total)
**Root cause**: The hard-coded `test_map` used pre-CDISC names like `BUN`,
`HCYS`, `EGFR`, `CREATSI`; LBTEST strings with parenthetical abbreviations
(`Erythrocytes (RBC)`); and units typed with `^` instead of CDISC's
preferred forms.

**Fix**: Replace the `test_map` with CDISC-aligned values (see table above).

**Coverage after fix**: All 12 distinct LBTESTCDs and 9 distinct LBORRESUs in
the output are CDISC C65047 / C71620 submission values.

---

#### CT2003 — LBTESTCD / LBTEST pairing mismatch (4 instances)
**Root cause**: e.g. `LBTESTCD=EGFR` (CDISC concept "Epidermal Growth
Factor Receptor") paired with `LBTEST="Estimated GFR"` (no CDISC concept).
The two had no shared NCI code.

**Fix**: Use canonical pairs from CDISC `SDTM Terminology.txt` (the
`Code` column in column 1 is the NCI concept and must match between
LBTESTCD and LBTEST rows). All pairs in `test_map` now share an NCI code:
`AMYLASE↔Amylase` (C64434), `UREAN↔Urea Nitrogen` (C125949),
`CL↔Chloride` (C64495), `HOMOCY↔Homocysteine` (C74741),
`CREAT↔Creatinine` (C64547), `GFR↔Glomerular Filtration Rate` (C90505),
`CHOL↔Cholesterol` (C105586), `TRIG↔Triglycerides` (C64812),
`HCT↔Hematocrit` (C64796), `HGB↔Hemoglobin` (C64848),
`RBC↔Erythrocytes` (C51946), `WBC↔Leukocytes` (C51948).

---

#### SD0057 — Expected variables LBLOBXFL, LBORNRHI, LBORNRLO missing
**Root cause**: Columns were not generated in the legacy build.

**Fix**: Added all three columns to the output schema with `NA_character_`
values, with derivation docs in the spec explaining why they are NA:
- `LBLOBXFL` — no exposure (Disposition.RECEIVEDINTERVENTION="No" for all
  subjects), so there is no anchor for a last-observation-before-exposure
  flag.
- `LBORNRLO` / `LBORNRHI` — the raw export carries only the help-text
  string "(Normal range, ...)"; no per-result range columns exist.

`LBSTNRLO` / `LBSTNRHI` (Permissible) were also added for symmetry.

---

### Known data limitations

| Rule | Residual count | Reason |
|------|---------------|--------|
| SD1084 LBDY null | 61 rows | LBDTC is year-only ("2026" from LABDATE) OR DM.RFSTDTC could not be derived (~97 subjects) |
| SD0057 LBLOBXFL null | 950 rows | Column present and required, but cannot be derived — no exposure |
| SD0057 LBORNRLO/LBORNRHI null | 950 rows | Reference ranges not captured in raw export (only help-text "Normal range" annotations) |
| LBNRIND null | 950 rows | Requires LBORNRLO/HI — same root cause |
| Dropped tests | n/a | NEPH.CREATR and CHEMPANEL.HOMOCRANGE are CRF normal-range help-text items, not lab results |

---

## Cross-domain dependencies

| Dependency | Direction | Notes |
|------------|-----------|-------|
| `data/sdtm/dm.rds` (RFSTDTC) | LB reads DM | Required for LBDY derivation; rebuild LB after any DM change that affects RFSTDTC |
| LB.USUBJID ⊂ DM.USUBJID | DM validates LB | All 169 LB subjects are in DM (810 subjects) |

**Rebuild order**: DM must be current before running LB. There are no
downstream SDTM dependencies on LB other than the ADaM ADLB build.

---

## Rebuild command

```bash
Rscript program/sdtm/lb.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
LB written: 950 rows x 23 cols
Unique subjects: 169
Residual dups on (USUBJID, LBTESTCD, VISITNUM, LBDTC): 0
LBDTC non-null: 934 / 950
LBDY  non-null: 889 / 950
LBTESTCDs: AMYLASE, CHOL, CL, CREAT, GFR, HCT, HGB, HOMOCY, RBC, TRIG, UREAN, WBC
LBORRESUs: %, 10^12/L, 10^9/L, g/dL, mg/dL, mL/min/1.73 m2, mmol/L, U/L, umol/L
```

Sanity checks:
```r
lb <- readRDS("data/sdtm/lb.rds")
# No duplicates on natural key
stopifnot(nrow(lb) == nrow(distinct(lb, USUBJID, LBTESTCD, VISITNUM, LBDTC)))
# All LBTESTCDs are CDISC CT
stopifnot(all(lb$LBTESTCD %in% c("AMYLASE","CHOL","CL","CREAT","GFR","HCT",
                                  "HGB","HOMOCY","RBC","TRIG","UREAN","WBC")))
# LBSEQ unique within USUBJID
stopifnot(!anyDuplicated(lb[, c("USUBJID", "LBSEQ")]))
# All LB subjects in DM
dm_ids <- readRDS("data/sdtm/dm.rds")$USUBJID
stopifnot(all(lb$USUBJID %in% dm_ids))
```
