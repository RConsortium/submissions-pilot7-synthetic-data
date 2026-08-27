# ARA06 (NCT00837434) — Evidence-Based Causal DAG

Structural causal model for the anti-TNF-in-RA digital twin (etanercept vs
adalimumab, both on background methotrexate). Variables are organized into the
four g-formula layers and generated in topological order:

```
L0 (baseline)  →  A (arm)  →  Lt (time-varying)  →  Yt (endpoints)
```

Every row carries its evidence **inline** in two columns (skill Citation format):
**Source** = origin-tagged pointer (`ctgov` / `paperclip` / `protocol` / `model`);
**Evidence** = the verbatim quote / exact value the row rests on. `protocol:` =
the user-provided ARA06 v3.0 PDF (ground truth). `model:` = a foundation-model
default or sanity prior with no external source (flagged for replacement).

Latent **frailties** (drawn once per patient, persist across all visits) induce
within-patient correlation across visits and AE types:
`f_heme` (myelosuppression), `f_hepatic` (transaminitis), `f_infect` (infection),
`f_msk` (musculoskeletal/general AE cluster), `f_dropout` (discontinuation).
Plus a latent **`resp`** (maximal fractional clinical improvement) — the engine
of every clinical-response endpoint.

---

## L0 — Baseline covariates (`ara06_baseline.py`)

| Node | Parents | Structural form | Source | Evidence |
|---|---|---|---|---|
| `arm` (is_etn) | ∅ (randomized 2:1, exogenous) | deterministic by index → exactly 43 ETN / 20 ADA | `ctgov: protocolSection/designModule` | "Subjects will be randomized in a 2:1 ratio until 40 and 20 subjects are treated with etanercept and adalimumab" |
| `age` | ∅ | N(52.0, 11.0), clip[18,75] | `ctgov: baselineCharacteristicsModule` | "Mean Age (SD), years … Total 52.0 (11.0)"; eligibility "Age of 18 to 75 years" |
| `sex` | ∅ | Bernoulli(F)=0.793 | `ctgov: baseline` | "Female, n (%) … 46 (79.3)" |
| `race` / `ethnicity` | ∅ | White 0.83; Hispanic 0.155 | `ctgov: baseline` | "Race: White 48 … Black 6"; "Ethnicity: Hispanic/Latino 9" (of 58) |
| `ra_duration_yr` | ∅ | Gamma, mean 5.3 | `ctgov: baseline` | "RA duration, mean (SD) years 5.3 (7.0)" |
| `rf_ccp_positive` | ∅ | Bernoulli(0.759); **randomization stratifier** | `ctgov: baseline` + `protocol: §3.1.2` | "IgM RF or anti-CCP positive 44" (of 58); "stratification based on the presence or absence of antibodies to RF and/or CCP" |
| `mtx_dose` | ∅ | N(17.9, 3.9), clip[7.5,25] | `ctgov: baseline` + `protocol: §4.1` | "MTX dose, mean (SD) mg 17.9 (3.9)"; "Stable dose of MTX between 7.5 mg and 25 mg" |
| `baseline_tjc` | disease severity | N(12.3, 6.7), clip[2,28] | `ctgov: baseline` | "Tender Joint Count, mean (SD) 12.3 (6.7)" |
| `baseline_sjc` | disease severity | N(9.7, 6.0), clip[1,28] | `ctgov: baseline` | "Swollen Joint Count, mean (SD) 9.7 (6.0)" |
| `baseline_crp` | disease severity | lognormal, mean ≈13.8 mg/L | `ctgov: baseline` | "CRP, mean (SD) mg/L 13.8 (24.9)" |
| `baseline_ptglobal/physglobal/pain` | disease severity | N(~50–55 mm, ~18) VAS | `protocol: App. D–F` | "mark a vertical line … 0 none … 10 most" (0–100 mm VAS) — values set so DAS28 lands on baseline |
| `baseline_haqdi` | disease severity | N(1.4, 0.7), clip[0,3] | `ctgov: baseline` | "HAQ-DI score, mean (SD) 1.4 (0.7)" |
| `baseline_das28` | tjc, sjc, crp, ptglobal | DAS28-4(CRP) formula; **resampled until > 4.4** | `protocol: App. C / §4.1` | "DAS28-4(CRP) = 0.56*sqrt(tender28) + 0.28*sqrt(swollen28) + 0.36*ln(CRP+1) + 0.014*GH + 0.96"; "Active RA with DAS28 > 4.4" (target ctgov mean 5.3) |
| `baseline_mem_switched` | sex, frailty | N(18.4, 7.6), clip[2,45] % | `paperclip: pmc_PMC2714135 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2714135/` | "post-switch IgD-CD27+ accumulate with increased disease duration … baseline in RA ~8.7–9.7%" (declines to ctgov wk12 ~13%) |
| `baseline_wbc/anc/alc/hgb/plt` | sex, frailty | N(·)+0.3–0.4·f_heme; eligibility floors | `protocol: §4.2 / 5.3.4.1` | "Neutropenia (ANC < 1,500); Thrombocytopenia (platelets < 100,000); Anemia (Hgb < 9 g/dL)" exclusions → floors |
| `baseline_ast/alt/creat` | age, frailty | N(24/26/0.85)+frailty; eligibility caps | `protocol: §4.2` | "≥ 2 times ULN … AST or ALT"; "Renal insufficiency (serum creatinine > 1.5 mg/dL)" exclusions |
| `frailties` (5) | ∅ | iid N(0, σ) | `model: latent random effects` | shared log-linear effects inducing within-patient AE/lab correlation (FLAURA2 v6 fix) |
| `resp` | arm | N(μ_arm, 0.30), clip[0,0.95]; μ_ETN<μ_ADA | `ctgov: outcomeMeasures` + `paperclip: pmc_PMC2377247 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2377247/` | ctgov ACR50 ADA>ETN (47.4% vs 29.7% wk12); class effect comparable: "Overall therapeutic effects were also similar regardless of the specific anti-TNFα drug used" |
| `comp_mult` (7) | ∅ | N(1.0, 0.30) per ACR component | `model: ACR 3-of-5 spread` | per-component improvement multipliers so the ACR "≥3 of 5" rule is stochastic, not lockstep |

