# Causal DAG — RAVE (NCT00104299 / ITN021AI)

Structural causal model for the RAVE trial (rituximab vs. cyclophosphamide→azathioprine for
remission induction in ANCA-associated vasculitis). One row per variable: **parents**,
**structural equation** (g-formula submodel), **Source** (origin-tagged: `ctgov` / `paperclip`
/ `model`), and inline **Evidence** (verbatim quote the row rests on).

Topological order: **L₀ (baseline + frailties) → A (treatment) → Lₜ (time-varying) → Yₜ (endpoints)**.
The simulator (Step 5) generates variables strictly in this order; every endpoint is *derived
from the trajectory*, never drawn directly (see Calibration invariants in the skill).

Trajectory horizon: study days per SoA — V1(d1) … V8(d180, month-6 primary endpoint) … V12(d545,
month 18). `ADMIN_CENSOR_DAY = 545`.

## Disease model in one paragraph

RAVE is **not** a tumor trial; the central latent state is **BVAS/WG disease activity** (0 =
remission). Both arms are *effective* remission-induction regimens (the trial showed
non-inferiority, not a large effect), so the dominant *treatment* signal is **not** on efficacy
but on the **toxicity profile**: oral cyclophosphamide (control arm) drives myelosuppression
(leukopenia/neutropenia) and emesis/alopecia, while rituximab drives B-cell depletion /
hypogammaglobulinemia and infusion reactions. The **primary endpoint** (complete remission at 6
months) is a deterministic readout of the BVAS/WG trajectory **and** the protocol glucocorticoid
taper, not a parametric survival draw.

---

## Latent frailties (drawn once per patient at baseline; persist across all visits)

These induce within-patient correlation across visits and across related AE types — the
mechanism FLAURA2 v6 was missing. Each is N(0, σ²) on a log-hazard / linear-predictor scale.

| Frailty | Shared across | Role | Source | Evidence |
|---|---|---|---|---|
| `f_heme` | WBC, ANC, HGB, PLT | myelosuppression susceptibility (cytopenia cluster) | `model: latent-frailty default` | "Always introduce a frailty per AE cluster" — skill design (FLAURA2 v6 fix) |
| `f_infect` | all infection PTs | infection susceptibility (B-cell depletion / immunosuppression) | `paperclip: PMC10176387 https://pmc.ncbi.nlm.nih.gov/articles/PMC10176387/` | "A lower total number of CD19+ B cells at baseline and at month one was observed in patients with severe infections … in the rituximab (RTX) arm" |
| `f_GI` | nausea, vomiting, diarrhea | chemo/azathioprine emesis cluster | `model: latent-frailty default` | GI AEs co-occur within patient on cytotoxic therapy; shared-frailty default |
| `f_relapse` | flare hazard after remission | unobserved relapse propensity | `paperclip: PMC8407598 https://doi.org/10.1093/rap/rkab018` | "Relapses affect 30–50% of patients with ANCA-associated vasculitis (AAV) over 5 years" |
| `f_steroid` | hyperglycemia, cushingoid, insomnia | glucocorticoid-toxicity susceptibility | `paperclip: PMC10910690 https://pmc.ncbi.nlm.nih.gov/articles/PMC10910690/` | "Higher cumulative glucocorticoid doses correlated with increased toxicity" |
| `f_dropout` | discontinuation hazard | unobserved dropout propensity | `model: latent-frailty default` | dropout-propensity default (CTGov ~9–10% non-completion per arm) |

---

## L₀ — Baseline covariates (shaped by eligibility)

