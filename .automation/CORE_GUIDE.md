# Using the CORE Dataset Comment Automation

## What It Does

Reads the latest CDISC CORE validation report and automatically posts
validation findings to GitHub issues that mention dataset names (like ADAE,
ADQS, ADSL, etc.).

## Why CORE (not Pinnacle 21)

Pinnacle 21 Community only runs on Windows/macOS and needs an interactive IQ
activation that cannot be satisfied in ephemeral CI — it fails with
`CLI.3.17` on fresh installs. **CORE** (the CDISC Open Rules Engine) is
CDISC's official open-source validator: a self-contained Linux executable
shipped with a bundled rules + controlled-terminology cache. It runs on
`ubuntu-latest` with no license, activation, or API key, which is why the
`.github/workflows/core-validate.yml` pipeline uses it.

## The File

**`.automation/core_dataset_comments.md`** — single automation prompt file
(same pattern as `triage_issues.md`).

## How to Use

### Option 1: Manual Run (Test It Now)

In Claude Code, from the repo root:

```
Read .automation/core_dataset_comments.md and execute it
```

The AI agent will:
1. Bootstrap the R environment
2. Find the latest `core-report-*.json` files in the repo root
3. Scan all open GitHub issues
4. Comment on issues mentioning dataset names with validation findings
5. Label them `core-commented`
6. Print a summary table

### Option 2: Schedule It (Production)

1. From repo root in Claude Code:
   ```
   /schedule
   ```

2. Configure the routine:
   - **Name**: CORE Dataset Comments
   - **Cadence**: Daily at 10:00 AM (or after each validation run)
   - **Prompt**:
     ```
     Read .automation/core_dataset_comments.md from the repo root and execute it exactly as written. The file is the complete job — do not add steps, skip steps, or ask for clarification. Start by running Step 0 (bootstrap); if that exits non-zero, stop. Otherwise proceed through the per-issue loop. End with the stdout summary table specified at the bottom of the file.
     ```

The `core-validate.yml` workflow already runs this prompt automatically via
`claude-code-action` after each validation on a PR, so scheduling is only
needed if you want extra out-of-band runs.

## Prerequisites

- ✅ R installed (handled by `bootstrap_system.sh`)
- ✅ R packages `jsonlite`, `dplyr` (handled by the prompt's Step 0)
- ⚠️ **GitHub CLI (`gh`) must be authenticated** (or a git credential present)

Check GitHub CLI:
```bash
gh auth status
```

## How It Matches Issues

The automation looks for dataset names in issue titles and bodies:

| Issue Example | Matched Datasets | What Gets Posted |
|---------------|------------------|------------------|
| "Fix ADAE validation errors" | ADAE | All ADAE validation issues from report |
| "Clean up ADQS and ADSL" | ADQS, ADSL | Combined findings for both datasets |
| "Address validation issues" | None | Skipped (no dataset name) |

**Dataset names searched:** ADSL, ADAE, ADLB, ADCM, ADQS, ADMH, ADCE, ADDS, ADIE, DM, AE, LB, CM, QS, MH, CE, DS, IE, EX

A domain is matched against a report's `dataset` field (upper-cased, `.xpt`
suffix removed), so `AE` matches the `ae.xpt` rows in the SDTM report.

## What Gets Posted

For each matched dataset, the comment includes:

```markdown
## CDISC CORE Validation Findings

### ADAE

Report: `core-report-ADAM.json`
- **Total issues**: 182
- **Unique rules**: 5

**Issues by rule:**
- **CORE-000123** (81): Value not found in extensible codelist
- **CORE-000047** (30): Variable label mismatch with library metadata
...

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
| ... | ... | ... | ... | ... |

</details>

---

_(posted by CDISC CORE validation report)_
```

## The CORE JSON report shape

The prompt parses the machine-readable `core-report-*.json` (the `.xlsx`
twin is only for humans). Top-level keys (spaces/hyphens → underscores):

| Key | Contents |
|---|---|
| `Conformance_Details` | Engine version, standard, version, CT package, timestamps |
| `Dataset_Details` | One row per dataset: `filename`, `label`, `length`, … |
| `Issue_Summary` | Per dataset + rule: `dataset`, `core_id`, `message`, `issues` (count) |
| `Issue_Details` | Per finding: `core_id`, `message`, `dataset`, `USUBJID`, `row`, `SEQ`, `variables[]`, `values[]` |
| `Rules_Report` | Per rule: `core_id`, `cdisc_rule_id`, `fda_rule_id`, `status` |

## Smart Features

✅ **No duplicates**: won't re-comment if the report filename is already in the issue
✅ **Multi-dataset**: handles issues mentioning multiple datasets
✅ **No issues = positive comment**: if a dataset has 0 validation issues
✅ **Labeled**: adds the `core-commented` label to processed issues
✅ **Safe**: never closes issues, only adds comments

## State Management

Uses GitHub labels (same as `triage_issues.md`):

- `core-commented` — issue has CORE findings posted
- `claude-needs-human` — does **not** block CORE comments
- `wontfix`, `duplicate`, `invalid` — skipped

## Troubleshooting

**"No CORE report found" / `NO_REPORTS`**
- Ensure the JSON report is in the repo root (not a subdirectory)
- Filename must match `core-report-*.json`
- In CI, the report is produced by the `core-validate` job and downloaded as
  the `core-validation-reports` artifact by the `post-comments` job

**"gh: command not found"**
- GitHub CLI not installed — the prompt falls back to `curl` with a git
  credential; if neither is available it stops in Step 1

**No issues get commented**
- Check that issues mention dataset names (ADAE, ADQS, etc.)
- Check whether they are already labeled `core-commented`
- Run `gh issue list --state open` to see open issues

## Comparison with triage_issues.md

| Feature | triage_issues.md | core_dataset_comments.md |
|---------|------------------|--------------------------|
| Purpose | General issue triage | CORE-specific validation comments |
| Input | Issue title/body | CORE JSON report |
| Action | Answer OR create PR | Post validation findings |
| Trigger | Any open issue | Issues mentioning dataset names |
| Label | `claude-triaged` | `core-commented` |

Both work together — they don't conflict.

## Updating the engine / standards

Everything tunable lives in the `env:` block of
`.github/workflows/core-validate.yml`:

- `CORE_VERSION` / `CORE_ASSET` — pin to a CORE GitHub release + Linux asset
- `SDTM_VERSION` / `ADAM_VERSION` — CORE uses hyphenated versions. SDTM is
  plain (`3-3`). For ADaM the standard id is `adam` and the version must carry
  the product prefix (`adamig-1-3`), since the metadata key is
  `standards/adam/adamig-1-3`.
- `CT_SDTM` / `CT_ADAM` — CT package ids that exist in CORE's bundled cache
  (e.g. `sdtmct-2024-06-28`)

To validate against newer rules or CT than the bundled cache provides, add a
`core update-cache` step (it accepts a CDISC Library `--apikey`).
