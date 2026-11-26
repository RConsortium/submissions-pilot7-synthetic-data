# PHMPT reproduction kit

yamaa specifications that reproduce the ADaM datasets and Define-XML that
Moderna and Pfizer/BioNTech submitted for four COVID-19 vaccine trials, as
FDA released them on [phmpt.org](https://phmpt.org/) (Module 5, Full
Productions), and the scripts that check them. The results are on the
[Pilot 7 site](https://rconsortium.github.io/submissions-pilot7-synthetic-data/phmpt/)
and in `../docs/phmpt/evidence.json`.

Exported from the development repository at `2bf2cfd21e3e`
with yamaa `0b46a21` (`yamaa.lock`), results collected
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

Needs Python 3.12 and yamaa built from the commit in `yamaa.lock`:

```sh
git clone https://github.com/elong0527/yamaa.git
git -C yamaa checkout $(awk '/^commit:/{print $2}' yamaa.lock)
pip install maturin && (cd yamaa/python && maturin build --release -o wheels)
pip install yamaa/python/wheels/*.whl -r requirements.txt
```

Then, from this folder:

```sh
python scripts/reproduce.py fetch  --study mrna-1273-p201 --cut s3-d57   # reads only the needed zip members
python scripts/reproduce.py verify --study mrna-1273-p201 --cut s3-d57   # run the specs, compare
python scripts/reproduce.py fetch  --study mrna-1273-p201 --dataset define-adam
python scripts/reproduce.py define --study mrna-1273-p201 --transcribe  # transcribe, compose, compare
```

`fetch` writes `<cut>/data/` and `<cut>/spec/define/define-adam.xml`;
`.gitignore` keeps them out of the repository. C4591001 specs also read
study-level lists: `python scripts/convert_lists.py`. The review page of each
finding gives its exact commands.

40 input files exist on PHMPT only as JMP tables (`format` `jmp` in
`data/sources.csv`). JMP has no open reader, so `fetch` cannot rebuild them;
a dataset that reads one needs a conversion of your own (the development
repository holds reviewed conversions).
