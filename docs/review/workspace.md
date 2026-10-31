# SDTM to ADaM workspace

The **SDTM -> ADaM** tab of a study shows an output dataset, the SDTM inputs
its derivations read and the yamaa specification that produced it, side by
side for the selected subjects. The pilot studies and the KN189 and KN564
synthetic studies share this workspace.

## Subjects and datasets

The workspace starts with the first three subjects. **Subjects** searches
identifiers, selects individual subjects or a larger group, or selects all;
there is no selection limit. Click outside a picker, move focus outside it or
press Escape to close it.

The dataset tabs choose the output dataset. **Select domain** under the input
area opens further input datasets, named by domain and description, such as
`DM - Demographics`; the output area's **Select domain** adds output
datasets beside the current one. **Output dataset type** switches a pilot
output between the yamaa-derived dataset and the generated ADaM datasets.
**Specification** chooses the YAML currently shown; selecting a column in
another output focuses that output's specification. Comparisons you opened
stay open.

## Tables

Each table starts with up to ten matching rows. Its **Rows** control selects
10, 25, 50 or 100 rows per page, and its arrows page through the remaining
records. Table heights grow to show the selected page without an inner
scrollbar; scroll the page for larger row counts. A subject without events
can correctly have no event rows, and subject-independent lookup tables stay
visible. **Search records** matches values across the displayed datasets and
links records with matching subject identifiers. Missing values are shown as
a dash.

## Column lineage

Select an output column to reveal the input datasets and columns it depends
on; the connection can pass through another derived dataset into its
upstream sources. **Related columns** narrows every table to the linked
variables while keeping the subject identifier and declared keys; **All
columns** restores the complete schemas. Blue marks the selected column and
amber the related columns. Purple **Key** badges mark keys declared in each
dataset's Define-XML or yamaa specification, and an **ID** badge marks the
configured subject identifier when no key is declared. Input headers and
YAML blocks also select declared connections. **Clear highlight** removes the
column focus and restores the manual input selection.

Connections include declared values, joins, filters, keys and ordering. They
describe column dependencies, not the input rows that contributed to a
value. Matching keys are included only for the input or lookup a derivation
reads, so unused inputs and sibling lookup fields do not become sources of
every column. Row filters, grouping and lookup selection order stay in the
trace; final output sorting adds no value dependency. For example, `TRT01AN`
traces to DM, while an exposure-derived `TRTSDT` also opens EX. Unresolved
references are reported above the specification.

## Specification view

With a column selected, the YAML pane shows only the upstream rules needed
to derive it: it hides `output.columns`, keeps the relevant input
declarations and intermediate definitions, and narrows column, row and
intermediate derivations to related entries. The selected definition is
highlighted, omitted line ranges are marked, and composed line numbers are
kept. **All columns** or **Clear highlight** restores the complete specification.

The pane shows the **yamaa specification**. The composed YAML combines
inherited declarations, copied producer columns and named windows, and it
passes the pinned engine's checks. Its file is under the study's
`spec/yamaa/resolved/`, with the engine's inspection record beside it as
`*.inspection.json`. **Open source** opens the complete composed file in the
repository. For authoring conventions, see
[Writing specifications](../yaml-authoring.md).

## Layout

Drag the specification separator to change its width, or the horizontal
separator between the input and output areas to change their heights.
Dataset panels resize from their bottom-right corners or the width buttons
in their headers, and a column resizes from its right edge. Focus a separator
and use the arrow keys for keyboard resizing. **Reset layout** restores the
defaults. On a phone, the panels stack vertically. Layout sizes stay local to
your browser.

## Share a view

Copy the browser URL to preserve the specification, subjects, compared
datasets, row counts, column focus, searches and open evidence. **Comments** below the workspace holds a GitHub Discussion for the focused
dataset; GitHub sign-in is required to post. If the embedded discussion
cannot load, the review-issue link remains available.
