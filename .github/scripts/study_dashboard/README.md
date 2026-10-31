# Study dashboard maintenance

The production dashboard is part of the normal MkDocs site. There is one build
path and no study-specific frontend build. It uses static JSON and gzip chunks;
GitHub Discussions through giscus supplies comments without an application server.
The reviewer guide is `docs/review/index.md`; the pages beside it describe
each dashboard screen.

All pilot studies share the same tabs, finding filters and Start review
sections: Define-XML vs. reproduced yamaa specification from ADaM data,
subject examples and Human Review. Studies supply their own data, documents
and review claims; committed claims require the same derivation verification
for publication.

## Source layout

```text
.github/dashboard.json                    shared defaults and comment service
.github/yamaa-studies.json                study publication catalog
.github/scripts/
  validate_yamaa.py                       execute and compare; record artifact hashes
  study_artifacts.py                     verify full input/output/source inventories
    study_define.py                        native ADaM Define-XML metadata comparison
  stage_study_artifacts.py                transfer exact derived files between CI jobs
  build_study_docs.py                     stage, verify, and promote the complete bundle
  dashboard_nav.py                        discover native navigation from the catalog
  study_metrics.py                       independent-reference agreement totals
  study_dashboard/
    config.py                            settings and confined reference paths
    datasets.py                          CSV/Parquet adapters and subject chunks
    lineage.py                           conservative YAML dependencies and source spans
    references.py                        scoped lookup keys and expression-local bindings
    specifications.py                    portable engine-resolved models and original sources
    domains.py                           dataset descriptions from retained Define-XML
    synthetic.py                         separate source and development manifests
    documents.py                         retained originals and searchable reading copies
    document_views.py                    workbook tables and original XML HTML
    define_comparison.py                 exact compared XML and numbered source views
    consistency.py                       metadata checks and source-backed review questions
    rule_review.py                       documented-rule checks from the verification report
    issues.py                            validated issue grouping and normalized evidence
    artifacts.py                         versioned study and gallery manifests
    workspace.py                         shared pilot and synthetic study workspace
    pages.py                             study page shells and the static two-page study report
docs/assets/dashboard/
  app.js                                 lifecycle, events, and navigation
  state.js                               validated, shareable review URLs
  data.js                                versioned transport, subject selection, and search
  lineage.js                             dependency graph traversal
  review-model.js                        cross-specification identity and panel planning
  specification.js                       focused derivation context with original source lines
  resize.js, synthetic.js                 sizing and synthetic-development views
  shell.js, workspace.js                 study layout and linked review panels
  source-documents.js                    independent file tabs and two original viewers
  workbook.js                            worksheet tabs and multi-sheet comparison
  define-comparison.js                   original/generated XML and metadata differences
  report.js, comments.js, ui.js           evidence, discussions, and shared primitives
  issues.js                              concise issues, progressive traces and check aliases
  trace-review.js                        expanded evidence and per-finding human review
  review-drafts.js                       browser-local assessments bound to reviewed evidence
docs/stylesheets/dashboard.css           responsive layout and light/dark themes
.github/tests/dashboard/                 artifact, extension, module, and browser checks
<study>/spec/review/questions.json        optional authored review questions
<synthetic-study>/spec/review/findings.json  coverage, gaps and review decisions
```

Generated `docs/studies/`, `docs/evidence/`, and `site/` stay ignored. The bundle
is published under `evidence/dashboard/`; assets use URLs relative to the module
so GitHub Pages project prefixes and MkDocs instant navigation work together.
Heading-based URL tracking is disabled because dashboard fragments own review state.

Synthetic studies remain in `.github/synthetic-studies.json`. Their pinned
engine is installed separately by `synthetic-check.yml`; `validate_synthetic.py`
builds SDTM/ADaM and submission files through yamaa. `synthetic_checks.py`
independently checks keys, subject coverage, every XPT cell and the retained
CDISC Define-XML XSD. The report binds all inputs, specifications and outputs
to their bytes; missing, stale or failed required evidence blocks publication.
`synthetic_evidence.py --stage <study>` transfers exact files between CI jobs.
The frontend `synthetic-development.js` renders coverage and unresolved findings
and exports browser-local human review drafts without applying them.
After validating both synthetic studies, `python .github/scripts/export_synthetic_review.py`
packages a portable review in `.build/kn189-kn564-review.zip`. It embeds the same
production components and exact study manifests, with source and download files
beside `review.html`; it needs no external scripts or server. Local preview of
the existing website uses `python .github/scripts/preview_site.py` and keeps
official pilot results explicitly omitted when their evidence is unavailable.

