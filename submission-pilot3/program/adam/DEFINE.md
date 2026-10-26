# Pilot 3 Define-XML generation

The workflow generates a schema-valid Define-XML 2.1 candidate with yamaa.
It covers all five datasets, 216 dataset variables, 15 ADADAS.AVAL value-level
definitions, and 36 codelists in the published ADaM Define-XML.
It does not yet reproduce that Define-XML's metadata in full.

The reference under `spec/define/define-adam.xml` remains unchanged. The
submission layers under `spec/yamaa/submission/` inherit the executable
specifications and declare the export metadata separately. Metadata was
transcribed from the preserved reference, including methods, comments,
terminology aliases, dictionary versions, and the reviewer guide link. The
runtime generator never reads the reference to construct its output; the
independent comparator reads it only after generation.

The draft layers use `core: Cond`, a field required by yamaa but absent from
both the published Define-XML and its Excel source. Core is not written to
Define-XML. These declarations require ADaMIG review and are not a claim of
approved standard core designations.

## Run

Use the engine revision already pinned for Pilot 3:
`3e8d5f6b5d2af223fba6aa29fa7209699123f706` (`1.0.0rc1`).
From the repository root:

```bash
python -m pip install -r submission-pilot3/program/adam/python/requirements-define.txt

# The authoritative CDISC XSDs are retained in the tested yamaa source.
git clone https://github.com/elong0527/yamaa.git .build/pilot3-define-schema-source
git -C .build/pilot3-define-schema-source checkout --detach 3e8d5f6b5d2af223fba6aa29fa7209699123f706

python submission-pilot3/program/adam/python/generate_define.py \
  --schemas .build/pilot3-define-schema-source/rust/tests/schemas
```

The generator:

1. Runs the original ADaM project and its existing reference comparator.
2. Copies the derived Parquet artifacts and unchanged ADRG into
   `.build/pilot3-define/data/`.
3. Checks the submission layers and composes `data/define.xml` with
   `project.submission("adam")`. The creation time is fixed for reproducible XML.
4. Validates against the local CDISC Define-XML 2.1 XSD bundle with network
   imports disabled.
5. Resolves XML references and compares study and dataset metadata, ordered
   variables, keys, types, lengths, precision, formats, labels, origins,
   methods, comments, codelists, value-level definitions, and document links.
6. Audits the candidate metadata and the reference metadata against the
   derived artifacts. Writes `.build/pilot3-define/report.json`.

The current exit code is **1**, with status `incomplete`. Generation and XSD
validation succeed, but equivalence and data conformance do not. No option
ignores these differences. A failed attempt replaces the previous report;
the generator removes the previous XML before starting.

This is a metadata-only export. It references the copied Parquet files;
it does not create XPT files. A successful composition does not establish that
running the submission layers passes yamaa's data checks. The original
ADaM derivations and comparison policy remain separate and unchanged.

## Remaining differences

The first complete comparison found 133 unequal metadata fields. The JSON
report records every reference and candidate value, with no allowlist.

| Area | What remains |
| --- | --- |
| Format | The reference is Define-XML 2.0 from Pinnacle 21; yamaa emits 2.1. Root representation differences are retained in the report. |
| Terminology classification | 2.1 marks the 35 item codelists as non-standard because the source supplies no CT publishing-set/version declaration. NCI aliases and all coded values/decodes are retained; aliases alone do not establish a terminology release. |
| Files | The five dataset leaves name generated Parquet files instead of the reference XPT files. The ADRG link resolves to an unchanged copy. |
| Keys | yamaa's executable keys differ from the published descriptive keys and require non-missing values. The reference marks every variable optional, including its keys; ADAE.ASTDT is a declared reference key but is missing on 11 records. |
| Numeric types | Reference ADADAS.BASE, CHG and PCHG are declared integer, but have fractional values on 17, 36 and 2,084 records respectively. The candidate retains float values and declares 13 decimal places; it does not truncate the values. |
| Origins and methods | The faithful transcription initially produced 35 origin-refutation issues. The candidate describes the executable sources, recodes, planned rows, LOCF and assigned constants. Every resulting difference from the published origins and methods remains in the report. |

For ADADAS's subject variables, the submission layer reads ADSL directly
through its declared USUBJID key rather than through the parent specification's
ADSL_LOOKUP alias. It retains the analysis-window lookup. This permits
Predecessor metadata for the direct copy; it does not change the original
project or the artifacts the metadata-only export copies.

The comparison resolves generated OIDs by their bindings, collapses prose
whitespace, and maps the documented 2.0/2.1 representations of classes,
implementation guides, English text, and Sponsor origins. It compares a shared
method at every variable/value-level binding. Unknown XML content, dangling
references, duplicate identities, missing definitions, and extra definitions
cannot produce an equivalence pass. Coded values and expression code retain
their content. These normalizations do not waive the remaining differences.

## Data conformance findings

The candidate's data audit reports seven conflicts:

- Empty strings outside the bound codelist in ADSL.DCSREAS and ADLBC.DSRAEFL,
  AVISIT, BNRIND and LBNRIND. The audit preserves the distinction between empty
  strings and nulls rather than expanding the published terminology.
- 120 ADLBC.VISITNUM values differ from their decimal codelist values at binary
  floating-point precision, for example `1.2000000000000002` versus `1.2`.
  The audit does not round clinical values or add near-duplicate codes.
- ADAE.ADURU has declared length 3, but contains `DAYS` on 718 records.

The separate audit of the published reference metadata additionally records
the three integer/fraction conflicts and the missing ADAE key described above.
All 2,291,147 cells still pass the original five-dataset comparison under its
existing numeric tolerance and missing-character policy.

Full reproduction requires resolving these metadata decisions and the target
format. Schema validity and complete inventory coverage are established;
metadata equivalence and a conformant submission package are not.
