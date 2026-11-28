# PHMPT reproduction with yamaa

FDA released the submitted SDTM, ADaM and Define-XML of four COVID-19 vaccine trials on [phmpt.org](https://phmpt.org/) (Module 5, Full Productions). AI agents wrote a [yamaa](https://elong0527.github.io/yamaa/) specification for each submitted ADaM dataset, porting the sponsor's programs where they were released; yamaa ran each one on the submitted SDTM; and automated checks compared the output with the submitted dataset cell by cell, and the define composed from the same specifications with the received define element by element. No PHMPT file and no participant-level value is published here: the kit fetches the inputs from PHMPT, so anyone can rerun a result with [`phmpt/reproduce.sh`](https://github.com/RConsortium/submissions-pilot7-synthetic-data/blob/main/phmpt/reproduce.sh). Every result is a draft pending human review.

## Key findings

yamaa `ac826f0`, results collected 2026-11-27. Terms are defined in the [glossary](glossary.md).

- **Analysis set: 158 of 166 ADaM datasets, 16,119 of 17,089 columns and 5,472.17M of 7,350.32M cells**, in the 4 of the 22 PHMPT studies that released ADaM datasets. The analysis set is the part of the release that holds every input its values are derived from; it is fixed from the release, before any comparison ([analysis set](#analysis-set)). What it leaves out is listed with the absent input ([inputs outside the analysis set](findings/inputs.md)).
- **Fully reproduced: 148 of 158 datasets, 15,263 of 16,119 columns and 5,106.83M of 5,472.17M cells**, equal to the submitted values under the comparison rules (numbers within 1e-10, spaces ignored; BNT162-01 is compared strictly). 117 of these datasets hold every input; the other 31 reproduce every value that has one. Of the rest, 1 cell differs, and 855 columns and 365.33M cells were not fully compared (next point).
- **10 datasets in the analysis set are not counted as fully reproduced:** 6 not compared cell by cell, because the release cannot supply some of their columns and `scripts/verify_compare.py` stops when the column sets differ ([mRNA-1273-P301 `s3` ADCM](findings/mrna-1273-p301.md#s3), [C4591001 `s1` ADCM](findings/c4591001.md#s1), [C4591001 `s211-1mth` ADCM](findings/c4591001.md#s211-1mth), [C4591001 `s135` ADCM](findings/c4591001.md#s135), [C4591001 `s211-6mth` ADCM](findings/c4591001.md#s211-6mth), [C4591001 `s6` ADXB](findings/c4591001.md#s6)); 2 only where the submitted file is defective ([C4591001 `s1-safety-fa-eff` ADMH](findings/c4591001.md#s1-safety-fa-eff), [C4591001 `s1-ia` ADC19EF](findings/c4591001.md#s1-ia)); 2 with a diagnosed cause still to fix ([C4591001 `s1-supp` ADCEVD](findings/c4591001.md#s1-supp), [C4591001 `s1-supp` ADFACEVD](findings/c4591001.md#s1-supp)). The datasets that still differ were compared on keys, which do not record the rows on one side only, so none of their cells is counted as reproduced either.
- **Define-XML: 25,210 of 25,210 received elements reproduced** in the 13 deliverables with a define, 25,185 of them byte for byte; the other 25 differ only by named yamaa engine gaps (G1, G6, G8). **0 differences are unexplained.**
- **Define-XML against the data: 688 findings in 129 of the 159 datasets** in the 13 deliverables with a define, where the sponsor's received define and its submitted datasets disagree: 538 mandatory variables with missing values, 81 key sets that repeat, 40 lengths, 15 variables in only one of the two, 8 variables with values outside their codelist, 6 datasets in only one of the two. 228 more, types and labels in files FDA redacted or released as JMP tables, may come from the release and are set apart ([define vs data](findings/define-data.md)).
- **Still open:** the 2 datasets that still differ with a cause to fix; a cell-by-cell comparison of the 6 datasets whose column sets differ; 2 released folders with SDTM but no ADaM datasets and no specs (mRNA-1273-P301 `s27`, C4591001 `s9-safety-fa-eff`); the engine gaps, each tracked as a yamaa issue ([engine gaps](findings/define-gaps.md)); 40 input files PHMPT released only as JMP tables, which the kit cannot fetch ([`phmpt/reproduce.sh`](https://github.com/RConsortium/submissions-pilot7-synthetic-data/blob/main/phmpt/reproduce.sh) says how to supply a conversion).

## Start here

<div class="grid cards" markdown>

-   **Results by study**

    ---

    Each cut's datasets and define, and every difference with its recorded reason.

    [mRNA-1273-P201](findings/mrna-1273-p201.md) - [mRNA-1273-P301](findings/mrna-1273-p301.md) - [BNT162-01](findings/bnt162-01.md) - [C4591001](findings/c4591001.md)

-   **Reproduce from PHMPT**

    ---

    Rerun a study on your machine from phmpt.org with one script. Its header says what you need and what to run.

    [`phmpt/reproduce.sh`](https://github.com/RConsortium/submissions-pilot7-synthetic-data/blob/main/phmpt/reproduce.sh)

-   **Review a finding**

    ---

    Check one finding's evidence and submit your assessment on GitHub.

    [Review a finding](review/index.md)

-   **Glossary**

    ---

    Cut, layer, exact, missing input, carried column, engine gap and the other terms these pages use.

    [Glossary](glossary.md)

-   **Define-XML engine gaps**

    ---

    What yamaa cannot declare yet, with counts per cut and the yamaa issue for each.

    [Engine gaps](findings/define-gaps.md)

-   **Inputs outside the analysis set**

    ---

    Every absent or problem input: what it is, and the datasets, columns and rows it leaves out.

    [Inputs](findings/inputs.md)

-   **Define-XML against the data**

    ---

    Where each received define and its submitted datasets disagree, by check and by deliverable.

    [Define vs data](findings/define-data.md)

-   **Module 5 coverage**

    ---

    All 22 studies: what PHMPT released for each and what is reproduced.

    [Coverage](coverage.md)

</div>

## Analysis set

Results are counted on an analysis set fixed from the release before any comparison: a value is in it when the release holds every input the value is derived from and a submitted value to compare it with. Whether a value reproduces plays no part. Everything outside the set is listed with its absent input on [Inputs outside the analysis set](findings/inputs.md).

<div class="pilot-metrics" markdown="1" role="region" aria-label="Analysis set" tabindex="0">

| Level | Released | Outside the analysis set | Analysis set | Fully reproduced |
| --- | --- | --- | --- | --- |
| Studies | 22 on PHMPT | 18 released documents only, no ADaM datasets ([coverage](coverage.md)) | **4**, 3 of them with the sponsor's ADaM programs | - |
| ADaM datasets | 166 in 15 deliverables, all with a spec | 8 built from a domain the release lacks (mRNA-1273-P301 S5 and S80: ADAR, ADAR1, ADAR2, ADARP7D) | **158** (95.2%) | **148** (93.7%) |
| Columns | 17,089 | 970: 720 in those 8 datasets, 219 that read an absent input, 31 carried from the submitted dataset | **16,119** (94.3%) | **15,263** (94.7%) |
| Cells | 7,350.32M | 1,878.15M: 1,846.69M in those 8 datasets, 31.45M in columns and rows without input, 3,298 submitted cells FDA redacted to `(b)(6)` | **5,472.17M** (74.4%) | **5,106.83M** (93.3%) |

</div>

- **Studies.** Only 4 of the 22 studies released ADaM datasets in Module 5. BNT162-01 released datasets and defines but no programs; its specs follow the define and the data. The others released documents only.
- **Datasets.** Every released ADaM dataset has a spec. A dataset is outside when the release lacks the domain its rows are built from. For mRNA-1273-P301 S5 and S80 it is this cut's FACE (the release has SUPPFACE but no FACE). The spec reads another release's snapshot instead; the study page reports that result, but it is not counted here.
- **Columns.** A column is outside when its derivation reads an input the release does not hold: a licensed dictionary or a sponsor file that was not submitted, SDTM values FDA redacted, or records the released SDTM does not carry. Each absent input is recorded, with the owner's decision, in `data/differences.yaml`. The 31 carried columns are copied from the submitted dataset because their input is absent.
- **Rows and cells.** Where an absent input decides whether a row exists (the WHODRUG ATC expansion of C4591001 ADCM, records the released EUA SDTM lacks), the submitted rows with no derived counterpart are outside: 38,049 rows. The cells are those of the analysis-set columns on the analysis-set rows, less the submitted cells FDA redacted, which have no value to compare with.
- **Fully reproduced** means equal to the submitted value under the study's comparison rules, as the comparison recorded it. A column counts when all of its analysis-set cells do, so a submitted row yamaa does not write counts against every column. A dataset counts when all of its analysis-set cells do and yamaa writes no row the submitted dataset lacks, apart from rows an absent input explains. Nothing is counted as reproduced where the comparison did not account for every cell: 6 datasets whose column sets differ (the comparison stops there) and the 2 that still differ, compared on keys, which do not record rows on one side only. Together they hold 855 columns and 365.33M cells of the set. 117 of the 148 hold every input. Of the other 10, 6 were not compared cell by cell, 2 differ only where the submitted file is defective and 2 still differ ([key findings](#key-findings)).

## Results by study

<div class="pilot-metrics" markdown="1" role="region" aria-label="Results by study" tabindex="0">

| Study | Sponsor | Program files released | Deliverables | Datasets reproduced | Columns reproduced | Cells reproduced | Define-XML elements reproduced | Define vs data findings |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| [mRNA-1273-P201](findings/mrna-1273-p201.md) | Moderna | 61 | 2 | **30 / 30** (100%) | **2,569 / 2,569** (100%)<br>31 without input | **55.98M / 55.98M** (100%) | **4,091 / 4,091** (100%), 0 unexplained<br>engine gaps: G1 (48), G6 (6) | [120 in 26 datasets](findings/define-data.md) |
| [mRNA-1273-P301](findings/mrna-1273-p301.md) | Moderna | 100 | 3 | **53 / 54** (98.1%)<br>1 not compared cell by cell<br>8 outside the analysis set | **5,196 / 5,306** (97.9%)<br>110 not fully compared<br>781 without input | **2,868.58M / 2,890.04M** (99.3%)<br>21.46M not fully compared | **7,671 / 7,671** (100%), 0 unexplained<br>engine gaps: G1 (86), G6 (8) | [502 in 53 datasets](findings/define-data.md) |
| [BNT162-01](findings/bnt162-01.md) | Pfizer/BioNTech | none | 2 | **14 / 14** (100%) | **1,448 / 1,448** (100%) | **24.87M / 24.87M** (100%) | **2,846 / 2,846** (100%), 0 unexplained<br>engine gaps: G1 (18) | [2 in 1 dataset](findings/define-data.md) |
| [C4591001](findings/c4591001.md) | Pfizer/BioNTech | 25 | 8 | **51 / 60** (85.0%)<br>2 match except a submitted-file defect<br>2 still differ<br>5 not compared cell by cell | **6,050 / 6,796** (89.0%)<br>745 not fully compared<br>158 without input | **2,157.40M / 2,501.28M** (86.3%)<br>1 differ<br>343.88M not fully compared | **10,602 / 10,602** (100%), 0 unexplained<br>engine gaps: G8 (8) | [64 in 49 datasets](findings/define-data.md) |
| **All** | | 186 | 15 | **148 / 158** (93.7%)<br>2 match except a submitted-file defect<br>2 still differ<br>6 not compared cell by cell<br>8 outside the analysis set | **15,263 / 16,119** (94.7%)<br>855 not fully compared<br>970 without input | **5,106.83M / 5,472.17M** (93.3%)<br>1 differ<br>365.33M not fully compared | **25,210 / 25,210** (100%), 0 unexplained<br>engine gaps: G1 (152), G6 (14), G8 (8) | [688 in 129 datasets](findings/define-data.md) |

</div>

**Datasets**, **columns** and **cells reproduced** are counted within the [analysis set](#analysis-set): those equal to the submitted values under the comparison rules, of those in the set. A dataset counts when all of its analysis-set cells do. *Without input* counts the columns outside the set. The two define columns cover every dataset of a deliverable with a define. **Define-XML elements reproduced** counts the received elements of datasets with a spec that yamaa's composed define reproduces, exactly or apart from a [named engine gap](findings/define-gaps.md). **Define vs data findings** counts where the sponsor's received define and submitted datasets disagree, release artifacts apart.

## Results by cut

<div class="pilot-metrics" markdown="1" role="region" aria-label="Results by cut" tabindex="0">

| Study and cut | Datasets reproduced | Columns reproduced | Cells reproduced | Define-XML elements reproduced | Define vs data findings |
| --- | --- | --- | --- | --- | --- |
| [mRNA-1273-P201 Day 57 analysis (BLA 125752 S3)](findings/mrna-1273-p201.md#s3-d57) | **15 / 15** (100%) | **1,242 / 1,242** (100%) | **26.33M / 26.33M** (100%) | **1,940 / 1,940** (100%), 0 unexplained<br>engine gaps: G1 (24), G6 (3) | [54 in 12 datasets](findings/define-data.md#mrna-1273-p201-s3-d57) |
| [mRNA-1273-P201 Addendum 1 (BLA 125752 S3)](findings/mrna-1273-p201.md#s3-add1) | **15 / 15** (100%) | **1,327 / 1,327** (100%)<br>31 without input | **29.65M / 29.65M** (100%) | **2,151 / 2,151** (100%), 0 unexplained<br>engine gaps: G1 (24), G6 (3) | [66 in 14 datasets](findings/define-data.md#mrna-1273-p201-s3-add1) |
| [mRNA-1273-P301 BLA interim analysis (BLA 125752 S3)](findings/mrna-1273-p301.md#s3) | **24 / 25** (96.0%)<br>1 not compared cell by cell | **2,772 / 2,882** (96.2%)<br>110 not fully compared<br>35 without input | **2,188.29M / 2,209.75M** (99.0%)<br>21.46M not fully compared | **3,620 / 3,620** (100%), 0 unexplained<br>engine gaps: G1 (50), G6 (8) | [349 in 25 datasets](findings/define-data.md#mrna-1273-p301-s3) |
| [mRNA-1273-P301 Interim analysis IA1b (27073 S5)](findings/mrna-1273-p301.md#s5) | **15 / 15** (100%)<br>4 outside the analysis set | **1,289 / 1,289** (100%)<br>374 without input | **351.38M / 351.38M** (100%) | **2,111 / 2,111** (100%), 0 unexplained<br>engine gaps: G1 (36) | [80 in 14 datasets](findings/define-data.md#mrna-1273-p301-s5) |
| [mRNA-1273-P301 Interim analysis IA1a (19745-83 S80)](findings/mrna-1273-p301.md#s80) | **14 / 14** (100%)<br>4 outside the analysis set | **1,135 / 1,135** (100%)<br>372 without input | **328.91M / 328.91M** (100%) | **1,940 / 1,940** (100%), 0 unexplained | [73 in 14 datasets](findings/define-data.md#mrna-1273-p301-s80) |
| [BNT162-01 EUA 27034 S1 (Oct 2020)](findings/bnt162-01.md#27034) | **7 / 7** (100%) | **708 / 708** (100%) | **9.12M / 9.12M** (100%) | **1,405 / 1,405** (100%), 0 unexplained<br>engine gaps: G1 (10) | [2 in 1 dataset](findings/define-data.md#bnt162-01-27034) |
| [BNT162-01 BLA 125742 S1 (Mar 2021)](findings/bnt162-01.md#125742) | **7 / 7** (100%) | **740 / 740** (100%) | **15.75M / 15.75M** (100%) | **1,441 / 1,441** (100%), 0 unexplained<br>engine gaps: G1 (8) | 0 |
| [C4591001 Safety and efficacy (BLA 125742 S1)](findings/c4591001.md#s1) | **10 / 11** (90.9%)<br>1 not compared cell by cell | **1,174 / 1,285** (91.4%)<br>111 not fully compared<br>26 without input | **583.41M / 584.29M** (99.8%)<br>0.89M not fully compared | **2,310 / 2,310** (100%), 0 unexplained<br>engine gaps: G8 (2) | [16 in 11 datasets](findings/define-data.md#c4591001-s1) |
| [C4591001 1-month cut (BLA 125742 S211)](findings/c4591001.md#s211-1mth) | **10 / 11** (90.9%)<br>1 not compared cell by cell | **1,174 / 1,285** (91.4%)<br>111 not fully compared<br>26 without input | **583.55M / 584.44M** (99.8%)<br>0.89M not fully compared | **2,259 / 2,259** (100%), 0 unexplained<br>engine gaps: G8 (2) | [12 in 11 datasets](findings/define-data.md#c4591001-s211-1mth) |
| [C4591001 EUA resubmission (EUA 27034 S135)](findings/c4591001.md#s135) | **10 / 11** (90.9%)<br>1 not compared cell by cell | **1,169 / 1,280** (91.3%)<br>111 not fully compared<br>29 without input | **582.87M / 583.75M** (99.8%)<br>0.89M not fully compared | **2,259 / 2,259** (100%), 0 unexplained<br>engine gaps: G8 (2) | [14 in 11 datasets](findings/define-data.md#c4591001-s135) |
| [C4591001 6-month cut, ages 12-15 (BLA 125742 S211)](findings/c4591001.md#s211-6mth) | **8 / 9** (88.9%)<br>1 not compared cell by cell | **846 / 949** (89.1%)<br>103 not fully compared<br>18 without input | **13.05M / 13.07M** (99.9%)<br>18,540 not fully compared | **1,675 / 1,675** (100%), 0 unexplained<br>engine gaps: G8 (2) | [9 in 7 datasets](findings/define-data.md#c4591001-s211-6mth) |
| [C4591001 Supplementary datasets (BLA 125742 S1 Supp)](findings/c4591001.md#s1-supp) | **2 / 4** (50.0%)<br>2 still differ | **385 / 645** (59.7%)<br>260 not fully compared<br>14 without input | **16.65M / 357.79M** (4.7%)<br>341.14M not fully compared | No define | No define |
| [C4591001 XB datasets (BLA 125742 S6)](findings/c4591001.md#s6) | **1 / 2** (50.0%)<br>1 not compared cell by cell | **212 / 261** (81.2%)<br>49 not fully compared<br>13 without input | **10.20M / 10.25M** (99.5%)<br>56,154 not fully compared | **569 / 569** (100%), 0 unexplained | [1 in 1 dataset](findings/define-data.md#c4591001-s6) |
| [C4591001 EUA safety and final efficacy (EUA 27034 S1)](findings/c4591001.md#s1-safety-fa-eff) | **8 / 9** (88.9%)<br>1 matches except a submitted-file defect | **834 / 835** (99.9%)<br>26 without input | **321.66M / 321.66M** (99.9%)<br>1 differ | **1,530 / 1,530** (100%), 0 unexplained | [12 in 8 datasets](findings/define-data.md#c4591001-s1-safety-fa-eff) |
| [C4591001 EUA interim efficacy analysis (EUA 27034 S1)](findings/c4591001.md#s1-ia) | **2 / 3** (66.7%)<br>1 matches except a submitted-file defect | **256 / 256** (100%)<br>6 without input | **46.01M / 46.01M** (100%) | No define | No define |

</div>

The columns mean what they mean in the table by study. A define's elements are its OID-bearing parts: datasets, variables, methods, comments, codelists, value lists, where clauses, documents and result displays.

## What this shows and what it does not

- **Agreement is not validation.** A verdict compares yamaa's output with the dataset the sponsor submitted. Agreement shows that the specification reproduces the submitted values from the released inputs. It is not regulatory validation, and it does not show that a derivation follows the analysis plan.
- **Not every match is exact.** *Matches except missing input*, *reproduced on a substitute input* and *matches except a defect of the submitted file* are reported apart from exact, with the absent input or the defect named and every differing cell counted.
- **Carried columns are not derived.** In mRNA-1273-P201 Addendum 1 (BLA 125752 S3), 5 ADIS columns and 26 ADSL columns are copied from the submitted datasets, because the input they are derived from is not in the release. Some specs also read another submitted ADaM dataset as input where the program does; the dataset's notes name it.
- **The define text was transcribed, not authored.** The labels, methods, comments and origins in the composed defines come from the received defines through the reproduced-mode layer. Define agreement shows that yamaa can express and write every element of those documents, apart from the named engine gaps; it does not show that yamaa authored that text.
- **Some inputs are not in an open format.** 40 input files are on PHMPT only as JMP tables. The published results used reviewed conversions kept in the development repository; to rerun a dataset that reads one, you supply your own conversion (steps in [`phmpt/reproduce.sh`](https://github.com/RConsortium/submissions-pilot7-synthetic-data/blob/main/phmpt/reproduce.sh)).
- **A successful run is not a review.** Every result is a draft until a person reviews it.

## Responsibilities

| Role | Responsibility |
| --- | --- |
| Human review | The project owner sets the scope and the comparison rules, decides how each kind of difference is reported (dated owner decisions), reviews and merges changes in the private development repository, and approves each publication to Pilot 7 through a pull request. Reviewers check single findings and record their assessment on the [review page](review/index.md). |
| AI drafting | AI agents (Claude) drafted the specifications, the fetch, verify and define scripts, the recorded reason for each difference and these pages, in the private development repository. Their output is a draft until a person reviews it. |
| Engine execution | yamaa, at the commit pinned in `yamaa.lock` (`ac826f0`), executes each specification on the submitted SDTM and composes each define from the specifications and the reproduced-mode layer. |
| Automated checks | Scripts compare every output with the submitted dataset or the received define and record the result; the publication gate checks every published file; CI repeats the checks on each change. |

## Tools

| Tool | Purpose |
| --- | --- |
| [yamaa](https://elong0527.github.io/yamaa/) | Resolve and execute the YAML specifications; compose Define-XML in reproduced mode. |
| `scripts/reproduce.py fetch` | Read only the needed members of the PHMPT zips over HTTP range requests and convert SAS transport files to Parquet. |
| `scripts/reproduce.py verify`, `scripts/verify_compare.py` | Run each spec, in USUBJID partitions where a dataset is large, and compare the output with the submitted dataset under the study's comparison rules. |
| `scripts/reproduce.py define`: `transcribe_define.py`, `compose_define.py`, `compare_define.py` | Transcribe the received define into the reproduced-mode layer, compose the define, and compare it element by element, attributing each difference to an engine gap or a dataset with no spec. |
| `scripts/site/check_verdicts.py` | Compare a fresh run's reports with the recorded verdicts. |
| Publication gate: `scripts/publish/check_bundle.py`, run again by Pilot 7 as `.github/scripts/check_phmpt_bundle.py` | Check every published file: an allowlist, ASCII text, the closed evidence schema, no subject identifier, and no 12-word run copied from a sponsor program or received define. |
| GitHub Actions | In the development repository: recompose every define, re-verify mRNA-1273-P201 and BNT162-01, and run the gate on each change. In Pilot 7: run the gate on each pull request. |
| GitHub Discussions | Record review assessments. |
