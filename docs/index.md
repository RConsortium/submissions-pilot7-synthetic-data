# Pilot 7: Agentic data standardization

Pilot 7 uses publicly available pilot studies and synthetic clinical trial
data to demonstrate and evaluate agentic workflows for clinical data
standardization.

## Pilot studies

AI agents review pilot submission packages and generate derivation
specifications in YAML format.
The yamaa engine executes these specifications to derive
ADaM datasets from SDTM. We compare the yamaa outputs with the published
ADaM datasets from the original submissions.

<div class="pilot-metrics" markdown="1" role="region" aria-label="Pilot study comparison metrics" tabindex="0">

<!-- pilot-metrics:begin -->
[View the latest validated study metrics on the project website](https://rconsortium.github.io/submissions-pilot7-synthetic-data/).
<!-- pilot-metrics:end -->

</div>

Values are **fully matched / reference total (percentage)**; **M**
means one million.

## Synthetic studies

We use synthetic studies to develop and demonstrate the full workflow:

> EDC data extraction -> SDTM mapping -> ADaM derivation -> define.xml generation.

These outputs support eCTD submission package preparation.

| Study | Status |
| --- | --- |
| [KN189](studies/kn189.md) | Ongoing |
| [KN564](studies/kn564.md) | Ongoing |

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
| GitHub Issues | Record requests, discussions, and decisions. |
| GitHub Actions | Run automated checks and dataset comparisons. Build and deploy the project website through CI/CD. |