## A — Treatment (`ara06_baseline.py`)

| Node | Parents | Structural form | Source | Evidence |
|---|---|---|---|---|
| `EX` anti-TNF | arm | ETN 50 mg SQ QW **or** ADA 40 mg SQ Q2W × 24 wk | `protocol: §5.2` | "etanercept 50 mg … SQ every week for 24 weeks"; "adalimumab 40 mg SQ every other week for 24 weeks" |
| `EX` methotrexate | ∅ (both arms) | MTX po QW (constant) | `protocol: §3.1` | "subjects will have been receiving a stable dose of MTX … The MTX dose will remain constant throughout the entire trial" |

## Lt — Time-varying state (`ara06_longitudinal.py`)

| Node | Parents | Structural form | Source | Evidence |
|---|---|---|---|---|
| `tjc/sjc/ptglobal/physglobal/pain/haqdi/crp` (t) | baseline value, `resp`, `comp_mult`, ramp(t) | `value_t = base·(1 − clip(resp·ramp(t)·comp_mult))·(1+ε)`; ramp wk12=0.92, wk24=1.05 | `model: monotone response decay` + `ctgov` (calibrated to ACR/DAS28 targets) | response builds over time; magnitude set by latent `resp` (arm-specific). Endpoints read off these. |
| `das28` (t) | tjc, sjc, crp, ptglobal | DAS28-4(CRP) formula (deterministic) | `protocol: App. C` | "DAS28-4(CRP) = 0.56*sqrt(tender28)+0.28*sqrt(swollen28)+0.36*ln(CRP+1)+0.014*GH+0.96" |
| `mem_switched_pct` (t) | baseline_mem, arm, t | wk12 = base·0.76 + (−0.5)·is_etn + N(0,4.5); **arm effect ≈ null** | `ctgov: outcomeMeasures` + `paperclip: pmc_PMC2714135` | ctgov "Etanercept 13.2 (7.3) … Adalimumab 13.8 (7.2) … p-value = 0.3"; literature: "anti-TNF therapy increased … pre-switch memory" and does **not** reduce switched memory (reduction is a rituximab/anti-CD20 effect, not anti-TNF) |
| `wbc/anc/alc/hgb/plt` (t) | prev value, baseline, MTX, f_heme | AR(1) with MTX myelosuppression drag + frailty | `paperclip: pmc_PMC4851368 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4851368/` | "MTX-related myelosuppression … 2 to 10.2% … Neutropenia … 1.4 to 7% … anemia and thrombocytopenia also occur" |
| `ast/alt` (t) | prev value, baseline, MTX, arm, f_hepatic | AR(1) + MTX hepatic drag + ETN extra + strong shared f_hepatic loading | `paperclip: pmc_PMC6186305 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6186305/` | "incidence proportion of elevated transaminases > 1 × ULN for MTX, MTX + INF, MTX + ETA were 19.1%, 14.2%, and 23.5%" — MTX+etanercept highest; shared f_hepatic → AST/ALT co-elevate within patient |
| `creat` (t) | prev value, baseline, arm, f_hepatic | AR(1) + small drag | `ctgov: adverseEventsModule` | "Blood creatinine increased … Etanercept 5 … Adalimumab 1" |
| `AE: lab-derived` (Anaemia, Leukopenia, Neutropenia, Lymphopenia, AST↑, ALT↑, Creatinine↑) | corresponding lab value | **deterministic NCI-CTCAE grade** on the lab, then Bernoulli(report) | `protocol: §7.4.1 (NCI-CTCAE v3.0)` + `ctgov` | "graded … according to the National Cancer Institute's CTCAE Version 3.0"; ctgov counts e.g. "Anaemia … 9 / 3", "AST increased … 10 / 3" |
| `AE: non-lab` (URI, Nasopharyngitis, Bronchitis, Headache, Pain in extremity, Arthralgia, Rash) | frailty cluster, arm | per-visit hazard `log h = log(base)+f_cluster+log_rr_etn·is_etn` | `ctgov: adverseEventsModule` + `paperclip: pmc_PMC3105607 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3105607/` | ctgov per-PT counts (e.g. "Nasopharyngitis 4 / 3"); anti-TNF serious-infection "adjHR 1.2 (95% CI 1.1, 1.5) … risk did not differ … between adalimumab, etanercept and infliximab" |
| `AE: serious` (RA flare; GERD / suicide attempt) | frailty, arm | rare per-visit hazard; flare↑ADA, idiosyncratic↑ETN | `ctgov: adverseEventsModule` | "Rheumatoid arthritis flare … 0 / 1"; "Gastrooesophageal reflux disease … 1 / 0"; "Suicide attempt … 1 / 0" |
| `dose_action` (t) | lab grade | Grade ≥3 lab toxicity → DRUG INTERRUPTED | `protocol: §5.3.5.6, §5.3.5.13` | cytopenia / LFT decision trees: "Stop MTX and study product until cytopenia resolves"; "Hold MTX dose" |
| `discontinuation` (t) | f_dropout, arm | per-visit `expit(intercept_arm + 0.5·f_dropout)`; **reason = administrative, never AE** | `ctgov: participantFlowModule` | ETN withdrawals: "Physician decision (3), lost to follow-up (1), sponsor withdrawal (1), noncompliance (2) …"; ADA: "Lost to follow-up (1)" — no adverse-event discontinuations |

