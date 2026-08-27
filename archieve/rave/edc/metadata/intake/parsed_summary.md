# RAVE (NCT00104299 / ITN021AI) — Step 1 intake summary

Source: `RAVE_output/intake/NCT00104299.json` (ClinicalTrials.gov API v2, fetched 2026-06-19).
All field paths below are `ctgov:` origin unless noted.

## Design
- **Title**: Rituximab Therapy for the Induction of Remission and Tolerance in ANCA-Associated Vasculitis (ITN021AI)
- **Type**: Interventional, Phase 2/3, randomized, double-blind (participant + investigator), parallel, double-dummy.
- **Enrollment**: 197 actual (Rituximab 99, Control 98). Allocation effectively 1:1.
- **Primary purpose**: Treatment (remission induction; non-inferiority design).

### Arms / interventions
| Arm | n | Regimen |
|---|---|---|
| **Rituximab** (experimental) | 99 | Rituximab 375 mg/m² IV weekly ×4 + **cyclophosphamide placebo**; + glucocorticoids |
| **Control** (active comparator) | 98 | Cyclophosphamide 2 mg/kg/day PO (months 1–3/6) → azathioprine 2 mg/kg/day (months 4–6) + **rituximab placebo**; + glucocorticoids |

Both arms: IV methylprednisolone pulse then oral prednisone 1 mg/kg/day, tapered to 0 by ~month 5–6.

## Eligibility → baseline population priors
- Sex: ALL; min age 15 y; weight ≥40 kg.
- Dx: Wegener's granulomatosis (GPA) or microscopic polyangiitis (MPA), Chapel Hill definitions.
- Newly diagnosed OR flare with BVAS/WG ≥3 requiring CYC; **PR3-ANCA or MPO-ANCA positive** at screening.
- Severe disease (would normally get CYC). Exclusions: Churg-Strauss, limited disease, alveolar hemorrhage needing ventilation, active/severe infection, HBV/HCV/HIV, cancer <5 y, anti-GBM disease, pregnancy.

### Baseline characteristics (ctgov: resultsSection/baselineCharacteristicsModule)
| Var | Rituximab (n=99) | Control (n=98) | Total |
|---|---|---|---|
| Age, mean (SD) y | 54.0 (16.8) | 51.5 (14.1) | 52.8 (15.5) |
| Age ≥65 / 18–65 / ≤18 | 36 / 60 / 3 | 19 / 76 / 3 | 55 / 136 / 6 |
| Female / Male | 52 / 47 | 45 / 53 | 97 / 100 |
| Region US / Netherlands | 91 / 8 | 90 / 8 | 181 / 16 |
| BVAS/WG, mean (SD) | 8.1 (2.8) | 8.0 (3.4) | 8.0 (3.1) |
| VDI, mean (SD) | 1.4 (1.8) | 1.0 (1.4) | 1.2 (1.7) |

(Note: stratification factors per protocol = ANCA type [PR3 vs MPO] and new-diagnosis vs relapsing, and clinical center — to be confirmed from protocol SoA.)

## Endpoint targets (calibration)
### Primary — complete remission at 6 months (BVAS/WG = 0 AND prednisone taper completed)
| | Rituximab | Control |
|---|---|---|
| n achieving | **63 / 99 (63.6%)** | **52 / 98 (53.1%)** |
| Difference (RTX − ctrl) | **+10.6%**, 95.1% CI [−3.2, 24.3] | — |
Non-inferiority met (margin −20%, one-sided 0.025), p<0.001 for NI. (NEJM 2010 reports 64% vs 53%.)

### Secondary (time-to-event, Cox HR, censored at crossover / open-label / month 18)
| Endpoint | RTX vs Ctrl | HR (95% CI) |
|---|---|---|
| Duration of complete remission → flare | medians NA (both) | 0.9 (0.5–1.7) |
| Duration of remission → flare | medians NA | 0.9 (0.6–1.5) |
| Time to remission (BVAS/WG=0) | median 57 vs 43 d | 1.0 (0.7–1.3) |
| Time to complete remission (off GC) | median 180 vs 183 d | 1.3 (0.9–1.8) |

## Participant flow (overall study)
- Completed: RTX 90/99, Control 88/98.
- Not completed: RTX 9 (AE 3, death 2, withdrawal 2, MD decision 1, renal transplant 1); Control 10 (AE 1, death 2, withdrawal 6, MD decision 1).

## Adverse-event targets (ctgov: resultsSection/adverseEventsModule; CTCAE v3.0; randomization → common close-out 18 mo)
Group-level (numAffected / numAtRisk):
| | Rituximab | Control |
|---|---|---|
| ≥1 **serious** AE (uncensored) | 60 / 99 (60.6%) | 47 / 98 (48.0%) |
| ≥1 **other** (non-serious ≥5% threshold) AE | 97 / 99 | 97 / 98 |
| ≥1 SAE (post-hoc, censored at crossover) | 42 / 99 | 37 / 98 |

### "Selected AEs of interest" (secondary endpoint #1 — participant counts)
| Event | RTX | Control |
|---|---|---|
| Death | 2 | 2 |
| Gr ≥2 leukopenia | **7** | **23** |
| Gr ≥2 thrombocytopenia | 4 | 1 |
| Gr ≥3 infection | 18 | 16 |
| Hemorrhagic cystitis (≤Gr2) | 2 | 1 |
| Malignancy | 5 | 2 |
| VTE | 6 | 8 |
| Hospitalization from disease | 16 | 7 |
| CVA | 1 | 1 |
| Infusion reaction → disc. | 1 | 0 |

### Dominant causal arm signal in PT-level "other" events (RTX vs Control counts)
Cyclophosphamide (control) → **myelosuppression + emesis + alopecia**:
- Leukopenia 13 vs **39**; WBC decreased 6 vs **21**; haematocrit decreased 8 vs 16; ESR incr 5 vs 12.
- Alopecia 11 vs **21**; Rash 14 vs 23; Nausea 25 vs 31; Vomiting 8 vs 13; Pyrexia 10 vs 17.
Rituximab arm higher: Thrombocytopenia 9 vs 5; UTI 18 vs 7; Oropharyngeal pain 11 vs 3; Musculoskeletal pain 11 vs 4; Cough 32 vs 24; Arthralgia 34 vs 24.
Disease-related serious events: Wegener's granulomatosis flare 8 vs 4; Pulmonary alveolar haemorrhage 2 vs 2.

These PT-level differences are the **AE-arm causal edges** Step 3 must encode (chiefly `arm → CYC exposure → myelosuppression/alopecia/emesis`).

## Notable design facts for the simulator
- **Trajectory horizon**: 18 months (common close-out). Primary readout at month 6.
- **Glucocorticoid taper to 0 by ~month 5.5** is part of the primary-endpoint definition.
- AE grading: **NCI-CTCAE v3.0**.
- Disease activity instrument: **BVAS/WG** (0 = remission); damage = **VDI**.
- Primary "remission" combines a *continuous latent disease-activity process* (BVAS/WG→0) with a *protocol GC-taper completion* indicator — neither is a simple parametric survival draw.
