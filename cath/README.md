# cath — synthetic SDTM + ADaM + TLF (NCT00789880)

Synthetic individual-patient-data environment for **CATH / NCT00789880**
(ADVN CATH 03-01) — a randomized, double-blind trial of **oral vitamin D3
4000 IU/day vs placebo over 21 days**, in a 2×3 design (VitD/Placebo ×
Non-AD / Atopic-Dermatitis / Psoriasis), measuring skin antimicrobial-peptide
(cathelicidin) expression. A forward causal-DAG simulation is turned into CDISC
SDTM, ADaM, and TLF outputs through the four-stage layering of the reference
environment `clinical-data-terminal-dev/src/cdt/environments/cdiscpilot1`
(`edc → sdtm → adam → tlf`).

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
cd cath
Rscript run.R                  # through ADaM
Rscript run.R --stage sdtm     # only through SDTM
Rscript run.R --stage tlf      # also render TLF outputs
```

The EDC generator reproduces the committed CRFs with its default config
(N=82, seed=88); change `seed`/`scale` via a `GenConfig` in
`edc/generators/config.py`. Like `ara06`/`rave`, CATH is *simulated up* from a
structural causal model (no SDTM truth), so the SDTM derivations are the
ground-truth mapping and the pipeline stops at derive → export (typed XPT +
Define-XML) — there is no in-repo CDISC-validation step.

## Layout

```
cath/
├── run.R                    # orchestrates edc -> sdtm -> adam -> tlf
├── edc/                     # COLLECTION (causal-DAG simulator -> raw CRFs)
├── sdtm/                    # TABULATION  (common.R, derive_*.R, run_all.R, export_conformant.py)
│   └── sdtm-derived/        #   *.csv + xpt/*.xpt + define.xml (generated)
├── adam/                    # ANALYSIS (admiral: 00_setup.R, ad_*.R, run_all.R, export_xpt.R)
│   └── adam-derived/        #   *.{rds,csv} + _xpt/*.xpt (generated)
└── tlf/                     # REPORTING (one folder per output, like cdiscpilot1/tlf)
    ├── tlf_data.R, run_all.R, GUIDE.md
    ├── table-lbt01/         #   task.json + data_setup.R + solve.R
    └── tlf-derived/<task>/  #   result1.{txt,rds} or .png (generated)
```

## SDTM domains

| Domain | Source CRF(s) | Notes |
|---|---|---|
| DM       | DM (+DS, EX) | RFENDTC from disposition; RFXST/EN from EX |
| SUPPDM   | DM           | diagnostic stratum (DXGROUP) + Fitzpatrick skin type |
| VS       | VS (+DM)     | BP/pulse/temp/weight per visit; baseline height/BMI from DM |
| MH       | MH           | baseline diagnosis (healthy / AD / psoriasis) |
| SUPPMH   | MH           | atopy history |
| EX       | EX           | vitamin D3 / placebo, 21-day course |
| SUPPEX   | EX           | pill-count compliance (%) |
| AE       | AE           | sparse; MedDRA-coded |
| LB       | LB, SB, SA, TS | serum panel + skin-biopsy mRNA + saliva + tape-strip AMP, by `LBSPEC`/`LBLOC` |
| MB       | MB           | skin-surface bacterial load (log10 CFU) by compartment |
| RS       | DD           | PASI (psoriasis stratum only) |
| RP       | PG           | pregnancy test |
| DS       | DS           | disposition event |

## ADaM datasets

| Dataset | Source | Notes |
|---------|--------|-------|
| ADSL | DM, EX, DS | treatment (TRTSDT/TRTEDT/TRTDURD), EOSSTT/EOSDT/DCSREAS, SAFFL/ITTFL, groupings; arms Placebo / Vitamin D3 |
| ADAE | AE, ADSL | OCCDS: TRTEMFL, ASEV/ASEVN, ASTDT/ASTDY, occurrence flags (onset-only; no AEENDTC) |
| ADVS | VS, ADSL | BDS: SYSBP/DIABP/PULSE/TEMP/WEIGHT/HEIGHT/BMI |
| ADLB | LB, ADSL | BDS across CHEMISTRY / IMMUNOLOGY / GENE EXPRESSION / **ANTIMICROBIAL PEPTIDE** (cathelicidin) |
| ADRS | RS, ADSL | BDS **efficacy**: PASI |

Derived with [admiral](https://pharmaverse.github.io/admiral/). See `adam/GUIDE.md`.

## TLF (tables, listings, figures)

Reporting outputs from the ADaM with `tern`/`rtables` and `ggplot2`, organized like
the `cdiscpilot1/tlf/` catalog (one `<task>/` folder with `task.json` +
`data_setup.R` + `solve.R`; `tlf/run_all.R` discovers and renders them). A
**starter kit** — one efficacy table is implemented; see `tlf/GUIDE.md` to add more.

| Task | Type | Output |
|------|------|--------|
| `table-lbt01` | Efficacy table | Antimicrobial Peptide (Cathelicidin) — Value and Change from Baseline by Visit (ITT, primary endpoint), from ADLB |

## Dependencies

- Python ≥ 3.10: EDC simulator; SDTM XPT/Define-XML export (`pandas`, `pyreadstat`)
- R ≥ 4.0: `dplyr`, `tidyr`, `readr`, `stringr`, `admiral`, `haven`, `lubridate`;
  plus `tern`, `rtables`, `rlistings`, `ggplot2` for the TLF stage

## Reproduce / vary

```python
from cdt.environments.cath import generate_edc, generate_sdtm
generate_edc()                        # committed CRFs (N=82, seed=88)
generate_sdtm("/tmp/cath", seed=7)    # fresh cohort -> SDTM CSVs
```
