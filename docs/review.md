# Dashboard review guide

**Pilot studies** and **Synthetic data** have separate navigation sections and
[dashboard galleries](studies/index.md). Pilots support review against published
submission packages. [Synthetic workspaces](synthetic/index.md) support source
exploration and development of the EDC-to-submission workflow.

The links beside each study name return to its gallery and open that study's
source folder in this repository. Build evidence remains available in the
expandable reproduction section of pilot pages.

## Compare pilot datasets

The workspace starts with the first three subjects. Open **Subjects** to search
identifiers, choose individual subjects or a larger group, or select all. There
is no subject selection limit. Click outside a picker, move focus outside it,
or press Escape to close it.

**Select domains** opens multiple input datasets. Names include the domain and
description, such as **DM - Demographics**. **Compare outputs** adds output
datasets beside the current output. **Specification** chooses the YAML currently
shown; selecting a column in another output focuses that output's specification.
Previously selected comparisons remain open.

Each table starts with up to ten matching rows. Its **Rows** control independently
selects 10, 25, 50, or 100 rows per page. Use its arrow controls to explore all
remaining records. A subject without events can correctly have no event rows.
Subject-independent lookup tables remain visible. Search matches values across
the displayed datasets and links records with matching subject identifiers.

## Follow columns and resize the workspace

Select an output column to reveal its connected input datasets automatically.
The connection can pass through another derived dataset into its upstream
sources. **Related columns** narrows tables to linked variables while retaining
the subject identifier. **All columns** restores the complete schemas. Manually
selected comparison datasets remain available. Input headers and YAML blocks
also select declared connections. **Clear highlight** restores the manual input
selection and removes the column focus.

Connections include declared values, joins, filters, keys, and ordering. They
describe column dependencies; they do not identify contributing input rows.
Unresolved references are reported above the specification.

Drag the specification separator to change its width, or the horizontal
separator between input and output areas to change their heights. Dataset
panels can be resized using their bottom-right corners or the width buttons in
their headers. Drag a column's right edge to change its width. Focus a separator
and use arrow keys for keyboard resizing. **Reset layout** restores the defaults.
Additional panels can be reached with the area's scrollbars. On a phone, panels
stack vertically.

## Verify documentation observations

Select **Documentation review** in the summary and search a variable, dataset,
document, or phrase in the consistency report. Each observation links relevant
YAML lines and available source evidence. **Open evidence in workspace** opens
the affected dataset with its evidence panel. **Open cited source** goes to the
extracted location; use the retained original to confirm wording and context.

Label differences and missing columns require review. **Not reviewed** identifies
an authored question with a verified source excerpt. **Missing evidence** means
the expected source or excerpt could not be verified. Narrative coverage is
partial. Reference agreement is separate from this report and is not regulatory
validation. See the [verification policy](verification.md).

## Review synthetic workflow readiness

Synthetic workspaces inventory staged ODM archives and show the availability
of source, SDTM, ADaM, and submission-metadata files. Missing stages are shown as
**Not staged**. Archive members, sizes, and repository links help locate source
material. These dashboards describe source availability; they do not claim
successful derivations or passed reference comparisons.

## Share and discuss a review

Copy the browser URL to preserve the specification, subjects, compared datasets,
row-count choices, column focus, searches, and open evidence. **Review comments**
appears below pilot dashboard content with a separate GitHub Discussion for the
focused dataset. GitHub sign-in is required to post. **Copy review context**
includes compared outputs, source revision, and the view link. A review-issue
link remains available if the embedded discussion cannot load.
