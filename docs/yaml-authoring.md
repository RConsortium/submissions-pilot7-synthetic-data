# Writing and reviewing yamaa specifications

A specification should make its clinical intent, record selection and missing
value policy easy to inspect. Use the study's pinned yamaa engine and keep
independent reference datasets and comparison policies intact.

## Start from the rule

For each consequential derivation, identify the input grain, output grain,
eligible records, ordering and tie policy, missing-value behavior and source
document clause. A fixed study decision, such as a retained site-pooling list,
needs its rationale. Agreement with published data does not settle a conflict
between the data, SAP and Define-XML.

Keep source-backed review questions in `spec/review/questions.json`. For a
documented-rule assessment, use the existing claims, probes, adjudication and
issue files under `spec/review/`; follow the [verification policy](verification.md).
An interpretation still awaiting a reviewer remains visible as an open issue.

## Reuse an established contract

Use `copy` for same-named subject-level columns whose type, label and submission
content metadata agree with their producer:

```yaml
input:
  ADSL:
    path: ../../data/adam/adsl-yamaa.parquet
    schema: adsl.yaml
    key: [STUDYID, USUBJID]

columns:
  - copy:
      dataset: ADSL
      columns: [AGE, SEX, TRTSDT, TRTEDT]
```

This is an excerpt from a dataset specification. Keep its other columns,
declared keys and explicit `output.columns`. A renamed variable, a changed
label or an additional transformation needs its own column declaration.

Use `parent` for a complete dataset template, `include` for cohesive shared
derivations and named `windows` for repeated grouping, ordering and selection.
Keep a shared recoding dictionary in a file named by `mapping.dict`. Read the
[schema introduction](https://elong0527.github.io/yamaa/articles/schema-intro/)
before moving paths or overriding inherited mappings: omitted mapping members
can remain inherited, and paths retain their declaring-file semantics.

Give helper columns names describing their purpose. Keep them in dependency
order; `output.columns` selects the delivered fields and their presentation
order. Review the engine's resolved model when composing specifications.

The three pilots use the repository's
[shared contracts](https://github.com/RConsortium/submissions-pilot7-synthetic-data/tree/main/spec/yamaa).
The ADSL parent shares demographics, while study-local fragments define
exposure, baseline, and populations. Analysis datasets inherit the generated
ADSL contract. CDISC Pilot 01 additionally shares its laboratory construction
within that study. Output columns, clinical differences, and original missing
values remain explicit in the study entries. Shared paths use `relative_to:
entry`; use `clear` before restating an inherited ordered mapping in full.

## State clinical invariants

Use existing verifications for meaningful requirements, for example:

```yaml
verifications:
  - assert:
      id: treatment_date_order
      when: TRTSDT IS NOT NULL AND TRTEDT IS NOT NULL
      require: TRTEDT >= TRTSDT
```

Document the intended behavior for missing dates, unmatched subjects, unmapped
categories, baseline ties and generated records. Use stable verification IDs.
Warnings require an `output.report` so their evidence is retained. Avoid a
permissive fallback that hides a rule requiring investigation.

Keep rounding conventions explicit. `FLOOR(x * 10 + 0.5) / 10` and rounding
half away from zero differ for negative values; replacing one requires checking
the documented rule and boundary cases.

## Check a change

Run the existing `lint()` and `check()` tools with the pinned engine; generated
JSON Schemas provide editor field completion, while engine checks establish
binding and expression validity. Expression fields read bare names as variables
and quoted expression text as literals, for example `derivation: "'Y'"`.
Study validation now requires both the study YAML and shared library to pass
the pinned engine's authoring checks.

For a refactor, compare the derived tables before and after the change,
including types, labels, column order, row order and missing values, and run
`python .github/scripts/validate_yamaa.py <study>` against the independent
reference. Refresh validation and reviewed-derivation evidence before building
the website. See the [review guide](review.md) for source and resolved-model views.

## Turn a pilot pattern into a benchmark

Contribute benchmark cases to the
[yamaa benchmark repository](https://github.com/elong0527/yamaa/tree/main/benchmarks).
Keep one derivation idea per case, with independently authored expected results.
State the clinical rule, input and output grain, missing policy and tie policy.
Explain the purpose of unusual input rows and pair high-risk cases with their
boundary or failure examples. Link the example from the pilot specification's
review evidence. Revisit implementation-workaround comments when the pinned
engine gains support for a construct.
