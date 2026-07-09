# Parameter derivation — CATH (NCT00789880)

Each parameter → value → derivation source. Per the skill citation format: `ctgov:` = read from
the ClinicalTrials.gov record, `paperclip:` = literature record, `model:` = sanity default.
Per-cell baseline and outcome means/SDs are **not** stored here — they are read live from
`intake/targets.json` (single source of truth) by `cath/params.py` and applied by the structural
equations in `DAG.md`. Snapshot of the tunable surface: `params_final.json`.

## Treatment mediator — serum 25-OH-D rise (drives the biopsy change)
| Param | Value | Source |
|---|---|---|
| `vitd_rise_mean` / `vitd_rise_sd` | 10.0 / 4.0 ng/mL | `paperclip: PMC506781` "112 ± 41 nmol/L for the 100 mcg/day [4000 IU] group" (≈ +40 nmol/L = +16 ng/mL plateau at months; ~+10 by 3 wk) + `PMC4148309` "186% versus 14%" |
| `plac_rise_mean` / `plac_rise_sd` | 0.3 / 2.0 | `model:` placebo ≈ flat over 21 d |
| `mediator_threshold` | 4.0 ng/mL | `model:` "did the supplement raise 25-OH-D" indicator (routes arm→Δexpression); ~93% VITD / ~0% PLAC exceed it |

## Safety serum panel at Day 21 (no hypercalcemia at 4000 IU)
| Param | Value | Source |
|---|---|---|
| `pth_vitd_drop` / `pth_day21_sd` | 2.0 / 4.0 pg/mL | `paperclip: PMC506781` "Both doses lowered plasma parathyroid hormone" |
| `ca_day21_sd` (clip Ca < 10.6) | 0.15 mg/dL | `paperclip: PMC506781`/`PMC4148309` "no effect on plasma calcium" |
| `creat_day21_sd` | 0.05 mg/dL | `model:` 21-day dosing, renal stable |

## Biopsy change submodel (the calibrated endpoint)
| Param | Value | Source |
|---|---|---|
| per-cell change mean/SD | **read from `targets.json:outcomes`** | `ctgov: outcomeMeasuresModule` — e.g. CAMP AD-lesional "VitD −0.4 (2.8) / Plac 0.1 (2.4)" |
| `f_amp_load` | 0.8 | `model:` shared cathelicidin+defensin frailty loading (CAMP, HBD-3); residual SD = √(cell_sd²−0.8²) |
| `f_th2_load` | 0.6 | `model:` TH2 frailty loading on IL-13 |
| `change_mean_scale` / `change_sd_scale` | 1.0 / 1.0 | calibration multipliers — **left at identity** (cell means/SDs reproduced directly, no tuning needed) |

## Baseline absolute biopsy levels (model; only the CHANGE is calibrated)
| Param | Value | Source |
|---|---|---|
| `base_level_offset` | 25.0 | `model:` keeps absolute expression ≫ change-noise SD so the physical floor (≥0.1) never clips the change distribution (**the single calibration adjustment — see calibration_log.md**) |
| `base_levels` (per group/skin/peptide) | psoriasis-lesional cathelicidin/HBD high; AD-lesional blunted; IL-13 high in AD-lesional | `paperclip: PMC3346901` "psoriasis is characterized by overexpression of cathelicidin … In atopic dermatitis, cathelicidin induction might be disturbed" |
| `base_level_cv` | 0.30 | `model:` baseline biological spread |

## Secondary skin readouts (model; non-calibrated — no posted target)
| Param | Value | Source |
|---|---|---|
| `saliva_camp_base` / `_cv` | 8.0 / 0.35 | `model:` (protocol §10.2 saliva cathelicidin) |
| `tape_camp_load` | 0.7 | `model:` tape-strip cathelicidin tracks biopsy CAMP (protocol §14.2.11 tape-vs-biopsy) |
| `cfu_base_log10` / `cfu_sd` / `cfu_lesional_bump` | 4.0 / 0.5 / 0.6 | `model:` bacterial colony counts (protocol §11.5) |
| `pasi_change_mean` / `_sd` | −0.6 / 2.0 | `model:` slight psoriasis improvement; no posted change |
| `ige_change_cv` | 0.10 | `ctgov` (IgE measured) + `model:` observed change non-significant → small |

## Adverse events (sparse — CTGov posted 0 serious, no PT ≥5%)
| Param | Value | Source |
|---|---|---|
| `ae_base_haz` (mild GI/headache PTs) | 0.04 | `paperclip: protocol §9.2.3` "most common complaints … constipation, gas, and bloating"; `ctgov` "no … 5% or greater frequency" |
| `ae_proc_haz` (skin reaction/erythema) | 0.03 | `paperclip: protocol §16` "a very mild erythema may develop … after a series of tape stripping" |

## Run configuration
| Param | Value | Source |
|---|---|---|
| cell sizes (started) | 16/16/8/16/18/8 | `ctgov: participantFlowModule STARTED` |
| dropouts (reason×cell) | AE 1 (AD-Plac); Protocol Violation 1 (AD-VitD), 1 (NonAD-Plac); Withdrawal 1 (NonAD-VitD), 2 (AD-Plac) | `ctgov: participantFlowModule dropWithdraws` |
| seed | 88 | representative N=82 draw (all gates pass, 30/30 cells, pooled age=32.5) |
