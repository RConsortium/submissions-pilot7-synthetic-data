# automation/

Recurring tasks that run against this repo. Each task is a self-contained
prompt file in this folder; the *runner* (a Claude Code routine) is
configured separately.

## Files

| File | Purpose |
|---|---|
| `triage_issues.md`    | Triage every open GitHub issue: answer from the repo, or open a ready-for-review PR + comment. Full rules, hard limits, and end-of-run output spec are inside the file. |
| `weekly_update.md`    | Post a weekly activity digest (commits, merged PRs, issue activity, needs-attention list) as one Slack message to `#pilot7-sdtm-adam-tlf-bench` (`C0B44HS7CNA`). Read-only on GitHub; state lives in the channel history; no R bootstrap needed. |
| `core_dataset_comments.md` | Download the newest `core-validation-reports` artifact from the `CORE Validate` workflow and post CDISC CORE findings as comments on open issues that name a dataset. Pure `gh` + `jq`; **no R bootstrap needed**. Idempotent per workflow run — see below. |
| `bootstrap_system.sh` | Pre-pre-flight installer. `apt-get`s `r-base` + `r-base-dev` + the system libraries `{renv}` compiles packages against, but only if `Rscript` is missing from `PATH`. Idempotent. Runs first in Step 0 of `triage_issues.md`. |
| `bootstrap_r.R`       | Pre-flight installer. Reads `cart-t/renv.lock`, diffs against `installed.packages()`, and uses `{renv}` to install whatever is missing or version-mismatched. Idempotent — no-op on a warm machine. Runs after `bootstrap_system.sh` in Step 0. |

## How it runs

These prompts are designed to be invoked by a **Claude Code routine**
(scheduled remote agent). To wire one up, from this repo:

```
/schedule
```

…then point it at the prompt you want to run and the cadence you want
(e.g. hourly, every 6 hours, daily at 09:00). The routine starts in the
repo root with `gh` and `git` already authenticated to
`RConsortium/submissions-pilot7-synthetic-data`.

### The exact prompt to paste into the routine

Keep the routine config short — point it at the prompt file in this
folder rather than inlining instructions. That way edits to
`triage_issues.md` take effect on the next run, are reviewed in git,
and don't drift from a copy hidden in routine settings.

