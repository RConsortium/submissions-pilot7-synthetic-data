# Source documents for derivation review

These unchanged documents originate from the CDISC SDTM/ADaM Pilot Project.
[manifest.json](manifest.json) records the upstream repositories, exact
commits, paths, Git blob IDs, file sizes, and SHA-256 checksums. Paths in all
four study manifests are relative to the Pilot 7 repository root.

| Document | Review use |
| --- | --- |
| [dataguide.pdf](dataguide.pdf) | Selected derivation explanations, including AE date imputation, occurrence flags, visit selection, LOCF, and NPI-X parameters. |
| [SAP.pdf](SAP.pdf) | The original study SAP, retained from Pilot 6's `documents/SAP.pdf`: populations, endpoints, assessment windows, and missing-data conventions. |
| [ADaM Define-XML](../define/define-adam.xml) | Published dataset, variable, value-level, and derivation metadata. |
| [SDTM Define-XML](../define/define-sdtm.xml) | Published input metadata and traceability context. |
| [programs/adae.sas](programs/adae.sas) | The only ADaM program the submission package publishes. |
| [programs/pilot6/](programs/pilot6/) | R Consortium Pilot 6's R programs, a later reimplementation that reproduces these reference datasets. They show how a reference value can be computed, not what the original authors intended. |

The SAP is stored once here and referenced by Pilots 3, 5, and 6. Its
applicability must be reviewed against each pilot's own workbook,
Define-XML, and reviewer guide. A shared study does not establish identical
derivations across pilots. The data guide is from the updated analysis
submission; the SAP predates that update.

## Provenance and updates

The import verified each copied file's Git blob ID against the pinned
upstream tree. Existing Define-XML files are also inventoried, without
changing their bytes. This establishes document identity; conversion and
alignment of the staged Parquet reference data were not revalidated.

Update a document and its manifest together after reviewing its relationship
to the staged inputs and ADaM references. Keep original PDF/XLSX contents
unchanged. Maintained notes use ASCII.

Attribution: [CDISC SDTM/ADaM Pilot Project](https://github.com/cdisc-org/sdtm-adam-pilot-project)
and [R Consortium Pilot 6](https://github.com/RConsortium/submissions-pilot6-adams-tlfs).
Upstream terms and notices continue to apply.
