# Analysis — CATH (NCT00789880) synthetic IPD vs. published

Step-6 output. Simulated CRFs (N=82, seed 88) vs. the posted ClinicalTrials.gov results
(`intake/targets.json`). Machine-readable copy: `sim_vs_published.json`.

**Status: PASS** — all 30 biomarker change cells within sampling tolerance (2 SE) at N=82;
all per-cell means converge to target at population scale (×60, max |Δ| 0.27); **all 7 DAG
gates pass**; 0 serious AEs; participant flow reproduced exactly (76 completers / 6 dropouts).

## 1. Baseline characteristics (pooled, N=82)

| Metric | Published (CTGov total) | Simulated | OK |
|---|---|---|---|
| Age, mean (y) | 32.5 | 32.50 | ✅ |
| BMI, mean (kg/m²) | 25.3 | 25.69 | ✅ |
| Serum 25-OH-D, mean (ng/mL) | 29.2 | 28.68 | ✅ |
| Serum calcium, mean (mg/dL) | 9.4 | 9.36 | ✅ |
| Female fraction | 0.537 (44/82) | 0.561 | ✅ |

Per-cell baseline means (age/BMI/25-OH-D/PTH/Ca/IgE) and the AD-driven IgE elevation are
reproduced by construction (drawn from the per-cell CTGov moments); see `sim_vs_published.json`.

## 2. Participant flow

| | Published | Simulated |
|---|---|---|
| Enrolled / started | 82 | 82 |
| Completed | 76 | 76 |
| Discontinued | 6 | 6 |
| └ Adverse Event | 1 (AD-Placebo) | 1 (AD-Placebo) |
| └ Protocol Violation | 2 (AD-VitD, NonAD-Placebo) | 2 |
| └ Withdrawal by Subject | 3 (NonAD-VitD, AD-Placebo×2) | 3 |

## 3. Primary/secondary endpoints — change baseline→Day 21 (mean ± SD)

Per peptide × diagnostic group × skin compartment × arm; completers only (AD/NonAD n=15, Pso n=8).
"Pub" = CTGov `outcomeMeasuresModule`. Tolerance = 2·SE (sampling) or 0.6 abs, whichever larger.

<!-- BEGIN CELLS TABLE -->
| Peptide·Group·Skin·Arm | n | Pub mean (SD) | Sim mean (SD) | |Δ| | 2·SE tol | ✓ |
|---|---|---|---|---|---|---|
| CAMP NonAD·NonLesional·VitD | 15 | 1.2 (2.4) | 0.68 (1.64) | 0.52 | 1.24 | ✅ |
| CAMP NonAD·NonLesional·Plac | 15 | 0.3 (1.7) | 0.59 (2.55) | 0.29 | 0.88 | ✅ |
| CAMP AD·Lesional·VitD | 15 | -0.4 (2.8) | 0.52 (3.05) | 0.92 | 1.45 | ✅ |
| CAMP AD·Lesional·Plac | 15 | 0.1 (2.4) | 0.45 (2.99) | 0.35 | 1.24 | ✅ |
| CAMP AD·NonLesional·VitD | 15 | -0.6 (2.0) | -0.19 (1.88) | 0.41 | 1.03 | ✅ |
| CAMP AD·NonLesional·Plac | 15 | 0.7 (2.5) | -0.11 (2.35) | 0.81 | 1.29 | ✅ |
| CAMP Pso·Lesional·VitD | 8 | -0.9 (3.0) | 0.44 (2.42) | 1.34 | 2.12 | ✅ |
| CAMP Pso·Lesional·Plac | 8 | 0.2 (3.2) | 0.90 (4.32) | 0.70 | 2.26 | ✅ |
| CAMP Pso·NonLesional·VitD | 8 | -0.6 (2.3) | 0.23 (2.33) | 0.83 | 1.63 | ✅ |
| CAMP Pso·NonLesional·Plac | 8 | 0.7 (2.4) | 1.19 (1.20) | 0.49 | 1.70 | ✅ |
| HBD3 NonAD·NonLesional·VitD | 15 | 0.2 (2.8) | -0.17 (2.11) | 0.37 | 1.45 | ✅ |
| HBD3 NonAD·NonLesional·Plac | 15 | 1.2 (3.2) | 1.53 (3.64) | 0.33 | 1.65 | ✅ |
| HBD3 AD·Lesional·VitD | 15 | -0.1 (7.3) | -1.72 (8.55) | 1.62 | 3.77 | ✅ |
| HBD3 AD·Lesional·Plac | 15 | -0.8 (2.8) | -0.38 (3.01) | 0.42 | 1.45 | ✅ |
| HBD3 AD·NonLesional·VitD | 15 | -0.1 (3.5) | 0.52 (3.29) | 0.62 | 1.81 | ✅ |
| HBD3 AD·NonLesional·Plac | 15 | 1.4 (3.9) | -0.03 (4.44) | 1.43 | 2.01 | ✅ |
| HBD3 Pso·Lesional·VitD | 8 | 0.8 (5.3) | -0.74 (5.11) | 1.54 | 3.75 | ✅ |
| HBD3 Pso·Lesional·Plac | 8 | -1.6 (4.4) | -2.15 (4.33) | 0.55 | 3.11 | ✅ |
| HBD3 Pso·NonLesional·VitD | 8 | -1.5 (3.2) | -0.80 (3.59) | 0.70 | 2.26 | ✅ |
| HBD3 Pso·NonLesional·Plac | 8 | -1.5 (4.3) | -3.21 (4.26) | 1.71 | 3.04 | ✅ |
| IL13 NonAD·NonLesional·VitD | 15 | 0.2 (2.4) | -0.11 (2.99) | 0.31 | 1.24 | ✅ |
| IL13 NonAD·NonLesional·Plac | 15 | 0.5 (1.5) | 0.70 (1.00) | 0.20 | 0.77 | ✅ |
| IL13 AD·Lesional·VitD | 15 | -0.7 (2.8) | 0.35 (3.60) | 1.05 | 1.45 | ✅ |
| IL13 AD·Lesional·Plac | 15 | 1.1 (2.7) | 1.45 (3.02) | 0.35 | 1.39 | ✅ |
| IL13 AD·NonLesional·VitD | 15 | -0.8 (2.3) | -1.38 (2.29) | 0.58 | 1.19 | ✅ |
| IL13 AD·NonLesional·Plac | 15 | -0.1 (3.2) | -1.03 (2.74) | 0.93 | 1.65 | ✅ |
| IL13 Pso·Lesional·VitD | 8 | -2.1 (4.6) | -2.80 (3.91) | 0.70 | 3.25 | ✅ |
| IL13 Pso·Lesional·Plac | 8 | -0.1 (4.1) | 2.35 (4.54) | 2.45 | 2.90 | ✅ |
| IL13 Pso·NonLesional·VitD | 8 | -0.3 (2.7) | 1.43 (2.38) | 1.73 | 1.91 | ✅ |
| IL13 Pso·NonLesional·Plac | 8 | 0.9 (3.3) | 1.43 (4.02) | 0.53 | 2.33 | ✅ |
<!-- END CELLS TABLE -->

