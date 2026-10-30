# Synthetic analysis review

KN189, KN564 and CAR-T for ALL are synthetic studies with no independent generated ADaM comparison
datasets. The [synthetic data report](../synthetic/index.md) inventories
their staged ODM archives and the availability of source, SDTM, ADaM and
submission-metadata files; missing stages are shown as **Not staged**, and
availability alone does not establish a successful derivation.

## Workspace

KN189 and KN564 open the same linked workspace as the pilot studies: select
subjects, review YAML and data side by side, follow column lineage and open
the retained protocol, SAP and generated metadata under **Source
documents**. [SDTM to ADaM workspace](workspace.md) describes the controls.
CAR-T for ALL also opens a linked specification and data workspace.

## Analysis development

After a successful development build, **Analysis development** adds
**Analysis coverage**, **Findings for review** and **Built datasets**.
Coverage separates supported descriptive scope from partial and unsupported
analyses. Findings distinguish data gaps, measured conflicts and unresolved
decisions; expand a finding for measured counts, representative records,
verbatim protocol and SAP citations and a proposed action, with a link that
opens the cited source line.

Download the study package for Parquet and XPT datasets, both Define-XML
files, the maintained yamaa specifications, the retained source documents and
the exact build evidence. XPT read-back and XML schema checks are distinct
from a comparison with independent generated ADaM datasets or regulatory validation.

## Review drafts

Use the search and type filter to focus a review. Enter a decision draft and
notes, then **Export review draft** to retain them as JSON. Drafts stay in
the current browser and build until exported; they do not resolve findings or
approve datasets. Share an exported draft through a
[GitHub issue](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/new).
Apply agreed specification or data changes, then rebuild before claiming
analysis readiness. Primary efficacy records remain unapproved while their
governing decisions are open.
