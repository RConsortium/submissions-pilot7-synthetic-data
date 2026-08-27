# CRF Schema — CATH (NCT00789880 / ADVN CATH 03-01)

Derived from **Protocol ADVN CATH 03-01 v3.0 (July 7, 2009), §10.6 Schedule of Activities**
(Table 10.1 psoriatic subjects, Table 10.2 AD/non-AD subjects — user-provided protocol PDF), with
endpoint/AE field sets shaped by the posted ClinicalTrials.gov results (`intake/NCT00789880.json`).
Each form lists its visit grid, CDISC-aligned variables, protocol source, and how it maps onto the
structural causal model (SCM) in `DAG.md`.

Therapeutic area: **dermatology / innate immunity** (vitamin D3 → skin antimicrobial-peptide
expression) — *not* oncology. The oncology module of the template (RECIST/tumor/PFS-OS) is replaced
by a **skin innate-immunity module**: qRT-PCR mRNA expression of CAMP/LL-37, HBD-3, IL-13 in
lesional/non-lesional biopsies, plus PASI, saliva/tape-stripping cathelicidin, and bacterial colony
counts. The endpoint is a **continuous change score** (Day21 − Baseline), not a time-to-event.

## Arms × diagnostic groups

| ARMCD | ARM | DXGROUP | Intervention | n started |
|---|---|---|---|---|
| `VITD` | Vitamin D3 | Non-AD / AD / Psoriasis | cholecalciferol 4000 IU/day PO ×21 d | 16 / 16 / 8 |
| `PLAC` | Placebo | Non-AD / AD / Psoriasis | identical placebo capsule PO ×21 d | 16 / 18 / 8 |

Source: `ctgov: armsInterventionsModule` — "Subjects received a 21-day course of oral vitamin D3
(cholecalciferol, 4,000 international units \[IU\])" / "…vitamin D3-placebo". Randomization within
diagnostic group (≈1:1). **DXGROUP** is a fixed baseline stratum, not randomized.

## Trial-level visit grid (protocol §10.6)

| Visit code | VISITNUM | Study day | Nominal time | Source |
|---|---|---|---|---|
| `SCRN` (Visit 1) | 1 | −8 | Screening (Day −7 to −10): consent, history, **eligibility bloods** | SoA Table 10.1 |
| `BASE` (Visit 2) | 2 | 0 | Baseline / **randomization** / start drug / **baseline biopsies+saliva+tape+microbial** | SoA |
| `D21`  (Visit 3) | 3 | 21 | Day 21 (window 18–27): end of dosing / **repeat biopsies + bloods** | SoA |
| `UNSCH` | 9 | event-driven | Unscheduled (insufficient sample / AE / confirm) | SoA §10.6.4 |
| `ADMIN_CENSOR` | — | day 21 | Analysis snapshot = Day-21 visit | CTGov timeFrame "Baseline to Day 21" |

**Bloods** (vitamin D 25-OH, calcium, PTH, creatinine, total IgE, RAST) are drawn at **Visit 1
(screening)** and **Visit 3 (Day 21)** (Table 10.1). **Skin biopsies / tape stripping / saliva /
microbial** are at **Visit 2 (baseline)** and **Visit 3** — so the biomarker baseline is Day 0 and
the change is Day21 − Day0. Compartments: AD & psoriasis have **lesional + non-lesional**; non-AD
healthy controls have **non-lesional only**.

---

## Form inventory

### Form: Demographics — `DM`
- **Domain**: DM. **Source**: SoA "Medical history" (Screening) + `ctgov: baselineCharacteristicsModule`.
- **Visit grid**: `SCRN`.
- **Variables**: USUBJID, SITEID, ARMCD (`VITD`/`PLAC`), ARM, DXGROUP (NONAD/AD/PSO), AGE (y), SEX (M/F),
  RACE, ETHNIC (HISPANIC/NOT), COUNTRY (USA), HEIGHT (cm), WEIGHT (kg), BMI (kg/m²), FITZPATRICK (I–VI),
  RFSTDTC.
- **SCM mapping**: L₀. Per-cell age/BMI/sex/race/Fitzpatrick from `targets.json:baseline`.

### Form: Inclusion/Exclusion — `IE`
- **Domain**: IE. **Source**: protocol §8.1–8.2 (Screening + Baseline).
- **Visit grid**: `SCRN`. **Variables**: USUBJID, IETESTCD, IECAT (INCL/EXCL), IEORRES (Y/N).
  Support of L₀ = eligible population (age 18–70, definitive dx, normal screening Ca/PTH/creatinine,
  no vit-D >400 IU/day). All simulated patients pass.

