# Reproduce from PHMPT

Every result in this section can be rerun on your own machine from the files FDA released on [phmpt.org](https://phmpt.org/). The kit in [`phmpt/`](https://github.com/RConsortium/submissions-pilot7-synthetic-data/tree/main/phmpt) holds the specs and the scripts, and no PHMPT file. Its scripts read only the zip members they need, straight from PHMPT, and write them into folders git ignores. The differences your run finds, row by row, stay on your machine.

## What you need

- Python 3.12 and git.
- A Rust toolchain ([rustup](https://rustup.rs/)), to build yamaa from source.
- 15 GB of memory. The specs are built to run in 15 GB: the largest datasets run in USUBJID partitions streamed through disk (`partitions` in `phmpt/studies.yaml`).
- Disk: the fetched Parquet files of every cut take about 1.08 GB (mRNA-1273-P201 0.02 GB, mRNA-1273-P301 0.55 GB, BNT162-01 0.01 GB, C4591001 0.51 GB). Allow more for temporary files: `fetch` writes each SAS transport file to a temporary folder before converting it, and `verify` writes partitions to the folder `VERIFY_TMPDIR` names (the system temporary folder by default).
- Network access to PHMPT's storage, which serves the Full Productions zips.
- For mRNA-1273-P301 and four C4591001 files: your own conversion of the 40 inputs PHMPT released only as JMP tables ([below](#jmp)).

## Set up

In an empty folder:

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

`yamaa.lock` pins the yamaa commit every published result was produced with (`4ea397f`). `requirements.txt` adds pyarrow, pandas, PyYAML and lxml; pyreadstat and zipfile-deflate64 for `fetch`; and openpyxl for `scripts/convert_lists.py`.

!!! note "macOS"

    zipfile-deflate64 0.2.0 does not compile with current Apple clang. Install it first with
    `CFLAGS="-Dfdopen=fdopen" pip install zipfile-deflate64`, then install `requirements.txt`.

Every command below runs in `phmpt/`.

## The steps

1. **fetch.** `python scripts/reproduce.py fetch --study <study> --cut <cut>` reads each file of the cut listed in `data/sources.csv` from its PHMPT Full Productions zip, with HTTP range requests, so only that member is downloaded (the zips are up to tens of GB). It converts SAS transport files to Parquet in `<study>/<cut>/data/sdtm/` and `data/adam/`, and copies the received define unchanged to `<study>/<cut>/spec/define/define-adam.xml`. `--dataset <name>` fetches one file (`define-adam` for the define), and `--dry-run` lists the zip and member of each file without fetching. Without `--cut`, it covers every cut of the study.
2. **convert_lists (C4591001).** `python scripts/convert_lists.py` reads the spreadsheets the C4591001 specs read (subject lists, term lists, a BMI scale) from the same zips and writes `c4591001/data/lists/`. It copies cells and derives nothing.
3. **verify.** `python scripts/reproduce.py verify --study <study> --cut <cut>` runs each spec of the cut on the fetched data and compares the output with the submitted dataset under the study's [comparison rules](glossary.md#comparison-rules). `--dataset adsl` (or a comma-separated list) runs one dataset. Each dataset writes a report to `.local-run/reports/<study>-<cut>-<dataset>.json`; helper outputs are kept in `.local-run/work/<study>/<cut>/`.
4. **define.** `python scripts/reproduce.py define --study <study> --transcribe` transcribes each received define into the [reproduced-mode layer](glossary.md#reproduced-mode-layer) (`<cut>/spec/define/`), composes `define-adam-yamaa.xml` from the specs and that layer, and compares it element by element with the received define. Each cut writes `.local-run/reports/define-<study>-<cut>.json`. Run it for the whole study, after fetching every cut's define: a later cut's layer is written over the earlier cut's.

## Compare your run with the published results

```sh
python scripts/site/check_verdicts.py --evidence ../docs/phmpt/evidence.json
```

For every report in `.local-run/reports/`, this prints `ok` or `FAIL` with your result and the published one, and exits 1 on any disagreement. Datasets you did not run are skipped. A report's `status` reads against the published result as follows:

| Your report | Published result |
| --- | --- |
| `exact` | Exact |
| `exact under comparison rules` | Exact under the comparison rules |
| `mismatch`, with the published number of differing cells | Matches except missing input; reproduced on a substitute input; matches except a defect of the submitted file; N cells differ |

A `mismatch` report counts the differing cells of each column (`columns.<name>.mismatches`) and shows example rows (`lines`). Those rows are participant-level data: keep them on your machine. A define report gives the `verdict` and the `unexplained` differences, which the study page's Define-XML section states for each cut.

## Commands for every cut

Each block fetches what the cut's specs read, runs them, then composes and compares the defines and checks the results. Copy a block, or the lines of one cut.

### mRNA-1273-P201 {#mrna-1273-p201}

```sh
# Day 57 analysis (BLA 125752 S3)
python scripts/reproduce.py fetch  --study mrna-1273-p201 --cut s3-d57
python scripts/reproduce.py verify --study mrna-1273-p201 --cut s3-d57
# Addendum 1 (BLA 125752 S3)
python scripts/reproduce.py fetch  --study mrna-1273-p201 --cut s3-add1
python scripts/reproduce.py verify --study mrna-1273-p201 --cut s3-add1
# Define-XML of every cut with a define
python scripts/reproduce.py fetch  --study mrna-1273-p201 --dataset define-adam
python scripts/reproduce.py define --study mrna-1273-p201 --transcribe
# Compare with the published results
python scripts/site/check_verdicts.py --evidence ../docs/phmpt/evidence.json --study mrna-1273-p201
```

### mRNA-1273-P301 {#mrna-1273-p301}

```sh
# BLA interim analysis (BLA 125752 S3): needs your conversion of 13 JMP-only files (see below)
python scripts/reproduce.py fetch  --study mrna-1273-p301 --cut s3
python scripts/reproduce.py verify --study mrna-1273-p301 --cut s3
# Interim analysis IA1b (27073 S5): needs your conversion of 12 JMP-only files (see below)
python scripts/reproduce.py fetch  --study mrna-1273-p301 --cut s5
# (reads s3 FACE, s3 SUPPFACE, fetched above)
python scripts/reproduce.py verify --study mrna-1273-p301 --cut s5
# Interim analysis IA1a (19745-83 S80): needs your conversion of 11 JMP-only files (see below)
python scripts/reproduce.py fetch  --study mrna-1273-p301 --cut s80
# (reads s3 FACE, s3 SUPPFACE, fetched above)
python scripts/reproduce.py verify --study mrna-1273-p301 --cut s80
# Define-XML of every cut with a define
python scripts/reproduce.py fetch  --study mrna-1273-p301 --dataset define-adam
python scripts/reproduce.py define --study mrna-1273-p301 --transcribe
# Compare with the published results
python scripts/site/check_verdicts.py --evidence ../docs/phmpt/evidence.json --study mrna-1273-p301
```

Released folders with data but no specs yet, which no published result reads: `s27` (8 files).

### BNT162-01 {#bnt162-01}

```sh
# EUA 27034 S1 (Oct 2020)
python scripts/reproduce.py fetch  --study bnt162-01 --cut 27034
python scripts/reproduce.py verify --study bnt162-01 --cut 27034
# BLA 125742 S1 (Mar 2021)
python scripts/reproduce.py fetch  --study bnt162-01 --cut 125742
python scripts/reproduce.py verify --study bnt162-01 --cut 125742
# Define-XML of every cut with a define
python scripts/reproduce.py fetch  --study bnt162-01 --dataset define-adam
python scripts/reproduce.py define --study bnt162-01 --transcribe
# Compare with the published results
python scripts/site/check_verdicts.py --evidence ../docs/phmpt/evidence.json --study bnt162-01
```

### C4591001 {#c4591001}

```sh
# Study-level lists, which the specs of every cut below read
python scripts/convert_lists.py
# Safety and efficacy (BLA 125742 S1)
python scripts/reproduce.py fetch  --study c4591001 --cut s1
python scripts/reproduce.py verify --study c4591001 --cut s1
# 1-month cut (BLA 125742 S211)
python scripts/reproduce.py fetch  --study c4591001 --cut s211-1mth
python scripts/reproduce.py verify --study c4591001 --cut s211-1mth
# EUA resubmission (EUA 27034 S135): needs your conversion of 2 JMP-only files (see below)
python scripts/reproduce.py fetch  --study c4591001 --cut s135
python scripts/reproduce.py verify --study c4591001 --cut s135
# 6-month cut, ages 12-15 (BLA 125742 S211)
python scripts/reproduce.py fetch  --study c4591001 --cut s211-6mth
# (reads s135 AE, s135 SUPPAE, fetched above)
python scripts/reproduce.py verify --study c4591001 --cut s211-6mth
# Supplementary datasets (BLA 125742 S1 Supp)
python scripts/reproduce.py fetch  --study c4591001 --cut s1-supp
# (reads the s1 files, fetched above)
python scripts/reproduce.py verify --study c4591001 --cut s1-supp
# XB datasets (BLA 125742 S6)
python scripts/reproduce.py fetch  --study c4591001 --cut s6
# (reads the s1 files, fetched above)
python scripts/reproduce.py verify --study c4591001 --cut s6
# EUA safety and final efficacy (EUA 27034 S1): needs your conversion of 1 JMP-only file (see below)
python scripts/reproduce.py fetch  --study c4591001 --cut s1-safety-fa-eff
python scripts/reproduce.py verify --study c4591001 --cut s1-safety-fa-eff
# EUA interim efficacy analysis (EUA 27034 S1): needs your conversion of 1 JMP-only file (see below)
python scripts/reproduce.py fetch  --study c4591001 --cut s1-ia
python scripts/reproduce.py verify --study c4591001 --cut s1-ia
# Define-XML of every cut with a define
python scripts/reproduce.py fetch  --study c4591001 --dataset define-adam
python scripts/reproduce.py define --study c4591001 --transcribe
# Compare with the published results
python scripts/site/check_verdicts.py --evidence ../docs/phmpt/evidence.json --study c4591001
```

Released folders with data but no specs yet, which no published result reads: `s9-safety-fa-eff` (2 files).

### Run time {#run-time}

*Run times will be added here from a full rerun of every cut from PHMPT.*

## Inputs released only as JMP tables {#jmp}

PHMPT released 40 input files only as JMP tables, not as SAS transport files (`format` `jmp` in `data/sources.csv`). JMP has no open reader, so `fetch` lists them and skips them. The published results used conversions reviewed in the development repository (each converted twice and cross-checked with the define, the programs and the SAS transport datasets that carry the same variables). To rerun a dataset that reads one of these files, supply your own conversion:

1. Get the original file: `python scripts/reproduce.py fetch --study <study> --cut <cut> --jmp` saves each JMP member of the cut unchanged, next to where its conversion belongs (`<study>/<cut>/data/sdtm/<name>.jmp` or `data/adam/`), in a folder git ignores. Add `--dataset <name>` to fetch one file.
2. Convert it to Parquet at the path `data/sources.csv` gives (the same name with `.parquet`), with the released table's columns, values and types. `sources.csv` gives its number of rows and columns. One route: export it from JMP as a SAS transport file and convert that with the kit's converter: `python -c "import sys; sys.path.insert(0, 'scripts'); from convert_xpt import convert_file; convert_file(sys.argv[1], sys.argv[2], 'JMP export')" <name>.xpt <path>`.
3. Cut every text value at its first NUL byte: `python scripts/cut_jmp_strings.py`. JMP keeps text in fixed-width buffers and shows only what comes before the first NUL. Where FDA redacted a value, it wrote `(b)(6)` and a NUL over the start of the buffer and left the rest of the original value behind the NUL. A reader that keeps the whole buffer exposes that leftover text, which is redacted information: cut it, and never publish or paste it anywhere.

A difference on a dataset that reads your conversion may come from the conversion; compare the file with the published row and column counts before you report it.

Each table lists the JMP-only files of one cut, where PHMPT holds them, and the published results that read them: as the submitted dataset a result is compared with, or as an input.

#### mRNA-1273-P301 BLA interim analysis (BLA 125752 S3)

| File | PHMPT zip and member | Published results that read it |
| --- | --- | --- |
| `s3/data/adam/adae.parquet` | md-production-060225.zip: `FDA-CBER-2022-1614-4147731-4148673_125752_S3_M5_mrna-1273-p301_A_D_adae.jmp` | compared with it: ADAE |
| `s3/data/adam/adcm.parquet` | md-production-060225.zip: `FDA-CBER-2022-1614-4148674-4153549_125752_S3_M5_mrna-1273-p301_A_D_adcm.jmp` | compared with it: ADCM; input to ADSL |
| `s3/data/adam/admh.parquet` | md-production-060225.zip: `FDA-CBER-2022-1614-4202982-4207395_125752_S3_M5_mrna-1273-p301_A_D_admh.jmp` | compared with it: ADMH |
| `s3/data/adam/adrisk.parquet` | md-production-060225.zip: `FDA-CBER-2022-1614-4153550-4167991_125752_S3_M5_mrna-1273-p301_A_D_adrisk.jmp` | compared with it: ADRISK |
| `s3/data/adam/adsl.parquet` | md-production-050125.zip: `FDA-CBER-2022-1614-3824347-3825106_125752_S3_M5_mrna-1273-p301_A_D_adsl.jmp` | all 25 datasets of the cut: compared with it (ADSL), input to the other 24 |
| `s3/data/adam/adslsf.parquet` | md-production-020325.zip: `FDA-CBER-2022-1614-2982713-2982753_125752_S3_M5_mrna-1273-p301_A_D_adslsf.jmp` | compared with it: ADSLSF |
| `s3/data/sdtm/cm.parquet` | md-production-060225.zip: `FDA-CBER-2022-1614-4169217-4174092_125752_S3_M5_mrna-1273-p301_S_cm.jmp` | input to ADCM |
| `s3/data/sdtm/ds.parquet` | md-production-050125.zip: `FDA-CBER-2022-1614-3825911-3830059_125752_S3_M5_mrna-1273-p301_S_ds.jmp` | input to ADAE, ADSL, ADSLSF |
| `s3/data/sdtm/mh.parquet` | md-production-060225.zip: `FDA-CBER-2022-1614-4207396-4216570_125752_S3_M5_mrna-1273-p301_S_mh.jmp` | input to ADMH, ADSL |
| `s3/data/sdtm/pr.parquet` | md-production-050125.zip: `FDA-CBER-2022-1614-3830060-3830345_125752_S3_M5_mrna-1273-p301_S_pr.jmp` | input to ADSYMP |
| `s3/data/sdtm/sc.parquet` | md-production-060225.zip: `FDA-CBER-2022-1614-4174247-4188700_125752_S3_M5_mrna-1273-p301_S_sc.jmp` | input to ADRISK |
| `s3/data/sdtm/suppdv.parquet` | md-production-010225.zip: `FDA-CBER-2022-1614-2782091-2788258_125752_S3_M5_mrna-1273-p301_S_suppdv.jmp` | input to ADDV, ADSL |
| `s3/data/sdtm/sv.parquet` | md-production-060225.zip: `FDA-CBER-2022-1614-4188701-4201848_125752_S3_M5_mrna-1273-p301_S_sv.jmp` | input to ADSL, ADVS |

#### mRNA-1273-P301 Interim analysis IA1b (27073 S5)

| File | PHMPT zip and member | Published results that read it |
| --- | --- | --- |
| `s5/data/adam/adae.parquet` | md-eua-110325.zip: `FDA-CBER-2022-1614-4441946 - 4442346_27073_S5_M5_mrna-1273-p301_A_adae.jmp` | compared with it: ADAE |
| `s5/data/adam/adaesmq.parquet` | md-eua-110325.zip: `FDA-CBER-2022-1614-4442347 - 4442747_27073_S5_M5_mrna-1273-p301_A_adae.jmp` | compared with it: ADAESMQ |
| `s5/data/adam/adcm.parquet` | md-eua-090126.zip: `FDA-CBER-2022-1614-6431855-6435791_27073_S5_M5_mrna-1273-p301_A_adcm.jmp` | compared with it: ADCM |
| `s5/data/adam/adrisk.parquet` | md-eua-080326.zip: `FDA-CBER-2022-1614-6314544-6328949_27073_S5_M5_mrna-1273-p301_A_adrisk.jmp` | compared with it: ADRISK |
| `s5/data/adam/adsl.parquet` | md-eua-080326.zip: `FDA-CBER-2022-1614-6328950-6329713_27073_S5_M5_mrna-1273-p301_A_adsl.jmp` | all 19 datasets of the cut: compared with it (ADSL), input to the other 18 |
| `s5/data/sdtm/cm.parquet` | md-eua-090126.zip: `FDA-CBER-2022-1614-6438496-6442432_27073_S5_M5_mrna-1273-p301_S_cm.jmp` | input to ADCM |
| `s5/data/sdtm/ds.parquet` | md-eua-010226.zip: `FDA-CBER-2022-1614-4982646 - 4985010_27073_S5_M5_mrna-1273-p301_S_ds.jmp` | input to ADAE, ADAESMQ, ADSL |
| `s5/data/sdtm/mh.parquet` | md-eua-090126.zip: `FDA-CBER-2022-1614-6443236-6451245_27073_S5_M5_mrna-1273-p301_S_mh.jmp` | input to ADSL |
| `s5/data/sdtm/sc.parquet` | md-eua-080326.zip: `FDA-CBER-2022-1614-6350394-6364848_27073_S5_M5_mrna-1273-p301_S_sc.jmp` | input to ADRISK |
| `s5/data/sdtm/suppdv.parquet` | md-eua-040126.zip: `FDA-CBER-2022-1614-5660327-5660987_27073_S5_M5_mrna-1273-p301_S_suppdv.jmp` | input to ADDV, ADSL |
| `s5/data/sdtm/sv.parquet` | md-eua-090126.zip: `FDA-CBER-2022-1614-6451246-6459075_27073_S5_M5_mrna-1273-p301_S_sv.jmp` | input to ADVS |
| `s5/data/sdtm/vs.parquet` | md-eua-080326.zip: `FDA-CBER-2022-1614-6365478-6405905_27073_S5_M5_mrna-1273-p301_S_vs.jmp` | input to ADAR, ADAR1, ADAR2, ADARP7D, ADARSUM, ADSL, ADSYMP, ADVS |

#### mRNA-1273-P301 Interim analysis IA1a (19745-83 S80)

| File | PHMPT zip and member | Published results that read it |
| --- | --- | --- |
| `s80/data/adam/adae.parquet` | md-eua-110325.zip: `FDA-CBER-2022-1614-4534520 - 4534852_19745-83_S80_M5_mrna-1273-p301_A_.jmp` | compared with it: ADAE |
| `s80/data/adam/adcm.parquet` | md-eua-090126.zip: `FDA-CBER-2022-1614-6405906-6409666_19745-83_S80_M5_mrna-1273-p301_A_ad.jmp` | compared with it: ADCM |
| `s80/data/adam/adrisk.parquet` | md-eua-080326.zip: `FDA-CBER-2022-1614-6225618-6240008_19745-83_S80_M5_mrna-1273-p301_A_ad.jmp` | compared with it: ADRISK |
| `s80/data/adam/adsl.parquet` | md-eua-080326.zip: `FDA-CBER-2022-1614-6240009-6240772_19745-83_S80_M5_mrna-1273-p301_A_ad.jmp` | all 18 datasets of the cut: compared with it (ADSL), input to the other 17 |
| `s80/data/sdtm/cm.parquet` | md-eua-090126.zip: `FDA-CBER-2022-1614-6412068-6415828_19745-83_S80_M5_mrna-1273-p301_S_cm.jmp` | input to ADCM |
| `s80/data/sdtm/ds.parquet` | md-eua-010226.zip: `FDA-CBER-2022-1614-4890863 - 4893187_19745-83_S80_M5_mrna-1273-p301_S_.jmp` | input to ADAE, ADSL |
| `s80/data/sdtm/mh.parquet` | md-eua-090126.zip: `FDA-CBER-2022-1614-6416632-6424539_19745-83_S80_M5_mrna-1273-p301_S_mh.jmp` | input to ADSL |
| `s80/data/sdtm/sc.parquet` | md-eua-080326.zip: `FDA-CBER-2022-1614-6260672-6275110_19745-83_S80_M5_mrna-1273-p301_S_sc.jmp` | input to ADRISK |
| `s80/data/sdtm/suppdv.parquet` | md-eua-040126.zip: `FDA-CBER-2022-1614-5656383-5656940_19745-83_S80_M5_mrna-1273-p301_S_su.jmp` | input to ADDV, ADSL |
| `s80/data/sdtm/sv.parquet` | md-eua-090126.zip: `FDA-CBER-2022-1614-6424540-6431854_19745-83_S80_M5_mrna-1273-p301_S_sv.jmp` | input to ADVS |
| `s80/data/sdtm/vs.parquet` | md-eua-080326.zip: `FDA-CBER-2022-1614-6275739-6314543_19745-83_S80_M5_mrna-1273-p301_S_vs.jmp` | input to ADAR, ADAR1, ADAR2, ADARP7D, ADARSUM, ADSL, ADSYMP, ADVS |

#### C4591001 EUA resubmission (EUA 27034 S135)

| File | PHMPT zip and member | Published results that read it |
| --- | --- | --- |
| `s135/data/sdtm/co.parquet` | p1215d-eua-production-080125.zip: `FDA-CBER-2022-5812-0526166-0529890_27034_S135_M5_c4591001_S_D_co.jmp` | input to ADSL |
| `s135/data/sdtm/mh.parquet` | p1215d-eua-production-090225.zip: `FDA-CBER-2022-5812-0940211 - 0945135_27034_S135_M5_c4591001_S_D_mh.jmp` | input to ADMH, ADSL, ADSYMPT |

#### C4591001 EUA safety and final efficacy (EUA 27034 S1)

| File | PHMPT zip and member | Published results that read it |
| --- | --- | --- |
| `s1-safety-fa-eff/data/sdtm/co.parquet` | pd-eua-production-051925.zip: `FDA-CBER-2021-5683-1504670-1506840_27034_S1_M5_c4591001-safety-fa-eff-S-co.jmp` | input to ADSL |

#### C4591001 EUA interim efficacy analysis (EUA 27034 S1)

| File | PHMPT zip and member | Published results that read it |
| --- | --- | --- |
| `s1-ia/data/sdtm/co.parquet` | pd-eua-production-051925.zip: `FDA-CBER-2021-5683-1239581-1241516_27034_S1_M5_c4591001-ia efficacy-S-co.jmp` | input to ADSL |

## Keep PHMPT data local

- `phmpt/.gitignore` keeps everything the kit fetches or writes out of git: `*/*/data/`, `*/data/lists/`, `*/*/spec/define/` and `.local-run/`. Do not commit any of it, and do not force-add it.
- Do not paste rows, subject identifiers, data values or program text from PHMPT files into a review discussion or an issue. Cite the finding and describe the difference with column names and counts ([review a finding](review/index.md)).
