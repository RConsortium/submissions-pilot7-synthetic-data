# Data and provenance

Each study keeps its inputs, specifications, programs, and outputs together.
The four yamaa projects in this repository start at the **SDTM → ADaM** stage;
they do not reconstruct ODM or simulate new subjects.

| Folder | Source |
| --- | --- |
| `cdiscpilot01/` | [CDISC SDTM/ADaM Pilot Project](https://github.com/cdisc-org/sdtm-adam-pilot-project/tree/master/updated-pilot-submission-package/900172/m5/datasets/cdiscpilot01) |
| `submission-pilot3/` | [R Consortium Pilot 3 submission](https://github.com/RConsortium/submissions-pilot3-adam/tree/main/submission) |
| `submission-pilot5/` | [R Consortium Dataset-JSON pilot](https://github.com/RConsortium/submissions-pilot5-datasetjson/tree/main/pilot5-submission) |
| `submission-pilot6/` | [R Consortium ADaM and TLF expansion](https://github.com/RConsortium/submissions-pilot6-adams-tlfs) |

The study READMEs record staging details. Most datasets are Parquet, with
original labels retained in Arrow schema metadata. Define-XML files and the
Pilot 6 workbook provide source metadata. Pilot 3 also carries reviewed CSV
planning relations used by ADADAS.

Pilot 6 stages all 21 SDTM inputs and 8 production ADaM references from its
upstream DVC snapshot at `a4f85c95cfef1f6aa27795362630f8ae43210185`.
Its S3 remote permits anonymous downloads. The study's
[`spec/source-snapshot.json`](https://github.com/RConsortium/submissions-pilot7-synthetic-data/blob/main/submission-pilot6/spec/source-snapshot.json)
records source and output hashes, dimensions and metadata sources; its
[README](https://github.com/RConsortium/submissions-pilot7-synthetic-data/blob/main/submission-pilot6/README.md)
documents conversion and refresh commands. Shared clinical data does not
establish that the analysis datasets or derivation choices are identical
across pilots. Import verification does not establish YAMAA reference agreement.

## Repository layout

```text
<study>/
  data/odm/          collected source data, when present
  data/sdtm/         tabulation datasets
  data/adam/         official references and ignored derived outputs
  data/mapping/      planning relations, when needed
  program/odm/       source ingestion programs
  program/sdtm/      tabulation programs
  program/adam/      analysis runners and comparators
  spec/define/       original Define-XML, when present
  spec/yamaa/        project and derivation YAML
  tlf/               tables, listings, and figures
  log/               execution logs
```

The structure check discovers studies automatically and uses
`.github/repo-structure.json` as its template. Website directories are
explicitly excluded from study discovery.

## Synthetic studies and archives

`kn189/` and `kn564/` are separate study folders and are outside the four
yamaa projects on this site. Earlier work is retained under `.archieve/`.
The repository README records the `clinical-trial-ipd-sim` skill used for
the synthetic data under `.archieve/CWMM-LAA1/` and `kn564/`.

Consult each upstream source for its dataset provenance, applicable terms,
and supporting submission documents before reusing the data.
