# ADaM derivation guide — EIDD-2801-1001-UK

Derives the ADaM datasets from this environment's **generated SDTM**
(`../sdtm/sdtm-derived/xpt/*.xpt`) with [admiral](https://pharmaverse.github.io/admiral/).
Mirrors the cdiscpilot1 `adam/` stage; only the inputs (and the reduced
dataset set for a single-dose Phase 1 study with no AE/DS/CM/MH) differ.

## Pipeline
```
../sdtm/sdtm-derived/xpt/*.xpt          (generated SDTM; build it first — see ../sdtm)
    │  run_all.R -> ad_<dataset>.R      (admiral derivations, ADSL first)
    ▼
adam-derived/<dataset>.{rds,csv}
    │  export_xpt.R                      (labelled SAS Transport v5, numeric dates/times)
    ▼
adam-derived/_xpt/<dataset>.xpt
```

## Prerequisite — build the SDTM first
```sh
cd ..                      # EIDD-2801 root
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
ADSL                       ← runs first; reads DM + EX
├── ADVS                   ← reads adsl.rds + VS
├── ADEG                   ← reads adsl.rds + EG
└── ADLB                   ← reads adsl.rds + LB
```

| Dataset | Source SDTM | Notes |
|---------|-------------|-------|
| ADSL | DM, EX | TRTSDTM/TRTEDTM/TRTDURD from EX; SAFFL/ITTFL; AGEGR1/RACEGR1/REGION1. No DS/AE → no disposition or death variables. |
| ADVS | VS, ADSL | BDS: SYSBP/DIABP/PULSE/RESP/TEMP; ADT/ADY, BASE/CHG/PCHG, ABLFL, ASEQ. |
| ADEG | EG, ADSL | BDS: EGHR (numeric AVAL) + INTP (AVALC). |
| ADLB | LB, ADSL | BDS across all lab analytes; PARCAT1 = LBCAT; numeric AVAL / qualitative AVALC. |

No ADPC: the PC domain is a biospecimen-collection log with no assayed
concentrations, so there is nothing to analyze.

## Files
| File | Purpose |
|------|---------|
| `00_setup.R` | Paths (SDTM_DIR → `../sdtm/sdtm-derived/xpt`, ADAM_DIR → `adam-derived`), `read_sdtm/read_adam/save_adam`, ADaM labelling. |
| `ad_<dataset>.R` | One admiral derivation per ADaM. |
| `run_all.R` | Orchestrator — sources `00_setup.R` then each `ad_*.R` (ADSL first). |
| `export_xpt.R` | Renders `adam-derived/*.rds` → labelled XPT v5 (Date/POSIXct/hms → numeric SAS dates/times). |
