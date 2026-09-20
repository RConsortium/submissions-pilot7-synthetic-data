# cdiscpilot05

RConsortium submissions-pilot5 (the Dataset-JSON pilot), staged for
YAMAA-based SDTM-to-ADaM derivation and the weekly schema-complexity rerun.

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
- `spec/define-sdtm.xml` and `spec/define-adam.xml`: the original define.xml
  files from the submission package.
- `program/adam/`: YAMAA derivation specs (SDTM -> ADaM), added one dataset at
  a time by the weekly rerun job.

All data files are parquet; the only exceptions are the define.xml files.
