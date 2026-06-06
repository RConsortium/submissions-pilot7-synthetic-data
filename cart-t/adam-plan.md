# ADaM — Pinnacle 21 Findings & Remediation Plan

Source: P21 report `pinnacle21-report-2026-05-25T22-14-36-221.xlsx`,
posted to GitHub issues #22–#30 by the validation bot.

All 9 ADaM domain issues are **OPEN** on GitHub. No P21 fixes have
been merged for ADaM yet (the prior PR `af211c9` / `ca60796` only
touched SDTM DM/DS). ADSL has a draft from @jeffreyad pending review
(`adam/adsl-initial` branch, see #22).

| Dataset | Issue | Total findings | Unique rules |
|---|---|---|---|
| ADSL | [#22](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/22) | 2,956 | 5 |
| ADAE | [#23](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/23) | 59 | 5 |
| ADCE | [#24](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/24) | 24 | 4 |
| ADCM | [#25](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/25) | 68 | 5 |
| ADDS | [#26](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/26) | 24 | 4 |
| ADIE | [#27](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/27) | 12 | 5 |
| ADLB | [#28](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/28) | 586 | 4 |
| ADMH | [#29](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/29) | 856 | 5 |
| ADQS | [#30](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/30) | 2,037 | 5 |

**The same 3–4 rule codes recur across every ADaM dataset.** Three of
them — AD0018 (variable label mismatch), AD0503 (`*DT` must contain
`"Date"` in the label), and CT2002 (RACE codelist) — can be fixed
*once* with cross-cutting changes and will eliminate the vast majority
of findings. See [Cross-cutting fixes](#cross-cutting-fixes) below.

---

## ADSL — Subject-Level (#22)

**P21 findings (2,956 issues, 5 rules)**

| Rule | Count | Message |
|---|---|---|
| AD0019 | 810 | ITTFL subject-population flag value is null |
| AD0019 | 810 | RANDFL subject-population flag value is null |
| AD0019 | 809 | COMPLFL subject-population flag value is null |
| AD0019 | 482 | SAFFL subject-population flag value is null |
| AD0018 | 26 | Variable label mismatch between dataset and ADaM standard |
| CT2002 | 17 | RACE value not found in 'Race' extensible codelist |
| AD0320 | 1 | Non-standard dataset label |
| AD0503 | 1 | *DT must contain 'Date' in the label |

**Plan**

1. **AD0019 (population flags null) — 2,911 of 2,956 findings.**
   `RANDFL` / `ITTFL` / `COMPLFL` / `SAFFL` must be `Y` *or* `N`,
   never `NA`. Current code (`program/adam/adsl.R:97-101`) leaves them
   as `NA` for the negative case. Fix: replace each `if_else(..., "Y",
   NA_character_)` with `if_else(..., "Y", "N")`. ADaMIG requires
   `Y`/`N` for population flags by name (`RANDFL`, `ITTFL`,
   `SAFFL`, `EFFFL`, `COMPLFL`).
2. **AD0018 (label mismatches).** All ADSL variables show
   `LABEL=null`. The dataset is being written without column labels.
   Either: (a) attach CDISC-standard labels via `xportr::xportr_label()`
   with a metacore object, or (b) source labels from
   `spec/adam/adsl.yaml`. Same fix applies to every ADaM dataset.
3. **CT2002 (RACE).** Inherited from SDTM DM — fix the DM mapping
   (see `sdtm-plan.md` §DM CT2002) and ADSL picks up the corrected
   value.
4. **AD0320 (non-standard dataset label).** Set dataset label to
   `"Subject-Level Analysis Dataset"` via `xportr::xportr_label()`.
5. **AD0503 (`*DT` label).** A `*DT` variable (likely `RANDDT` or
   `TRTSDT`) is missing the word `Date` in its label. Audit all `*DT`
   labels.

**Pending:** ADSL rewrite from @jeffreyad (`adam/adsl-initial`
branch) introduces admiral-based derivations with placeholders for
`ARMCD`, `AGEGR1` cutpoints, `SAFFL` trigger, and `ITTFL` ARMCD
exclusions. Resolve those placeholders during review, then apply the
P21 fixes above on top.

---

## ADAE — Adverse Events Analysis (#23)

**P21 findings (59 issues, 5 rules)**

| Rule | Count | Message |
|---|---|---|
| AD0018 | 30 | Variable label mismatch between dataset and ADaM standard |
| AD0047 | 12 | Required variable is not present |
| CT2002 | 10 | RACE value not found in 'Race' extensible codelist |
| AD0361 | 5 | Value of ASTDT is greater than value of AENDT |
| AD0503 | 2 | *DT must contain 'Date' in the label |

**Plan**

1. **AD0018 / AD0503 / CT2002.** Cross-cutting — see end of file.
2. **AD0047 (12 required vars missing).** Audit
   `spec/adam/adae.yaml` against the OCCDS ADaMIG 1.3 + OCCDS IG 1.1
   required-variable list. Likely candidates: `TRTA`, `TRTAN`,
   `AOCCFL`, `AOCC02FL`, `ASEV`/`AESEVN`, `AREL`. Add the missing
   ones to spec + program.
3. **AD0361 (5 rows ASTDT > AENDT).** Direct fallout from SDTM AE
   SD0013 — fix at SDTM level (`sdtm-plan.md` §AE SD0013), ADAE
   inherits the correction.

---

## ADCE — Clinical Events Analysis (#24)

**P21 findings (24 issues, 4 rules)**

| Rule | Count | Message |
|---|---|---|
| AD0018 | 14 | Variable label mismatch between dataset and ADaM standard |
| AD0019 | 7 | SAFFL subject-population flag value is null |
| CT2002 | 2 | RACE value not found in 'Race' extensible codelist |
| AD0503 | 1 | *DT must contain 'Date' in the label |

**Plan**

1. **AD0018 / AD0503 / CT2002.** Cross-cutting — see end of file.
2. **AD0019 (SAFFL null).** Merge corrected `SAFFL` from ADSL (after
   ADSL fix #1 above) into ADCE. Confirm `derive_vars_merged()` with
   `new_vars=exprs(SAFFL)` is wired through
   `program/adam/adce.R`.

---

## ADCM — Concomitant Medications Analysis (#25)

**P21 findings (68 issues, 5 rules)**

| Rule | Count | Message |
|---|---|---|
| AD0019 | 31 | SAFFL subject-population flag value is null |
| AD0018 | 21 | Variable label mismatch between dataset and ADaM standard |
| CT2002 | 9 | RACE value not found in 'Race' extensible codelist |
| CT2002 | 4 | CMROUTE value not found in 'Route of Administration' codelist |
| AD0503 | 2 | *DT must contain 'Date' in the label |
| AD0361 | 1 | Value of ASTDT is greater than value of AENDT |

**Plan**

1. **AD0018 / AD0503 / CT2002 (RACE).** Cross-cutting.
2. **AD0019 (SAFFL null).** Same as ADCE — propagate corrected
   ADSL.SAFFL.
3. **CT2002 (CMROUTE).** Inherited from SDTM CM — fix at SDTM level
   (`sdtm-plan.md` §CM CT2002 CMROUTE).
4. **AD0361 (1 row ASTDT > AENDT).** Inherited from SDTM CM SD0013.

---

## ADDS — Disposition Analysis (#26)

**P21 findings (24 issues, 4 rules)**

| Rule | Count | Message |
|---|---|---|
| AD0018 | 13 | Variable label mismatch between dataset and ADaM standard |
| AD0019 | 9 | ITTFL subject-population flag value is null |
| AD0503 | 1 | *DT must contain 'Date' in the label |
| CT2002 | 1 | RACE value not found in 'Race' extensible codelist |

**Plan**

1. **AD0018 / AD0503 / CT2002.** Cross-cutting.
2. **AD0019 (ITTFL null).** Same fix as ADSL §1 — propagate `ITTFL`
   with `Y`/`N`, never `NA`, from corrected ADSL.

---

## ADIE — Inclusion/Exclusion Analysis (#27)

**P21 findings (12 issues, 5 rules)**

| Rule | Count | Message |
|---|---|---|
| AD0018 | 7 | Variable label mismatch between dataset and ADaM standard |
| CT2002 | 2 | RACE value not found in 'Race' extensible codelist |
| AD0013 | 1 | Illegal variable name: basic format is violated |
| AD0503 | 1 | *DT must contain 'Date' in the label |
| SD1474 | 1 | Invalid value for Variable Name |

**Plan**

1. **AD0018 / AD0503 / CT2002.** Cross-cutting.
2. **AD0013 / SD1474 (illegal variable name: `SCRNFAILFL`).**
   `SCRNFAILFL` exceeds the 8-character limit for SAS V5 XPT variable
   names. Rename to `SCRNFFL` (or `SCRFLFL`) in `program/adam/adie.R`
   and `spec/adam/adie.yaml`. ADaMIG also constrains analysis flag
   names to 8 chars.

---

## ADLB — Laboratory Analysis (#28)

**P21 findings (586 issues, 4 rules)**

| Rule | Count | Message |
|---|---|---|
| AD0019 | 546 | SAFFL subject-population flag value is null |
| AD0018 | 29 | Variable label mismatch between dataset and ADaM standard |
| CT2002 | 10 | RACE value not found in 'Race' extensible codelist |
| AD0503 | 1 | *DT must contain 'Date' in the label |

**Plan**

1. **AD0019 (SAFFL null) — 546 of 586 findings.** Same fix as
   ADCE/ADCM — propagate corrected ADSL.SAFFL into ADLB; once ADSL §1
   lands, this drops to 0.
2. **AD0018 / AD0503 / CT2002.** Cross-cutting.

**Known data-gap blockers (out of P21 scope):** `ANRIND` and `ATOXGR`
cannot be derived because SDTM LB has no reference range columns
(`CLAUDE.md:245-251`). Note in the spec and in define.xml.

---

## ADMH — Medical History Analysis (#29)

**P21 findings (856 issues, 5 rules)**

| Rule | Count | Message |
|---|---|---|
| AD0019 | 607 | ITTFL subject-population flag value is null |
| AD0019 | 214 | SAFFL subject-population flag value is null |
| AD0018 | 16 | Variable label mismatch between dataset and ADaM standard |
| CT2002 | 16 | RACE value not found in 'Race' extensible codelist |
| AD0503 | 2 | *DT must contain 'Date' in the label |
| AD0361 | 1 | Value of ASTDT is greater than value of AENDT |

**Plan**

1. **AD0019 (ITTFL+SAFFL null) — 821 of 856 findings.** Same as
   ADLB/ADDS — both are inherited from ADSL; fix ADSL §1 first.
2. **AD0018 / AD0503 / CT2002.** Cross-cutting.
3. **AD0361 (1 row).** Inherited from SDTM MH SD0013.

---

## ADQS — Questionnaire Analysis (#30)

**P21 findings (2,037 issues, 5 rules)**

| Rule | Count | Message |
|---|---|---|
| AD0146B | 1,000 | Inconsistent value for PARAM |
| AD0147B | 1,000 | Inconsistent value for PARAMN |
| AD0018 | 26 | Variable label mismatch between dataset and ADaM standard |
| CT2002 | 10 | RACE value not found in 'Race' extensible codelist |
| AD0503 | 1 | *DT must contain 'Date' in the label |

**Plan**

1. **AD0146B / AD0147B (PARAM/PARAMN inconsistent) — 2,000 of 2,037
   findings.** For any given `PARAMCD`, every row must carry the same
   `PARAM` and `PARAMN`. The current build at `program/adam/adqs.R:25-29`
   sets `PARAM=QSTESTCD` and likely doesn't ensure 1-to-1 consistency
   with `PARAMCD`. Fix: build a `(PARAMCD, PARAM, PARAMN)` lookup
   once, then `derive_vars_merged()` it onto the rows so the trio is
   always consistent. Also ensure `PARAM` carries the long
   instrument-specific label (not `QSTESTCD`).
2. **AD0018 / AD0503 / CT2002.** Cross-cutting.

---

## Cross-cutting fixes

Three rules fire across **every** ADaM dataset and together account
for ~75% of the non-flag findings. Fix them once.

### 1. AD0018 — Variable label mismatch (every dataset)

**Symptom:** every variable shows `LABEL=null` in the P21 sample
records.

**Root cause:** the build programs write `.rds` files without column
labels; xport/define.xml steps then carry empty labels.

**Fix:** at the bottom of every `program/adam/<ds>.R`, attach labels
from the YAML spec before saving. The canonical pattern is
`metacore` + `xportr`:

```r
library(metacore)
library(xportr)

spec <- spec_to_metacore("spec/adam/<ds>.yaml")
<ds> <- <ds> |>
  xportr_label(metacore = spec) |>
  xportr_format(metacore = spec) |>
  xportr_length(metacore = spec) |>
  xportr_type(metacore = spec)
```

Each YAML already has `label` populated for every variable
(per the binding rule in `CLAUDE.md:127-146`), so the lookup data
is in place.

### 2. AD0503 — `*DT` labels must contain `"Date"`

**Symptom:** at least one `*DT` variable per dataset (e.g., `ASTDT`,
`AENDT`, `RANDDT`, `TRTSDT`) has a label that doesn't contain the
substring `Date`.

**Fix:** part of cross-cutting fix #1 — once `xportr_label()` runs
against the spec, audit the `label` field for every `*DT` in every
`spec/adam/*.yaml` and ensure it contains `Date`. Typical fix:
`"Analysis Start"` → `"Analysis Start Date"`.

### 3. CT2002 — RACE codelist

**Symptom:** raw RACE codes (`1`, `1,2,5`, …) flow from DM into every
downstream ADaM dataset.

**Fix:** at the SDTM level (`sdtm-plan.md` §DM CT2002). Map raw codes
to CDISC RACE; for multi-valued cases set `RACE="MULTIPLE"` with
components in `SUPPDM.RACE`. ADaM picks up the corrected value
automatically.

### 4. AD0019 — Population flags must be `Y` or `N`

**Symptom:** `RANDFL`/`ITTFL`/`SAFFL`/`COMPLFL` are `NA` in ADSL,
which propagates to every OCCDS/BDS dataset.

**Fix:** in `program/adam/adsl.R:97-101`, replace
`NA_character_` with `"N"` in every `if_else()` for the population
flags. The ADaMIG-named flags (`RANDFL`, `ITTFL`, `SAFFL`, `EFFFL`,
`COMPLFL`) require `Y`/`N`, never null.

---

## Estimated impact of cross-cutting fixes

Applying the four cross-cutting fixes alone would clear roughly:

| Fix | Cleared findings | Datasets affected |
|---|---|---|
| AD0019 (ADSL pop flags `Y`/`N`) | 3,544 | ADSL, ADCE, ADCM, ADDS, ADLB, ADMH |
| AD0018 (apply spec labels via xportr) | 182 | every dataset |
| AD0503 (`*DT` label audit) | 11 | every dataset |
| CT2002 RACE (fix at DM) | 77 | every dataset |
| **Subtotal** | **~3,814** of 6,622 ADaM findings | |

The remaining ~2,800 findings are dominated by ADQS PARAM/PARAMN
consistency (2,000) and ADAE missing required vars (12 of the rule,
but a small per-finding count) plus a handful of dataset-specific
items (ADIE `SCRNFAILFL` rename, ASTDT>AENDT inheritance, etc.).

## Workflow

After applying fixes for a dataset:

1. Run the per-dataset build: `Rscript program/adam/<ds>.R`.
2. Run the full ADaM batch: `Rscript program/adam/_run_all.R` and
   inspect `logs/adam/<ds>.log`.
3. Re-export XPT (with labels via `xportr`) and re-run Pinnacle 21.
4. Post a fresh findings comment on the issue and close it when the
   relevant rules drop to 0.

## Ordering

Recommended order — each step unblocks the next:

1. **SDTM DM CT2002 RACE** (clears CT2002 from every ADaM dataset).
2. **ADSL AD0019 flags `Y`/`N`** (clears 3,544 findings across 6 ADaM
   datasets).
3. **Cross-cutting AD0018 + AD0503** via `xportr` in every ADaM
   program (clears ~190 findings).
4. **ADQS PARAM/PARAMN consistency** (clears 2,000 findings).
5. **ADAE AD0047 required vars audit** + dataset-specific items
   (ADIE rename, SDTM-inherited AD0361 fixes).
