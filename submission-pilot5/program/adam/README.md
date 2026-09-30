# Pilot 5 ADaM derivations

Five single-output yamaa specifications in `../../spec/yamaa/` derive the official
Pilot 5 ADaM datasets from SDTM. Run `python/run.py` from this directory to
execute the specs in dependency order and write
`../../data/adam/<dataset>-yamaa.parquet`.
Every ADaM variable is derived in a specification. `python/compare.py` checks
all official columns and cells at an absolute numeric tolerance of 1e-10,
and compares the YAML label declarations with the official labels.

```bash
cd submission-pilot5/program/adam
pip install -r python/requirements.txt
python3 python/run.py
python3 python/compare.py
```

The dependency order is ADSL, ADAE, ADADAS, ADTTE, ADLBC. All downstream
specs read the derived ADSL; ADTTE also reads derived ADAE.

ADAE and ADLBC read the derived ADSL through an implicit join on `STUDYID`
and `USUBJID`; neither needs a named intermediate for that key match.
ADLBC reads SUPPLB ENDPOINT in-spec via the `SUP_EP` intermediate: `str_pad`
formats the numeric `LBSEQ` to 8 chars to match text `IDVARVAL`, so no
staging script is needed. The `EOTFB` intermediate ranks fallback
candidates in-spec (REQ-1262/REQ-1263).

The specs follow yamaa's [specification style contract](https://github.com/elong0527/yamaa/blob/main/rules/specification/style.md)
at revision `e6bca4ac`: schema field order, blank-line spacing, a 79-character
line limit, `{literal: X}` for literal expressions, and bare strings for
plain sources. Run `python3 -m yamaa.style --fix ../../spec/` for safe layout
fixes; the checker reports any remaining findings.

The complete comparison passed with zero yamaa validation issues on
`e6bca4ac` (2026-09-29):

| Dataset | Columns | Matching cells |
| --- | ---: | ---: |
| ADSL | 49/49 | 12,446/12,446 |
| ADAE | 55/55 | 65,505/65,505 |
| ADADAS | 40/40 | 498,520/498,520 |
| ADTTE | 26/26 | 6,604/6,604 |
| ADLBC | 46/46 | 1,708,072/1,708,072 |
| **Total** | | **2,291,147/2,291,147** |

The ADSL spec derives the official disease duration, baseline MMSE, and end
of study variables. Downstream specs consume its derived output. String flags
and categories explicitly emit the official empty text where applicable.
