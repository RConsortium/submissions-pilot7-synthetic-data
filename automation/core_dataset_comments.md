# CORE dataset validation comment automation

You are running on a schedule against the `RConsortium/submissions-pilot7-synthetic-data`
repository. Your job is to read the latest CDISC CORE validation report(s) and
post validation findings as comments on open issues that mention specific
dataset names (ADAE, ADQS, ADSL, etc.).

Treat this file as the full job. Do not ask clarifying questions — make the
call yourself and document the reasoning in the comment.

---

## Inputs you can rely on

- Git root: the parent of this `automation/` folder
- CORE reports: JSON files matching `core-report-*.json` in git root.
  There may be more than one (e.g. a separate SDTM report and ADaM report).
  Detect domain coverage automatically — do not assume one file covers both.
  (The `.xlsx` twins of these files are for humans; parse the `.json`.)
- Tooling: `git` is configured, `Rscript` is available. `gh` may or may not
  be installed — detect it and fall back to `curl` if absent (see Step 1).
- Bot identity: sign comments with `_(posted by CDISC CORE validation report)_`

---

## Step 0 — Bootstrap R + packages (always, every run)

Before doing anything else, ensure R and packages are available:

```bash
bash automation/bootstrap_system.sh
Rscript automation/bootstrap_r.R
```

If either exits non-zero, stop the whole run and exit non-zero.

Also ensure the system R library has the packages needed for this script
(`jsonlite`, `dplyr`). These are not in the renv lockfile (they run outside
renv). Install any that are missing:

```bash
Rscript --vanilla -e "
  pkgs <- c('jsonlite', 'dplyr')
  missing <- pkgs[!pkgs %in% rownames(installed.packages())]
  if (length(missing) > 0) {
    install.packages(missing, repos='https://cloud.r-project.org', quiet=TRUE)
  }
  cat('packages ok\n')
"
```

---

## Step 1 — Detect GitHub API transport

`gh` may not be installed. Detect it once and use the appropriate method
for all subsequent GitHub calls in this run:

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
  GH_MODE="gh"
else
  GH_MODE="curl"
  GH_TOKEN=$(printf "protocol=https\nhost=github.com\n" | git credential fill 2>/dev/null \
    | grep ^password | cut -d= -f2)
  if [[ -z "$GH_TOKEN" ]]; then
    echo "ERROR: gh not available and no GitHub credential found. Cannot proceed."
    exit 1
  fi
fi
echo "GitHub transport: $GH_MODE"
```

Use this pattern for every subsequent GitHub API call:
- If `GH_MODE=gh`: use `gh` CLI commands as written.
- If `GH_MODE=curl`: replace each `gh` call with the equivalent `curl` call
  using `-H "Authorization: token $GH_TOKEN"` against `https://api.github.com/repos/RConsortium/submissions-pilot7-synthetic-data`.

---

## Step 2 — Resolve a cross-platform temp directory

`/tmp` is not visible to Windows R. Get the platform-safe path once and
reuse it for all temp files in this run:

```bash
R_TMPDIR=$(Rscript --vanilla -e 'cat(tempdir())' 2>/dev/null)
echo "Temp dir: $R_TMPDIR"
```

Use `$R_TMPDIR` (not `/tmp`) for all temp file paths throughout this run.

---

## Step 3 — Find and catalogue CORE reports

There may be one file per standard (SDTM, ADaM) or several. Read every JSON
report and record which datasets/domains each covers. Domain coverage is
derived from the report's `Dataset_Details` (and `Issue_Summary`) datasets,
normalised to upper-case domain names with any `.xpt` suffix stripped.

