# Pilot 5 ADaM derivations

One yamaa specification defines each official ADaM output. `run.py` stages
SDTM input, derives ADSL, ADAE, ADADAS, ADTTE, and ADLBC in dependency order,
and saves `work/adam/<dataset>-yamaa.parquet`. All ADaM variables are
calculated in the YAML specs. The ADLBC input helper selects chemistry LB
records and joins SUPPLB to expose the ENDPOINT supplement.

Install the pinned yamaa revision and run from this directory:

```bash
python3 -m pip install -r requirements.txt
python3 run.py
python3 compare.py
```

`run.py` is 30 lines of code and preserves each declared `yamaa:label` in
the Parquet output. `compare.py` aligns on unique dataset keys, checks every
official column and cell with absolute numeric tolerance `1e-10`, and exits
nonzero for missing outputs or mismatches. Null and empty text are distinct.

The following full comparisons passed with zero yamaa validation issues on
`6ab77309` (2026-09-28):

| Dataset | Columns | Matching cells |
| --- | ---: | ---: |
| ADSL | 49/49 | 12,446/12,446 |
| ADAE | 55/55 | 65,505/65,505 |
| ADADAS | 40/40 | 498,520/498,520 |
| ADTTE | 26/26 | 6,604/6,604 |
| ADLBC | 46/46 | 1,708,072/1,708,072 |
| **Total** | | **2,291,147/2,291,147** |

The ADSL spec derives the official disease duration, baseline MMSE, and end
of study variables. Downstream specs consume its derived output. String
flags and categories explicitly emit the official empty text where
applicable; the comparison does not normalize it to null.
