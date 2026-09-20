# cdiscpilot01

CDISC SDTM/ADaM Pilot Project (Study CDISC Pilot 01), staged for YAMAA-based
SDTM-to-ADaM derivation.

- Source: https://github.com/cdisc-org/sdtm-adam-pilot-project/tree/master/updated-pilot-submission-package/900172/m5/datasets/cdiscpilot01
- `data/sdtm/`: the 22 SDTM tabulation datasets, converted from SAS transport
  (.xpt) to parquet. Column labels are preserved in the arrow schema metadata.
- `spec/define-sdtm.xml`: the original SDTM define.xml from the submission package.
- `program/adam/`: YAMAA derivation specs (SDTM -> ADaM), added one dataset
  per week by the automated derivation job.
- `data/adam/`: ADaM analysis datasets derived by YAMAA, in parquet.

All data files are parquet; the only exception is define.xml.
