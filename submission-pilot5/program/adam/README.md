# Submission Pilot 5 ADaM derivations

`../../spec/yamaa/project.yaml` lists the active specifications in dependency
order. The project uses the yamaa 1.0 language and API at the source revision
pinned in `python/requirements.txt` (currently an unreleased engine).
Python 3.12 or later and Rust/Cargo 1.82 or later are required for installation.

From the repository root:

```bash
python -m pip install -r submission-pilot5/program/adam/python/requirements.txt
python submission-pilot5/program/adam/python/run.py
python submission-pilot5/program/adam/python/compare.py
```

Both scripts resolve the study from their own locations and work from any
working directory. Outputs are ignored `data/adam/<dataset>-yamaa.parquet`
files; the official reference datasets are preserved.

The complete reference comparison passes with the pinned engine at
`3e8d5f6b5d2af223fba6aa29fa7209699123f706` (2026-10-24). Numeric cells
use the existing absolute tolerance of `1e-10`. The comparator aligns rows by its dataset keys and checks all official columns, cells, and declared labels. Null and empty text are normalized according to the original comparison policy.

Specifications now declare explicit lookup keys, producing-specification
links, current temporal operations, and grammar expressions. Explicit
`nulls: last` terms preserve the prior missing-value ordering. Retired
COALESCE/GREATEST functions are expressed with helper derivations and the
current verbs. The migration preserves the original comparison policies.

The active order is ADSL, ADAE, ADADAS, ADTTE, ADLBC. ADLBC reads SUPPLB
ENDPOINT through a named intermediate and ranks fallback candidates in-spec;
no external input staging program is needed.
