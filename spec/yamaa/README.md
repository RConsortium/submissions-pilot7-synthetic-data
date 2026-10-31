# Shared yamaa templates

CDISC Pilot 01, Submission Pilot 3 and Submission Pilot 5 are three
submission packages of one study, CDISCPILOT01. They read the same SDTM
data, and their ADaM references agree on almost every value. Each fact about
the study is therefore written once, in a pilot program template that the
studies inherit, and each study states only what its package records
differently.

## Templates

`pilot-program/` holds one template per dataset, in versions where packages
derive a dataset differently. Version 1 holds what every package publishes,
in CDISC Pilot 01's rules. Each later version inherits the version it
changes and adds or changes what one package publishes. A study's entry
inherits the version its package submitted.

For most datasets every package publishes the same rows, so version 1 is
all of CDISC Pilot 01's dataset and version 2 is what R Submission Pilot 3
changed:

```text
spec/yamaa/pilot-program/<dataset>_v1.yaml         CDISC Pilot 01 version
|-- cdiscpilot01/spec/yamaa/<dataset>.yaml
`-- spec/yamaa/pilot-program/<dataset>_v2.yaml     R Submission Pilot version
    |-- submission-pilot3/spec/yamaa/<dataset>.yaml
    `-- submission-pilot5/spec/yamaa/<dataset>.yaml
```

CDISC Pilot 01's ADLBC also publishes 18 shift parameters that the R
Submission Pilots do not. Version 1 holds the 18 chemistry parameters every
package publishes, version 2 adds the shift parameters, and version 3 is what
R Submission Pilot 3 changed:

```text
spec/yamaa/pilot-program/adlbc_v1.yaml             chemistry parameters
|-- spec/yamaa/pilot-program/adlbc_v2.yaml         CDISC Pilot 01 version
|   `-- cdiscpilot01/spec/yamaa/adlbc.yaml
`-- spec/yamaa/pilot-program/adlbc_v3.yaml         R Submission Pilot version
    |-- submission-pilot3/spec/yamaa/adlbc.yaml
    `-- submission-pilot5/spec/yamaa/adlbc.yaml
```

CDISC Pilot 01 names the ADAS-Cog dataset ADQSADAS and the R Submission
Pilots name it ADADAS. Pilots 3 and 5 publish the same records in different
orders, so version 2 is what R Submission Pilot 3 changed and version 3 is the
key order of Pilot 5's Dataset-JSON resubmission:

```text
spec/yamaa/pilot-program/adadas_v1.yaml            CDISC Pilot 01 version
|-- cdiscpilot01/spec/yamaa/adqsadas.yaml
`-- spec/yamaa/pilot-program/adadas_v2.yaml        R Submission Pilot 3 version
    |-- submission-pilot3/spec/yamaa/adadas.yaml
    `-- spec/yamaa/pilot-program/adadas_v3.yaml    R Submission Pilot 5 version
        `-- submission-pilot5/spec/yamaa/adadas.yaml
```

| File | Holds |
| --- | --- |
| `<dataset>_v1.yaml` | Inputs, keys, output columns and order, intermediates, and every column's type, label and derivation for what every package publishes, as the original CDISC Pilot 01 submission derives them. |
| A later version | Inherits the version it changes and states what one package adds or changes. CDISC Pilot 01's version adds the rows only it publishes. The R Submission Pilot version states what Pilot 3 changed: renamed or added variables, changed values or labels, and the Define-XML 2.0 metadata that Pilots 3 and 5 both record. Pilot 5 resubmitted the Pilot 3 ADaM as Dataset-JSON. |
| A study's entry | The dataset's `domain` and the Define-XML metadata only its package records, such as Pilot 5's Dataset-JSON file names. |

## Where a fact goes

1. A rule the packages share goes in version 1. Where packages wrote
   different rules that produce the same reference values, version 1 keeps
   one: the CDISC Pilot 01 rule, which its reviewed evidence cites.
2. A difference in a package's values, variable names or labels, and a row
   only one package publishes, goes in a later version, with a comment that
   states the difference. A layer cannot remove an inherited row template or
   column, so version 1 never holds what one package leaves out. A new
   version is added only when a package needs it, and inherits the version it
   changes.
3. Define-XML metadata goes in the most shared file whose packages record
   it identically. A column's `submission` block and the root `submission`
   block are written whole, so no file merges metadata into another's.
4. Paths are written from an entry with `relative_to: entry`, so each study
   reads its own staged data and writes its own output.

A study-only dataset, such as CDISC Pilot 01's ADVS, stays in its study's
`spec/yamaa/` folder until a second package needs it.

## Working columns

A working column is a column that the output does not list. Write one only
where yamaa needs a named value:

1. A verb argument that takes a variable name, such as the `source` of
   `round_half_away_from_zero`, `impute` or `str_extract`, the `start` and
   `end` of `diff`, a window's `group_by` or `order_by`, and `output.order_by`,
   when the value is a computed one rather than a column or a lookup field.
   `BMIBL_RAW` holds the unrounded BMI that `BMIBL` rounds.
