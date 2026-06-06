# CE — Domain Knowledge

## Overview
CE (Clinical Events) captures one record per protocol-defined clinical
event per subject. The only event the study collects is Suspected MI,
so `CECAT` is the constant `"SUSPECTED MI"` and `CEPRESP` is constant
`"Y"` (pre-specified protocol event).

The Suspected MI CRF (`data/raw/mi.rds`) is a tiny, sparse form: only
17 EVENT item-group rows total, and 9 of them contain operator
test/junk text in the DESC field rather than real event data. After
canonicalising terms and dropping the junk rows the emitted CE has
**8 rows × 12 cols** across 8 subjects.

Because CE comes from a separate form from AE, the "no overlap with AE"
check in issue #15 is structurally satisfied — CE and AE share no raw
rows.

---

## Raw data sources

| File | Form / Event | Key items | Subject coverage |
|------|-------------|-----------|-----------------|
| `data/raw/mi.rds` | "Suspected MI" (SE_ENDPOINT), itemgroupname=`EVENT` | DESC, EVENTDATE | 17 form repeats across 13 subjects (14 with DESC, 1 row has DESC = "" / NA after filter) |
| `data/raw/mi.rds` | same form, itemgroupname=`PANEL` | CK, CKMB, TROP | Lab values — belong in LB, not CE |
| `data/raw/mi.rds` | same form, itemgroupname=`UPLOADS` | ANGIO, EKG + dates | Diagnostic procedures — belong in PR / EG (out of scope for v3.3 build) |
| `data/sdtm/dm.rds` | DM output | RFSTDTC (CESTDY + EPOCH), RFENDTC (EPOCH boundary) | 810 subjects; 713 with RFSTDTC, 713 with RFENDTC |

Form is small enough that all 14 DESC values can be listed:

```
"Chest pain, with dyspnea, nausea, no diaphoresis."   -> CHEST PAIN
" chest pain" (x3)                                    -> CHEST PAIN
" cest pain" (typo)                                   -> CHEST PAIN
"chest pain"                                          -> CHEST PAIN
"myocardial infarction"                               -> SUSPECTED MYOCARDIAL INFARCTION
"MI"                                                  -> SUSPECTED MYOCARDIAL INFARCTION
" lakjsd"                                             -> dropped (junk)
"cjkcxhcjclJKHdlkhsjk clkjhcljkdhls  'cslSkjCShCLSKJh"-> dropped (junk)
"This is only a test"                                 -> dropped (junk)
"this is another test"                                -> dropped (junk)
"Testing this"                                        -> dropped (junk)
"This is a test"                                      -> dropped (junk)
"This is an older event"                              -> dropped (operator placeholder)
"A more recent event"                                 -> dropped (operator placeholder)
```

---

## Controlled terminology mappings

### CETERM
There is no CDISC CT codelist for CETERM in v3.3 — it is a verbatim
"Reported Term" field, free-text by definition. P21 SD1021 flags it
against a **sponsor-defined codelist** when one is declared in the
Define. For this study the only protocol-valid event terms are:

| Canonical CETERM | Source DESC patterns |
|------------------|----------------------|
| `CHEST PAIN` | anything matching `/c[eh]st pain/i` or `/chest pain/i` |
| `SUSPECTED MYOCARDIAL INFARCTION` | exact `"MI"` or anything matching `/myocardial infarction/i` |

Everything else is operator test/junk text and the row is **dropped**
from the emitted CE rather than carried forward with a mis-leading
CT-violating term.

### CECAT
Constant `"SUSPECTED MI"` — assigned by the build, not from CRF.

### CEPRESP / CEOCCUR / CESER
NY codelist (C66742); all constant `"Y"`.

### EPOCH
CDISC EPOCH codelist (C99079). Three values used by this study:
`SCREENING`, `TREATMENT`, `FOLLOW-UP`. The same three are used by DS
(`program/sdtm/ds.R`) so the values are consistent across domains.

---

## P21 rules and fixes

### Resolved rules

