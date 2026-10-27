# Shared yamaa layers

CDISC Pilot 01, Submission Pilot 3 and Submission Pilot 5 are three
submission packages of one study, CDISCPILOT01. They read the same SDTM
data, and their ADaM references agree on almost every value. Each fact about
the study is therefore written once, in a layer that every package inherits,
and each package states only what it records differently.

## Layers

```text
spec/yamaa/cdiscpilot01/<dataset>.yaml              study layer
|-- cdiscpilot01/spec/yamaa/<dataset>.yaml          CDISC Pilot 01 entry
`-- spec/yamaa/cdiscpilot01/pilot3/<dataset>.yaml   Pilot 3 layer
    |-- submission-pilot3/spec/yamaa/<dataset>.yaml Pilot 3 entry
    `-- submission-pilot5/spec/yamaa/<dataset>.yaml Pilot 5 entry
```

| Layer | Holds |
| --- | --- |
| Study layer | Inputs, keys, output columns and order, intermediates, and every column's type, label and derivation, as the original CDISC Pilot 01 submission derives them. |
| Pilot 3 layer | What R Submission Pilot 3 changed: renamed or added variables, changed values or labels, and the Define-XML 2.0 metadata that Pilots 3 and 5 both record. Pilot 5 resubmitted the Pilot 3 ADaM as Dataset-JSON. |
| Entry | The dataset's `domain` and the Define-XML metadata only this package records, such as Pilot 5's Dataset-JSON file names. |

## Where a fact goes

1. A rule the packages share goes in the study layer. Where packages wrote
   different rules that produce the same reference values, the study layer
   keeps one: the CDISC Pilot 01 rule, which its reviewed evidence cites.
2. A difference in a package's values, variable names or labels goes in the
   package's layer, with a comment that states the difference.
3. Define-XML metadata goes in the most shared layer whose packages record
   it identically. A column's `submission` block and the root `submission`
   block are written whole, so no layer merges metadata into another's and
   no `clear` is needed.
4. Paths are written from an entry with `relative_to: entry`, so each
   package reads its own staged data and writes its own output.

A study-only dataset, such as CDISC Pilot 01's ADVS, stays in its study's
`spec/yamaa/` folder until a second package needs it.

## Shared datasets

Each file under `cdiscpilot01/` is a shared dataset, and the comments in
its `pilot3/` counterpart state each Pilot 3 change. A dataset without a
study layer is still written in full by each package.

## Reviewing a layered dataset

The study dashboard opens the layer that writes a selected variable's rule,
and its resolved-model view shows the composed specification. In Python,
`yamaa.spec(path).resolve()` returns the same model, with the file that wrote
each value. A change to a layer here affects every package that inherits it, so
validate each of them; pull request CI selects the studies whose
specifications reach the changed layer through `parent` or `include`.
