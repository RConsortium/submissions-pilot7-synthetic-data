# cdiscpilot01

CDISC SDTM/ADaM Pilot Project (Study CDISC Pilot 01), staged for yamaa-based
SDTM-to-ADaM derivation.

- Source: https://github.com/cdisc-org/sdtm-adam-pilot-project/tree/master/updated-pilot-submission-package/900172/m5/datasets/cdiscpilot01
- `data/sdtm/`: the 22 SDTM tabulation datasets, converted from SAS transport
  (.xpt) to parquet. Column labels are preserved in the arrow schema metadata.
- `spec/define/`: the original SDTM and ADaM define.xml files.
- `spec/yamaa/`: eight active yamaa derivation specifications (SDTM -> ADaM).
- `program/adam/python/`: the runner, strict comparator, and requirements.
- `data/adam/`: official ADaM reference datasets and ignored yamaa outputs.

All data files are parquet; the only exception is define.xml.

## License and attribution

Data and imported reference metadata originate from the CDISC SDTM/ADaM Pilot
Project, published by CDISC. They are excluded from the root MIT grant and
remain subject to upstream terms. Original Pilot 7 code and documentation are
MIT-licensed. See [LICENSING.md](../LICENSING.md#cdisc-pilot-data-and-reference-material)
and the retained [CDISC notice](../LICENSE-CDISC.txt). The existing Parquet
conversions do not establish permission to modify or redistribute the data.
