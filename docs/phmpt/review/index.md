# Review a PHMPT finding

Each finding below is one claim about one cut of a study: an ADaM dataset
reproduces the submitted one, the define reproduces the received one, or a
define difference comes from a named defect of the submitted define, which
yamaa does not copy. Every claim is a draft
pending human review; one evidence-backed assessment is a complete
contribution.

## How to review

1. **Choose a finding.** Filter by study, kind or verdict, or search for a
   dataset (`ADSL`) or a defect of the submitted define (`repeated-order`).
   Findings that are not exact, and define defects, are the most useful to
   check.
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

Follow
[`phmpt/reproduce.sh`](https://github.com/RConsortium/submissions-pilot7-synthetic-data/blob/main/phmpt/reproduce.sh):
its header says what you need. From the root of a clone of this repository:

```sh
sh phmpt/reproduce.sh setup        # once: build yamaa at yamaa.lock, install the kit
sh phmpt/reproduce.sh bnt162-01    # fetch, define, verify, compare with the published results
```

To rerun one finding, run the commands under **Reproduce it** in `phmpt/`
after `. .local-run/venv/bin/activate`. Keep what you fetch and the
differences you find on your machine.

## Findings

<div id="phmpt-review" class="phmpt-review" data-review-url="https://github.com/RConsortium/submissions-pilot7-synthetic-data/discussions/new?category=general"></div>
