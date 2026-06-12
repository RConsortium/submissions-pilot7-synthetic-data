# Weekly repo update prompt

You are running on a schedule against the `RConsortium/submissions-pilot7-synthetic-data`
repository. Your job is to post **one Slack message** summarising the past
week's activity in the repo — commits, merged PRs, issue activity, and
anything that needs a human's attention — to the team channel, so everyone
has a ready-made digest before the Friday standup.

- **Workspace:** `rconsortium.slack.com`
- **Channel:** `#pilot7-sdtm-adam-tlf-bench`, channel ID `C0B44HS7CNA`
  (https://rconsortium.slack.com/archives/C0B44HS7CNA)

Treat this file as the full job. Do not ask the user clarifying questions —
make the call yourself and note any judgement calls in the digest itself.

This routine is **read-only on GitHub** (only `gh`/`git` reads) and its one
write action anywhere is sending a single Slack message to the channel
above. No commits, no branches, no PRs, no issues, no comments, no labels.

---

## Inputs you can rely on

- Git root: the parent of this `automation/` folder.
- Tooling: `gh` is authenticated; read-only access is enough. `git` is
  configured and `origin` points at the repo.
- The **Slack connector** is attached to the routine, with read + post
  access to channel `C0B44HS7CNA`. If Slack tools are missing or the
  channel is unreachable, print the error to stdout and exit non-zero —
  do **not** fall back to posting a GitHub issue or any other channel.
- No R needed. Do **not** run `bootstrap_system.sh` or `bootstrap_r.R`.

## Step 1 — Determine the reporting window and check idempotency

State lives in the channel itself. Read recent channel history (Slack
`read channel`, ~50 messages) and find the most recent digest — a message
whose first line starts with:

```
:test_tube: *submissions-pilot7-synthetic-data — week of
```

- `WINDOW_START` = the end date in that digest's header (`week of
  <start> → <end>`). If no digest is found in the last 50 messages,
  use 7 days ago (UTC).
- `WINDOW_END` = today (UTC).
- **Idempotency guard:** if the most recent digest was posted less than
  3 days ago, exit silently — the routine double-fired or someone posted
  manually. Print `SKIP: last digest posted <date>` to stdout and do
  nothing else.

Make sure local refs are current before counting commits:

```bash
git fetch origin main
```

## Step 2 — Gather the data

All windows below are `WINDOW_START` → `WINDOW_END`. Use `--limit 100`
on every `gh` list call; if anything hits the limit, say "100+" rather
than paginating.

| Section | Source |
|---|---|
| Commits to `main` | `git rev-list --count --since="$WINDOW_START" origin/main` and `git shortlog -sn --since="$WINDOW_START" origin/main` |
| Merged PRs | `gh pr list --state merged --search "merged:>=<date>" --json number,title,author,mergedAt` |
| Closed-unmerged PRs | `gh pr list --state closed --search "closed:>=<date>" ...` minus the merged ones |
| Open PRs awaiting review | `gh pr list --state open --json number,title,author,createdAt,isDraft` (exclude drafts) |
| Issues opened / closed | `gh issue list --state all --search "created:>=<date>"` and `--state closed --search "closed:>=<date>"` |
| Needs human attention | `gh issue list --state open --label claude-needs-human --json number,title` |
| Stale PRs | open non-draft PRs with `createdAt` older than 14 days |

`<date>` in `gh` search qualifiers is the `YYYY-MM-DD` part of
`WINDOW_START`. The day-granularity overlap with the previous digest is
acceptable; do not try to be cleverer than the search API allows.

To characterise the week (the one-clause summaries below), skim the
merged-PR titles and `git log --oneline --since="$WINDOW_START"
origin/main` — do not read diffs unless a title is uninformative.

## Step 3 — Compose the digest

Match the format already established in the channel. Slack markdown,
one message, target well under 3000 characters. Links must be full
GitHub URLs in Slack link form, e.g.
`<https://github.com/RConsortium/submissions-pilot7-synthetic-data/pull/47|#47>`
(bare `#47` does not link in Slack).

Template (omit a bullet entirely if it has nothing to report; if the
whole week is quiet, send just the header plus "Quiet week — no commit,
PR, or issue activity."):

```
:test_tube: *submissions-pilot7-synthetic-data — week of <WINDOW_START> → <WINDOW_END>*
• *Commits:* <N> from <M> contributors (<names>) — <one clause on the dominant theme>.
• *PRs:* <N> merged — <#link> <one-clause description>, <#link> <one-clause description>. <Closed-unmerged or notable open PRs, if any.>
• *Issues:* <opened/closed/still-active counts with <#links> and short labels>.
• *Needs attention:* <open `claude-needs-human` issues, stale PRs> — only when non-empty.
• *TL;DR:* <1–2 sentences: what landed, what's next>.
```

Keep it tight: short clauses, titles paraphrased not pasted, no
section the reader can't act on. The reader can click through.

## Step 4 — Send

Send the message to channel `C0B44HS7CNA` with the Slack send-message
tool. Verify the send succeeded (a message timestamp came back). Do not
post to any other channel, thread, or DM, and do not post twice — if the
send result is ambiguous, re-read the channel to check before retrying.

---

## Hard rules

- **Never** push, commit, branch, open PRs, create/close/label issues,
  or comment on GitHub. This routine writes nothing to GitHub at all.
- **Never** post to any Slack destination other than `C0B44HS7CNA`.
- **Never** send more than one message per run, or any message at all if
  the idempotency guard in Step 1 trips.
- **Never** @-mention users or use `@here`/`@channel`.
- No file writes outside `/tmp/`.
- If a `gh` call or Slack call fails (auth, network, rate limit), print
  the error to stdout and exit non-zero — do not post a partial digest.

## End-of-run summary

Print one line per action to stdout so the routine log is useful:

```
Window   2026-06-11 → 2026-06-18
Posted   to #pilot7-sdtm-adam-tlf-bench (ts 1781234567.123456)
```

Or, when the guard trips: `SKIP: last digest posted 2026-06-11`.
No other output.
