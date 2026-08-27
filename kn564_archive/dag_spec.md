# DAG Specification — KEYNOTE-564

## Structural Causal Model (SCM) Variable Definitions

Each variable lists its parents, structural equation form, and evidence source.

---

## L0 — Baseline Variables

### `age`
- **Parents**: None (exogenous)
- **Equation**: `age ~ Normal(60, 10)`, truncated [24, 84]
- **Evidence**: Protocol Table 1; median 60, range 24–84

### `sex`
- **Parents**: None
- **Equation**: `sex ~ Bernoulli(0.71)` for male
- **Evidence**: Table 1: 71% male

### `race`
- **Parents**: `region`
- **Equation**: If US: WHITE 0.75, BLACK 0.12, ASIAN 0.05, OTHER 0.08; If OTHER: WHITE 0.50, ASIAN 0.35, BLACK 0.02, OTHER 0.13
- **Evidence**: Protocol demographics

### `region`
- **Parents**: None
- **Equation**: `region ~ Bernoulli(0.30)` for US
- **Evidence**: Stratification; ~30% US enrollment

### `risk_category`
- **Parents**: None
- **Equation**: `risk_category ~ Categorical(M0_INT_HIGH=0.86, M0_HIGH=0.08, M1_NED=0.06)`
- **Evidence**: Table 1: intermediate-high 86%, high 8%, M1 NED 6%

### `sarcomatoid`
- **Parents**: `risk_category`
- **Equation**: `sarcomatoid ~ Bernoulli(p)` where p=0.13 if M0_HIGH, 0.20 if M1_NED, 0.10 otherwise
- **Evidence**: 11% overall sarcomatoid; enriched in higher risk

### `pdl1_cps`
- **Parents**: `sarcomatoid`
- **Equation**: `pdl1_cps ~ Categorical(<1: 0.24, >=1: 0.75, MISSING: 0.01)`; if sarcomatoid: shift +10% toward >=1
- **Evidence**: Table 1; sarcomatoid tumors tend PD-L1+

### `ecog_bl`
- **Parents**: `age`
- **Equation**: `ecog_bl ~ Bernoulli(expit(-2.0 + 0.02*(age-60)))` for ECOG 1
- **Evidence**: 85% ECOG 0, 15% ECOG 1; slight age dependence

### `f_thyroid`
- **Parents**: None (latent)
- **Equation**: `f_thyroid ~ Normal(0, 1)`
- **Evidence**: Individual susceptibility to thyroid immune toxicity

### `f_skin`
- **Parents**: None (latent)
- **Equation**: `f_skin ~ Normal(0, 1)`
- **Evidence**: Individual susceptibility to skin AEs (rash, pruritus)

### `f_GI`
- **Parents**: None (latent)
- **Equation**: `f_GI ~ Normal(0, 1)`
- **Evidence**: Individual susceptibility to GI AEs (diarrhea, colitis)

### `f_systemic`
- **Parents**: None (latent)
- **Equation**: `f_systemic ~ Normal(0, 1)`
- **Evidence**: Individual susceptibility to systemic AEs (fatigue, arthralgia)

### `f_recurrence`
- **Parents**: None (latent)
- **Equation**: `f_recurrence ~ Normal(0, 1)`
- **Evidence**: Unmeasured disease aggressiveness beyond risk category

### `f_dropout`
- **Parents**: None (latent)
- **Equation**: `f_dropout ~ Normal(0, 1)`
- **Evidence**: Propensity for early discontinuation independent of AEs

---

## A — Treatment Assignment

### `arm`
- **Parents**: `risk_category`, `ecog_bl`, `region` (stratification)
- **Equation**: 1:1 stratified block randomization within strata
- **Evidence**: Protocol Section 5.1; stratified by M-status, ECOG, region (within M0)

---

## Lt — Time-Varying (per cycle t = 1..17)

### `thyroid_state[t]`
- **Parents**: `thyroid_state[t-1]`, `arm`, `f_thyroid`, `dose_status[t]`
- **Equation**:
  - If EUTHYROID: prob -> HYPERTHYROID = p_hyper * exp(beta_frailty * f_thyroid) * I(on_treatment)
  - If HYPERTHYROID: prob -> HYPOTHYROID = 0.30/cycle
  - HYPOTHYROID is absorbing state
- **Evidence**: Thyroid dysfunction pattern: transient hyperthyroidism followed by hypothyroidism; 21% hypothyroid in pembro arm

### `tsh[t]`
- **Parents**: `thyroid_state[t]`
- **Equation**:
  - EUTHYROID: `tsh ~ LogNormal(log(2.0), 0.3)`
  - HYPERTHYROID: `tsh ~ LogNormal(log(0.1), 0.5)`
  - HYPOTHYROID: `tsh ~ LogNormal(log(15.0), 0.4)`
- **Evidence**: Clinical thyroid physiology; TSH inversely tracks thyroid function

### `ft4[t]`
- **Parents**: `thyroid_state[t]`
- **Equation**:
  - EUTHYROID: `ft4 ~ Normal(1.2, 0.2)`
  - HYPERTHYROID: `ft4 ~ Normal(2.5, 0.5)`
  - HYPOTHYROID: `ft4 ~ Normal(0.5, 0.15)`
- **Evidence**: Clinical thyroid physiology

### `ae_immune[t]` (pruritus, rash, diarrhea, colitis, hepatitis)
- **Parents**: `arm`, `f_skin` or `f_GI`, `dose_status[t]`, `cycle`
- **Equation**: Per-cycle hazard = base_prob * exp(beta_frailty * f) * I(on_treatment); onset follows Bernoulli per cycle
- **Evidence**: Table S5 AE rates; immune-mediated AEs require active treatment

