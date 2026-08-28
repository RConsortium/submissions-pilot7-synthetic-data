
# Project Scope

## Why this project matters
The pharmaceutical ecosystem is seeing rapid growth of open-source R tools and AI-enabled applications across clinical development, analysis, and regulatory submissions.

However, objective benchmarking and evaluation of these tools is currently constrained by the lack of high-quality, publicly available clinical trial datasets.

Existing public datasets, such as **CDISC Pilot 1**, have important limitations:

- They are outdated and not well aligned with current CDISC standards or current industry practice
- They are limited in scale and complexity
- They are insufficient for evaluating modern workflows, including AI-assisted analysis, automation, and end-to-end submissions

As a result, there is a clear need for modern, realistic, and reusable synthetic clinical trial data that can support:

- Tool demonstration
- Method evaluation
- Community development and education

## Initial Scope
The initial scope of this project was to build **benchmark datasets and evaluation test cases for open-source tools** relevant to clinical data science.

The goal is to create a shared and practical foundation for assessing how well open-source tools perform on realistic pharma use cases, especially in settings where modern workflows require more representative and reusable benchmark data.

## Expanded Scope
The scope has now been expanded to include a second workstream: **benchmark test cases for pharma open-source skills**.

These skills are more focused, task-oriented, and reusable capabilities that support specific workflows in clinical data science. The first skill in this effort is [**group sequential design (GSD)**](https://github.com/RConsortium/pharma_skills/tree/main).

This expansion is being developed in collaboration with [**BBSW**](www.bbsw.org), which is supporting the work by sponsoring shared tokens for the automated evaluation pipeline.

## Current Activities Overview
The project now includes two complementary parts:

- **Part A:** Benchmark datasets and test cases for evaluating open-source tools
- **Part B:** Benchmark test cases for evaluating pharma open-source skills, starting with **GSD**

Together, these efforts aim to build a stronger public foundation for rigorous, scalable, and transparent evaluation of open-source capabilities in clinical data science.

## Join Us

Pilot 7 holds weekly standups three times a month on Fridays from 8-9 AM PST. We also host monthly Submissions Working Group meetings with FDA staff, bringing together participants across different pilot subgroups.

[Pilot 7 Meeting minutes](https://github.com/RConsortium/submissions-pilot7-synthetic-data/wiki/Meeting-Minutes)

Everyone is welcome to join. To access our calendar and join the Slack workspace, please see 
[here](https://rconsortium.github.io/submissions-wg/join.html)


To learn more about the R consortium Submissions Working Group, visit [here](https://rconsortium.github.io/submissions-wg/)


## Synthetic Trial Data

All data under `.archieve/CWMM-LAA1/` and `kn564/` was generated using the [clinical-trial-ipd-sim](https://github.com/RConsortium/pharma-skills/tree/main/clinical-trial-ipd-sim) skill, based on the original protocol.

## Folder Structure

Each study lives in its own top-level folder, organized by pipeline stage. The
data flow is **ODM -> SDTM -> ADaM -> TLF**: an ODM export of the collected CRF
data is mapped to SDTM tabulation datasets, those are derived into ADaM
analysis datasets, and the ADaM feed the tables, listings, and figures.

```
<study>/                      a study name
+-- data/
|   +-- odm/                  source ODM v2.0 export
|   +-- sdtm/                 SDTM tabulation datasets
|   +-- adam/                 ADaM analysis datasets
+-- program/
|   +-- odm/                  ODM XML -> per-form CRF data
|   +-- sdtm/                 CRF data -> SDTM
|   +-- adam/                 SDTM -> ADaM
+-- tlf/                      tables, listings, and figures
```

Stage folders that are not yet populated are tracked with an empty `.gitkeep`.

### Supporting folders

| Folder                | Contents                                                       |
|-----------------------|----------------------------------------------------------------|
| `.github/workflows/`  | CI, including CDISC CORE validation of the SDTM/ADaM datasets   |
| `.automation/`        | Scheduled Claude Code routine prompts and bootstrap scripts     |
| `.archieve/`          | Earlier studies, retained for reference                         |

## Reference: CDISC Pilot 1 data
- Original sdtm: [json version](https://github.com/RConsortium/submissions-pilot6-adams-tlfs/tree/main/data/sdtm)
- Original xpt versions: see pilot 5 [repo](https://github.com/RConsortium/submissions-pilot5-datasetjson) 
- CSR: [https://github.com/cdisc-org/sdtm-adam-pilot-project/blob/master/updated-pilot-submission-package/900172/m5/53-clin-stud-rep/535-rep-effic-safety-stud/5351-stud-rep-contr/cdiscpilot01/cdiscpilot01.pdf](https://github.com/cdisc-org/sdtm-adam-pilot-project/blob/master/updated-pilot-submission-package/900172/m5/53-clin-stud-rep/535-rep-effic-safety-stud/5351-stud-rep-contr/cdiscpilot01/cdiscpilot01.pdf)


