# Dashboard review guide

**Pilot studies** and **Synthetic data** have separate navigation sections.
Pilots support review against published submission packages; the
[study report](studies/index.md) summarizes their results and opens each
review workspace. [Synthetic workspaces](synthetic/index.md) support source
exploration and development of the EDC-to-submission workflow.

The links beside each study name return to the study report and open that
study's source folder in this repository.

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

The YAML pane shows the upstream rules needed to derive the selected variable.
It hides `output.columns`, keeps the relevant input declarations and intermediate
definitions, and narrows column, row and intermediate derivations to related
entries. Matching keys, filters, grouping and lookup selection order stay with
their relevant rule. Row-driver declarations remain available even for literal
values. The selected definition is highlighted, and the caption shows how many
source lines are visible.

Other study settings and verifications remain visible for context. Original
line numbers are retained; inline input and output mappings show the relevant
fields. **All columns** or **Clear highlight** restores the complete original
specification.

Connections include declared values, joins, filters, keys, and ordering. They
describe column dependencies; they do not identify contributing input rows.
Unresolved references are reported above the specification.

Matching keys are included for the input or lookup a derivation actually reads.
Unused inputs and sibling lookup fields do not become sources of every column.
Row filters, grouping and lookup selection order remain part of the trace;
final output sorting does not add value dependencies. For example, `TRT01AN`
traces to DM, while an exposure-derived `TRTSDT` also opens EX. Manually selected
comparison panes remain open independently of automatic lineage.

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

## Review documented rules

Datasets that have been through the consistency review workflow add
**Documented rules** findings. The counts above the table give, per reviewed
dataset, the findings by severity, the adjudication and the verified citations.
Each finding:

- names the rule it violates, such as **CR-5**, and quotes the rule;
- quotes the document statement, with the relevant clause highlighted inside the
  full citation; **View source** opens the cited page or Define-XML variable, and
  the XML lines link to the original file;
- quotes the yamaa specification, with line numbers and the quoted lines
  highlighted;
- shows the data evidence: for a documented rule run as a probe, the records
  that differ from the reference and how the probe states the rule;
- records the adjudicator's decision. **Disputed** findings are the first to
  settle.

**Open evidence in workspace** also selects the subjects whose records differ,
so the workspace shows exactly those records. Statements the adjudicator found
uncited are listed under the counts, with their sources. Severity is
**conflict** (documents disagree with the data or with each other),
**divergence** (the specification states a documented rule differently, with the
same values on this data), **gap** (a rule or clause is undocumented) or
**evidence** (a quote was not found). The rules and the workflow are in the
repository's `.automation/consistency_review/` folder.

## View source documents

Each retained file has its own tab in **Source documents**. Choose a file and use
**Compare side by side** to open a second independent viewer. Switch files within
either pane; **Close comparison** returns to one. On narrow screens, the two
viewers stack vertically. Use arrow keys, Home, or End to move between file tabs.

PDF pages retain their original layout. Excel sheet tables retain coordinates,
merged cells and formulas. XML uses the publisher's retained stylesheet. Each
file title has a **Source** link to that file in the repository at the displayed
study revision. Extracted reading copies and repository paths are omitted from
this interface. Selected files and the primary cited location are preserved in
the review URL. Missing documents remain explicitly unavailable.

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
