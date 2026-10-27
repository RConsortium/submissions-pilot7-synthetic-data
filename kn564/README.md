# KN564 synthetic analysis development

The source is the unchanged 994-subject ODM archive in `data/odm/`.
The uploaded MMD archives retain protocol 564-04 (13-Oct-2020) and the appended
supplemental SAP (22-Dec-2020) for NCT03142334. Both archives contain the same
combined document.

Install Python 3.12+ and the pinned dependencies, using Rust 1.99.1 when
building yamaa from source, then run from the repository root:

```bash
python -m pip install -r kn564/program/adam/python/requirements.txt
python .github/scripts/validate_yamaa.py kn564
```

The structural ODM adapter preserves source values, including fractional
laboratory values whose ODM metadata declares integer. The maintained YAML
in `spec/yamaa/` performs SDTM mappings and ADaM derivations without rounding
those source values. Outputs include Parquet, XPT and separate SDTM/ADaM
Define-XML. Independent XPT read-back checks every cell; both XML documents
are validated against the retained CDISC Define-XML 2.1 XSD.

The measured review record is in `.build/synthetic/kn564/`; its readable
findings are in `log/findings.md`. The authored register is
`spec/review/findings.json`. Review it in the dashboard before analysis use.

Source-summary DFS/OS and assessment-based DFS candidates remain distinct.
Cause-specific survival, BICR sensitivity analyses, COVID sensitivity, and
the complete prespecified PRO analysis lack required data. Week-52 PRO
coverage is checked using the SAP day window, not source nominal labels.
Primary endpoint flags remain missing and `APPRFL=N`. A successful build
is not an independent reference match, regulatory validation, or human sign-off.

The dashboard exports human review drafts without marking findings resolved.
Apply approved specification/data changes and rerun before relying on an export.