#### SD1021 — Unexpected character value in CETERM (4 → 0)
**Root cause**: Raw DESC was copied verbatim into CETERM, including a
misspelling (`cest pain`) and junk values (`lakjsd`,
`cjkcxhcj…JKHdlkhsjk…`, `This is only a test`, etc.). P21 checks
CETERM against the sponsor-defined event codelist declared in the
Define-XML.

**Fix** (`program/sdtm/ce.R`):
```r
map_ceterm <- function(x) {
  u <- toupper(trimws(x))
  dplyr::case_when(
    is.na(u) | !nzchar(u)                       ~ NA_character_,
    grepl("^C[EH]ST PAIN", u)                   ~ "CHEST PAIN",
    grepl("CHEST PAIN", u)                      ~ "CHEST PAIN",
    u == "MI"                                   ~ "SUSPECTED MYOCARDIAL INFARCTION",
    grepl("MYOCARDIAL INFARCTION", u)           ~ "SUSPECTED MYOCARDIAL INFARCTION",
    TRUE                                        ~ NA_character_   # junk -> drop
  )
}

ce <- wide |>
  filter(!is.na(DESC) & nzchar(DESC)) |>
  mutate(CETERM = map_ceterm(DESC)) |>
  filter(!is.na(CETERM)) |>                                       # SD1021: drop junk
  ...
```
**Coverage after fix**: 8 / 8 CETERM populated with a canonical term.

---

#### SD1076 — Permissible variable added to standard domain (3 → 0)
**Root cause**: VISITNUM and VISIT were emitted, but the SDTMIG v3.3 CE
variable table does not list either. (CE uses --DTC/--STDTC/--ENDTC and
EPOCH for timing; VISIT/VISITNUM are Findings-class timing variables.)

**Fix** (`program/sdtm/ce.R`): Dropped `VISITNUM` and `VISIT` from the
final `select()`. They were derived from `studyeventoid` /
`eventname`; the source columns are still pivoted in but never reach
the output.

---

#### SD1078 — Permissible variable with missing value for all records (3 → 0)
**Root cause**: `CEDECOD`, `CESTAT`, and `CESEV` were emitted but set to
`NA_character_` for every row — no MedDRA coding workflow exists in
this synthetic export, every emitted row reflects an event that
occurred (so CESTAT cannot be "NOT DONE"), and the form has no
severity item.

**Fix** (`program/sdtm/ce.R`): Dropped all three columns from the final
`select()`. A real submission with MedDRA coding would add CEDECOD
(and CEBODSYS) back in.

---

#### SD1079 — Variable is in wrong order within domain (2 → 0)
**Root cause**: The previous `select()` order put CEDECOD before CECAT,
CESEV between CESTAT and CESER, and the timing block (CESTDTC, CESTDY)
before EPOCH. SDTMIG v3.3 CE puts EPOCH **before** CESTDTC.

**Fix** (`program/sdtm/ce.R`): Reorder per SDTMIG v3.3:
```r
select(STUDYID, DOMAIN, USUBJID, CESEQ,
       CETERM, CECAT, CEPRESP, CEOCCUR, CESER,
       EPOCH, CESTDTC, CESTDY)
```
Note: CEDECOD, CESCAT, CEBODSYS, CESEV, CESTAT, CEDTC, CEENDTC, CEDY,
CEENDY, CESTRF/CEENRF/CESTRTPT/CESTTPT/CEENRTPT/CEENTPT are all
permissible-core variables that this study cannot populate — they are
omitted entirely rather than emitted as all-NA columns (per SD1078).

---

#### SD1077 — Regulatory Expected variable EPOCH not found (1 → 0)
**Root cause**: EPOCH was never derived.

