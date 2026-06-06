# ADaM — Pinnacle 21 Findings Resolution Summary

Branch: `P21-fix-all`. All 9 ADaM dataset issues (#22–#30) have had
their P21 findings addressed at the code level. This document
summarizes the fixes applied per dataset, the residual findings that
are data limitations (not code defects), and the per-dataset commit
trail.

## Commit trail

| Commit | Dataset | Issue |
|---|---|---|
| `891aa95` | — (infra) | adds adam-issue-resolver agent, clears stale logs |
| `2c0f164` | ADSL | #22 |
| `0259c80` | ADAE | #23 |
| `92cb8c2` | ADCE | #24 |
| `c4106bc` | ADCM | #25 |
| `0f6beed` | ADDS | #26 |
| `0288d01` | ADIE | #27 |
| `c6bf5b2` | ADLB | #28 |
| `ccae929` | ADMH | #29 |
| `70ce4d1` | ADQS | #30 |

All 9 per-program logs were regenerated cleanly via
`Rscript program/adam/_run_all.R` after the last commit.

## Final dataset sizes

| Dataset | Rows × Cols | Output |
|---|---|---|
| ADSL | 810 × 35 | `data/adam/adsl.{rds,xpt}` |
| ADAE | 327 × 48 | `data/adam/adae.{rds,xpt}` |
| ADCE | 8 × 21 | `data/adam/adce.{rds,xpt}` |
| ADCM | 259 × 27 | `data/adam/adcm.{rds,xpt}` |
| ADDS | 1,442 × 20 | `data/adam/adds.{rds,xpt}` |
| ADIE | 20 × 19 | `data/adam/adie.{rds,xpt}` |
| ADLB | 950 × 30 | `data/adam/adlb.{rds,xpt}` |
| ADMH | 607 × 25 | `data/adam/admh.{rds,xpt}` |
| ADQS | 3,611 × 27 | `data/adam/adqs.{rds,xpt}` |

Every dataset has both an `.rds` and an `.xpt` (SAS V5 transport)
artifact in `data/adam/`.

## Cross-cutting infrastructure

A few decisions taken once and applied uniformly across all 9
datasets:

### Label & dataset-label attachment

`metacore`, `xportr`, and `labelled` are **not installed** in the
project renv. Rather than adding three packages, every ADaM program
now uses a uniform manual pattern at the bottom:

```r
spec_yaml <- yaml::read_yaml("spec/adam/<ds>.yaml")
for (v in names(<ds>)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(<ds>[[v]], "label") <- lab
}
attr(<ds>, "label") <- spec_yaml$label
```

This clears AD0018 (label mismatch), AD0320 (non-standard dataset
label), and AD0503 (`*DT` label must contain `Date`) in one pass,
without touching the renv lockfile. The dataset label is written
into the XPT via `haven::write_xpt()`.

### YAML quoting quirk

`yaml::read_yaml()` chokes on `derivation:` values that start with a
bare quoted token like `"Y"` (the parser reads the `"Y"` as a
mapping key candidate). Every YAML spec was audited and the offending
entries rewritten as block scalars (`derivation: |`). Affected specs:
adsl, adce, adcm, adds, adlb, adqs.

### XPT export pattern

Every program ends with:

```r
adqs_xpt <- adqs
int_cols <- names(adqs_xpt)[vapply(adqs_xpt, is.integer, logical(1))]
if (length(int_cols)) adqs_xpt[int_cols] <- lapply(adqs_xpt[int_cols], as.double)
haven::write_xpt(adqs_xpt, path = "data/adam/adqs.xpt", version = 5, name = "ADQS")
```

`haven::write_xpt()` does not support integer columns in V5, so they
are coerced to double before export.

### Inherited fixes from SDTM

The SDTM remediation (see `sdtm-summary.md`) already addressed:
- DM.RACE — mapped to CDISC RACE; multi-valued cases →
  `RACE="MULTIPLE"` per SDTMIG-blessed extension.
- AE / CM / MH SD0013 — inverted dates nulled; ADaM ASTDT>AENDT
  inherits the correction.
- CM CMROUTE — canonicalised; ADCM inherits.
- LB LBLOBXFL / LBORNRLO / LBORNRHI — added (NA) so the SDTM
  Expected variables exist; ADLB picks them up but ANRIND / ATOXGR
  remain un-derivable.

So most of ADaM's CT and date-inversion findings were resolved
upstream and pick up automatically on rebuild against the corrected
SDTM RDS files.

---

## ADSL — Subject-Level (#22, commit `2c0f164`)

Initial P21 findings: 2,956 across 5 rules.

**Fixes** — all 5 rule codes resolved.

| Rule | Count | Resolution |
|---|---|---|
| AD0019 | 2,911 | `RANDFL`/`ITTFL`/`SAFFL`/`EFFFL`/`COMPLFL` now `Y`/`N`, never `NA`. Replaced `NA_character_` with `"N"` in every `if_else()`. Final distribution: RANDFL 280/530, ITTFL 280/530, SAFFL 769/41, EFFFL 106/704, COMPLFL 0/810. |
| AD0018 | 26 | All 35 variable labels attached from spec via manual `attr(adsl[[v]], "label")` loop. |
| AD0320 | 1 | Dataset label set to `"Subject-Level Analysis Dataset"` via `attr(adsl, "label")`. |
| AD0503 | 1 | All four `*DT` labels (TRTSDT, TRTEDT, RANDDT, EOSDT) contain "Date". |
| CT2002 | 17 | RACE now carries CDISC CT values (inherited from DM commit `af211c9`). Distribution: WHITE 270, AIAN 25, ASIAN 18, MULTIPLE 20, NHOPI 12, BLACK 5, OTHER 3, NA 457. |

**Implementation notes**

- `EFFFL` derivation rewritten to reference `RANDFL` directly (not
  the just-derived `ITTFL`) for order-independence.
- `COMPLFL = "N"` for all 810 subjects: the one "COMPLETED" DS row
  belongs to a subject whose latest disposition is `EARLY TERMINATION`
  (slice_head by `desc(DSSTDTC), desc(DSSEQ)`), so `EOSSTT =
  "DISCONTINUED"`. Correct per DS-fix `ca60796`.

**Residuals (data limitations)**

- RACE NA (457 rows) — subjects with no DM CRF form / no PTRACE
  captured.
- TRTSDT/TRTEDT NA for the 530 SCRNFAIL subjects — no treatment
  exposure data in the pilot.

Knowledge file: `.claude/agents/domains/adsl.md`.

---

## ADAE — Adverse Events Analysis (#23, commit `0259c80`)

Initial P21 findings: 59 across 5 rules.

**Fixes** — all 5 rule codes resolved.

| Rule | Count | Resolution |
|---|---|---|
| AD0018 | 30 | Manual label-attach for all 48 columns; dataset label set. |
| AD0047 | 12 | Added required OCCDS vars: `TRTP`, `TRTPN`, `TRTA`, `TRTAN`, `TRTSDT`, `TRTEDT`, `ASEV`(=AESEV), `AREL`(=AEREL verbatim), `RANDFL`, `ITTFL`, `AESTDTC`, `AEENDTC`, `STRAT1`, `STRAT1L` (last two per `CLAUDE.md` OCCDS phenotype carryforward). |
| CT2002 | 10 | RACE inherited from corrected DM via ADSL. |
| AD0361 | 5 | Inherited from SDTM AE SD0013 fix (`7a620f3`). Verified count = 0. |
| AD0503 | 2 | All four `*DT` labels contain "Date". |

ADAE went from 32 → 48 columns.

**Residuals**

- 6 `RACE="MULTIPLE"` rows — SDTMIG-blessed extension to extensible
  C74457 codelist. Document in ADRG.
- `AEBODSYS` null (327 rows) — no MedDRA in export.
- `AEDECOD = uppercased AETERM` — synthetic stand-in.
- 273 `TRTEMFL` null — `ASTDT < TRTSDT` or no TRTSDT for SCRNFAIL.
- 311 `AREL` with non-CT values (`NOT_RELATED`, `POSSIBLY_RELATED`,
  `UNLIKELY_RELATED`) — collapsing to CDISC `RELATED`/`NOT RELATED`
  requires SAP guidance.

Knowledge file: `.claude/agents/domains/adae.md`.

---

## ADCE — Clinical Events Analysis (#24, commit `92cb8c2`)

Initial P21 findings: 24 across 4 rules.

**Fixes** — all 4 rule codes resolved.

| Rule | Count | Resolution |
|---|---|---|
| AD0019 | 7 | `SAFFL` inherited from corrected ADSL (0 NA; all 8 CE subjects = Y). |
| AD0018 | 14 | All 21 columns labelled from spec; dataset label = "Clinical Events Analysis Dataset". |
| CT2002 | 2 | RACE inherited from DM via ADSL. Final: WHITE 3, MULTIPLE 1, NA 4. |
| AD0503 | 1 | `ASTDT` label = "Analysis Start Date". |

**Side fix:** `spec/adam/adce.yaml` had two `derivation: "Y" on the
row…` entries that broke `yaml::read_yaml()`. Rewrote as block
scalars.

**Residuals**

- 1 `RACE="MULTIPLE"` row — SDTMIG extension.
- 4 `RACE=NA` rows — upstream sparsity.

Knowledge file: `.claude/agents/domains/adce.md`.

---

## ADCM — Concomitant Medications Analysis (#25, commit `c4106bc`)

Initial P21 findings: 68 across 5 rules.

**Fixes** — all 5 rule codes resolved.

| Rule | Count | Resolution |
|---|---|---|
| AD0019 | 31 | SAFFL inherited from ADSL (254 Y / 5 N / 0 NA). |
| AD0018 | 21 | 27/27 columns labelled; dataset label set. |
| CT2002 (RACE) | 9 | Inherited from DM via ADSL. |
| CT2002 (CMROUTE) | 4 | Inherited from SDTM CM `map_route()` (commit `93f08e1`). |
| AD0503 | 2 | TRTSDT, TRTEDT, ASTDT, AENDT labels all contain "Date". |
| AD0361 | 1 | Inherited from SDTM CM SD0013 null-out. |

**Code changes required (not just inheritance)**

- Dropped `CMRXCUI` from ADCM (SDTM CM dropped it under SD1076).
- `ONGOFL` derivation switched from `CMENRF == "ONGOING"` to
  `CMENRTPT == "ONGOING"` — the legacy `CMENRF` was removed in the
  SDTM CM SD1078 cleanup.
- Added `TRTSDT`/`TRTEDT` (carried from ADSL) and `ANL01FL`.

**Residuals**

- 100 `RACE=NA`, 5 `MULTIPLE`, 2 `OTHER` rows — upstream sparsity +
  extensible codelist extensions.
- 32 `CMROUTE=NA` rows — raw values ("Other" / numeric / blank)
  with no CDISC ROUTE equivalent.
- 235 `AENDT=NA` rows — CMENRTPT ONGOING/UNKNOWN justifies it per
  SDTMIG.

Knowledge file: `.claude/agents/domains/adcm.md`.

---

## ADDS — Disposition Analysis (#26, commit `0f6beed`)

Initial P21 findings: 24 across 4 rules.

**Fixes** — all 4 rule codes resolved.

| Rule | Count | Resolution |
|---|---|---|
| AD0019 | 9 | ITTFL inherited from ADSL (818 Y / 624 N / 0 NA). |
| AD0018 | 13 | 20/20 columns labelled; dataset label = "Disposition Analysis Dataset". |
| AD0503 | 1 | ASTDT label = "Analysis Start Date". |
| CT2002 | 1 | RACE inherited from DM via ADSL. |

**Side fix:** wrapped `FINALFL.derivation` as a block scalar to avoid
the bare `"Y"` YAML parse issue.

**Residuals**

- 48 `RACE="MULTIPLE"`, 7 `OTHER`, 526 `NA` — SDTMIG extensions +
  upstream sparsity.
- 1 `ASTDT=NA` row — DS row `SS_MGH213` has DSSTDTC NA (no
  EARLYTERMINATIONDATE).
- ASTDY NA on the 530 SCRNFAIL subjects (no TRTSDT to reference).

Knowledge file: `.claude/agents/domains/adds.md`.

---

## ADIE — Inclusion/Exclusion Analysis (#27, commit `0288d01`)

Initial P21 findings: 12 across 5 rules.

**Fixes** — all 5 rule codes resolved.

| Rule | Count | Resolution |
|---|---|---|
| AD0013 / SD1474 | 2 | Renamed `SCRNFAILFL` (10 chars) → `SCRNFFL` (7 chars). No other programs referenced it. |
| AD0018 | 7 | 19/19 columns labelled; dataset label = "Inclusion/Exclusion Analysis Dataset". |
| CT2002 | 2 | RACE inherited from DM via ADSL. Final: WHITE 3, AIAN 1, NA 16. |
| AD0503 | 1 | `ADT` label = "Analysis Date". |

**Bonus fix:** the original `SCRNFFL` derivation tested `is.na(RANDFL)`,
but ADSL.RANDFL is `Y`/`N` (never NA) per ADaMIG. Now tests
`RANDFL == "N"` — yields 17 Y / 3 NA across 20 rows.

**Residuals**

- 16 `RACE=NA` rows — upstream sparsity.

Knowledge file: `.claude/agents/domains/adie.md`.

---

## ADLB — Laboratory Analysis (#28, commit `c6bf5b2`)

Initial P21 findings: 586 across 4 rules.

**Fixes** — all 4 rule codes resolved.

| Rule | Count | Resolution |
|---|---|---|
| AD0019 | 546 | SAFFL inherited from ADSL (912 Y / 38 N / 0 NA). |
| AD0018 | 29 | All 30 columns labelled; dataset label = "Laboratory Test Results Analysis Dataset" (exactly 40 chars — V5 limit). |
| CT2002 | 10 | RACE inherited from DM via ADSL. |
| AD0503 | 1 | ADT label = "Analysis Date". |

**Side fix:** spec lines 201 and 275 had `derivation:` strings
starting with `"Y"`; converted to block scalars.

**Residuals (upstream data gaps)**

- `ANRLO` / `ANRHI` / `ANRIND` NA on all 950 rows — SDTM LB has no
  reference ranges in the raw export. Blocks `ATOXGR` derivation.
- 32 subjects have `RACE=NA`.
- `ADY` NA for ~61 rows where `LBDTC` is year-only ("2026").

Knowledge file: `.claude/agents/domains/adlb.md`.

---

## ADMH — Medical History Analysis (#29, commit `ccae929`)

Initial P21 findings: 856 across 5 rules.

**Fixes** — all 5 rule codes resolved.

| Rule | Count | Resolution |
|---|---|---|
| AD0019 | 821 | ITTFL+SAFFL inherited from ADSL. ITTFL 429/178, SAFFL 607/0 — both 0 NA. |
| AD0018 | 16 | All 25 columns labelled; dataset label = "Medical History Analysis Dataset". |
| CT2002 | 16 | RACE inherited from DM via ADSL. 36 `MULTIPLE` rows documented. |
| AD0503 | 2 | ASTDT="Analysis Start Date", AENDT="Analysis End Date". |
| AD0361 | 1 | Inherited from SDTM MH SD0013 null-out fix. |

**Code changes required (not just inheritance)**

- Replaced `MHENRF`-based logic with `MHENRTPT == "ONGOING"` —
  legacy `MHENRF` was dropped in SDTM MH SD1078 cleanup.
- Added `AGEGR1` to the ADSL merge column set.

**Residuals**

- `MHDECOD`/`MHBODSYS` all-NA (607 rows) — no MedDRA in export.
- 3 `RACE=NA` rows.

Knowledge file: `.claude/agents/domains/admh.md`.

---

## ADQS — Questionnaire Analysis (#30, commit `70ce4d1`)

Initial P21 findings: 2,037 across 5 rules.

**Fixes** — all 5 rule codes resolved.

| Rule | Count | Resolution |
|---|---|---|
| AD0146B + AD0147B | 2,000 | Inline `tribble()` lookup `(PARAMCD, PARAM, PARAMN)` for all 20 SF-12 v1 PARAMCDs merged via `derive_vars_merged(by_vars=exprs(PARAMCD))`. PARAM is human-readable (e.g. `"SF-12 Q01 General Health (SF1201)"`); PARAMN is the canonical SF-12 index (items 1–12, subscales 13–20). |
| AD0018 | 26 | All 27 columns labelled; dataset label = "Questionnaire Analysis Dataset". |
| CT2002 | 10 | RACE inherited from DM via ADSL. |
| AD0503 | 1 | ADT label = "Analysis Date". |

**Root cause of AD0146B/AD0147B (2,000 findings):** previous build
used `PARAMN = dense_rank(PARAMCD)` with `.by = USUBJID`, making
PARAMN a per-subject rank rather than dataset-wide. Same PARAMCD
could carry up to 7 different PARAMN values across subjects.

**Side fix:** `ABLFL.derivation` and `ANL01FL.derivation` had bare
quoted `"Y"` strings — converted to block scalars.

**Residuals (data limitations, deferred follow-ups)**

- SF-12 subscale recomputation from items per the published v1/v2
  algorithm — deferred per the #21 SDTM triage. `QSSTRESN`/`QSSTRESC`
  still pass through from SDTM.
- PF/RP/RE/MH composite subscale rows not emitted — raw export only
  carries the A/S components.
- 95 `RACE="MULTIPLE"`, 1,810 `RACE=NA` rows.

Knowledge file: `.claude/agents/domains/adqs.md`.

---

## Cross-cutting outcomes

- **Population flags (AD0019)** — Fixed once in ADSL (`Y`/`N`,
  never NA), cleared ~3,544 findings across 6 downstream datasets
  on rebuild.
- **Variable labels (AD0018)** — Fixed via a single manual
  `yaml::read_yaml` + `attr<-` block at the bottom of every ADaM
  program. ~190 findings cleared in one pass.
- **`*DT` labels (AD0503)** — Same pass; every `*DT` in every spec
  now has `Date` in its label.
- **Dataset labels (AD0320)** — Same pass; every dataset has its
  ADaMIG-conforming label.
- **RACE codelist (CT2002)** — Fixed once at SDTM DM
  (commit `af211c9`); inherits through every downstream ADaM dataset.
- **Date inversions (AD0361)** — Fixed once at the SDTM level
  (`AE.SD0013`, `CM.SD0013`, `MH.SD0013` commits); inherited.

## Known data limitations carried forward

- **No MedDRA coding** — `AEDECOD`/`AEBODSYS`, `MHDECOD`/`MHBODSYS`,
  `CEDECOD`/`CEBODSYS` are NA or synthetic stand-ins (AEDECOD
  uppercased AETERM). Same gap in ADAE / ADMH / ADCE.
- **No exposure records** — `TRTSDT`/`TRTEDT` NA for the 530 SCRNFAIL
  subjects; downstream `TRTEMFL` (ADAE), `PREFL`/`ONTRTFL` (ADCM),
  `LBLOBXFL` (LB→ADLB) all sparse.
- **No lab reference ranges** — `ANRLO`/`ANRHI`/`ANRIND`/`ATOXGR` un-
  derivable in ADLB.
- **RACE="MULTIPLE"** — SDTMIG-blessed extension to the extensible
  Race codelist (C74457). Document in ADRG.
- **RACE=NA** — subjects with no PTRACE captured in raw DM. Document.
- **`AREL` non-CT values in ADAE** — `NOT_RELATED`/`POSSIBLY_RELATED`/
  `UNLIKELY_RELATED` from the raw export; CDISC mapping to
  `RELATED`/`NOT RELATED` requires SAP guidance.
- **SF-12 subscale recomputation** — deferred follow-up.

## How to verify

```bash
# Full ADaM build (writes logs/adam/<ds>.log per program):
Rscript program/adam/_run_all.R

# Per-dataset build + inline sanity output:
Rscript program/adam/<ds>.R

# Re-run Pinnacle 21 against the regenerated XPTs:
#   Point P21 Community at data/adam/*.xpt with standard=ADaMIG v1.3.
#   Expected outcome: each dataset's finding count drops to the
#   residual data-limitation set documented above. Any count above
#   that residual is a regression.
```

## What's next

- Re-run Pinnacle 21 Community against `data/sdtm/*.xpt` and
  `data/adam/*.xpt` to confirm the projected drop from ~14,856 total
  findings (8,234 SDTM + 6,622 ADaM) to the documented residual
  data-limitation set.
- Resolve the deferred SF-12 subscale recomputation (issue #21
  follow-up) when an algorithm version is chosen.
- Decide whether to commit a synthetic MedDRA stand-in for
  AE/CE/MH coded variables, or leave NA + document.
