# Causal DAG — CATH (NCT00789880 / ADVN CATH 03-01)

Structural causal model for the CATH substudy (oral vitamin D3 4000 IU/day × 21 d vs placebo;
change in skin antimicrobial-peptide / TH2-cytokine mRNA expression in atopic dermatitis,
psoriasis, and non-atopic controls). One row per variable: **parents**, **structural equation**
(g-formula submodel), **Source** (origin-tagged `ctgov` / `paperclip` / `model`), and inline
**Evidence** (verbatim quote the row rests on).

Topological order: **L₀ (baseline + frailties) → A (treatment) → Lₜ (Day-21 state) → Yₜ (change endpoints)**.
The simulator (Step 5) generates variables strictly in this order; every endpoint is a **change
score derived from the trajectory** (Day21 − Baseline), never drawn directly (skill invariant #1).

Trajectory horizon: SCRN (d −8, screening bloods) → BASE (d 0, baseline biopsy + randomization)
→ D21 (d 21, repeat biopsy + bloods). `ADMIN_CENSOR_DAY = 21`.

## Disease model in one paragraph

CATH is **not** a survival trial; the central latent state is **skin innate-immune peptide
expression** — cathelicidin (**CAMP**/LL-37) and β-defensin-3 (**HBD-3**) — plus the TH2 cytokine
**IL-13**, measured by qRT-PCR in lesional/non-lesional punch biopsies at Day 0 and Day 21. The
mechanistic hypothesis is that oral vitamin D3 raises **serum 25-OH-D**, which (via the vitamin D
receptor and a VDRE in the *CAMP* promoter) induces cathelicidin in keratinocytes. But baseline
cathelicidin is already **high in psoriasis lesions** and **blunted in atopic dermatitis**, so the
trial's own result was **null** — small, noisy, group/skin-specific changes with overlapping arms.
The SCM therefore encodes a **near-null treatment effect routed through the realized 25-OH-D rise**
(arm → 25-OH-D → Δexpression), with cell-specific measurement variance and a shared latent
antimicrobial-peptide frailty that correlates CAMP and HBD-3 within a patient.

---

## Latent frailties (drawn once per patient at baseline; persist across visits)

These induce within-patient correlation across the related peptides — the mechanism a naïve
independent-draw model would miss. Each is N(0, σ²) on the change scale.

| Frailty | Shared across | Role | Source | Evidence |
|---|---|---|---|---|
| `f_amp` | ΔCAMP, ΔHBD-3, tape/saliva cathelicidin | shared antimicrobial-peptide responsiveness (cathelicidin + defensin co-regulation) | `paperclip: PMC4206472 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4206472/` | _(excerpt)_ "…1,25(OH)2D3 … increased DEFB4 and CAMP gene expression and … production of HBD-2 and LL-37" (CAMP & defensin co-induced → shared frailty) |
| `f_th2` | ΔIL-13, ΔIL-4, IgE | TH2-axis activation (atopy) | `paperclip: PMC7307373 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7307373/` | "Increased serum total IgE level, peripheral eosinophils, and basophils were seen more frequently in AD patients than in non-AD patients (P < .05)" (shared TH2 tone) |
| `f_dropout` | discontinuation propensity | unobserved dropout propensity | `model: latent-frailty default` | dropout-propensity default (CTGov 6/82 non-completion); drop assignment pinned to published flow |

---

## L₀ — Baseline covariates (shaped by eligibility; per-cell from ctgov baseline)

| Node | Parents | Structural equation | Source | Evidence |
|---|---|---|---|---|
| `dxgroup` (NONAD/AD/PSO) | — (enrollment stratum) | fixed per cell to match started counts (16/16/8 VITD; 16/18/8 PLAC) | `ctgov: resultsSection/participantFlowModule` | STARTED "{FG000:16, FG001:16, FG002:8, FG003:16, FG004:18, FG005:8}" |
| `arm` (VITD/PLAC) | — (randomized, exogenous) | fixed per cell (≈1:1 within group) | `ctgov: designModule` | "allocation: RANDOMIZED … masking: QUADRUPLE"; "oral vitamin D3 (cholecalciferol, 4,000 … IU)" vs "vitamin D3-placebo" |
| `age` | — | Normal(per-cell mean, sd), clip [18,70] | `ctgov: baseline "Age, Continuous"` | total "32.5 (10.9)"; per cell e.g. Pso-VitD "40.5 (11.6)", AD-Plac "28.6 (9.8)" |
| `sex` | dxgroup,arm | Bernoulli(per-cell female fraction) | `ctgov: baseline "Sex: Female, Male"` | "Female … {BG006(Total): 44}", "Male … {BG006: 38}" → 53.7% female |
| `race`,`ethnic` | — | Categorical(White .66/Asian .12/Black .11/Other .11; Hispanic .11) | `ctgov: baseline "Race/Ethnicity"` | "White … 54", "Asian … 10", "Black … 9", "Hispanic or Latino … 9" (of 82) |
| `fitzpatrick` (I–VI) | race | Categorical(pooled; darker if Black) | `ctgov: baseline "Fitzpatrick Skin Scale"` | "Fair … 20", "Medium … 26", "Olive … 22", "Markedly Black … 6" |
| `bmi`,`height`,`weight` | sex,dxgroup,arm | BMI Normal(per-cell), weight = BMI·(h/100)² | `ctgov: baseline "Body Mass Index"` | total "25.3 (4.9)"; Pso higher ("28 (6.9)") |
| `base_vitd_25oh` | age, bmi, fitzpatrick | Normal(per-cell mean) − 0.12·(age−ā) − 0.20·(bmi−b̄) − 1.2·(fitz−3) + ε (covariate terms centred → cell mean preserved) | `ctgov: baseline "Serum Vitamin D 25-Hydroxy"` + `paperclip: PMC8838096`, `PMC6616201` | ctgov total "29.2 (11.2)"; "older age … higher waist/hip ratio … were independent correlates of lower serum calcidiol"; "Major determinants … include sun exposure, skin reflectance, and adiposity" |
| `base_calcium` | — | Normal(per-cell), clip [8.4,10.6] | `ctgov: baseline "Serum Calcium"` | total "9.4 (0.4)" — normocalcemic (eligibility excludes abnormal Ca) |
| `base_pth` | base_vitd_25oh | Normal(per-cell) − 0.4·(25OHD−mean), clip [8,90] | `ctgov: baseline "Serum Parathyroid Hormone"` | total "34.4 (11.4)" (PTH inversely tracks vitamin D) |
| `base_creat` | — | Normal(per-cell), clip [0.4,1.3] | `ctgov: baseline "Serum Creatinine"` | total "0.8 (0.2)" (eligibility excludes abnormal creatinine) |
| `base_ige` | dxgroup (atopy) | LogNormal(method-of-moments to per-cell mean/sd) | `ctgov: baseline "Total Serum IgE"` + `paperclip: PMC7307373` | AD-VitD "1870.1 (3310.5)", AD-Plac "724.9 (2030.6)" vs Non-AD/Pso ~46–85; "Increased serum total IgE … more frequently in AD patients than in non-AD" |
| `base_rast` | base_ige | ordinal from log10(IgE) | `ctgov: outcomesModule` (RAST measured) | RAST testing per protocol; correlated with total IgE |
| `base_biopsy[comp].{CAMP,HBD3,IL13,IL4}` | dxgroup, compartment | model level + offset + cv·N; psoriasis-lesional cathelicidin/HBD high, AD-lesional blunted, IL-13 high in AD-lesional | `paperclip: PMC3346901 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3346901/` | "In atopic dermatitis, cathelicidin induction might be disturbed … In contrast, psoriasis is characterized by overexpression of cathelicidin" |
| `base_pasi` (PSO only) | dxgroup | Normal(8,3), clip [1,30] | `model: psoriasis-severity default` | mild–moderate plaque psoriasis (protocol §8.1 / Appendix I); absolute level not posted |
| `base_cfu[comp]` | compartment | Normal(4.0 log10 + 0.6·lesional, 0.5) | `model: skin-flora default` | bacterial colony counts collected (protocol §11.5); no posted value |

**Compartments:** AD & PSO biopsy LESIONAL + NONLESIONAL; NONAD (healthy) NONLESIONAL only.

---

## A — Treatment assignment & exposure

| Node | Parents | Structural equation | Source | Evidence |
|---|---|---|---|---|
| `arm` | — (randomized) | VITD vs PLAC, ≈1:1 within dxgroup | `ctgov: designModule` | "allocation: RANDOMIZED" |
| `vitd_exposure` | arm | 4000 IU/day PO × 21 d (or placebo); compliance by pill count | `paperclip: protocol §9.1` + `ctgov: armsInterventionsModule` | "Subjects received a 21-day course of oral vitamin D3 (cholecalciferol, 4,000 … IU)" |

**Identification note:** `arm` is the *only* exogenous treatment node. All arm→endpoint effects flow
through the **serum 25-OH-D mediator** below — no direct arm→Δexpression edge (skill invariant #2).

---

## Lₜ — Day-21 state (per visit, topological within visit)

| Node | Parents | Structural equation | Source | Evidence |
|---|---|---|---|---|
| `vitd_25oh[D21]` **(treatment mediator)** | arm, base_vitd_25oh | base + ΔD: VITD ~ N(+10, 4); PLAC ~ N(+0.3, 2) | `paperclip: PMC506781 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC506781/` + `PMC4148309` | "Supplementation … produced mean 25(OH)D levels of … 112 ± 41 nmol/L for the 100 mcg/day [4000 IU] group"; "3000 IU … increased … (186% versus 14% [placebo])" |
| `responded` | vitd_25oh[D21], base_vitd_25oh | 1{Δ25OHD > 4 ng/mL} (mediator indicator routing arm→Δexpression) | `model: mediator threshold` | operationalizes "did the supplement raise 25-OH-D" — ~93% of VITD, ~0% of PLAC |
| `calcium[D21]` | base_calcium | base + N(0,0.15), clip < 10.6 (no hypercalcemia) | `paperclip: PMC506781` + `PMC4148309` | "no effect on plasma calcium"; "No change … in urinary calcium excretion" |
| `pth[D21]` | base_pth, arm | base − 2·1{VITD} + N(0,4) (physiologic suppression) | `paperclip: PMC506781` | "Both doses lowered plasma parathyroid hormone" |
| `creat[D21]` | base_creat | base + N(0,0.05) (stable) | `model: short-trial stability` | 21-day dermatology dosing; renal function unchanged |
| `Δbiopsy[comp].CAMP` **(primary)** | base_biopsy, arm, responded, f_amp | VITD: δ = m_plac + (eff−m_plac)·responded + 0.8·f_amp + N(0,√(sd²−0.8²)), where eff = (m_vitd−(1−p)·m_plac)/p and p = P(responded) — so the **marginal** VITD mean is exactly m_vitd while the effect is realized only in 25-OH-D responders. PLAC: δ = m_plac + 0.8·f_amp + noise. D21 = base + δ | `ctgov: outcomeMeasuresModule (PRIMARY)` + `paperclip: PMC4206472`, `PMC2709447` | cell means/SDs e.g. AD-lesional "VitD −0.4 (2.8) / Plac 0.1 (2.4)"; mechanism "vitamin D analogs induced cathelicidin through activation of the vitamin D receptor and MEK/ERK signaling" |
| `Δbiopsy[comp].HBD3` **(primary)** | base_biopsy, arm, responded, f_amp | same form, HBD-3 cell targets, shared `f_amp` | `ctgov: outcomeMeasuresModule (PRIMARY)` + `paperclip: PMC4206472` | "VitD −0.1 (7.3) / Plac −0.8 (2.8)" (AD-lesional); "increased … production of HBD-2 and LL-37" |
| `Δbiopsy[comp].IL13` **(secondary)** | base_biopsy, arm, responded, f_th2 | same form, IL-13 cell targets, loading on `f_th2` | `ctgov: outcomeMeasuresModule (SECONDARY)` + `paperclip: PMC4425186` | "VitD −2.1 (4.6) / Plac −0.1 (4.1)" (Pso-lesional); "1,25(OH)2D … induces … IL-4" (TH2 modulation; IL-13-specific magnitude not OA — `model` near-null per trial) |
| `Δbiopsy[comp].IL4` | Δbiopsy.IL13 | 0.5·ΔIL13 + N(0,1.2) | `model: TH2 coupling` (no posted target) | IL-4 co-measured (protocol); tracks IL-13; no CTGov value |
| `saliva_camp[D21]`,`tape_camp[comp,D21]` | f_amp, ΔCAMP | track biopsy cathelicidin via f_amp + tape_load·ΔCAMP | `paperclip: protocol §14.2.11` (`model` levels) | tape-strip-vs-biopsy correlation objective; absolute values not posted |
| `cfu[comp,D21]` | base_cfu | base + N(0,0.3) | `model: skin-flora default` | colony counts collected; no posted change |
| `pasi[D21]` (PSO) | base_pasi | base − 0.6 + N(0,2) | `model: psoriasis course default` | PASI collected; no posted change (slight improvement) |
| `ige[D21]` | base_ige | base·(1 + 0.10·N) (small) | `ctgov` (IgE measured) + `model` | trial hypothesized IgE decrease; observed change not significant → small |

### Adverse events (sampled at D21; sparse)

| Node | Parents | Structural equation | Source | Evidence |
|---|---|---|---|---|
| `ae_mild[t]` (constipation/nausea/abdominal distension/headache) | — | per-PT hazard 0.04, grade 1, non-serious | `ctgov: adverseEventsModule` + `paperclip: protocol §9.2.3` | "There were no serious adverse events. No adverse events occurred at a 5% or greater frequency threshold"; "most common complaints … constipation, gas, and bloating" |
| `ae_procedure[t]` (skin reaction / erythema) | — | hazard 0.03, grade 1, non-serious | `paperclip: protocol §16` | "a very mild erythema may develop … after a series of tape stripping … expected to resolve within 12 hours" |
| `serious_ae` | (none) | structurally 0 | `ctgov: adverseEventsModule eventGroups` | "seriousNumAffected 0/16 … 0/18 …" across all groups |

### Disposition (descendant; never a parent of the change endpoints)

| Node | Parents | Structural equation | Source | Evidence |
|---|---|---|---|---|
| `discontinuation` | f_dropout (pinned to published flow) | 6 dropouts assigned by cell to reproduce participantFlow exactly | `ctgov: participantFlowModule dropWithdraws` | "Adverse Event {FG004:1}", "Protocol Violation {FG001:1, FG003:1}", "Withdrawal by Subject {FG000:1, FG004:2}" |
| `ae→withdrawal link` | discontinuation reason, serious/triggering AE | the AD-Placebo AE-dropout's AE gets AEACN=DRUG WITHDRAWN (deterministic projection) | `ctgov: participantFlowModule` | "Adverse Event … {FG004: 1}" → AE↔DS traceability |

---

## Yₜ — Endpoints (DERIVED from trajectory; never drawn directly)

| Node | Parents (trajectory) | Derivation rule | Source | Evidence |
|---|---|---|---|---|
| `dCAMP_{LES,NL}` | biopsy[BASE], biopsy[D21] | CAMP(D21) − CAMP(BASE) per compartment (completers only) | `ctgov: outcomeMeasures (PRIMARY)` | "Change From Baseline on Day 21 in Relative Abundance of CAMP mRNA …" |
| `dHBD3_{LES,NL}` | biopsy[BASE], biopsy[D21] | HBD-3(D21) − HBD-3(BASE) | `ctgov: outcomeMeasures (PRIMARY)` | "… HBD-3 mRNA …" |
| `dIL13_{LES,NL}` | biopsy[BASE], biopsy[D21] | IL-13(D21) − IL-13(BASE) | `ctgov: outcomeMeasures (SECONDARY)` | "… IL-13 mRNA …" |
| `dVITD25OH` | vitd_25oh[SCRN], vitd_25oh[D21] | D21 − screening (the realized mediator change) | `ctgov: baseline` (25-OH-D measured pre/post) | serum 25-OH-D drawn at screening + Day 21 |
| `completer`,`disposition` | discontinuation | COMPLETED iff has a Day-21 biopsy | `ctgov: participantFlowModule` | COMPLETED "{FG000:15 … FG005:8}" = 76; NOT COMPLETED = 6 |

---

## DAG gates (Step-6 causality checks — must hold after every calibration update)

1. **g1 endpoint = trajectory** — `RE.dCAMP_*` reproducible as `SB.CAMP[D21] − SB.CAMP[BASE]`
   (agreement 1.0; the change is read off the trajectory, not drawn). Cf. invariant #1.
2. **g2 arm→25-OH-D mediation** — mean Δ25-OH-D(VITD) ≫ Δ25-OH-D(PLAC); the arm→Δexpression effect
   flows only through this mediator (no direct edge). Invariant #2.
3. **g3 within-patient AMP correlation** — ΔCAMP and ΔHBD-3 positively correlated within patient via
   `f_amp` (r > 0). The frailty mechanism (invariant #4 — don't zero shared frailties).
4. **g4 L₀ group→IgE direction** — baseline total IgE AD ≫ Non-AD and Pso (atopy signal; `PMC7307373`).
5. **g5 mediation separation** — VITD completers Δ25-OH-D above threshold, PLAC below (clean routing
   of the treatment path through the mediator).
6. **g6 AE↔DS traceability** — the single AD-Placebo AE-discontinued patient has exactly one
   `AEACN=DRUG WITHDRAWN` AE naming the cause, and vice-versa.
7. **g7 safety realism** — no calcium > 11 mg/dL (no hypercalcemia at 4000 IU) and 0 serious AEs
   (matches CTGov). Deterministic-rule grade is fixed; lab distribution is the knob (invariant #5).

## Evidence dossier — literature priors (paperclip)

| Edge | Source | Verbatim quote | Use |
|---|---|---|---|
| VitD3 4000 IU → ↑25-OH-D, no Ca change, ↓PTH | `paperclip: PMC506781 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC506781/` | "produced mean 25(OH)D levels of … 112 ± 41 nmol/L for the 100 mcg/day group. Both doses lowered plasma parathyroid hormone with no effect on plasma calcium." | mediator rise; PTH drop; Ca safety |
| VitD → ↑25-OH-D magnitude | `paperclip: PMC4148309 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4148309/` | "3000 IU of oral cholecalciferol daily … 25(OH)vitamin D … increased … (186% versus 14% [placebo]) … No change … in urinary calcium excretion" | rise magnitude / Ca safety |
| 1,25D3 → CAMP/HBD induction (keratinocyte) | `paperclip: PMC4206472 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4206472/` | _(excerpt)_ "…1,25(OH)2D3 … increased DEFB4 and CAMP gene expression and … production of HBD-2 and LL-37" | arm→Δexpression mechanism; f_amp (CAMP+HBD3) |
| VDR/MEK-ERK induction of cathelicidin | `paperclip: PMC2709447 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2709447/` | "vitamin D analogs induced cathelicidin through activation of the vitamin D receptor and MEK/ERK signaling" | VDR mechanism for the CAMP edge |
| Psoriasis ↑ / AD ↓ baseline cathelicidin | `paperclip: PMC3346901 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3346901/` | "In atopic dermatitis, cathelicidin induction might be disturbed … In contrast, psoriasis is characterized by overexpression of cathelicidin" | baseline biopsy level ordering |
| AD → ↑ total IgE | `paperclip: PMC7307373 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7307373/` | "Increased serum total IgE level … seen more frequently in AD patients than in non-AD patients (P < .05)" | L₀ dxgroup→IgE; f_th2 |
| VitD → TH2 (IL-4) modulation | `paperclip: PMC4425186 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4425186/` | "1,25(OH)2D inhibits IL-17 and IFN-γ, and induces T regulatory cells and IL-4" | IL-13/IL-4 edge direction (magnitude `model`, near-null per trial) |
| Age + central adiposity → ↓25-OH-D | `paperclip: PMC8838096 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8838096/` | "older age … higher waist/hip ratio … were independent correlates of lower serum calcidiol" | base_vitd_25oh parents (age, bmi) |
| Adiposity + pigmentation → ↓25-OH-D | `paperclip: PMC6616201 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6616201/` | "Major determinants of serum 25(OH)D … include sun exposure, skin reflectance, and adiposity" | base_vitd_25oh parent (fitzpatrick) |
| 4000 IU/day = tolerable upper level | `paperclip: PMC10407748 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10407748/` | "A UL of 100 μg vitamin D equivalents (VDE)/day is established for adults" | safety bound (g7); 0 serious AEs |

**Substitution note (honest sourcing):** the canonical primary sources for several edges — Vieth
*AJCN* 2001 (4000 IU), Ong *NEJM* 2002 (AD vs psoriasis cathelicidin), Liu *Science* 2006, Wang/Gombart
*JBC* 2004 (VDRE in *CAMP*) — are **not open-access** in the Paperclip PMC corpus and could not be
retrieved. Equivalent open-access papers grounding the *same* claim were substituted (above) and are
flagged as such. The IL-13-specific effect magnitude was not found in an OA source; only the TH2-axis
direction is grounded (`PMC4425186`), so the IL-13 effect size itself is tagged `model` and set
near-null consistent with the trial's own non-significant result. The `PMC4206472` evidence is shown
as an **excerpt** (ellipses) — it abridges non-contiguous clauses of the source's results text; the
co-induction of CAMP and HBD (the edge it supports) is preserved, but it is not a single contiguous
verbatim sentence.
