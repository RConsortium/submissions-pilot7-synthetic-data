# ARA06 — Parameter Derivation (Step 4)

Each structural-equation parameter (`ara06/params.py`, snapshot
`params_final.json`) maps to a derivation source per the skill hierarchy:
**(1) ctgov results** (closest to ground truth) → **(2) foundation-model /
fixed rules** (CTCAE, DAS28, ACR — never tuned) → **(3) literature priors**
(paperclip, with verbatim quote). Calibration (Step 6) adjusts only these
values, never the model structure.

## Baseline population (L0)

| Parameter | Value | Derivation |
|---|---|---|
| `p_female` | 0.793 | `ctgov` baseline 46/58 female |
| `age_mean/sd` | 52.0 / 11.0 | `ctgov` baseline "Age, Continuous" total |
| `p_rf_ccp_pos` | 0.759 | `ctgov` baseline 44/58 RF-or-CCP+ (stratifier) |
| `mtx_dose_mean/sd` | 17.9 / 3.9 | `ctgov` baseline MTX dose |
| `tjc/sjc/crp/haqdi` means | 12.3 / 9.7 / 13.8 / 1.4 | `ctgov` baseline |
| `das28_floor` | 4.4 | `protocol §4.1` eligibility "Active RA with DAS28 > 4.4" |
| lab eligibility floors | ANC≥1.5, PLT≥110, HGB≥9, AST/ALT<2×ULN, creat≤1.5 | `protocol §4.2` exclusions |

## Mechanistic primary — switched memory B cells

| Parameter | Value | Derivation |
|---|---|---|
| `mem_base_mean/sd` | 18.4 / 7.6 | `paperclip PMC2714135` RA switched-memory baseline ~9–13%, declining; tuned so wk12 ≈ ctgov |
| `mem_decay` | 0.76 | calibrated to ctgov wk12 means (ETN 13.2, ADA 13.8) |
| `mem_arm_etn` | −0.5 (≈null) | `ctgov` p=0.3 (no arm difference); `PMC2714135` anti-TNF does NOT reduce switched memory |
| `mem_noise` | 4.5 | calibrated to ctgov wk12 SD ≈ 7.3 |

## Clinical response process

| Parameter | Value | Derivation |
|---|---|---|
| `resp_mu_etn / resp_mu_ada` | 0.59 / 0.66 | calibrated to ctgov ACR20/50 + DAS28 response; ADA deeper (ctgov ACR50 47.4% vs 29.7%) |
| `resp_sigma` | 0.30 | calibrated so DAS28-response (lenient) > ACR20 > ACR50 ordering holds |
| `comp_mult_sigma` | 0.30 | spread driving the ACR "≥3 of 5" rule; `paperclip PMC2377247` anti-TNF class effect comparable |
| `ramp_wk12 / ramp_wk24` | 0.92 / 1.05 | response builds over time (wk24 ≥ wk12 in ctgov) |
| DAS28 formula, ACR rule, EULAR thresholds | **FIXED** | `protocol App. B, C` — deterministic, never tuned |

## Labs & adverse events

| Parameter | Value | Derivation |
|---|---|---|
| `wbc/hgb/plt _mtx_drag` (+ f_heme) | 0.45 / 0.03 / 8.0 | `paperclip PMC4851368` MTX myelosuppression 2–10.2% (neutropenia 1.4–7%) |
| `ast/alt _mtx_drag, _etn_extra, _frailty` | 1.0 / 2.8(ETN), 1.2 / 6.0–6.5 | `paperclip PMC6186305` MTX+ETA transaminase elevation 23.5% (> MTX alone 19.1%); shared `f_hepatic` → AST/ALT co-elevate |
| CTCAE grade thresholds (anaemia/leuko/neutro/lympho/AST/ALT/creat) | **FIXED** | `protocol §7.4.1` NCI-CTCAE v3.0 — never tuned |
| `*_report` Bernoulli probs | grade-increasing | calibrated to ctgov per-PT affected counts |
| `ae_nonlab` base hazards | 0.015–0.022 | calibrated to ctgov infection/MSK per-PT counts; `paperclip PMC3105607` anti-TNF SI adjHR 1.2 |
| `sae_flare_haz / sae_idio_haz` | 0.0015 / 0.0016 | `ctgov` 2/39 ETN, 1/19 ADA participants with SAE |
| `disc_intercept_etn / _ada` | −3.25 / −5.0 | `ctgov` ETN 9/43, ADA 1/20 noncompletion; reasons administrative (no AE) |

## What is fixed vs. tunable

**Fixed (never touched by calibration):** DAS28-4(CRP) formula, EULAR
good/moderate thresholds, ACR20/ACR50 rule, all NCI-CTCAE grade cutoffs, the
2:1 randomization, the DAG edge set. **Tunable:** the distribution parameters
above (means, SDs, drags, hazards, reporting probabilities, response μ/σ).
