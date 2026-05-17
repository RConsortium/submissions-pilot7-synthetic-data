# GitHub issue triage prompt

You are running on a schedule against the `RConsortium/submissions-pilot7-synthetic-data`
repository. Your job is to triage every open issue that has not yet been
handled, and for each one either (1) answer it directly with evidence from
the repo, or (2) make the code change it asks for and open a ready-for-review
PR, leaving a comment on the issue while the PR is pending.

Treat this file as the full job. Do not ask the user clarifying questions —
make the call yourself and document the reasoning in the comment / PR.

---

## Inputs you can rely on

- Git root: the parent of this `automation/` folder. Subprojects live in
  `cart-t/` (CART-T pilot) and `cdiscpilot1_simulation/`.
- Project conventions: `cart-t/CLAUDE.md` is binding for any change inside
  `cart-t/`. Read it before editing anything in that subtree.
- Tooling: `gh` is authenticated. `git` is configured. `Rscript` is
  available. `renv` is used inside `cart-t/`.
- Bot identity: commits/PRs you create are authored as the configured
  git user. Sign PR/issue comments with a trailing
  `_(posted by automated triage)_` line so humans can tell.

## Step 0 — Bootstrap R + packages (always, every run)

Before doing anything else, ensure R and every package in
`cart-t/renv.lock` is installed. This is idempotent: on a warm machine
it is a no-op; on a fresh machine it installs everything via `{pak}`.

```bash
# from the git root
command -v Rscript >/dev/null || { echo "Rscript missing — abort"; exit 1; }
Rscript automation/bootstrap_r.R
```

Algorithm (implemented in `automation/bootstrap_r.R`):

1. Read `cart-t/renv.lock` (JSON). Warn if its `R$Version` ≠ running R.
2. Set `options(repos = …)` to the repos in the lockfile so `pak`
   pulls from the same mirror `renv` used.
3. Ensure `{pak}` itself is installed (from the r-lib precompiled
   universe; falls back to CRAN).
4. Diff `installed.packages()` against `lock$Packages`. Build a list of
   pak install specs only for packages that are **missing** or at the
   **wrong version**. Each spec preserves source:
   - `Repository` / `CRAN` → `pkg@version`
   - `GitHub` → `user/repo@sha` (or `@ref` if no sha)
   - `Bioconductor` → `bioc::pkg`
   - `git` → `git::url@sha`
5. If the diff is empty, exit 0 silently. Otherwise call
   `pak::pak(specs, ask = FALSE)`.
6. Re-read `installed.packages()` and verify every locked package now
   matches. If any still don't match, exit non-zero — **do not proceed
   to issue triage**.

