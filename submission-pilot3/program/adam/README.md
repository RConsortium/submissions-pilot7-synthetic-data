# Pilot 3 ADaM derivation programs (yamaa)

yamaa target specs that regenerate the five Pilot 3 ADaM datasets from the
SDTM parquets in `../data/sdtm/`. Every derivation lives in the YAML specs
(plus the hand-built planning relations in `inputs/`, which mirror the R
program's tribbles). `run.py` only stages inputs and runs the specs;
`compare.py` only compares the derived datasets against the official ADaM.

Each dataset is derived with one call:

    import yamaa
    adsl = yamaa.yamaa_domain("adsl.yaml").output

## End-to-end run

From a fresh clone:

    cd submission-pilot3/program/adam
    pip install -r requirements.txt
    python3 run.py        # derive all five datasets into work/derived/
    python3 compare.py    # verify every cell against ../data/adam/

`run.py` stages the SDTM parquets and the planning inputs into a `work/`
directory, runs the specs in dependency order with
`yamaa.yamaa_domain("<ds>.yaml").output` (persisting via `.save()`), and
writes the five derived datasets to `work/derived/` as `adsl-yamaa.parquet`,
`adae-yamaa.parquet`, `adadas-yamaa.parquet`, `adtte-yamaa.parquet`, and
`adlbc-yamaa.parquet`, each with variable labels. `compare.py` then checks
every cell against the official ADaM in `../data/adam/` (numeric cells
within `|derived - official| <= 1e-10`, non-numeric exact with null/`""`
normalized, variable labels compared) and reports matched/total columns
and cells per dataset. Its reusable helpers work standalone too:

    from compare import compare, compare_domain
    compare("work/derived/adsl-yamaa.parquet", "../data/adam/adsl.parquet", "adsl")
    compare_domain("adsl")  # resolves the standard paths and compares

`work/` is git-ignored build output; only the specs, inputs, scripts,
requirements, and this README are committed.

## Stage order (what run.py does)

1. `adsl_exdose.yaml` — per-record exposure staging (REQ-0483): one row per
   EX record with the imputed exposure start/end dates and per-record dose.
2. `adsl.yaml` — from SDTM DM/DS/QS/SV/VS/SC/MH plus the exdose staging
   (TRTSDT/TRTEDT/CUMDOSE all aggregate the staging; SDTM EX is never read
   directly). Output: ADSL.
3. `adae.yaml` — from SDTM AE plus the derived ADSL. Output: ADAE.
4. `adadas.yaml` — from SDTM QS (plus a `QSDTC_D` date column parsed from
   `QSDTC` at staging time, since the planner's static gate currently rejects
   ISO date text for `to_date`, REQ-0607/REQ-1107), the derived ADSL, the
   222-row LOCF planning relation (`inputs/plan.csv`), and the 4-row
   analysis-window lookup (`inputs/aw_lookup.csv`). Output: ADADAS.
5. `adtte.yaml` — from derived ADSL, derived ADAE, and SDTM DS. Output:
   ADTTE.
6. `adlbc.yaml` — from SDTM LB/SUPPLB plus the derived ADSL. Output: ADLBC.

Subject-level variables are derived once, in ADSL; the other four specs
read them from the derived `adsl-yamaa.parquet` predecessor instead of
re-deriving them.

## Notes

- Every spec column declares a `label:` (the yamaa way); `run.py` stamps
  them onto the derived parquet as `yamaa:label` field metadata — the
  engine's R020 parquet profile carries no field metadata of its own
  (REQ-0741). Labels are sourced from the official ADaM parquets and
  cross-checked against `../spec/define-adam.xml` (100% agreement); the
  comparison verifies every label matches.
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
(`python3 run.py && python3 compare.py`, same tolerance as above):

- ADSL: 49/49 columns, 12,446/12,446 cells.
- ADAE: 55/55 columns, 65,505/65,505 cells.
- ADADAS: 40/40 columns, 498,520/498,520 cells.
- ADTTE: 26/26 columns, 6,604/6,604 cells.
- ADLBC: 46/46 columns, 1,708,072/1,708,072 cells.
