# Consistency findings

The **Consistency findings** tab of every pilot study lists outstanding issues
between ADaM data and the submitted Define-XML. Findings include observed value
or metadata discrepancies, invalid documented sources, and contradictory or
incomplete Define-XML rules that need clarification. A documentation finding
can remain open without a measured subject difference.

Differences confined to YAML or a program stay in the complete verification
audit. A missing source excerpt, unsupported calculation, or unavailable
referenced document is an assessment limit, not evidence of a dataset error.
**Study coverage gaps** lists checks awaiting evidence separately. This review
is separate from **Generated ADaM dataset agreement**; see the
[verification policy](../verification.md).

The message bar above the filters reminds you to open **Start review** for
a finding's evidence and record both decisions under **Human Review**.
The **Consistency review** card above the tabs counts grouped findings over
the whole study.

## The findings table

Each row is one issue.

| Column | Meaning |
| --- | --- |
| Dataset | The output dataset the finding concerns. |
| Variable | The output variable, or **Dataset-wide** for a finding about the whole dataset. Its consistency rule IDs appear underneath; select a rule ID to read its requirements. Select the variable to open the workspace with the affected subjects. |
| Status | Under Review until maintainers record a human decision. When the adjudicating agent disputed the finding, or its decision is stale or mixed, the cell says so. |
| Critical finding | The automated criticality assessment: Yes, No or Needs review. |
| Type | The issue type, listed below. |
| Documented rule vs data | How many subjects differ when the documented rule, run as written, is compared with the data; **No differences in tested data**; or **Not measured** when the finding compares statements only. A count here measures the written rule, not the dataset: the review states whether the yamaa output matches the generated ADaM datasets. |
| Issue | A short title and a one-sentence summary. |
| Evidence | **Start review** opens the complete evidence. Your own draft assessment, if you have one, appears underneath. |

The count above the table separates grouped findings from the automated checks
that support them. Several checks can establish the same underlying problem
and share one row. Independent problems for the same variable can have separate
rows. The table counts each supporting check once; a raw check total is not the
number of outstanding findings.

**Study coverage gaps**, below the table, shows the whole study's checks that
could not be assessed, with the dataset, variable and reason. Examples include
an unavailable governing SAP or an external dictionary. Coverage gaps are
counted separately and are not added to the finding total or subject impact.
Finding filters do not change this study-wide coverage list.

## Filters and search

Filters sit directly below the table's column headings. Text filters match
without regard to case, and all active filters apply together:

- **Dataset** matches only the dataset name.
- **Variable** matches the variable name or a displayed rule ID. Combine it with
  **Dataset** to narrow the same variable across different datasets.
- **Status** filters the agent review: agreed, disputed, stale, mixed or not
  adjudicated. Every finding remains Under Review until a human decision is
  recorded; agent agreement is not resolution.
- **Critical finding** filters Yes, No and Needs review. Incorrect source,
  derivation, category and output rules are critical; differences limited to
  significant digits or variable labels are not. Incomplete evidence and
  documentation gaps need review. Criticality is independent of the number of
  affected subjects.
  An empty **No** result means that the current published findings contain no
  non-critical assessments. A grouped finding takes the highest-priority
  assessment of its supporting checks: Yes, then Needs review, then No. A
  label-only or precision-only check can therefore support a finding that also
  contains a more consequential discrepancy. **No** remains available for
  findings assessed as non-critical; it does not mean that a check passed or
  that no subjects were affected. Use **Clear filters** to return to all findings.
- **Type** filters the issue types below.
- **Documented rule vs data** matches a subject count or result text, such as
  `No differences` or `Not measured`.
- **Issue** matches the title or summary.
- **Evidence** filters **Your review**: Not reviewed, Draft or Both decisions
  saved. This filter stays in your browser.

**Search issues** searches across variables, issue text, documents, quotations
and rule IDs. An exact name, such as `ADSL.TRTSDT` or `ADSL`, selects that variable
or dataset alone. **By dataset** offers shortcuts and counts under the current
column filters.

**Issue** starts wider than **Documented rule vs data**. Drag either column's
right header edge to resize it, or focus that edge and use the Left and Right
arrow keys. Widths remain while filtering or switching tabs. On small screens,
the column filters appear above the stacked finding rows.

**Clear filters** restores the full list. The list puts findings marked
**Critical finding: Yes** first, then **Needs review**, then **No**, in the
report's order within each group. Disputed, stale and mixed agent reviews
follow agreed ones within the same criticality. The dataset, shared column
filters, search and open finding are part of the page URL, so a copied link
reproduces them, including the finding open in **Start review**.

## Issue types

| Type | Meaning |
| --- | --- |
| conflict | ADaM values disagree with a verified Define-XML rule, or the relevant Define-XML statements contradict one another. |
| inconsistent | Dataset metadata or structure disagrees with an explicit Define-XML declaration. |
| gap | A documented rule leaves a necessary source, condition or computation unstated. |
| unclear | The verified rule needs clarification before the dataset can be assessed. |

