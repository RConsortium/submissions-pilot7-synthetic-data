# CM — Domain Knowledge

## Overview
CM (Concomitant Medications) captures one record per recorded medication
administration per subject. Source is the OpenClinica "ConMed" form
(itemgroupname=`group1`). RxNorm Coding workflow on the same form provides
CMDECOD via the `MEDNAME` item. Per a documented sponsor decision the
dictionary is **RxNorm, not WHO Drug** — see `spec/sdtm/cm.yaml` `sources:`
block.

Current output: 259 rows × 22 cols across 259 unique subjects.

---

## Raw data sources

| File | Form / Event | Key items | Subject coverage |
|------|-------------|-----------|-----------------|
| `data/raw/cm.rds` | "ConMed" form, itemgroupname=`group1` | CMTRTL, CMTRTLX, MEDNAME, CMDOSE, CMDOSU, CMDOSUTXT, CMDOSFRM, CMDOSFRMTEXT, CMDOSFRQ, CMROUTE, CMINDC, CMSTDAT, CMENDAT, ONGOING, RXCUI, RXAUI, RXSTR, RXTTY, RXTYPE | 273 raw subjects; 259 with non-blank CMTRTL |
| `data/sdtm/dm.rds` | DM output | RFSTDTC (CMSTDY/CMENDY derivation) | 810 subjects; 713 with RFSTDTC |

Raw value reference (post-build, from `data/raw/cm.rds`):

| Item | Raw values observed |
|------|---------------------|
| CMDOSFRM | Aerosol, Capsule, Ointment, Other, Suppository, Suspension, Tablet |
| CMDOSFRQ | 8, "BID (twice a day)", "PRN (as needed)", "QD (once a day)", "QID (four times a day)", "QM (every month)", "TID (three times a day)" |
| CMDOSU | G, L, MG, mL, Other, µg |
| CMDOSUTXT | mcg, mg/m^2 |
| CMROUTE | 3, Intravaneous, Oral, Subcutaneous, Topical |
| ONGOING | Yes (220), No (25), "1" (1), "" (1) |

Note: ONGOING is `Yes`/`No` (long form), NOT `Y`/`N`. The previous build
checked `toupper(ONGOING) == "Y"` which never matched — that bug left
CMENRF (and downstream CMSTDY/CMENDY/CMENRTPT) all-NA. Always check the
literal string used in the source CRF before writing a comparison.

---

## Controlled terminology mappings

### CMDOSFRM — CDISC FRM (C66726) — `map_dosfrm()`

| Raw (OpenClinica CL_207) | CDISC FRM |
|--------------------------|-----------|
| Aerosol | AEROSOL |
| Capsule | CAPSULE |
| Cream | CREAM |
| Gel | GEL |
| Ointment | OINTMENT |
| Patch | PATCH |
| Powder | POWDER |
| Spray | SPRAY |
| Suppository | SUPPOSITORY |
| Suspension | SUSPENSION |
| Tablet | TABLET |
| Liquid | LIQUID |
| Gas | GAS |
| Implant | IMPLANT |
| Chewable | CHEWABLE TABLET |
| Other | NA (no CT match) |

### CMDOSFRQ — CDISC FREQ (C71113) — `map_dosfrq()`

| Raw (OpenClinica CL_209) | CDISC FREQ |
|--------------------------|------------|
| "QD (once a day)" | QD |
| "BID (twice a day)" | BID |
| "TID (three times a day)" | TID |
| "QID (four times a day)" | QID |
| "QH (every hour)" | QH |
| "QM (every month)" | QM |
| "QOM (every other mo)" | QOM |
| "QOD (every other day)" | QOD |
| "PC (after meals)" | PC |
| "AC (before meals)" | AC |
| "PRN (as needed)" | PRN |
| numeric coded values (1–12), Other | NA |

### CMDOSU — CDISC UNIT (C71620) — `map_dosu()`

CDISC UNIT terms are mixed-case (e.g. `mg`, `mL`, `ug`); not uppercased.

| Raw | CDISC UNIT |
|-----|-----------|
| MG | mg |
| G | g |
| L | L |
| mL | mL |
| µg, mcg, ug | ug |
| Other, mg/m^2 | NA |

### CMROUTE — CDISC ROUTE (C66729) — `map_route()`

