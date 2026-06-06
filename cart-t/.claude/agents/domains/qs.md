# QS — Domain Knowledge

## Overview
QS (Questionnaires) captures one record per questionnaire item per
timepoint per subject. This pilot only carries the RAND SF-12 v1
instrument. EQ-5D-5L and the Skin Conditions Questionnaire are absent
from the OpenClinica export and therefore cannot be built (per
`CLAUDE.md`). The SF-12 form (`SE_QUALITYOFLIFE`) is administered once
per subject, producing 12 item rows (Q1..Q12) plus 4 subscale-score
rows per subject for the 247 SF-12 respondents.

Emitted dataset: 3,611 rows × 19 cols across 247 subjects.

---

## Raw data sources

| File | Form / Event | Key items | Subject coverage |
|------|-------------|-----------|-----------------|
| `data/raw/qs_sf12.rds` | "RAND SF-12 Survey" (SE_QUALITYOFLIFE) | Q1..Q12 (items), Q1V..Q12V (validated items), BP/GH/VT/SF (subscale scores), PF-A/PF-S, RP-A/RP-S, RE-A/RE-S, ME-A/ME-S (subscale components) | 247 subjects, 8871 raw rows |
| `data/sdtm/dm.rds` | DM output | RFSTDTC, RFENDTC | 247 / 247 have RFSTDTC (needed for EPOCH + QSDY) |

The composite subscale codes **PF**, **RP**, **RE**, **ME** are **NOT**
emitted as standalone rows in the raw export — only their A/S
components are present. So the QS build emits item rows (12) +
**4** subscale rows (BP/GH/VT/SF) per respondent, not 8.

Item-group distribution in raw:
- `G`, `G1`, `G2AND3`, `G4AND5`, `G6AND7`, `G9TO11`: raw item responses
- `c`: validated / recoded items + scored subscales

---

## Controlled terminology mappings

### QSCAT (raw constant)
CDISC "Category of Questionnaire" extensible codelist value for SF-12
v1 is **`"SF12"`** — no dash. The previous build used `"SF-12"` which
triggered CT2002.

### QSTESTCD / QSTEST (raw item `itemname` → CDISC SF-12 v1 pair)

QSCAT="SF12" canonical pairs (all QSTEST ≤ 40 chars):

| Raw itemname | QSTESTCD | QSTEST                          | QSSCAT   |
|--------------|----------|---------------------------------|----------|
| Q1           | SF1201   | General Health                  | ITEM     |
| Q2           | SF1202   | Moderate Activities             | ITEM     |
| Q3           | SF1203   | Climb Several Flights           | ITEM     |
| Q4           | SF1204   | Accomplished Less - Physical    | ITEM     |
| Q5           | SF1205   | Limited in Kind - Physical      | ITEM     |
| Q6           | SF1206   | Accomplished Less - Emotional   | ITEM     |
| Q7           | SF1207   | Less Careful - Emotional        | ITEM     |
| Q8           | SF1208   | Pain Interfered                 | ITEM     |
| Q9           | SF1209   | Calm and Peaceful               | ITEM     |
| Q10          | SF1210   | Energy                          | ITEM     |
| Q11          | SF1211   | Felt Downhearted                | ITEM     |
| Q12          | SF1212   | Social Interference             | ITEM     |
| PF           | SF12PF   | Physical Functioning Score      | SUBSCALE |
| RP           | SF12RP   | Role Physical Score             | SUBSCALE |
| BP           | SF12BP   | Bodily Pain Score               | SUBSCALE |
| GH           | SF12GH   | General Health Score            | SUBSCALE |
| VT           | SF12VT   | Vitality Score                  | SUBSCALE |
| SF           | SF12SF   | Social Functioning Score        | SUBSCALE |
| RE           | SF12RE   | Role Emotional Score            | SUBSCALE |
| ME           | SF12MH   | Mental Health Score             | SUBSCALE |

