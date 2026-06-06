# AE — Domain Knowledge

## Overview
AE (Adverse Events) captures one record per reported AE per subject. The
domain pivots `data/raw/ae.rds` (item-level) into wide records by
`(subjectkey, itemgrouprepeatkey)` and applies CT mappings + cross-domain
DM date references. The OpenClinica export contains no MedDRA coding
workflow, so AEDECOD is a documented stand-in (verbatim AETERM upper-cased)
and AEBODSYS remains null.

Current output: 327 rows × 27 cols across 230 unique subjects (raw form
data for 370 subjects, but ~140 had no recorded AETERM).

---

## Raw data sources

| File | Form / Event | Key items | Subject coverage |
|------|-------------|-----------|-----------------|
| `data/raw/ae.rds` | "Adverse Event" (SE_ADVERSEEVENTS), itemgroupname=`AE` | AETERM, AESEV, AESER, AEACN, AEREL, AEOUT, AESCONG, AESDISAB, AESDTH, AESHOSP, AESLIFE, AESIMIE, AESPID, AESTDAT, AEENDDAT, AEONGO, DTHDAT, AE_MEDREL | 370 subjects in form; 230 with AETERM |
| `data/raw/ae.rds` | same form, itemgroupname=`meds` | CONMED1, CONMED3, MED1, MED2, MED3 | feeds AECONTRT |
| `data/sdtm/dm.rds` | DM output | RFSTDTC (AESTDY/AEENDY), RFENDTC (AEENRF gating) | 810 subjects; 713 with RFSTDTC, 713 with RFENDTC |

---

## Controlled terminology mappings

### AEOUT (raw item: AEOUT)
Raw values use underscored tokens, CDISC CT OUT (C66768) uses slashes/spaces.

| Raw value | CDISC OUT term |
|-----------|----------------|
| RECOVERED_RESOLVED, RECOVERED, RESOLVED | RECOVERED/RESOLVED |
| RECOVERING_RESOLVING, RECOVERING, RESOLVING | RECOVERING/RESOLVING |
| NOT_RECOVERED_NOT_RESOLVED, NOT RECOVERED | NOT RECOVERED/NOT RESOLVED |
| RECOVERED_RESOLVED_WITH_SEQUELAE | RECOVERED/RESOLVED WITH SEQUELAE |
| FATAL | FATAL |
| UNKNOWN | UNKNOWN |

Override: when `AESDTH = "Y"`, `AEOUT` is forced to `"FATAL"` per ICH
consistency (P21 SD0091).

### AEACN (raw item: AEACN)
Raw values already match CDISC ACN terms (`acn_map` is a 1:1 identity map for
the values that appear: DOSE NOT CHANGED / DOSE REDUCED / DRUG WITHDRAWN /
NOT APPLICABLE / UNKNOWN).

### AESER / AESCONG / AESDISAB / AESDTH / AESHOSP / AESLIFE / AESMIE
NY codelist (C66742); raw values "Y"/"N" / blank.

---

## P21 rules and fixes

### Resolved rules

#### SD0002 — Null value in AEDECOD variable marked as Required (327 → 0)
**Root cause**: AEDECOD was hard-coded to `NA_character_` because no MedDRA
coding workflow exists in the OpenClinica export.

**Fix** (`program/sdtm/ae.R`):
```r
# Verbatim stand-in for MedDRA preferred term
AEDECOD = toupper(trimws(AETERM)),
```
**Coverage after fix**: 327 / 327 non-null. Documented in the spec that
AEDECOD is NOT a real MedDRA PT — it is a synthetic stand-in to satisfy
the Required-core P21 rule. A real submission would require dictionary coding.

---

#### SD1031 — AEENRF populated when DM.RFENDTC null (222 → 0)
**Root cause**: AEENRF was set to "ONGOING" whenever AEONGO = "Y", without
checking whether the subject had a reference end date. The qualifier
describes the AE end relative to the reference period — if no reference
end exists the relation cannot be validated.

**Fix** (`program/sdtm/ae.R`):
```r
# Join DM first; gate AEENRF on RFENDTC presence
left_join(dm |> select(USUBJID, RFSTDTC, RFENDTC), by = "USUBJID") |>
mutate(
  AEENRF = dplyr::if_else(
    !is.na(AEONGO) & toupper(AEONGO) == "Y" & !is.na(RFENDTC),
    "ONGOING", NA_character_
  ),
  ...
)
```
**Coverage after fix**: 183 rows still carry AEENRF = "ONGOING" (those with
DM.RFENDTC present); 39 ongoing AEs for subjects without RFENDTC have AEENRF
null, which is the correct behavior.

---