| Node | Parents | Structural equation | Source | Evidence |
|---|---|---|---|---|
| `age` | — | Normal(52.8, 15.5), clip [15, 90] | `ctgov: resultsSection/baselineCharacteristicsModule "Age, Continuous"` | "54.0 (16.8)" RTX, "51.5 (14.1)" Control; total mean 52.8 (SD 15.5) |
| `sex` | — | Bernoulli(P(female)=0.49) | `ctgov: baseline "Sex: Female, Male"` | "Female {BG002: 97}", "Male {BG002: 100}" → 49.2% female |
| `country` | — | Categorical{USA 0.92, NLD 0.08} | `ctgov: baseline "Region of Enrollment"` | "United States … 181", "Netherlands … 16" |
| `weight_kg` | sex, age | Normal(80/68 by sex, 16), clip ≥40 | `ctgov: eligibility` + `model` | "Weight of at least 88 pounds (40 kilograms)" (drives BSA for RTX mg/m² & CYC mg/kg) |
| `diagnosis_type` (GPA vs MPA) | — | Bernoulli(P(GPA)=0.75) | `paperclip: protocol.pdf` (`model` mix) | "Diagnosis of WG or MPA according to the Chapel Hill Consensus Conference definitions"; RAVE enrolled ~75% GPA/WG |
| `anca_type` (PR3 vs MPO) | diagnosis_type | Bernoulli(P(PR3)=0.66) | `ctgov: eligibility` | "positive for either PR3-ANCA … or MPO-ANCA … at the screening" (stratification factor; RAVE ~2:1 PR3:MPO) |
| `new_diagnosis` (new vs relapsing) | — | Bernoulli(0.5) | `ctgov: eligibility` | "Newly diagnosed patient … OR must be experiencing a disease flare" (stratification factor) |
| `renal_involvement` | anca_type, diagnosis_type | Bernoulli(expit(−0.2 + 0.4·MPO)) | `model: AAV phenotype default` | MPO-AAV more renal-predominant; PR3 more ENT/pulmonary (sanity default) |
| `baseline_bvaswg` | new_diagnosis | Normal(8.0, 3.1), clip ≥3 | `ctgov: baseline "BVAS/WG"` | "8.1 (2.8)" RTX, "8.0 (3.4)" Control; eligibility "BVAS/WG of 3 or greater" |
| `baseline_vdi` | age | round·Normal(1.2, 1.7), clip ≥0 | `ctgov: baseline "VDI"` | "1.4 (1.8)" RTX, "1.0 (1.4)" Control |
| `htn`, `dm` | age | logistic in (age−60) | `model: age-logistic default` | comorbidity prevalence rises with age (no trial-specific source) |
| `baseline_wbc` | f_heme | Normal(8.0, 2.2), clip ≥4.0 | `ctgov: protocol exclusion` | "White blood cell count less than 4000/mm3 … [excluded]" → support ≥4.0 ×10⁹/L |
| `baseline_anc` | baseline_wbc, f_heme | 0.6·WBC + Normal(0,0.8), clip ≥1.5 | `model: CBC differential default` | ANC ≈ 55–65% of WBC (sanity default) |
| `baseline_plt` | f_heme | Normal(300, 80), clip ≥120 | `ctgov: protocol exclusion` | "platelet counts less than 120,000/mm3 … [excluded]" |
| `baseline_hgb` | sex, renal_involvement | Normal(13.5/12.3 by sex − 0.8·renal, 1.3) | `model: anemia-of-inflammation default` | AAV/renal disease lowers Hgb (sanity default) |
| `baseline_creat` | age, sex, renal_involvement | Normal(0.9 + 0.8·renal, 0.3), clip ≤4.0 | `ctgov: protocol exclusion` | "Serum creatinine level greater than 4.0 mg/dl … [excluded]" |
| `baseline_crp` | baseline_bvaswg | Normal(2.0 + 0.5·BVAS, 3), clip ≥0 | `model: inflammation-tracks-activity` | CRP rises with active vasculitis (sanity default; chemistry = BUN/creatinine/CRP only) |

---

## A — Treatment assignment & exposure

| Node | Parents | Structural equation | Source | Evidence |
|---|---|---|---|---|
| `arm` | — (randomized, exogenous) | Bernoulli(0.5): RTX vs CYC | `ctgov: designModule` | "allocation: RANDOMIZED … masking: DOUBLE"; arms n=99 / n=98 ≈ 1:1 |
| `rituximab_exposure[t]` | arm | active (real or placebo) at V1–V4 (d1,8,15,22) | `paperclip: protocol.pdf` | "intravenous infusions of rituximab (375 mg/m2/week times 4)" |
| `cyc_active[t]` | arm | control arm, induction (d1–~90), oral daily | `paperclip: protocol.pdf` | "The control arm will receive CYC (2 mg/kg, with doses modified for renal dysfunction)" |
| `aza_active[t]` | arm | control arm, maintenance (after CYC→AZA switch, mo 3–6 on) | `paperclip: protocol.pdf` | "The control arm will switch from daily CYC to AZA (2 mg/kg/day)" |
| `prednisone_dose[t]` | t | protocol taper: ~1 mg/kg/day → 0 by day 180 (month 6) | `paperclip: protocol.pdf` | "prednisone will be tapered so that by month 6 all participants in clinical remission will be off glucocorticoids" |

