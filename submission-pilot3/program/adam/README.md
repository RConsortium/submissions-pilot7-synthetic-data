# Submission Pilot 3 ADaM derivations

R and Python run the same [yamaa project](../../spec/yamaa/project.yaml):
ADSL -> ADAE -> ADADAS -> ADTTE -> ADLBC.
The engine revision is pinned in [python/requirements.txt](python/requirements.txt).

Run the commands below from the repository root.

## Setup

Source installation requires Python 3.12+, Rust/Cargo 1.82+, Git, and a C
compiler. The R runner also requires R 4.2+.
The R planning generator requires `arrow` (`install.packages("arrow")`).

Install the Python engine and comparison tools:

```bash
python -m pip install -r submission-pilot3/program/adam/python/requirements.txt
```

For R, build the package from the same pinned revision:

```bash
mkdir -p .build/pilot3-r/library
git clone https://github.com/elong0527/yamaa.git .build/pilot3-r/yamaa-source
git -C .build/pilot3-r/yamaa-source checkout --detach 3e8d5f6b5d2af223fba6aa29fa7209699123f706
(
  cd .build/pilot3-r/yamaa-source
  python -m tools.staging.stage_r_package ../package
)
R CMD INSTALL --library=.build/pilot3-r/library .build/pilot3-r/package
```

With rustup, staging uses the checkout's declared Rust toolchain.

## Run and compare

Choose either runner:

```bash
# R
Rscript --vanilla submission-pilot3/program/adam/R/make_plan.R
R_LIBS="$PWD/.build/pilot3-r/library" Rscript --vanilla submission-pilot3/program/adam/R/run.R

# Python
python submission-pilot3/program/adam/python/make_plan.py
python submission-pilot3/program/adam/python/run.py
```

Both write `submission-pilot3/data/adam/<dataset>-yamaa.parquet`.
Compare the outputs with the official references:

```bash
python submission-pilot3/program/adam/python/compare.py
```
