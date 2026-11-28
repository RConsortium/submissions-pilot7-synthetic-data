# PHMPT reproduction kit

yamaa specifications that reproduce the ADaM datasets and Define-XML that
Moderna and Pfizer/BioNTech submitted for four COVID-19 vaccine trials, as
FDA released them on [phmpt.org](https://phmpt.org/) (Module 5, Full
Productions), and the scripts that check them. The results are on the
[Pilot 7 site](https://rconsortium.github.io/submissions-pilot7-synthetic-data/phmpt/) and in `../docs/phmpt/evidence.json`.

Exported from the development repository at `4db63a9c8922`
with yamaa `ac826f0` (`yamaa.lock`), results collected
2026-11-27. Do not edit this folder by hand: the next export
replaces it.

## What is here, and what is not

| Here | Not here (fetched from PHMPT when you run the kit) |
| --- | --- |
| `<study>/<cut>/spec/yamaa/`, `<study>/spec/yamaa/base/`: the specs | the submitted SDTM and ADaM datasets |
| `scripts/`: fetch, convert, verify, transcribe, compose, compare | the received `define-adam.xml` of each cut |
| `data/sources.csv`: the PHMPT zip and member of every input | the sponsors' programs and documents |
| `data/differences.yaml`: every known difference and its reason | participant-level values of any kind |

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
