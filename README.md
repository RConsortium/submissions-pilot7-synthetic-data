# Pilot 7: Agentic workflow evaluation

Pilot 7 uses publicly available pilot studies and synthetic clinical trial
data to demonstrate and evaluate agentic workflows for clinical development.

This repository demonstrates and evaluates agentic workflows for clinical data
standardization. See the [project website](https://rconsortium.github.io/submissions-pilot7-synthetic-data/) for details.

We collaborate with [BBSW](https://www.bbsw.org), which sponsors shared
tokens for the automated evaluation pipeline.

## Join Us

Pilot 7 holds weekly standups three times a month on Fridays from 8-9 AM PST. We also host monthly Submissions Working Group meetings with FDA staff, bringing together participants across different pilot subgroups.

[Pilot 7 Meeting minutes](https://github.com/RConsortium/submissions-pilot7-synthetic-data/wiki/Meeting-Minutes)

Everyone is welcome to join. To access our calendar and join the Slack workspace, please see
[here](https://rconsortium.github.io/submissions-wg/join.html)

To learn more about the R consortium Submissions Working Group, visit [here](https://rconsortium.github.io/submissions-wg/)

## Synthetic Trial Data

All data under `.archieve/CWMM-LAA1/`, `kn189/`, and `kn564/` was generated
using the [clinical-trial-ipd-sim](https://github.com/RConsortium/pharma-skills/tree/main/clinical-trial-ipd-sim) skill,
based on the original protocol.

## Folder Structure

The [CAR-T study](cart-t/README.md) rebuilds the archived OpenClinica ODM
through SDTM, exploratory ADaM and draft Define-XML with yamaa. Its PR/CI
`cart-t-standardization` artifact contains the standardized data,
specifications and dataset quality evidence. CAR-T does not include TLFs.

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
+-- spec/                     dataset specifications and standards metadata
|   +-- define/              define.xml files, when present
|   +-- yamaa/               yamaa derivation specifications, when present
+-- tlf/                      optional tables, listings, and figures
+-- log/                      execution logs, one per program
```

### Supporting folders

| Folder                | Contents                                                       |
|-----------------------|----------------------------------------------------------------|
| `.github/`            | CI checks, manual ADaM comparison, CORE validation, yamaa evidence and website, and study manifests |
| `.automation/`        | Scheduled issue triage and weekly update prompts     |
| `.archieve/`          | Earlier studies, retained for reference                         |

## Related repositories

- [pharma-skills](https://github.com/RConsortium/pharma-skills)
- [yamaa](https://github.com/elong0527/yamaa)

## License

Original Pilot 7 code and documentation are licensed under the [MIT
License](LICENSE). Study data, including synthetic and derived datasets, and
imported reference material are excluded from the root MIT grant. CDISC pilot
material remains subject to CDISC's terms; existing third-party notices are
retained. See [LICENSING.md](LICENSING.md) for scope, sources, and reuse limits.
