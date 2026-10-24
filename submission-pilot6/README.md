# Submission Pilot 6

R Consortium's ADaM and TLF expansion on the CDISC Pilot 01 study.

- Source: https://github.com/RConsortium/submissions-pilot6-adams-tlfs
- `data/sdtm/`: 21 CDISC Pilot 01 SDTM datasets, excluding TS, as staged
  previously. Labels are preserved in Arrow schema metadata.
- `data/adam/`: official production ADaM references are not staged here.
  Locally generated `*-yamaa.parquet` files are ignored.
- `spec/define-adam.xml`, `spec/define-sdtm.xml`, and `spec/pilot6-specs.xlsx`:
  source metadata and derivation specifications.
- `spec/yamaa/`: an initial ADSL specification and a yamaa 1.0 project.
- `program/adam/python/`: the location-independent runner and requirements.

## Current yamaa coverage

ADSL adapts the shared Pilot 3 study derivations into a self-contained
specification. It reads only Pilot 6's staged SDTM and adds COMPLFL from
the Pilot 6 workbook.
It builds 254 subjects and 50 columns with zero engine issues. It has not
been compared with Pilot 6's production ADSL and remains a starting point
for review, not a verified replacement for the production program.

ADADAS, ADAE, ADLBC, ADLBH, ADNPIX, ADTTE, and ADVS still need specifications.
They are not listed in the active project and are not counted as passing.

From the repository root:

```bash
python -m pip install -r submission-pilot6/program/adam/python/requirements.txt
python submission-pilot6/program/adam/python/run.py
```

The runner checks and builds ADSL. No official reference comparison is
performed because the production reference data is not staged here.

## Reference data

The upstream repository documents anonymous DVC downloads of its S3-backed
data. The S3 endpoint was blocked by the development environment's network
policy during this update. No production ADaM was substituted from another
pilot. Once the official references are imported and the derivations are
reviewed, add a strict comparator before treating the output as verified.
