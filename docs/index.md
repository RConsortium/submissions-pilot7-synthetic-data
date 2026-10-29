# Pilot 7: Agentic data standardization

Pilot 7 uses publicly available pilot studies and synthetic clinical trial
data to demonstrate and evaluate agentic workflows for clinical data
standardization. AI agents draft derivation specifications in YAML, the
[yamaa](https://elong0527.github.io/yamaa/) engine executes them, and
automated checks compare the outputs with the published submissions and the
study documents. Every result on this site is a draft pending human review.

## Start reviewing

Statistical programmers and biostatisticians can review one finding at a
time. Nothing is installed, and one evidence-backed recommendation is a
complete contribution.

<div class="grid cards" markdown>

-   **Review Pilot 5 findings**

    ---

    Open the Submission Pilot 5 dashboard at its consistency findings, pick a
    dataset and start with the critical findings.

    [Open the findings](studies/submission-pilot5.md#submission-pilot5/overview/ADSL?findingSearch=ADSL)

-   **Learn how to review**

    ---

    What a finding is, how to check its evidence and how to record your
    assessment on GitHub.

    [Read the review guide](review/index.md)

-   **See the results**

    ---

    Reference agreement and consistency findings for every pilot study on one
    printable page.

    [Open the pilot study report](studies/index.md)

</div>

## Pilot studies

For each pilot submission package, AI agents review the package and write
the derivation specifications, yamaa derives the ADaM datasets from the
staged SDTM data, and the outputs are compared with the published ADaM
datasets and with the study documents. Two measures are reported, and they
answer different questions:

- **Published ADaM reference agreement**: does the derived dataset reproduce
  the published one under the study's comparison rules?
- **Consistency review**: do the documents, derivation rules and data agree
  with one another? Findings stay open until a person decides them, even
  when reference agreement is 100%.

<div class="pilot-metrics" markdown="1" role="region" aria-label="Pilot study comparison metrics" tabindex="0">

<!-- pilot-metrics:begin -->
[View the latest validated study metrics on the project website](https://rconsortium.github.io/submissions-pilot7-synthetic-data/).
<!-- pilot-metrics:end -->

</div>

Reference values are **matching / reference total**. Column and cell counts
come from datasets that pass the reference comparison; **M** means one
million. Select a findings count to open its evidence. The
[verification policy](verification.md) defines both measures and their
limits, and the [pilot study report](studies/index.md) compares the packages
dataset by dataset.

## Synthetic studies

Synthetic studies exercise the complete workflow:

> EDC data extraction -> SDTM mapping -> ADaM derivation -> define.xml generation.

They have no published reference, so their dashboards support source
exploration and analysis review rather than reference comparison. These
outputs support eCTD submission package preparation.

| Study | Scope | Review |
| --- | --- | --- |
| [KN189](studies/kn189.md) | Protocol/SAP-based SDTM and ADaM development with submission metadata | Analysis coverage and open findings |
| [KN564](studies/kn564.md) | Protocol/SAP-based SDTM and ADaM development with submission metadata | Analysis coverage and open findings |
| [CAR-T for ALL](studies/cart-t.md) | OpenClinica ODM export standardized to SDTM, exploratory ADaM and draft Define-XML | Linked specification and data workspace |

The [synthetic data report](synthetic/index.md) inventories the staged
sources and workflow readiness of all three studies.

## Agentic SDLC workflow

We use [yamaa](https://elong0527.github.io/yamaa/) within four stages of the
software development lifecycle (SDLC):

1. **Plan:** define specifications, derivation rules, and acceptance criteria. Record decisions.
2. **Develop:** implement mappings, derivations, metadata, and custom functions.
3. **Evaluate:** run specification checks and dataset comparisons. Review discrepancies and evaluation reports.
4. **Deploy:** release reviewed programs, specifications, and outputs.

Human reviewers work with AI agents to refine plans and evaluate results
throughout the workflow.

## Responsibilities

| Role | Responsibility |
| --- | --- |
| Human reviewers | Define clinical and statistical requirements and acceptance criteria. Review and approve specifications, code, results, and releases. |
| AI agents | Draft specifications, custom functions, evaluation reports, and GitHub Actions workflows. Propose fixes for human review. |

## Tools

| Tool | Purpose |
| --- | --- |
| [yamaa](https://elong0527.github.io/yamaa/) | Check and execute YAML specifications to generate datasets and define.xml. |
| GitHub Issues and Discussions | Record requests, review assessments, and decisions. |
| GitHub Actions | Run automated checks and dataset comparisons. Build and deploy the project website through CI/CD. |
