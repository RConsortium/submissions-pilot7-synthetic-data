# Dashboard review guide

Open a [study workspace](studies/index.md) to review its specification, input
records, and analysis output together. Study dashboards use the full browser
width. **All studies** returns to the study gallery; build evidence remains
available in the expandable reproduction section.

## Explore the data

The workspace starts with the first three subjects. Open **Subjects** to search
identifiers, select individual subjects, choose a larger group, or select all.
There is no subject selection limit. Each data panel shows up to ten rows at a
time; use its row controls to explore the remaining selected records. Panels
with fewer matching rows show all available records. Click outside the subject
picker, move focus outside it, or press Escape to close it.

Choose an ADaM dataset, then choose its input or another staged SDTM dataset.
The output control switches between the yamaa result and its independent
reference, when available. Subject-independent lookup tables remain visible.
A subject without events can correctly have no rows in an event dataset.

## Follow a derivation

Select an input column, a YAML block's line number, or an output column. Related
columns and specification blocks highlight together. Use **Clear highlight** to
reset. Drag the separator, or focus it and use the arrow keys, to resize the
specification. The workspace fills the available desktop width. On a phone,
the panels stack vertically.

Connections come from declared values, joins, filters, and ordering rules.
They describe column dependencies; they do not identify which individual input
rows contributed to an output value. Unresolved references are reported above
the specification. An unhighlighted area is not proof of independence.

## Verify documentation observations

Select **Documentation review** in the summary and search a variable, dataset,
document, or phrase in the consistency report.
Each observation links to the relevant YAML line and available source evidence.
**Open evidence in workspace** opens the affected dataset with the evidence panel.
**Open cited source** goes to the extracted location; use the retained original
to confirm wording, tables, and context. **Source documents** lists the original
submission documents, reading copies, and upstream links.

Label differences and missing columns are automated observations requiring
review. **Not reviewed** identifies an authored question with a verified source
excerpt; it does not assert that the derivation is wrong. **Missing evidence**
means the expected source or excerpt could not be verified. Narrative coverage
is partial and is displayed explicitly. Reference agreement is separate from
this report and is not regulatory validation. See the [verification policy](verification.md).

## Share a reproducible review

The browser URL preserves the dataset, selected subjects, column highlight,
search, and open evidence. Copy it to share a view. **Review comments** appears
below the dashboard content, with a separate GitHub Discussion for each dataset
and the same comment service as the yamaa benchmark.
GitHub sign-in is required to post. **Copy review context** includes the source
revision and view link so a reviewer can reproduce the observation. An issue
link remains available if the embedded discussion cannot load. The static site
does not store comments itself.
