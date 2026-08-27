# CORE dataset validation comment automation

You are running on a schedule against the `RConsortium/submissions-pilot7-synthetic-data`
repository. Your job is to download the most recent CDISC CORE validation
report(s) produced by the `CORE Validate` workflow and post validation
findings as comments on open issues that mention specific dataset names
(ADAE, ADQS, ADSL, etc.).

Treat this file as the full job. Do not ask clarifying questions — make the
call yourself and document the reasoning in the comment.

---

## Inputs you can rely on

- Git root: the parent of this `.automation/` folder. Work from there.
- Tooling: `gh` is authenticated and `jq` is available. `git` is configured
  and `origin` points at the repo. **No R is needed** — do *not* run
  `bootstrap_system.sh` or `bootstrap_r.R`. This routine is pure
  `gh` + `jq` + shell.
- The `gh` token needs **`actions: read`** (to download workflow artifacts)
  in addition to issue read/write. If artifact download 403s, that scope is
  the first thing to check.
- CORE reports are **not** in the repo. They are published by
  `.github/workflows/core-validate.yml` as the `core-validation-reports`
  artifact, and Step 1 below downloads them into the git root. There may be
  more than one (a separate SDTM report and ADaM report). Detect domain
  coverage automatically — do not assume one file covers both. (The `.xlsx`
  twins are for humans; parse the `.json`.)
- Bot identity: every comment ends with a footer naming the workflow run it
  came from. That footer is also the idempotency key — see Step 5c.

---

## Step 0 — Preconditions

No bootstrap. Just confirm the two tools exist and fail loudly if not.

**Run every snippet in this file under `bash`**, not `sh` or `zsh`. They
rely on `[[ ]]`, and on word-splitting of unquoted `$matched_datasets` in
Step 5d — which zsh does not do, so under zsh the whole domain list is
treated as a single domain and every issue gets one bogus "No CORE report
found covering domain ADSL DM QS" block.

```bash
set -uo pipefail
command -v gh >/dev/null || { echo "ERROR: gh not found"; exit 1; }
command -v jq >/dev/null || { echo "ERROR: jq not found"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "ERROR: gh not authenticated"; exit 1; }

WORK=$(mktemp -d)
REPO="RConsortium/submissions-pilot7-synthetic-data"
echo "Work dir: $WORK"
```

Use `$WORK` for every temp file in this run.

---

## Step 1 — Fetch the newest CORE reports

The routine starts from a clean clone, so it must go and get its own inputs.
Take the most recent **successful** run of the validation workflow and pull
its artifact into the git root:

```bash
run_json=$(gh run list --repo "$REPO" --workflow=core-validate.yml \
  --status=success --limit 1 \
  --json databaseId,headSha,number,createdAt)

CORE_RUN_ID=$(echo "$run_json" | jq -r '.[0].databaseId // empty')
CORE_RUN_NO=$(echo "$run_json" | jq -r '.[0].number // empty')
CORE_RUN_SHA=$(echo "$run_json" | jq -r '.[0].headSha // empty')

if [[ -z "$CORE_RUN_ID" ]]; then
  echo "SKIP: no successful CORE Validate run found"
  exit 0
fi

# Never reuse stale files from a previous run of this routine.
rm -f core-report-*.json core-report-*.xlsx

if ! gh run download "$CORE_RUN_ID" --repo "$REPO" \
      --name core-validation-reports --dir . 2>"$WORK/dl.err"; then
  echo "SKIP: run #$CORE_RUN_ID has no core-validation-reports artifact"
  echo "      (artifacts expire after 90 days; or the token lacks actions:read)"
  cat "$WORK/dl.err"
  exit 0
fi

CORE_SHA7="${CORE_RUN_SHA:0:7}"
echo "Using CORE run #$CORE_RUN_NO (id $CORE_RUN_ID, commit $CORE_SHA7)"
ls -la core-report-*.json 2>/dev/null || { echo "SKIP: artifact had no JSON reports"; exit 0; }
```

`$CORE_RUN_ID`, `$CORE_RUN_NO` and `$CORE_SHA7` are used in Steps 5c and 5d.
Carry them through the whole run.

---

## Step 2 — Catalogue the reports

Read every JSON report and record which domains each one covers. Coverage
comes from `Dataset_Details[].filename` and `Issue_Summary[].dataset`,
upper-cased with any `.xpt` suffix stripped.

