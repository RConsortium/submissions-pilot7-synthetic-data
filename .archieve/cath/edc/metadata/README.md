# CATH (NCT00789880 / ADVN CATH 03-01) — synthetic IPD run

Causal-DAG, g-formula simulation of individual patient data for the **ADVN CATH 03-01** substudy
(oral vitamin D3 4000 IU/day × 21 d vs placebo; change in skin antimicrobial-peptide / TH2-cytokine
mRNA expression in atopic dermatitis, psoriasis, and non-atopic controls). CRFs reproduce the
published marginal statistics **and** follow an explicit, literature-grounded causal DAG. Generated
by the `clinical-trial-ipd-sim` skill (non-oncology / continuous-endpoint path, after the RAVE build).

## 1. Contents

| Path | What's in it | Step |
|---|---|---|
| `intake/NCT00789880.json` | Raw ClinicalTrials.gov v2 API record (`hasResults: true`) | 1 |
| `intake/parsed_summary.md` | Parsed design / flow / baseline / endpoint + AE targets | 1 |
| `intake/targets.json` | **Machine-readable calibration targets** (baseline, outcomes, flow, AE) | 1 |
| `intake/protocol_extract.txt` | SoA + design facts from the user-provided protocol PDF | 1 |
| `intake/preconditions.json` | Protocol-gate attestation (status **formal**, PASS) | 1 |
| `CRF_spec.md` | Forms × visits × variables, anchored to the protocol SoA | 2 |
| `DAG.md` | Variable / parents / structural equation / cited evidence (ctgov·paperclip·model) | 3 |
| `params/params_final.json` | Final calibrated parameter snapshot (reproducibility) | 4·6 |
| `params/params_derivation.md` | Each parameter → value → source | 4 |
| `params/calibration_log.md` | What changed each iteration (audit trail) + invariants held | 6 |
| `crfs/CATH_CRF_*.csv` | **The deliverable** — 15 synthetic CRFs, 82 patients | 5·6 |
| `analysis/analysis.md` | Sim-vs-published tables, DAG-gate results, AE summary | 6 |
| `analysis/sim_vs_published.json` | Machine-readable metrics + gates | 6 |

Engine code lives **outside** this folder in [`cath/`](../cath/) (reused across runs);
`params/` + the RNG seed reproduce a run without copying code.

## 2. Manifest

| Field | Value |
|---|---|
| Trial / NCT | CATH / NCT00789880 (protocol ADVN CATH 03-01) |
| Protocol source | **ADVN CATH 03-01 v3.0 (July 7, 2009)**, user-provided PDF — `protocol_status: formal` (gate PASS) |
| Posted results | Yes (CTGov resultsSection, posted 2013-01-22) — calibration targets |
| Therapeutic area | Dermatology / innate immunity — **continuous biomarker-change endpoints** (no survival) |
| Patients (N) | **82** (6 cells: Non-AD/AD/Pso × VitD/Placebo = 16/16/8 + 16/18/8) |
| RNG seed | **88** (`python -m cath.cath_run 88`) |
| Engine | `cath/` (dag_state, baseline, longitudinal, outcomes, emit, run, params, metrics) |
| CRFs emitted | 15 forms (DM, IE, MH, DD, VS, SB, SA, TS, LB, MB, EX, AE, PG, DS, RE) |
| Generated | 2026-06-23 |
| Calibration iterations | 3 (see `params/calibration_log.md`) |
| **Status** | **PASS** — all 30 biomarker change cells within sampling tolerance; all 7 DAG gates pass |
| Population validation | scale ×60 (N=4920): all 30 change means within 0.5 of target (max 0.27), all SDs within 0.6 — calibration holds in expectation |

**Reproduce:** `python -m cath.cath_run 88` (uses `cath/params.py` defaults = `params_final.json`).
The seed matters — minor parameter changes shift RNG state. Verify: `python -m cath.metrics CATH_output/crfs`.

## 3. Targets vs. achieved (N=82, seed 88)

| Metric | Published (CTGov) | Simulated | Within tol |
|---|---|---|---|
| Pooled age (y) | 32.5 | 32.50 | ✅ |
| Pooled BMI (kg/m²) | 25.3 | 25.69 | ✅ |
| Baseline 25-OH-D (ng/mL) | 29.2 | 28.68 | ✅ |
| Female fraction | 0.537 | 0.561 | ✅ |
| Completers / dropouts | 76 / 6 | 76 / 6 | ✅ |
| Dropout reasons | AE 1 · PV 2 · WD 3 | AE 1 · PV 2 · WD 3 | ✅ |
| Serious AEs | 0 | 0 | ✅ |
| Biomarker change cells (CAMP/HBD-3/IL-13 × group × skin × arm) | 30 targets | 30/30 within 2 SE | ✅ |

### DAG gates (causal identifiability — all must pass)
✅ endpoint = trajectory (ΔCAMP agreement 1.000) · ✅ arm→25-OH-D mediation (+10.4 vs +0.3) ·
✅ within-patient AMP correlation (ΔCAMP–ΔHBD-3 r=+0.12) · ✅ L₀ group→IgE direction (AD 1115 ≫
NonAD 70 / Pso 82) · ✅ mediation separation · ✅ AE↔DS traceability (1=1) · ✅ safety (no
hypercalcemia, 0 serious AE).

> **Note on N=82 scatter.** At the true trial size each per-cell change mean scatters by ≈ SD/√n
> (n = 8–15) — the published trial is itself one N=82 draw, and its own primary contrasts were
> non-significant (e.g. CAMP AD-lesional p ≈ 0.7). Per-cell agreement is therefore checked within
> sampling tolerance (2 SE) at N=82 and convergence to the exact targets is demonstrated at
> population scale (×60). All arm→endpoint effects flow through the serum 25-OH-D mediator; change
> scores are derived from the biopsy trajectory, never drawn directly.
