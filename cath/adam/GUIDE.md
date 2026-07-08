# ADaM derivation guide — CATH (Vitamin D3 vs Placebo, skin AMP study)

Derives the ADaM datasets from this environment's **generated SDTM**
(`../sdtm/sdtm-derived/xpt/*.xpt`) with [admiral](https://pharmaverse.github.io/admiral/).
Mirrors the cdiscpilot1 `adam/` stage.

## Prerequisite — build the SDTM first
```sh
cd ..                      # cath root
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
├── ADAE                   ← reads adsl.rds + AE   (OCCDS; onset-only, no AEENDTC)
├── ADVS                   ← reads adsl.rds + VS   (BDS)
├── ADLB                   ← reads adsl.rds + LB   (BDS; incl. antimicrobial peptide)
└── ADRS                   ← reads adsl.rds + RS   (BDS, efficacy: PASI)
```

| Dataset | Source SDTM | Notes |
|---------|-------------|-------|
| ADSL | DM, EX, DS | TRTSDT/TRTEDT/TRTDURD from EX; EOSSTT/EOSDT/DCSREAS from DS; SAFFL/ITTFL; groupings. Arms: Placebo / Vitamin D3. |
| ADAE | AE, ADSL | OCCDS: TRTEMFL, ASEV/ASEVN, ASTDT/ASTDY, AOCC*FL. CATH AE has onset only (no AEENDTC). |
| ADVS | VS, ADSL | BDS: SYSBP/DIABP/PULSE/TEMP/WEIGHT/HEIGHT/BMI; BASE/CHG/PCHG. |
| ADLB | LB, ADSL | BDS across CHEMISTRY / IMMUNOLOGY / GENE EXPRESSION / **ANTIMICROBIAL PEPTIDE** (cathelicidin, primary biomarker); PARCAT1 = LBCAT. |
| ADRS | RS, ADSL | BDS **efficacy**: PASI (Psoriasis Area and Severity Index). |

## Files
| File | Purpose |
|------|---------|
| `00_setup.R` | Paths, `read_sdtm/read_adam/save_adam`, ADaM labelling. |
| `ad_<dataset>.R` | One admiral derivation per ADaM. |
| `run_all.R` | Orchestrator — `00_setup.R` then each `ad_*.R` (ADSL first). |
| `export_xpt.R` | Renders `adam-derived/*.rds` → labelled XPT v5. |
