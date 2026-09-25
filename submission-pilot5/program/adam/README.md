# Pilot 5 ADaM derivation programs (yamaa)

yamaa target specs that derive the five Pilot 5 ADaM datasets from the SDTM
parquets in `../data/sdtm/`. Every derivation lives in the YAML specs; the one
Python script stages an input (it derives no ADaM variable).

## Run order

Specs read inputs relative to the directory they are run from, so run each
from this directory with the yamaa engine (e.g. `yamaa run <spec>`):

1. `adsl.yaml` — from SDTM DM/EX/VS/DS/SC/MH/SV/QS. Output: ADSL.
2. `adae.yaml` — from SDTM AE plus the derived ADSL staged as `adsl.parquet`.
   Output: ADAE.
3. `adadas-obs.yaml` → `adadas-actot.yaml` → `adadas-locf.yaml` — observation
   stage from SDTM QS plus derived ADSL, then a slim ACTOT lookup relation,
   then the LOCF completion stage. Output: ADADAS (`adadas-out.parquet`).
4. `adtte.yaml` — from derived ADSL, derived ADAE, and SDTM DS. Output: ADTTE.
5. ADLBC, staged then derived:
   - `python3 stage-adlbc-lb.py` — stages `adlbc-lb.parquet` from SDTM
     LB + SUPPLB (input prep only: pivots the ENDPOINT supplement, keeps
     CHEMISTRY records; no ADaM variable is derived).
   - `adlbc-eot-rn.yaml` → `adlbc-eot.yaml` — rank and filter the End-of-
     Treatment fallback candidates (`adlbc-eot.parquet`).
   - `adlbc.yaml` — from `adlbc-lb.parquet`, derived ADSL, and
     `adlbc-eot.parquet`. Output: ADLBC (`adlbc-out.parquet`).

## Verification (2026-09-21, yamaa engine @ main)

Cell-by-cell comparison of each derived dataset against the official ADaM in
`../data/adam/`, numeric cells within `|derived - official| <= 1e-10`:

- ADSL: 12,446/12,446 cells pass
- ADAE: 65,505/65,505 cells pass
- ADADAS: 498,520/498,520 cells pass
- ADTTE: 6,604/6,604 cells pass
- ADLBC: 1,708,072/1,708,072 cells pass
