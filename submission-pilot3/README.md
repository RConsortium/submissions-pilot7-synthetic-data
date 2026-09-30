# submission-pilot3

R Consortium R Submission Pilot 3 (Study CDISC Pilot 03), staged for
YAMAA-based SDTM-to-ADaM derivation.

- Source: https://github.com/RConsortium/submissions-pilot3-adam/tree/main/submission
  (verified byte-identical to the FDA eCTD submission package at
  https://github.com/RConsortium/submissions-pilot3-adam-to-fda)
- `data/sdtm/`: the 22 SDTM tabulation datasets, converted from SAS transport
  (.xpt) to parquet. Column labels are preserved in the arrow schema metadata.
- `data/adam/`: the 5 ADaM analysis datasets from the official FDA submission
  (adadas, adae, adlbc, adsl, adtte), converted from SAS transport (.xpt) to
  parquet. Column labels are preserved in the arrow schema metadata.
- `data/mapping/`: the checked-in ADADAS planning and analysis-window CSVs.
- `spec/define/`: the official define.xml files from the submission package.
- `spec/yamaa/`: YAMAA derivation specifications (SDTM -> ADaM).
- `program/adam/`: the Python runner, comparison, and planning generator.
- Note: the development repo also carries 7 additional team-defined ADaM
  datasets (advs, adcibc, adlbcpv, adlbh, adlbhpv, adlbhy, adnpix) that were
  not part of the FDA submission; they are not staged here.

The study also includes the mapping CSVs and define.xml files.
