# P21 dataset validation comment automation

You are running on a schedule against the `RConsortium/submissions-pilot7-synthetic-data`
repository. Your job is to read the latest Pinnacle21 validation report and
post validation findings as comments on open issues that mention specific
dataset names (ADAE, ADQS, ADSL, etc.).

Treat this file as the full job. Do not ask clarifying questions — make the
call yourself and document the reasoning in the comment.

---

## Inputs you can rely on

- Git root: the parent of this `automation/` folder
- P21 reports: Excel files matching `pinnacle21-report-*.xlsx` in git root
- Tooling: `gh` is authenticated, `git` is configured, `Rscript` is available
- Bot identity: sign comments with `_(posted by P21 validation report)_`

## Step 0 — Bootstrap R + packages (always, every run)

Before doing anything else, ensure R and packages are available:

```bash
bash automation/bootstrap_system.sh
Rscript automation/bootstrap_r.R
```

If either exits non-zero, stop the whole run. Print the captured stdout/stderr
to the routine log and exit non-zero. Do not proceed to issue processing.

## Step 1 — Find latest P21 report

Find the most recent Pinnacle21 report:

```bash
latest_report=$(ls -t pinnacle21-report-*.xlsx 2>/dev/null | head -1)
if [[ -z "$latest_report" ]]; then
  echo "No Pinnacle21 report found, exiting"
  exit 0
fi
report_filename=$(basename "$latest_report")
echo "Processing report: $report_filename"
```

## State tracking

Use **GitHub labels** as state:

- `p21-commented` — you have already posted findings from the current report.
  **Skip on next run.**
