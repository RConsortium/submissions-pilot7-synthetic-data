# Pilot 5 Define-XML generation

The [yamaa project](../../spec/yamaa/project.yaml) uses the same five dataset
YAML files for derivation and Define-XML generation. Each file owns its
derivations, labels, and dataset/column submission metadata. Shared
[codelists](../../spec/yamaa/codelists.yaml), study identity, ADaMIG 1.1 and
the reviewer guide are declared by that project. Metadata was transcribed
from Pilot 5's own preserved Define-XML, including its methods and VLM.

From the repository root:

```bash
python -m pip install -r submission-pilot5/program/adam/python/requirements-define.txt

# Reuse this pinned checkout if it was prepared for Pilot 3.
git clone https://github.com/elong0527/yamaa.git .build/define-schema-source
git -C .build/define-schema-source checkout --detach 3e8d5f6b5d2af223fba6aa29fa7209699123f706

python .github/scripts/generate_define.py submission-pilot5 \
  --schemas .build/define-schema-source/rust/tests/schemas
```

The shared command runs and checks all five ADaM datasets, compares them
under Pilot 5's existing policy, generates `data/adam/define-yamaa.xml` from
the same project, validates it against the local Define-XML 2.1 XSDs, and
writes `.build/submission-pilot5-define/report.json`. The XML references the
actual `<dataset>-yamaa.parquet` files beside it. `data/adam/adrg.pdf` is an
unchanged copy of the source guide. The fixed creation time denotes the
reference's original instant in UTC.

As in [Pilot 3](../../../submission-pilot3/program/adam/DEFINE.md), the specs
use numeric codelists matching their executable float types, explicit blank
terms for existing empty strings, one-decimal ADLBC visit codes, and duration
unit length 4. Origins describe Pilot 5's own observed/LOCF and lab-donor
constructions. These declarations are enforced by normal project runs.
Reference data and XML are preserved; the comparison tolerance and existing
missing-character policy are unchanged.

The generated document covers five datasets, 216 variables, 15 value-level
definitions and 36 codelists. Source core designations and CT release
information remain unavailable: `core: Cond` is draft, and local blank terms
are not assigned NCI aliases. Those additions and every other metadata
difference are reported rather than treated as reference equivalence.

The command remains **incomplete** and exits 1 while metadata differs from
the published Define-XML 2.0, even when dataset, generation, XSD and candidate
data checks pass. Remaining differences include keys/mandatory flags, numeric
types, provenance, explicit blank terms, corrected length, codelist
classification, and Parquet versus XPT leaves. No XPT transport or full 2.0
reproduction is claimed.