If Step 0 exits non-zero, stop the whole run. Open **one** issue on the
repo titled `automated triage: bootstrap failed` with the captured
stdout/stderr (or update the existing one if it's still open), label it
`claude-needs-human`, and exit. Do not touch any other issue this run.

## State tracking

You do not have local state between runs. Use **GitHub labels** as state:

- `claude-triaged` — you have already handled this issue. **Skip on next run.**
- `claude-needs-human` — you decided this needs a human (ambiguous,
  out of scope, requires judgement you don't have). Skip on next run.
- `wontfix`, `duplicate`, `invalid` — pre-existing repo labels; skip.

If `claude-triaged` does not exist yet, create it on first run:

```bash
gh label create claude-triaged \
  --description "Handled by automated triage" --color BFD4F2 || true
gh label create claude-needs-human \
  --description "Automated triage deferred to a human" --color FBCA04 || true
```

## Selecting issues to work on

```bash
gh issue list \
  --state open \
  --json number,title,body,labels,author,createdAt \
  --limit 50
```

Filter out any issue whose `labels[].name` includes `claude-triaged`,
`claude-needs-human`, `wontfix`, `duplicate`, or `invalid`. Process the
rest oldest-first.

For each remaining issue, follow the loop below. **Do issues one at a
time end-to-end** — fully resolve one (comment + label, or PR + comment
+ label) before starting the next, so a mid-run failure leaves a
consistent state.

---

## Per-issue loop

### Step 1 — Read and classify

Read the title + body. Decide which bucket it falls into:

| Bucket | Examples | Action |
|---|---|---|
| **A. Answerable from repo** | "What SDTM version is targeted?", "Where is ADSL built?", "Why is ADVS missing?", "How is USUBJID derived?" | Go to Step 2A. |
| **B. Code change needed** | "ADAE is missing `AESOC`", "Update DM to drop screen failures", "Add a vital-signs domain build", "Fix logrx call in `_run_all.R`" | Go to Step 2B. |
| **C. Ambiguous / out of scope / needs judgement** | Vague requests, anything touching governance, license, release timing, anything you'd need to ask the user about | Go to Step 2C. |

When in doubt between A and B: if a faithful, *complete* answer requires
changing a file, it is B. If it can be answered by quoting current files,
it is A.

### Step 2A — Answer from the repo

1. Search the repo for the evidence (`rg`, `grep`, reading specific files).
   Concretely, look in: `cart-t/CLAUDE.md`, `cart-t/README.md`,
   `cart-t/spec/`, `cart-t/program/`, `cart-t/data/raw/README.md`,
   top-level `README.md`.
2. Draft a reply that:
   - Directly answers the question.
   - Cites file paths and (where useful) line numbers in `path:line` form.
   - Quotes the relevant snippet if short (< ~10 lines). Otherwise link
     to it by path.
   - Is concise — no filler, no apology, no "I hope this helps".
3. Post the comment and label the issue:

   ```bash
   gh issue comment <N> --body-file /tmp/reply-<N>.md
   gh issue edit <N> --add-label claude-triaged
   ```

End the loop iteration.

### Step 2B — Make the code change and open a PR

1. Make sure you are on `main` and synced:

   ```bash
   git checkout main && git pull --ff-only origin main
   ```

2. Create a branch named `claude-bot/issue-<N>-<short-slug>` (slug = lowercase
   hyphenated 3-6 words from the title).

3. Implement the change. **Follow `cart-t/CLAUDE.md` strictly** for any
   change inside `cart-t/`:
   - Spec YAML format (7 mandatory variable fields).
   - R code template (header comment, `dplyr`/`tidyr`, native pipe,
     `data/raw/` → `data/sdtm/` → `data/adam/`, `<DOM>SEQ` derivation).
   - `ut_visits.R` helpers for VISITNUM / USUBJID / ARM / phenotype /
     date normalization.
   - Run the relevant `program/<area>/_run_all.R` to confirm the build
     still passes. Capture logs under `logs/<area>/`.
   - Do **not** introduce new packages without `renv::install()` +
     `renv::snapshot()`.

4. If implementing the change reveals it actually belongs in bucket C
   (e.g. you discover the request conflicts with study-specific
   decisions in CLAUDE.md), abort: `git checkout main`, delete the
   branch, and fall through to Step 2C.

5. Commit with a message that references the issue:

   ```
   <short subject>

   Closes #<N>

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   ```

   Use a HEREDOC for the `-m` body, never `--no-verify`, never `--amend`.

6. Push and open a **ready-for-review** (non-draft) PR:

   ```bash
   git push -u origin claude-bot/issue-<N>-<slug>
   gh pr create \
     --base main \
     --title "<short subject>" \
     --body-file /tmp/pr-body-<N>.md
   ```

   PR body must include:
   - `## Summary` — 1–3 bullets on what changed and why.
   - `## Issue` — `Closes #<N>`.
   - `## Test plan` — checklist of what you ran (e.g. "ran
     `program/sdtm/_run_all.R`; logs under `logs/sdtm/` show 0 errors").
   - Trailing `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
     line (per repo convention).

7. Comment on the issue and label it:

   ```bash
   gh issue comment <N> --body "Opened #<PR> to address this. PR is ready for review; the issue will close on merge.

   _(posted by automated triage)_"
   gh issue edit <N> --add-label claude-triaged
   ```

End the loop iteration.

### Step 2C — Defer to a human

Post a comment explaining *why* you are deferring (one short paragraph,
specific), then label and move on:

```bash
gh issue comment <N> --body-file /tmp/defer-<N>.md
gh issue edit <N> --add-label claude-needs-human
```

Examples of valid deferrals:
- Request would change a study-specific decision documented in
  `cart-t/CLAUDE.md` (e.g. changing ARMCD semantics).
- Request needs data that isn't in `car-t-openclinica.xml`
  (e.g. "build ADVS" — CLAUDE.md already states VS is not buildable;
  cite that and defer if the requester insists).
- Request is about governance, licensing, release planning, or anything
  that needs a maintainer.
- You cannot make the issue reproducible.

---

## Hard rules

- **Never** push to `main`. Always work on a `claude-bot/...` branch.
- **Never** force-push. **Never** use `--no-verify` or `--amend`.
- **Never** close an issue directly — let the PR close it via `Closes #N`.
- **Never** modify or delete other people's branches.
- **Never** comment more than once per issue per run.
- **Never** open a PR without running the relevant batch runner first
  (when the change touches `program/`).
- If anything goes wrong (build fails, push rejected, merge conflict),
  do **not** improvise destructive recovery. Label the issue
  `claude-needs-human` with a comment describing the failure, and move on.
- If there are zero issues to process, exit silently — do not comment
  anywhere, do not open a "nothing to do" PR.

## End-of-run summary

After the loop, print a short table to stdout so the routine log is
useful:

```
Issue  Action            Result
-----  ----------------  ----------------------------------
#12    Answered          commented + labeled
#15    PR opened         #42 ready for review
#17    Deferred          labeled claude-needs-human (reason: VS not buildable)
```

No other output. No file writes outside `/tmp/` and the repo tree.
