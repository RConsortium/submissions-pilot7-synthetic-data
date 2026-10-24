# Pilot 6 ADaM derivations

The initial ADSL specification is self-contained and reads only Pilot 6's
staged SDTM. See the [study README](../../README.md) for its provenance,
the missing production reference data, and the seven remaining datasets.

From the repository root:

```bash
python -m pip install -r submission-pilot6/program/adam/python/requirements.txt
python submission-pilot6/program/adam/python/run.py
```

The runner uses `../../spec/yamaa/project.yaml` with the pinned yamaa 1.0
engine and saves `../../data/adam/adsl-yamaa.parquet`. It resolves the study
from its own location, so it works from any working directory.

ADSL builds 254 rows and 50 columns with zero engine issues. Its production
reference comparison remains unavailable and is not counted as a pass.
