# Study dashboard maintenance

The production dashboard is part of the normal MkDocs site. There is one build
path and no study-specific frontend build. It uses static JSON and gzip chunks;
GitHub Discussions through giscus supplies comments without an application server.
The reviewer guide is `docs/review.md`.

## Source layout

```text
.github/dashboard.json                    shared defaults and comment service
.github/yamaa-studies.json                study publication catalog
.github/scripts/
  validate_yamaa.py                       execute and compare; record artifact hashes
  study_artifacts.py                     verify full input/output/source inventories
  stage_study_artifacts.py                transfer exact derived files between CI jobs
  build_study_docs.py                     stage, verify, and promote the complete bundle
  dashboard_nav.py                        discover native navigation from the catalog
  study_metrics.py                       independent-reference agreement totals
  study_dashboard/
    config.py                            settings and confined reference paths
    datasets.py                          CSV/Parquet adapters and subject chunks
    lineage.py                           conservative YAML dependencies and source spans
    domains.py                           dataset descriptions from retained Define-XML
    synthetic.py                         separate source/readiness manifests
    documents.py                         retained originals and searchable reading copies
    consistency.py                       metadata checks and source-backed review questions
    artifacts.py                         versioned study and gallery manifests
    pages.py                             accessible page shells and static fallback evidence
docs/assets/dashboard/
  app.js                                 lifecycle, events, and navigation
  state.js                               validated, shareable review URLs
  data.js                                versioned transport, subject selection, and search
  lineage.js                             dependency graph traversal
  review-model.js                        cross-specification identity and panel planning
  resize.js, synthetic.js                 sizing and synthetic-development views
  shell.js, workspace.js                 study layout and linked review panels
  report.js, comments.js, ui.js           evidence, discussions, and shared primitives
docs/stylesheets/dashboard.css           responsive layout and light/dark themes
.github/tests/dashboard/                 artifact, extension, module, and browser checks
<study>/spec/review/questions.json        optional authored review questions
```

Generated `docs/studies/`, `docs/evidence/`, and `site/` stay ignored. The bundle
is published under `evidence/dashboard/`; assets use URLs relative to the module
so GitHub Pages project prefixes and MkDocs instant navigation work together.
Heading-based URL tracking is disabled because dashboard fragments own review state.

## Add a study

1. Follow `.github/repo-structure.json`; stage independent source and reference
   data, YAML specifications, the project manifest, pinned engine requirements,
   and the study comparator. Keep generated ADaM outputs in `data/adam/` with
   the `-yamaa.parquet` suffix, separate from published reference files. Preserve
   existing comparison policies.
2. Add the study's title, description, upstream source, and comparison policy
   (`official` or `optional`) to `.github/yamaa-studies.json`. Navigation, gallery,
   study pages, and the CI publication matrix discover it automatically.
3. Optional `dashboard` settings in that catalog entry override shared defaults:

   ```json
   {
     "subject_key": "USUBJID",
     "default_subject_count": 3,
     "references": {"CUSTOM": "data/adam/published-name.parquet"}
   }
   ```

   Reference paths are study-relative. The default is
   `data/adam/<domain-lowercase>.parquet`. These settings identify files for
   display; the study comparator remains responsible for validating agreement.
   Supported displayed datasets are Parquet and CSV. CSV `types` declarations
   preserve text identifiers and convert declared numeric values and nulls.
4. Retain documents under `spec/source/` and list repo-relative paths in its
   `manifest.json` `files` array. Define-XML under `spec/define/` is discovered
   automatically. PDF pages, workbook rows, and Define variable sections have
   stable reading-copy anchors; originals are preserved. Missing declared sources
   remain visible. No source document is fetched during publication.
5. Optionally add `spec/review/questions.json`, with `schema_version: 1` and a
   `questions` array. Each question needs unique `id`, `dataset`, optional
   `variable`, `title`, study-relative `document`, `section`, exact `excerpt`,
   and `guidance`. Sections use `page-N`, `sheet-N-row-M`, or `DOMAIN.VARIABLE`.
   Whitespace-normalized excerpts must occur in the declared section. Verified
   questions are Not reviewed; missing/changed evidence is flagged explicitly.
   Do not put study narrative rules in the shared generator.
6. Validate and run the complete publication commands below. For an unstarted
   optional study, set `allow_pending: true` and omit the project file. It receives
   an explicit pending page and never contributes passing results.

