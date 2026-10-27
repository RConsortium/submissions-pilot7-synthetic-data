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

The specification's **View** control switches between the original source files
and the engine's **Resolved model (inspection)**. The resolved model expands
inherited declarations, copied producer columns and named windows. Source files
retain their original text and line numbers; the resolved model is an inspection
artifact with its own line numbers. Its normalized representation is not an
authoring template. **Open source** opens the selected original file.

Focused views mark omitted line ranges. **Copy source file** copies the complete
selected file, including hidden lines. **Copy model** copies the complete
inspection model. The selected view is retained in the shared review URL.
For authoring conventions and verification examples, see
[Writing specifications](yaml-authoring.md).

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

The summary separates **Published ADaM reference agreement** from
**Consistency review**. Reference agreement measures reproduction of the
published datasets under the study's comparison rules. Consistency review
checks agreement among documents, derivation rules, and data. Findings can
remain open even when reference agreement is 100%.

The **Consistency findings** tab lists actionable issues. Each row names the
problem, summarizes the difference, and shows measured impact and agent review.
The **Consistency** metric counts issues; the listing separately counts the
supporting automated checks. Successful execution stays in the study metrics.

Search a variable, issue, document, quote or rule ID. **Issue type** filters
conflicts, divergences and gaps. **Impact / review** is the second column.
**Critical finding** filters Yes, No and Needs review, with a reason in each row.
Incorrect source, derivation, category and output rules are critical; differences
limited to significant digits or variable labels are not. Incomplete evidence
and documentation gaps need review. Criticality is independent of the number
of affected subjects. Agent assessments remain visible in the impact column;
agreement is not resolution.
Several checks can support one issue; independent problems in one variable stay
separate. A shared check can support more than one issue without duplicating it
in the supporting-check count.

Expand **Trace evidence** and follow the numbered steps:

1. **Rule comparison:** compare expected and observed behavior with the quoted
   document and specification clauses.
2. **Data comparison:** read the subject-impact summary, then inspect record
   counts and representative value pairs for each named comparison.
3. **Proposed action:** review the suggested change or decision.

Measured impact names both sides, such as **Documented rule vs published
reference** or **Documented codelist vs yamaa output**. Each comparison counts
its own subjects; context-only comparisons are excluded from issue impact.

**Full context** reveals the complete quotation or specification with original
line numbers. **Supporting checks and agent review** retains the rule statements,
complete check evidence and the adjudicator's reasons. Source quotations stay
literal. **View source** opens the retained document. **Source lines** opens
the original quoted XML element or YAML lines in the repository. Define-XML
2.x derivation citations follow the variable's referenced `MethodDef`; comment
and codelist citations open their own elements. Define-XML 1.0 derivations
remain on the `ItemDef` that contains their comment text.

Impact counts distinct subjects across issue-specific comparisons. Shared and
alternative comparisons are labelled as context and excluded from impact.
**Impact not measured** is different from **No differences in tested data**.
Reference differences do not by themselves identify an error in the derived data.

**Open evidence in workspace** selects the variable and the subjects named by
its measured impact. Without a measured subject set, the current subject selection
is retained. Old links naming an individual check open its first related issue.

Label differences and missing columns remain review issues. **Not reviewed**
identifies an authored question with a verified source excerpt. **Missing
evidence** means the expected source or excerpt could not be verified.
Narrative coverage is partial. See the [verification policy](verification.md).

## Review documented rules

Reviewed datasets add **Documented rules** issues. Study-specific grouping is
explicit: each issue has a short title, expected and observed behavior, a proposed
action, and links to its supporting checks. Changes to check evidence require
the grouping to be reviewed before publication. Datasets without a grouping
file retain one issue per check.

Issue types are **conflict** (documents disagree with data or one another),
**divergence** (a documented rule is expressed differently), **gap** (a rule or
clause is undocumented), and **evidence** (a quote was not found). A divergence
can matter even when the current data do not distinguish the rules. Agent
review and human resolution are separate from these types.

## View source documents

Each retained file has its own tab in **Source documents**. Choose a file and use
**Compare side by side** to open a second independent viewer. Switch files within
either pane; **Close comparison** returns to one. On narrow screens, the two
viewers stack vertically. Use arrow keys, Home, or End to move between file tabs.

PDF pages retain their original layout. Excel sheet tables retain coordinates,
merged cells and formulas. XML uses the publisher's retained stylesheet. Each
viewer has a **Source** link to that file in the repository at the displayed
study revision. Extracted reading copies and repository paths are omitted from
this interface. Selected files and the primary cited location are preserved in
the review URL. Missing documents remain explicitly unavailable.

## Compare Define-XML

Open **Define-XML comparison** in a pilot workspace to view the original ADaM
Define-XML on the left and the yamaa-generated XML on the right. Both files have
line numbers, an **Open source** link and a **Download XML** link for the unchanged
file. The panes stack on smaller screens.

The metadata result and field differences come from study validation. Review
the original and generated values below the XML panes, including any legacy
metadata gaps, unsupported content and unresolved source declarations. **Complete
comparison evidence** opens the recorded result. Metadata agreement is separate
from XML byte identity, schema validity and data conformance.

## Review synthetic analysis development

Synthetic workspaces inventory staged ODM archives and show the availability
of source, SDTM, ADaM, and submission-metadata files. Missing stages are shown as
**Not staged**. Archive members, sizes, and repository links help locate source
material. Availability alone does not establish successful derivation.

KN189 and KN564 open the same linked SDTM-to-ADaM dashboard as the pilot
studies. Select subjects, review YAML and data side by side, follow column
lineage, and open retained protocol/SAP and generated metadata under
**Source documents**. Use **Analysis development** for their coverage,
findings, downloads and review drafts. CAR-T for ALL also appears under
**Synthetic data**.

After a successful development build, each study adds **Analysis coverage**,
**Findings for review**, and **Built datasets**. Download the study package for
Parquet, XPT, both Define-XML files, maintained yamaa specifications, retained
source documents and exact build evidence. XPT read-back and XML schema checks
are distinct from an independent reference comparison or regulatory validation.

Coverage separates supported descriptive scope from partial and unsupported
analyses. Findings distinguish data gaps, measured conflicts and unresolved
decisions. Expand a finding to see measured counts, representative records,
verbatim protocol/SAP citations and a proposed action. The retained document
link opens the cited source line.

Use the search and type filter to focus a review. Enter a decision draft and
notes, then **Export review draft** to retain them as JSON. Drafts stay in the
current browser and build until exported. They do not resolve findings or
approve datasets. Apply agreed specification or data changes, then rebuild
before claiming analysis readiness. Primary efficacy records remain unapproved
while their governing decisions are open.

## Share and discuss a review

Copy the browser URL to preserve the specification, subjects, compared datasets,
row-count choices, column focus, searches, and open evidence. **Review comments**
appears below pilot dashboard content with a separate GitHub Discussion for the
focused dataset. GitHub sign-in is required to post. A review-issue link remains
available if the embedded discussion cannot load.