## Add a study

1. Follow `.github/repo-structure.json`; stage independent source and reference
   data, YAML specifications, the project manifest, pinned engine requirements,
   and the study comparator. Keep generated ADaM outputs in `data/adam/` with
   the `-yamaa.parquet` suffix, separate from published reference files. Preserve
   existing comparison policies.
2. Add the study's title, description, upstream source, and comparison policy
   (`official` or `optional`) to `.github/yamaa-studies.json`. Navigation, the
   study report, study pages, and the CI publication matrix discover it automatically.
   The report reads the staged bundle, so it adds a column for the study and rows
   for its datasets. Keep it within two printed pages.
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
   remain visible. XML entries can declare a repo-relative `stylesheet` and its
   `stylesheet_upstream` provenance URL. Retain the exact publisher stylesheet;
   it is included in artifact verification, even when shared across studies.
   Publication renders the original HTML using lxml with external resource access
   disabled. PDF originals are embedded directly; workbook HTML preserves sheet,
   row and column positions and merged cells. No source document is fetched
   during publication. Workbook tables use the full viewer width and omit blank
   rows while retaining original row numbers and citation anchors. Each worksheet
   has its own tab and uses the dashboard's shared review-table styles. Compare
   worksheets selects multiple tabs for independently scrollable tables; narrow
   screens stack them. Row citations reveal their worksheet automatically.
   Source documents use the original views only, with one or
   two independent tabbed panes; extracted text is kept for consistency checks.
   Retained R programs have syntax colors generated with Pygments and embedded
   styles, so viewing code needs no external scripts or network requests. Program
   text, line numbers, citation ranges and upstream links are preserved.
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
terms. `comments.review_url` names GitHub's new-discussion composer for reviewer
assessments, `https://github.com/<owner>/<repo>/discussions/new?category=<slug>`;
it points at this repository's General category and can name any repository
with Discussions enabled, or a dedicated category once one exists.

The review dialog prepares a structured reviewer assessment. **Submit review on
GitHub** opens that composer in a new tab with the assessment in its `title` and
`body` query parameters, the prefill GitHub documents for issues and honours for
discussions. The reviewer signs in to GitHub if needed and selects Start
discussion, so the post carries their identity and no server, token or GitHub
App stands between the static site and GitHub. GitHub's OAuth token exchange
has no CORS support and needs a client secret, so a static page cannot post on
a reviewer's behalf by itself. A link over 8,000 characters is not sent: the
composer then opens with the title only and the dialog keeps the text to paste.
Without `review_url`, the dialog falls back to **Copy review**.

Prepared review text remains selectable under **Human Review** for manual copying.
Opening the composer, copying or saving locally never reports a successful
GitHub post. Browser checks intercept the
composer tab; they do not exercise GitHub sign-in or post real discussions.

## Build and verify

Install each study's pinned requirements and `docs/requirements.txt`, then:

```bash
export GITHUB_SHA=$(git rev-parse HEAD)
python .github/scripts/validate_yamaa.py cdiscpilot01
python .github/scripts/validate_yamaa.py submission-pilot3
python .github/scripts/validate_yamaa.py submission-pilot5
python .github/scripts/verify_derivations.py cdiscpilot01 --reviewed
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

Validation also records the retained SDTM and ADaM Define-XML versions. When a
project declares an ADaM `define` output, validation composes it with the pinned
engine and compares its metadata using `define_metadata.py`. The `define_xml`
record retains the comparison, both XML hashes, and the generated version.
Projects without that output say Not compared. This metadata agreement is
separate from dataset agreement, XML byte identity, schema validation, and data
conformance. The study report groups source information, SDTM, and ADaM rows;
both study and dataset table headers link to each study workspace.
Dataset result badges count `report.review.issues` for that dataset, separately
from their supporting checks, and nonzero badges link to its filtered issue list.

The pilot workspace's Define-XML comparison tab shows the original and generated
ADaM XML side by side using the retained publisher stylesheets, with independent
numbered source and download links. The source manifest selects the reference's
stylesheet; matching generated versions reuse it. `define_stylesheets` in
`.github/dashboard.json` maps other Define-XML versions to retained stylesheets,
which join the study's artifact inventory. A version without a retained stylesheet
shows its explicitly labeled numbered source view instead.
It lists the validation job's metadata differences and retains unsupported legacy content,
unresolved source declarations and version-mapping policies. Generated XML joins
the artifact inventory and cross-job transfer; publication verifies both compared
XML files against the recorded hashes before rendering their HTML and creating
their escaped source views. Rendering uses the Source documents XSLT adapter,
with external resource access disabled; publisher scripts run in isolated iframes.
The tab has a shareable `#<study>/define/<dataset>` route and stacks its panes on
small screens. No XML comparison is recomputed in the browser.

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
Panels grow to fit the current page; the specification stays sticky on desktop.
Table metadata includes declared `keys` and their repository `key_source`.
SDTM/reference keys come from Define-XML (DomainKeys or KeySequence); derived
keys come from yamaa specifications. Related-column views retain these keys.
Subject-independent lookups stay visible. Dates use ISO text; nonfinite numbers
use explicit text. Complete source files remain in the bundle for evidence; table download controls
are omitted from the reviewer interface. Keep generation and
browser schema versions aligned when changing this contract.

New consistency checks belong in `consistency.py`, document adapters in
`documents.py`, dataset adapters in `datasets.py`, and UI components alongside
`workspace.js`. Add meaningful boundary coverage with each new capability.

## Derivation verification

`.github/scripts/verify_derivations.py` compares each derivation with the
document text that states it and writes `report.json`, `report.md` and the
citable `sections/` text under `.build/verification/<study>/`. Run it with the
study's pinned engine requirements and the documentation requirements:

```bash
python .github/scripts/verify_derivations.py cdiscpilot01 --dataset ADSL
python .github/scripts/verify_derivations.py cdiscpilot01 --reviewed
```

`--reviewed` verifies the datasets with a committed
`<study>/spec/review/<dataset>-claims.json`, as publication does. The study
validation job runs it there, where the pinned engine runs the probes, and
uploads `report.json` and `report.md` as the `verification-<study>` artifact.
`build_study_docs.py` reads them from `.build/verification/<study>/`, and
`validate_verifications` refuses a report from another commit or engine, or one
that does not cover exactly the reviewed datasets. A study with reviewed
datasets cannot publish without one. `rule_review.py` preserves the underlying
checks and adds document links. `issues.py` groups them using the versioned
[issue schema](issue-schema.md); the JSON Schemas live in `.github/schemas/`.
`docs/assets/dashboard/issues.js` renders concise issue rows and progressively
expanded trace evidence from that contract. Rows show dataset/variable, status,
criticality badge, type badge, issue and evidence in that order. Impact,
criticality reasons and agent review remain in the expanded trace. Verified
clauses without authored grouping share a row only for the same variable and
exact source-file pair; all supporting checks and quotations remain available.
Both the metric and the static study
report count issues. The table separately counts unique supporting checks.
The Start review button opens an expanded dialog, keeping complete evidence out of the
initial listing DOM. Its first panel pairs only the cited Define-XML item with
the selected variable's resolved YAML, preserving source links and line numbers.
The second panel shows **ADaM data** and **Documented Rule** in two columns;
record keys and inputs accompany the data value. Alternative interpretations
and open-question panels are omitted. **Human Review** asks for agreement,
criticality, then optional dataset correctness.

`review_scope.py` projects the complete check audit into outstanding findings
between actual ADaM data and original Define-XML. It keeps observed data and
metadata discrepancies, invalid documented sources, and verified contradictory
or incomplete rules requiring clarification. YAML-only and program-only
differences remain in the raw audit. A conditional interpretation does not supply
literal-rule impact, and an assessment limit does not establish a data error.

Direct dataset checks read original predecessor origins and legacy value-level
metadata rather than treating reading-copy omissions as missing documentation.
Integer checks inspect actual values, enumerated numeric codelists tolerate
representation noise, and `SignificantDigits` does not imply an algorithmic
rounding step. A key declaration establishes the declared key order; it does
not by itself state that every key component must be nonmissing.