**Identification note:** `arm` is the *only* exogenous treatment node. All arm→endpoint effects
must flow through the mediators below (labs, AEs, BVAS/WG, GC taper) — no direct arm→endpoint edge
(skill calibration invariant #2).

---

## Lₜ — Time-varying state (per visit, topological within visit)

| Node | Parents | Structural equation | Source | Evidence |
|---|---|---|---|---|
| `wbc[t]` | wbc[t−1], baseline_wbc, cyc_active, f_heme | AR(1): 0.5·prev + 0.5·base − cyc_drag(1.8+0.6·f_heme) + N(0,0.7) | `paperclip: PMC5880843 https://pmc.ncbi.nlm.nih.gov/articles/PMC5880843/` | "neutropenia of ≤ 0.5 × 10⁹/L occurred in 9 (16%) PO and 0 (0%) IV cyclophosphamide patients (P = 0.003) … PO administration induces greater marrow toxicity" |
| `anc[t]` | wbc[t], f_heme | ≈0.6·wbc[t] + N(0,0.4) | `model: CBC differential` | ANC tracks WBC; deterministic CTCAE neutropenia grading downstream |
| `hgb[t]` | hgb[t−1], baseline_hgb, cyc_active, f_heme | AR(1) with mild cyc drag (0.6+0.2·f_heme) | `ctgov: adverseEventsModule "Anaemia"` | "Anaemia … {EG000: 22}, {EG001: 18}" (similar both arms → small arm effect) |
| `plt[t]` | plt[t−1], baseline_plt, cyc_active, f_heme | AR(1), small cyc drag | `ctgov: outcomeMeasures "Gr ≥2 Thrombocytopenia"` | "{OG000: 4}, {OG001: 1}" (slightly higher RTX) |
| `creat[t]`, `bun[t]` | prev, baseline_creat, renal_involvement, bvaswg[t] | AR(1) improving as BVAS/WG falls (renal recovery) | `paperclip: PMC8407598 https://doi.org/10.1093/rap/rkab018` | "anti-PR3 ANCA positivity, cardiovascular involvement, and creatinine levels are associated with relapse risk" |
| `crp[t]`, `esr[t]` | prev, bvaswg[t] | track disease activity (fall with remission) | `ctgov: adverseEventsModule "C-reactive protein increased"` | "C-reactive protein increased … {EG000: 8}, {EG001: 9}" |
| `hematuria[t]` | renal_involvement, bvaswg[t] | ordinal; resolves as renal vasculitis controlled | `ctgov: adverseEventsModule "Haematuria"` | "Haematuria … {EG000: 6}, {EG001: 14}" |
| `bvaswg[t]` | bvaswg[t−1], arm, prednisone_dose, anca_type, new_diagnosis, f_relapse | latent activity: exp decay toward 0 under induction (both arms), GC accelerates; post-remission flare hazard (PR3/relapsing ↑) | `ctgov: outcomeMeasures (primary)` + `paperclip: PMC8407598` | "63 [/99] vs 52 [/98] [complete remission]" (arms ≈ equivalent); "anti-PR3 ANCA-positive patients are at an increased risk of relapse" |
| `flare[t]` | bvaswg[t], anca_type, prednisone_dose, f_relapse | after remission: hazard ↑ with PR3, ↓ with prednisone | `paperclip: PMC4520074 https://pmc.ncbi.nlm.nih.gov/articles/PMC4520074/` | "the relapse rate in MPO-ANCA positive cases was lower than that of PR3-ANCA positive cases (17 % and 56 %, respectively)" |

### AEs derived/sampled at each visit

| Node | Parents | Structural equation | Source | Evidence |
|---|---|---|---|---|
| `leukopenia[t]` / `neutropenia[t]` | wbc[t] / anc[t] | **deterministic CTCAE v3.0 grading** of WBC/ANC + reporting prob | `model: CTCAE v3.0 rule` (grade) + `ctgov` (target) | "NCI-CTCAE version 3.0 … was used to grade severity"; targets "Leukopenia {EG000:13},{EG001:39}", "WBC count decreased {EG000:6},{EG001:21}" |
| `anemia[t]`, `thrombocytopenia[t]` | hgb[t], plt[t] | deterministic CTCAE grading | `model: CTCAE v3.0 rule` | grading fixed; lab distribution is the tunable knob (skill invariant #5) |
| `nausea/vomiting/diarrhea[t]` | f_GI, cyc_active, aza_active | log-hazard = base + f_GI + log(RR_chemo) | `ctgov: adverseEventsModule` | "Nausea {EG000:25},{EG001:31}", "Vomiting {EG000:8},{EG001:13}" (control ≥ RTX) |
| `alopecia[t]` | cyc_active | hazard ↑ on cyclophosphamide | `ctgov: adverseEventsModule "Alopecia"` | "Alopecia … {EG000: 11}, {EG001: 21}" (CYC arm higher) |
| `infection[t]` (incl. serious) | f_infect, rituximab_exposure, cyc_active, prednisone_dose | hazard from frailty + immunosuppression; ~balanced across arms in RAVE | `paperclip: PMC5570101 https://pmc.ncbi.nlm.nih.gov/articles/PMC5570101/` + `ctgov` | "hypogammaglobulinemia occurs in >50% of AAV patients treated with RTX … 13% of patients developed infections requiring hospitalization"; CTGov "Grade 3 or Higher Infections {OG000:18},{OG001:16}" |
| `infusion_reaction[t]` | rituximab_exposure (real, RTX arm) | hazard at V1–V4 infusions; small | `ctgov: outcomeMeasures` | "Infusion Reactions Leading to Infusion Disc. {OG000:1},{OG001:0}" |
| `steroid_ae[t]` (hyperglycemia, cushingoid, insomnia) | prednisone_dose[t], f_steroid | hazard ∝ current prednisone dose | `paperclip: PMC10547218 https://pmc.ncbi.nlm.nih.gov/articles/PMC10547218/` | "greater number of GC-related toxic adverse events in the high-dose cohort (44% … vs 29% …)" |
| `hypogammaglobulinemia[t]` | rituximab_exposure, prior_cyc, sex | latent; ↑ with RTX, prior CYC, female; feeds `f_infect` | `paperclip: PMC8149951 https://doi.org/10.3389/fimmu.2021.671503` | "Hypogammaglobulinemia … with prior cyclophosphamide and female sex predicting worse outcomes" (OR 3.60 prior CYC; OR 8.57 female) |

### Actions (descendants of AEs/disease — never parents of endpoints except through disposition)

| Node | Parents | Structural equation | Source | Evidence |
|---|---|---|---|---|
| `dose_modification[t]` | leukopenia[t], neutropenia[t] | CYC/AZA hold or 50% reduce on cytopenia; pre-infusion WBC<3.0 → withhold | `paperclip: protocol.pdf SoA fn17` | "If a pre-infusion WBC <3,000/mm3 is noticed, the infusion should be withheld" |
| `crossover[t]` | bvaswg[t] (non-response/flare), V5–V8 window | switch to alternate blinded drug | `paperclip: protocol.pdf Appendix 2` | "Participants can be crossed over to the alternate drug treatment any time between visit V5 … and visit V8" |
| `discontinuation[t]` | f_dropout, serious AE, flare, death | logistic hazard | `ctgov: participantFlowModule dropWithdraw` | reasons "Adverse Event {3,1}", "Death {2,2}", "Withdrawal by Subject {2,6}", "Physician Decision {1,1}" |

---

## Yₜ — Endpoints (DERIVED from trajectory; never drawn directly)

| Node | Parents (trajectory) | Derivation rule | Source | Evidence |
|---|---|---|---|---|
| `complete_remission_6mo` | bvaswg[d180], prednisone_dose[d180] | **1 iff BVAS/WG=0 AND prednisone taper complete (dose=0) at day 180** | `ctgov: outcomeMeasures[0] (PRIMARY)` | "A BVAS/WG score of 0 with prednisone taper successfully completed at six months"; target "63 [/99] vs 52 [/98]" |
| `time_to_remission` | bvaswg[·] | first day BVAS/WG=0 | `ctgov: outcomeMeasures[5]` | medians "57 vs 43" days; "Cox … 1.0 (0.7–1.3)" |
| `time_to_complete_remission` | bvaswg[·], prednisone_dose[·] | first day BVAS/WG=0 & off GC | `ctgov: outcomeMeasures[6]` | medians "180 vs 183" days; "Cox … 1.3 (0.9–1.8)" |
| `flare_event`, `flare_day`, `remission_duration` | flare[·] after remission | first flare day post-remission; censor at crossover/mo18 | `ctgov: outcomeMeasures[4]` | "Cox Proportional Hazard 0.9 (0.6–1.5)" (duration of remission to flare) |
| `serious_ae` | infection/cytopenia/flare serious AEs | any AESER=Y over trajectory | `ctgov: adverseEventsModule eventGroups` | "seriousNumAffected 60/99 [RTX]" vs "47/98 [Control]" |
| `death` | serious AE, disease | low hazard; ~2 per arm | `ctgov: outcomeMeasures "Death"` | "{OG000: 2}, {OG001: 2}" |
| `disposition` | discontinuation/death/completion | terminal status + reason | `ctgov: participantFlowModule` | "COMPLETED {FG000:90, FG001:88}" |

---

## DAG gates (Step-6 causality checks — must hold after every calibration update)

1. **AE↔lab linkage**: mean WBC at a `Leukopenia`/`Neutropenia` AE row ≪ mean WBC overall
   (deterministic CTCAE rule, not a random draw). Cf. skill invariant #5.
2. **Arm→myelosuppression mediation**: control (CYC) arm leukopenia/WBC-decreased rate > RTX arm,
   and this flows through `wbc[t]` (no direct arm→leukopenia edge). Target ratio ≈ 39:13 / 21:6.
3. **Within-patient AE-AE correlation**: GI-cluster AEs (nausea/vomiting/diarrhea) positively
   correlated within patient via `f_GI` (r > 0).
4. **Primary endpoint = trajectory**: `complete_remission_6mo` reproducible as
   `1{bvaswg[d180]==0 & prednisone[d180]==0}` with correlation 1.0 to the emitted CR flag.
5. **Stratifier→outcome direction**: PR3 (vs MPO) and relapsing (vs new) patients show higher
   flare rate (sign matches `paperclip: PMC8407598` HR 1.69).
6. **No endpoint drawn directly**: no Weibull/parametric draw of remission/flare conditioned only
   on arm — all via BVAS/WG + GC trajectory.

## Evidence dossier — literature priors (paperclip)

| Edge | Source | Verbatim quote | Effect used |
|---|---|---|---|
| PR3-ANCA → ↑relapse | `paperclip: PMC8407598 https://doi.org/10.1093/rap/rkab018` | "anti-PR3 ANCA positivity [HR 1.69 (95% CI 1.46, 1.94)]" | flare log-HR ≈ +0.52 for PR3 |
| (heterogeneity) serotype no effect | `paperclip: PMC10836254` | "The ANCA serotype also had no effect on either disease relapse (p = .20)" | down-weight: modest PR3 effect, not deterministic |
| PR3 vs MPO relapse rates | `paperclip: PMC4520074` | "relapse rate in MPO-ANCA positive cases was lower than that of PR3-ANCA positive cases (17 % and 56 %)" | corroborates direction |
| oral CYC → neutropenia | `paperclip: PMC5880843` | "neutropenia of ≤ 0.5 × 10⁹/L occurred in 9 (16%) PO and 0 (0%) IV cyclophosphamide patients (P = 0.003)" | CYC arm WBC drag (oral route) |
| CYC dose → leukopenia | `paperclip: PMC8294897` | "lower rate of leukopenia (HR = 2.73 [95% CI, 1.2−6.3], P = .014)" | dose-dependent myelosuppression |
| RTX → severe infection (RAVE) | `paperclip: PMC10176387` | "11 of 99 patients (11.1%) experienced severe infections" (RTX arm) | infection hazard calibration anchor |
| RTX hypogamma → infection | `paperclip: PMC5570101` | "hypogammaglobulinemia occurs in >50% of AAV patients treated with RTX … 13% … infections requiring hospitalization" | f_infect prior |
| RTX serious infection rare | `paperclip: PMC6324375` | "serious infections were rare, occurring at a rate of 0.85 per 10 patient-years" | sanity bound |
| GC dose → toxicity | `paperclip: PMC10547218` | "greater number of GC-related toxic adverse events in the high-dose cohort (44% … vs 29% …)" | steroid_ae ∝ prednisone dose |