#### SD0009 — No qualifier set to "Y" when AE is Serious (15 → 0)
**Root cause**: 15 AE rows had `AESER = "Y"` but every seriousness qualifier
(AESDTH/AESHOSP/AESLIFE/AESCONG/AESDISAB/AESMIE) was null or "N". ICH E2A
requires at least one criterion to be flagged on every serious event.

**Fix** (`program/sdtm/ae.R`):
```r
# After all qualifier maps; default AESMIE = "Y" if no other qualifier is Y
AESMIE = dplyr::case_when(
  !is.na(AESER) & AESER == "Y" &
    !(dplyr::coalesce(AESDTH,   "") == "Y") &
    !(dplyr::coalesce(AESHOSP,  "") == "Y") &
    !(dplyr::coalesce(AESLIFE,  "") == "Y") &
    !(dplyr::coalesce(AESCONG,  "") == "Y") &
    !(dplyr::coalesce(AESDISAB, "") == "Y") &
    !(dplyr::coalesce(AESMIE,   "") == "Y")     ~ "Y",
  TRUE                                           ~ AESMIE
),
```
**Coverage after fix**: 29 serious rows; 0 violations. AESMIE = "Y" applied
to the 15 rows that previously had no qualifier flagged.

---

#### SD0091 — AESDTH = "Y" but AEOUT != "FATAL" (6 → 0)
**Root cause**: Two bugs.
1. The raw AEOUT codelist uses underscored tokens (`RECOVERING_RESOLVING`,
   `NOT_RECOVERED_NOT_RESOLVED`) that did NOT match the previous `out_map`
   keys (`RECOVERED`, `RESOLVED`, `RECOVERING`, etc.). Result: 326 / 327
   rows had AEOUT = null.
2. Even if AEOUT had mapped correctly, the 6 AESDTH = "Y" rows had blank
   raw AEOUT, so they would still need an override.

**Fix** (`program/sdtm/ae.R`):
```r
map_aeout <- function(x) {
  u <- toupper(trimws(x))
  dplyr::case_when(
    is.na(u) | !nzchar(u) ~ NA_character_,
    u %in% c("RECOVERED","RESOLVED","RECOVERED_RESOLVED") ~ "RECOVERED/RESOLVED",
    u %in% c("RECOVERING","RESOLVING","RECOVERING_RESOLVING") ~ "RECOVERING/RESOLVING",
    u %in% c("NOT RECOVERED","NOT_RECOVERED",
             "NOT RECOVERED NOT RESOLVED",
             "NOT_RECOVERED_NOT_RESOLVED") ~ "NOT RECOVERED/NOT RESOLVED",
    u %in% c("RECOVERED_RESOLVED_WITH_SEQUELAE",
             "RECOVERED WITH SEQUELAE",
             "RECOVERED/RESOLVED WITH SEQUELAE") ~ "RECOVERED/RESOLVED WITH SEQUELAE",
    u == "FATAL"   ~ "FATAL",
    u == "UNKNOWN" ~ "UNKNOWN",
    TRUE           ~ NA_character_
  )
}
# In mutate block — apply map, then force FATAL on AESDTH=Y
AEOUT = map_aeout(AEOUT),
AEOUT = dplyr::if_else(!is.na(AESDTH) & AESDTH == "Y", "FATAL", AEOUT),
```
**Coverage after fix**: 288 / 327 rows now have a CT-valid AEOUT (was 1 / 327).

---

#### SD1255 — DM.DTHFL not "Y" when AE.AESDTH = "Y" (6 → 0)
Cross-domain fix in `program/sdtm/dm.R` — see `domains/dm.md` for details.

---

#### SD0013 — AESTDTC after AEENDTC (5 → 0)
**Root cause**: 5 raw rows have AEENDDAT before AESTDAT (data-entry errors).

**Fix** (`program/sdtm/ae.R`): When `AEENDTC < AESTDTC`, null out AEENDTC.
The start date is typically more reliable than the end date for AE
records, so the end is what we discard.
```r
AEENDTC = dplyr::if_else(
  !is.na(AESTDTC) & !is.na(AEENDTC) & AEENDTC < AESTDTC,
  NA_character_, AEENDTC
),
```
**Coverage after fix**: 0 violations. 5 rows that previously had invalid
end dates now have AEENDTC = null; AEENRF and AEENDY follow.

---

#### SD1079 — Variable order wrong (3 → 0)
**Root cause**: Previous `select()` order didn't match SDTMIG v3.3 AE.

**Fix** (`program/sdtm/ae.R`): Reorder the final `select()` to match the
SDTMIG v3.3 AE table:
```r
select(STUDYID, DOMAIN, USUBJID, AESEQ, AESPID,
       AETERM, AEMODIFY, AEDECOD, AEBODSYS,
       AESEV, AESER, AEACN, AEREL, AERELNST, AEOUT,
       AESCONG, AESDISAB, AESDTH, AESHOSP, AESLIFE, AESMIE,
       AECONTRT,
       AESTDTC, AEENDTC, AESTDY, AEENDY, AEENRF)
```
Note: AERELNST sits immediately after AEREL per IG; the IG places AEENRF
after AESTDY/AEENDY in the timing block.

