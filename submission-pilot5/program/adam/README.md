# Pilot 5 ADaM derivation programs (yamaa)

yamaa target specs that derive the five Pilot 5 ADaM datasets from the SDTM
parquets in `../data/sdtm/`. Every derivation lives in the YAML specs; the one
Python script stages an input (it derives no ADaM variable).

## End-to-end run

`run.py` executes the whole pipeline: it stages the SDTM parquets into a
`work/` directory, runs the specs in dependency order (derived ADSL/ADAE are
staged as predecessors where downstream specs need them), writes the five
derived datasets to `work/derived/`, and compares every derived column
against the official ADaM in `../data/adam/` (numeric cells within
`|derived - official| <= 1e-10`, non-numeric exact with null/"" normalized).

Requires the yamaa engine (`pip install` from
https://github.com/elong0527/yamaa), polars, and pyarrow.

    python3 run.py                          # everything, then compare
    python3 run.py --datasets adsl,adtte    # subset (predecessors auto-included)
    python3 run.py --no-compare            # derive only
    python3 run.py --work /tmp/p5          # custom work directory

`work/` is git-ignored build output; only the specs, scripts, and this README
are committed.

## Stage order (what run.py does)

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

## Verification

Cell-by-cell comparison of the derived datasets against the official ADaM
(`python3 run.py`, same tolerance as above):

- ADAE: all 52 derived columns match — 61,932/61,932 cells.
- ADTTE: all 26 derived columns match — 6,604/6,604 cells, zero diffs.
- ADADAS: 436,205/436,205 non-key cells match exactly; zero key mismatches.
- ADLBC: 1,708,072 cells within 1e-10 (1,692,639 exact; the remainder is
  machine-epsilon floating-point noise in derived laboratory values).
- ADSL: derived columns match except known documented gaps — the R program's
  1-digit rounding on dose/weight values (AVGDD, CUMDOSE, BMIBL, HEIGHTBL,
  WEIGHTBL; REQ-0418 deliberately keeps rounding out of derivations) and the
  codelist mapping skipped in the sketch (DCSREAS, EDUCLVL). 17 of the 49
  official columns are not derived by the spec.

Verified 2026-09-21, yamaa engine @ main.
