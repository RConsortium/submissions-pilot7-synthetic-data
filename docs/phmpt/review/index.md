# Review a PHMPT finding

Each finding below is one claim about one cut of a study: an ADaM dataset
reproduces the submitted one, the define reproduces the received one, or a
define difference is a named yamaa engine gap. Every claim is a draft
pending human review; one evidence-backed assessment is a complete
contribution.

## How to review

1. **Choose a finding.** Filter by study, kind or verdict, or search for a
   dataset (`ADSL`) or an engine gap (`G1`). Findings that are not exact,
   and define gaps, are the most useful to check.
2. **Check the evidence.** It gives the counts behind the claim, the reason
   recorded for every difference, the specification, and where the
   submitted file is on PHMPT. Exact means the derived data equals the
   submitted data under the comparison rules, not that the specification
   follows the analysis plan; columns carried from the submitted dataset are
   not derived at all.
3. **Rerun it if you want rows.** This site publishes no PHMPT file and no
   participant-level value. The commands under **Reproduce it** fetch the
   inputs from [phmpt.org](https://phmpt.org/) and print the differences on
   your machine.
4. **Submit your assessment.** Choose **Agree**, **Disagree** or **Need
   clarification**, say what you checked, and select **Submit review on
   GitHub**. Check the pre-filled discussion, then select **Start
   discussion**. Drafts save in this browser only.

Do not paste rows, subject identifiers or program text from PHMPT files into
a discussion; describe the difference and cite the finding instead.

## Reproduce a result

[Reproduce from PHMPT](../reproduce.md) is the full guide: what you need,
how to build yamaa at the pinned commit, the commands for every cut, how to
compare your run with the published results, and the inputs PHMPT released
only as JMP tables. Each finding below also lists its own commands under
**Reproduce it**. For example, after the setup, in `phmpt/`:

```sh
python scripts/reproduce.py fetch  --study bnt162-01 --cut 27034
python scripts/reproduce.py verify --study bnt162-01 --cut 27034
python scripts/site/check_verdicts.py --evidence ../docs/phmpt/evidence.json
```

Keep what you fetch and the differences you find on your machine.

## Findings

<div id="phmpt-review" class="phmpt-review" data-review-url="https://github.com/RConsortium/submissions-pilot7-synthetic-data/discussions/new?category=general"></div>
