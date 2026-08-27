# TLF guide — EIDD-2801-1001-UK

Tables, Listings, and Figures generated from this environment's derived ADaM
(`../adam/adam-derived/_xpt/`) with [tern](https://insightsengineering.github.io/tern/)
/ [rtables](https://insightsengineering.github.io/rtables/) (tables & listings)
and [ggplot2](https://ggplot2.tidyverse.org/) (figures).

Structured like the `cdiscpilot1/tlf/` catalog: one folder per output, each with
`task.json` + `data_setup.R` + `solve.R`; `run_all.R` discovers and runs them and
writes results to `tlf-derived/<task>/`.

This is a **starter kit** — one safety table (`table-vst01`) is implemented.

## Layout
```
TLF/
├── tlf_data.R            # read_adam() / adam_available() (reads adam-derived/_xpt)
├── run_all.R             # discovers <task>/ (those with task.json) and renders them
├── GUIDE.md
├── table-vst01/          # SAFETY table: Vital Signs + Change from Baseline by Visit
│   ├── task.json         #   metadata: inputs, output_type, expected_variables
│   ├── data_setup.R      #   preprocessing (read_adam + tern df_explicit_na)
│   └── solve.R           #   builds result1 (rtables layout + build_table)
└── tlf-derived/<task>/   # generated: result1.{rds,txt} (tables/listings) or .png (figures)
```

## Run
```sh
cd TLF
Rscript run_all.R                 # all tasks -> tlf-derived/<task>/
Rscript run_all.R table-vst01     # only the named task(s)
```
(Build the ADaM first: from the study root, `Rscript run.R`.)

## Add a new TLF (the convention)
1. Create a folder `TLF/<kind>-<id>/` — e.g. `table-lbt01`, `listing-vsl01`, `graph-vsg01`.
2. Add **`task.json`**:
   ```json
   {
     "task_id": "table-lbt01", "category": "tlf_derivation",
     "output_type": "table", "subject": "LBT01",
     "subtitle": "Laboratory Results by Visit", "population": "Safety",
     "inputs": { "cadsl.rds": "cadsl.rds", "cadlb.rds": "cadlb.rds" },
     "expected_variables": "result1"
   }
   ```
   `inputs` keys are legacy `cad<name>` ids resolved to our ADaM by `tlf_data.R`
   (`cadsl`→adsl, `cadvs`→advs, `cadeg`→adeg, `cadlb`→adlb). A task whose inputs
   are not generated is reported `BLOCKED`, not faked.
3. Add **`data_setup.R`** — load with `read_adam("adsl")` etc. (provided globally),
   preprocess (tern `df_explicit_na`, factors, filters).
4. Add **`solve.R`** — build the `rtables`/`rlistings` object or a `ggplot`, and
   assign it to the name(s) in `expected_variables` (e.g. `result1`).
5. `run_all.R` picks the folder up automatically (any dir with a `task.json`).

## Available ADaM
`adsl`, `advs`, `adeg`, `adlb`. Key BDS variables: `PARAMCD`, `PARAM`, `AVISIT`,
`AVISITN`, `AVAL`, `AVALC`, `BASE`, `CHG`, `PCHG`, `ABLFL`, `ASEQ`; treatment
`TRT01A`/`TRT01P`; population `SAFFL`/`ITTFL`. `AVISIT` values are the study visit
labels (`Day -1` … `Day 15/EOS`), ordered by `AVISITN`.

## Ideas for more tasks (safety / PK)
- `table-dmt01`  — demographic & baseline characteristics (ADSL).
- `table-egt01`  — ECG (heart rate + interpretation) summary by visit (ADEG).
- `table-lbt01`  — laboratory results & change from baseline by visit (ADLB).
- `listing-vsl01` — subject-level vital-signs listing (rlistings).
- `graph-vsg01`  — mean (± SE) vital sign over time by treatment (ggplot2).

> Single-dose Phase 1 PK study with no formal efficacy endpoint and no AE/CM/MH
> source, so the catalogue is safety/PK-oriented (no adverse-event tables).
