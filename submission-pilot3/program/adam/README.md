# Pilot 3 ADaM derivation programs (yamaa)

yamaa target specs that regenerate the five Pilot 3 ADaM datasets from the
SDTM parquets in `../data/sdtm/`. Every derivation lives in the YAML specs
(plus the hand-built planning relations in `inputs/`, which mirror the R
program's tribbles); `run.py` only stages inputs, runs the specs, and
verifies the results.

## End-to-end run

From a fresh clone:

    cd submission-pilot3/program/adam
    pip install -r requirements.txt
    python3 run.py

`run.py` stages the SDTM parquets and the planning inputs into a `work/`
directory, runs the specs in dependency order (derived ADSL/ADAE are staged
as predecessors where downstream specs need them), writes the five derived
datasets to `work/derived/`, and compares every cell against the official
ADaM in `../data/adam/` (numeric cells within `|derived - official| <=
1e-10`, non-numeric exact with null/`""` normalized).

    python3 run.py --datasets adsl,adtte   # subset (predecessors auto-included)
    python3 run.py --no-compare            # derive only
    python3 run.py --work /tmp/p3          # custom work directory

`work/` is git-ignored build output; only the specs, inputs, scripts,
requirements, and this README are committed.

## Stage order (what run.py does)

1. `adsl_exdose.yaml` — per-record exposure staging (REQ-0483): one row per
   EX record with the imputed/capped exposure end date and per-record dose.
2. `adsl.yaml` — from SDTM DM/DS/EX/QS/SV/VS/SC/MH plus the exdose staging.
   Output: ADSL.
3. `adae.yaml` — from SDTM AE plus the derived ADSL. Output: ADAE.
4. `adadas.yaml` — from SDTM QS (plus a `QSDTC_D` date column parsed from
   `QSDTC` at staging time, since the planner's static gate currently rejects
   ISO date text for `to_date`, REQ-0607/REQ-1107), the derived ADSL, the
   222-row LOCF planning relation (`inputs/plan.csv`), and the 4-row
   analysis-window lookup (`inputs/aw_lookup.csv`). Output: ADADAS.
5. `adtte.yaml` — from derived ADSL, derived ADAE, and SDTM DS. Output:
   ADTTE.
6. `adlbc.yaml` — from SDTM LB/SUPPLB plus the derived ADSL. Output: ADLBC.

## Notes

- `requirements.txt` pins the yamaa engine (editable install) to the merge
  commit of elong0527/yamaa PR #759, which carries the engine fixes the
  specs rely on (intermediate match hash index, window group_by through the
  readable row view, stable column dependency order). The editable install
  is required so the engine finds its schema bundle (`yaml/schema.yaml`,
  which lives at the yamaa repo root outside the Python package).
- The planning relations under `inputs/` are committed as CSV (the repo's
  structure check only allows `.parquet` under `data/`); `run.py` stages
  them as parquets with pinned dtypes, and builds the ADADAS QS input
  (`QSDTC` plus a `QSDTC_D` date column — all staged `QSDTC` values are
  clean ISO dates) at staging time. The staged parquets are byte-identical
  to the inputs the specs were verified against.

## Verification

Cell-by-cell comparison of the derived datasets against the official ADaM
(`python3 run.py`, same tolerance as above):

- ADSL: 49/49 columns, 12,446/12,446 cells.
- ADAE: 55/55 columns, 65,505/65,505 cells.
- ADADAS: 40/40 columns, 498,520/498,520 cells.
- ADTTE: 26/26 columns, 6,604/6,604 cells.
- ADLBC: 46/46 columns, 1,708,072/1,708,072 cells.
