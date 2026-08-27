# rave — synthetic SDTM + ADaM + TLF (NCT00104299)

Synthetic individual-patient-data environment for **RAVE / NCT00104299**
(ITN021AI) — a randomized, double-blind, double-dummy trial of **rituximab vs
cyclophosphamide→azathioprine** for remission induction in ANCA-associated
vasculitis (GPA/MPA), over 18 months (primary endpoint: complete remission at
month 6). A forward causal-DAG simulation is turned into CDISC SDTM, ADaM, and
TLF outputs through the four-stage layering of the reference environment
`clinical-data-terminal-dev/src/cdt/environments/cdiscpilot1` (`edc → sdtm → adam → tlf`).

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
cd rave
Rscript run.R                  # through ADaM
Rscript run.R --stage sdtm     # only through SDTM
Rscript run.R --stage tlf      # also render TLF outputs
```

The EDC generator reproduces the committed CRFs with its default config
(N=197, seed=123; RTX 95 / CYC 102); change `n_patients`/`seed` via a `GenConfig`
in `edc/generators/config.py`. Like `ara06`/`cath`, RAVE is *simulated up* from a
structural causal model (no SDTM truth), so the SDTM derivations are the
ground-truth mapping and the pipeline stops at derive → export (typed XPT +
Define-XML) — there is no in-repo CDISC-validation step.

## Layout

```
rave/
├── run.R                    # orchestrates edc -> sdtm -> adam -> tlf
├── edc/                     # COLLECTION (causal-DAG simulator -> raw CRFs)
├── sdtm/                    # TABULATION  (common.R, derive_*.R, run_all.R, export_conformant.py)
│   └── sdtm-derived/        #   *.csv + xpt/*.xpt + define.xml (generated)
├── adam/                    # ANALYSIS (admiral: 00_setup.R, ad_*.R, run_all.R, export_xpt.R)
│   └── adam-derived/        #   *.{rds,csv} + _xpt/*.xpt (generated)
└── tlf/                     # REPORTING (one folder per output, like cdiscpilot1/tlf)
    ├── tlf_data.R, run_all.R, GUIDE.md
    ├── table-rst01/         #   task.json + data_setup.R + solve.R
    └── tlf-derived/<task>/  #   result1.{txt,rds} or .png (generated)
```

## SDTM domains

| Domain | Source CRF(s) | Notes |
|---|---|---|
| DM       | DM (+DS, EX) | RFENDTC from disposition; RFXST/EN from active study drug; DTHDTC/DTHFL |
| VS       | DM           | baseline WEIGHT (used for mg/kg dosing) |
| MH       | DC           | AAV primary diagnosis (GPA / MPA) |
| SUPPMH   | DC           | ANCA type/status, new-vs-relapsing, renal involvement |
| EX       | EX, GC       | randomized study drug (RTX/CYC/AZA + placebos) + protocol prednisone taper |
| AE       | AE           | MedDRA-coded; includes lab-derived cytopenias |
| LB       | LB_HEM, LB_CHEM, LB_UA | hematology + chemistry + urinalysis, long pivot |
| RS       | DA, VDI      | BVAS/WG activity + remission/flare/GC-free status, Vasculitis Damage Index |
| DS       | DS           | disposition event |
| SUPPDS   | DS           | treatment crossover (flag + study day) |

## ADaM datasets

| Dataset | Source | Notes |
|---------|--------|-------|
| ADSL | DM, EX, DS | treatment (TRTSDT/TRTEDT/TRTDURD), EOSSTT/EOSDT/DCSREAS, DTHDT/DTHFL, SAFFL/ITTFL, groupings; arms Control (CYC) / Rituximab (RTX) |
| ADAE | AE, ADSL | OCCDS: TRTEMFL, ASEV/ASEVN, ASTDT/AENDT, occurrence flags |
| ADVS | VS, ADSL | BDS: weight |
| ADLB | LB, ADSL | BDS across CHEMISTRY / HEMATOLOGY / URINALYSIS |
| ADRS | RS, ADSL | BDS **efficacy**: BVAS/WG, remission status, flare, glucocorticoid-free, VDI |

Derived with [admiral](https://pharmaverse.github.io/admiral/). See `adam/GUIDE.md`.

## TLF (tables, listings, figures)

Reporting outputs from the ADaM with `tern`/`rtables` and `ggplot2`, organized like
the `cdiscpilot1/tlf/` catalog (one `<task>/` folder with `task.json` +
`data_setup.R` + `solve.R`; `tlf/run_all.R` discovers and renders them). A
**starter kit** — one efficacy table is implemented; see `tlf/GUIDE.md` to add more.

| Task | Type | Output |
|------|------|--------|
| `table-rst01` | Efficacy table | Birmingham Vasculitis Activity Score (BVAS/WG) by Visit (ITT, disease activity), from ADRS |

## Dependencies

- Python ≥ 3.10: EDC simulator; SDTM XPT/Define-XML export (`pandas`, `pyreadstat`)
- R ≥ 4.0: `dplyr`, `tidyr`, `readr`, `stringr`, `admiral`, `haven`, `lubridate`;
  plus `tern`, `rtables`, `rlistings`, `ggplot2` for the TLF stage

## Reproduce / vary

```python
from cdt.environments.rave import generate_edc, generate_sdtm
generate_edc()                        # committed CRFs (N=197, seed=123)
generate_sdtm("/tmp/rave", seed=7)    # fresh cohort -> SDTM CSVs
```
