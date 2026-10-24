# Clinical trial data that you can inspect and reproduce

Pilot 7 is building a public foundation for evaluating open-source tools
and reusable skills in clinical data science. The project brings together
clinical trial datasets, readable derivation specifications, and comparisons
with official analysis data.

[Explore the studies](studies/index.md){ .md-button .md-button--primary }
[Run the derivations](running.md){ .md-button }

## From source data to analysis

The repository follows one pipeline:

**ODM → SDTM → ADaM → tables, listings, and figures**

The four studies in the current yamaa work start with staged **SDTM** data.
Their specifications derive ADaM datasets with the same Rust engine used by
yamaa's Python, R, and command-line interfaces. Data stays in the study
folders; specifications and execution evidence stay available for review.

| Study | Active coverage | Reference data |
| --- | --- | --- |
| [CDISC Pilot 01](studies/cdiscpilot01.md) | Eight ADaM specifications | Official ADaM staged in the repository |
| [Submission Pilot 3](studies/submission-pilot3.md) | Five ADaM specifications | Official FDA submission datasets |
| [Submission Pilot 5](studies/submission-pilot5.md) | Five ADaM specifications | Official Dataset-JSON pilot analysis datasets |
| [Submission Pilot 6](studies/submission-pilot6.md) | Initial ADSL specification | Production ADaM not yet staged here |

The [study verification pages](studies/index.md) show what built and what
matched for the source revision used to build this website. Pilot 6's
unverified output is identified separately.

## Why this work matters

Public clinical data is limited in scale, complexity, and alignment with
current standards. More representative, reusable datasets make it easier
to demonstrate tools, evaluate methods, teach clinical programming, and
assess AI-assisted workflows on shared examples.

Pilot 7 has two complementary workstreams:

- **Benchmark datasets and test cases** for open-source clinical tools.
- **Benchmark test cases for pharma skills**, starting with group sequential
  design in the [pharma skills project](https://github.com/RConsortium/pharma_skills).

The four studies here are reference examples. They complement the project's
synthetic data work; their presence does not imply that all of their source
data was newly simulated by Pilot 7. See [data and provenance](data.md).

## Built with yamaa

The specifications use the new **yamaa 1.0 language and API**, pinned to a
source commit while 1.0 remains unreleased. Each study has a project file,
explicit lookup keys, and a runner that works from any working directory.

Read the [yamaa documentation](https://elong0527.github.io/yamaa/) for the
language, engine, and benchmarks. This website follows that project's MkDocs
Material layout, system fonts, and navy/steel-blue palette.
