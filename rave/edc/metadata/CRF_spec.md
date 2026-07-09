# CRF Schema — RAVE (NCT00104299 / ITN021AI)

Derived from **Protocol ITN021AI v7.0 (July 15, 2009), Appendix 1/2 Schedule of Assessments**
(`intake/protocol.pdf`), with endpoint/AE field sets shaped by the posted ClinicalTrials.gov
results (`intake/NCT00104299.json`). Each form lists its visit grid, CDISC-aligned variables,
protocol source, and how it maps onto the structural causal model (SCM) built in Step 3.

Therapeutic area: **ANCA-associated vasculitis** (GPA/Wegener's + MPA) — *not* oncology, so the
oncology module of the template (RECIST/tumor) is replaced by a **disease-activity module**
(BVAS/WG, VDI, ANCA, flare).

## Arms

| ARMCD | ARM | Induction (mo 0–3/6) | Maintenance (mo 3/6–18) |
|---|---|---|---|
| `RTX` | Rituximab | Rituximab 375 mg/m²/wk ×4 IV + CYC-placebo + prednisone | AZA-placebo + prednisone(off by mo6) |
| `CYC` | Control | Cyclophosphamide 2 mg/kg/day PO + rituximab-placebo ×4 + prednisone | Azathioprine 2 mg/kg/day + prednisone(off by mo6) |

Source: `protocol.pdf` "The experimental arm will receive intravenous infusions of rituximab
(375 mg/m2/week times 4) … The control arm will receive CYC (2 mg/kg …) … The control arm will
switch from daily CYC to AZA (2 mg/kg/day)." Randomization 1:1, double-blind double-dummy.

## Trial-level visit grid (Appendix 1 — original treatment assignment)

| Visit code | VISITNUM | Study day | Nominal time | Source |
|---|---|---|---|---|
| `SCRN` (V-1) | 1 | -14 | Screening (≤14 d before baseline) | SoA Appendix 1 |
| `V1` | 2 | 1 | Baseline / randomization / infusion 1 | SoA |
| `V2` | 3 | 8 | Week 1 / infusion 2 | SoA |
| `V3` | 4 | 15 | Week 2 / infusion 3 | SoA |
| `V4` | 5 | 22 | Week 3 / infusion 4 | SoA |
| `V5` | 6 | 29 | Month 1 | SoA |
| `V6` | 7 | 60 | Month 2 | SoA |
| `V7` | 8 | 120 | Month 4 | SoA |
| `V8` | 9 | 180 | **Month 6 — PRIMARY ENDPOINT** | SoA |
| `V9` | 10 | 270 | Month 9 | SoA |
| `V10` | 11 | 365 | Month 12 | SoA |
| `V11` | 12 | 455 | Month 15 | SoA |
| `V12` | 13 | 545 | Month 18 (end of main study) | SoA |
| `VFU` (V13+) | 14+ | q6mo after V12 | Post-treatment follow-up (CRF marked V13,V14…) | SoA footnote 3 |
| `VCCD` | 99 | common closing date | 18 mo after last participant enrolled | SoA |
| `ADMIN_CENSOR` | — | day 545 (per patient) | Analysis censor = month-18 visit | CTGov timeFrame |

Crossover (Appendix 2): any time between V5 and V8, the participant restarts at `V1A` on the
alternate blinded drug and is re-followed on the V1A-anchored schedule. **Stratification factors**
(protocol §): ANCA type (PR3 vs MPO), disease severity, new-diagnosis vs relapsing, clinical center.

---

## Form inventory

### Form: Demographics — `DM`
- **Domain**: DM. **Source**: SoA "Demography, Medical history, Height" (Screening); CTGov baselineCharacteristicsModule.
- **Visit grid**: `SCRN` only.
- **Variables**: USUBJID, SITEID, ARMCD, ARM, AGE (years), SEX (M/F), RACE, ETHNIC, COUNTRY (USA/NLD), HEIGHT (cm), WEIGHT (kg), RFSTDTC.
- **SCM mapping**: L₀ baseline node `demographics`. Age mean 52.8 (SD 15.5); 49% female; 92% US.

### Form: Inclusion/Exclusion — `IE`
- **Domain**: IE. **Source**: SoA "Inclusion and exclusion criteria" (Screening + Baseline); protocol synopsis eligibility.
- **Visit grid**: `SCRN`, `V1`.
- **Variables**: USUBJID, IETESTCD, IETEST, IECAT (INCL/EXCL), IEORRES (Y/N). All simulated patients pass (support of L₀ is the eligible population): BVAS/WG ≥3, ANCA+, weight ≥40 kg, age ≥15.

### Form: Medical History — `MH`
- **Domain**: MH. **Source**: SoA "Medical history (with vaccine)" (Screening).
- **Visit grid**: `SCRN`.
- **Variables**: USUBJID, MHTERM, MHDECOD, MHCAT (e.g. AAV, comorbidity, vaccine), MHSTDTC, MHDX (newly-diagnosed vs relapsing), disease-duration.
- **SCM mapping**: L₀ `disease_history` + comorbidity parents of baseline labs.

### Form: Disease Characteristics / ANCA — `DC`
- **Domain**: SC/MB. **Source**: SoA "ANCA (clinical)" (Screening); eligibility "positive for either PR3-ANCA or MPO-ANCA".
- **Visit grid**: `SCRN`.
- **Variables**: USUBJID, DIAGTYPE (GPA/WG vs MPA), ANCATYPE (PR3 vs MPO), ANCASTAT (POS), NEWDX (new vs relapsing), ORGAN involvement flags (renal, pulmonary, ENT). 
- **SCM mapping**: L₀ stratifiers — parents of disease-activity & flare nodes.

### Form: Vital Signs — `VS`
- **Domain**: VS. **Source**: SoA "Vital signs" (every visit; intra-infusion q15min, footnote 11).
- **Visit grid**: all visits.
- **Variables**: USUBJID, VISIT, VSDTC, SYSBP, DIABP, PULSE, TEMP, RESP, WEIGHT.
- **SCM mapping**: Lₜ vitals; intra-infusion vitals feed infusion-reaction detection (RTX arm).

### Form: Physical Examination — `PE`
- **Domain**: PE. **Source**: SoA "Physical examination" (every visit).
- **Visit grid**: all visits. **Variables**: USUBJID, VISIT, PEDTC, PEORRES by body system (normal/abnormal).

### Form: BVAS/WG Disease Activity & Flare — `DA`
- **Domain**: RS (disease response). **Source**: SoA "BVAS/WG and flare history" (Screening, then V5→VCCD; flare history not at screen/baseline, footnote 16); primary endpoint definition.
- **Visit grid**: `SCRN`, `V5`–`VFU`.
- **Variables**: USUBJID, VISIT, DADTC, **BVASWG** (0–63 score units), REMISSION (Y/N = BVAS/WG=0), FLARE (NONE/LIMITED/SEVERE), FLARETYPE, GCFREE (Y/N off glucocorticoids).
- **SCM mapping**: Lₜ **latent disease-activity process** → BVAS/WG; remission = BVAS/WG=0; the primary endpoint `complete_remission_6mo` is derived from this + the GC log. Baseline BVAS/WG mean 8.0 (SD 3.1).

### Form: Vasculitis Damage Index — `VDI`
- **Domain**: RS. **Source**: SoA "VDI" (Baseline, V8/mo6, V10/mo12, V12/mo18, FU).
- **Visit grid**: `V1`, `V8`, `V10`, `V12`, `VFU`. **Variables**: USUBJID, VISIT, VDI (0–n, monotone non-decreasing damage). Baseline VDI mean 1.2 (SD 1.7).

### Form: Physician Global Assessment — `PGA`
- **Domain**: RS. **Source**: SoA "Physician Global Assessment Form" + "AVID" (Baseline, V5→VCCD).
- **Visit grid**: `V1`, `V5`–`VFU`. **Variables**: USUBJID, VISIT, PGA (0–10 VAS), AVID flag.

### Form: Laboratory — Hematology — `LB` (cat HEM)
- **Domain**: LB. **Source**: SoA "Hematology" (every visit, incl. WESR; STAT V2–V4; pre-infusion WBC<3000 → withhold, footnote 17).
- **Visit grid**: all visits.
- **Variables**: USUBJID, VISIT, LBDTC, **WBC** (×10⁹/L), **ANC** (×10⁹/L), **LYMPH**, **HGB** (g/dL), **HCT** (%), **PLT** (×10⁹/L), **WESR/ESR** (mm/hr); LBSTRESN, LBNRIND (NORMAL/HIGH/LOW), LBTOXGR (CTCAE v3.0).
- **SCM mapping**: Lₜ AR(1) lab nodes. **The arm causal signal lives here**: CYC arm → leukopenia/WBC↓ (CTGov: leukopenia 39 vs 13, WBC↓ 21 vs 6). ANC/WBC drive deterministic CTCAE leukopenia/neutropenia AEs and infusion-withhold logic.

### Form: Laboratory — Chemistry — `LB` (cat CHEM)
- **Domain**: LB. **Source**: SoA "Chemistry" — *"includes only BUN, creatinine, and C-reactive protein"* (footnote 18), every visit.
- **Visit grid**: all visits.
- **Variables**: USUBJID, VISIT, LBDTC, **BUN** (mg/dL), **CREAT** (mg/dL), **CRP** (mg/L); LBSTRESN, LBNRIND.
- **SCM mapping**: Lₜ renal-function (CREAT/BUN, renal vasculitis activity) + inflammatory marker (CRP tracks disease activity).

### Form: Laboratory — Urinalysis with microscopy — `LB` (cat UA)
- **Domain**: LB. **Source**: SoA "UA with microscopy" — **explicitly listed at every visit** (footnote 22), so a standalone urinalysis form *is* warranted here (cf. skill suppression note).
- **Visit grid**: all visits.
- **Variables**: USUBJID, VISIT, HEMATURIA (neg/+/++/+++), PROTEIN, RBCCAST (Y/N), RBC/hpf.
- **SCM mapping**: Lₜ renal vasculitis activity (hematuria tracks BVAS/WG renal items; CTGov: haematuria 6 vs 14).

### Form: Adverse Events — `AE`
- **Domain**: AE. **Source**: SoA "Adverse events" (V1→VCCD); CTGov adverseEventsModule (CTCAE v3.0); secondary-endpoint "selected AEs".
- **Visit grid**: V1→VCCD (event-driven; emitted at the visit of detection).
- **Variables**: USUBJID, AETERM, AEDECOD (MedDRA PT), AEBODSYS (SOC), AESEV (MILD/MOD/SEVERE/LIFE-THREAT), **AETOXGR** (1–4, CTCAE v3.0), **AESER** (Y/N — seriousness is a column, *no separate SAE form* per skill suppression note), AEREL (NOT/POSSIBLY/RELATED), AEACN (dose action), AEOUT, AESTDTC, AEENDTC.
- **SCM mapping**: derived AEs (leukopenia, neutropenia, anemia, thrombocytopenia) from CTCAE grading of `LB`; non-lab AEs (nausea, infection, alopecia, infusion reaction, etc.) sampled from latent **frailty clusters** + arm. Targets: ≥1 serious AE 60% RTX / 48% CYC; SAE 42 vs 37.

### Form: Concomitant Medications — `CM`
- **Domain**: CM. **Source**: SoA "Concomitant medications" + "Prophylactic medications" (every visit).
- **Visit grid**: all visits. **Variables**: USUBJID, CMTRT, CMDECOD, CMINDC, CMSTDTC, CMENDTC. Includes PJP prophylaxis, premeds (diphenhydramine/acetaminophen). Causally downstream of AEs.

### Form: Glucocorticoid Log — `GC`
- **Domain**: EX (cat GLUCOCORTICOID). **Source**: SoA "Glucocorticoid log" (V1–V12) + "Glucocorticoid PO" (SCRN–V8); protocol "prednisone will be tapered so that by month 6 all participants in clinical remission will be off glucocorticoids".
- **Visit grid**: `V1`–`V12` (oral SCRN–V8).
- **Variables**: USUBJID, VISIT, PREDDOSE (mg/day), CUMGC (cumulative mg), GCFREE (Y/N).
- **SCM mapping**: Lₜ protocol-driven prednisone taper to 0 by mo6 — **a parent of the primary endpoint** (complete remission = BVAS/WG=0 AND GC taper completed). Higher GC → fewer flares but more steroid AEs (hyperglycemia, cushingoid, insomnia).

### Form: Study Drug Exposure — `EX`
- **Domain**: EX. **Source**: SoA "Rituximab/rituximab placebo" (V1–V4), "Oral study drug kits" CYC/AZA (V1–V11), "Glucocorticoid IV" (V1).
- **Visit grid**: rituximab V1–V4; oral drug V1–V11; IV GC V1.
- **Variables**: USUBJID, VISIT, EXTRT, EXDOSE, EXDOSU, EXROUTE, EXSTDTC, EXENDTC, dose-modified flag.
- **SCM mapping**: A-node exposure indicators that drive Lₜ (e.g., CYC active → myelosuppression drag in `LB`).

### Form: Infusion & Reactions — `IR`
- **Domain**: EX/AE. **Source**: SoA footnote 11 (vitals q15min during infusion), footnote 27 (premed diphenhydramine 50 mg + acetaminophen 650 mg). 
- **Visit grid**: `V1`–`V4` (infusion visits). **Variables**: USUBJID, VISIT, PREMED (Y/N), INFRXN (Y/N), INFRXNGR, INFDISC (infusion discontinued Y/N). CTGov: "Infusion reactions leading to disc." 1 RTX / 0 CYC.

### Form: Chest Imaging — `IM`
- **Domain**: FA/PR. **Source**: SoA "Chest x-ray or CT scan" (SCRN/baseline, mo1, mo6, mo9, mo18 all; mo2/4/12/15 if abnormal, footnote 14).
- **Visit grid**: `SCRN`, `V5`, `V8`, `V9`, `V12` (+ abnormal subset). **Variables**: USUBJID, VISIT, IMMETHOD (CXR/CT), IMORRES (normal / infiltrate / nodule / hemorrhage). Maps to pulmonary BVAS/WG items.

### Form: ECG — `EG`
- **Domain**: EG. **Source**: SoA "ECG" — *"after screening, an ECG must be done at V10, V12, and when the participant withdraws"* (footnote 15).
- **Visit grid**: `SCRN`, `V10`, `V12`, withdrawal. **Variables**: USUBJID, VISIT, EGORRES (normal/abnormal), HR. (No QTcF driver drug here — low-salience; minimal model.)

### Form: Disposition — `DS`
- **Domain**: DS. **Source**: SoA "Randomization" (V1); CTGov participantFlowModule.
- **Visit grid**: `V1` (randomization milestone) + event-driven.
- **Variables**: USUBJID, DSDECOD (RANDOMIZED / COMPLETED / DISCONTINUED / DEATH / CROSSOVER), DSTERM (reason: AE / death / withdrawal by subject / physician decision / renal transplant), DSSTDTC.
- **SCM mapping**: Yₜ disposition derived from trajectory. Targets: completed 90/99 RTX, 88/98 CYC; reasons per CTGov dropWithdraw.

### Form: Remission / Endpoint Summary — `RE`
- **Domain**: RS (derived). **Source**: primary + secondary endpoint definitions (synopsis); CTGov outcomeMeasuresModule.
- **Visit grid**: derived (snapshot at mo6, plus flare/remission time-to-event over 18 mo).
- **Variables**: USUBJID, **CR6MO** (complete remission at 6 mo: BVAS/WG=0 AND GC taper complete = primary endpoint), TTREM_DAY (time to BVAS/WG=0), TTCR_DAY (time to complete remission off GC), REMDUR_DAY (duration of remission to flare), FLARE_EVENT, FLARE_DAY, censor flags.
- **SCM mapping**: Yₜ **derived purely from the BVAS/WG trajectory + GC log** — never drawn directly. Targets: CR6MO 63/99 (RTX) vs 52/98 (CYC); flare HR ≈0.9.

### Form: SF-36 PRO — `QS` (optional, low-salience)
- **Domain**: QS. **Source**: SoA "SF-36 v.2 Health Survey". Visit grid SCRN/baseline, V5→VCCD. Minimal model (PCS/MCS summary scores); not tied to a published marginal target → simulated coarsely or omitted under KISS.

**Out of scope (mechanistic research assays, not clinical CRF outcomes):** PBMC T-cell assay, HLA
genotyping, flow cytometry, gene-expression profiling, secreted cytokines, serum/plasma archive,
HACA, research-ANCA, rituximab PK levels. These are bio-sample collections with no published
marginal target to calibrate against; excluded from the synthetic CRF set (KISS).

---

## SoA-to-form crosswalk (visit × form)

| Visit (day) | DM | IE | MH | DC | VS | PE | DA | VDI | PGA | LB-HEM | LB-CHEM | LB-UA | AE | CM | GC | EX | IR | IM | EG | DS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SCRN (-14) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | ✓ | ✓ |  | ✓ | ✓ |  |  | ✓ | ✓ |  |
| V1 (1) |  | ✓ |  |  | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | ✓ |
| V2 (8) |  |  |  |  | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |
| V3 (15) |  |  |  |  | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |
| V4 (22) |  |  |  |  | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |
| V5 (29) |  |  |  |  | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ |  |  |
| V6 (60) |  |  |  |  | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  |
| V7 (120) |  |  |  |  | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  |
| V8 (180) |  |  |  |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ |  |  |
| V9 (270) |  |  |  |  | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ |  | ✓ |  |  |
| V10 (365) |  |  |  |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ |  |  | ✓ |  |
| V11 (455) |  |  |  |  | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ |  |  |  |  |
| V12 (545) |  |  |  |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  | ✓ | ✓ | ✓ |
| VFU (q6mo) |  |  |  |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  |  | ✓ |

(✓ approximates Appendix-1 marks; mechanistic-assay rows omitted. EX-rituximab only V1–V4; oral
study drug V1–V11; GC log V1–V12. DS rows beyond V1 are event-driven.)

## CDISC compliance notes
- USUBJID = `RAVE-{SITE}-{SUBJ:04d}`; dates ISO-8601; VISITNUM monotone in study day.
- ARMCD ≤8 chars (`RTX`/`CYC`); AE grades CTCAE v3.0 (matches CTGov "NCI-CTCAE version 3.0").
- Seriousness = `AESER` column on `AE` (no separate SAE page). No standalone form beyond those above.