Reviewed publication decisions live in
`<study>/spec/review/publication.json` or per-dataset
`<dataset>-publication.json`. Their versioned schema binds the original
Define-XML SHA256 and identifies current check IDs, a reason and the disposition
`finding`, `clarification`, `coverage` or `exclude`. An optional check basis
binds a decision to its evidence, and a shared group can combine supporting
checks for one root problem. Unknown IDs and changed bound evidence fail
publication rather than silently dropping a review decision.

`report.review.issues` counts grouped findings. Supporting checks are counted
separately, and `report.coverage_items` lists checks awaiting evidence or a
supported assessment as `{id, dataset, variable, title, reason}` entries.
`scope_summary` records finding, check and coverage totals. The frontend shows
study-wide coverage below the findings without adding it to findings or subject
impact. Original raw findings, logic checks and the standalone verification
report retain the complete audit. The projected review keeps valid check and
evidence relationships so dataset badges, counts, sibling navigation and direct
links share the same scope.

Human agreement, criticality and comments are browser-local assessments. Neither
decision is preselected. Drafts save automatically as the reviewer edits; there
is no separate local-save action. A draft does not resolve the finding or
replace agent adjudication or automated criticality. Drafts are scoped to the
study and issue and bound to its current evidence; changed evidence returns an
earlier assessment as a draft. The copied GitHub comment retains source revision
and check IDs. No review is posted to GitHub automatically. Use a GitHub discussion or the workspace's dataset Comments box to
publish the copied assessment.

The verifier retains row-aligned examples from the actual reference, yamaa and
probe tables. It chooses complementary subjects from measured differences where
available, preserves missing/blank/absent distinctions, and labels abbreviated
subject records. The browser shows at most two subjects. Examples do not supply
impact counts, and an unavailable example never becomes invented data. Optional
claim `example_columns` adds reference context such as an event term; dependencies
read from REF or its base input are included automatically. The verifier also
walks the reproduced YAML's local variable dependencies, including selection
context, and includes those present in the same ADaM reference dataset. Keys and
the compared variable are not repeated as input columns. External input fields
are not matched by name to ADaM fields. These columns display reference values,
not a contributing-row trace or a rerun of the upstream derivation.
Alternate calculations use their
plain-language `reading` descriptions; VARIABLE__READING names remain in the generated verification report.

Retained ADaM programs, listed in a study's source manifest with the role
`adam_program` or `reference_reimplementation`, are cited by line range
(`L<first>-L<last>`). The verifier checks the quote inside those lines and
links the repository and upstream lines; `documents.py` renders the program
as numbered lines that mark the cited range. A program shows how the
reference was computed, so a claim that cites only program lines leaves the
variable undocumented (CR-11), and its finding shows the lines.

Author `<study>/spec/review/<dataset>-issues.json` to group related checks.
Inventory every check and its basis hash, then write short issue titles,
expected/observed behavior and actions. Explicit data and citation selectors
keep a shared check's unrelated evidence out of the primary trace. Counts come
from complete measured data, never editorial text or truncated samples. Missing
checks, stale bases, unresolved selectors and invalid schema relations block
publication. The previous published bundle remains intact.

The generated `report.json` retains raw `findings` and `logic_checks` for audit
and adds `review` with its own `schema_version: 1`, normalized issues, checks,
evidence and counts. The browser rejects unsupported review versions. Old URLs
with a check ID resolve to its first related issue. Dataset workspaces select
only the issue's measured subjects. Agent agreement remains separate from issue
resolution. Standalone verifier `report.md` remains the complete check audit.

`.automation/consistency_review/workflow.md` is the agentic workflow around it.
Agents propose and the script decides. The extraction agent writes
`<study>/spec/review/<dataset>-claims.json` (verbatim citations, and clauses
that quote both the document and a specification element) and
`<dataset>-documented-rules.yaml`, a yamaa specification that states each documented rule
literally. An independent adjudicator writes `<dataset>-adjudication.json`. The
script accepts a quote only when it is found where it is cited: a section that
`documents.py` extracts, the text the dashboard's reading copy shows, or a
specification element that `lineage.py` locates. It runs the probes, compares
them with the reference and the yamaa output, and turns each inconsistency into
a finding citing one rule of `.automation/consistency_review/rules.yaml`.
Define-XML copies such as `DM.AGE` and codelist values are checked without an
agent. `consistency_report.py` renders `report.md` from `report.json` alone:
each finding quotes its rule, shows the document and specification quotes with
links to the reading copy, the original page or XML lines and the
specification lines, and lists the differing records. Findings are not
regulatory validation; each awaits a person's decision.

