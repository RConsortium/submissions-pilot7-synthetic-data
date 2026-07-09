# ADaM derivation guide — ARA06 (Anti-TNF in Rheumatoid Arthritis)

Derives the ADaM datasets from this environment's **generated SDTM**
(`../sdtm/sdtm-derived/xpt/*.xpt`) with [admiral](https://pharmaverse.github.io/admiral/).
Mirrors the cdiscpilot1 `adam/` stage.

## Pipeline
```
../sdtm/sdtm-derived/xpt/*.xpt          (generated SDTM; build it first — see ../sdtm)
    │  run_all.R -> ad_<dataset>.R      (admiral derivations, ADSL first)
    ▼
adam-derived/<dataset>.{rds,csv}
    │  export_xpt.R                      (labelled SAS Transport v5, numeric dates)
    ▼
adam-derived/_xpt/<dataset>.xpt
```

## Prerequisite — build the SDTM first
```sh
cd ..                      # ara06 root
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
ADSL                       ← runs first; reads DM + EX + DS
├── ADAE                   ← reads adsl.rds + AE   (OCCDS)
├── ADVS                   ← reads adsl.rds + VS   (BDS)
├── ADLB                   ← reads adsl.rds + LB   (BDS)
└── ADRS                   ← reads adsl.rds + RS   (BDS, efficacy)
```

| Dataset | Source SDTM | Notes |
|---------|-------------|-------|
| ADSL | DM, EX, DS | TRTSDT/TRTEDT/TRTDURD from EX; EOSSTT/EOSDT/DCSREAS from DS; SAFFL/ITTFL; AGEGR1/RACEGR1/REGION1. |
| ADAE | AE, ADSL | OCCDS: TRTEMFL, ASEV/ASEVN, ASTDT/AENDT/ASTDY/AENDY, AOCC(S/P)FL occurrence flags, AESER/AREL. |
| ADVS | VS, ADSL | BDS: Weight (baseline). ABLFL from VSBLFL; BASE/CHG. |
| ADLB | LB, ADSL | BDS across chemistry / hematology / flow-cytometry analytes; PARCAT1 = LBCAT. |
| ADRS | RS, ADSL | BDS efficacy: DAS28-CRP, HAQ-DI, SJC28, TJC28, VAS, global assessments; BASE/CHG/PCHG. |

## Files
| File | Purpose |
|------|---------|
| `00_setup.R` | Paths (SDTM_DIR → `../sdtm/sdtm-derived/xpt`, ADAM_DIR → `adam-derived`), `read_sdtm/read_adam/save_adam`, ADaM labelling. |
| `ad_<dataset>.R` | One admiral derivation per ADaM. |
| `run_all.R` | Orchestrator — sources `00_setup.R` then each `ad_*.R` (ADSL first). |
| `export_xpt.R` | Renders `adam-derived/*.rds` → labelled XPT v5. |