2. A verb result that an expression reads, such as `DURDIS_DAYS`, which
   `DURDIS_RAW` divides into months, or a `row_number` that a flag tests.
3. A missing value replaced by 0, written as a `case`, because the expression
   language has no `COALESCE`, such as `_CUM0`.
4. A value that each row template sets differently and later columns read.

Everything else goes where it is used:

- Read a lookup field directly, in an expression or as a verb's `source`:
  `impute: {source: SV8.SVSTDTC}`, not a copy of `SV8.SVSTDTC` in its own column.
- Write a verb inside the `case` branch that uses it, such as the `mapping`
  in `DCREASCD`'s `otherwise`, or the rounding in ADLBC's `_U_AVAL`.
- Round only with `round_half_away_from_zero`, the one rounding of yamaa
  (FORMULA-16), never with `FLOOR(x * 10 + 0.5) / 10`. Its `source` is a
  variable name, so a computed value it rounds is the one working column
  that rounding needs.

Label a working column with what it holds. Validate every study that
inherits a template after removing one, and update review claims that quote
it.

## Shared datasets

Each file under `pilot-program/` is a shared dataset version, and the
comments in a later version state each change from the version it
inherits. A dataset without a template is still written in full by each
study.

## Reviewing a layered dataset

The study dashboard opens the file that writes a selected variable's rule,
and its resolved-model view shows the composed specification. In Python,
`yamaa.spec(path).resolve()` returns the same model, with the file that wrote
each value. A change to a template affects every study that inherits it, so
validate each of them; pull request CI selects the studies whose
specifications reach the changed file through `parent` or `include`.

## Saved resolved specifications

Each active study keeps one generated yamaa specification per project dataset in
`<study>/spec/yamaa/resolved/`, preserving any `sdtm/` or `adam/` subfolder.
For example, Pilot 01's ADAE is
`cdiscpilot01/spec/yamaa/resolved/adae.yaml`. It starts with `yamaa` and
`type: spec`, combines all parent layers and includes, and retains the final
column rules and metadata. It has no `parent` or `include` directives.
Input/output paths are rebased to its location, and producer schemas point
to the corresponding composed files. `resolved/project.yaml` preserves the
project settings and points to these generated specifications.

Each YAML file has a separate `<dataset>.inspection.json` record containing
the engine's full resolution, mapping order, origins, layers and resource
locations. The record also holds the exact engine revision, hashes of the
generated YAML and project, and hashes of the source inputs, including shared
templates, producer schemas and project codelists. The JSON inspection record
is not itself a yamaa specification.

Install the study's pinned engine, then regenerate after a specification,
project or engine-pin change:

```bash
python .github/scripts/resolved_specs.py cdiscpilot01
python .github/scripts/resolved_specs.py cdiscpilot01 --check
```

Omit the study argument to process every active project. Commit the generated
snapshots with the source change. Validation checks them against fresh engine
resolution before execution; missing, changed or obsolete snapshots fail the
check. Resolving reads no clinical data and runs no project code.

Dataset execution and native Define-XML generation use `resolved/project.yaml`.
Downstream label comparisons, document-rule review, transport metadata readers
and dashboard publication use the saved model and its inspection record.
Validation evidence identifies each snapshot by path and SHA-256, and
publication refuses changes after validation. Downstream readers verify source
hashes and do not compose the YAML language themselves.

The generator calls `project.spec(name).resolve()` to compose the source
layers; it does not merge parents itself. That API returns an inspection
envelope. The generator writes its composed `specification` as ordinary YAML,
rebases the engine-recorded resource paths and uses engine diagnostics to
restore the mandatory shorthand that normalization expanded (SCHEMA-15).
Every generated project must pass the pinned engine's `check()` before its
files are saved. The inspection envelope stays in the JSON record.

Edit the source layers and regenerate, then commit both the YAML and JSON.
Do not edit the generated files directly.

## Why documented-rule specifications are separate

`<study>/spec/review/adae-documented-rules.yaml` is an executable check of the rules
cited in `adae-claims.json`, not the production ADAE specification. It starts
from published reference rows and recomputes selected variables using the
documented inputs and rules. For ADAE, these include analysis dates, inclusive
duration, treatment emergence, first-occurrence flags and the dermatologic
query. Alternative readings have separate output columns, such as the
corrected SOC spelling used by `CQ01NAM`.

`verify_derivations.py` checks the citations, runs the documented rules with the pinned
engine, and compares its results with both the independent published reference
and the production output. This can reveal a documented rule that disagrees
with the reference even when production reproduces every reference value.
Reference values used for other variables keep each check focused on the selected
rule; it is not an independent end-to-end derivation. Claims and adjudication
record the reading and remaining review decisions. Keep these checks independent of
the production specification and its resolved snapshot.
