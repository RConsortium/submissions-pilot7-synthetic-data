# ARA06 (NCT00837434) — Simulation vs Published Analysis

Final run: **N=63 (43 ETN + 20 ADA), seed 2009.** All 6 DAG gates pass;
**22/24** marginal metrics within tolerance (proportions ±0.12, memory-B mean
±2.0 %). The 2 near-misses are both on the 20-patient adalimumab arm (≈2 patients).

## Targets vs achieved

| Metric | Published | Simulated | Δ | Status |
|---|---|---|---|---|
| `mem_wk12_ETN_mean` | 13.200 | 12.889 | -0.311 | PASS |
| `mem_wk12_ADA_mean` | 13.800 | 12.378 | -1.422 | PASS |
| `das28resp_wk12_ETN` | 0.865 | 0.914 | +0.049 | PASS |
| `das28resp_wk12_ADA` | 0.895 | 0.833 | -0.062 | PASS |
| `das28resp_wk24_ETN` | 0.882 | 0.938 | +0.055 | PASS |
| `das28resp_wk24_ADA` | 0.842 | 0.833 | -0.009 | PASS |
| `acr20_wk12_ETN` | 0.676 | 0.771 | +0.095 | PASS |
| `acr20_wk12_ADA` | 0.737 | 0.778 | +0.041 | PASS |
| `acr20_wk24_ETN` | 0.735 | 0.750 | +0.015 | PASS |
| `acr20_wk24_ADA` | 0.842 | 0.778 | -0.064 | PASS |
| `acr50_wk12_ETN` | 0.297 | 0.400 | +0.103 | PASS |
| `acr50_wk12_ADA` | 0.474 | 0.500 | +0.026 | PASS |
| `acr50_wk24_ETN` | 0.382 | 0.500 | +0.118 | PASS |
| `acr50_wk24_ADA` | 0.632 | 0.500 | -0.132 | NEAR (−0.012 over tol; ≈2 ADA pts) |
| `anyae_ETN` | 0.795 | 0.884 | +0.089 | PASS |
| `anyae_ADA` | 0.895 | 0.750 | -0.145 | NEAR (−0.025 over tol; ≈2 ADA pts) |
| `sae_ETN` | 0.051 | 0.140 | +0.089 | PASS |
| `sae_ADA` | 0.053 | 0.000 | -0.053 | PASS |
| `anaemia_ETN` | 0.231 | 0.186 | -0.045 | PASS |
| `anaemia_ADA` | 0.158 | 0.150 | -0.008 | PASS |
| `ast_ETN` | 0.256 | 0.349 | +0.093 | PASS |
| `ast_ADA` | 0.158 | 0.050 | -0.108 | PASS |
| `noncomplete_ETN` | 0.209 | 0.279 | +0.070 | PASS |
| `noncomplete_ADA` | 0.050 | 0.100 | +0.050 | PASS |

(Memory-B SD: ETN 6.5, ADA 6.0 — vs published 7.3 / 7.2; structural expectation
at large N is 7.0–7.1.)

## DAG gates (all pass)

| Gate | Check | Result |
|---|---|---|
| g1 | AE↔lab linkage: mean AST at "AST increased" AE > ULN & > overall | AST@AE 47.2 > overall 28.0 ✅ |
| g2 | arm→hepatotoxicity: ETN AST-increased rate ≥ ADA (ctgov 25.6% vs 15.8%) | ETN 0.349 ≥ ADA 0.050 ✅ |
| g3 | within-patient AST↑/ALT↑ correlation > 0 (shared `f_hepatic`) | r = 0.349 ✅ |
| g4 | endpoints == trajectory (recompute mem & ACR20 from BC/DA) | agreement 1.000 / 1.000 ✅ |
| g5 | arm→deep response: ADA ACR50 ≥ ETN ACR50 (ctgov 47% vs 30%) | ADA 0.500 ≥ ETN 0.400 ✅ |
| g6 | AE↔DS traceability: AE-discontinuation set == DRUG-WITHDRAWN set | both empty (no AE-driven disc) ✅ |

## Interpretation

- **Primary endpoint faithfully null.** Switched-memory-B % at Week 12 is ~12–13%
  in both arms (published 13.2 / 13.8, p=0.3). This matches both the trial's
  negative result and the broader literature that anti-TNF does *not* reduce
  switched-memory B cells (paperclip PMC2714135) — a deliberate modeling choice,
  not a calibration failure.
- **Clinical efficacy ordering reproduced.** DAS28 good/moderate response (lenient,
  ~85–94%) > ACR20 (~75–78%) > ACR50, with adalimumab showing the deeper ACR50
  response seen in the trial (gate g5).
- **Safety signal is causally grounded.** Anaemia/AST AEs arise from CTCAE grading
  of the simulated CBC/LFT trajectories (gate g1), the etanercept hepatic excess is
  mediated by the lab process (gate g2), and AST/ALT co-elevate within patient via a
  shared hepatic frailty (gate g3) — all consistent with MTX±anti-TNF hepatotoxicity
  (PMC6186305) and MTX myelosuppression (PMC4851368).
- **Disposition is administrative**, exactly as published (physician decision,
  noncompliance, logistics, lost-to-follow-up — no adverse-event withdrawals),
  so the AE↔DS link set is correctly empty (gate g6).

## Reproduce

```bash
~/miniforge3/envs/keiji/bin/python -m ara06.ara06_run 63 2009          # → ARA06_output/crfs/
~/miniforge3/envs/keiji/bin/python -m ara06.metrics ARA06_output/crfs  # marginals + gates
```
