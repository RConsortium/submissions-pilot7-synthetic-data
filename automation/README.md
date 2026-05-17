# automation/

Recurring tasks that run against this repo. Each task is a self-contained
prompt file in this folder; the *runner* (a Claude Code routine) is
configured separately.

## Files

| File | Purpose |
|---|---|
| `triage_issues.md` | Triage every open GitHub issue: answer from the repo, or open a ready-for-review PR + comment. Full rules, hard limits, and end-of-run output spec are inside the file. |
| `bootstrap_r.R`    | Pre-flight installer. Reads `cart-t/renv.lock`, diffs against `installed.packages()`, and uses `{pak}` to install whatever is missing or version-mismatched. Idempotent — no-op on a warm machine. Triage runs invoke this first. |

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

To run a prompt manually right now without scheduling, paste the
contents of the prompt file into a Claude Code session at the repo root.

## State

State is kept in **GitHub labels**, not on disk, so the routine is
idempotent across runs and across machines:

- `claude-triaged` — issue has been handled (skip next run).
- `claude-needs-human` — automation deferred; needs a human.

Both labels are auto-created on first run.

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

- **R is installed** and `Rscript` is on `PATH`. The version should be
  close to `cart-t/renv.lock`'s `R$Version` (currently `4.6.0`). Minor
  drift is fine; major drift will be flagged by `bootstrap_r.R`.
- **System libraries** that `{pak}` cannot install for you (compilers,
  `libxml2-dev`, `libcurl4-openssl-dev`, `libssl-dev`, `libgit2-dev`).
  On Ubuntu/WSL the rstudio image already has these; on a fresh runner,
  install them once.
- **`gh` CLI authenticated** as the bot identity with `repo` scope on
  `RConsortium/submissions-pilot7-synthetic-data`. Verify with
  `gh auth status`. The token needs: read issues, write issues
  (comment + label), read/write PRs, push branches.
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
  will `pak::pak()` the delta automatically.
- **Branch protection on `main`** that requires PR review. The routine
  opens PRs ready-for-review but never merges; a human always merges.

### What to watch / how to kill it

- Every run prints an end-of-run table to the routine log
  (Issue / Action / Result). Scan it after each fire.
- To pause the routine: disable the schedule in Claude Code, or
  pre-label every open issue with `claude-needs-human`.
- To retire it: delete the routine and remove this folder. No
  on-repo state needs cleanup beyond the two labels.
