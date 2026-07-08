# Intake summary — CATH (NCT00789880 / ADVN CATH 03-01)

**Step 1 deliverable.** Parsed from `NCT00789880.json` (full ClinicalTrials.gov v2 record,
`hasResults: true`, results posted 2013-01-22) + the user-provided protocol PDF (`protocol_extract.txt`).
Machine-readable calibration targets are in `targets.json`; the protocol gate attestation is in
`preconditions.json` (status **formal**, PASS).

## Trial in one paragraph
A single-center (UCSD), randomized, quadruple-blind, placebo-controlled **Phase 2** substudy testing
whether **oral vitamin D3 (cholecalciferol) 4000 IU/day for 21 days** changes skin innate-immune
peptide expression. It enrolls **three diagnostic groups** — atopic dermatitis (AD), psoriasis, and
non-atopic healthy controls (Non-AD) — each split across **Vitamin D3** and **Placebo** arms. The
endpoints are **continuous mRNA-expression changes** (cathelicidin **CAMP**/LL-37, **HBD-3**, and the
TH2 cytokine **IL-13**) from baseline (Day 0) to **Day 21**, measured by qRT-PCR in lesional and
non-lesional skin punch biopsies. There is no survival/PFS endpoint — so this build follows the
**RAVE** (non-oncology) generalization of the skill, not the FLAURA2/oncology path.

## Design (→ `targets.json:design`)
- Phase 2; allocation RANDOMIZED; parallel; masking QUADRUPLE.
- Arms: **Vitamin D3** (4000 IU/day × 21 d) vs **Placebo** (identical capsule).
- Enrollment **82 actual**; primary completion Dec 2009; 3 US centers (recruited Jan–Nov 2009).
- Analysis horizon = Day 21 (`ADMIN_CENSOR_DAY = 21`).

## Cells & participant flow (→ `targets.json:cells`, `:dropouts`)
| Group | Arm | Started | Completed | Dropouts (reason) |
|---|---|---|---|---|
| Non-AD | Vitamin D3 | 16 | 15 | 1 Withdrawal by Subject |
| Non-AD | Placebo | 16 | 15 | 1 Protocol Violation |
| AD | Vitamin D3 | 16 | 15 | 1 Protocol Violation |
| AD | Placebo | 18 | 15 | 1 Adverse Event + 2 Withdrawal by Subject |
| Psoriasis | Vitamin D3 | 8 | 8 | — |
| Psoriasis | Placebo | 8 | 8 | — |
| **Total** | | **82** | **76** | **6** (1 AE, 2 protocol violation, 3 withdrawal) |

Outcome denominators are completers with paired biopsies: AD 15/15, Non-AD 15/15, Pso 8/8.

## Baseline characteristics (→ `targets.json:baseline`) — pooled (per-cell in JSON)
Age 32.5 (SD 10.9) y · 44 F / 38 M · 100% US · White 54 / Asian 10 / Black 9 / Other 9, Hispanic 9 ·
BMI 25.3 (4.9) · Fitzpatrick I–VI = 3/20/26/22/4/6 (+1 unknown) · serum 25-OH-D 29.2 (11.2) ng/mL ·
creatinine 0.8 (0.2) · PTH 34.4 (11.4) · calcium 9.4 (0.4) · **total IgE 553 (1825) kU/L — driven by
AD** (AD-VitD 1870, AD-Plac 725) vs Non-AD/Pso ~46–85 (atopy signal; key L₀ group effect).

## Endpoint targets (→ `targets.json:outcomes`)
Change baseline→Day21 in relative mRNA abundance (mean ± SD, "cycle number" units), per
group × skin-compartment × arm. Non-AD = non-lesional only. Highlights:
- **CAMP** AD lesional: VitD −0.4±2.8 vs Plac 0.1±2.4; Non-AD non-lesional VitD 1.2±2.4 vs 0.3±1.7;
  Pso lesional VitD −0.9±3.0 vs 0.2±3.2.
- **HBD-3** AD lesional VitD −0.1±7.3 vs −0.8±2.8; Pso lesional VitD 0.8±5.3 vs −1.6±4.4.
- **IL-13** AD lesional VitD −0.7±2.8 vs 1.1±2.7; Pso lesional VitD −2.1±4.6 vs −0.1±4.1.

**Substantive read:** point estimates are small and noisy with overlapping arms (the trial's own
conclusion was a null — e.g. CAMP AD lesional p≈0.7). The SCM therefore encodes a **near-null,
group/skin-specific treatment effect mediated by the serum 25-OH-D rise**, with cell-specific
measurement variance — never a large arm→endpoint draw.

## Adverse events (→ `targets.json:adverse_events`)
**0 serious AEs, 0 deaths, no AE at ≥5% frequency** (CTGov AE module empty above threshold). One
AE-related discontinuation (AD-Placebo) is the only AE-attributable exit. The AE domain is therefore
sparse: low per-visit hazard for mild, non-serious vitamin-D/procedure complaints, with the single
AD-Placebo AE flagged `AEACN=DRUG WITHDRAWN` for AE↔DS traceability.

## What is NOT in the published results (filled from protocol + literature, flagged `model`/`paperclip`)
Absolute baseline biopsy expression levels (only the *change* is posted), saliva/tape-stripping
cathelicidin, PASI, bacterial colony counts, IL-4, RAST values, and per-cell exact Fitzpatrick/race
splits. These are simulated as protocol-faithful but **non-calibrated** forms.