```bash
Rscript --vanilla - "$R_TMPDIR" <<'RSCRIPT'
library(jsonlite)

tmp <- commandArgs(trailingOnly=TRUE)[1]

reports <- list.files(".", pattern="^core-report-.*\\.json$", full.names=TRUE)
reports <- reports[order(file.mtime(reports), decreasing=TRUE)]  # newest first

if (length(reports) == 0) {
  cat("NO_REPORTS\n")
  quit(status=0)
}

norm_domain <- function(x) toupper(sub("\\.xpt$", "", x, ignore.case=TRUE))

catalogue <- lapply(reports, function(f) {
  rpt <- tryCatch(fromJSON(f, simplifyVector=FALSE), error=function(e) NULL)
  if (is.null(rpt)) return(NULL)
  ds <- character(0)
  if (!is.null(rpt$Dataset_Details))
    ds <- c(ds, vapply(rpt$Dataset_Details, function(d) d$filename %||% "", ""))
  if (!is.null(rpt$Issue_Summary))
    ds <- c(ds, vapply(rpt$Issue_Summary, function(d) d$dataset %||% "", ""))
  domains <- unique(norm_domain(ds[nzchar(ds)]))
  list(file=basename(f), path=f, domains=domains)
})
catalogue <- Filter(Negate(is.null), catalogue)

writeLines(toJSON(catalogue, auto_unbox=TRUE), file.path(tmp, "core_catalogue.json"))
cat(sprintf("Catalogued %d report(s)\n", length(catalogue)))
for (r in catalogue)
  cat(sprintf("  %s -> [%s]\n", r$file, paste(r$domains, collapse=",")))
RSCRIPT
```

If the script prints `NO_REPORTS`, stop: no CORE reports found.

---

## Step 4 — Create label if missing

```bash
# gh mode
gh label create core-commented \
  --description "Validation findings posted from CORE report" \
  --color D4C5F9 2>/dev/null || true

# curl mode equivalent
curl -s -X POST \
  -H "Authorization: token $GH_TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"core-commented","color":"D4C5F9","description":"Validation findings posted from CORE report"}' \
  "https://api.github.com/repos/RConsortium/submissions-pilot7-synthetic-data/labels" > /dev/null
```

---

## Step 5 — Fetch all open issues

```bash
issues_file="$R_TMPDIR/open_issues.json"

# gh mode
gh issue list --state open --json number,title,body,labels --limit 100 > "$issues_file"

# curl mode equivalent
curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/repos/RConsortium/submissions-pilot7-synthetic-data/issues?state=open&per_page=100" \
  -o "$issues_file"
```

---

## Step 6 — Per-issue loop

Process issues **oldest-first** (lowest issue number first). Resolve one
issue completely (generate → post → label) before moving to the next.

### 6a — Check skip labels

Skip the issue if it carries any of: `core-commented`, `wontfix`,
`duplicate`, `invalid`.

**Do NOT skip** issues labeled `claude-needs-human` — CORE validation
findings should be posted regardless of triage state.

### 6b — Match datasets using word-boundary search

Use `grep -w` (whole-word matching) to avoid false positives from
short domain names appearing as substrings in common words (e.g. "CE"
inside "process", "DM" inside "odm").

```bash
matched_datasets=""
for dataset in ADSL ADAE ADLB ADCM ADQS ADMH ADCE ADDS ADIE DM AE LB CM QS MH CE DS IE EX; do
  if echo "$issue_title $issue_body" | grep -iqw "$dataset"; then
    matched_datasets="$matched_datasets $dataset"
  fi
done
matched_datasets=$(echo $matched_datasets)  # trim whitespace

if [[ -z "$matched_datasets" ]]; then
  echo "Issue #$issue_num: no dataset names found, skipping"
  continue
fi
```

### 6c — Check for existing comment on the same report(s)

Fetch the issue's comments and skip if any comment body already contains
the report filename(s) that would be used for this issue. This prevents
duplicate posts when the routine fires more than once.

```bash
# gh mode
existing=$(gh issue view "$issue_num" --json comments \
  --jq ".comments[].body" | grep -l "$report_filename" | head -1)

# curl mode equivalent: fetch comments and grep for filename
curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/repos/RConsortium/submissions-pilot7-synthetic-data/issues/$issue_num/comments" \
  | grep -q "$report_filename" && existing="yes" || existing=""

if [[ -n "$existing" ]]; then
  echo "Issue #$issue_num: already commented for this report, labeling and skipping"
  # apply label then skip
  continue
fi
```

