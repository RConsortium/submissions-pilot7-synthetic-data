# Pilot 5 Define-XML 2.0 reproduction

The native yamaa composer reproduces all metadata in the published
Define-XML 2.0.0: 5 datasets, 216 variables, 15 value-level entries and
36 codelists. A complete comparison must report zero differences. Byte
identity is separate: yamaa retains its own provenance, generated object
identifiers and formatting.

Each [dataset specification](../../spec/yamaa/project.yaml) contains its
derivations and historical `submission` metadata in one YAML file. The same
project supplies the study, ADaMIG 1.1, documents and shared
[codelists](../../spec/yamaa/codelists.yaml). Generation does not read or copy
the reference XML. The comparison reads it independently afterwards.

## Run

From the repository root:

```bash
python -m pip install -r submission-pilot5/program/adam/python/requirements-define.txt

git clone https://github.com/elong0527/yamaa.git .build/define-schema-source
git -C .build/define-schema-source checkout --detach bfe94ebc3a966b8b70977d45e731bd6bdd2c7c2a

python .github/scripts/generate_define.py submission-pilot5 \
  --schemas .build/define-schema-source/rust/tests/schemas
```

The required engine changes are proposed in
[yamaa PR #4030](https://github.com/elong0527/yamaa/pull/4030), addressing
issues #4028 and #4029. The source revision in
`requirements.txt` includes both changes; an older released engine cannot
reproduce this metadata profile.

The command checks and runs the five specifications, saves the derived
Parquet files, and compares every dataset with the original published data
using the existing comparison policy. It then composes twice at the fixed
reference creation instant, requires identical bytes, validates against the
local CDISC 2.0 schema with network access disabled, and compares every
metadata field with the unchanged published XML.

Outputs:

- `data/adam/<dataset>-yamaa.parquet`: derived datasets.
- `data/adam/define-yamaa.xml`: generated Define-XML 2.0.0.
- `data/adam/adrg.pdf`: unchanged copy of the source reviewer guide.
- `.build/submission-pilot5-define/report.json`: generation, determinism,
  schema, dataset, metadata-comparison and data-audit evidence.

The Define-XML reproduction workflow uploads the XML and report for each
pilot. The published reference XML and data remain unchanged.

## Historical declarations and data conformance

`submission.mode: historical` explicitly retains the received metadata. The
project selects `define_version: "2.0.0"` and `context: Other`, without
transport generation. Historical `key_sequence` values are independent of
the executable dataset keys. Integer metadata can therefore describe a
physical float column exactly as the source document does.

The historical declarations do not add data constraints to execution.
Executable column types, keys, explicit verifications and all derivation
logic remain active and unchanged. The ordinary validated metadata mode is
the default for specifications that do not select historical mode.

Faithful reproduction retains the published metadata's conflicts: fractional
values declared integer, missing historical key values, blank strings absent
from codelists, and `DAYS` exceeding its declared length of 3. The generator
audits both the derived data and the independent published data, preserving
every conflict in separate report sections. No blank terms, corrected
lengths, invented core designations or replacement origins are added to the
historical metadata.

A successful command means the data comparison and metadata reproduction
passed. It does not mean the historical declarations conform to the data.
`submission_data_conformant` reports that separate audit result. Metadata
mismatches or schema/generation failures produce a nonzero exit status.

Historical XPT/JSON package links are retained literally. No transport is
produced, and `historical_package_links` records whether those files are
available beside the generated XML. This is metadata reproduction, not a
complete or certified submission package.

## Comparison coverage

The independent comparator resolves references and compares every variable's
label, type, length, precision, format, key, mandatory flag, origin, method and
comment, including all value-level conditions and shared method bindings. It
also compares dataset order and properties, document references, ordered
codelist values, decodes, aliases and external dictionary versions.

Unknown and unused content cannot pass equivalence. Dangling references and
duplicate identities fail. There is no difference allowlist, and the
comparison policy is unchanged by this reproduction work. The report records
all normalizations, every remaining difference and raw representation facts,
including the explicit `byte_identical` result.
