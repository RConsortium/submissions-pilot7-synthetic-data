# Pilot 5 ADaM derivations

One yamaa specification defines each output dataset. `run.py` stages SDTM
inputs, runs the specifications in dependency order, and writes
`work/adam/<dataset>-yamaa.parquet`. `compare.py` compares every official
column and cell at absolute numeric tolerance 1e-10. Missing or extra
columns, missing outputs, duplicate keys, and mismatched cells fail.

Install the current [yamaa](https://github.com/elong0527/yamaa) Python
engine, Polars, and PyArrow. The latest engine checked here was `9d34c56`.

```bash
python3 run.py                    # ADSL, ADAE, ADTTE
python3 compare.py adsl,adae,adtte
python3 run.py adadas             # manual investigation
python3 run.py adlbc              # manual investigation
python3 compare.py                # all five; fails until both are resolved
```

The default run covers the three datasets verified against current yamaa:

| Dataset | Columns | Matching cells |
| --- | ---: | ---: |
| ADSL | 49/49 | 12,446/12,446 |
| ADAE | 55/55 | 65,505/65,505 |
| ADTTE | 26/26 | 6,604/6,604 |

The ADSL spec now derives every official column, including disease duration
from the inclusive days between disease onset and Visit 1 (`days * 12 /
365.25`, rounded to one decimal), the baseline MMSE total, and end of study
status. Subject variables are derived once in ADSL and read by downstream
specs. All output columns declare labels.

ADADAS and ADLBC remain under investigation on current yamaa. Their single
specifications run for more than two and three minutes respectively on the
full study input without producing output; neither is included in the
default run or claimed equivalent. `stage-adlbc-lb.py` only prepares the
LB/SUPPLB input for the ADLBC specification. The study cannot claim full
five-dataset equivalence until these two outputs finish and pass
`compare.py`.
