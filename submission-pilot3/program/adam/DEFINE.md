# Pilot 3 Define-XML generation

One [project](../../spec/yamaa/project.yaml) runs the ADaM derivations and
generates Define-XML. Each dataset YAML contains its executable derivations,
labels, and dataset/column `submission` metadata. The same project supplies
study identity, ADaMIG 1.1, supporting documents, and shared
[codelists](../../spec/yamaa/codelists.yaml). There is no separate submission
project or second set of dataset specifications.

## Run

From the repository root, install the existing engine pin and XML validator:

```bash
python -m pip install -r submission-pilot3/program/adam/python/requirements-define.txt

# The authoritative CDISC XSDs are retained in the tested yamaa source.
git clone https://github.com/elong0527/yamaa.git .build/define-schema-source
git -C .build/define-schema-source checkout --detach 3e8d5f6b5d2af223fba6aa29fa7209699123f706

python .github/scripts/generate_define.py submission-pilot3 \
  --schemas .build/define-schema-source/rust/tests/schemas
```

The shared generator checks and runs this project's five specs, saves the
ADaM outputs, and invokes the existing reference comparator. It then calls
`submission("adam")` on the same project, validates the XML against the local
Define-XML 2.1 XSDs with network imports disabled, compares all metadata, and
audits the actual derived files against both XML documents.

Outputs:

- `data/adam/<dataset>-yamaa.parquet`: the derived datasets.
- `data/adam/define-yamaa.xml`: generated Define-XML, referencing those files.
- `data/adam/adrg.pdf`: unchanged copy of the source reviewer guide.
- `.build/submission-pilot3-define/report.json`: generation, schema, dataset,
  metadata-comparison, and data-audit results.

The creation time is fixed to the reference instant for reproducible XML.
Dataset entry order follows the reference Define; yamaa schedules execution
by dependencies. The published XML and reference datasets remain unchanged.

## Metadata enforced during derivation

All 216 output variables carry submission metadata in their derivation spec.
The project also declares 15 ADADAS.AVAL value-level entries and 36 codelists.
The normal R/Python project run now checks these metadata constraints.

The declarations account for the executable representation:

- Numeric columns and bound numeric codelists retain the derivation's `float`
  type. Integer-valued floats declare zero decimal places; fractional
  ADADAS.BASE, CHG and PCHG retain 13. Dates keep ADaM date representation.
- Draft character codelists explicitly list the empty string with decode
  `Blank` where the existing outputs use it. These local additions have no NCI
  alias and remain visible in the comparison; blank and null remain distinct.
- ADLBC.VISITNUM is rounded to the codelist's one-decimal precision, removing
  binary transport noise such as `1.2000000000000002`. The original absolute
  comparison tolerance of `1e-10` remains unchanged.
- ADAE.ADURU declares length 4 to accommodate `DAYS`.
- Origins and methods describe the actual sources, recodes, LOCF/planned rows,
  and constants. ADADAS reads subject variables directly from the unique
  ADSL.USUBJID join instead of a lookup alias.

The source XML/XLSX does not state core designations. The draft `core: Cond`
annotations required by yamaa still need ADaMIG review; Core is not emitted
in Define-XML. No CT release is invented from NCI aliases alone.

## Reproduction status

Derivation, data comparisons, composition, XSD validation, and the candidate
data audit must be assessed separately from reference metadata equivalence.
The shared command exits **1** with `incomplete` while any metadata differs,
even when generation and the data checks pass. There is no difference allowlist.

The reference uses Define-XML 2.0 and XPT leaves; yamaa emits 2.1 and references
the derived Parquet files. Remaining differences include executable keys and
mandatory flags, numeric types, actual provenance, explicit blank terms,
ADURU's corrected length, and the 2.1 codelist classification. Every differing
field retains its reference and candidate values in the JSON report.

The independent audit also keeps the reference's data conflicts visible:
fractional values declared integer, ADAE.ASTDT key values missing on 11
records, blank strings absent from its lists, and `DAYS` exceeding length 3.

The comparator resolves OID references, compares every bound method/comment
including shared VLM methods, and checks ordered codelist values/decodes and
all VLM conditions. It accounts for unknown and unused content and refuses
dangling references or duplicate identities. Its documented version/format
normalizations do not waive the remaining differences. The XML is not claimed
to reproduce the original 2.0 file in full, and no XPT transport is generated.