**Important**: CDISC code for Mental Health subscale is `SF12MH`, NOT
`SF12ME`. The raw itemname is `ME` (RAND SF-12 source notation), so the
map translates `ME -> SF12MH`.

### QSORRESU / QSSTRESU (unit)
**Always NA** for SF-12. The Unit codelist does not contain "SCORE";
item responses are coded categorical (no unit) and subscale scores are
unitless on a 0-100 scale (raw or norm-based). Leave NA — do not emit
`"SCORE"`.

### EPOCH (CDISC EPOCH codelist C99079)
Three values used: `SCREENING`, `TREATMENT`, `FOLLOW-UP`. Same set as
CE and DS — derived from QSDTC vs DM.RFSTDTC / RFENDTC.

---

## P21 rules and fixes

### Resolved rules

#### SD0017 — Invalid value for QSTEST variable (439 → 0)
**Root cause**: Previous build emitted QSTEST strings like
`"SF-12 Q05 - Limited Kind of Work - Physical"` (43 chars) which:
1. exceeded the 40-char QSTEST length limit, and
2. did not match the CDISC SF-12 v1 controlled QSTEST values.

**Fix** (`program/sdtm/qs.R`): Replace the bespoke "SF-12 Qnn - …"
strings with CDISC canonical QSTEST short labels. New max length: 29.
```r
raw_items <- tibble::tribble(
  ~itemname, ~QSTESTCD, ~QSTEST,                          ~QSSCAT,
  "Q1",      "SF1201",  "General Health",                 "ITEM",
  "Q2",      "SF1202",  "Moderate Activities",            "ITEM",
  ...
  "Q12",     "SF1212",  "Social Interference",            "ITEM"
)
subscale_items <- tibble::tribble(
  ~itemname, ~QSTESTCD, ~QSTEST,                       ~QSSCAT,
  "BP",      "SF12BP",  "Bodily Pain Score",           "SUBSCALE",
  "GH",      "SF12GH",  "General Health Score",        "SUBSCALE",
  "VT",      "SF12VT",  "Vitality Score",              "SUBSCALE",
  "SF",      "SF12SF",  "Social Functioning Score",    "SUBSCALE",
  ...
  "ME",      "SF12MH",  "Mental Health Score",         "SUBSCALE"  # MH not ME
)
```
**Coverage after fix**: 3611 / 3611 QSTEST in CDISC SF-12 v1 codelist.

---

#### CT2002 — QSCAT value not in 'Category of Questionnaire' codelist (1 → 0)
**Root cause**: QSCAT was emitted as `"SF-12"` (with dash). CDISC code is
`"SF12"` (no dash).

**Fix**:
```r
mutate(QSCAT = "SF12")     # was "SF-12"
```

---

#### CT2002 — QSORRESU / QSSTRESU 'SCORE' not in Unit codelist (1 + 1 → 0)
**Root cause**: Previous build set `QSORRESU = "SCORE"` and
`QSSTRESU = "SCORE"` on subscale rows. "SCORE" is not a CDISC unit.

**Fix**: Leave both NA — SF-12 subscale scores are unitless.
```r
mutate(
  QSORRESU = NA_character_,
  QSSTRESU = NA_character_,
)
```

---

#### SD1077 — Regulatory Expected variable EPOCH not found (1 → 0)
**Root cause**: EPOCH was never derived.

**Fix**: Derive EPOCH from QSDTC vs DM reference dates (same pattern
as CE / DS):
```r
qs <- qs |>
  left_join(dm |> select(USUBJID, RFSTDTC, RFENDTC), by = "USUBJID") |>
  mutate(
    EPOCH = dplyr::case_when(
      is.na(QSDTC) | is.na(RFSTDTC)            ~ NA_character_,
      QSDTC < RFSTDTC                          ~ "SCREENING",
      !is.na(RFENDTC) & QSDTC > RFENDTC        ~ "FOLLOW-UP",
      TRUE                                     ~ "TREATMENT"
    ),
    QSDY = dplyr::if_else(
      !is.na(QSDTC) & !is.na(RFSTDTC),
      as.integer(as.Date(QSDTC) - as.Date(RFSTDTC)) +
        ifelse(QSDTC >= RFSTDTC, 1L, 0L),
      NA_integer_
    )
  )
```
**Coverage after fix**: EPOCH 3611 / 3611, QSDY 3611 / 3611.

