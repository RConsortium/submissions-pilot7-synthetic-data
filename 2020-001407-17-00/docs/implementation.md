# Implementation Notes — EIDD-2801-1001-UK Simulator

## Overview

The simulator is a faithful R port of two Python scripts, reorganized into the
layered structure of `cdiscpilot1_simulation`:

| Python source | R home |
|---------------|--------|
| `simulate_patient_cases.py` (generic CRF form-filler) | `simulator/sim_core.R` (+ constants in `sim_config.R`) |
| `cases_to_sdtm.py` (SDTM mapping) | `simulator/forms/sim_*.R` (one module per domain) |

The two stages are merged behind a single driver, `simulator/run_simulator.R`.

## Data flow

```
crf_json/*.json                      # 63 parsed eCRF templates (input)
        │  load_template()
        ▼
make_patient() ─► simulate_patient()  # generic engine fills every form
        │                             #   -> data/cases/<P###>/<form>.json  (ground truth)
        ▼
forms/sim_<domain>.R :: build_<domain>(patient, cases)   # per-domain SDTM mapping
        │
        ▼
rows_to_df() ─► write_domain()        # data/sdtm/<domain>.{csv,json}
```

`run_simulator()` samples each patient once, fills all CRF forms via the generic
engine, then dispatches the filled `cases` to every module listed in
`sdtm_domain_registry()`. Each module owns the SDTM mapping for one domain and
maintains its own chronological `--SEQ` counter per subject.

## Engine design (`sim_core.R`)

The CRF filler is **form-agnostic** — it is driven by field names and a
conditional cascade (`RowState`), so it is shared rather than per-domain:

- **Patient profile** — sex, childbearing potential, age, baseline/dose
  datetimes, study-fixed formulation + dose, race/ethnicity, eligibility.
- **Conditional cascade** — Yes/No parents drive "If No, Reason"; "Abnormal" →
  significance → comments; a not-taken dose blanks downstream dosing fields;
  pregnancy/FSH tests are skipped (with the correct N/A reason) for
  sex-incompatible subjects; I/E criteria are ticked only for ineligible ones.
- **Planned Time Point** — forms offering multiple timepoints are pinned to a
  single study-wide choice (`FORM_TP_CHOICE`), seeded once per run.
- **Value generators** — vitals/dosing keyword ranges, unit-aware generation,
  Yes/No biasing, exact-name lab reference ranges, and weighted qualitative
  urinalysis dipstick results.

## Two unit sets (important)

The form-filler and the SDTM mapper use **different** unit sets, mirroring the
two Python scripts:

- `UNIT_KEYWORDS` (filler) — substring match to *generate* a measured value
  from a unit. **Excludes `ms`**, so ECG interval fields (whose only template
  value is `"ms"`) are left as the literal token rather than fabricated.
- `UNIT_TOKENS` (mapper) — exact match to *suppress* cells that are only a unit.
  **Includes `ms`**, so those ECG interval cells become no observation row.

Net effect: ECG yields Heart Rate + Interpretation rows; PR/QRS/QT/RR/QTcF are
collection placeholders only and are dropped — matching the source data.

## Clinical reference ranges (`sim_config.R`)

- `LAB_NUMERIC_RANGES` — exact-CRF-name ranges for hematology analytes + BUN,
  checked *before* the loose keyword list so "Ery. Mean Corpuscular **Volume**"
  is not mistaken for a dosing volume.
- `URINALYSIS_VALUES` — weighted qualitative dipstick results (normal-biased).
- `NUMERIC_BY_FIELD_NAME` — vitals/dosing keyword ranges.

## Fidelity caveats

- **Demographics** are not captured on any CRF form. SEX/AGE/RACE/ETHNIC come
  from the sampled patient profile (the source of truth in this combined
  pipeline — no inference needed); the dosing record supplies reference dates
  and arm (dose level + formulation).
- **PC** rows are collection logs only — the CRF captures no assayed
  concentration, so `PCORRES` is blank.
- **LB specimen type** for chemistry/urinalysis is whatever the CRF recorded
  (the template offers Serum/Urine/Blood/Breath and is not constrained), so an
  occasional implausible `LBSPEC` is inherited from the source CRF, not a port
  artifact.
- **Reproducibility** is within R (`set.seed`). Bit-exact parity with the Python
  output is not a goal — R and Python use different RNGs — so row counts differ
  by a few percent (driven by Yes/No and abnormal-flag draws) while structure,
  value ranges, and SDTM conventions match.

## Reproducing / scaling

```bash
Rscript run.R --n 100 --seed 0     # default
Rscript run.R --n 500 --seed 7     # larger cohort
Rscript simulator/run_simulator.R  # direct (defaults), bypassing run.R
```
