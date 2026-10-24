# cdiscpilot06

RConsortium submissions-pilot6 (ADaM and TLF expansion on the CDISC Pilot 01
study), staged for YAMAA-based SDTM-to-ADaM derivation and the weekly
schema-complexity rerun.

- Source: https://github.com/RConsortium/submissions-pilot6-adams-tlfs
- Input snapshot: [`a4f85c95cfef1f6aa27795362630f8ae43210185`](https://github.com/RConsortium/submissions-pilot6-adams-tlfs/commit/a4f85c95cfef1f6aa27795362630f8ae43210185)
  (the upstream `main` revision checked on 2026-10-24).
- `data/sdtm/`: the 21 SDTM tabulation datasets Pilot 6 builds on (ae, cm, dm,
  ds, ex, lb, mh, qs, relrec, sc, se, suppae, suppdm, suppds, supplb, sv, ta,
  te, ti, tv, vs). Every source Dataset-JSON file was verified against the
  size and MD5 in Pilot 6's current DVC pointers before conversion. The JSON
  was retrieved from the identical, publicly available Pilot 5 copy at
  commit `5b63261496f504b4d7fb8baa5155367881451393`. Row and column order,
  character blanks, numeric missing values, and column labels are preserved;
  labels use `yamaa:label` Arrow field metadata. Numeric values follow the
  source JSON's decimal text. This updates tiny floating-point differences
  in CM, LB, and QS from the earlier XPT-based staging. TS is not an upstream
  Pilot 6 input and is excluded.
- `data/adam/`: PENDING. Pilot 6's 8 production ADaM datasets (adadas, adae,
  adlbc, adlbh, adnpix, adsl, adtte, advs) are DVC-tracked in S3. The upstream
  README now documents anonymous `dvc pull`; the import environment blocked
  the S3 endpoint, so these reference outputs have not been imported. Their
  availability and comparison results are separate from SDTM input verification.
- `spec/define-adam.xml` and `spec/pilot6-specs.xlsx`: the ADaM define.xml and
  derivation specs from the same pinned Pilot 6 revision, including the
  current workbook. `spec/define-sdtm.xml`: the CDISC
  Pilot 01 SDTM define (shared study, same file as cdiscpilot01).
- `program/adam/`: YAMAA derivation specs (SDTM -> ADaM), added one dataset at
  a time by the weekly rerun job.

Datasets are Parquet. `spec/source-snapshot.json` records the upstream
commit, each DVC pointer's size and MD5, retrieval URLs, row and column
counts, Parquet SHA-256 hashes, and specification hashes.

## Reproduce or verify the SDTM import

Install `pyarrow==25.0.1` and `PyYAML==6.0.3`. From the Pilot 7 repository root:

```bash
git clone https://github.com/RConsortium/submissions-pilot6-adams-tlfs.git /tmp/pilot6-source
git -C /tmp/pilot6-source checkout a4f85c95cfef1f6aa27795362630f8ae43210185
python .github/scripts/import_pilot6_inputs.py /tmp/pilot6-source \
  --mirror-ref 5b63261496f504b4d7fb8baa5155367881451393
```

Add `--verify-only` to check the staged data and manifest without writing.
Alternatively, run `dvc pull` in the source checkout and omit `--mirror-ref`,
or supply an existing JSON directory with `--json-dir`. Every mode rejects
files whose size or MD5 differs from the pinned Pilot 6 DVC pointers.
Unsupported Dataset-JSON types and changes to the 21-domain inventory fail
explicitly for review. The importer stages all files before replacing data;
existing Parquet files with identical values, types, and labels are retained.
