# ara06 — synthetic SDTM + ADaM + TLF (NCT00837434)

Synthetic individual-patient-data environment for **ARA06 / NCT00837434** — a
Phase IV, 2:1 randomized trial of **etanercept vs adalimumab** (both on background
methotrexate) in rheumatoid arthritis. A forward g-formula causal-DAG simulation
is turned into CDISC SDTM, ADaM, and TLF outputs through the four-stage layering
of the reference environment
`clinical-data-terminal-dev/src/cdt/environments/cdiscpilot1` (`edc → sdtm → adam → TLF`).

## Pipeline

```
edc/    ( python3 -m generators.build_all )   -> edc/forms/*.csv       raw CRF extract
sdtm/   Rscript sdtm/run_all.R                 -> sdtm-derived/*.csv    SDTM domains
sdtm/   python sdtm/export_conformant.py       -> sdtm-derived/xpt/*.xpt + define.xml
adam/   Rscript adam/run_all.R                  -> adam-derived/*.{rds,csv}  ADaM (admiral)
adam/   Rscript adam/export_xpt.R               -> adam-derived/_xpt/*.xpt
tlf/    Rscript tlf/run_all.R                   -> tlf-derived/<task>/*  tables/listings/figures
```

Or the whole thing via the orchestrator:

```bash
cd ara06
Rscript run.R                  # through ADaM
Rscript run.R --stage sdtm     # only through SDTM
Rscript run.R --stage tlf      # also render TLF outputs
```

The EDC generator reproduces the committed CRFs with its default config
(N=63, seed=2009); change `n_patients`/`seed` via a `GenConfig` in
`edc/generators/config.py`.

## How this differs from `cdiscpilot1`

`cdiscpilot1` *samples an EDC down* from a canonical SDTM truth and validates the
derivation with a **round-trip oracle**. ARA06 has **no SDTM truth**: it is
*simulated up* from a structural causal model (`edc/generators/sim/`), so the SDTM
derivations are themselves the ground-truth mapping (as in `cath`/`rave`). The
pipeline stops at derive → export (typed XPT + Define-XML) — there is no in-repo
CDISC-validation step.

## Layout

```
ara06/
├── run.R                    # orchestrates edc -> sdtm -> adam -> TLF
├── edc/                     # COLLECTION
│   ├── generators/          #   causal-DAG simulator (config.py, build_all.py, sim/)
│   ├── forms/               #   generated CRFs ARA06_CRF_*.csv
│   ├── lookups/             #   visit_schedule.csv (hand-curated)
│   └── metadata/            #   provenance: DAG.md, CRF_spec.md, intake/, params/
├── sdtm/                    # TABULATION
│   ├── common.R, derive_*.R, run_all.R, export_conformant.py
│   └── sdtm-derived/        #   *.csv + xpt/*.xpt + define.xml (generated)
├── adam/                    # ANALYSIS (admiral)
│   ├── 00_setup.R, ad_*.R, run_all.R, export_xpt.R, GUIDE.md
│   └── adam-derived/        #   *.{rds,csv} + _xpt/*.xpt (generated)
└── tlf/                     # REPORTING (one folder per output, like cdiscpilot1/tlf)
    ├── tlf_data.R, run_all.R, GUIDE.md
    ├── table-aet02/         #   task.json + data_setup.R + solve.R
    └── tlf-derived/<task>/  #   result1.{txt,rds} or .png (generated)
```

## SDTM domains

| Domain | Source CRF(s) | Notes |
|---|---|---|
| DM     | DM (+DS, EX) | RFENDTC from disposition day; RFXST/EN from study-drug EX |
| VS     | DM           | baseline WEIGHT (used for dosing) as one VS record |
| MH     | MH           | RA primary-diagnosis record |
| SUPPMH | MH           | RA duration (RADURYR) + RF/anti-CCP status (RFCCPPOS) |
| EX     | EX           | etanercept/adalimumab + background MTX dosing |
| AE     | AE           | MedDRA-coded; CTCAE grade, relationship, action, outcome |
| LB     | LB_HEM, LB_CHEM, BC | wide→long pivot; BC = switched-memory B-cell flow cytometry |
| RS     | DA           | DAS28-CRP composite + components (disease activity) |
| DS     | DS           | disposition event; study day → date vs RFSTDTC |

## ADaM datasets

| Dataset | Source | Notes |
|---------|--------|-------|
| ADSL | DM, EX, DS | treatment (TRTSDT/TRTEDT/TRTDURD), EOSSTT/EOSDT/DCSREAS, SAFFL/ITTFL, groupings |
| ADAE | AE, ADSL | OCCDS: TRTEMFL, ASEV/ASEVN, ASTDT/AENDT, occurrence flags |
| ADVS | VS, ADSL | BDS: baseline weight |
| ADLB | LB, ADSL | BDS: chemistry / hematology / flow-cytometry analytes |
| ADRS | RS, ADSL | BDS **efficacy**: DAS28-CRP, HAQ-DI, SJC28/TJC28, VAS, global assessments |

Derived with [admiral](https://pharmaverse.github.io/admiral/). See `adam/GUIDE.md`.

## TLF (tables, listings, figures)

Reporting outputs from the ADaM with `tern`/`rtables` and `ggplot2`, organized like
the `cdiscpilot1/tlf/` catalog (one `<task>/` folder with `task.json` +
`data_setup.R` + `solve.R`; `tlf/run_all.R` discovers and renders them). A
**starter kit** — one safety table is implemented; see `tlf/GUIDE.md` to add more.

| Task | Type | Output |
|------|------|--------|
| `table-aet02` | Safety table | Adverse Events by System Organ Class and Preferred Term (Treatment-Emergent, Safety Population), from ADAE |

## Dependencies

- Python ≥ 3.10: EDC simulator; SDTM XPT/Define-XML export (`pandas`, `pyreadstat`)
- R ≥ 4.0: `dplyr`, `tidyr`, `readr`, `stringr`, `admiral`, `haven`, `lubridate`;
  plus `tern`, `rtables`, `rlistings`, `ggplot2` for the TLF stage

## Reproduce / vary

```python
from cdt.environments.ara06 import generate_edc, generate_sdtm, GenConfig
generate_edc()                                       # committed CRFs (N=63, seed=2009)
generate_sdtm("/tmp/ara06", n_patients=120, seed=7)  # fresh cohort -> SDTM CSVs
```
