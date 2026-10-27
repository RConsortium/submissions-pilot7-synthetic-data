# CDISC Pilot 01 Define-XML 2.0 and legacy comparison

The project generates Define-XML 2.0.0 from the same ten YAML specifications
that derive the ADaM datasets. Each dataset has `submission.mode: historical`;
there is no separate submission specification set. The published reference
remains unchanged under `spec/define/define-adam.xml` and uses Define-XML 1.0.0,
ODM 1.2, and the draft ADaMRes analysis-results extension.

The engine is pinned to yamaa commit
`fa2867b68497755023daa4baa4477b34e5cfedc7`, the merged Define-XML 2.0 support.
Use Python 3.12+ and the source checkout's pinned Rust toolchain, 1.99.1.

Run from the repository root:

```bash
python -m pip install --config-settings build-args=--profile=dev -r cdiscpilot01/program/adam/python/requirements-define.txt
git clone https://github.com/elong0527/yamaa.git .build/define-engine
git -C .build/define-engine checkout --detach fa2867b68497755023daa4baa4477b34e5cfedc7
python .github/scripts/generate_define.py cdiscpilot01 --schemas .build/define-engine/rust/tests/schemas
```

The command checks and derives the project, runs the existing strict official
data comparison, composes XML twice with a fixed creation time, and validates
it against the local CDISC 2.0 XSD. It writes:

- `cdiscpilot01/data/adam/define-yamaa.xml`: the generated document;
- `.build/cdiscpilot01-define/comparison.html`: a readable comparison report;
- `.build/cdiscpilot01-define/comparison.json`: every compared field, source
  and target object ID, conversion, difference and coverage gap; and
- `.build/cdiscpilot01-define/report.json`: generation, comparison, package-link
  availability and independent data-audit results.

The Define-XML reproduction workflow uploads these files. A successful job
means that generation, schema validation, data comparison and the approved
comparison scope completed. It does not mean that the legacy file is fully
reproduced or that all metadata fields match. Unexpected differences fail the
job; evidenced inheritance limitations remain different fields in the report.
A failed attempt removes earlier XML and comparison artifacts before recording
the failure.

## Cross-version mappings

The existing 2.0/2.1 comparator remains unchanged. A separate legacy reader
resolves the ODM 1.2 reference and maps its supported fields into the 2.0
comparison structures. Unknown content is a difference. References are checked
by object type, including references inside unsupported analysis results;
the draft permits an analysis result and its computational method to share
an OID, so those identities are not conflated with dataset metadata.

- The legacy header cites the ADaM 2.1 model. The staged data guide explicitly
  says that the current data comply with ADaMIG 1.0. The target cites that guide;
  the report retains both citations rather than calling them the same version.
- Legacy classes ADSL, ADAE and BDS map to SUBJECT LEVEL ANALYSIS DATASET,
  OCCURRENCE DATA STRUCTURE and BASIC DATA STRUCTURE. Each original class and
  its target mapping remains in the report.
- Inline labels, origins, comments and domain keys map to 2.0 descriptions,
  Origin elements, CommentDef objects and ItemRef key sequences.
- Every legacy value-level ItemDef.Name occurs in the dataset's linked
  PARAMCD codelist. That is the evidence for its explicit PARAMCD equality
  clause; an unverified selector remains unresolved and is not guessed.
- Value-list items are ordered by their original OrderNumber. Relative order
  is compared and the original numbers are retained separately. The 2.0 writer
  numbers each list from one, while many legacy lists use larger offsets.

The comparison covers ten datasets, 415 variables, 47 value lists, 903
value-level entries and 58 codelists. Native generation never reads or passes
through the reference XML. It reads the authored YAML metadata; the independent
legacy reader runs afterward as the comparison oracle.

Thirty-six copied columns are expanded from bulk-copy shorthand into equivalent
explicit column declarations so their target-specific historical metadata can
be authored. The resolved execution specifications, physical types, labels,
verifications and keys are unchanged when submission annotations are removed.
The project listing follows the reference's dataset order; derivation results
must continue to pass the original data comparison, including label checks.

## Explicit gaps

The report distinguishes matched, converted, different, unsupported and
unresolved records. It always records `full_reference_reproduced: false`.

- The draft extension's 14 result displays and 18 analysis results, including
  analysis variables, datasets, selection criteria, programming code and
  documentation, are inventoried in full and are not generated.
- Twenty-one additional legacy document leaves remain inventoried, including
  their original parent-directory links. They are not rewritten to invented
  resources or added to the generated package.
- ADLBHY's legacy DomainKeys names LBSEQ, but that variable does not exist in
  the reference dataset. This is an unresolved source declaration. The data
  and XML do not gain an invented column.
- Historical value-level metadata inherits optional parent fields in yamaa.
  The language currently has no clear override for an omitted legacy field.
  This produces 252 SignificantDigits differences and 96 codelist-binding
  differences. Every original absence and inherited target value remains a
  difference with its parent-field evidence; none is counted as matched.
- A schema-valid document can retain received metadata that disagrees with
  the data or with business rules. The audits retain these conflicts. They
  are not complete regulatory or Define-XML business-rule validation; Derived
  origins without separately declared methods remain received declarations.

The original XPT archive links remain literal; this workflow derives Parquet
and does not produce a transport package. The copied data guide is available,
while stylesheet and other link availability are reported separately.
XML formatting, namespaces, generated IDs and provenance also differ from the
legacy file. XML byte identity is not claimed.