### `ae_general[t]` (fatigue, arthralgia, nausea)
- **Parents**: `arm`, `f_systemic`, `dose_status[t]`
- **Equation**: Per-cycle hazard = base_prob * exp(beta_frailty * f_systemic); some background rate even off treatment
- **Evidence**: Table S5; general AEs have placebo background rate

### `ae_grade[t]`
- **Parents**: `ae_type`, `arm`
- **Equation**: Grade ~ Categorical with type-specific distribution; pembro arm has slightly higher severe fraction
- **Evidence**: Table S5 grade distribution

### `dose_status[t]`
- **Parents**: `dose_status[t-1]`, `ae_immune[t]`, `ae_general[t]`, `ae_grade[t]`, `f_dropout`
- **Equation**:
  - If previously DISCONTINUED: stays DISCONTINUED
  - If Gr3+ immune AE: hold/discontinue with probability from params
  - If Gr4 any: discontinue with high probability
  - Cumulative holds > 3: discontinue
- **Evidence**: 21.1% discontinuation in pembro; protocol dose modification rules

### `ecog_ps[t]`
- **Parents**: `ecog_bl`, `ae_general[t]`, `recurrence_status`
- **Equation**: ECOG can worsen with multiple concurrent AEs or post-recurrence
- **Evidence**: Generally stable in adjuvant setting pre-recurrence

---

## Recurrence Process

### `latent_recurrence_day`
- **Parents**: `risk_category`, `pdl1_cps`, `sarcomatoid`, `age`, `ecog_bl`, `f_recurrence`, `arm`
- **Equation**: Weibull AFT:
  ```
  log_scale = log(base_scale[risk]) + beta_pdl1 * I(cps>=1) + beta_sarc * sarc
              + beta_age * (age-60)/10 + beta_ecog * ecog + beta_frailty * f_recurrence
              + treatment_effect(arm, t)
  latent_day = weibull_quantile(U, shape, exp(log_scale))
  ```
  Treatment effect: full effect during treatment, waning post-treatment with half-life
- **Evidence**: DFS HR 0.72; risk category drives baseline hazard; Weibull captures decreasing hazard

### `observed_recurrence_day`
- **Parents**: `latent_recurrence_day`, imaging schedule
- **Equation**: `observed_day = next_imaging_day(latent_day, IMAGING_SCHEDULE)`
- **Evidence**: Recurrence detected at scheduled imaging; interval censoring by design

### `recurrence_type`
- **Parents**: `risk_category`, `time_to_recurrence`
- **Equation**: P(distant) = 0.60 if M1_NED, 0.45 if M0_HIGH, 0.35 if M0_INT_HIGH; earlier recurrence more likely distant
- **Evidence**: Higher risk categories have more distant recurrence

---

## Post-Recurrence / Death

### `subsequent_therapy`
- **Parents**: `arm`, `recurrence_type`
- **Equation**: P(subsequent_IO) = 0.80 if prior_placebo, 0.50 if prior_pembro (rechallenge less common)
- **Evidence**: Post-recurrence management patterns; pembro-exposed patients less likely to receive IO

### `death_day_post_recurrence`
- **Parents**: `recurrence_type`, `subsequent_therapy`, `arm`, `time_to_recurrence`
- **Equation**: Weibull AFT from recurrence day:
  ```
  post_recurrence_time = weibull_quantile(U, shape, scale * exp(betas...))
  death_day = recurrence_day + post_recurrence_time
  ```
- **Evidence**: OS data; post-recurrence survival varies by disease biology

### `death_day_no_recurrence`
- **Parents**: `age`, `ecog_bl`
- **Equation**: Exponential with rate = annual_rate + beta_age*(age-60)/10 + beta_ecog*ecog; converted to days
- **Evidence**: Background mortality ~2.7% at 4 years in disease-free patients

---

## Yt — Endpoint Derivation (Deterministic)

### `DFS_DAY`
- **Parents**: `observed_recurrence_day`, `death_day`, `ADMIN_CENSOR_DAY`
- **Equation**: `DFS_DAY = min(observed_recurrence_day, death_day, ADMIN_CENSOR_DAY)`
- **Evidence**: Standard DFS definition: first of recurrence, death, or censoring

### `DFS_EVENT`
- **Parents**: `DFS_DAY`, `observed_recurrence_day`, `death_day`
- **Equation**: `DFS_EVENT = I(DFS_DAY < ADMIN_CENSOR_DAY)`
- **Evidence**: Event if not administratively censored

### `OS_DAY`
- **Parents**: `death_day`, `ADMIN_CENSOR_DAY`
- **Equation**: `OS_DAY = min(death_day, ADMIN_CENSOR_DAY)`
- **Evidence**: Standard OS definition

### `OS_EVENT`
- **Parents**: `OS_DAY`, `death_day`
- **Equation**: `OS_EVENT = I(death_day <= ADMIN_CENSOR_DAY)`
- **Evidence**: Event if death observed before administrative censoring

---

## DAG Gates (Structural Consistency Checks)

| Gate | Variables Tested | Criterion |
|------|-----------------|-----------|
| Thyroid-lab | tsh[t], thyroid_state[t] | TSH > 10 at hypothyroid visits |
| AE-frailty | ae_immune across types | Within-patient r > 0.15 |
| DFS-trajectory | DFS_DAY, latent_recurrence_day | Correlation > 0.95 for events |
| Temporal ordering | recurrence_day, death_day | death >= recurrence always |
| Risk direction | DFS by risk_category | M1 NED worst, M0 int-high best |
| Treatment-dose link | DFS, dose_status | Discontinued patients have less benefit |
