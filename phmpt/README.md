# PHMPT reproduction kit

yamaa specifications that reproduce the ADaM datasets and Define-XML that
Moderna and Pfizer/BioNTech submitted for four COVID-19 vaccine trials, as
FDA released them on [phmpt.org](https://phmpt.org/) (Module 5, Full
Productions), and the scripts that check them. The results are on the
[Pilot 7 site](https://rconsortium.github.io/submissions-pilot7-synthetic-data/phmpt/) and in `../docs/phmpt/evidence.json`.

Exported from the development repository at `eb7d419159ea`
with yamaa `67b14f9` (`yamaa.lock`), results collected
2026-11-26. Do not edit this folder by hand: the next export
replaces it.

## What is here, and what is not

| Here | Not here (fetched from PHMPT when you run the kit) |
| --- | --- |
| `<study>/<cut>/spec/yamaa/`, `<study>/spec/yamaa/base/`: the specs | the submitted SDTM and ADaM datasets |
| `scripts/`: fetch, convert, verify, transcribe, compose, compare | the received `define-adam.xml` of each cut |
| `data/sources.csv`: the PHMPT zip and member of every input | the sponsors' programs and documents |
| `data/differences.yaml`: every known difference and its reason | participant-level values of any kind |

## Reproduce a result

The [Reproduce page](https://rconsortium.github.io/submissions-pilot7-synthetic-data/phmpt/reproduce/) is the full guide: what you need,
the commands for every cut, how to compare your run with the published
results, and the inputs released only as JMP tables. In short, in an empty
folder (Python 3.12, git and a Rust toolchain):

```sh
git clone https://github.com/RConsortium/submissions-pilot7-synthetic-data
git clone https://github.com/elong0527/yamaa
git -C yamaa checkout $(awk '/^commit:/{print $2}' submissions-pilot7-synthetic-data/phmpt/yamaa.lock)
python3.12 -m venv .venv
. .venv/bin/activate
pip install maturin==1.9.6
(cd yamaa/python && maturin build --release -o wheels)
pip install yamaa/python/wheels/*.whl
pip install -r submissions-pilot7-synthetic-data/phmpt/requirements.txt
cd submissions-pilot7-synthetic-data/phmpt
```

On macOS, zipfile-deflate64 0.2.0 does not compile with current Apple
clang: install it first with `CFLAGS="-Dfdopen=fdopen" pip install
zipfile-deflate64`, then install `requirements.txt`.

Then, from this folder:

```sh
python scripts/reproduce.py fetch  --study mrna-1273-p201 --cut s3-d57   # reads only the needed zip members
python scripts/reproduce.py verify --study mrna-1273-p201 --cut s3-d57   # run the specs, compare
python scripts/reproduce.py define --study mrna-1273-p201 --cut s3-d57 --transcribe   # transcribe, compose, compare
python scripts/site/check_verdicts.py --evidence ../docs/phmpt/evidence.json   # your run against the published results
```

`fetch` writes `<cut>/data/` and `<cut>/spec/define/define-adam.xml`;
`define` writes the transcribed layers in `<cut>/spec/define/`, and the
reports go to `.local-run/`. `.gitignore` keeps all of it out of git: never
commit it, and never paste rows, subject identifiers or program text from
it into a review discussion. C4591001 specs also read study-level lists:
`python scripts/convert_lists.py`. The review page of each finding gives
its exact commands.

40 input files exist on PHMPT only as JMP tables (`format` `jmp` in
`data/sources.csv`). JMP has no open reader, so `fetch` cannot convert
them; a dataset that reads one needs a conversion of your own (`fetch --jmp`
saves the original files; the Reproduce page lists them and says how).
