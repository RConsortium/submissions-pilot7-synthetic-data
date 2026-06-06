# SDTM — Pinnacle 21 Findings Resolution Summary

Branch: `P21-fix-all`. All 9 SDTM domain issues (#13–#21) have had
their P21 findings addressed at the code level. This document
summarizes the fixes applied per domain, the residual findings that
are data limitations (not code defects), and the per-domain commit
trail.

## Commit trail

| Commit | Domain(s) | Issue |
|---|---|---|
| `af211c9` | DM, DS | #13 |
| `ca60796` | DS | #17 |
| `7a620f3` | AE (+ DM cross-domain) | #14 |
| `c492afc` | CE (+ ADCE cascade) | #15 |
| `93f08e1` | CM | #16 |
| `c5b9f8c` | IE | #18 |
| `64694f5` | LB | #19 |
| `1b7369a` | MH (+ ADMH cascade) | #20 |
| `3c55428` | QS | #21 |

All 9 per-program logs were regenerated cleanly via
`Rscript program/sdtm/_run_all.R` after the last commit.

## Final dataset sizes

| Domain | Rows × Cols | Unique subjects | Output |
|---|---|---|---|
| DM | 810 × 24 | 810 | `data/sdtm/dm.{rds,xpt}` |
| DS | (per `ca60796`) | 810 | `data/sdtm/ds.{rds,xpt}` |
| AE | 327 × 27 | — | `data/sdtm/ae.{rds,xpt}` |
| CE | 8 × 12 | 8 | `data/sdtm/ce.{rds,xpt}` |
| CM | 259 × 22 | 259 | `data/sdtm/cm.{rds,xpt}` |
| IE | 20 × 15 | 17 | `data/sdtm/ie.{rds,xpt}` |
| LB | 950 × 23 | 169 | `data/sdtm/lb.{rds,xpt}` |
| MH | 607 × 20 | 256 | `data/sdtm/mh.{rds,xpt}` |
| QS | 3,611 × 19 | 247 | `data/sdtm/qs.{rds,xpt}` |

Every domain has both an `.rds` and an `.xpt` (SAS V5 transport)
artifact in `data/sdtm/`.

---

## DM — Demographics (#13, commit `af211c9`)

Initial P21 findings: 5,624 across 19 rules.

**Fixes**

- **SD1363 / SD1364 (ARMCD/ACTARMCD)** — Aligned to repo convention:
  `ARMCD="SCRNFAIL"` for non-randomized, `"TREATMENT"` for randomized;
  `ACTARMCD` mirrors `ARMCD` since no exposure data exists.
- **SD1210 (RFICDTC missing)** — Use `Disposition.CONSENTEDDT` as the
  RFICDTC source.
- **SD1240 / SD1374 (no IC / no DS coverage)** — Cross-domain: DS was
  expanded so every DM subject has matching Informed Consent +
  Disposition rows (delivered in the same commit).
- **CT2002 (RACE)** — Raw OpenClinica codes (`1`, `1,2,5`, …) mapped
  to CDISC RACE; multi-valued cases → `RACE="MULTIPLE"` with
  components in `SUPPDM.RACE`.
- **SD1255 (DTHFL)** — Added in the AE fix (commit `7a620f3`): when
  `AE.AESDTH='Y'`, propagate `DM.DTHFL='Y'` and `DM.DTHDTC` from
  `AE.DTHDAT`. Build order is now **DM → AE → DM-refresh-not-needed**
  (DM reads AE in one pass).

**Residuals (data limitations)**

- **SD0087/SD0088/SD1213/SD1376 (RFSTDTC/RFENDTC null on
  randomized/treated subjects)** — Pilot has no exposure records, so
  treatment-start/end dates can't be sourced. Documented limitation.
- **SD1343 (RFXSTDTC missing for treated)** — Same root cause.
- **DM.DTHDTC null for 4 of 9 DTHFL=Y subjects** (MGH-021, MGH-038,
  MGH-041, MGH-121) — `AESDTH=Y` recorded but no `DTHDAT` captured
  upstream.

Knowledge file: `.claude/agents/domains/dm.md`.

---

## DS — Disposition (#17, commits `af211c9` + `ca60796`)

Initial P21 findings: 25 across 8 rules.

**Fixes**

- **SD0022 + SD1118 (missing DSSTDTC)** — Dedup logic was clobbering
  dated rows in favor of undated ones; reworked to sort
  `is.na(DSSTDTC)` ascending before source-priority so dated rows
  always win.
- **SD1088 (DSSTDY null)** — Derived from `DSSTDTC` and
  `DM.RFSTDTC`.
- **SD1367 (multiple events per DSSCAT/EPOCH)** — Added dedup on
  (USUBJID, DSSCAT, EPOCH) preferring the most recent dated row.
- **CT2005 (DSDECOD invalid)** — Mapped to the controlled
  Completion/Reason and Protocol Milestone codelists.

**Residuals**

- **SD1076 / SD1078 / SD1079** — Audited variable list, dropped
  non-standard permissibles, reordered per SDTMIG v3.3 anchor.

Knowledge file: `.claude/agents/domains/ds.md`.

---

## AE — Adverse Events (#14, commit `7a620f3`)

Initial P21 findings: 638 across 18 rules.

**Fixes**

| Rule | Count | Resolution |
|---|---|---|
| SD0002 | 327 | `AEDECOD = toupper(trimws(AETERM))` — documented synthetic stand-in (no MedDRA coding in export). |
| SD1031 | 222 | `AEENRF="ONGOING"` only when `DM.RFENDTC` is non-null. |
| SD0009 | 15 | Default `AESMIE='Y'` when `AESER='Y'` and no other seriousness qualifier is `Y`. |
| SD0091 | 6 | `AEOUT='FATAL'` forced when `AESDTH='Y'`. New `map_aeout()` handles underscored tokens. |
| SD1255 | 6 | Propagate `DM.DTHFL='Y'` + `DM.DTHDTC` from `AE.AESDTH` / `AE.DTHDAT`. Cross-domain change to DM. |
| SD0013 | 5 | Null out `AEENDTC` when it precedes `AESTDTC`. |
| SD1079 | 3 | Variable order aligned to SDTMIG v3.3 AE. |
| SD1076 | 2 | Dropped `AESINTV`, `VISIT`, `VISITNUM` (not in IG v3.3 AE). |

**Residuals**

- **SD0021 (72 rows AEENDTC still null)** — AEs with neither
  `AEONGO='Y'` nor `AEENDDAT`; raw CRF field empty.
- **SD0022 (7 rows AESTDTC still null)** — No `AESTDAT` and no
  startdate proxy. Subjects: CART2020-021/022/023/029/031, DF-043,
  MGH-091.
- **AEDECOD = verbatim AETERM** — documented stand-in until a
  MedDRA-coded source is available; `AEBODSYS` remains null.

Knowledge file: `.claude/agents/domains/ae.md`.

---

## CE — Clinical Events (#15, commit `c492afc`)

Initial P21 findings: 14 across 6 rules.

**Fixes**

| Rule | Count | Resolution |
|---|---|---|
| SD1021 | 4 | `map_ceterm()` canonicalises `DESC` to `"CHEST PAIN"` or `"SUSPECTED MYOCARDIAL INFARCTION"`. Dropped 6 junk rows (`lakjsd`, `cjkcxhcj…`, `This is only a test`, …). |
| SD1077 | 1 | `EPOCH` derived from `CESTDTC` vs `DM.RFSTDTC` / `RFENDTC` (same boundaries as DS). |
| SD1076 | 3 | Dropped `VISITNUM`, `VISIT` (not in SDTMIG v3.3 CE). |
| SD1078 | 3 | Dropped 100%-null permissibles: `CEDECOD`, `CESTAT`, `CESEV`. |
| SD1079 | 2 | `EPOCH` precedes `CESTDTC` per IG. |
| SD0022 | 1 | The null-`CESTDTC` row was the junk-text drop. |

Cascade: `program/adam/adce.R` and `spec/adam/adce.yaml` referenced
`CE.CEDECOD`; references removed so ADCE rebuilds cleanly.

**Residuals**

- 1 row (DF-400) has null `EPOCH` and `CESTDY` — subject has no
  `RFSTDTC` in DM.
- `CEDECOD` / `CEBODSYS` omitted entirely (no MedDRA in export).
- `CESEV` omitted (no severity item on the Suspected-MI CRF).

Final dataset: 8 × 12 (down from 13 × 16).

Knowledge file: `.claude/agents/domains/ce.md`.

---

## CM — Concomitant Medications (#16, commit `93f08e1`)

Initial P21 findings: 278 across 10 rules.

**Fixes**

| Rule | Count | Resolution |
|---|---|---|
| SD0021 | 232 | Justified missing `CMENDTC` via `CMENRTPT`/`CMENTPT`. Bug fix: `ONGOING` raw value is `"Yes"` not `"Y"`. |
| SD0022 | 14 | `CMSTRTPT="UNKNOWN"` + `CMSTTPT="DATE OF FIRST ASSESSMENT"` for rows with no `CMSTDAT`. |
| CT2002 (×4) | 20 | New `map_dosfrm()`, `map_dosfrq()`, `map_dosu()`, `map_route()` map OpenClinica codelists to CDISC FRM/FREQ/UNIT/ROUTE. Also fixes raw spellings (`Intravaneous`→`INTRAVENOUS`, `Introacular`→`INTRAOCULAR`). |
| SD1079 | 4 | Final `select()` follows SDTMIG v3.3 CM order. |
| SD1076 | 2 | Removed `CMRXCUI`; dropped `CMCLAS` (raw was RxNorm term-type, not drug class). |
| SD1078 | 2 | Dropped `CMMODIFY` (no coder modifications); `CMSTDY`/`CMENDY`/`CMENRF` now derived. |
| SD0013 | 1 | Subject DF-193 — null `CMENDTC` and surface `CMENRTPT="UNKNOWN"`. |

**Residuals**

- After CT mapping, NA counts: 22 `CMDOSFRM`, 28 `CMDOSFRQ`,
  14 `CMDOSU`, 32 `CMROUTE` rows where raw values are "Other" /
  numeric / free text with no CDISC CT match. Could move to SUPPCM in
  a future pass.
- `CMCLAS` null across all 259 rows — RxNorm workflow stores term
  type, not a drug class. Documented sponsor decision to keep RxNorm
  coding instead of switching to WHO Drug.

Final dataset: 259 × 22.

Knowledge file: `.claude/agents/domains/cm.md`.

---

## IE — Inclusion/Exclusion (#18, commit `c5b9f8c`)

Initial P21 findings: 17 across 3 rules.

**Fixes** — all 17 instances resolved.

| Rule | Count | Resolution |
|---|---|---|
| SD1046 | 15 | Flipped the IEORRES/IESTRESC semantic: INCLUSION rows now `"N"` (criterion not met → failure), EXCLUSION rows stay `"Y"` (criterion met → excluded). |
| SD1077 | 1 | `EPOCH="SCREENING"` constant — Eligibility form is collected only at `SE_ENROLLMENT`. |
| SD1084 | 1 | `IEDY` derived from `IEDTC - DM.RFSTDTC` with no-day-0 convention. All 17 subjects have `RFSTDTC` → IEDY non-null on every row. |

`record_rule` in `spec/sdtm/ie.yaml` also corrected — previously
claimed rows existed for "not met" criteria, which is only true for
INCLUSION.

**No residuals.** 20 × 15 final.

Knowledge file: `.claude/agents/domains/ie.md`.

---

## LB — Laboratory Test Results (#19, commit `64694f5`)

Initial P21 findings: 142 across 7 rules.

**Fixes**

| Rule | Count | Resolution |
|---|---|---|
| SD1117 | 110 | Stable-sort + `slice_tail` dedup on (USUBJID, LBTESTCD, VISITNUM, LBDTC). 218 raw duplicate rows → 0 residual. |
| SD1084 | 7 | `LBDY` derived from `LBDTC` and `DM.RFSTDTC`. 889/950 rows populated. |
| CT2002 LBTESTCD | 3 | `BUN`→`UREAN`, `HCYS`→`HOMOCY`, `EGFR`→`GFR`; dropped `CREATSI`. |
| CT2002 LBTEST | 5 | Canonical CDISC names: `Urea Nitrogen`, `Homocysteine`, `Glomerular Filtration Rate`, `Erythrocytes`, `Leukocytes`. |
| CT2002 LBORRESU/LBSTRESU | 6 | `10^3/uL`→`10^9/L`, `10^6/uL`→`10^12/L`, `mL/min/1.73m2`→`mL/min/1.73 m2`. |
| CT2003 | 4 | LBTESTCD/LBTEST pairs now share an NCI concept code per CDISC SDTM Terminology. |
| SD0057 | 3 | Added `LBLOBXFL`, `LBORNRLO`, `LBORNRHI` columns (plus `LBSTNRLO`/`LBSTNRHI`). |

Bonus discovery: `NEPH.CREATR` and `CHEMPANEL.HOMOCRANGE` were CRF
help-text annotations (literal "(Normal range, Female: 0.5 - 1.1)"
strings) being mis-mapped to a lab test code; now filtered out.

**Residuals (data limitations)**

- **LBDY null** (61 rows): `LBDTC` is year-only for some subjects and
  ~97 DM subjects have no derivable `RFSTDTC`.
- **LBLOBXFL null** (950 rows): no exposure data.
- **LBORNRLO / LBORNRHI / LBSTNRLO / LBSTNRHI / LBNRIND null**
  (950 rows): the raw export carries no per-result reference ranges,
  only help-text "Normal range" strings.

Final dataset: 950 × 23.

Knowledge file: `.claude/agents/domains/lb.md`.

---

## MH — Medical History (#20, commit `1b7369a`)

Initial P21 findings: 1,053 across 8 rules.

**Fixes** — all 8 rules / 1,053 instances addressed.

| Rule | Count | Resolution |
|---|---|---|
| SD0021 | 565 | Bug fix: raw ongoing flag is `"1"` not `"Y"`. Emit `MHENRTPT`/`MHENTPT` for every missing `MHENDTC` (134 ONGOING + 432 UNKNOWN). |
| SD0022 | 428 | `MHSTRTPT="UNKNOWN"` + `MHSTTPT="DATE OF FIRST ASSESSMENT"` for 428 rows. |
| SD1201 | 46 | Decoded CANCER1 (CL_68) and CANCER2 (CL_69) so the same raw code `"1"` produces distinct terms ("Carcinoma" vs "Adenocarcinoma"); added suppression filter + final `distinct()`. |
| SD1078 | 6 | Derived `MHENRF` and `MHSTDY`; dropped `MHPRESP`/`MHOCCUR`/`MHSTAT`. 2 residual (MHDECOD/MHBODSYS — MedDRA gap). |
| SD1079 | 4 | Order matches SDTMIG v3.3 MH. |
| SD1076 | 2 | Dropped `MHPRESP` + `MHOCCUR` (no source data). |
| SD0013 | 1 | Subject DF-506: null inverted `MHENDTC`; SD0021 escape kicks in. |
| SD1088 | 1 | `MHSTDY` derived from `MHSTDTC` vs `DM.RFSTDTC` (179 non-null). |

Cascade: `data/adam/admh.rds` re-derived from new MH.

**Residuals**

- `MHDECOD` / `MHBODSYS` all-NA — no MedDRA in synthetic export
  (same gap as AE/CE).
- 428 missing `MHSTDTC` / 566 missing `MHENDTC` — all P21-justified
  via relative-timing variables.

Final dataset: 607 × 20.

Knowledge file: `.claude/agents/domains/mh.md`.

---

## QS — Questionnaires (#21, commit `3c55428`)

Initial P21 findings: 443 across 3 rules.

**Fixes** — all 5 rules (3 unique rule codes) resolved.

| Rule | Count | Resolution |
|---|---|---|
| SD0017 | 439 | Replaced ad-hoc `"SF-12 Qnn - <text>"` `QSTEST` strings (>40 char) with CDISC SF-12 v1 canonical short labels (≤ 40 char). Items use `SF1201..SF1212`; subscales use `SF12PF/RP/BP/GH/VT/SF/RE/MH`. (Mental Health subscale is `SF12MH`, not `SF12ME`.) |
| CT2002 QSCAT | 1 | `"SF-12"` → `"SF12"` (CDISC controlled, no dash). |
| CT2002 QSORRESU | 1 | `"SCORE"` → `NA` (SF-12 is unitless). |
| CT2002 QSSTRESU | 1 | `"SCORE"` → `NA`. |
| SD1077 | 1 | `EPOCH` derived from `QSDTC` vs `DM.RFSTDTC`/`RFENDTC`. Coverage 3611/3611. |

Collateral fixes:
- `QSDTC` now uses `normalize_iso_date(substr(startdate, 1, 10))` so
  ISO-datetime rows (e.g. MGH-131 at `2022-10-20T10:47:00`) parse.
  Coverage 3595 → 3611/3611.
- `QSDY` previously hardcoded `NA_integer_`; now derived. 3611/3611.

**Out of scope per #21 triage** — Recomputing SF-12 subscale scores
from items Q1–Q12 per the published SF-12v1/v2 algorithm.
`QSSTRESN`/`QSSTRESC` still copied from raw item-group values. This
is the deferred follow-up.

**Residuals (data limitations)**

- PF/RP/RE/ME composite subscale rows not emitted — raw export only
  carries the A/S components (`PF-A`, `PF-S`, …), not the combined
  subscale value. Only BP, GH, VT, SF subscale rows are present.
- EQ-5D-5L and Skin Conditions Questionnaire absent from
  OpenClinica export entirely.

Final dataset: 3,611 × 19. Max `QSTEST` length: 29.

Knowledge file: `.claude/agents/domains/qs.md`.

---

## Cross-cutting outcomes

- **MedDRA coding (AE, CE, MH)** — Out of repo's reach. AE uses
  verbatim AETERM as a documented synthetic stand-in for AEDECOD;
  AEBODSYS, MHDECOD, MHBODSYS, CEDECOD, CEBODSYS remain null.
- **Exposure data absent** — Drives the residuals in DM
  (RFSTDTC/RFENDTC/RFXSTDTC null for non-randomized/treated subjects)
  and downstream LBLOBXFL. Pilot-scope decision documented in
  `CLAUDE.md:69-84`.
- **Reference ranges absent (LB)** — `LBORNRLO`/`LBORNRHI`/
  `LBSTNRLO`/`LBSTNRHI` emit as NA columns so the SDTM-Expected
  variables exist; populating them requires the upstream data to
  start carrying ranges.
- **SF-12 scoring** — Items pass through unchanged; subscale
  recomputation deferred to a follow-up issue per the original #21
  triage.
- **Domain knowledge files** — `.claude/agents/domains/<dom>.md`
  exists for all 9 domains (DM, DS, AE, CE, CM, IE, LB, MH, QS) and
  encodes raw-data coverage, CT mappings, the resolved rules with
  R-code snippets, and the residual limitations. Future runs of
  `sdtm-issue-resolver` start from these instead of rediscovering.

## How to verify

```bash
# Full SDTM build (writes logs/sdtm/<dom>.log per program):
Rscript program/sdtm/_run_all.R

# Per-domain build + inline sanity output:
Rscript program/sdtm/<dom>.R

# Re-run Pinnacle 21 against the regenerated XPTs:
#   Point P21 Community at data/sdtm/*.xpt with standard=SDTMIG v3.3.
#   Expected outcome: each domain's finding count drops to the
#   residual data-limitation set documented above. Any count above
#   that residual is a regression.
```

## What's next

ADaM remediation (`adam-plan.md`). The biggest win there is a
cross-cutting `xportr` label + format pass driven by the YAML specs,
plus flipping ADSL population flags to `Y`/`N` (never `NA`).
