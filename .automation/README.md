# Scheduled agent tasks

This folder contains prompts for externally configured Claude Code routines.
The runner starts at the repository root with authenticated `gh` and `git`.
Repository conventions and checks live in `AGENTS.md`.

| Prompt | Task | Access and state |
| --- | --- | --- |
| `triage_issues.md` | Answer open issues or open a reviewed change as a PR. | GitHub issue comments and labels, branch pushes, and PR creation. State: `claude-triaged` and `claude-needs-human` labels. |
| `weekly_update.md` | Send one weekly activity digest to the team Slack channel. | Read-only GitHub; Slack channel read and post access. State: the previous digest in channel history. |
| `consistency_review/workflow.md` | Review one dataset's derivations against the submission documents and open a PR whose report cites a rule and quotes the sources for every finding. Uses the `extract.md` and `adjudicate.md` subagent prompts and the rules in `rules.yaml`. | Repository read/edit, the study's pinned engine, branch pushes and PR creation. State: `<study>/spec/review/<dataset>-claims.json`, `-documented-rules.yaml` and `-adjudication.json`. |

## Configure a routine

Register each prompt as a separate routine. Use this instruction, replacing
`<prompt>` with its filename:

```text
Read .automation/<prompt> from the repository root and execute it. Follow AGENTS.md and the prompt's scope, state rules, and end-of-run summary.
```

For triage, choose the desired cadence and provide repository read/edit tools,
`gh`, and `git`. Builds use the affected study's pinned requirements only when
needed; answering an issue requires no study environment. The runner must be
able to create `claude-bot/*` branches and PRs. A human reviews and merges.

For the weekly digest, schedule it before the Friday standup in
`America/Los_Angeles`. Attach the Slack connector with access to
`C0B44HS7CNA` in `rconsortium.slack.com`. Follow the prompt's reporting window,
send guard, and destination exactly.

## CORE reports are handled by CI

`.github/workflows/core-validate.yml` runs CORE and retains per-study
`core-reports-<study>` artifacts for 90 days. Reports stay in those artifacts;
the workflow does not open PRs, post comments, or add labels to issues. No
scheduled agent or R bootstrap is involved.

When migrating an existing routine configuration:

- Disable any old CORE dataset-comment routine. Its prompt and the old
  `core-validation-reports` artifact contract have been retired.
- Replace any copied triage instructions with the file reference above.
- Check branch rules if they require checks from the retired Structure Check
  or Pilot3 plan.csv workflows; their jobs now run in `CI`.

Routine registrations live outside this repository and are managed separately.
See `.github/AUTOMATION.md` for CI ownership, local commands, and report artifacts.
