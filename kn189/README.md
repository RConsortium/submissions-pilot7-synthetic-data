# KN189 synthetic analysis development

The source is the unchanged 616-subject ODM archive in `data/odm/`.
The uploaded MMD archives retain protocol amendment 189-12 (31-May-2022)
for NCT02578680. Both uploaded archives contain the same combined protocol/SAP.

Install Python 3.12+ and the pinned dependencies, using Rust 1.99.1 when
building yamaa from source, then run from the repository root:

```bash
python -m pip install -r kn189/program/adam/python/requirements.txt
python .github/scripts/validate_yamaa.py kn189
```

The structural ODM adapter copies collected values without clinical
derivations. The maintained YAML in `spec/yamaa/` performs SDTM mappings and
ADaM derivations. The run writes Parquet, XPT, separate SDTM/ADaM Define-XML,
native reports, and a measured review record in `.build/synthetic/kn189/`.
Every XPT cell is checked with the independent pyreadstat reader. Both XML
files are checked against the retained CDISC Define-XML 2.1 XSD.

Review `spec/review/findings.json`, the generated `log/findings.md`, and the
KN189 dashboard before using any endpoint. Source-summary and assessment-based
time-to-event candidates are separate. Primary analysis flags remain missing;
`APPRFL=N` is not a claim of human approval. No cutoff-specific confirmatory
analysis, independent published-reference match, or regulatory validation is claimed.

SDTM uses a custom ZX findings domain for precomputed source efficacy values
and XP for subsequent therapies. SUPPDM and SUPPAE retain original text when
standard codes are mapped. Units are not invented. The proposed metadata
versions, baseline convention, safety rules, and strata remain review decisions.

The dashboard can export a human review draft. Exported notes do not update
the register or datasets until reviewed changes are applied and the study is rebuilt.