- `claude-needs-human` — deferred (don't comment on these)
- `wontfix`, `duplicate`, `invalid` — skip

If `p21-commented` does not exist yet, create it:

```bash
gh label create p21-commented \
  --description "Validation findings posted from P21 report" \
  --color D4C5F9 || true
```

## Selecting issues to work on

Get all open issues:

```bash
gh issue list \
  --state open \
  --json number,title,body,labels \
  --limit 100 > /tmp/open_issues.json
```

Process each issue that:
1. Is NOT labeled `p21-commented`, `claude-needs-human`, `wontfix`, `duplicate`, or `invalid`
2. Mentions dataset names in title or body

Dataset names to look for (case-insensitive):
- ADAM: ADSL, ADAE, ADLB, ADCM, ADQS, ADMH, ADCE, ADDS, ADIE
- SDTM: DM, AE, LB, CM, QS, MH, CE, DS, IE, EX

Process oldest-first. **Do issues one at a time end-to-end** — fully resolve
one (comment + label) before starting the next.

---

## Per-issue loop

### Step 1 — Read issue and find dataset mentions

For each open issue, extract title and body, then search for dataset names:

```bash
issue_json=$(gh issue view "$issue_num" --json title,body,labels)
issue_title=$(echo "$issue_json" | jq -r '.title')
issue_body=$(echo "$issue_json" | jq -r '.body // empty')
issue_labels=$(echo "$issue_json" | jq -r '.labels[].name')

# Check labels - skip if already handled
if echo "$issue_labels" | grep -qE "p21-commented|claude-needs-human|wontfix|duplicate|invalid"; then
  echo "Issue #$issue_num: skipped (labeled)"
  continue
fi

# Find dataset mentions
matched_datasets=""
for dataset in ADSL ADAE ADLB ADCM ADQS ADMH ADCE ADDS ADIE DM AE LB CM QS MH CE DS IE EX; do
  if echo "$issue_title $issue_body" | grep -iq "$dataset"; then
    matched_datasets="$matched_datasets $dataset"
  fi
done

if [[ -z "$matched_datasets" ]]; then
  echo "Issue #$issue_num: no dataset names mentioned, skipping"
  continue
fi

echo "Issue #$issue_num: matched datasets:$matched_datasets"
```

### Step 2 — Check if already commented on this report

Verify the issue doesn't already have a comment mentioning this specific report:

```bash
existing_comment=$(gh issue view "$issue_num" --json comments \
  --jq ".comments[] | select(.body | contains(\"$report_filename\")) | .id" | head -1)

if [[ -n "$existing_comment" ]]; then
  echo "Issue #$issue_num: already has comment for report $report_filename"
  gh issue edit "$issue_num" --add-label p21-commented || true
  continue
fi
```

### Step 3 — Generate comment with validation findings

For each matched dataset, read the P21 report and extract findings.

Use R to generate the comment:

```bash
Rscript - "$issue_num" "$latest_report" "$report_filename" $matched_datasets <<'RSCRIPT'
library(readxl)
library(dplyr)

args <- commandArgs(trailingOnly = TRUE)
issue_num <- args[1]
report_file <- args[2]
report_filename <- args[3]
datasets <- args[4:length(args)]

# Read validation details
details <- read_excel(report_file, sheet = "Details")

# Build comment
comment <- c(
  "## Pinnacle21 Validation Findings",
  "",
  sprintf("Report: `%s`", report_filename),
  ""
)

# Process each dataset
for (dataset in datasets) {
  dataset_issues <- details |> filter(Domain == dataset)
  
  if (nrow(dataset_issues) == 0) {
    comment <- c(comment,
      sprintf("### Dataset: %s", dataset),
      "",
      sprintf("✅ **No validation issues found** for %s in this report.", dataset),
      ""
    )
    next
  }
  
  comment <- c(comment,
    sprintf("### Dataset: %s", dataset),
    "",
    sprintf("- **Total Issues**: %d", nrow(dataset_issues)),
    sprintf("- **Unique Rules**: %d", n_distinct(dataset_issues$`Pinnacle 21 ID`)),
    ""
  )
  
  # Group by rule
  rule_summary <- dataset_issues |>
    group_by(`Pinnacle 21 ID`, Message) |>
    summarise(count = n(), .groups = "drop") |>
    arrange(desc(count)) |>
    head(10)
  
  comment <- c(comment, "**Issues by Rule:**", "")
  
  for (i in seq_len(nrow(rule_summary))) {
    comment <- c(comment,
      sprintf("- **%s** (%d): %s",
              rule_summary$`Pinnacle 21 ID`[i],
              rule_summary$count[i],
              rule_summary$Message[i])
    )
  }
  
  comment <- c(comment, "")
  
  # Sample records
  samples <- dataset_issues |>
    select(Record, Variables, Values, `Pinnacle 21 ID`, Message) |>
    head(5)
  
  if (nrow(samples) > 0) {
    comment <- c(comment,
      "**Sample Issues:**",
      "",
      "| Record | Variables | Values | Rule | Message |",
      "|--------|-----------|--------|------|---------|"
    )
    
    for (i in seq_len(nrow(samples))) {
      record <- ifelse(is.na(samples$Record[i]), "-", as.character(samples$Record[i]))
      variables <- ifelse(is.na(samples$Variables[i]), "-",
                         substring(as.character(samples$Variables[i]), 1, 30))
      values <- ifelse(is.na(samples$Values[i]), "-",
                      substring(as.character(samples$Values[i]), 1, 20))
      rule <- samples$`Pinnacle 21 ID`[i]
      msg <- substring(samples$Message[i], 1, 50)
      
      comment <- c(comment,
        sprintf("| %s | %s | %s | %s | %s... |", record, variables, values, rule, msg)
      )
    }
    
    comment <- c(comment, "")
  }
}

# Footer
comment <- c(comment,
  "---",
  "",
  sprintf("See full details in `%s` (Details sheet)", report_filename),
  "",
  "_(posted by P21 validation report)_"
)

# Write to file
output_file <- sprintf("/tmp/comment-%s.md", issue_num)
writeLines(comment, output_file)
cat("Generated comment for issue", issue_num, "\n")
RSCRIPT
```

### Step 4 — Post comment and label

```bash
comment_file="/tmp/comment-${issue_num}.md"

if [[ ! -f "$comment_file" ]]; then
  echo "Issue #$issue_num: comment generation failed, skipping"
  continue
fi

# Post comment
gh issue comment "$issue_num" --body-file "$comment_file"

# Add label
gh issue edit "$issue_num" --add-label p21-commented

echo "Issue #$issue_num: posted P21 findings"
rm "$comment_file"
```

End the loop iteration.

---

## Hard rules

- **Never** close issues — only add comments and the `p21-commented` label
- **Never** modify other issue metadata (assignees, milestones, projects)
- **Never** comment more than once per issue per report (check filename in existing comments)
- **Never** post comments to issues that don't mention dataset names
- **Never** post empty comments — if comment generation fails, skip
- Process issues one at a time. If posting fails, log it and continue to next issue.
- If the report changes (new validation run), new comments are allowed even if
  `p21-commented` is set (report filename check prevents duplicates)

## End-of-run summary

After processing all issues, print a summary table to stdout:

```
Report: pinnacle21-report-2026-05-25T22-14-36-221.xlsx

Issue  Dataset(s)      Action            Result
-----  --------------  ----------------  ----------------------------------
#42    ADAE            Posted            182 issues, 5 rules
#45    ADQS            Posted            1205 issues, 8 rules
#48    ADSL, ADAE      Posted            combined findings
#51    None            Skipped           no datasets mentioned
#53    ADAE            Skipped           already commented on this report
```

No other output. No file writes outside `/tmp/` and the repo tree.
