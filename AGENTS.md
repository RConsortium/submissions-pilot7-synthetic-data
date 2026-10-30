# Pilot 7 agent guide

This repository evaluates agentic workflows for clinical data standardization.
Write for statistical programmers and biostatisticians familiar with CDISC.
Keep explanations short, concrete, and easy to follow.

## Repository map

- Each study has its own top-level folder with data, programs, specifications,
  outputs, and logs. The template is in `.github/repo-structure.json`.
- `spec/yamaa/` contains the yamaa templates that several studies'
  specifications inherit; its README states where each fact goes.
- `docs/` contains the project website; `mkdocs.yml` defines its navigation.
- `.github/scripts/` contains validation, comparison, and documentation tools.
- `.github/workflows/` contains CI and website deployment workflows.
- `.automation/` contains scheduled triage and weekly update prompts.
- `.archieve/` contains historical studies retained for reference.

## Working rules

- Use ASCII only in maintained documentation, source code, specifications,
  configuration, and automation prompts. Use `->`, `<=`, `-`, and straight
  quotes instead of Unicode arrows, symbols, punctuation, or emoji.
- Preserve original study data, published reference Define-XML, and archives.
  The ASCII checker excludes these artifacts; do not rewrite clinical values
  or reference metadata to satisfy an editorial rule. The exact policy is in
  `.github/scripts/check_ascii.py`. Any new exception needs a documented reason.
- Keep published ADaM references independent of derived outputs. Do not change
  reference datasets or relax comparison policies to make a check pass.
- Distinguish a successful build from a passed reference comparison. Report
  coverage and remaining work explicitly; agreement with a reference is not
  regulatory validation. See `docs/verification.md`.
- Preserve user edits and keep changes focused on the requested task.
- Write the framework name as lowercase `yamaa`.

## Website changes

- Edit `docs/index.md` for the landing page. Its first section routes
  reviewers to the Pilot 5 findings, the review guide and the study report.
- Edit `docs/review/index.md` for the community review guide and the pages
  beside it, `findings.md`, `workspace.md`, `documents.md` and
  `synthetic.md`, for the dashboard screen each one names. Keep the
  headings of those pages aligned with the labels in the dashboard.
- Edit `docs/studies/kn189.md` and `docs/studies/kn564.md` for synthetic studies.
- Generate pilot study pages and JSON evidence with
  `python3 .github/scripts/build_study_docs.py` after validating the studies.
  Do not hand-edit or commit these generated files.
- MkDocs renders landing-page metrics from `.build/validation` during the build.
  Keep the source block between the pilot-metrics markers as a website link;
  do not commit generated numbers to `docs/index.md`.
- The production dashboard generator is `.github/scripts/study_dashboard/`;
  browser modules are `docs/assets/dashboard/`, with `docs/stylesheets/dashboard.css`.
  Read the package README for study extension, artifact integrity, and tests.
  Add study-specific review questions under `<study>/spec/review/`, not shared code.
- Keep Responsibilities and Tools as separate sections. Describe human review,
  AI drafting, engine execution, and automated checks clearly.

## Checks before a push

Run the shared local and CI checks:

```bash
python3 .github/scripts/check_ascii.py
python3 .github/scripts/check_structure.py
python3 -m unittest discover -s .github/scripts -p 'test_*.py' -v
git diff --check
```

For a derivation change, also run
`python3 .github/scripts/validate_yamaa.py <study>` for the affected study.
For website changes, validate every study in `.github/yamaa-studies.json`,
install `docs/requirements.txt`, run
`python3 .github/scripts/verify_derivations.py <study> --reviewed` for each study
selected by `study_evidence.reviewed_datasets`. The `dataset_define` review
scope does not require multisource claim verification. Then
generate study pages with `python3 .github/scripts/build_study_docs.py`, and run
`python3 -m mkdocs build --strict`.

CI runs the ASCII check on pull requests and pushes to `main`. The website
build repeats it after generating study pages; a violation blocks deployment.

PR CI keeps shared checks in one job and selects additional study jobs from
the changed files. Site-only PRs use a layout preview with no study results.
Publication on main still requires fresh validation of the full study catalog.
See `.github/AUTOMATION.md` for scope rules and the reusable study worker.
