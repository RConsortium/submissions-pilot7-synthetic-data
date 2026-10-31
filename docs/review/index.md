# Community review guide

Goal: assess the Submission Pilot 5 package by checking the findings that
AI agents reported against the study documents, the specifications and the
data.

These results are *draft / dry run, pending human review*. We welcome
statistical programmers and biostatisticians to review one finding, variable
or rule. You do not need to install software or review an entire study to
help: *one evidence-backed recommendation is a useful completed
contribution.*

## 1. Choose a Pilot 5 finding

Open the [Pilot 5 consistency findings](../studies/submission-pilot5.md#submission-pilot5/overview/ADSL?findingSearch=ADSL).
It opens on ADSL with the critical findings first; pick another dataset
under **By dataset** when you are done, and take documentation gaps after
the findings marked **Critical finding: Yes** or **Needs review**. You can also report a problem that the automated checks missed.

Each row names the dataset and variable, the issue type and the automated
criticality assessment. [Consistency findings](findings.md) explains the
columns, the filters and the issue types.

## 2. Check the evidence

For a finding, open **Start review**. The review dialog keeps the findings for
the same variable separate and follows this order:

| Section | Review question |
| --- | --- |
| The finding | What concrete difference is reported, and what impact was measured? |
| Define-XML vs. reproduced yamaa specification from ADaM data | What does the cited Define-XML item require, and how does the resolved yamaa specification express it? |
| Subject examples | Do actual records support the explanation? Examples illustrate the calculation; the measured comparison determines impact. |
| Human Review | Do you agree with the finding and its criticality? Which source is right? |

Read **Question for you**, the measured impact and the automated criticality
assessment under **The finding**. Use **View source** to check a citation. To inspect
the affected subjects, the specification and the linked SDTM inputs, select
the finding's variable name in the findings table;
[SDTM to ADaM workspace](workspace.md) explains its controls.

*A 100% match with generated ADaM datasets does not establish correctness or human
approval.* Documents, specifications and data can still disagree, and a
dataset difference alone does not identify which source is wrong.
Automated checks and agent assessments support your review; they do not
resolve findings. See the [verification policy](../verification.md) for the
comparison scope and limits.

## 3. Leave a recommendation

At the end of the review dialog, under **Human Review**, choose **Agree**,
**Disagree** or **Need clarification**, then **Critical**, **Not critical** or
**Unsure**, and explain your assessment. Drafts save automatically in this
browser and are not shared until you submit them.

**Submit review on GitHub** needs both decisions. It opens a new GitHub
discussion in a new tab with your assessment filled in. Sign in with GitHub
if asked, then select **Start discussion** to publish it under your own
account.

Maintainers assess feedback, record the human decision and apply agreed
changes before rebuilding. A comment does not approve a dataset.

**Your reviews** above the findings table counts what you have reviewed and
hands over all of your assessments as one document (**Copy your reviews**
or **Download your reviews**) for a study lead;
[Consistency findings](findings.md#your-reviews) describes it.

## Other studies

CDISC Pilot 01 and Submission Pilot 3 use the same dashboard; the
[pilot study report](../studies/index.md) opens each one. KN189, KN564 and
CAR-T for ALL have no independent generated ADaM comparison datasets;
[synthetic analysis review](synthetic.md) describes how to review their
coverage and findings.
