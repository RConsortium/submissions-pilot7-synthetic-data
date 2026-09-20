# cdiscpilot06

RConsortium submissions-pilot6 (ADaM and TLF expansion on the CDISC Pilot 01
study), staged for YAMAA-based SDTM-to-ADaM derivation and the weekly
schema-complexity rerun.

- Source: https://github.com/RConsortium/submissions-pilot6-adams-tlfs
- `data/sdtm/`: the 21 SDTM tabulation datasets Pilot 6 builds on (ae, cm, dm,
  ds, ex, lb, mh, qs, relrec, sc, se, suppae, suppdm, suppds, supplb, sv, ta,
  te, ti, tv, vs). Pilot 6 targets the CDISC Pilot 01 study ("Protocol:
  CDISCPILOT01" in its TLF programs), so these are the verified cdiscpilot01
  SDTM parquets, minus `ts` which Pilot 6 does not stage. Column labels are
  preserved in the arrow schema metadata.
- `data/adam/`: PENDING. Pilot 6's 8 production ADaM datasets (adadas, adae,
  adlbc, adlbh, adnpix, adsl, adtte, advs) are DVC-tracked in a private S3
  bucket; pulling them needs signup credentials (see the pilot6 repo README).
  They will be added here as parquet once the credentials are available.
- `spec/define-adam.xml` and `spec/pilot6-specs.xlsx`: the ADaM define.xml and
  derivation specs from the pilot6 repo. `spec/define-sdtm.xml`: the CDISC
  Pilot 01 SDTM define (shared study, same file as cdiscpilot01).
- `program/adam/`: YAMAA derivation specs (SDTM -> ADaM), added one dataset at
  a time by the weekly rerun job.

All data files are parquet; the only exceptions are the define.xml and
specs files.
