# Shared yamaa authoring contracts

These templates support the three submission demonstrations. Each study keeps
its own entry specifications, clinical rules, inputs, output column order,
metadata, and independent ADaM references. The pinned engine composes the YAML;
the Python and R runners only execute the project and save its outputs.

| Resource | Responsibility |
| --- | --- |
| `templates/adsl.yaml` | Demographic rules identical across all three studies |
| `templates/subject-analysis.yaml` | Generated ADSL input contract and `copy` of common subject columns |
| `fragments/bds-record.yaml` | Shared BDS record metadata |
| `fragments/analysis-flags.yaml` | Baseline flag vocabulary |
| `<study>/spec/yamaa/fragments/adsl-*.yaml` | Study-specific exposure, baseline, and population rules |
| `cdiscpilot01/spec/yamaa/templates/laboratory.yaml` | Shared chemistry/hematology structure within that study |

## Composition rules

- Use one `parent` for a shared dataset contract, and `include` for cohesive
  fragments. A fragment carries rules, not an independently executable dataset.
- Use `copy` for unchanged producer columns. Write a local derivation for a
  renamed column or a study-specific value. Producer metadata stays authoritative.
- Anchor shared input paths with `relative_to: entry`; study entries use their
  normal relative paths. Consumers read generated `*-yamaa.parquet` files.
- Keep output columns and ordering explicit in each study entry. Retain original
  blanks, labels, types, visit conventions, and documented submission quirks.
- Give reusable windows meaningful names. Keep source values in row derivations
  where they must exist before grouping or lookup. The few corresponding lint
  exceptions state that reason at the rule.
- Use `clear` only when a child must replace an ordered mapping in full; ADLBH's
  donor derivations illustrate inserting a prerequisite before a window.

ADQSNPIX retains its standalone grouping and SELF logic. Its source-dependent
construction does not share a useful executable parent with the other BDS
datasets. Metadata reuse is appropriate only when it preserves those semantics.

## Reproducing the submissions

Pilot 3 constructs missing ACTOT visits from QS and generated ADSL inside its
ADADAS YAML. The visit-window CSV contains static definitions, not subject-level
results. LOCF donors in Pilot 5 and CDISC Pilot 01 select observed QS records
using explicit subject lookups and the original analysis-window rules.

No derivation reads a submitted reference ADaM or repairs an output after the
engine saves it. Validation rejects reference files used as derivation inputs
or outputs. All active datasets must pass their independent comparators.
Text, blanks, nulls, and NaNs retain their submitted meanings; numeric comparison
uses the existing absolute tolerance of `1e-10`.

Run the checks in [AGENTS.md](../../AGENTS.md) before publishing. See the
[authoring guide](../../docs/yaml-authoring.md) and
[verification policy](../../docs/verification.md) for the review workflow.
