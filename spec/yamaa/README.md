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