Shared defaults and giscus identifiers live in `.github/dashboard.json`.
Keep the existing `term_prefix` and study/dataset IDs to retain discussion threads.
Current comments use the yamaa Discussions repository, with separate Pilot 7
terms, as Pilot 7 does not have Discussions enabled.

## Build and verify

Install each study's pinned requirements and `docs/requirements.txt`, then:

```bash
export GITHUB_SHA=$(git rev-parse HEAD)
python .github/scripts/validate_yamaa.py cdiscpilot01
python .github/scripts/validate_yamaa.py submission-pilot3
python .github/scripts/validate_yamaa.py submission-pilot5
python .github/scripts/build_study_docs.py
python .github/scripts/check_ascii.py
python -m mkdocs build --strict
python -m unittest discover -s .github/scripts -p 'test_*.py' -v
python -m pip install -r .github/tests/dashboard/requirements.txt
python -m playwright install chromium
bash .github/scripts/check_dashboard.sh site
```

Use the catalog's full study list when it changes. Node 22+ runs dependency-free
module tests. Browser checks require Chromium; `browser.py --browser-path PATH`
can use an installed browser. The browser suite exercises real study bundles,
project prefixes, full-width layout, ten-row paging, lineage in each direction, source links,
instant navigation, retryable fetches, mobile, and dark mode. It intercepts the
comment widget and checks its configuration without signing in or posting.

## Evidence and publication contract

Every nonpending validation record inventories SHA256 hashes for clinical inputs,
independent references, generated outputs, study specifications/documents,
Python programs, and shared execution configuration. Publication checks the
source commit, engine pin, complete dataset records, build/comparison statuses,
and the exact artifact inventory before and after export. Changes, additions,
and deletions require fresh validation, including ignored generated files.
The previous bundle stays intact when generation or verification fails.

CI transfers validated generated Parquet bytes as `derived-<study>` artifacts,
preserving repository-relative paths; the publication job verifies them again.
Both the PR publication check and main deployment run the same strict build
and dashboard tests. Main publishes through the existing GitHub Pages workflow.
Dashboard code, configuration, test, and source-document changes select the full
publication check. Ordinary website prose retains the cheaper layout preview.

Manifests (`index.json`, each study's `catalog.json`, `report.json`, and spec
JSON) declare `schema_version: 1`. Unsupported versions fail visibly in the
browser. Catalog tables contain typed columns, total rows, subject index,
source path/hash, download URL, and chunk URLs. Compressed chunks are arrays
`[original_row_ordinal, ...values]`, grouped by subjects; the browser restores
source ordering and pages the display at 10, 25, 50, or 100 rows per panel without
limiting subject selection.
Subject-independent lookups stay visible. Dates use ISO text; nonfinite numbers
use explicit text. Complete source files remain in the bundle for evidence; table download controls
are omitted from the reviewer interface. Keep generation and
browser schema versions aligned when changing this contract.

New consistency checks belong in `consistency.py`, document adapters in
`documents.py`, dataset adapters in `datasets.py`, and UI components alongside
`workspace.js`. Add meaningful boundary coverage with each new capability.

## Dataset comparisons and synthetic workspaces

`review-model.js` scopes each specification's nodes before joining lineage
through shared derived tables. It plans manually selected input/output panels,
automatically linked input datasets, and related columns. Equal column names
in different datasets remain distinct. `resize.js` owns pane and column sizing;
`workspace.js` renders independent table pages with 10/25/50/100 row choices.
The shared URL records compared datasets and per-panel row counts. Layout sizes
are local view state. Changing the focused specification preserves comparisons.

`domains.py` reads dataset descriptions from retained Define-XML, with browser
fallbacks for common domains and lookup tables. Adding a domain does not require
a study-specific UI branch.

Synthetic studies are declared separately in `.github/synthetic-studies.json`.
`synthetic.py` inspects source archive headers and staged-file availability,
without extracting the archive or loading its clinical XML. It writes small
source/readiness manifests under `synthetic/` in the evidence bundle.
`synthetic.js` provides the distinct development dashboard. Availability is
separate from derivation and comparison success. Original archives stay in the
repository and are linked at the publication revision.

To add a synthetic workspace, add its title, description, and study-relative
archive paths to that catalog and create a maintained page like
`docs/studies/kn189.md` with a `synthetic-dashboard` container and `data-study`
matching the catalog key. Navigation and source inventory follow the catalog.
Keep a study in the catalog for its intended purpose; pilot verification and
synthetic source development use different dashboard contracts.
