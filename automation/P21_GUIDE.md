# Using the P21 Dataset Comment Automation

## What It Does

Reads the latest Pinnacle21 validation report and automatically posts validation findings to GitHub issues that mention dataset names (like ADAE, ADQS, ADSL, etc.).

## The File

**`automation/p21_dataset_comments.md`** - Single automation prompt file (same pattern as `triage_issues.md`)

## How to Use

### Option 1: Manual Run (Test It Now)

In Claude Code, from the repo root:

```
Read automation/p21_dataset_comments.md and execute it
```

The AI agent will:
1. Bootstrap R environment
2. Find latest `pinnacle21-report-*.xlsx` in repo root
3. Scan all open GitHub issues
4. Comment on issues mentioning dataset names with validation findings
5. Label them `p21-commented`
6. Print summary table

### Option 2: Schedule It (Production)

1. From repo root in Claude Code:
   ```
   /schedule
   ```

2. Configure the routine:
   - **Name**: P21 Dataset Comments
   - **Cadence**: Daily at 10:00 AM (or after each validation run)
   - **Prompt**:
     ```
     Read automation/p21_dataset_comments.md from the repo root and execute it exactly as written. The file is the complete job — do not add steps, skip steps, or ask for clarification. Start by running Step 0 (bootstrap); if that exits non-zero, stop. Otherwise proceed through the per-issue loop. End with the stdout summary table specified at the bottom of the file.
     ```

## Prerequisites

- ✅ R installed (handled by `bootstrap_system.sh`)
- ✅ R packages (handled by `bootstrap_r.R`)
- ⚠️ **GitHub CLI (`gh`) must be authenticated**

Check GitHub CLI:
```bash
gh auth status
```

If not installed/authenticated, the automation will fail at the `gh issue list` step.

## How It Matches Issues

The automation looks for dataset names in issue titles and bodies:

| Issue Example | Matched Datasets | What Gets Posted |
|---------------|------------------|------------------|
| "Fix ADAE validation errors" | ADAE | All ADAE validation issues from report |
| "Clean up ADQS and ADSL" | ADQS, ADSL | Combined findings for both datasets |
| "Address validation issues" | None | Skipped (no dataset name) |

**Dataset names searched:** ADSL, ADAE, ADLB, ADCM, ADQS, ADMH, ADCE, ADDS, ADIE, DM, AE, LB, CM, QS, MH, CE, DS, IE, EX

## What Gets Posted

For each matched dataset, the comment includes:

```markdown
## Pinnacle21 Validation Findings

Report: `pinnacle21-report-2026-05-25.xlsx`

### Dataset: ADAE
- **Total Issues**: 182
- **Unique Rules**: 5

**Issues by Rule:**
- **AD0018** (30): Variable label mismatch between dataset and define.xml
- **AD0047** (12): Required variable missing
- **CT2002** (81): RACE value not found in 'Race' extensible codelist
...

**Sample Issues:**
| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
| ... | ... | ... | ... | ... |

---
See full details in `pinnacle21-report-2026-05-25.xlsx` (Details sheet)

_(posted by P21 validation report)_
```

## Smart Features

✅ **No duplicates**: Won't re-comment if report filename already in issue  
✅ **Multi-dataset**: Handles issues mentioning multiple datasets  
✅ **No issues = positive comment**: If dataset has 0 validation issues  
✅ **Labeled**: Adds `p21-commented` label to processed issues  
✅ **Safe**: Never closes issues, only adds comments  

## Example Workflow

1. Run Pinnacle21 validation → generates `pinnacle21-report-2026-05-25.xlsx`
2. Copy report to repo root
3. Run automation (manual or scheduled)
4. Issues mentioning "ADAE", "ADQS", etc. get comments with findings
5. Review comments and create fix PRs as needed

## State Management

Uses GitHub labels (same as `triage_issues.md`):

- `p21-commented` - Issue has P21 findings posted
- `claude-needs-human` - Skipped (needs human review)
- `wontfix`, `duplicate`, `invalid` - Skipped

## Report Tracking

Each report has a unique filename with timestamp:
- `pinnacle21-report-2026-05-25T22-14-36-221.xlsx`

The automation checks if the issue already has a comment mentioning this specific filename. This means:
- ✅ Same issue can get comments from multiple reports over time
- ✅ Each validation run posts new findings
- ✅ No duplicate comments from same report

## Troubleshooting

**"No Pinnacle21 report found"**
- Ensure report file is in repo root (not subdirectory)
- Filename must match pattern: `pinnacle21-report-*.xlsx`

**"gh: command not found"**
- GitHub CLI not installed
- Won't work without it (needs to read/comment on issues)

**No issues get commented**
- Check if issues mention dataset names (ADAE, ADQS, etc.)
- Check if already labeled `p21-commented`
- Run with `gh issue list --state open` to see open issues

## Comparison with triage_issues.md

| Feature | triage_issues.md | p21_dataset_comments.md |
|---------|------------------|-------------------------|
| Purpose | General issue triage | P21-specific validation comments |
| Input | Issue title/body | P21 Excel report |
| Action | Answer OR create PR | Post validation findings |
| Trigger | Any open issue | Issues mentioning dataset names |
| Label | `claude-triaged` | `p21-commented` |

Both work together - they don't conflict!

## Next Steps

1. **Test it**: 
   ```
   Read automation/p21_dataset_comments.md and execute it
   ```

2. **Check results**: Look for comments on issues mentioning dataset names

3. **Schedule it**: Use `/schedule` to run automatically after each validation

4. **Integrate**: Make P21 validation → automation → fix → re-validate a regular workflow
