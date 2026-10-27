# CDISC Pilot 01 ADaM derivations

R and Python run the same [yamaa project](../../spec/yamaa/project.yaml).
The project lists all ten datasets in reference Define-XML order, beginning
with ADSL, which supplies the shared subject-level data.
The engine revision is pinned in [python/requirements.txt](python/requirements.txt).

The same specifications also generate Define-XML 2.0.0 and a comparison with
the published 1.0 reference. See [Define-XML generation and comparison](DEFINE.md)
for commands, coverage and explicit gaps.

Run the commands below from the repository root.

## Setup

Source installation requires Python 3.12+, Git, a C compiler, and the source
checkout's pinned Rust toolchain (1.99.1). The R runner also requires R 4.2+.

Install the Python engine and comparison tools:

```bash
python -m pip install -r cdiscpilot01/program/adam/python/requirements.txt
```

For R, build the package from the same pinned revision:

```bash
mkdir -p .build/cdiscpilot01-r/library
git clone https://github.com/elong0527/yamaa.git .build/cdiscpilot01-r/yamaa-source
git -C .build/cdiscpilot01-r/yamaa-source checkout --detach 1d78496c0cbd4fe89462596a738db3adbd72c8ad
python -m pip install py-yaml12==0.2.0
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