Copy the text inside the code block below verbatim into the routine's
prompt field (the fence itself is just for copy-paste; don't include it):

```
Read automation/triage_issues.md from the repo root and execute it exactly as written. The file is the complete job — do not add steps, skip steps, or ask for clarification. Start by running Step 0 (Rscript automation/bootstrap_r.R); if that exits non-zero, follow the failure path in the prompt and stop. Otherwise proceed through the per-issue loop. End with the stdout summary table specified at the bottom of the file.
```

For the **weekly update** routine, register a *separate* routine (don't
multiplex), schedule it weekly — Fridays 07:00 PST works well, just
before the 8–9 AM PST standup — attach the **Slack connector** (it posts
to `C0B44HS7CNA`), and paste:

```
Read automation/weekly_update.md from the repo root and execute it exactly as written. The file is the complete job — do not add steps, skip steps, or ask for clarification. Skip the R bootstrap entirely; this routine only needs gh, git, and the Slack tools. Respect the idempotency guard in Step 1, send at most one Slack message to the channel named in the file, and end with the stdout summary lines specified at the bottom of the file.
```

For the **CORE dataset comments** routine, register another separate
routine and schedule it **hourly** (`0 * * * *`) — one hour is the
minimum interval a routine allows, and the run exits in seconds when
there is nothing new. Paste:

```
Read automation/core_dataset_comments.md from the repo root and execute it exactly as written. The file is the complete job — do not add steps, skip steps, or ask for clarification. Skip the R bootstrap entirely; this routine only needs gh and jq. Start at Step 0, and if Step 1 finds no successful run, no artifact, or no parseable report, print the SKIP line and exit 0 — that is a normal outcome, not a failure. End with the stdout summary table specified at the bottom of the file.
```

To run a prompt manually right now without scheduling, paste the
contents of the prompt file into a Claude Code session at the repo root.

## Why the LLM step is a routine and not a CI job

`.github/workflows/core-validate.yml` used to have a second job that ran
`claude-code-action` against `core_dataset_comments.md`, gated on an
`ANTHROPIC_API_KEY` repo secret. That job is gone.

Validation and commenting are now split at the artifact boundary:

- The **workflow** runs on `pull_request` when XPT files change, runs
  CORE, and uploads `core-validation-reports`. It needs **no secrets**.
- The **routine** runs on a schedule, downloads that artifact from the
  newest successful run, and posts the comments. Its Anthropic
  credential is the Claude account the routine is registered under —
  held by Anthropic, never stored in this repo, this org, or a runner.

The tradeoff is latency: comments appear on the routine's next tick
rather than the instant CI finishes. For issue comments read by humans,
that is not a meaningful difference, and it is the only arrangement with
no Anthropic credential anywhere in GitHub.

**If you ever delete the routine, also delete the now-unused
`ANTHROPIC_API_KEY` secret** if one is still set on the repo or org —
nothing reads it any more.

## State

State is kept in **GitHub labels**, not on disk, so the routine is
idempotent across runs and across machines:

- `claude-triaged` — issue has been handled (skip next run).
- `claude-needs-human` — automation deferred; needs a human.
- `core-commented` — CORE findings have been posted at least once.

All three labels are auto-created on first run.

`core-commented` is a marker, **not** the skip condition. The CORE
routine decides whether to post by searching an issue's comments for the
workflow run id in the footer (`run #<number> (<id>)`), so a new
validation run posts fresh findings to an already-labelled issue while a
re-fire of the same run is a no-op. Keying on the report *filename* would
not work — filenames are constant (`core-report-SDTM.json` every run), so
the first comment would block all later ones forever.

The weekly update routine keeps no GitHub state at all: its reporting
window and idempotency guard come from the most recent digest message it
finds in the Slack channel itself.

## Hard limits (apply to every prompt in this folder)

- Never push to `main`. Branches are `claude-bot/<topic>`.
- Never force-push, `--no-verify`, or `--amend`.
- Never close issues directly — let PRs close via `Closes #N`.
- One comment per issue per run, max.
- If anything is destructive or ambiguous, defer to a human with a
  `claude-needs-human` label and a one-paragraph explanation.

If you add a new prompt, follow the same shape: inputs at the top,
selection rules, per-item loop, hard rules, end-of-run summary.

---

## What a human must leave in place for the routine

The Claude Code routine is **stateless across runs** and only sees what
you configure once. If any of the following drifts, the routine will
either fail loudly (good) or silently stop working (bad). Audit this
list whenever you rotate credentials or change CI.

### One-time, on the machine/runner the routine uses

- **R is installed** and `Rscript` is on `PATH`. Required by
  `triage_issues.md` only — the weekly update and CORE dataset comment
  routines do not use R and must not run the bootstrap scripts. The version should be
  close to `cart-t/renv.lock`'s `R$Version` (currently `4.6.0`). Minor
  drift is fine; major drift will be flagged by `bootstrap_r.R`. On a
  fresh Debian/Ubuntu container, `bootstrap_system.sh` will install R
  via `apt-get` at the start of every run — but only if the runner is
  root (or has `sudo`). For non-root runners, bake R into the
  container image (e.g. `rocker/r-ver:4.6.0`).
- **System libraries** that `{renv}` cannot install for you (compilers,
  `libxml2-dev`, `libcurl4-openssl-dev`, `libssl-dev`, `libgit2-dev`,
  `libuv1-dev`). On Ubuntu/WSL the rstudio image already has these;
  on a fresh runner, `bootstrap_system.sh` apt-installs them
  alongside `r-base`.
- **`gh` CLI authenticated** as the bot identity with `repo` scope on
  `RConsortium/submissions-pilot7-synthetic-data`. Verify with
  `gh auth status`. The token needs: read issues, write issues
  (comment + label), read/write PRs, push branches. Issue *creation*
  is not required — bootstrap failures surface in the routine log
  only, not as an auto-filed issue. The **weekly update** routine only
  needs *read* access on GitHub; its single write action is a Slack
  message. The **CORE dataset comments** routine additionally needs
  **`actions: read`** — it calls `gh run list` and `gh run download`
  to pull the validation artifact. A 403 on artifact download almost
  always means this scope is missing.
- **`jq`** on `PATH` for the CORE dataset comments routine. It is
  present on the standard runner images; the prompt fails loudly in
  Step 0 if it is not.
- **`git` user.name and user.email** set to the bot identity so commits
  and PR authorship are recognisable. Do **not** use a real person's
  identity — humans should be able to tell at a glance.
- **Push access to `claude-bot/*` branches** on the repo. Branch
  protection on `main` should *not* allow the bot to push there
  directly (the prompt forbids it; protection is the belt to the
  prompt's suspenders).

### In the Claude Code routine config itself

- **Schedule** — cadence you want triage to run at (e.g. hourly, every
  6h, daily 09:00). Set via `/schedule` from this repo.
- **Working directory** — the git root
  (`submissions-pilot7-synthetic-data/`), not `cart-t/`.
- **Prompt** — point at `automation/triage_issues.md`. When you add new
  prompts in this folder, register each as its own routine; don't try
  to multiplex.
- **Tool allowlist** — at minimum: `Bash` (for `gh`, `git`, `Rscript`),
  `Read`, `Write`, `Edit`. Do **not** allowlist destructive global
  tools. The prompt enforces no `--no-verify` / no `--amend` / no
  force-push, but tool-level limits are a backstop.
- **Slack connector** (weekly update routine only) — attached to the
  routine, signed into the `rconsortium` workspace, with read + post
  access to `#pilot7-sdtm-adam-tlf-bench` (`C0B44HS7CNA`). The triage
  routine does not need it.
- **Network access** — must be able to reach `api.github.com`, the
  CRAN/p3m mirror in `renv.lock`, and (if any GitHub-sourced packages
  exist in `renv.lock`) `github.com`.

### On the repo

- **Labels** `claude-triaged` and `claude-needs-human` exist. The
  prompt creates them on first run, but don't delete them — that is
  what makes the routine idempotent.
- **`cart-t/CLAUDE.md`** is the source of truth for any change inside
  `cart-t/`. Keep it accurate; the routine reads it before editing.
- **`cart-t/renv.lock`** is the source of truth for the R environment.
  When you bump packages, commit the new lockfile; the next routine run
  will `renv::install()` the delta automatically.
- **Branch protection on `main`** that requires PR review. The routine
  opens PRs ready-for-review but never merges; a human always merges.
