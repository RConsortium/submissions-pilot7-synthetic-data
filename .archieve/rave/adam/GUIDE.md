# ADaM derivation guide — RAVE (Rituximab vs Cyclophosphamide, ANCA vasculitis)

Derives the ADaM datasets from this environment's **generated SDTM**
(`../sdtm/sdtm-derived/xpt/*.xpt`) with [admiral](https://pharmaverse.github.io/admiral/).
Mirrors the cdiscpilot1 `adam/` stage.

## Prerequisite — build the SDTM first
```sh
cd ..                      # rave root
Rscript run.R --stage sdtm # edc -> sdtm-derived/xpt/*.xpt
```

## Run
```sh
cd adam
Rscript run_all.R          # -> adam-derived/<adam>.{rds,csv}
Rscript export_xpt.R       # -> adam-derived/_xpt/<adam>.xpt
```

## Datasets & dependency
```
ADSL                       ← runs first; reads DM + EX + DS (+ death from DM)
├── ADAE                   ← reads adsl.rds + AE   (OCCDS)
├── ADVS                   ← reads adsl.rds + VS   (BDS)
├── ADLB                   ← reads adsl.rds + LB   (BDS)
└── ADRS                   ← reads adsl.rds + RS   (BDS, efficacy)
```

| Dataset | Source SDTM | Notes |
|---------|-------------|-------|
| ADSL | DM, EX, DS | TRTSDT/TRTEDT/TRTDURD from EX; EOSSTT/EOSDT/DCSREAS from DS; DTHDT/DTHFL (death); SAFFL/ITTFL; groupings. Arms: Control (CYC) / Rituximab (RTX). |
| ADAE | AE, ADSL | OCCDS: TRTEMFL, ASEV/ASEVN, ASTDT/AENDT/ASTDY/AENDY, AOCC*FL, AESER/AREL. |
| ADVS | VS, ADSL | BDS: Weight; BASE/CHG. |
| ADLB | LB, ADSL | BDS across CHEMISTRY / HEMATOLOGY / URINALYSIS; PARCAT1 = LBCAT. |
| ADRS | RS, ADSL | BDS **efficacy**: BVAS/WG, remission status, flare, glucocorticoid-free, VDI. |

## Files
| File | Purpose |
|------|---------|
| `00_setup.R` | Paths, `read_sdtm/read_adam/save_adam`, ADaM labelling. |
| `ad_<dataset>.R` | One admiral derivation per ADaM. |
| `run_all.R` | Orchestrator — `00_setup.R` then each `ad_*.R` (ADSL first). |
| `export_xpt.R` | Renders `adam-derived/*.rds` → labelled XPT v5. |
