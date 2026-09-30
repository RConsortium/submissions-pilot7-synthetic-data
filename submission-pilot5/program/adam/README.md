# Pilot 5 ADaM derivations

Five single-output yamaa specifications in `../../spec/` derive ADSL, ADAE,
ADADAS, ADTTE, and ADLBC from Pilot 5 SDTM. The Python runner and comparison
tool live in `python/`. The ADLBC helper prepares chemistry LB and its
SUPPLB ENDPOINT input; all ADaM variables are derived in the YAML specs.

From this directory, install the pinned yamaa revision and run:

```bash
python3 -m pip install -r python/requirements.txt
python3 python/run.py
python3 python/compare.py
python3 -m yamaa.style ../../spec/
```

`python/run.py` stages SDTM in the ignored `work/` directory, runs the specs
in dependency order, and writes `work/adam/<dataset>-yamaa.parquet`. The
derived ADSL and ADAE are staged as inputs for downstream specs.
`python/compare.py` aligns on unique dataset keys, checks every official
column, label, type, and cell, and exits nonzero on a mismatch. Numeric cells
use absolute tolerance `1e-10`; null and empty text remain distinct.

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
