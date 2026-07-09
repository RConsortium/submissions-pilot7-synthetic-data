# Implementation notes — EIDD-2801-1001-UK

## Overview

The environment produces SDTM + ADaM in three stages, mirroring
`cdiscpilot1` (`edc/ → sdtm/ → adam/`), driven by a single orchestrator (`run.R`).

| Stage | Where | Output |
|-------|-------|--------|
| Collection — fill every eCRF per subject | `edc/generators/` (`build_all.R` + `sim_core.R`/`sim_config.R`) | `edc/forms/*.csv`, `edc/forms/subjects.csv`, `edc/lookups/visit_schedule.csv` |
| Tabulation — raw forms → SDTM | `sdtm/derive_*.R` (+ `common.R`) | `sdtm/sdtm-derived/*.csv` → `xpt/*.xpt` + `define.xml` |
| Analysis — SDTM → ADaM (admiral) | `adam/ad_*.R` (+ `00_setup.R`) | `adam/adam-derived/*.{rds,csv}` → `_xpt/*.xpt` |

## Data flow

```
edc/crf_json/*.json                         63 parsed eCRF templates (spec)
        │  load_template()  (sim_core.R)
        ▼
make_patient() ─► simulate_patient()         generic form-filler fills every form
        │  build_all.R  (union of CRF fields per form category)
        ▼
edc/forms/<form>.csv  +  subjects.csv        RAW EDC extract (collection layer)
        │  sdtm/derive_<domain>.R            (read_form + common.R helpers)
        ▼
sdtm/sdtm-derived/<domain>.csv               SDTM tabulations
        │  sdtm/export_conformant.py         (cdt.environments.sdtm_export)
        ▼
sdtm/sdtm-derived/xpt/*.xpt + define.xml     conformant SAS Transport + Define-XML
        │  adam/ad_<dataset>.R               (admiral; ADSL first)
        ▼
adam/adam-derived/<dataset>.{rds,csv}        ADaM analysis datasets
        │  adam/export_xpt.R
        ▼
adam/adam-derived/_xpt/*.xpt                 labelled ADaM SAS Transport
```

## Reformulation notes

- The study previously used a single-shot R simulator (`simulator/run_simulator.R`)
  that mapped filled CRF cases straight to SDTM in `data/sdtm/`. That logic was
  re-split to match the reference layout:
  - The generic CRF form-filler moved to `edc/generators/` and now writes the
    **raw** filled forms (one CSV per CRF form category) rather than SDTM.
  - The per-domain SDTM mappings (`simulator/forms/sim_*.R`) became
    `sdtm/derive_*.R`, reading `edc/forms/*.csv` instead of in-memory case lists.
- No canonical SDTM truth exists (forward-simulated), so — like `ara06`/`cath`/
  `rave` — there is no round-trip oracle. The derivations are the ground-truth
  mapping; the SDTM stage output is the conformant XPT + Define-XML.

## Fidelity caveats

- **PC** captures biospecimen collection only (no assayed concentration), so
  `PCORRES` is blank and there is no ADPC.
- **IE** records only criteria flagged as not met; an all-eligible seed yields an
  empty IE domain (dropped from the output).
- **EG** interval parameters recorded only as the unit token `ms` carry no value
  and are dropped, leaving Heart Rate (numeric) + Interpretation (text).
- The study has no AE/CM/MH/DS collection, so those SDTM/ADaM domains are absent;
  ADSL therefore carries treatment + population + demographic groupings only.