Adjudication state can store the finding's `basis_fingerprint` in its `basis`
field instead of duplicating the complete evidence string. The verifier
recomputes this SHA-256 fingerprint from the full current basis; legacy full-text
decisions remain valid, and changed evidence still makes either format stale.
The generated report retains the full basis, quotations and record comparisons.

## Dataset comparisons and synthetic workspaces

`review-model.js` scopes each specification's nodes before joining lineage
through shared derived tables. It plans manually selected input/output panels,
automatically linked input datasets, and related columns. Equal column names
in different datasets remain distinct. `resize.js` owns pane and column sizing;
`workspace.js` renders independent table pages with 10/25/50/100 row choices.
The shared URL records compared datasets and per-panel row counts. Layout sizes
are local view state. Changing the focused specification preserves comparisons.

The YAML view uses upstream dependencies for a selected variable. Source-location
metadata identifies input members, `output.columns`, row drivers and intermediate
derivations, so the browser can hide unrelated declarations and field expressions
without altering the source file. Inline mappings retain their visible members
and original line anchors. Clearing focus or choosing All columns restores the
complete specification. Manually pinned data panes do not add unrelated YAML
input declarations to a variable's derivation view.

Column lineage attaches an input's matching keys only when that input is read.
Named lookups retain their own key pairs, filters and record-selection order;
one field does not inherit sibling field derivations. Row filters and grouping
remain dependencies of the values those rows produce, and row overrides replace
the corresponding root derivation. Aggregate-local names are scoped separately
from output columns and unused local expressions do not add sources. Final
output sort references are recorded as `output_order`, separately from column
value dependencies. This remains a conservative static index across declared
branches, not contributing-row provenance.

Each study saves executable composed specifications and `project.yaml` under
`spec/yamaa/resolved/`, with provenance in separate `*.inspection.json` records.
Validation checks them against fresh resolution and executes the composed
project. It records both YAML and inspection-record paths and SHA-256 hashes.
Downstream readers load that saved evidence. Validation records
`resolved_specification` inspection packets with the pinned
engine's normalized model, mapping order, original sources, origins and resolved
resource locations. Publication checks source text against the artifact inventory
and uses those facts without installing the engine. Copies, includes, inheritance
and named windows require fresh resolved evidence; they are never approximated
from authored YAML. Resolved dataset resources must be in the study's artifact
inventory. Schema-default origins name engine schema modules, not study files.
The workspace displays the exact executable composed YAML and links to its
complete file in the repository. Focused views mark omitted lines.

`domains.py` reads dataset descriptions from retained Define-XML, with browser
fallbacks for common domains and lookup tables. Adding a domain does not require
a study-specific UI branch.

Synthetic studies are declared separately in `.github/synthetic-studies.json`.
`synthetic.py` inspects source archive headers and staged-file availability,
without extracting the archive or loading its clinical XML. It writes small
source/readiness manifests under `synthetic/` in the evidence bundle.
`synthetic.js` renders the overview and individual studies with the shared
report metrics, study tables, workflow readiness, and archive inventories.
KN189 and KN564 use `workspace.py` and the same linked specification/data
dashboard as the pilot studies. Their Analysis development tab retains build
evidence, downloads, findings and browser-local review drafts. Synthetic build
records carry engine-resolved specification packets; publication verifies their
source texts and input/output inventories before exporting a workspace.
Availability is separate from derivation and comparison success. Original
archives stay in the repository and are linked at the publication revision.

To add a synthetic workspace, add its title, description, and study-relative
archive paths to that catalog and create a maintained page like
`docs/studies/kn189.md` with a `synthetic-dashboard` container, the
`study-report synthetic-report` classes, and `data-study` matching the catalog
key. Navigation and source inventory follow the catalog.
Keep a study in the catalog for its intended purpose; pilot verification and
synthetic source development use different dashboard contracts.

Use a `study-dashboard` container for a synthetic study with a required build
and a linked workspace. Studies validated through the pilot build worker can
set `category: synthetic` in `.github/yamaa-studies.json` to appear under
Synthetic data and in its overview while retaining their existing validation
path. They do not contribute to the pilot report or landing-page pilot metrics.
