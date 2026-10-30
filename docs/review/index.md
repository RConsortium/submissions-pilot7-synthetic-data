# Community review guide

**Goal:** review consistency and gaps between two Pilot 5 sources:

1. The current derived ADaM datasets (`data/adam/*-yamaa.parquet`).
2. The retained ADaM Define-XML (`spec/define/define-adam.xml`).

Open the [Pilot 5 consistency findings](../studies/submission-pilot5.md#submission-pilot5/overview/ADSL).
Choose a dataset or variable, then **Start review**. The evidence identifies
the compared files, their revision and SHA256 hashes, the XML declaration,
and the observed dataset metadata or records.

## Responsibilities

Reviewers decide whether the reported difference or gap is supported by the
two sources and whether it could materially affect an analysis or its
interpretation. Dataset agreement with Define-XML does not establish which
source is clinically correct. Maintainers record decisions and apply agreed
changes before rebuilding.

## Tools

The automated checker reads actual dataset schemas, stored labels, values and
Define-XML declarations. It checks variable coverage in both directions,
logical types, observed text lengths, declared keys, enumerated codelists,
supported value-level conditions and literal arithmetic methods that use
columns already present in the same dataset.

A check can pass, report a difference or gap, or remain **Not assessed**.
Missing dataset label metadata, unsupported conditions, external dictionaries,
rounding-dependent rules and derivations needing SDTM or another document
remain explicit. The review does not substitute YAML labels for stored labels.

Use **Dataset and Define-XML** to inspect selected subjects beside the retained
XML. The checks cover all records, independently of the displayed subjects.
The retained reference datasets, generated Define-XML, YAML, workbook, SAP,
ADRG and original programs do not contribute findings to this Pilot 5 view.
Build and independent dataset reproduction checks continue separately in CI.

## Record a recommendation

Under **Your review**, choose **Agree**, **Disagree** or **Need clarification**,
then **Critical**, **Not critical** or **Unsure**. Add the evidence supporting
your assessment. Drafts save in this browser. **Submit review on GitHub** opens
a prefilled discussion; select **Start discussion** there to publish it.
A draft or posted comment does not resolve the finding.

**Your reviews** exports your assessments with their evidence revision.
[Consistency findings](findings.md) explains the statuses and controls;
[Dataset review](workspace.md) describes the side-by-side view.

## Other studies

This focused workflow is enabled for Pilot 5. Other pilot studies retain their
existing document and derivation review. Synthetic studies retain their
[analysis development review](synthetic.md). The
[verification policy](../verification.md) distinguishes reproduction checks
from consistency review and human approval.
