# SDTM — Pinnacle 21 Findings & Remediation Plan

Source: P21 report `pinnacle21-report-2026-05-25T22-06-00-560.xlsx`,
posted to GitHub issues #13–#21 by the validation bot.

All 9 SDTM domain issues are **OPEN** on GitHub. **DM (#13)** and **DS
(#17)** have had an initial pass of fixes landed already (commits
`af211c9`, `ca60796`); the issues remain open pending the rest of the
checklist. Rules below are the *full* P21 set as last posted — re-run
P21 to confirm what is now resolved.

| Domain | Issue | Total findings | Unique rules | Status |
|---|---|---|---|---|
| DM | [#13](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/13) | 5,624 | 19 | partial fix landed (`af211c9`) |
| AE | [#14](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/14) | 638 | 18 | not started |
| CE | [#15](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/15) | 14 | 6 | not started |
| CM | [#16](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/16) | 278 | 10 | not started |
| DS | [#17](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/17) | 25 | 8 | partial fix landed (`ca60796`) |
| IE | [#18](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/18) | 17 | 3 | not started |
| LB | [#19](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/19) | 142 | 7 | not started |
| MH | [#20](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/20) | 1,053 | 8 | not started |
| QS | [#21](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/21) | 443 | 3 | not started |

---

## DM — Demographics (#13)

**P21 findings (5,624 issues, 19 rules)**

| Rule | Count | Message |
|---|---|---|
| SD1210 | 809 | Missing value for RFICDTC |
| SD1240 | 809 | No Informed Consent Obtained record in DS domain for subject |
| SD1374 | 808 | No Disposition record found for subject |
| SD1363 | 530 | ARMCD/ARM is populated for a subject not assigned to treatment |
| SD1364 | 530 | ACTARMCD/ACTARM is populated for a subject who wasn't treated |
| SD1343 | 280 | Missing value for RFXSTDTC when subject is treated |
| SD0087 | 279 | RFSTDTC is not provided for a randomized subject |
| SD0088 | 279 | RFENDTC is not provided for a randomized subject |
| SD1213 | 279 | RFSTDTC is not provided for a treated subject |
| SD1376 | 279 | RFENDTC is not provided for a treated subject |
| CT2002 | — | RACE value not found in 'Race' extensible codelist (samples: `1`, `1,2,5`, etc.) |

**Plan**

1. **SD1363/SD1364 (ARM/ACTARM population).** Repo convention is
   `ARMCD="SCRNFAIL"`/`ARMCD="TREATMENT"` for randomized vs.
   not-randomized subjects, with `ACTARMCD` mirroring `ARMCD` because
   no exposure data exists (`CLAUDE.md:54-86`). Commit `af211c9`
   already aligned this; verify by re-running P21.
2. **SD1210 (RFICDTC missing).** Use `Disposition.CONSENTEDDT` as the
   RFICDTC source (already wired at `program/sdtm/dm.R:50-57` after
   `af211c9`); confirm zero-NA on the randomized cohort.
3. **SD1240 / SD1374 (no IC / no DS record).** Cross-domain coverage:
   commit `af211c9` adds Informed Consent + Disposition rows in DS so
   every DM subject has matching DS coverage. Verify P21 re-run.
4. **SD0087/SD0088/SD1213/SD1376 (RFSTDTC/RFENDTC null).** These are
   blocked on the missing exposure data (`CLAUDE.md:69-84`). Decision
   needed: keep `NA` and accept the findings as data limitations, or
   define a proxy (e.g., `RFICDTC` for `RFSTDTC`, last visit date for
   `RFENDTC`).
5. **SD1343 (RFXSTDTC missing for treated).** Same root cause — no
   exposure. Accept as data limitation in pilot scope.
6. **CT2002 (RACE values `1`, `1,2,5`, …).** RACE is being stored as
   raw OpenClinica codes rather than CDISC CT terms. Map raw codes →
   CDISC RACE codelist values; for multi-valued cases set
   `RACE="MULTIPLE"` and populate `SUPPDM.RACE` with the components.

---

## AE — Adverse Events (#14)

**P21 findings (638 issues, 18 rules)**

| Rule | Count | Message |
|---|---|---|
| SD0002 | 327 | Null value in AEDECOD variable marked as Required |
| SD1031 | 222 | Value for AEENRF is populated when RFENDTC is null |
| SD0021 | 28 | Missing End Time-Point value |
| SD0009 | 15 | No qualifiers set to 'Y' when AE is Serious |
| SD0022 | 7 | Missing Start Time-Point value |
| SD0091 | 6 | AEOUT is not 'FATAL' when AESDTH='Y' |
| SD1255 | 6 | DTHFL does not equal 'Y' when AE.AESDTH = 'Y' |
| SD0013 | 5 | AESTDTC is after AEENDTC |
| SD1079 | 3 | Variable is in wrong order within domain |
| SD1076 | 2 | Model Permissible variable added into standard domain |

**Plan**

1. **SD0002 (AEDECOD null).** Source has no MedDRA coding output
   (`program/sdtm/ae.R:57-58`). Needs maintainer decision:
   (a) integrate licensed MedDRA dictionary, or (b) populate
   `AEDECOD` with the verbatim `AETERM` as a synthetic stand-in for
   the pilot. Document the choice in `spec/sdtm/ae.yaml`.
2. **SD1031 (AEENRF populated while RFENDTC null).** Couple `AEENRF`
   derivation to `DM.RFENDTC` — only populate when both sides exist.
   Same root cause as DM SD0088.
3. **SD0021 / SD0022 (missing start/end time-points).** Decide whether
   to leave `AESTDTC`/`AEENDTC` `NA` (current behavior via
   `normalize_iso_date()`) or impute partial dates per a chosen rule
   (e.g., year-only → `YYYY-01-01` floor).
4. **SD0009 (no SAE qualifier `Y` when AE is Serious).** When
   `AESER='Y'`, at least one of `AESCAN`/`AESCONG`/`AESDISAB`/
   `AESDTH`/`AESHOSP`/`AESLIFE`/`AESMIE` must be `Y`. Add a derivation
   that defaults `AESMIE='Y'` when no other seriousness reason
   applies, or surface the actual raw CRF item.
5. **SD0091 / SD1255 (death consistency).** When `AESDTH='Y'`:
   set `AEOUT='FATAL'` in AE, and propagate `DTHFL='Y'` to DM.
6. **SD0013 (AESTDTC > AEENDTC).** 5 rows have inverted dates. Add a
   validation step and either correct via raw lookup or set bad
   `AEENDTC` to `NA`.
7. **SD1079 / SD1076 (variable order / permissible vars).** Reorder
   per SDTMIG v3.3 anchor `AE+Specification`; drop or move non-standard
   permissibles into `SUPPAE`.

---

## CE — Clinical Events (#15)

**P21 findings (14 issues, 6 rules)**

| Rule | Count | Message |
|---|---|---|
| SD1021 | 4 | Unexpected character value in CETERM (`chest pain`, `cest pain`, `lakjsd`) |
| SD1076 | 3 | Model Permissible variable added into standard domain |
| SD1078 | 3 | Permissible variable with missing value for all records |
| SD1079 | 2 | Variable is in wrong order within domain |
| SD0022 | 1 | Missing Start Time-Point value |
| SD1077 | 1 | Regulatory Expected variable EPOCH not found |

**Plan**

1. **SD1021 (CETERM free-text).** Clean `CETERM` to a controlled set
   ("Chest pain", "Suspected MI", etc.) via a small lookup at
   `program/sdtm/ce.R:33`; raw verbatims (`chest pain`, `cest pain`,
   `lakjsd`) should map to canonical terms or be dropped.
2. **SD1077 (EPOCH missing).** Add `EPOCH` derivation tied to DM
   reference dates (SCREENING / TREATMENT / FOLLOW-UP). Source the
   epoch convention from `program/sdtm/ds.R` so DS and CE agree.
3. **SD1078 (all-NA permissibles).** Drop the columns that are all
   `NA` from the build, or populate when source data exists.
4. **SD1079 / SD1076.** Reorder per SDTMIG anchor; drop or move
   non-standard permissibles to `SUPPCE`.
5. **SD0022.** Same partial-date decision as AE.

---

## CM — Concomitant Medications (#16)

**P21 findings (278 issues, 10 rules)**

| Rule | Count | Message |
|---|---|---|
| SD0021 | 232 | Missing End Time-Point value |
| SD0022 | 14 | Missing Start Time-Point value |
| CT2002 | 7 | CMDOSFRM value not in 'Dosage Form' codelist |
| CT2002 | 5 | CMDOSFRQ value not in 'Frequency' codelist |
| CT2002 | 4 | CMDOSU value not in 'Unit' codelist |
| CT2002 | 4 | CMROUTE value not in 'Route' codelist |
| SD1079 | 4 | Variable is in wrong order within domain |
| SD1076 | 2 | Model Permissible variable added into standard domain |
| SD1078 | 2 | Permissible variable with missing value for all records |
| SD0013 | 1 | CMSTDTC is after CMENDTC |

**Plan**

1. **SD0021 (CMENDTC missing).** When `ONGOING="Y"` on the raw CRF,
   set `CMENRTPT="ONGOING"` and `CMENTPT="DATE OF LAST ASSESSMENT"`
   rather than leaving `CMENDTC` blank — the P21 rule allows the
   relative timing variables in place of an absolute date.
2. **SD0022.** Same partial-date rule as AE/CE.
3. **CT2002 ×4 (CMDOSFRM/CMDOSFRQ/CMDOSU/CMROUTE).** Map raw
   OpenClinica values ("Aerosol", "Capsule", "Ointment", "Suppository",
   "Other", …) to the CDISC CT codelists. Where a raw value has no
   equivalent (e.g., "Other"), populate the original verbatim into
   `SUPPCM` and leave the CT variable `NA`.
4. **Coding system (CMDECOD/CMCLAS).** Source is RxNorm not WHO Drug
   (`spec/sdtm/cm.yaml:12`); maintainer decision required to either
   keep RxNorm + document the substitution, or invest in WHO Drug
   licensing.
5. **SD0013.** 1 row with `CMSTDTC > CMENDTC` — fix the raw record or
   blank `CMENDTC`.
6. **SD1079 / SD1076 / SD1078.** Reorder and drop/move as in AE/CE.

---

## DS — Disposition (#17)

**P21 findings (25 issues, 8 rules)**

| Rule | Count | Message |
|---|---|---|
| SD0022 | 7 | Missing Start Time-Point value |
| SD1118 | 7 | Neither DSSTDTC, DSDTC nor DSSTDY are populated |
| SD1076 | 2 | Model Permissible variable added into standard domain |
| SD1079 | 2 | Variable is in wrong order within domain |
| SD1088 | 2 | DSSTDY variable value is not populated |
| SD1367 | 2 | Multiple disposition events for the same DSSCAT and EPOCH |
| CT2005 | 1 | DSDECOD not in 'Completion/Reason for Non-Completion' codelist (when DSCAT=='DISPOSITION EVENT') |
| CT2005 | 1 | DSDECOD not in 'Protocol Milestone' codelist (when DSCAT=='PROTOCOL MILESTONE') |
| SD1078 | 1 | Permissible variable with missing value for all records |

**Status:** addressed by commit `ca60796` ("resolve P21 CT2005,
SD0022/1118, SD1088, SD1367 findings"). Confirm via P21 re-run.

**Plan (residual)**

1. **SD1076 / SD1079 / SD1078.** Audit the variable list against
   SDTMIG anchor `DS+Specification`; reorder and drop/move non-standard
   permissibles.

---

## IE — Inclusion/Exclusion (#18)

**P21 findings (17 issues, 3 rules)**

| Rule | Count | Message |
|---|---|---|
| SD1046 | 15 | IESTRESC is not 'N' when IECAT ='INCLUSION' |
| SD1077 | 1 | Regulatory Expected variable EPOCH not found |
| SD1084 | 1 | IEDY variable value is not populated |

**Plan**

1. **SD1046 (IESTRESC must be `N` for INCLUSION failures).** Current
   code hard-codes `IEORRES='Y'` (`program/sdtm/ie.R:52`). Convention
   for IE: a row exists *because* the criterion was failed (inclusion)
   or met (exclusion). Set `IESTRESC='N'` for `IECAT='INCLUSION'`
   rows; keep `IESTRESC='Y'` for `IECAT='EXCLUSION'`.
2. **SD1077 (EPOCH).** Set `EPOCH='SCREENING'` for all IE rows.
3. **SD1084 (IEDY).** Derive `IEDY` from `IEDTC` and `DM.RFSTDTC`
   using `admiral::derive_vars_dy()` or equivalent.

---

## LB — Laboratory Test Results (#19)

**P21 findings (142 issues, 7 rules)**

| Rule | Count | Message |
|---|---|---|
| SD1117 | 110 | Duplicate records |
| SD1084 | 7 | LBDY variable value is not populated |
| CT2002 | 5 | LBTEST value not in 'Laboratory Test Name' codelist |
| CT2003 | 4 | LBTESTCD and LBTEST values do not have same Code in CDISC CT |
| CT2002 | 3 | LBORRESU value not in 'Unit' codelist (`10^3/uL`, `10^6/uL`, `mL/min/1.73m2`) |
| CT2002 | 3 | LBSTRESU value not in 'Unit' codelist |
| CT2002 | 3 | LBTESTCD value not in 'Laboratory Test Code' codelist |
| SD0057 | 1 | SDTM Expected variable LBLOBXFL not found |
| SD0057 | 1 | SDTM Expected variable LBORNRHI not found |
| SD0057 | 1 | SDTM Expected variable LBORNRLO not found |

**Plan**

1. **SD1117 (110 duplicate records).** Largest issue by count. Add a
   `distinct(USUBJID, LBTESTCD, LBDTC, LBORRES)` step in
   `program/sdtm/lb.R` and investigate root cause (multiple visits
   captured at same datetime? merge artifact?).
2. **SD1084 (LBDY null).** Both `LBDTC` and `DM.RFSTDTC` exist
   (per @jeffreyad's comment on #19) — derive `LBDY` with
   `admiral::derive_vars_dy()`.
3. **CT2002 / CT2003 (LBTESTCD / LBTEST / units).** Align the fixed
   in-program LBTESTCD table at `program/sdtm/lb.R:21-…` to CDISC Lab
   CT pairs; map raw units (`10^3/uL`→`10*3/uL`, `10^6/uL`→`10*6/uL`,
   `mL/min/1.73m2`→`mL/min/1.73m2` — verify against current CDISC UNIT
   release).
4. **SD0057 (LBLOBXFL / LBORNRHI / LBORNRLO missing).** Add the
   columns to the spec and build. Reference ranges are absent from the
   raw CRF (`CLAUDE.md:245-251`) — emit empty `NA` columns with
   correct labels and lengths so the *Expected variable* check
   passes; populate when ranges become available.

---

## MH — Medical History (#20)

**P21 findings (1,053 issues, 8 rules)**

| Rule | Count | Message |
|---|---|---|
| SD0021 | 565 | Missing End Time-Point value |
| SD0022 | 428 | Missing Start Time-Point value |
| SD1201 | 46 | Duplicate records in MH domain |
| SD1078 | 6 | Permissible variable with missing value for all records |
| SD1079 | 4 | Variable is in wrong order within domain |
| SD1076 | 2 | Model Permissible variable added into standard domain |
| SD0013 | 1 | MHSTDTC is after MHENDTC |
| SD1088 | 1 | MHSTDY variable value is not populated |

**Plan**

1. **SD0021 / SD0022 (start/end null).** Same partial-date decision
   as AE. For ongoing conditions, populate `MHENRTPT="ONGOING"` so
   missing `MHENDTC` is justified by the relative-timing pair.
2. **SD1201 (46 duplicates).** Add a dedup step on
   `(USUBJID, MHTERM, MHSTDTC, MHCAT)` in `program/sdtm/mh.R`.
3. **SD0013 (1 inverted row).** Found a row `MHSTDTC=2020-03-03`
   after `MHENDTC=2020-02-…` — correct or blank `MHENDTC`.
4. **SD1088 (MHSTDY null).** Derive `MHSTDY` from `MHSTDTC` and
   `DM.RFSTDTC` (same approach as LBDY/IEDY).
5. **SD1076 / SD1078 / SD1079.** Reorder per SDTMIG anchor; drop or
   move non-standard permissibles to `SUPPMH`.
6. **MedDRA coding (out-of-scope blocker).** `MHDECOD`/`MHBODSYS` are
   `NA` — same maintainer call as AE.

---

## QS — Questionnaires (#21)

**P21 findings (443 issues, 3 rules)**

| Rule | Count | Message |
|---|---|---|
| SD0017 | 439 | Invalid value for QSTEST variable |
| CT2002 | 1 | QSCAT value not in 'Category of Questionnaire' codelist (`SF-12`) |
| CT2002 | 1 | QSORRESU value not in 'Unit' codelist (`SCORE`) |
| CT2002 | 1 | QSSTRESU value not in 'Unit' codelist (`SCORE`) |
| SD1077 | 1 | Regulatory Expected variable EPOCH not found |

**Plan**

1. **SD0017 (439× QSTEST invalid).** `QSTEST` values like
   `"SF-12 Q05 - Limited …"` exceed the 40-char `QSTEST` length and
   aren't the CDISC SF-12 instrument-CT short labels. Align both
   `QSTESTCD` and `QSTEST` to the published CDISC SF-12 codelist
   (`QSTEST` ≤ 40 chars).
2. **CT2002 (QSCAT='SF-12').** Map to the controlled spelling — the
   CDISC `QSCAT` value is `"SF12"` (or per-version equivalent), not
   `"SF-12"`. Update `program/sdtm/qs.R` accordingly.
3. **CT2002 (QSORRESU/QSSTRESU='SCORE').** `"SCORE"` isn't a CDISC
   UNIT term. Either leave `QSORRESU`/`QSSTRESU` `NA` for unit-less
   scores or pick the appropriate CDISC unit per subscale (the SF-12
   subscales are unitless on the 0–100 scale).
4. **SD1077 (EPOCH).** Add `EPOCH` derivation tied to DM reference
   dates.
5. **SF-12 scoring algorithm (deferred).** Per the triage on #21, the
   8 subscale scores are currently copied from raw, not recomputed
   from items. A separate follow-up issue should pick an algorithm
   (SF-12v1 vs v2, US-norm based vs raw) and re-derive `QSSTRESN` —
   this is independent of the P21 fixes above.

---

## Cross-cutting items

- **CT alignment is blocked on #9** (CDISC CT version pinning). Until
  a CT release is chosen, the CT2002/CT2003/CT2005 fixes above need
  to be re-checked once the canonical CT version is fixed.
- **MedDRA coding (AE/MH).** Decision pending — license vs. synthetic
  stand-in. Affects AE.SD0002, MH coded variables, downstream ADAE
  and ADMH.
- **No exposure data.** DM RFXSTDTC/RFXENDTC null and downstream
  treatment-emergent flags are blocked by the source data
  (`CLAUDE.md:69-84`). Pilot-level decision: accept and document, or
  synthesize EX.
- **Variable order / permissible vars (SD1076/SD1079).** A single pass
  across all 9 specs against SDTMIG v3.3 will close most of these in
  one batch.

## Workflow

After applying fixes for a domain:

1. Run the per-domain build: `Rscript program/sdtm/<dom>.R`.
2. Run the full SDTM batch: `Rscript program/sdtm/_run_all.R` and
   inspect `logs/sdtm/<dom>.log`.
3. Re-export XPT and re-run Pinnacle 21.
4. Post a fresh findings comment on the issue and close it when the
   relevant rules drop to 0.
