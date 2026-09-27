# Pilot 1 ADaM derivations (yamaa)

Native yamaa specs deriving CDISC Pilot 1 ADaM datasets from SDTM.
Every analysis variable is derived by the yamaa engine; `run.py`
only invokes the engine (no Python derivation).

## Specs

Single-spec (derive-only, validated):
- `adsl.yaml` — 254 × 48, 0 validation issues, 12,192/12,192 cells exact
- `adae.yaml` — 1,191 × 55, 0 issues, 65,505/65,505 cells exact
- `adtte.yaml` — 254 × 26, 0 issues, 6,604/6,604 cells exact
- `advs.yaml` — 32,139 × 34, 0 issues, 1,092,726/1,092,726 cells exact
- `adlbc.yaml` — native PREV via row_value (no prevmap); validation pending
- `adlbh.yaml` — native PREV via row_value (no prevmap); 0 issues
- `adlbhy.yaml` — from ADLBC output
- `adqsnipx.yaml` — 31,140 × 41, 0 issues (domain ADQSNPIX)

Staged (blocked on yamaa issues, not consolidated):
- `adqsadas-s1/s2/s2subj/s3/final.yaml` — blocked by elong0527/yamaa#1148
  (window_on_window_result: rank → case → previous_non_missing)
- `adqscibc-s1/s2/s3a/s3b/s3c/s3d/s4j/s4/s5j/s5.yaml` — blocked by
  validator hang on multiple diff-case "closest to target" blocks

## Run

    python3 run.py            # 8 single specs, in dependency order
    python3 compare.py        # strict: |diff| <= 1e-10 numeric, exact else

`compare.py` checks shape, column order, Arrow types, yamaa:label
metadata, and every cell against `../../data/adam/`. Null vs "" are
distinct. Exit nonzero on mismatch.

## Notes

- ADSL is derived once; downstream specs consume the derived ADSL.
- Outputs are written to `output/` per the spec's `output.path`.
- `adqsnipx.yaml` uses domain ADQSNPIX (official spelling); the
  filename follows the ten-file contract.
