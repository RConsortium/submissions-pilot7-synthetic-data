# CDISC Pilot 01 ADaM derivations

`../../spec/yamaa/project.yaml` lists the active specifications in dependency
order. The project uses the yamaa 1.0 language and API at the source revision
pinned in `python/requirements.txt` (currently an unreleased engine).
Python 3.12 or later and Rust/Cargo 1.82 or later are required for installation.

From the repository root:

```bash
python -m pip install -r cdiscpilot01/program/adam/python/requirements.txt
python cdiscpilot01/program/adam/python/run.py
python cdiscpilot01/program/adam/python/compare.py
```

Both scripts resolve the study from their own locations and work from any
working directory. Outputs are ignored `data/adam/<dataset>-yamaa.parquet`
files; the official reference datasets are preserved.

The complete reference comparison passes with the pinned engine at
`3e8d5f6b5d2af223fba6aa29fa7209699123f706` (2026-10-24). Numeric cells
use the existing absolute tolerance of `1e-10`. The comparator checks row order, column order, Arrow types, every cell, and the declared labels. Null and empty text remain distinct.

Specifications now declare explicit lookup keys, producing-specification
links, current temporal operations, and grammar expressions. Explicit
`nulls: last` terms preserve the prior missing-value ordering. Retired
COALESCE/GREATEST functions are expressed with helper derivations and the
current verbs. The migration preserves the original comparison policies.

The active order is ADSL, ADAE, ADTTE, ADVS, ADLBC, ADLBH, ADLBHY, ADQSNPIX.
The last specification is named `adqsnipx.yaml`, while its official reference
is `adqsnpix.parquet`. ADQSADAS and ADQSCIBC remain outside the active project;
they still need single-spec implementations and comparisons.
