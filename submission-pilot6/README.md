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
- `program/adam/python/`: the location-independent runner, strict comparator,
  regression tests, and pinned requirements.

## Current yamaa coverage

ADSL adapts the shared Pilot 3 study derivations into a self-contained
specification. It reads only Pilot 6's staged SDTM and adds COMPLFL from
the Pilot 6 workbook. The 50 output columns, their order, and their labels
agree with that workbook.
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

The runner checks and builds ADSL, exiting nonzero on engine errors.
Use `run.py --check` to check without saving outputs, or `run.py --compare`
to require a successful comparison with the official reference. The latter
fails while the reference is absent.

```bash
python -m unittest discover -s submission-pilot6/program/adam/python/tests -v
python submission-pilot6/program/adam/python/run.py --check
python submission-pilot6/program/adam/python/compare.py
```

The comparator aligns unique, nonmissing `STUDYID`/`USUBJID` keys and requires
matching columns/order, logical types, and specification labels versus the
official `yamaa:label` field metadata. Numeric absolute tolerance is `1e-10`;
missing strings normalize to R's empty-string convention. Duplicate keys,
missing subjects, extra columns, label differences, and missing references fail.
`compare.py --data-root /path/to/data` reads both Parquet files from that
location's `adam/` folder.

## Production-program review

Reviewed against [production adsl.r at a4f85c95](https://github.com/RConsortium/submissions-pilot6-adams-tlfs/blob/a4f85c95cfef1f6aa27795362630f8ae43210185/code/adam/adsl.r).
The specification now selects treatment dates from qualifying exposure
(positive dose or zero-dose placebo), leaves partial start dates missing,
imputes partial end dates to the last day/month, and bounds imputed components
by discontinuation dates only. Fully collected end dates are retained.
Cumulative dose propagates missing duration/dose values rather than silently
summing only complete records. Disposition flags, the completion reason,
visit/reference date parsing, and the MMSE source also follow that program.

The regression suite uses small, authored source records with hand-calculated
results. CI runs those tests and builds the staged 254-subject ADSL on every
relevant PR, including drafts. These checks do not establish agreement with
production output or establish that the staged SDTM is current.

## Reference data

The upstream repository documents anonymous DVC downloads of its S3-backed
data. The S3 endpoint was blocked by the development environment's network
policy during this update. No production ADaM was substituted from another
pilot. To finish validation, download the input and output Dataset-JSON together
using the upstream README's anonymous DVC procedure and record the upstream
commit. Convert the refreshed SDTM and official ADaM to the repository's
Parquet layout, preserving labels in `yamaa:label` metadata; stage official
ADSL as `data/adam/adsl.parquet`. Then run `run.py --compare`. That command
must pass before treating ADSL as verified. The remaining seven derivations
and confirmation that the staged SDTM matches that upstream revision are
still outstanding.
