# Pilot 6 source documents

[manifest.json](manifest.json) records provenance for the Pilot 6 workbook
and Define-XML files. The Define-XML files moved to `spec/define/`, as in
Pilot 3; their bytes are unchanged.

| Document | Review use |
| --- | --- |
| [pilot6-specs.xlsx](../pilot6-specs.xlsx) | Expected metadata and documented derivations for the Pilot 6 target datasets. |
| [ADaM Define-XML](../define/define-adam.xml) | Published machine-readable analysis metadata. |
| [SDTM Define-XML](../define/define-sdtm.xml) | Published input metadata, shared with CDISC Pilot 01. |
| [Shared study SAP](../../../cdiscpilot01/spec/source/SAP.pdf) | Supporting study definitions; applicability to Pilot 6 remains to be reviewed. |

## Workbook version

The staged workbook matches the upstream snapshot
`a4f85c95cfef1f6aa27795362630f8ae43210185`, Git blob
`8dbbe4fa5ffdf788c55feadc612e6432a8c945b3`, as do the ADaM Define-XML, the
21 SDTM inputs and the 8 ADaM references. It replaces the workbook staged
from commit `a9e83a646ce9773409aef4d268c433e490bae6c2` (Git blob
`b4ea7ab38e001398d5a92f3b35f94e1da460f657`); the ADaM Define-XML is
identical at both commits. [source-snapshot.json](../source-snapshot.json)
records the full snapshot, and the
[upstream R reproduction](../../program/adam/README.md) checks the ADaM
programs on these inputs against the references.

Copying documents does not establish a successful derivation or a passed
reference comparison.

Follow the shared [review and provenance conventions](../../../cdiscpilot01/spec/source/README.md).

Attribution: [R Consortium Pilot 6](https://github.com/RConsortium/submissions-pilot6-adams-tlfs),
based on the CDISC SDTM/ADaM Pilot Project. Upstream terms and notices continue
to apply.
