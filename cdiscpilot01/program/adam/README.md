# Pilot 1 ADaM derivations

Each active ADaM output has one yamaa specification in `../../spec/yamaa/`.
`python/run.py` reads the study's SDTM Parquet files, runs the specs in
dependency order, and saves `../../data/adam/<dataset>-yamaa.parquet`.
The other specs read the derived ADSL and,
for ADLBHY, the derived ADLBC. ADaM variables are derived in YAML.

Install the requirements, then run from this directory:

```bash
python3 -m pip install -r python/requirements.txt
python3 -m yamaa.style ../../spec/yamaa/*.yaml
python3 python/run.py                     # all eight active outputs
python3 python/run.py adsl adae adtte     # selected outputs in dependency order
python3 python/compare.py                # strict comparison of all eight outputs
python3 python/compare.py adsl adae      # selected comparisons
```

`python/compare.py` checks output shape, column order and types, `yamaa:label`
metadata, and every cell against `../../data/adam/`. Numeric values must
match within absolute tolerance `1e-10`; null and empty text differ. Missing
or mismatched outputs make it exit nonzero. The official ADQSNIPX file is
named `adqsnpix.parquet`.

## Verified outputs

The following full comparisons passed with zero yamaa validation issues on
yamaa `e6bca4ac` (2026-09-29):

| Dataset | Columns | Matching cells |
| --- | ---: | ---: |
| ADSL | 48/48 | 12,192/12,192 |
| ADAE | 55/55 | 65,505/65,505 |
| ADTTE | 26/26 | 6,604/6,604 |
| ADVS | 34/34 | 1,092,726/1,092,726 |
| ADLBC | 46/46 | 3,416,144/3,416,144 |
| ADLBH | 46/46 | 2,296,872/2,296,872 |
| ADLBHY | 43/43 | 428,022/428,022 |
| ADQSNIPX | 41/41 | 1,276,740/1,276,740 |

The ADLBC and ADLBH specifications explicitly exclude unscheduled records
from the previous-value window. ADQSNIPX looks up baseline by subject and
test code.

The specifications follow yamaa's [specification style contract][style]:
schema field order, blank-line layout, lines of at most 79 characters, and
canonical literal and source expressions.

[style]: https://github.com/elong0527/yamaa/blob/e6bca4ac6589f7b884c26604afe3a0c13af71ad3/rules/specification/style.md

## Outputs awaiting a single specification

ADQSADAS and ADQSCIBC are excluded from `run.py` and `compare.py`. Their old
multi-stage YAML workarounds have been removed. The rank-to-forward-fill
limitation previously cited for ADQSADAS was fixed in
[yamaa#1148](https://github.com/elong0527/yamaa/issues/1148); a single spec
still needs to be built and compared. The ADQSCIBC single-spec validation
hang is tracked in [yamaa#1484](https://github.com/elong0527/yamaa/issues/1484).
