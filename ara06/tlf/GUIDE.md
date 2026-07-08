# TLF guide — ARA06 (Anti-TNF in Rheumatoid Arthritis)

Tables, Listings, and Figures generated from this environment's derived ADaM
(`../adam/adam-derived/_xpt/`) with [tern](https://insightsengineering.github.io/tern/)
/ [rtables](https://insightsengineering.github.io/rtables/) (tables & listings)
and [ggplot2](https://ggplot2.tidyverse.org/) (figures).

Structured like the `cdiscpilot1/tlf/` catalog: one folder per output, each with
`task.json` + `data_setup.R` + `solve.R`; `run_all.R` discovers and runs them and
writes results to `tlf-derived/<task>/`.

This is a **starter kit** — one safety table (`table-aet02`) is implemented.

## Layout
```
tlf/
├── tlf_data.R            # read_adam() / adam_available() (reads adam-derived/_xpt)
├── run_all.R             # discovers <task>/ (those with task.json) and renders them
├── GUIDE.md
├── table-aet02/          # SAFETY table: Adverse Events by SOC and Preferred Term
│   ├── task.json         #   metadata: inputs, output_type, expected_variables
│   ├── data_setup.R      #   preprocessing (read_adam + tern df_explicit_na)
│   └── solve.R           #   builds result1 (rtables AE occurrence table)
└── tlf-derived/<task>/   # generated: result1.{rds,txt} or .png
```

## Run
```sh
cd tlf
Rscript run_all.R                 # all tasks -> tlf-derived/<task>/
Rscript run_all.R table-aet02     # only the named task(s)
```
(Build the ADaM first: from the study root, `Rscript run.R`.)

## Add a new TLF (the convention)
1. Create a folder `tlf/<kind>-<id>/` — e.g. `table-rst01`, `listing-ael01`, `graph-rsg01`.
2. Add **`task.json`** (`inputs` keys are legacy `cad<name>` ids resolved by
   `tlf_data.R`: `cadsl`→adsl, `cadae`→adae, `cadvs`→advs, `cadlb`→adlb, `cadrs`→adrs).
3. Add **`data_setup.R`** — load with `read_adam("adsl")` etc., preprocess.
4. Add **`solve.R`** — build the `rtables`/`rlistings` object or a `ggplot`, and
   assign it to the name(s) in `expected_variables` (e.g. `result1`).
5. `run_all.R` picks the folder up automatically.

## Available ADaM
`adsl`, `adae`, `advs`, `adlb`, `adrs`. Key vars: OCCDS `adae` has `TRTEMFL`,
`AEBODSYS`, `AEDECOD`, `ASEV/ASEVN`, `AESER`, `AOCC*FL`; BDS (`advs`/`adlb`/`adrs`)
have `PARAMCD`, `PARAM`, `AVISIT`, `AVISITN`, `AVAL`, `AVALC`, `BASE`, `CHG`,
`PCHG`, `ABLFL`; treatment `TRT01A`/`TRT01P`; population `SAFFL`/`ITTFL`.

## Ideas for more tasks (safety / efficacy)
- `table-dmt01` — demographic & baseline characteristics (ADSL).
- `table-aet01` — overview of adverse events (any AE / serious / by severity).
- `table-rst01` — DAS28-CRP change from baseline by visit (ADRS, **efficacy**).
- `table-lbt01` — laboratory results & change from baseline by visit (ADLB).
- `graph-rsg01` — mean disease-activity trajectory by treatment (ADRS, ggplot2).
