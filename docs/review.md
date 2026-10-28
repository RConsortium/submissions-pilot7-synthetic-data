# Community review guide

**Goal:** Help us assess whether the generated specifications and outputs follow
the study documents, and whether the reported findings and proposed actions are
justified.

These results are **draft / dry run, pending human review**. We welcome
statistical programmers and biostatisticians to review one finding, variable,
or rule. You do not need to install software or review an entire study to help.

## 1. Choose a study and finding

Open the [pilot study report](studies/index.md), choose a study and dataset,
and open **Consistency findings**. Start with critical findings or items marked
**Needs review**, then documentation gaps. You can also report a problem that
the automated checks missed.

For KN189, KN564, and CAR-T for ALL, start with the
[synthetic data report](synthetic/index.md). In KN189 and KN564, open
**Analysis development** and **Findings for review**. Focus on whether the
protocol/SAP, available data, and proposed analysis support the intended use.
Check partial or unsupported analyses and pending decisions.

## 2. Check the evidence

For a pilot finding, open **Trace evidence**. The expanded review page keeps
related findings separate and follows this structure:

| Step | Review question |
| --- | --- |
| The finding | What concrete difference is being reported, and what impact was measured? |
| What the sources say | What does the cited protocol, SAP, or Define-XML require? Does the specification express that rule? |
| Subject examples | Do actual records support the explanation? Examples illustrate the calculations; full comparisons determine impact. |
| Recommended fix | Is the suggested correction or decision justified? Is more evidence needed? |

Use **Full context** or **View source** to check a citation. Use
**Open evidence in workspace** to inspect the relevant subjects, specification,
and linked inputs. Select an output column to follow its source dependencies.
For synthetic findings, expand the finding and check its cited rule, measured
records, and proposed action in the same way.

**A 100% published-reference match does not establish correctness or human
approval.** Documents, specifications, and data can still disagree. A reference
difference alone also does not identify which source is wrong. Automated checks
and agent assessments support your review; they do not resolve findings.
See the [verification policy](verification.md) for comparison scope and limits.

## 3. Leave a recommendation

At the end of the trace page, assess **Agree**, **Disagree**, or **Need
clarification**, then choose **Critical**, **Not critical**, or **Unsure**.
Add comments explaining your assessment. **Save draft** retains unfinished work;
**Save review** requires both decisions. These choices are stored in your browser
and remain separate from automated assessments and finding resolution. If the
evidence changes, an earlier review becomes a draft for reassessment.

Use **Download review** to keep or share your decisions and comments, with the
finding IDs and source revision. Share feedback through the discussion tools
below; a browser-local assessment is not posted automatically.

State **Agree with the proposed action**, **Suggest a correction**, or
**Need more evidence**, and explain why. Use this template:

```text
Study / dataset / variable:
Finding ID or shared dashboard URL:
Recommendation:
Expected rule and supporting source:
Observed behavior or affected records:
Suggested correction or evidence needed:
```

For pilot datasets, post under **Review comments** in the workspace; GitHub
sign-in is required. Copy the browser URL to preserve your selected subjects,
variable, and evidence. If comments are unavailable, use the review-issue link
or [open a GitHub issue](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/new).
Use a GitHub issue for synthetic-study feedback too.

**One evidence-backed recommendation is a useful completed contribution.**
Maintainers assess feedback, record the human decision, and apply agreed
changes before rebuilding. A comment does not approve a dataset. Synthetic
**Export review draft** saves a local draft; it must be shared to contribute
feedback and does not resolve a finding.

For controls, filters, source viewers, and sharing details, see the
[dashboard reference](dashboard-reference.md).
