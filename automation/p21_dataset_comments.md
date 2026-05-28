# P21 dataset validation comment automation

You are running on a schedule against the `RConsortium/submissions-pilot7-synthetic-data`
repository. Your job is to read the latest Pinnacle21 validation report(s) and
post validation findings as comments on open issues that mention specific
dataset names (ADAE, ADQS, ADSL, etc.).

Treat this file as the full job. Do not ask clarifying questions — make the
call yourself and document the reasoning in the comment.

---

## Inputs you can rely on

- Git root: the parent of this `automation/` folder
- P21 reports: Excel files matching `pinnacle21-report-*.xlsx` in git root.
  There may be more than one (e.g. a separate SDTM report and ADaM report).
  Detect domain coverage automatically — do not assume one file covers both.
- Tooling: `git` is configured, `Rscript` is available. `gh` may or may not
  be installed — detect it and fall back to `curl` if absent (see Step 1).
- Bot identity: sign comments with `_(posted by P21 validation report)_`

---

## Step 0 — Bootstrap R + packages (always, every run)

Before doing anything else, ensure R and packages are available:

```bash
bash automation/bootstrap_system.sh
Rscript automation/bootstrap_r.R
```

If either exits non-zero, stop the whole run and exit non-zero.

Also ensure the system R library has the packages needed for this script
(`readxl`, `jsonlite`, `dplyr`). These are not in the renv lockfile (they run
outside renv). Install any that are missing:

```bash
Rscript --vanilla -e "
  pkgs <- c('readxl', 'jsonlite', 'dplyr')
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

## Step 3 — Find and catalogue P21 reports

There may be one file covering both SDTM and ADaM, or two separate files.
Read every report and record which domains each covers:

```bash
Rscript --vanilla - "$R_TMPDIR" <<'RSCRIPT'
library(readxl)
library(jsonlite)

tmp <- commandArgs(trailingOnly=TRUE)[1]

reports <- list.files(".", pattern="^pinnacle21-report-.*\\.xlsx$", full.names=TRUE)
reports <- reports[order(file.mtime(reports), decreasing=TRUE)]  # newest first

if (length(reports) == 0) {
  cat("NO_REPORTS\n")
  quit(status=0)
}

catalogue <- lapply(reports, function(f) {
  details <- tryCatch(read_excel(f, sheet="Details"), error=function(e) NULL)
  if (is.null(details)) return(NULL)
  domains <- unique(details$Domain)
  domains <- domains[!is.na(domains) & domains != "GLOBAL"]
  list(file=basename(f), path=f, domains=domains)
})
catalogue <- Filter(Negate(is.null), catalogue)

writeLines(toJSON(catalogue, auto_unbox=TRUE), file.path(tmp, "p21_catalogue.json"))
cat(sprintf("Catalogued %d report(s)\n", length(catalogue)))
for (r in catalogue)
  cat(sprintf("  %s -> [%s]\n", r$file, paste(r$domains, collapse=",")))
RSCRIPT
```

If the script prints `NO_REPORTS`, stop: no P21 reports found.

---

## Step 4 — Create label if missing

```bash
# gh mode
gh label create p21-commented \
  --description "Validation findings posted from P21 report" \
  --color D4C5F9 2>/dev/null || true

# curl mode equivalent
curl -s -X POST \
  -H "Authorization: token $GH_TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"p21-commented","color":"D4C5F9","description":"Validation findings posted from P21 report"}' \
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

Skip the issue if it carries any of: `p21-commented`, `wontfix`,
`duplicate`, `invalid`.

**Do NOT skip** issues labeled `claude-needs-human` — P21 validation
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

