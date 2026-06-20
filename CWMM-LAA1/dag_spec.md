# DAG Specification — CWMM-LAA1 Eloralintide Phase 2

## Overview

This document specifies the structural causal model (SCM) used to generate
synthetic IPD for the CWMM-LAA1 trial (eloralintide phase 2, NCT06230523). The DAG has four layers:

- **L₀**: Baseline covariates (time-invariant)
- **A**: Treatment assignment
- **Lₜ**: Time-varying processes (body weight, AEs, metabolic markers)
- **Yₜ**: Derived endpoints

---

## Layer L₀ — Baseline Covariates

### Demographics

| Variable | Distribution | Parents | Notes |
|----------|-------------|---------|-------|
| `age` | TruncNorm(49, 12.6², 18, 75) | — | Years |
| `sex` | Bernoulli(0.78) | — | 1=Female |
| `race` | Categorical(0.78, 0.18, 0.04) | — | White, Black, Other |
| `height` | sex-dependent Normal | sex | F: N(164, 6²), M: N(178, 7²) cm |

### Anthropometrics

| Variable | Distribution | Parents | Notes |
|----------|-------------|---------|-------|
| `bmi_0` | TruncNorm(37.9, 6.7², 30, 65) | — | Eligibility: ≥30 |
| `bmi_strat` | Deterministic | bmi_0 | 1 if bmi_0 ≥ 35 |
| `body_weight_0` | Deterministic | bmi_0, height | bmi × height²/10000 |
| `waist_0` | Normal(115.2, 15.1²) | sex, bmi_0 | Conditional on BMI |

### Metabolic

| Variable | Distribution | Parents | Notes |
|----------|-------------|---------|-------|
| `hba1c_0` | TruncNorm(36.3, 4.2², 20, 47.9) | bmi_0 | mmol/mol, <48 per eligibility |
| `fasting_glucose_0` | Normal(5.2, 0.6²) | hba1c_0 | mmol/L |
| `fasting_insulin_0` | LogNormal(log(90), 0.5²) | bmi_0 | pmol/L |
| `homa_ir_0` | Deterministic | glucose, insulin | glucose×insulin/135 |
| `chol_0` | Normal(5.1, 1.0²) | — | mmol/L |
| `ldl_0` | Normal(3.2, 0.9²) | chol_0 | mmol/L |
| `hdl_0` | Normal(1.3, 0.3²) | sex | mmol/L |
| `trig_0` | LogNormal(log(1.5), 0.4²) | bmi_0 | mmol/L |
| `hscrp_0` | LogNormal(log(3.5), 0.8²) | bmi_0 | mg/L |
| `sysbp_0` | Normal(128, 14²) | age, bmi_0 | mmHg |
| `diabp_0` | Normal(80, 9²) | age, bmi_0 | mmHg |
| `pulse_0` | Normal(74, 10²) | — | bpm |

### Latent Frailties

| Variable | Distribution | Parents | Role |
|----------|-------------|---------|------|
| `f_GI` | Normal(0, 1) | — | Shared GI AE susceptibility |
| `f_fatigue` | Normal(0, 1) | — | Fatigue susceptibility |
| `f_metabolic` | Normal(0, 1) | — | Weight-loss responsiveness |
| `f_dropout` | Normal(0, 1) | — | Dropout propensity |

---

## Layer A — Treatment Assignment

| Variable | Distribution | Parents | Notes |
|----------|-------------|---------|-------|
| `arm` | Multinomial(2:1:1:1:2:1:2) | bmi_strat, sex | Stratified randomization |

### Dose Schedule

| Arm | Weeks 0–11 | Weeks 12–48 |
|-----|-----------|-------------|
| Placebo | 0 mg | 0 mg |
| 1mg | 1 mg | 1 mg |
| 3mg | 3 mg | 3 mg |
| 6mg | 6 mg | 6 mg |
| 9mg | 9 mg | 9 mg |
| 6→9mg | 6 mg | 9 mg |
| 3→9mg | 3 mg | 9 mg |

---

## Layer Lₜ — Time-Varying Processes

### Body Weight Trajectory

**Model**: Exponential approach to dose-dependent nadir

```
max_loss_pct[i] = beta_dose × effective_dose[i,t] + f_metabolic[i] × sigma_metabolic
wt_pct[i,t] = max_loss_pct[i] × (1 - exp(-k × t)) + epsilon[t]
```

**Parents**: arm (via effective_dose), f_metabolic, time, discontinuation status

**On treatment discontinuation**: Weight regain at rate `k_regain` toward baseline:
```
wt_pct[i,t] = wt_pct[i, t_disc] × exp(-k_regain × (t - t_disc))
```

### Adverse Events

**GI AEs** (nausea, diarrhea, vomiting):
```
logit(p_GI[i,t]) = alpha_GI + beta_GI_dose × dose[t] + beta_GI_escalation × I(escalation_phase) + gamma_GI × f_GI[i]
```

**Fatigue**:
```
logit(p_fatigue[i,t]) = alpha_fat + beta_fat_dose × dose[t] + gamma_fat × f_fatigue[i]
```

**Other AEs** (constipation, decreased appetite, alopecia, headache):
Per-arm calibrated base rates.

**Parents**: dose, escalation indicator, frailty, time

### Metabolic Markers (derived from weight change)

All metabolic changes are proportional to cumulative weight loss:
```
delta_hba1c[t] = rho_hba1c × pct_wt_change[t]
delta_glucose[t] = rho_glucose × pct_wt_change[t]
delta_insulin[t] = rho_insulin × pct_wt_change[t]
delta_trig[t] = rho_trig × pct_wt_change[t]
delta_hscrp[t] = rho_crp × pct_wt_change[t]
delta_sysbp[t] = rho_sbp × pct_wt_change[t]
```

### Treatment Discontinuation

**Hazard model** per visit interval:
```
logit(h_disc[i,t]) = alpha_disc + beta_disc_ae × cum_ae_burden[i,t] + beta_disc_arm × arm_effect + gamma_disc × f_dropout[i]
```

Once discontinued, patient may still attend visits (study continuation vs withdrawal).

---

## Layer Y — Derived Endpoints

| Endpoint | Formula | Parents |
|----------|---------|---------|
| `pct_wt_change_48` | (wt[48]-wt[0])/wt[0]×100 | wt trajectory |
| `abs_wt_change_48` | wt[48]-wt[0] | wt trajectory |
| `bmi_48` | wt[48]/height²×10000 | wt trajectory |
| `resp_5pct` | I(pct_wt_change_48 ≤ -5) | pct_wt_change_48 |
| `resp_10pct` | I(pct_wt_change_48 ≤ -10) | pct_wt_change_48 |
| `resp_15pct` | I(pct_wt_change_48 ≤ -15) | pct_wt_change_48 |
| `resp_20pct` | I(pct_wt_change_48 ≤ -20) | pct_wt_change_48 |

---

## Causal Edges Summary

```
age → sysbp_0, diabp_0
sex → height, hdl_0, waist_0
bmi_0 → body_weight_0, waist_0, fasting_insulin_0, trig_0, hscrp_0, hba1c_0, sysbp_0
bmi_strat, sex → arm (stratification)
arm → effective_dose[t]
effective_dose[t] → wt_pct[t], AE hazards
f_metabolic → wt_pct[t] (individual responsiveness)
f_GI → nausea, diarrhea, vomiting hazards
f_fatigue → fatigue hazard
f_dropout → discontinuation hazard
wt_pct[t] → metabolic markers[t] (proportional coupling)
AE burden → discontinuation hazard
discontinuation → wt_pct[t'] for t'>t_disc (regain)
```
