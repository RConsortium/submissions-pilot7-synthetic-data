# Parameter derivation — RAVE SCM (Step 4)

Each parameter → final value → derivation source (CTGov field / paperclip id / model default),
per the skill Citation format. Live values are in `params_final.json`; the calibration history
is in `calibration_log.md`. Calibration adjusted only the values below — never model structure.

## Baseline population (L₀) — fixed from CTGov, not calibrated
| Param | Value | Source | Evidence |
|---|---|---|---|
| `p_female` | 0.492 | `ctgov: baseline "Sex"` | Female 97 / Male 100 (n=197) |
| `age_mean/sd` | 52.8 / 15.5 | `ctgov: baseline "Age, Continuous"` | total mean 52.8 (SD 15.5) |
| `p_usa` | 0.92 | `ctgov: baseline "Region"` | US 181 / NL 16 |
| `p_pr3` | 0.66 | `ctgov: eligibility` + model | "positive for either PR3-ANCA or MPO-ANCA"; RAVE ~2:1 PR3:MPO |
| `bvaswg_mean/sd` | 8.0 / 3.1 | `ctgov: baseline "BVAS/WG"` | mean 8.0 (SD 3.1) |
| `wbc_floor` | 4.0 | `ctgov: protocol exclusion` | "WBC less than 4000/mm3 [excluded]" |
| `plt_floor` | 120 | `ctgov: protocol exclusion` | "platelet counts less than 120,000/mm3 [excluded]" |

## Remission / disease-activity process — calibrated to primary endpoint
| Param | Value | Source | Evidence / target |
|---|---|---|---|
| `remit_intercept` | 0.62 | calibrated | population cr6mo → RTX 0.598 / CYC 0.536 (target .636/.531) |
| `remit_rtx` | 0.46 | `ctgov: outcomeMeasures[0]` | drives RTX>CYC gap "63 vs 52" complete remission |
| `remit_relapsing` | −0.30 | `model` + paperclip | relapsing disease harder to fully remit |
| `remit_pr3` | −0.10 | `paperclip: PMC8407598` | PR3 → worse long-term remission/relapse |
| `remit_day_median` | 45 d | `ctgov: outcomeMeasures[5]` | time to remission median 43–57 d |
| `flare_window_start_day` | 185 | `model` (clinical) | flares accrue in maintenance (months 7–18), not induction |

## Flare process — calibrated to secondary flare endpoints + stratifier gate
| Param | Value | Source | Evidence / target |
|---|---|---|---|
| `flare_base_haz` | 0.045 | `ctgov: outcomeMeasures[4]` | duration-of-remission HR 0.9; ~24% flare over 18 mo |
| `flare_rtx` | −0.20 | `ctgov: outcomeMeasures[4]` | "Cox … 0.9 (0.6–1.5)" RTX modestly protective |
| `flare_pr3` | 0.62 | `paperclip: PMC8407598 / PMC4520074` | "HR 1.69 (1.46–1.94)"; "56% vs 17%" PR3 vs MPO relapse |
| `flare_relapsing` | 0.35 | `paperclip: PMC8407598` | relapsing history → higher re-flare |

## Labs — myelosuppression (the key arm AE signal) — calibrated to leukopenia
| Param | Value | Source | Evidence / target |
|---|---|---|---|
| `wbc_cyc_drag` | 1.7 | `paperclip: PMC5880843` | "neutropenia ≤0.5×10⁹/L in 9 (16%) PO vs 0 (0%) IV … PO induces greater marrow toxicity" |
| `wbc_cyc_drag_frailty` | 0.7 | `model` (f_heme) | shared-frailty spread → CYC leukopenia ~37% (target 39.8%) |
| `wbc_rtx_drag` | 0.6 | `paperclip: PMC3539507` | rituximab-associated neutropenia → RTX leukopenia ~15% (target 13.1%) |
| `wbc_rtx_drag_frailty` | 0.4 | `model` (f_heme) | — |

## CTCAE v3.0 grading — FIXED rules (never tuned)
| Rule | Source | Evidence |
|---|---|---|
| leuko/neutro/anemia/thrombo grade thresholds | `model: CTCAE v3.0` | "NCI-CTCAE version 3.0 … was used to grade severity" |
| cytopenia AE serious only at Gr4 | `ctgov: adverseEventsModule` | serious leukopenia 3 RTX / 0 CYC despite 39 events → rarely "serious" |
| `*_report` probabilities | calibrated | grade-dependent reporting (G1 under-reported, G3+ near-certain) |

## Adverse events & serious events — calibrated to AE tables
| Param | Value | Source | Evidence / target |
|---|---|---|---|
| `ae_nonlab[Alopecia].log_rr_cyc/rtx` | +0.65 / −2.0 | `ctgov: adverseEventsModule` | "Alopecia 11 [RTX] vs 21 [CYC]" — CYC-specific |
| `ae_nonlab[Nausea/Vomiting].log_rr_cyc` | +0.25 / +0.50 | `ctgov` | "Nausea 25 vs 31; Vomiting 8 vs 13" |
| `infect_rtx` | 0.12 | `paperclip: PMC5570101/PMC10176387` | RTX B-cell depletion; Gr≥3 infection 18 vs 16 |
| `infect_base_haz_serious_disease` | 0.014 | `ctgov: adverseEventsModule` | serious disease-related events (vasculitis/respiratory) |
| `serious_disease_rtx` | 0.65 | `ctgov: adverseEventsModule` | "Wegener's granulomatosis [serious] 8 [RTX] vs 4 [CYC]" |
| `p_infect_serious` | 0.30 | `ctgov: outcomeMeasures` | calibrates ≥1 SAE → RTX 0.558 / CYC 0.543 (target .606/.480) |
| `steroid_ae_per_mg` | 0.0016 | `paperclip: PMC10547218` | "GC-related toxic AEs 44% high-dose vs 29% low-dose" |

## Discontinuation — calibrated to participant flow
| Param | Value | Source | Evidence / target |
|---|---|---|---|
| `disc_intercept` | −5.2 | `ctgov: participantFlowModule` | non-completion RTX 9/99, CYC 10/98 |
| `disc_serious_ae` / `disc_severe_flare` | 0.7 / 1.5 | `ctgov: dropWithdraw` | AE & disease reasons for withdrawal |
| `death_base` | 0.020 | `ctgov: outcomeMeasures "Death"` | 2 per arm |
