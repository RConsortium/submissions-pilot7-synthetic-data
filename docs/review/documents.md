# Source documents and Define-XML

## Source documents

The **Source documents** tab shows the retained study documents in their
original form: PDF pages keep their layout, Excel sheets keep coordinates,
merged cells and formulas, and XML renders through the publisher's retained
stylesheet. Each retained file has its own tab, and each worksheet of a
workbook has its own tab too. Use the arrow keys, Home or End to move between
tabs.

Retained ADaM programs open as numbered lines. A finding that cites program
lines opens the program at those lines, marked, with a link to the same lines
in the upstream repository. Each program states its role: the submission's own
program, which produced the reference datasets, or a later reimplementation,
which shows how the reference values can be computed but not what the
original authors intended. A program shows how the reference was computed; it
never counts as documentation of the rule.

**Compare side by side** opens a second independent viewer; switch files
within either pane, and **Close comparison** returns to one. On narrow
screens the two viewers stack. Each viewer has a **Source** link to the file
in the repository at the displayed study revision. Selected files and the
cited location are preserved in the review URL, so a citation from a finding
opens the right page or row. Missing documents are shown as explicitly
unavailable; extracted reading copies are not part of this interface.

## Define-XML comparison

The **Define-XML comparison** tab of a pilot study shows the published ADaM
Define-XML on the left and the yamaa-generated Define-XML on the right, both
rendered with the retained stylesheets. **Open source** shows the unchanged
XML with line numbers, and **Download XML** saves the original bytes. If no
compatible stylesheet is retained, the pane is labeled **XML source** and
shows the numbered XML instead. The panes stack on smaller screens, and the
tab has its own shareable route.

Below the panes, the metadata result and field differences come from the
study's validation run: original and generated values, legacy metadata gaps,
unsupported content and unresolved source declarations. **Complete
comparison evidence** opens the recorded result. Metadata agreement is
separate from XML byte identity, schema validity, data conformance and
dataset agreement; the [pilot study report](../studies/index.md) lists each
of them per study.
