# Consistency findings

The **Consistency findings** tab of a pilot study lists every actionable
issue that the automated consistency review found among the study's
documents, derivation rules and data. It is separate from **Generated ADaM dataset agreement**: a derived dataset can match the generated ADaM datasets
while a document states a different rule, and that finding stays open until
a person decides it. The [verification policy](../verification.md) defines
both measures.

**How to review a finding**, above the filters, states the two decisions
every finding asks for, the working definition of critical and the issue
types, so the tab can be used without this page. It stays open until you
have started a review of the study. The **Consistency review** card above
the tabs counts your reviews over the whole study.

## The findings table

Each row is one issue.

| Column | Meaning |
| --- | --- |
| Dataset / variable | The output variable the issue concerns, with the IDs of the consistency rules its checks apply; select a rule ID to read what the rule requires. Select the name to open the variable in the workspace with the affected subjects. |
| Status | Under Review until maintainers record a human decision. When the adjudicating agent disputed the finding, or its decision is stale or mixed, the cell says so. |
| Critical finding | The automated criticality assessment: Yes, No or Needs review. |
| Type | The issue type, listed below. |
| Documented rule vs data | How many subjects differ when the documented rule, run as written, is compared with the data; **No differences in tested data**; or **Not measured** when the finding compares statements only. A count here measures the written rule, not the dataset: the review states whether the yamaa output matches the generated ADaM datasets. |
| Issue | A short title and a one-sentence summary. |
| Evidence | **Start review** opens the complete evidence. Your own draft assessment, if you have one, appears underneath. |

The count above the table separates issues from the automated checks that
support them. Several checks can support one issue, and a shared check can
support more than one issue without being counted twice. Repeated clause
differences for the same variable and the same pair of source files share one
row, including quotations from different pages; different source pairs stay
separate.

## Filters and search

**By dataset** shows how many issues each dataset has under the current
comparison, type and criticality filters; select a dataset to list its issues
alone, or **All** to list every dataset. The search matches a variable, issue
title, document name, quotation or rule ID; an exact name, such as
`ADSL.TRTSDT` or `ADSL`, selects that variable or dataset alone.

- **Comparison** separates input-to-output logic checks, source-document
  questions and documented-rule checks.
- **Issue type** filters the types below.
- **Agent review** filters by the adjudicating agent's decision: agreed,
  disputed, stale, mixed or not adjudicated. The list places disputed,
  stale and mixed findings after the agreed ones of the same criticality;
  they stay listed, because agent agreement is not resolution.
- **Critical finding** filters Yes, No and Needs review. Incorrect source,
  derivation, category and output rules are critical; differences limited to
  significant digits or variable labels are not. Incomplete evidence and
  documentation gaps need review. Criticality is independent of the number of
  affected subjects.

**Clear filters** restores the full list. The list puts findings marked
**Critical finding: Yes** first, then **Needs review**, then **No**, in the
report's order within each group. The dataset, filters, search and open
finding are part of the page URL, so a copied link reproduces them,
including the finding open in **Start review**.

## Issue types

| Type | Meaning |
| --- | --- |
| conflict | Documents disagree with the data or with one another. |
| divergence | A documented rule is expressed differently in the specification. A divergence can matter even when the current data do not distinguish the two rules. |
| gap | A rule or clause is undocumented. |
| evidence | A quoted passage was not found where it is cited. |
| inconsistent | An input-to-output check failed: a declared output column is absent, a label differs from the published Define-XML, or a build did not succeed. |
| unclear | A question the checks cannot settle, such as a dataset name without an exact Define-XML match or a document version that was not revalidated. |
| missing evidence | An authored review question whose source or excerpt could not be verified. |
| not reviewed | An authored review question with a verified excerpt and no decision yet. |

Agent review and human resolution are separate from these types; agent
agreement is not resolution.

## Start review

**Start review** opens the finding's complete evidence on its own page, with
the other findings for the same variable listed beside it, in the order a
reviewer needs them:

The opening **The finding** section shows the issue title and its expected
and observed behavior. The sections then follow the navigation:

1. **Source documents**: cited clauses from the protocol, SAP or Define-XML,
   side by side. **Full context** reveals the longer passage. **View source**
   opens the retained original at its cited row, page or YAML lines while
   keeping your place and draft.
2. **YAML specification**: YAML derivations side by side, with
   `documented-rules.yaml` on the left and the study's resolved dataset
   specification on the right. Submission metadata and prose descriptions
   are omitted. Line numbers and **View source** link to the complete source.
3. **Subject examples**: generated ADaM records beside document-based
   calculations, with differences highlighted. Examples illustrate the
   calculation; they do not determine the finding's reported impact.
4. **Recommended fix**: the proposed correction or decision. A question shared
   by multiple findings is headed **Open question for this variable**; decide
   each finding on its own evidence.

**Your review** follows the evidence; see
[Record your assessment](#record-your-assessment).

**Next finding in list** and **Previous finding in list** walk the
findings the table currently lists, in its order, without closing the page;
the footer counts your place in that list. When the open finding is not in
the list, the buttons walk its variable's findings instead.

## Documented rules

Reviewed datasets add **Documented rules** issues, which run each derivation
as the documents state it and compare the result with the generated ADaM datasets and the yamaa output. An authored grouping gives each issue a short
title, expected and observed behavior, a proposed action and links to its
supporting checks; a change to the check evidence requires the grouping to be
reviewed before publication. Without authored grouping, verified clause
discrepancies for the same variable and exact source-file pair share one
issue, and their complete checks remain in the generated verification report.

Define-XML 2.x derivation citations follow the variable's referenced
`MethodDef`; comment and codelist citations open their own elements.
Define-XML 1.0 derivations remain on the `ItemDef` that contains their
comment text.

## Record your assessment

Under **Your review**, choose **Agree**, **Disagree** or **Need
clarification**, then **Critical**, **Not critical** or **Unsure**. When the
finding sets a document against the specification, **Which side is right?**
(**The document**, **The specification**, **Neither as written**, **Unsure**)
is optional and answers the variable's open question; add a comment. Neither decision is preselected. Drafts save automatically in this
browser, scoped to the study and the issue and bound to its current
evidence; if the evidence changes in a later publication, your earlier
assessment returns as a draft marked **evidence changed**.

**Submit review on GitHub** needs both decisions. It opens GitHub's new
discussion composer in a new tab with your assessment in the title and body;
sign in if asked and select **Start discussion** to publish under your own
account. **Copy review instead** copies the same text to paste into the
dataset's **Review comments** box, where **Comment** publishes it. The text
keeps the source revision and the check IDs so maintainers can locate the
evidence.

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
review on GitHub** has opened the composer, and **Copied for GitHub** once you
copied the review; editing the assessment afterwards returns it to **Saved
locally** or to a draft. The dashboard never confirms what was published on
GitHub: only the discussion itself shows that. The hand-over document starts
with a line for your name, the date and the filters the list was under.

## Review comments

**Review comments** below the dashboard holds a GitHub Discussion for the
focused dataset, separate from the per-finding discussions that **Submit
review on GitHub** creates. GitHub sign-in is required to post. A
review-issue link remains available if the embedded discussion cannot load.
Old links that name an individual check open its first related issue.