| Raw (OpenClinica CL_211) | CDISC ROUTE |
|--------------------------|-------------|
| Oral | ORAL |
| Topical | TOPICAL |
| Subcutaneous | SUBCUTANEOUS |
| Intravaneous (sic) | INTRAVENOUS |
| Intramuscular | INTRAMUSCULAR |
| Intraperitoneal | INTRAPERITONEAL |
| Intradermal | INTRADERMAL |
| Introacular (sic) | INTRAOCULAR |
| Nasal | NASAL |
| Vaginal | VAGINAL |
| Rectal | RECTAL |
| Transdermal | TRANSDERMAL |
| Inhalation | INHALATION |
| numeric coded values (1–14), Other | NA |

---

## P21 rules and fixes

### Resolved rules

#### SD0021 — Missing CMENDTC (232 → 0 unjustified)
**Root cause**: CMENRF was wired to `toupper(ONGOING) == "Y"` but the raw
values are "Yes"/"No". All 220 ONGOING=Yes rows produced NA CMENRF and
NA CMENDTC with no P21 justification.

**Fix** (`program/sdtm/cm.R`):
```r
is_ongoing = !is.na(ONGOING) & toupper(trimws(ONGOING)) == "YES",
CMENDTC  = dplyr::if_else(is_ongoing, NA_character_, CMENDTC_raw),
CMENRTPT = dplyr::case_when(
  is_ongoing       ~ "ONGOING",
  is.na(CMENDTC)   ~ "UNKNOWN",
  TRUE             ~ NA_character_),
CMENTPT  = dplyr::if_else(is.na(CMENDTC),
                          "DATE OF LAST ASSESSMENT", NA_character_),
```
**Coverage after fix**: 0 rows with `is.na(CMENDTC) & is.na(CMENRTPT)` —
all missing end dates justified by CMENRTPT/CMENTPT.

#### SD0022 — Missing CMSTDTC (14 → 0 unjustified)
**Root cause**: CRF rows where CMSTDAT was never entered.

**Fix**:
```r
CMSTRTPT = dplyr::if_else(is.na(CMSTDTC), "UNKNOWN", NA_character_),
CMSTTPT  = dplyr::if_else(is.na(CMSTDTC),
                          "DATE OF FIRST ASSESSMENT", NA_character_),
```
**Coverage after fix**: 0 rows with `is.na(CMSTDTC) & is.na(CMSTRTPT)`.

#### CT2002 — CMDOSFRM, CMDOSFRQ, CMDOSU, CMROUTE not in codelist
**Root cause**: Raw values copied verbatim from the OpenClinica codelists,
which carry CRF-friendly long forms ("BID (twice a day)") and free text
("Intravaneous", numeric codes) — none of which are valid CDISC CT terms.

**Fix**: Four `map_*()` functions translate OpenClinica → CDISC CT
(see mapping tables above). Unmappable values ("Other", "mg/m^2", numeric
coded values 8/3) return NA.

**Coverage after fix**: All non-NA values are valid CDISC CT terms.
**Residuals** (NA after mapping):
- CMDOSFRM NA: 22 rows (mostly "Other" + raw missing)
- CMDOSFRQ NA: 28 rows ("Other", numeric "8", + raw missing)
- CMDOSU   NA: 14 rows ("Other", "mg/m^2", + raw missing)
- CMROUTE  NA: 32 rows (numeric "3", + raw missing)

#### SD0013 — CMSTDTC after CMENDTC (1 → 0)
**Root cause**: CRF data-entry inversion for subject DF-193 — CMSTDAT
`2021-08-05`, CMENDAT `2021-08-03`.

**Fix**: Null out CMENDTC when it precedes CMSTDTC, and rely on the
SD0021 escape (CMENRTPT="UNKNOWN", CMENTPT="DATE OF LAST ASSESSMENT") to
justify the missing end date:
```r
CMENDTC = dplyr::if_else(
    !is.na(CMSTDTC) & !is.na(CMENDTC) & CMENDTC < CMSTDTC,
    NA_character_, CMENDTC),
```
Non-fabricating — drops the demonstrably wrong end date rather than
swapping or inventing.

#### SD1076 — Permissible variable added (CMRXCUI)
**Root cause**: CMRXCUI was a sponsor-added variable to surface RxNorm CUI.
It is not in the SDTMIG v3.3 CM specification.

**Fix**: Removed CMRXCUI from CM. The RxNorm CUI is preserved in
`data/raw/cm.rds` and could be carried in SUPPCM if a Supplemental
Qualifiers dataset is added later (currently no SUPP- dataset in pilot).
RXTTY/RXAUI/RXSTR similarly not surfaced.

