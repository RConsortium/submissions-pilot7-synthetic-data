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

The SAP is stored once here and referenced by Pilots 3, 5, and 6. Its
applicability must be reviewed against each pilot's own workbook,
Define-XML, and reviewer guide. A shared study does not establish identical
derivations across pilots. The data guide is from the updated analysis
submission; the SAP predates that update.

## Review inventory

[rule-coverage.csv](../validation/rule-coverage.csv) is a starter inventory,
not a complete extraction of the source documents. Each row identifies a
source location, an existing yamaa specification where available, and a
proposed independent check. PDF page numbers count from the first PDF page.
ADQSADAS and ADQSCIBC remain outside the active yamaa project.

Every initial row has `review_status=pending_review` and
`check_status=not_implemented`. A blank `yamaa_spec` means no active
specification is staged for that dataset. The existing build and reference
comparison checks do not execute these proposed rule checks.

Before implementing a check, a statistical programmer or biostatistician
must confirm the source interpretation, exact scope, and expected result.
Document conflicting sources or reference behavior for review; preserve
published data, Define-XML, and the established comparison policies.
Report source review, rule-check coverage, successful builds, and reference
agreement separately. Reference agreement is not regulatory validation.

## Provenance and updates

The import verified each copied file's Git blob ID against the pinned
upstream tree. Existing Define-XML files are also inventoried, without
changing their bytes. This establishes document identity; conversion and
alignment of the staged Parquet reference data were not revalidated.

Update a document and its manifest together after reviewing its relationship
to the staged inputs and ADaM references. Keep original PDF/XLSX contents
unchanged. Maintained notes and review inventories use ASCII.

Attribution: [CDISC SDTM/ADaM Pilot Project](https://github.com/cdisc-org/sdtm-adam-pilot-project)
and [R Consortium Pilot 6](https://github.com/RConsortium/submissions-pilot6-adams-tlfs).
Upstream terms and notices continue to apply.
