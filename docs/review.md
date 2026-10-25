# Dashboard review guide

Open a [study workspace](studies/index.md) to review its specification, input
records, and analysis output together. Each page identifies the source commit
and reports build results separately from reference agreement.

## Explore the data

The workspace starts with the first three subjects. Open **Subjects** to search
identifiers, select individual subjects, choose a larger group, or select all.
There is no subject selection limit. The row controls page through all selected
records; **Selected CSV** exports all rows matching the current subjects and
record search. **Full Parquet** or **Full CSV** downloads the complete dataset.
CSV exports prefix formula-like text with a quote for spreadsheet safety; full
files preserve source values.

Choose an ADaM dataset, then choose its input or another staged SDTM dataset.
The output control switches between the yamaa result and its independent
reference, when available. Subject-independent lookup tables remain visible.
A subject without events can correctly have no rows in an event dataset.

## Follow a derivation

Select an input column, a YAML block's line number, or an output column. Related
columns and specification blocks highlight together. Use **Clear highlight** to
reset. Drag the separator, or focus it and use the arrow keys, to resize the
specification. **Widen workspace** makes more room on a desktop. On a phone,
the panels stack vertically.

Connections come from declared values, joins, filters, and ordering rules.
They describe column dependencies; they do not identify which individual input
rows contributed to an output value. Unresolved references are reported above
the specification. An unhighlighted area is not proof of independence.

## Verify documentation observations

Open **Consistency report** and search a variable, dataset, document, or phrase.
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

**Copy view link** preserves the dataset, selected subjects, column highlight,
search, and open evidence. **Comments** provides a separate GitHub Discussion
for each dataset, with the same comment service as the yamaa benchmark.
GitHub sign-in is required to post. **Copy review context** includes the source
revision and view link so a reviewer can reproduce the observation. An issue
link remains available if the embedded discussion cannot load. The static site
does not store comments itself.