#### SD1078 — All-NA permissibles (CMMODIFY, downstream CMSTDY/CMENDY/CMENRF)
**Root cause**: CMMODIFY mapped to raw item CMTRTLX which has only 1 row
populated in the entire export (1/4477 raw rows); after the CMTRTL filter
the column is empty. CMSTDY/CMENDY/CMENRF were never derived (set
`NA_integer_` / `NA_character_`).

**Fix**:
- Dropped CMMODIFY from final select() — no coder-modified names in the
  RxNorm Coding workflow used for this study.
- Derived CMSTDY/CMENDY from DM.RFSTDTC.
- Derived CMENRF via the new ONGOING/is_ongoing logic (now non-NA in 235
  rows; remaining 24 rows have a real CMENDTC and so CMENRF correctly
  carries NA).

#### SD1079 — Variable order
**Fix**: Final `select()` follows the SDTMIG v3.3 CM order:
STUDYID, DOMAIN, USUBJID, CMSEQ, CMTRT, CMDECOD, CMINDC, CMDOSE, CMDOSU,
CMDOSFRM, CMDOSFRQ, CMROUTE, CMSTDTC, CMENDTC, CMSTDY, CMENDY, CMSTRTPT,
CMSTTPT, CMENRTPT, CMENTPT, VISITNUM, VISIT.

(CMRXCUI removed; CMMODIFY removed; CMCLAS removed as it was being
populated with RxNorm term type — semantically not a CDISC drug class.
The RxNorm term type is preserved in `data/raw/cm.rds`.)

---

### Known data limitations

| Rule | Residual count | Reason |
|------|---------------|--------|
| CT2002 CMDOSFRM | 22 rows | Raw "Other" / blank — no CDISC FRM match |
| CT2002 CMDOSFRQ | 28 rows | Raw "Other" / numeric "8" / blank — no CDISC FREQ match |
| CT2002 CMDOSU | 14 rows | Raw "Other" / "mg/m^2" / blank — no CDISC UNIT match |
| CT2002 CMROUTE | 32 rows | Raw numeric "3" / blank — no CDISC ROUTE match |
| CMCLAS not populated | 259 rows | RxNorm coding workflow stores term type (BN/IN) not a real drug class. WHO-DD drug class is out of scope per sponsor decision. |
| CMDECOD same as raw CRF text | 259 rows | Raw `MEDNAME` is RxNorm preferred name; not further normalized. Production submission would refresh from a current RxNorm release. |

---

## Cross-domain dependencies

| Dependency | Direction | Notes |
|------------|-----------|-------|
| DM.RFSTDTC | CM reads DM | Required for CMSTDY / CMENDY derivation |

**Rebuild order**: DM must be rebuilt before CM when DM changes affect
RFSTDTC.

---

## Rebuild command

```bash
Rscript program/sdtm/cm.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
CM written: 259 rows x 22 cols
Unique subjects: 259
CMSTDTC  non-null: 245 / 259
CMENDTC  non-null:  24 / 259
CMENRTPT non-null: 235 / 259  (ONGOING justifications)
CMSTRTPT non-null:  14 / 259  (UNKNOWN start justifications)
CMSTDY   non-null: 211 / 259
CMENDY   non-null:  18 / 259
```

Sanity checks:
```r
cm <- readRDS("data/sdtm/cm.rds")
# No invalid CT
stopifnot(all(is.na(cm$CMDOSFRM) | cm$CMDOSFRM %in%
  c("AEROSOL","CAPSULE","CREAM","GEL","OINTMENT","PATCH","POWDER","SPRAY",
    "SUPPOSITORY","SUSPENSION","TABLET","LIQUID","GAS","IMPLANT",
    "CHEWABLE TABLET")))
# No date inversions
stopifnot(sum(!is.na(cm$CMSTDTC) & !is.na(cm$CMENDTC) &
              cm$CMSTDTC > cm$CMENDTC) == 0)
# All missing end dates justified
stopifnot(sum(is.na(cm$CMENDTC) & is.na(cm$CMENRTPT)) == 0)
stopifnot(sum(is.na(cm$CMSTDTC) & is.na(cm$CMSTRTPT)) == 0)
# No CMRXCUI / CMMODIFY / CMCLAS leakage
stopifnot(!any(c("CMRXCUI","CMMODIFY","CMCLAS") %in% colnames(cm)))
# CMSEQ unique within USUBJID
stopifnot(!anyDuplicated(cm[, c("USUBJID","CMSEQ")]))
# All CM subjects in DM
dm_ids <- readRDS("data/sdtm/dm.rds")$USUBJID
stopifnot(all(cm$USUBJID %in% dm_ids))
```