EPOCH distribution: SCREENING 48, TREATMENT 3563. No FOLLOW-UP rows
because the SF-12 form is administered pre/at randomization in this
pilot, all visits fall on or before the reference period end.

---

#### Date format proxy (collateral) — QSDTC for MGH-131
The raw `qs_sf12.rds$startdate` is a mix of ISO date (`2024-09-12`) and
ISO datetime (`2022-10-20T10:47:00`). `normalize_iso_date()` does not
parse datetimes, so the previous build silently produced NA QSDTC for
subject `CART-T-PILOT-01-MGH-131` (16 rows). Truncate to date portion
first (matching ds.R / lb.R pattern):
```r
QSDTC = normalize_iso_date(substr(startdate, 1, 10))
```
Coverage: QSDTC 3611 / 3611.

---

### Known data limitations

| Rule | Residual count | Reason |
|------|---------------|--------|
| Subscale rows for PF/RP/RE/ME | 0 emitted | Raw export only carries the A/S components (PF-A, PF-S, …) and validated items, never composite PF / RP / RE / ME subscale rows. The 4 emitted subscales (BP, GH, VT, SF) reflect what the source `c` itemgroup actually populates. |
| QSSTRESN recomputation | n/a | Subscale scores are copied directly from raw — not recomputed per the SF-12v1/v2 algorithm. Recomputing per published algorithm is a deferred follow-up (see issue #21 comment 0). |
| EQ-5D-5L, Skin Conditions Questionnaire | n/a | Absent from OpenClinica export entirely. |

---

## Cross-domain dependencies

| Dependency | Direction | Notes |
|------------|-----------|-------|
| DM.RFSTDTC | DM → QS | needed for QSDY and EPOCH SCREENING / TREATMENT boundary |
| DM.RFENDTC | DM → QS | needed for FOLLOW-UP / TREATMENT EPOCH boundary |

**Rebuild order when DM source data changes**:
```
1. Rscript program/sdtm/dm.R    # consume any upstream changes
2. Rscript program/sdtm/qs.R    # consumes updated DM.RFSTDTC / RFENDTC
```

---

## Rebuild command

```bash
Rscript program/sdtm/qs.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
QS written: 3611 rows x 19 cols
Unique subjects: 247
QSDTC non-null: 3611 / 3611
EPOCH non-null: 3611 / 3611
QSDY  non-null: 3611 / 3611
Max QSTEST length: 29 (limit 40)

QSCAT distribution:
SF12
3611

QSSCAT distribution:
    ITEM SUBSCALE
    2701      910

EPOCH distribution:
SCREENING TREATMENT
       48      3563

QSTESTCD distribution:
SF1201 SF1202 SF1203 SF1204 SF1205 SF1206 SF1207 SF1208 SF1209 SF1210 SF1211
   247    234    229    226    220    219    219    220    222    222    222
SF1212 SF12BP SF12GH SF12SF SF12VT
   221    220    247    221    222
```

Sanity checks:
```r
qs <- readRDS("data/sdtm/qs.rds")
stopifnot(max(nchar(qs$QSTEST), na.rm = TRUE) <= 40)
stopifnot(all(qs$QSCAT == "SF12"))
stopifnot(!any(qs$QSORRESU == "SCORE", na.rm = TRUE))
stopifnot(!any(qs$QSSTRESU == "SCORE", na.rm = TRUE))
stopifnot(all(is.na(qs$EPOCH) | qs$EPOCH %in% c("SCREENING","TREATMENT","FOLLOW-UP")))
```
