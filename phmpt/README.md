# PHMPT reproduction kit

yamaa specifications that reproduce the ADaM datasets and Define-XML that
Moderna and Pfizer/BioNTech submitted for four COVID-19 vaccine trials, as
FDA released them on [phmpt.org](https://phmpt.org/) (Module 5, Full
Productions), and the scripts that check them. The results are on the
[Pilot 7 site](https://rconsortium.github.io/submissions-pilot7-synthetic-data/phmpt/) and in `../docs/phmpt/evidence.json`.

This folder is the source of the reproduction. It was developed in a
private repository until 2026-11-27 and has been developed here since
([`DECISIONS.md`](DECISIONS.md), "Pilot 7 is the source").

## What is here, and what is not

| Here | Not here (fetched from PHMPT when you run the kit) |
| --- | --- |
| `<study>/<cut>/spec/yamaa/`, `<study>/spec/yamaa/base/`: the specs | the submitted SDTM and ADaM datasets |
| `scripts/`: fetch, convert, verify, transcribe, compose, compare, publish | the received `define-adam.xml` of each cut |
| `data/sources.csv`, `data/zips.txt`: the PHMPT zip and member of every input | the sponsors' programs and documents |
| `data/differences.yaml`: every known difference and its reason | participant-level values of any kind |
| `data/reproduction/`: the results, as counts and verdicts | the run reports (`.local-run/`) |
| `DECISIONS.md`: the owner's standing decisions | |

## Reproduce a result

Follow [`reproduce.sh`](reproduce.sh): its header says what you need and
what to run. In short, from the root of this repository:

```sh
sh phmpt/reproduce.sh setup              # once: build yamaa at yamaa.lock, install the kit
sh phmpt/reproduce.sh mrna-1273-p201     # fetch, define, verify, compare with the published results
```

40 input files exist on PHMPT only as JMP tables, so a dataset that reads
one needs a conversion of your own; the script's header says how. Keep what
the kit fetches and writes local: never commit it, and never paste rows,
subject identifiers or program text from it into a review discussion.

## Change a spec or a result

Work in a branch. Every push is public, so commit only what `DECISIONS.md`
allows; the publication gate checks it on each pull request.

1. Edit the specs. A submission `method` or origin `description` keeps the
   placeholder: `reproduce.py define --transcribe` restates the received
   text locally.
2. Rerun what changed, from `phmpt/` with the kit's venv active:
   `python scripts/reproduce.py verify --study <study> --cut <cut>` and
   `python scripts/reproduce.py define --study <study> --transcribe`.
3. Compare your run with the recorded results:
   `python scripts/site/check_verdicts.py --study <study>`. To record new
   results, rerun every study (`sh phmpt/reproduce.sh all`, hours), then
   `python scripts/reproduce.py site`, which writes `data/reproduction/`
   (`scripts/site/collect_results.py`, and the submitted column names from
   `scripts/site/inventory_columns.py`) and the pages
   (`scripts/site/publish.py`). A difference with a known cause goes in
   `data/differences.yaml` first.
4. Before pushing, from the repository root:
   `python3 .github/scripts/check_phmpt_bundle.py .` and
   `python3 phmpt/scripts/site/publish.py --check`.
