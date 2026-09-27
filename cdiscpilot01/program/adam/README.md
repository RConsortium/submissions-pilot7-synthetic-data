# Pilot 01 ADaM derivation programs (yamaa)

Executable yamaa target specs that derive all ten CDISC Pilot 01 ADaM
datasets from the SDTM parquets in `../data/sdtm/`. Every analysis variable
is derived natively by the yamaa engine; the one Python script is
orchestration only (dependency order, Arrow `large_string`→`string` recasts
between stages, joining the yamaa-derived PREV_AVAL map back onto LB, and
concatenating stage outputs).

## End-to-end run

`run.py` executes the whole pipeline and `compare.py` checks every derived
dataset cell-for-cell against the official ADaM in `../data/adam/`.

Requires the yamaa engine (`pip install` from
https://github.com/elong0527/yamaa), polars, pyarrow, and pyyaml.

    python3 run.py                 # everything, in dependency order
    python3 run.py adlbhy          # one dataset (predecessors auto-included)
    python3 compare.py             # strict check of all ten vs official ADaM
    python3 compare.py adsl adae   # strict check of a subset

On first run, `run.py` copies `../data/sdtm/` → `sdtm/` and `../data/adam/` →
`expected/` (a few MB; the engine rejects symlinked resource paths).
`sdtm/`, `expected/`, `upstream/`, `output/`, and `work/`
are git-ignored build output; only the specs, the two scripts, and this
README are committed.

## Stage order (what run.py does)

1. `adsl.yaml` — from SDTM DM/EX/VS/DS/SC/MH/SV/QS. Promoted to `upstream/`.
2. `adae.yaml` — from SDTM AE plus derived ADSL. Promoted to `upstream/`.
3. `adtte.yaml` — from derived ADSL, derived ADAE, SDTM DS.
4. `advs.yaml` — from SDTM VS plus derived ADSL.
5. `adlbh-prevmap.yaml` → join onto SDTM LB (`work/lb_h_with_prev.parquet`)
   → `adlbh.yaml`. The PREV_AVAL map (AVAL of the previous scheduled record
   within (USUBJID, LBTESTCD), raw BASELINE and unscheduled records excluded)
   is derived natively in yamaa; Python only joins it back by
   (USUBJID, LBTESTCD, LBSEQ).
6. `adlbc-prevmap.yaml` → join onto SDTM LB (`work/lb_with_prev.parquet`)
   → `adlbc.yaml`. Same PREV_AVAL pattern as ADLBH.
7. `adlbhy.yaml` — from the ADLBC output (promoted to `upstream/`).
   Derives BILIHY/TRANSHY/HYLAW natively per (subject, visit).
8. `adqsadas-s1.yaml` → `adqsadas-s2.yaml` → `adqsadas-s2subj.yaml` →
   `adqsadas-s3.yaml` → `adqsadas-final.yaml` — window assignment +
   closest-to-target selection, ACTOT forward-fill, per-subject empty-window
   flags, LOCF rows for empty windows, union with BASE/CHG/PCHG and ADSL
   covariates.
9. `adqscibc-s1.yaml` … `adqscibc-s5.yaml` (ten stages) → concat of natural +
   LOCF rows (`work/adqscibc-combined.parquet`) → `adqscibc-final.yaml`.
10. `adqsnpix-s1.yaml` → `adqsnpix-s2.yaml` → `adqsnpix-final.yaml` —
    window assignment + closest-to-target selection, per-subject NPTOTMN,
    union of item rows and NPTOTMN rows with BASE/CHG/PCHG.

## Verification

Strict cell-for-cell comparison (`python3 compare.py`: exact row/column
count and order, exact Arrow types, exact `yamaa:label` field metadata,
null-vs-"" distinct, floats exact or within a tiny relative tolerance):

- adsl: 254 x 48, bad_cols=0, close_float_cells=0
- adae: 1191 x 55, bad_cols=0, close_float_cells=0
- adtte: 254 x 26, bad_cols=0, close_float_cells=0
- advs: 32139 x 34, bad_cols=0, close_float_cells=0
- adlbh: 49932 x 46, bad_cols=0, close_float_cells=0
- adlbc: 74264 x 46, bad_cols=0, close_float_cells=0
- adlbhy: 9954 x 43, bad_cols=0, close_float_cells=0
- adqsadas: 12463 x 40, bad_cols=0, close_float_cells=0
- adqscibc: 730 x 36, bad_cols=0, close_float_cells=0
- adqsnpix: 31140 x 41, bad_cols=0, close_float_cells=768

Verified 2026-09-22, yamaa engine @ main
(`44a6d492bd49233a9b2e0376c03e8db5f459b759`).