**30/30 within tolerance.** The point estimates are small and noisy with overlapping arms — faithful
to the trial's own null result (e.g. CAMP AD-lesional published p ≈ 0.7). Larger |Δ| values are
confined to the small (n=8) psoriasis cells and the high-variance HBD-3 AD-lesional cell (SD 7.3),
exactly where sampling scatter is largest.

### Population validation (convergence in expectation, scale ×60, N=4920)
All 30 cells |sim − target| < 0.5 (max 0.27) **and** all 30 SDs within 0.6 of target; gates pass.
Confirms the calibration is correct in expectation — the N=82 scatter above is sampling, not bias.

## 4. Adverse events
Published: **0 serious AEs, 0 deaths, no PT at ≥5% frequency.** Simulated: **0 serious AEs**;
13 sporadic mild (grade-1, non-serious) events across 82 patients (vitamin-D GI complaints +
biopsy/tape procedure reactions) — none reaching a 5% per-group threshold. The single AD-Placebo
AE-discontinuation carries `AEACN=DRUG WITHDRAWN`.

## 5. DAG gates (causal identifiability — all must pass)

| Gate | Check | Result | Pass |
|---|---|---|---|
| g1 | endpoint = trajectory (ΔCAMP = SB[D21] − SB[BASE]) | agreement 1.000 (n=122) | ✅ |
| g2 | arm → 25-OH-D mediation | Δ25-OH-D VitD +10.4 vs Plac +0.3 | ✅ |
| g3 | within-patient AMP correlation (ΔCAMP vs ΔHBD-3) | r = +0.12 (>0) | ✅ |
| g4 | L₀ group→IgE direction (AD ≫ NonAD/Pso) | AD 1115 vs NonAD 70 / Pso 82 | ✅ |
| g5 | mediation separation (VitD>thr>Plac) | VitD +10.4 / Plac +0.3 | ✅ |
| g6 | AE↔DS traceability (1 AE-dropout ↔ 1 DRUG WITHDRAWN) | 1 = 1, no missing | ✅ |
| g7 | safety realism (no hypercalcemia; 0 serious AE) | max Ca 10.2 (<11); serious AE = 0 | ✅ |

All arm→endpoint effects flow through the serum 25-OH-D mediator; the change scores are read off the
biopsy trajectory, never drawn directly. The loop never broke a gate to chase a marginal.

## Reproduce
```
python -m cath.cath_run 88            # → CATH_output/crfs/CATH_CRF_*.csv
python -m cath.metrics CATH_output/crfs
```
