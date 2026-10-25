# Pilot 6 source documents

[manifest.json](manifest.json) records provenance for the existing Pilot 6
workbook and Define-XML files. They retain their current paths and bytes.

| Document | Review use |
| --- | --- |
| [pilot6-specs.xlsx](../pilot6-specs.xlsx) | Expected metadata and documented derivations for the Pilot 6 target datasets. |
| [ADaM Define-XML](../define-adam.xml) | Published machine-readable analysis metadata. |
| [SDTM Define-XML](../define-sdtm.xml) | Published input metadata, shared with CDISC Pilot 01. |
| [Shared study SAP](../../../cdiscpilot01/spec/source/SAP.pdf) | Supporting study definitions; applicability to Pilot 6 remains to be reviewed. |

## Workbook version

The staged workbook matches upstream commit
`a9e83a646ce9773409aef4d268c433e490bae6c2`, Git blob
`b4ea7ab38e001398d5a92f3b35f94e1da460f657`. The ADaM Define-XML also matches
that commit. At the inspected upstream snapshot
`a4f85c95cfef1f6aa27795362630f8ae43210185`, the workbook has Git blob
`8dbbe4fa5ffdf788c55feadc612e6432a8c945b3` and different bytes.

The newer workbook is not substituted for the staged version. Review its
changes together with the corresponding input and ADaM reference snapshot
before an update. The manifest records both versions to make the difference
explicit; alignment of the staged Parquet data was not revalidated.

Copying documents does not establish a successful derivation or a passed
reference comparison.

Follow the shared [review and provenance conventions](../../../cdiscpilot01/spec/source/README.md).

Attribution: [R Consortium Pilot 6](https://github.com/RConsortium/submissions-pilot6-adams-tlfs),
based on the CDISC SDTM/ADaM Pilot Project. Upstream terms and notices continue
to apply.