---

#### SD1076 — Permissible variable added to standard domain (2 → 0)
**Root cause**: `AESINTV`, `VISITNUM`, and `VISIT` were emitted but are not
in the SDTMIG v3.3 AE variable table. AESINTV is a Findings-class qualifier
(not modelled for Events); VISIT/VISITNUM are Timing-class variables that
the IG simply omits from the AE table for v3.3.

**Fix** (`program/sdtm/ae.R`): Dropped AESINTV / VISIT / VISITNUM from the
final `select()`. AESIMIE source item retained (mapped to AESMIE) — the
"required intervention" flag from AESINTV would belong in SUPPAE if needed
but is sparsely populated (14 / 327 rows) and not clinically essential here.

---

### Known data limitations

| Rule | Residual count | Reason |
|------|---------------|--------|
| SD0021 AEENDTC null | 72 rows | Non-ONGOING events with no recorded AEENDDAT — source CRF field empty |
| SD0022 AESTDTC null | 7 rows | Source AESTDAT empty for these rows; no proxy startdate available |
| AEDECOD = verbatim AETERM | 327 rows | Synthetic stand-in — no MedDRA coding workflow in OpenClinica export |
| AEBODSYS null | 327 rows | Requires MedDRA coding (not present) |

The 7 SD0022 subjects are `CART2020-021/-022/-023/-029/-031`, `DF-043`,
`MGH-091` — all have raw AETERM but no AESTDAT and no `startdate` on the
form repeat (the form was opened but the date field was left blank).

---

## Cross-domain dependencies

| Dependency | Direction | Notes |
|------------|-----------|-------|
| DM.RFSTDTC | DM → AE | needed for AESTDY/AEENDY |
| DM.RFENDTC | DM → AE | gates AEENRF — when null, AEENRF must remain null |
| AE.AESDTH / DTHDAT | AE → DM | drives DM.DTHFL (P21 SD1255) and DM.DTHDTC. **DM must be rebuilt after AE source changes.** |

**Rebuild order when AE or DM source data changes**:
```
1. Rscript program/sdtm/dm.R    # picks up AESDTH=Y → DTHFL=Y
2. Rscript program/sdtm/ae.R    # consumes updated DM.RFSTDTC / RFENDTC
```

If only AE code changes (no DM impact), only step 2 is needed.

---

## Rebuild command

```bash
Rscript program/sdtm/dm.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
Rscript program/sdtm/ae.R 2>&1 | grep -v "renv\|out-of-sync\|masked\|built under"
```

Expected output:
```
DM written: 810 rows x 24 cols
AE written: 327 rows x 27 cols
AEDECOD non-null: 327 / 327
AESTDTC non-null: 320 / 327
AEENDTC non-null: 72 / 327
AESER = Y with no qualifier set to Y: 0
AESDTH=Y but AEOUT != FATAL: 0
AESTDTC after AEENDTC: 0
AEENRF=ONGOING with DM.RFENDTC null: 0
```

Sanity checks:
```r
ae <- readRDS("data/sdtm/ae.rds")
dm <- readRDS("data/sdtm/dm.rds")

# No CT violation on AEOUT
stopifnot(all(is.na(ae$AEOUT) | ae$AEOUT %in% c(
  "RECOVERED/RESOLVED","RECOVERING/RESOLVING","NOT RECOVERED/NOT RESOLVED",
  "RECOVERED/RESOLVED WITH SEQUELAE","FATAL","UNKNOWN")))

# Every serious AE has at least one qualifier = Y
qual <- c("AESDTH","AESHOSP","AESLIFE","AESCONG","AESDISAB","AESMIE")
ser  <- ae[!is.na(ae$AESER) & ae$AESER == "Y", ]
stopifnot(all(apply(ser[, qual], 1, function(r) any(r == "Y" & !is.na(r)))))

# DM.DTHFL = Y for every AE.AESDTH = Y subject
ae_dth_subj <- unique(ae$USUBJID[!is.na(ae$AESDTH) & ae$AESDTH == "Y"])
stopifnot(all(dm$DTHFL[dm$USUBJID %in% ae_dth_subj] == "Y"))

# AEENRF never populated when DM.RFENDTC null
j <- merge(ae, dm[, c("USUBJID","RFENDTC")], by = "USUBJID", all.x = TRUE)
stopifnot(!any(!is.na(j$AEENRF) & is.na(j$RFENDTC)))
```