### Form: Medical History — `MH`
- **Domain**: MH. **Source**: SoA "Medical history / Medication history" (Screening).
- **Visit grid**: `SCRN`. **Variables**: USUBJID, MHTERM, MHDECOD, MHCAT (DX/comorbidity), disease-duration.
- **SCM mapping**: L₀ `dxgroup` + atopy history (parent of IgE).

### Form: Disease Diagnosis & PASI — `DD`
- **Domain**: SC/RS. **Source**: SoA "Diagnosis of Psoriasis", "Fitzpatrick Skin Scale", "PASI Scoring"
  (Baseline, Day21); protocol Appendix I diagnostic criteria.
- **Visit grid**: `BASE`, `D21` (PASI psoriasis only; diagnosis at `SCRN`/`BASE`).
- **Variables**: USUBJID, VISIT, DXGROUP, PASI (0–72, psoriasis only), PASIDTC.
- **SCM mapping**: L₀ disease stratum; Lₜ PASI change (psoriasis; non-calibrated, model-flagged).

### Form: Vital Signs — `VS`
- **Domain**: VS. **Source**: SoA "Vital signs" (Baseline, Day21, Unscheduled).
- **Visit grid**: `BASE`, `D21`. **Variables**: USUBJID, VISIT, VSDTC, SYSBP, DIABP, PULSE, TEMP, WEIGHT.

### Form: Skin Biopsy AMP Expression — `SB` *(primary endpoint form)*
- **Domain**: LB (cat GENE_EXPRESSION / qRT-PCR). **Source**: SoA "Skin biopsies … for AMP levels"
  (Baseline, Day21); `ctgov: outcomeMeasuresModule` (CAMP, HBD-3 primary; IL-13 secondary).
- **Visit grid**: `BASE`, `D21`. One row per (patient × visit × compartment).
- **Variables**: USUBJID, VISIT, SBDTC, COMPART (LESIONAL/NONLESIONAL), **CAMP**, **HBD3**, **IL13**,
  IL4 (relative mRNA abundance, qRT-PCR "cycle number" units). Non-AD: NONLESIONAL only.
- **SCM mapping**: Lₜ central state. **The endpoint lives here**: Day21 expression = Baseline + δ,
  with δ = group×skin natural drift + arm effect mediated by Δ(serum 25-OH-D) + shared `f_amp`
  frailty + cell-specific noise. The published change targets (`targets.json:outcomes`) calibrate δ.

### Form: Saliva AMP — `SA`
- **Domain**: LB. **Source**: SoA "Saliva collection … cathelicidin" (Baseline, Day21).
- **Visit grid**: `BASE`, `D21`. **Variables**: USUBJID, VISIT, CAMP_SALIVA (BCA-normalized),
  TOTPROT. **SCM mapping**: Lₜ secondary AMP readout (model-flagged; no published target).

### Form: Tape Stripping AMP — `TS`
- **Domain**: LB. **Source**: SoA "Tape stripping" (Baseline, Day21); protocol §14.2.11
  (tape-strip vs punch-biopsy correlation).
- **Visit grid**: `BASE`, `D21`. **Variables**: USUBJID, VISIT, COMPART, CAMP_TAPE.
- **SCM mapping**: Lₜ noninvasive cathelicidin proxy, correlated with `SB.CAMP` via `f_amp`
  (validates tape-vs-biopsy; model-flagged).

### Form: Laboratory — Bloods — `LB`
- **Domain**: LB. **Source**: SoA "Blood collection" (Screening, Day21); `ctgov: baseline` serum panel.
- **Visit grid**: `SCRN` (= baseline labs), `D21`.
- **Variables**: USUBJID, VISIT, LBDTC, **VITD25OH** (ng/mL), **CALCIUM** (mg/dL), **PTH** (pg/mL),
  **CREAT** (mg/dL), **IGE** (kU/L), RAST (class 0–6), LBNRIND.
- **SCM mapping**: `VITD25OH` is the **treatment mediator** — VitD arm rises Day0→Day21 (drives biopsy
  δ); placebo flat. Calcium/PTH/creatinine track safety (no hypercalcemia at 4000 IU). IGE = atopy
  marker (AD ≫ others). Baseline serum panel calibrated to `targets.json:baseline`.

### Form: Microbial / Bacterial Colony — `MB`
- **Domain**: MB. **Source**: SoA "skin microbial evaluation / bacterial colony counts" (Baseline, Day21).
- **Visit grid**: `BASE`, `D21`. **Variables**: USUBJID, VISIT, COMPART, CFU (colony-forming units, log10).
- **SCM mapping**: Lₜ skin flora (model-flagged; no published target).