### 6d — Generate comment

Use R to read the report(s) and write both a markdown file and a JSON body
file. **Always pass `--vanilla`** to prevent renv from activating.

The CORE JSON report has these top-level keys (spaces/hyphens → underscores):
`Conformance_Details` (object), `Dataset_Details`, `Issue_Summary`
(`{dataset, core_id, message, issues}`), `Issue_Details`
(`{core_id, message, executability, dataset, USUBJID, row, SEQ, variables[], values[]}`),
and `Rules_Report`. Match a domain against the `dataset` field, upper-cased
with any `.xpt` suffix removed.

```bash
Rscript --vanilla - "$issue_num" "$R_TMPDIR" $matched_datasets <<'RSCRIPT'
library(jsonlite)
library(dplyr)

`%||%` <- function(a, b) if (is.null(a) || length(a) == 0) b else a

args         <- commandArgs(trailingOnly=TRUE)
issue_num    <- args[1]
tmp          <- args[2]
datasets     <- args[3:length(args)]

norm_domain <- function(x) toupper(sub("\\.xpt$", "", x, ignore.case=TRUE))

# Load report catalogue built in Step 3
catalogue <- fromJSON(readLines(file.path(tmp, "core_catalogue.json"), warn=FALSE),
                      simplifyVector=FALSE)

# Cache parsed reports so each file is read at most once
report_cache <- new.env()
load_report <- function(path) {
  if (!is.null(report_cache[[path]])) return(report_cache[[path]])
  rpt <- fromJSON(path, simplifyVector=FALSE)
  report_cache[[path]] <- rpt
  rpt
}

# Helper: find the best report for a given domain
best_report <- function(domain) {
  for (r in catalogue) if (domain %in% unlist(r$domains)) return(r)
  NULL
}

join_vec <- function(v) {
  if (is.null(v) || length(v) == 0) return("-")
  paste(vapply(v, function(x) if (is.null(x)) "null" else as.character(x), ""),
        collapse=";")
}

block_for_domain <- function(domain) {
  rep <- best_report(domain)
  lines <- c(sprintf("### %s", domain), "")
  if (is.null(rep)) {
    return(c(lines, sprintf("No CORE report found covering domain %s.", domain), ""))
  }

  rpt     <- load_report(rep$path)
  summary <- rpt$Issue_Summary %||% list()
  details <- rpt$Issue_Details %||% list()

  # Rows for this domain
  srows <- Filter(function(x) norm_domain(x$dataset %||% "") == domain, summary)
  drows <- Filter(function(x) norm_domain(x$dataset %||% "") == domain, details)

  if (length(srows) == 0 && length(drows) == 0) {
    return(c(lines, sprintf("Report: `%s`", rep$file), "",
             "No validation issues found for this domain. ✅", ""))
  }

  total <- sum(vapply(srows, function(x) as.integer(x$issues %||% 0L), integer(1)))
  rule_ids <- unique(vapply(srows, function(x) x$core_id %||% "", ""))

  lines <- c(lines,
    sprintf("Report: `%s`", rep$file),
    sprintf("- **Total issues**: %d", total),
    sprintf("- **Unique rules**: %d", length(rule_ids)),
    "")

  # Issues by rule (top 10 by count)
  if (length(srows) > 0) {
    ord <- order(vapply(srows, function(x) as.integer(x$issues %||% 0L), integer(1)),
                 decreasing=TRUE)
    top <- srows[ord][seq_len(min(10, length(srows)))]
    lines <- c(lines, "**Issues by rule:**", "")
    for (s in top)
      lines <- c(lines, sprintf("- **%s** (%d): %s",
                                s$core_id %||% "?",
                                as.integer(s$issues %||% 0L),
                                s$message %||% ""))
    lines <- c(lines, "")
  }

  # Sample records (first 5 detail rows)
  if (length(drows) > 0) {
    samp <- drows[seq_len(min(5, length(drows)))]
    lines <- c(lines,
      "<details><summary>Sample records</summary>", "",
      "| Record | Variables | Values | Rule | Message |",
      "|--------|-----------|--------|------|---------|")
    for (d in samp) {
      rec  <- as.character(d$row %||% "-")
      vars <- substr(join_vec(d$variables), 1, 30)
      vals <- substr(join_vec(d$values),    1, 20)
      rule <- d$core_id %||% "-"
      msg  <- substr(d$message %||% "", 1, 70)
      lines <- c(lines, sprintf("| %s | %s | %s | %s | %s |", rec, vars, vals, rule, msg))
    }
    lines <- c(lines, "", "</details>", "")
  }
  lines
}

# Build full comment
comment <- c("## CDISC CORE Validation Findings", "")
for (d in datasets) comment <- c(comment, block_for_domain(d))
comment <- c(comment, "---", "", "_(posted by CDISC CORE validation report)_")

body_text  <- paste(comment, collapse="\n")
json_file  <- file.path(tmp, sprintf("core_body_%s.json", issue_num))
writeLines(toJSON(list(body=body_text), auto_unbox=TRUE), json_file)
cat(sprintf("Generated comment for issue #%s -> %s\n", issue_num, json_file))
RSCRIPT
```