## Yt — Endpoints (`ara06_outcomes.py`) — read off the trajectory, never drawn

| Node | Parents (trajectory) | Structural form | Source | Evidence |
|---|---|---|---|---|
| `mem_b_wk12` (PRIMARY) | `mem_switched_pct` at V5 | = V5 B-cell value | `ctgov: outcomeMeasures (primary)` | "Percentage of CD27+ Switched Memory B Cells at Week 12 … Etanercept 13.2 (7.3); Adalimumab 13.8 (7.2)" |
| `das28resp_wk{12,24}` | das28 at V5/V8 vs V2 | EULAR good-or-moderate response (value + ΔDAS28) | `ctgov: outcomeMeasures` + `protocol: §3.3.2` | "DAS-28-CRP Good or Moderate Response … wk12 ETN 86.5% / ADA 89.5%; wk24 88.2% / 84.2%" |
| `acr20_wk{12,24}` | TJC,SJC + 5 components at V5/V8 vs V2 | ACR20 rule: ≥20% in TJC & SJC and ≥3 of 5 | `ctgov` + `protocol: App. B` | "ACR20 … wk12 ETN 67.6% / ADA 73.7%; wk24 73.5% / 84.2%"; "20% … Response based on improvement: Tender Joint Count, Swollen Joint Count AND … three of the following" |
| `acr50_wk{12,24}` | same | ACR50 rule (≥50%) | `ctgov` + `protocol: App. B` | "ACR50 … wk12 ETN 29.7% / ADA 47.4%; wk24 38.2% / 63.2%" |
| `serious_ae` | AE trajectory | 1 iff any AESER=Y | `ctgov: adverseEventsModule` | "participants with SAEs … Etanercept 2 / Adalimumab 1" |
| `disposition` | discontinuation | COMPLETED / DISCONTINUED | `ctgov: participantFlowModule` | "Completed 34 / 19; Withdrawn 9 / 1" |

## Key causal commitments (preserved by the calibration gates)

1. **All treatment effects flow through mediators.** Arm → `resp` → component
   trajectory → ACR/DAS28; arm → labs → CTCAE grade → lab AE. No direct
   arm→endpoint edge except the single `resp` mean shift and the near-null
   `mem_arm_etn` (both literature/registry-grounded). *(gate g4)*
2. **Lab AEs are deterministic CTCAE functions of lab values** — grade thresholds
   are fixed; only the lab distributions are tunable. *(gates g1, g4)*
3. **Within-patient AE correlation comes from shared frailties**, not independent
   draws (e.g. AST↑/ALT↑ co-elevate via `f_hepatic`). *(gate g3)*
4. **The memory-B primary is honestly null** (p=0.3) — consistent with the
   anti-TNF literature that switched-memory reduction is NOT an anti-TNF effect.
5. **Discontinuations are administrative**, matching the published reasons — so
   the AE↔DS traceability set is correctly empty. *(gate g6)*
