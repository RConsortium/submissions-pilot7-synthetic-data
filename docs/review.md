# Community review guide

**Goal:** assess Pilot 5 submission package by leverage findings from AI.

These results are **draft / dry run, pending human review**. We welcome
statistical programmers and biostatisticians to review findings.
You do not need to install software or review an entire study to help.

## 1. Choose a Pilot 5 finding

Open the [Pilot 5 review dashboard](https://rconsortium.github.io/submissions-pilot7-synthetic-data/studies/submission-pilot5/#submission-pilot5/overview/ADSL)
Select a dataset and open **Consistency findings**.
Start with critical findings or items marked **Needs review**, then documentation
gaps. You can also report a problem that the automated checks missed.

## 2. Check the evidence

For a finding, open **Trace evidence**. The expanded review page keeps
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

**A 100% published-reference match does not establish correctness or human
approval.** Documents, specifications, and data can still disagree. A reference
difference alone also does not identify which source is wrong. Automated checks
and agent assessments support your review; they do not resolve findings.
See the [verification policy](verification.md) for comparison scope and limits.

## 3. Leave a recommendation

At the end of the trace page, assess **Agree**, **Disagree**, or **Need
clarification**, then choose **Critical**, **Not critical**, or **Unsure**.
Add comments explaining your assessment. Drafts save automatically in this
browser. **Copy review & open GitHub comments** requires both decisions and
copies your assessment. Paste it into the comment box, sign in with GitHub
if needed, and select **Comment** to publish.


**One evidence-backed recommendation is a useful completed contribution.**
Maintainers assess feedback, record the human decision, and apply agreed
changes before rebuilding. A comment does not approve a dataset.

For controls, filters, source viewers, and sharing details, see the
[dashboard reference](dashboard-reference.md).