### 6e — Post comment and label

Detect success by checking for `html_url` in the API response (not `"id":`,
which has a space after the colon and is easy to mis-parse).

```bash
json_file="$R_TMPDIR/core_body_${issue_num}.json"

if [[ ! -f "$json_file" ]]; then
  echo "Issue #$issue_num: comment generation failed, skipping"
  continue
fi

# gh mode
gh issue comment "$issue_num" --body-file <(jq -r '.body' "$json_file")
gh issue edit   "$issue_num" --add-label core-commented

# curl mode equivalent
resp=$(curl -s -X POST \
  -H "Authorization: token $GH_TOKEN" -H "Content-Type: application/json" \
  --data-binary "@$json_file" \
  "https://api.github.com/repos/RConsortium/submissions-pilot7-synthetic-data/issues/$issue_num/comments")

if echo "$resp" | grep -q '"html_url"'; then
  curl -s -X POST \
    -H "Authorization: token $GH_TOKEN" -H "Content-Type: application/json" \
    -d '{"labels":["core-commented"]}' \
    "https://api.github.com/repos/RConsortium/submissions-pilot7-synthetic-data/issues/$issue_num/labels" > /dev/null
  echo "Issue #$issue_num: posted and labeled"
else
  echo "Issue #$issue_num: POST failed — $(echo "$resp" | grep -o '"message":"[^"]*"' | head -1)"
fi

rm -f "$json_file"
```

---

## Hard rules

- **Never** close issues — only add comments and the `core-commented` label.
- **Never** modify other issue metadata (assignees, milestones, projects).
- **Never** comment more than once per issue per report (Step 6c prevents this).
- **Never** post to issues with no word-boundary dataset match.
- **Never** post an empty comment — if R generation fails, skip the issue.
- Process one issue at a time. A failure on one issue must not stop the loop.
- `claude-needs-human` does **not** block CORE comments. Post and label regardless.
- If a new report appears (new filename), posting is allowed even if
  `core-commented` is already set — the filename check in Step 6c prevents
  duplicates per report, not across all reports.

---

## End-of-run summary

After the loop, print this table to stdout:

```
Reports catalogued: core-report-SDTM.json (SDTM), core-report-ADAM.json (ADaM)

Issue  Dataset(s)       Action   Result
-----  ---------------  -------  ----------------------------------
#13    DM               Posted   5624 issues, 19 rules
#22    ADSL             Posted   2956 issues, 19 rules
#51    None             Skipped  no word-boundary dataset match
#53    ADAE             Skipped  already commented on this report
```

No other output. No file writes outside `$R_TMPDIR` and the repo tree.
