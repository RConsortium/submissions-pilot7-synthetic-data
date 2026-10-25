# Dashboard review guide

**Pilot studies** and **Synthetic data** have separate navigation sections and
[dashboard galleries](studies/index.md). Pilots support review against published
submission packages. [Synthetic workspaces](synthetic/index.md) support source
exploration and development of the EDC-to-submission workflow.

The links beside each study name return to its gallery and open that study's
source folder in this repository.

## Compare pilot datasets

The workspace starts with the first three subjects. Open **Subjects** to search
identifiers, choose individual subjects or a larger group, or select all. There
is no subject selection limit. Click outside a picker, move focus outside it,
or press Escape to close it.

**Select domain** opens multiple input datasets. Names include the domain and
description, such as **DM - Demographics**. The output **Select domain** control adds output
datasets beside the current output. **Specification** chooses the YAML currently
shown; selecting a column in another output focuses that output's specification.
Previously selected comparisons remain open.

Each table starts with up to ten matching rows. Its **Rows** control independently
selects 10, 25, 50, or 100 rows per page. Use its arrow controls to explore all
remaining records. Table heights grow to show the selected page without an inner
vertical scrollbar; scroll the page to review larger row counts. A subject without events can correctly have no event rows.
Subject-independent lookup tables remain visible. Search matches values across
the displayed datasets and links records with matching subject identifiers.

## Follow columns and resize the workspace

Select an output column to reveal its connected input datasets automatically.
The connection can pass through another derived dataset into its upstream
sources. **Related columns** narrows tables to linked variables while retaining
the subject identifier and declared keys. Purple **Key** badges and cells identify
keys from each dataset's Define-XML or yamaa specification. An **ID** badge marks
the configured subject identifier when no key is declared. Blue marks the selected
column and amber marks related columns; keys keep their purple background. **All columns** restores the complete schemas. Manually
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

The **Consistency review** tab follows **Review workspace**. Its table compares
**Input -> output logic** and **Source documents** with the derived datasets.
Search a variable, dataset, document, or phrase, or filter the comparison and
review status. Each row shows the yamaa rule, observed dataset values, source
information and the difference or remaining review task. **Executed** records a
yamaa build and its separate independent-reference result; it does not establish
that the original rule was interpreted correctly.

**Open evidence in workspace** opens the affected dataset and variable with its
evidence panel and derived output. **View source** opens the cited document
inside the website. Old Dataset overview and findings links lead to this table.

Label differences and missing columns require review. **Not reviewed** identifies
an authored question with a verified source excerpt. **Missing evidence** means
the expected source or excerpt could not be verified. Narrative coverage is
partial. Reference agreement is separate from this report and is not regulatory
validation. See the [verification policy](verification.md).

## View source documents

Use **Source documents** to select a retained document. PDF pages display in the
browser viewer with their original tables and layout. Excel workbooks display
sheet tables with row numbers, column letters and merged cells; formulas are
shown as entered. XML displays the HTML produced by the publisher's retained
stylesheet. Original files remain available through **Original document**.

Where available, choose **Extracted reading copy** for searchable text and exact
citation locations. The selected document, view and cited location are included
in the review URL. Missing documents remain explicitly unavailable.

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
