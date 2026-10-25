# CDISC Pilot 01 ADaM derivations

R and Python run the same [yamaa project](../../spec/yamaa/project.yaml):
ADSL -> ADAE -> ADTTE -> ADVS -> ADLBC -> ADLBH -> ADLBHY -> ADQSNPIX
-> ADQSADAS -> ADQSCIBC.
The engine revision is pinned in [python/requirements.txt](python/requirements.txt).

Run the commands below from the repository root.

## Setup

Source installation requires Python 3.12+, Rust/Cargo 1.82+, Git, and a C
compiler. The R runner also requires R 4.2+.

Install the Python engine and comparison tools:

```bash
python -m pip install -r cdiscpilot01/program/adam/python/requirements.txt
```

For R, build the package from the same pinned revision:

```bash
mkdir -p .build/cdiscpilot01-r/library
git clone https://github.com/elong0527/yamaa.git .build/cdiscpilot01-r/yamaa-source
git -C .build/cdiscpilot01-r/yamaa-source checkout --detach 3e8d5f6b5d2af223fba6aa29fa7209699123f706
(
  cd .build/cdiscpilot01-r/yamaa-source
  python -m tools.staging.stage_r_package ../package
)
R CMD INSTALL --library=.build/cdiscpilot01-r/library .build/cdiscpilot01-r/package
```

With rustup, staging uses the checkout's declared Rust toolchain.

## Run and compare

Choose either runner:

```bash
# R
R_LIBS="$PWD/.build/cdiscpilot01-r/library" Rscript --vanilla cdiscpilot01/program/adam/R/run.R

# Python
python cdiscpilot01/program/adam/python/run.py
```

Both write `cdiscpilot01/data/adam/<dataset>-yamaa.parquet`.
Compare the outputs with the official references:

```bash
python cdiscpilot01/program/adam/python/compare.py
```

The ADQSNPIX specification is named `adqsnipx.yaml`; its reference is
`adqsnpix.parquet`. ADQSADAS and ADQSCIBC read SDTM QS and derived ADSL,
with window selection and LOCF implemented in their yamaa specifications.