The raw audit also retains implementation divergences, missing quotations and
unreviewed tasks. These do not automatically become published findings. An
agent's proposed interpretation cannot supply a missing documented condition.

Agent review and human resolution are separate from these types; agent
agreement is not resolution.

## Start review

**Start review** opens the finding's complete evidence on its own page, with
the other findings for the same variable listed beside it, in the order a
reviewer needs them:

The opening **The finding** section shows the issue title and its expected
and observed behavior. The sections then follow the navigation:

- **Define-XML vs. reproduced yamaa specification from ADaM data**: the
  identified Define-XML item beside the selected variable in the executable
  resolved YAML. Only these two sources appear in this panel. Original YAML
  line numbers are retained;
  **View source** opens the complete file without losing your draft.
- **Subject examples**: two columns, **ADaM data** and **Documented Rule**,
  with differences highlighted. Record keys and input values appear with
  the data value. Alternative calculations are omitted. Examples illustrate
  the calculation; they do not determine the finding's reported impact.

**Human Review** follows the evidence; see
[Record your assessment](#record-your-assessment).

**Next finding in list** and **Previous finding in list** walk the
findings the table currently lists, in its order, without closing the page;
the footer counts your place in that list. When the open finding is not in
the list, the buttons walk its variable's findings instead.

## Documented rules

Reviewed datasets run documented rules against ADaM data and the yamaa output.
Direct checks also compare the actual dataset's structure, stored labels,
logical types, text lengths, keys and values with the original Define-XML.
Predecessor origins and value-level declarations are read from the XML, so an
omission in a reading copy cannot create an undocumented-derivation finding.

An authored grouping gives each issue a short title, expected and observed
behavior, a proposed action and links to its supporting checks. The publication
review decides which checks establish an outstanding data or documentation
issue, which need clarification, and which belong in coverage or the raw audit.
A change to the evidence requires the review to be checked before publication.
The complete checks remain in the generated verification report.

Measured impact uses only the documented rule and assessable records. A probe
that adds an unstated visit window, population or ordering is a conditional
interpretation; its differing records do not establish literal-rule impact.
`SignificantDigits` alone does not instruct a derivation to round its result.
Physical floating-point storage does not make an integer declaration wrong
when the actual values are integral, and numeric representation noise is not
a clinical discrepancy.

Define-XML 2.x derivation citations follow the variable's referenced
`MethodDef`; comment and codelist citations open their own elements.
Define-XML 1.0 derivations remain on the `ItemDef` that contains their
comment text.

## Record your assessment

Under **Human Review**, answer **Do you agree with this finding?** first:
**Agree**, **Disagree** or **Need clarification**. Next answer **Is this
finding critical?**: **Critical**, **Not critical** or **Unsure**. Third,
optionally assess **Is current dataset correctly derived?**: **Yes, dataset
is correct**, **No, define-xml is correct**, **Neither as written** or **Unsure**.
Add review comments if needed. The choices share a row on desktop and stack
on smaller screens. No answer is preselected. Drafts save automatically in this
browser, scoped to the study and the issue and bound to its current
evidence; if the evidence changes in a later publication, your earlier
assessment returns as a draft marked **evidence changed**.

**Submit review on GitHub** needs both decisions. It opens GitHub's new
discussion composer in a new tab with your assessment in the title and body;
sign in if asked and select **Start discussion** to publish under your own
account. The review keeps the source revision and the check IDs so
maintainers can locate the evidence.

No review is posted automatically, and a posted review does not resolve the
finding or approve the dataset: maintainers record the human decision and
apply agreed changes before rebuilding.

## Your reviews

**Your reviews** above the table counts the listed findings you have
started in this browser: how many have both decisions, how many are still
drafts, how many you shared and how many have changed evidence since. The
**Your review** filter lists only your drafts, only the findings with both
decisions, or only the ones you have not started. **Copy your reviews** and
**Download your reviews** hand over every assessment of the listed findings
as one Markdown document with the evidence revision, each decision, your
comment and a link back to the finding. The document is your own record; it
does not resolve a finding or approve a dataset.

A finding's row says **Your review: Draft** until both decisions are chosen,
**Saved locally** once they are, **Opened in GitHub composer** once **Submit
review on GitHub** has opened the composer; editing the assessment afterwards
returns it to **Saved locally** or to a draft. The dashboard never confirms
what was published on GitHub: only the discussion itself shows that. The hand-over document starts
with a line for your name, the date and the filters the list was under.

## Comments

**Comments** below the dashboard holds a GitHub Discussion for the
focused dataset, separate from the per-finding discussions that **Submit
review on GitHub** creates. GitHub sign-in is required to post. A
review-issue link remains available if the embedded discussion cannot load.
Old links that name an individual check open its first related issue.