```bash
: > "$WORK/catalogue.tsv"
for f in core-report-*.json; do
  [[ -e "$f" ]] || continue
  domains=$(jq -r '
    [ (.Dataset_Details[]?.filename // empty),
      (.Issue_Summary[]?.dataset   // empty) ]
    | map(ascii_upcase | sub("\\.XPT$"; ""))
    | map(select(length > 0)) | unique | join(",")
  ' "$f" 2>/dev/null)
  [[ -z "$domains" ]] && continue
  printf '%s\t%s\n' "$f" "$domains" >> "$WORK/catalogue.tsv"
  echo "  $f -> [$domains]"
done

if [[ ! -s "$WORK/catalogue.tsv" ]]; then
  echo "SKIP: no parseable CORE reports"
  exit 0
fi
```

Helper used later — first report covering a given domain:

```bash
report_for_domain() {  # $1 = domain
  awk -F'\t' -v d="$1" '{ n=split($2,a,","); for(i=1;i<=n;i++) if(a[i]==d){print $1; exit} }' \
    "$WORK/catalogue.tsv"
}
```

---

## Step 3 — Create label if missing

```bash
gh label create core-commented --repo "$REPO" \
  --description "Validation findings posted from CORE report" \
  --color D4C5F9 2>/dev/null || true
```

---

## Step 4 — Fetch all open issues

```bash
gh issue list --repo "$REPO" --state open \
  --json number,title,body,labels --limit 100 > "$WORK/open_issues.json"
```

---

## Step 5 — Per-issue loop

Process issues **oldest-first** (lowest number first). Resolve one issue
completely (match → generate → post → label) before moving to the next.

Write the block-rendering jq program once, up front:

```bash
cat > "$WORK/block.jq" <<'JQ'
def norm: ascii_upcase | sub("\\.XPT$"; "");
def trunc($n): if (length > $n) then .[0:$n] else . end;
def cell: gsub("\\|"; "\\|") | gsub("\n"; " ");
def joinvec: if (. == null or (length == 0)) then "-"
             else map(if . == null then "null" else tostring end) | join(";") end;

[ .Issue_Summary[]? | select(((.dataset // "") | norm) == $domain) ] as $srows |
[ .Issue_Details[]? | select(((.dataset // "") | norm) == $domain) ] as $drows |
([ $srows[] | (.issues // 0) ] | add // 0)          as $total |
([ $srows[] | (.core_id // "") ] | unique | length)  as $nrules |

(
  ["### \($domain)", "", "Report: `\($file)`", ""]
  + (
    if (($srows | length) == 0 and ($drows | length) == 0) then
      ["No validation issues found for this domain. ✅", ""]
    else
      ["- **Total issues**: \($total)", "- **Unique rules**: \($nrules)", ""]
      + (if ($srows | length) > 0 then
           ["**Issues by rule:**", ""]
           + ($srows | sort_by(-(.issues // 0)) | .[0:10]
              | map("- **\(.core_id // "?")** (\(.issues // 0)): \((.message // "") | cell)"))
           + [""]
         else [] end)
      + (if ($drows | length) > 0 then
           ["<details><summary>Sample records</summary>", "",
            "| Record | Variables | Values | Rule | Message |",
            "|--------|-----------|--------|------|---------|"]
           + ($drows | .[0:5] | map(
               "| \(.row // "-") "
               + "| \((.variables | joinvec) | trunc(30) | cell) "
               + "| \((.values    | joinvec) | trunc(20) | cell) "
               + "| \(.core_id // "-") "
               + "| \((.message // "") | trunc(70) | cell) |"))
           + ["", "</details>", ""]
         else [] end)
    end
  )
) | join("\n")
JQ
```

Then loop. Two things matter here:

- Base64-encode each issue so titles and bodies containing quotes,
  backticks, or `$(...)` cannot break the shell or be evaluated.
- Drive the loop from a **file**, not a pipe. `... | while read` runs the
  body in a subshell, so counters and the summary table would be lost at
  the end. Sorting happens in jq, so the loop is already oldest-first.

```bash
jq -r 'sort_by(.number) | .[] | @base64' "$WORK/open_issues.json" > "$WORK/issues.b64"

while read -r row; do
  issue=$(echo "$row" | base64 --decode)
  issue_num=$(echo "$issue"    | jq -r '.number')
  issue_title=$(echo "$issue"  | jq -r '.title // ""')
  issue_body=$(echo "$issue"   | jq -r '.body  // ""')
  issue_labels=$(echo "$issue" | jq -r '[.labels[].name] | join(",")')
  ...
done < "$WORK/issues.b64"
```

Give every `gh` call inside the loop `</dev/null`. Otherwise a `gh`
subcommand that reads standard input will swallow the rest of
`issues.b64` and the loop will silently process only the first issue.

### 5a — Check skip labels

Skip the issue if it carries any of: `wontfix`, `duplicate`, `invalid`.

**Do NOT skip** on `core-commented` — that label only records that *some*
report was posted once; whether *this* run has already been posted is
decided in Step 5c by run id. **Do NOT skip** `claude-needs-human` either —
CORE findings should be posted regardless of triage state.