**Fix** (`program/sdtm/ce.R`): Derive EPOCH from CESTDTC vs DM reference
dates, matching the boundaries DS already uses:
```r
left_join(dm |> select(USUBJID, RFSTDTC, RFENDTC), by = "USUBJID") |>
mutate(
  EPOCH = dplyr::case_when(
    is.na(CESTDTC) | is.na(RFSTDTC)         ~ NA_character_,
    CESTDTC < RFSTDTC                       ~ "SCREENING",
    !is.na(RFENDTC) & CESTDTC > RFENDTC     ~ "FOLLOW-UP",
    TRUE                                    ~ "TREATMENT"
  )
)
```
**Coverage after fix**: 7 / 8 EPOCH populated. The 1 null is subject
`CART-T-PILOT-01-DF-400` who has neither RFSTDTC nor RFENDTC in DM
(no consent / no randomization captured), so no reference period
exists for the EPOCH boundary check.

---

#### SD0022 — Missing Start Time-Point value (1 → 0)
**Root cause**: 1 row had `CESTDTC = null` (subject DF-035 had no raw
EVENTDATE on the form).

**Fix**: The same subject's DESC was junk text (`cjkcxhcj…JKHdlkhsjk
clkjhcljkdhls  'cslSkjCShCLSKJh`), so the row gets dropped by the
SD1021 fix above. No CESTDTC-specific fix needed; SD0022 is resolved
as a side effect of dropping the junk rows.

---

### Known data limitations

| Rule | Residual count | Reason |
|------|---------------|--------|
| EPOCH null | 1 row (DF-400) | Subject lacks RFSTDTC in DM — no reference period to compare CESTDTC against |
| CESTDY null | 1 row (DF-400) | Same — needs RFSTDTC for the arithmetic |
| CEDECOD omitted | n/a | No MedDRA coding workflow exists in the synthetic export |
| CESEV omitted | n/a | No severity item on the Suspected MI CRF |

---

## Cross-domain dependencies

| Dependency | Direction | Notes |
|------------|-----------|-------|
| DM.RFSTDTC | DM → CE | needed for CESTDY and EPOCH boundary |
| DM.RFENDTC | DM → CE | needed for FOLLOW-UP / TREATMENT EPOCH boundary |

**Rebuild order when DM source data changes**:
```
1. Rscript program/sdtm/dm.R    # consume any upstream changes
2. Rscript program/sdtm/ce.R    # consumes updated DM.RFSTDTC / RFENDTC
```

---

## Rebuild command

```bash
Rscript program/sdtm/ce.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
CE written: 8 rows x 12 cols
CETERM non-null: 8 / 8
CESTDTC non-null: 8 / 8
CESTDY non-null: 7 / 8
EPOCH non-null: 7 / 8
CETERM distribution:
                     CHEST PAIN SUSPECTED MYOCARDIAL INFARCTION
                              6                               2
EPOCH distribution:
FOLLOW-UP SCREENING      <NA>
        5         2         1
```

Sanity checks:
```r
ce <- readRDS("data/sdtm/ce.rds")
dm <- readRDS("data/sdtm/dm.rds")

# CETERM values must be in the sponsor codelist
stopifnot(all(ce$CETERM %in% c("CHEST PAIN","SUSPECTED MYOCARDIAL INFARCTION")))

# EPOCH values must be in CDISC EPOCH codelist
stopifnot(all(is.na(ce$EPOCH) | ce$EPOCH %in% c("SCREENING","TREATMENT","FOLLOW-UP")))

# CECAT / CEPRESP / CEOCCUR / CESER constants
stopifnot(all(ce$CECAT == "SUSPECTED MI"))
stopifnot(all(ce$CEPRESP == "Y"))
stopifnot(all(ce$CEOCCUR == "Y"))
stopifnot(all(ce$CESER == "Y"))

# Every CESTDTC present (junk rows dropped)
stopifnot(all(!is.na(ce$CESTDTC) & nzchar(ce$CESTDTC)))

# EPOCH null only when DM.RFSTDTC null
j <- merge(ce, dm[, c("USUBJID","RFSTDTC")], by = "USUBJID", all.x = TRUE)
stopifnot(all(!is.na(j$EPOCH) | is.na(j$RFSTDTC)))
```