```bash
Rscript --vanilla - "$issue_num" "$R_TMPDIR" $matched_datasets <<'RSCRIPT'
library(readxl)
library(jsonlite)
library(dplyr)

args         <- commandArgs(trailingOnly=TRUE)
issue_num    <- args[1]
tmp          <- args[2]
datasets     <- args[3:length(args)]

# Load report catalogue built in Step 3
catalogue <- fromJSON(readLines(file.path(tmp, "p21_catalogue.json"), warn=FALSE))

# Helper: find the best report for a given domain
best_report <- function(domain) {
  for (r in catalogue) {
    if (domain %in% r$domains) return(r)
  }
  NULL
}

block_for_domain <- function(domain) {
  rep <- best_report(domain)
  lines <- character(0)
  if (is.null(rep)) {
    lines <- c(lines, sprintf("### %s", domain), "",
               sprintf("No P21 report found covering domain %s.", domain), "")
    return(lines)
  }

  details <- read_excel(rep$path, sheet="Details")
  rows    <- details |> filter(Domain == domain)

  lines <- c(lines, sprintf("### %s", domain), "")

  if (nrow(rows) == 0) {
    lines <- c(lines, "No validation issues found in this report.", "")
    return(lines)
  }

  lines <- c(lines,
    sprintf("Report: `%s`", rep$file),
    sprintf("- **Total issues**: %d", nrow(rows)),
    sprintf("- **Unique rules**: %d", n_distinct(rows$`Pinnacle 21 ID`)),
    "")

  rules <- rows |>
    group_by(`Pinnacle 21 ID`, Message) |>
    summarise(n=n(), .groups="drop") |>
    arrange(desc(n)) |>
    head(10)

  lines <- c(lines, "**Issues by rule:**", "")
  for (i in seq_len(nrow(rules)))
    lines <- c(lines, sprintf("- **%s** (%d): %s",
                              rules$`Pinnacle 21 ID`[i], rules$n[i], rules$Message[i]))
  lines <- c(lines, "")

  samp <- rows |> select(Record, Variables, Values, `Pinnacle 21 ID`, Message) |> head(5)
  lines <- c(lines,
    "<details><summary>Sample records</summary>", "",
    "| Record | Variables | Values | Rule | Message |",
    "|--------|-----------|--------|------|---------|")
  for (i in seq_len(nrow(samp))) {
    rec  <- ifelse(is.na(samp$Record[i]),    "-", substr(as.character(samp$Record[i]),    1,40))
    vars <- ifelse(is.na(samp$Variables[i]), "-", substr(as.character(samp$Variables[i]),1,30))
    vals <- ifelse(is.na(samp$Values[i]),    "-", substr(as.character(samp$Values[i]),    1,20))
    rule <- samp$`Pinnacle 21 ID`[i]
    msg  <- substr(samp$Message[i], 1, 70)
    lines <- c(lines, sprintf("| %s | %s | %s | %s | %s |", rec, vars, vals, rule, msg))
  }
  lines <- c(lines, "", "</details>", "")
  lines
}

# Build full comment
comment <- c("## Pinnacle21 Validation Findings", "")
for (d in datasets) comment <- c(comment, block_for_domain(d))
comment <- c(comment, "---", "", "_(posted by P21 validation report)_")

body_text  <- paste(comment, collapse="\n")
json_file  <- file.path(tmp, sprintf("p21_body_%s.json", issue_num))
writeLines(toJSON(list(body=body_text), auto_unbox=TRUE), json_file)
cat(sprintf("Generated comment for issue #%s -> %s\n", issue_num, json_file))
RSCRIPT
```

### 6e — Post comment and label

Detect success by checking for `html_url` in the API response (not `"id":`,
which has a space after the colon and is easy to mis-parse).

```bash
json_file="$R_TMPDIR/p21_body_${issue_num}.json"

if [[ ! -f "$json_file" ]]; then
  echo "Issue #$issue_num: comment generation failed, skipping"
  continue
fi

# gh mode
gh issue comment "$issue_num" --body-file <(jq -r '.body' "$json_file")
gh issue edit   "$issue_num" --add-label p21-commented

# curl mode equivalent
resp=$(curl -s -X POST \
  -H "Authorization: token $GH_TOKEN" -H "Content-Type: application/json" \
  --data-binary "@$json_file" \
  "https://api.github.com/repos/RConsortium/submissions-pilot7-synthetic-data/issues/$issue_num/comments")

if echo "$resp" | grep -q '"html_url"'; then
  curl -s -X POST \
    -H "Authorization: token $GH_TOKEN" -H "Content-Type: application/json" \
    -d '{"labels":["p21-commented"]}' \
    "https://api.github.com/repos/RConsortium/submissions-pilot7-synthetic-data/issues/$issue_num/labels" > /dev/null
  echo "Issue #$issue_num: posted and labeled"
else
  echo "Issue #$issue_num: POST failed — $(echo "$resp" | grep -o '"message":"[^"]*"' | head -1)"
fi

rm -f "$json_file"
```

---

## Hard rules

- **Never** close issues — only add comments and the `p21-commented` label.
- **Never** modify other issue metadata (assignees, milestones, projects).
- **Never** comment more than once per issue per report (Step 6c prevents this).
- **Never** post to issues with no word-boundary dataset match.
- **Never** post an empty comment — if R generation fails, skip the issue.
- Process one issue at a time. A failure on one issue must not stop the loop.
- `claude-needs-human` does **not** block P21 comments. Post and label regardless.
- If a new report appears (new filename), posting is allowed even if
  `p21-commented` is already set — the filename check in Step 6c prevents
  duplicates per report, not across all reports.

---

## End-of-run summary

After the loop, print this table to stdout:

```
Reports catalogued: pinnacle21-report-SDTM.xlsx (SDTM), pinnacle21-report-ADAM.xlsx (ADaM)

Issue  Dataset(s)       Action   Result
-----  ---------------  -------  ----------------------------------
#13    DM               Posted   5624 issues, 19 rules
#22    ADSL             Posted   2956 issues, 19 rules
#51    None             Skipped  no word-boundary dataset match
#53    ADAE             Skipped  already commented on this report
```

No other output. No file writes outside `$R_TMPDIR` and the repo tree.