### 5b — Match datasets using word-boundary search

Use whole-word matching to avoid false positives from short domain names
appearing inside common words (e.g. "CE" in "process", "DM" in "odm").

```bash
matched_datasets=""
for dataset in ADSL ADAE ADLB ADCM ADQS ADMH ADCE ADDS ADIE DM AE LB CM QS MH CE DS IE EX; do
  if printf '%s %s' "$issue_title" "$issue_body" | grep -iqw "$dataset"; then
    matched_datasets="$matched_datasets $dataset"
  fi
done
matched_datasets=$(echo $matched_datasets)  # trim whitespace

if [[ -z "$matched_datasets" ]]; then
  echo "Issue #$issue_num: no dataset names found, skipping"
  continue
fi
```

### 5c — Idempotency: has this run already been posted here?

Keyed on the **workflow run id**, not the report filename. Report filenames
are constant (`core-report-SDTM.json` every time), so a filename check would
block every post after the first; the run id changes with each validation,
so re-firing the routine is a no-op while genuinely new results still post.

```bash
if gh issue view "$issue_num" --repo "$REPO" --json comments \
     --jq '.comments[].body' </dev/null 2>/dev/null \
   | grep -qF "run #${CORE_RUN_NO} (${CORE_RUN_ID})"; then
  echo "Issue #$issue_num: already commented for run #$CORE_RUN_NO, skipping"
  continue
fi
```

Use `grep -qF` — a fixed-string, quiet match. (Do not use `grep -l` here: it
prints `(standard input)` rather than matching, so it reports a hit every
time and silently suppresses all posting.)

### 5d — Generate the comment

```bash
body="$WORK/core_body_${issue_num}.md"
{
  echo "## CDISC CORE Validation Findings"
  echo ""
  for domain in $matched_datasets; do
    rep=$(report_for_domain "$domain")
    if [[ -z "$rep" ]]; then
      printf '### %s\n\nNo CORE report found covering domain %s.\n\n' "$domain" "$domain"
    else
      jq -r --arg domain "$domain" --arg file "$(basename "$rep")" \
        -f "$WORK/block.jq" "$rep"
      echo ""
    fi
  done
  echo "---"
  echo ""
  echo "_(posted by CDISC CORE validation report — run #${CORE_RUN_NO} (${CORE_RUN_ID}), commit ${CORE_SHA7})_"
} > "$body"
```

If `$body` is missing, empty, or contains only the header and footer with no
domain blocks, skip the issue rather than posting a hollow comment.

### 5e — Post and label

```bash
if [[ ! -s "$body" ]]; then
  echo "Issue #$issue_num: comment generation failed, skipping"
  continue
fi

if gh issue comment "$issue_num" --repo "$REPO" --body-file "$body" </dev/null; then
  gh issue edit "$issue_num" --repo "$REPO" --add-label core-commented </dev/null
  echo "Issue #$issue_num: posted and labeled"
else
  echo "Issue #$issue_num: comment POST failed"
fi
rm -f "$body"
```

---

## Step 6 — Clean up

The downloaded reports are build outputs, not source. Remove them so they
can never be committed by a later routine sharing the workspace:

```bash
rm -f core-report-*.json core-report-*.xlsx
rm -rf "$WORK"
```

---

## Hard rules

- **Never** commit, branch, push, or open a PR. This routine's only writes
  are issue comments and the `core-commented` label.
- **Never** close issues, or modify assignees, milestones, or projects.
- **Never** comment more than once per issue per workflow run (Step 5c).
- **Never** post to issues with no word-boundary dataset match.
- **Never** post an empty comment — if generation fails, skip the issue.
- Process one issue at a time. A failure on one issue must not stop the loop.
- `claude-needs-human` does **not** block CORE comments.
- If Step 1 finds no run, no artifact, or no parseable report, exit **0**
  with the `SKIP:` line. That is a normal outcome, not a failure.
- No file writes outside `$WORK` and the `core-report-*` files in git root,
  both of which Step 6 deletes.

---

## End-of-run summary

After the loop, print this table to stdout:

```
CORE run: #182 (id 18234567), commit a1b2c3d
Reports:  core-report-SDTM.json (SDTM), core-report-ADAM.json (ADaM)

Issue  Dataset(s)       Action   Result
-----  ---------------  -------  ----------------------------------
#13    DM               Posted   5624 issues, 19 rules
#22    ADSL             Posted   2956 issues, 19 rules
#51    None             Skipped  no word-boundary dataset match
#53    ADAE             Skipped  already commented on run #182
```

Or, when Step 1 bails: the single `SKIP: ...` line and nothing else.
No other output.
