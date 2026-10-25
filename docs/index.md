# Pilot 7: Agentic data standardization

Pilot 7 uses publicly available pilot studies and synthetic clinical trial
data to demonstrate and evaluate agentic workflows for clinical data
standardization.

## Pilot studies

We use AI agents to review pilot submission packages, reproduce ADaM
datasets, and share findings. Automated comparisons check the derived
datasets against published ADaM.

| Study | Status |
| --- | --- |
| [CDISC Pilot 01](studies/cdiscpilot01.md) | Done |
| [Submission Pilot 3](studies/submission-pilot3.md) | Done |
| [Submission Pilot 5](studies/submission-pilot5.md) | Done |
| [Submission Pilot 6](studies/submission-pilot6.md) | Ongoing |

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
