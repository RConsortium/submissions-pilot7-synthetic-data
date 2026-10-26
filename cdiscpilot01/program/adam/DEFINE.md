# CDISC Pilot 01 Define-XML assessment

The current yamaa specifications do not reproduce the published ADaM
Define-XML. They reproduce the ten ADaM datasets, but lack the metadata needed
to compose a Define-XML document. Exact reproduction also requires a format
and analysis-results extension that yamaa does not generate.

This assessment covers [define-adam.xml](../../spec/define/define-adam.xml)
and the ten specifications in [project.yaml](../../spec/yamaa/project.yaml),
using the source revision pinned in [python/requirements.txt](python/requirements.txt):
`3e8d5f6b5d2af223fba6aa29fa7209699123f706` (`1.0.0rc1`). The SDTM reference
has 22 datasets, but the project has no SDTM specification section; SDTM
Define-XML generation was not attempted.

## Repeat the checks

After the setup in [README.md](README.md), run from the repository root:

```bash
python cdiscpilot01/program/adam/python/assess_define.py
python .github/scripts/validate_yamaa.py cdiscpilot01
```

The first command currently exits 1. It writes
`.build/define/cdiscpilot01-assessment.json`, inventories the reference, and
records the engine's structured diagnostics for two composition calls:

| Call | Observed result |
| --- | --- |
| Unmodified study project | Three `missing_required_field` issues under DEFINE-28: `study`, `adam.standards`, `adam.define`. |
| Temporary project with those fields | Ten `submission_metadata_missing` issues under DEFINE-7, one for each dataset. |

The temporary project reads the study identity from the reference and uses
ADaMIG 1.0 solely to reach the next diagnostic. It does not establish an
approved implementation-guide version or change the production project.
Its unsaved Define target is beside the derived Parquet files, as DEFINE-16
requires dataset artifacts to be inside the document's package directory.
Neither composition calls `save()`, imports column metadata, or writes XML.
The report distinguishes authored metadata blocks from metadata that an
engine might inherit or infer.

The second command builds, saves, and compares the ten ADaM outputs. It passed
all 415 columns and 9,119,605 cells against the official references with the
existing comparison policy. This is evidence for the datasets only; it does
not validate Define-XML generation.

## Reference coverage and gaps

| Published ADaM reference content | Count | Current generation input |
| --- | ---: | --- |
| Dataset definitions | 10 | All ten specs lack dataset `submission` metadata. |
| Dataset variables | 415 | Output names and column order match; no column `submission` blocks are authored. |
| Value lists | 47 | No `submission.value_level` declarations. |
| Value-level item references | 903 | No declared selection conditions or per-value metadata. |
| Codelists | 58 | No project codelist files or submission bindings. |
| Draft analysis-result displays | 14 | Outside yamaa's Define-XML profile. |
| Draft analysis results | 18 | Outside yamaa's Define-XML profile. |

The reference has 1,318 `ItemDef` elements: 415 dataset variables plus 903
value-level definitions. Counting every `ItemDef` as an output variable
would overstate dataset coverage. The assessment counts dataset `ItemRef`
and value-list `ItemRef` entries separately.

The published file declares ODM 1.2, Define-XML 1.0.0, and the
`http://www.cdisc.org/ns/ADaMRes/DRAFT` extension. yamaa generates ODM 1.3.2
and Define-XML 2.1, not the original bytes or namespaces.
[DEFINE-26 at the tested revision](https://github.com/elong0527/yamaa/blob/3e8d5f6b5d2af223fba6aa29fa7209699123f706/rules/profiles/define-xml.md#define-26)
explicitly excludes analysis-results metadata. Value-level metadata and
codelists are supported by yamaa, but have not been declared for this study.

## Work needed for a generated candidate

1. Declare the study and section metadata and author dataset/column submission
   metadata: classes, structures, origins, methods, lengths, formats,
   codelists, value-level selection conditions, and supporting documents.
   Review these against the original documents and executable derivations;
   copying a reference comment alone does not establish consistency.
2. Save a separate Define-XML 2.1 candidate beside the derived artifacts.
   Preserve both published XML files under `spec/define/`.
3. Validate the candidate against the Define-XML 2.1 XSD and compare its study,
   datasets, keys, ordered variables, labels, types, origins, methods,
   codelists, value-level metadata, and document links with the reference.
   Treat version conversions and unsupported content as explicit differences.

Reproducing the original Define-XML 1.0 document with its draft analysis-results
extension requires support beyond the current yamaa profile. No candidate XML,
XML schema validation result, stylesheet rendering result, or semantic
equivalence is claimed by this assessment.