### Form: Study Drug Exposure — `EX`
- **Domain**: EX. **Source**: SoA "Oral Vitamin D3 / placebo" (Baseline→Day21); protocol §9.1/§9.5.
- **Visit grid**: `BASE` (dispense) → `D21` (pill count).
- **Variables**: USUBJID, EXTRT (VITAMIN D3 / PLACEBO), EXDOSE (4000), EXDOSU (IU), EXROUTE (ORAL),
  EXSTDTC, EXENDTC, COMPLIANCE_PCT (returned pill count). **SCM mapping**: A-node exposure driving
  the 25-OH-D rise mediator.

### Form: Adverse Events — `AE`
- **Domain**: AE. **Source**: SoA "Adverse events" (Baseline→Day21+7); `ctgov: adverseEventsModule`.
- **Visit grid**: event-driven. **Variables**: USUBJID, AETERM, AEDECOD (MedDRA PT), AEBODSYS (SOC),
  AESEV, AETOXGR (1–4), **AESER** (Y/N — seriousness is a column, *no separate SAE form*), AEREL,
  AEACN (incl. `DRUG WITHDRAWN`), AEOUT, AESTDTC.
- **SCM mapping**: sparse — CTGov posted **0 serious, no PT ≥5%**. Low per-patient hazard for mild
  vitamin-D GI complaints (constipation/nausea/bloating) + procedure events (biopsy-site reaction,
  tape erythema). The single AD-Placebo AE-discontinuation carries `AEACN=DRUG WITHDRAWN` (AE↔DS gate).

### Form: Pregnancy Test — `PG`
- **Domain**: RP. **Source**: SoA "Pregnancy test" (Screening, Baseline, Day21; women of childbearing
  potential). **Visit grid**: `SCRN`, `BASE`, `D21`. **Variables**: USUBJID, VISIT, PGRES (NEGATIVE).
  All negative (positive = exclusion). Low-salience; minimal model.

### Form: Disposition — `DS`
- **Domain**: DS. **Source**: SoA "Randomization" (Baseline); `ctgov: participantFlowModule`.
- **Visit grid**: `BASE` (randomized) + event-driven.
- **Variables**: USUBJID, DXGROUP, ARMCD, DSDECOD (RANDOMIZED/COMPLETED/DISCONTINUED), DSTERM
  (COMPLETED STUDY / ADVERSE EVENT / PROTOCOL VIOLATION / WITHDRAWAL BY SUBJECT), DSSTDY.
- **SCM mapping**: Yₜ disposition. Targets: 76/82 completed; 6 dropouts by exact reason×cell
  (`targets.json:dropouts`).

### Form: Endpoint Summary — `RE`
- **Domain**: RS (derived). **Source**: primary+secondary endpoint definitions; `ctgov: outcomeMeasuresModule`.
- **Visit grid**: derived (Day21 − Baseline).
- **Variables**: USUBJID, DXGROUP, ARMCD, **dCAMP_LES / dCAMP_NL**, **dHBD3_LES / dHBD3_NL**,
  **dIL13_LES / dIL13_NL** (change scores), dVITD25OH, dPASI, dIGE, COMPLETER (Y/N), DISPOSITION.
- **SCM mapping**: Yₜ **derived purely from the SB/LB trajectory** (Day21 − Baseline) — never drawn
  directly. Calibrated to `targets.json:outcomes` on completers.

**Out of scope (research bio-samples with no published marginal target — excluded under KISS):**
skin-swab genomic flora (stored for future analysis, no result posted), serum storage aliquots,
qRT-PCR housekeeping normalization detail. A collection flag could be emitted but adds no calibratable
signal.

---

## SoA-to-form crosswalk (visit × form)

| Visit (day) | DM | IE | MH | DD | VS | SB | SA | TS | LB | MB | EX | AE | PG | DS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SCRN (−8) | ✓ | ✓ | ✓ | ✓ |  |  |  |  | ✓ |  |  |  | ✓ |  |
| BASE (0)  |  | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ |
| D21 (21)  |  |  |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | (✓ event) |
| UNSCH     |  |  |  |  | ✓ | (✓) |  | (✓) | (✓) | (✓) |  | ✓ |  | (✓) |

(SB/SA/TS/MB baseline at Visit 2, repeat at Visit 3. LB bloods at Visit 1 + Visit 3. Non-AD = NONLESIONAL
compartment only. DS rows beyond BASE are event-driven dropouts.)

## CDISC compliance notes
- USUBJID = `CATH-{SITE}-{SUBJ:04d}`; dates ISO-8601; VISITNUM monotone in study day.
- ARMCD ≤8 chars (`VITD`/`PLAC`); DXGROUP is a separate stratum variable (not folded into ARM).
- AE grades CTCAE-style 1–4; seriousness = `AESER` column on `AE` (no standalone SAE page).
- Biomarker units follow CTGov ("Cycle Number" = qRT-PCR relative abundance); change = Day21 − Baseline.
