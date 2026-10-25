# submission-pilot5

RConsortium submissions-pilot5 (the Dataset-JSON pilot), staged for
yamaa-based SDTM-to-ADaM derivation and the weekly schema-complexity rerun.

- Source: https://github.com/RConsortium/submissions-pilot5-datasetjson/tree/main/pilot5-submission
- `data/sdtm/`: the 22 SDTM tabulation datasets (ae, cm, dm, ds, ex, lb, mh,
  qs, relrec, sc, se, suppae, suppdm, suppds, supplb, sv, ta, te, ti, tv, vs),
  converted from Dataset-JSON 1.1.0 to parquet. Column labels are preserved in
  the arrow schema metadata. Decimal columns become float64 (blank or NA
  values become null); string values are kept exactly as in the JSON, padding
  included.
- `data/adam/`: the 5 official ADaM analysis datasets (adadas, adae, adlbc,
  adsl, adtte), converted from SAS transport (.xpt) to parquet. SAS column
  labels are preserved in the arrow schema metadata.
- `spec/`: the original define.xml files and five yamaa ADaM YAML
  specifications.
- `program/adam/python/`: the yamaa runner and comparison tool. `program/adam/adam-compare-keys.json` holds the keys for
  the repository comparison workflow.

All data files are parquet; the only exceptions are the define.xml files.

## ADaM verification

Derived ADaM datasets are verified cell-by-cell against the official ones
with `.github/scripts/compare_adam.py`:

    python3 .github/scripts/compare_adam.py \
        --official submission-pilot5/data/adam \
        --derived <derived-adam-dir> \
        --keys-file submission-pilot5/program/adam/adam-compare-keys.json \
        --null-empty-equal

Comparison policy (all five pilot 5 datasets pass under it):

- Numeric cells match when `|derived - official| <= 1e-10` (absolute
  tolerance). Null equals null, NaN equals NaN.
- Non-numeric cells must match exactly. `--null-empty-equal` normalizes `""`
  to null first: the official XPT-sourced parquets store blanks as `""`.
- Rows are aligned by the key columns in `adam-compare-keys.json` before
  comparing. Column order differences are warnings; column set or row count
  differences are failures. Arrow schema metadata (e.g. column labels) is
  ignored.

## Source documents

[spec/source/](spec/source/README.md) retains the original ADaM workbook,
reviewer guide, pinned provenance, and a starter inventory of rules for review.

## License and attribution

This pilot uses the CDISC SDTM/ADaM Pilot Project study, published by CDISC,
through the Pilot 5 source linked above. Study data, including derived
datasets, and imported reference metadata are excluded from the root MIT
grant. Original Pilot 7 code and documentation are MIT-licensed. See
[LICENSING.md](../LICENSING.md#cdisc-pilot-data-and-reference-material) and the
retained [CDISC notice](../LICENSE-CDISC.txt) for attribution, upstream terms,
and the limits on conversion and redistribution.
