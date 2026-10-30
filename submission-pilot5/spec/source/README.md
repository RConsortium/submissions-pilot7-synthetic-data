# Pilot 5 source documents

These unchanged documents are retained from the R Consortium Pilot 5 eCTD
submission. [manifest.json](manifest.json) pins their upstream commit, paths,
Git blob IDs, file sizes, and SHA-256 checksums. The workbook is byte-identical
to the copy in the pinned development repository. The existing Define-XML
files are inventoried from that development repository because the pinned
eCTD tree does not contain Define-XML files.

| Document | Review use |
| --- | --- |
| [adam-pilot-5.xlsx](adam-pilot-5.xlsx) | Expected ADaM metadata and documented derivations. |
| [adrg.pdf](adrg.pdf) | Pilot-specific analysis and Dataset-JSON conventions. |
| [ADaM Define-XML](../define/define-adam.xml) | Published machine-readable analysis metadata. |
| [SDTM Define-XML](../define/define-sdtm.xml) | Published input metadata. |
| [Shared study SAP](../../../cdiscpilot01/spec/source/SAP.pdf) | Supporting study definitions; applicability to Pilot 5 remains to be reviewed. |
| [programs/](programs/) | The submission's ADaM programs, byte-identical to `pilot5-submission/pilot5-programs/` in the development repository, which produced the reference datasets. Review findings cite their lines to show how a reference value was computed. |

Source document identity was verified; alignment of the staged
Parquet references was not revalidated. Do not substitute Pilot 3's workbook
for this pilot's source documents.

Follow the shared [review and provenance conventions](../../../cdiscpilot01/spec/source/README.md).

Attribution: [R Consortium Pilot 5 submission](https://github.com/RConsortium/submissions-pilot5-datasetjson-to-fda),
based on the CDISC SDTM/ADaM Pilot Project. Upstream terms and notices continue
to apply.
