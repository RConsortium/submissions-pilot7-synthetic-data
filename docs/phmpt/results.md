# Results tables

yamaa `ac826f0`, results collected 2026-11-27. The [overview](index.md) shows these results as charts; terms are in the [glossary](glossary.md).

## Key findings

- **Analysis set: 158 of 166 ADaM datasets, 16,119 of 17,089 columns and 5,472.17M of 7,350.32M cells**, in the 4 of the 22 PHMPT studies that released ADaM datasets. The analysis set is the part of the release that holds every input its values are derived from; it is fixed from the release, before any comparison ([analysis set](#analysis-set)). What it leaves out is listed with the absent input ([inputs outside the analysis set](findings/inputs.md)).
- **Fully reproduced: 154 of 158 datasets, 15,978 of 16,119 columns and 5,472.13M of 5,472.17M cells**, equal to the submitted values under the comparison rules (numbers within 1e-10, spaces ignored; BNT162-01 is compared strictly). 117 of these datasets hold every input; the other 37 reproduce every value that has one. Of the rest, 36,847 cells differ.
- **4 datasets in the analysis set are not counted as fully reproduced:** 2 only where the submitted file is defective ([C4591001 `s1-safety-fa-eff` ADMH](findings/c4591001.md#s1-safety-fa-eff), [C4591001 `s1-ia` ADC19EF](findings/c4591001.md#s1-ia)); 2 with a diagnosed cause still to fix ([C4591001 `s1-supp` ADCEVD](findings/c4591001.md#s1-supp), [C4591001 `s1-supp` ADFACEVD](findings/c4591001.md#s1-supp)).
- **Define-XML: 25,210 of 25,210 received elements reproduced** in the 13 deliverables with a define, 25,185 of them byte for byte; the other 25 differ only by [defects of the submitted define](glossary.md#define-defect), which yamaa does not copy (differences: 152 repeated codelist `OrderNumber`, 14 nonstandard analysis-results metadata, 8 method OID with a non-breaking space). **0 differences are unexplained.**
- **Define-XML against the data: 688 findings in 129 of the 159 datasets** in the 13 deliverables with a define, where the sponsor's received define and its submitted datasets disagree: 538 mandatory variables with missing values, 81 key sets that repeat, 40 lengths, 15 variables in only one of the two, 8 variables with values outside their codelist, 6 datasets in only one of the two. 228 more, types and labels in files FDA redacted or released as JMP tables, may come from the release and are set apart ([define vs data](findings/define-data.md)).
- **Still open:** the 2 datasets that still differ with a cause to fix; 2 released folders with SDTM but no ADaM datasets and no specs (mRNA-1273-P301 `s27`, C4591001 `s9-safety-fa-eff`); 40 input files PHMPT released only as JMP tables, which the kit cannot fetch ([`phmpt/reproduce.sh`](https://github.com/RConsortium/submissions-pilot7-synthetic-data/blob/main/phmpt/reproduce.sh) says how to supply a conversion).

## Analysis set

Results are counted on an analysis set fixed from the release before any comparison: a value is in it when the release holds every input the value is derived from and a submitted value to compare it with. Whether a value reproduces plays no part. Everything outside the set is listed with its absent input on [Inputs outside the analysis set](findings/inputs.md).

<div class="pilot-metrics" markdown="1" role="region" aria-label="Analysis set" tabindex="0">

| Level | Released | Outside the analysis set | Analysis set | Fully reproduced |
| --- | --- | --- | --- | --- |
| Studies | 22 on PHMPT | 18 released documents only, no ADaM datasets ([coverage](coverage.md)) | **4**, 3 of them with the sponsor's ADaM programs | - |
| ADaM datasets | 166 in 15 deliverables, all with a spec | 8 built from a domain the release lacks (mRNA-1273-P301 S5 and S80: ADAR, ADAR1, ADAR2, ADARP7D) | **158** (95.2%) | **154** (97.5%) |
| Columns | 17,089 | 970: 720 in those 8 datasets, 219 that read an absent input, 31 carried from the submitted dataset | **16,119** (94.3%) | **15,978** (99.1%) |
| Cells | 7,350.32M | 1,878.15M: 1,846.69M in those 8 datasets, 31.45M in columns and rows without input, 3,298 submitted cells FDA redacted to `(b)(6)` | **5,472.17M** (74.4%) | **5,472.13M** (99.9%) |

</div>

- **Studies.** Only 4 of the 22 studies released ADaM datasets in Module 5. BNT162-01 released datasets and defines but no programs; its specs follow the define and the data. The others released documents only.
- **Datasets.** Every released ADaM dataset has a spec. A dataset is outside when the release lacks the domain its rows are built from. For mRNA-1273-P301 S5 and S80 it is this cut's FACE (the release has SUPPFACE but no FACE). The spec reads another release's snapshot instead; the study page reports that result, but it is not counted here.
- **Columns.** A column is outside when its derivation reads an input the release does not hold: a licensed dictionary or a sponsor file that was not submitted, SDTM values FDA redacted, or records the released SDTM does not carry. Each absent input is recorded, with the owner's decision, in `data/differences.yaml`. The 31 carried columns are copied from the submitted dataset because their input is absent.
- **Rows and cells.** Where an absent input decides whether a row exists (the WHODRUG ATC expansion of C4591001 ADCM, records the released EUA SDTM lacks), the submitted rows with no derived counterpart are outside: 38,049 rows. The cells are those of the analysis-set columns on the analysis-set rows, less the submitted cells FDA redacted, which have no value to compare with.
- **Fully reproduced** means equal to the submitted value under the study's comparison rules, as the comparison recorded it. A column counts when all of its analysis-set cells do, so a submitted row yamaa does not write counts against every column. A dataset counts when all of its analysis-set cells do and yamaa writes no row the submitted dataset lacks, apart from rows an absent input explains. Only what the comparison accounted for counts: where the column sets differ, `scripts/verify_compare.py` compares the columns both datasets have, and a comparison on keys records the rows on one side only. 117 of the 154 hold every input. Of the other 4, 2 differ only where the submitted file is defective and 2 still differ ([key findings](#key-findings)).

## Results by study

<div class="pilot-metrics" markdown="1" role="region" aria-label="Results by study" tabindex="0">

| Study | Sponsor | Program files released | Deliverables | Datasets reproduced | Columns reproduced | Cells reproduced | Define-XML elements reproduced | Define vs data findings |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| [mRNA-1273-P201](findings/mrna-1273-p201.md) | Moderna | 61 | 2 | **30 / 30** (100%) | **2,569 / 2,569** (100%)<br>31 without input | **55.98M / 55.98M** (100%) | **4,091 / 4,091** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (48), nonstandard analysis-results metadata (6) | [120 in 26 datasets](findings/define-data.md) |
| [mRNA-1273-P301](findings/mrna-1273-p301.md) | Moderna | 100 | 3 | **54 / 54** (100%)<br>8 outside the analysis set | **5,306 / 5,306** (100%)<br>781 without input | **2,890.04M / 2,890.04M** (100%) | **7,671 / 7,671** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (86), nonstandard analysis-results metadata (8) | [502 in 53 datasets](findings/define-data.md) |
| [BNT162-01](findings/bnt162-01.md) | Pfizer/BioNTech | none | 2 | **14 / 14** (100%) | **1,448 / 1,448** (100%) | **24.87M / 24.87M** (100%) | **2,846 / 2,846** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (18) | [2 in 1 dataset](findings/define-data.md) |
| [C4591001](findings/c4591001.md) | Pfizer/BioNTech | 25 | 8 | **56 / 60** (93.3%)<br>2 match except a submitted-file defect<br>2 still differ | **6,655 / 6,796** (97.9%)<br>158 without input | **2,501.25M / 2,501.28M** (99.9%)<br>36,847 differ | **10,602 / 10,602** (100%), 0 unexplained<br>submitted-define defects: method OID with a non-breaking space (8) | [64 in 49 datasets](findings/define-data.md) |
| **All** | | 186 | 15 | **154 / 158** (97.5%)<br>2 match except a submitted-file defect<br>2 still differ<br>8 outside the analysis set | **15,978 / 16,119** (99.1%)<br>970 without input | **5,472.13M / 5,472.17M** (99.9%)<br>36,847 differ | **25,210 / 25,210** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (152), nonstandard analysis-results metadata (14), method OID with a non-breaking space (8) | [688 in 129 datasets](findings/define-data.md) |

</div>

**Datasets**, **columns** and **cells reproduced** are counted within the [analysis set](#analysis-set): those equal to the submitted values under the comparison rules, of those in the set. A dataset counts when all of its analysis-set cells do. *Without input* counts the columns outside the set. The two define columns cover every dataset of a deliverable with a define. **Define-XML elements reproduced** counts the received elements of datasets with a spec that yamaa's composed define reproduces, exactly or apart from a [defect of the submitted define](glossary.md#define-defect). **Define vs data findings** counts where the sponsor's received define and submitted datasets disagree, release artifacts apart.

## Results by cut

<div class="pilot-metrics" markdown="1" role="region" aria-label="Results by cut" tabindex="0">

| Study and cut | Datasets reproduced | Columns reproduced | Cells reproduced | Define-XML elements reproduced | Define vs data findings |
| --- | --- | --- | --- | --- | --- |
| [mRNA-1273-P201 Day 57 analysis (BLA 125752 S3)](findings/mrna-1273-p201.md#s3-d57) | **15 / 15** (100%) | **1,242 / 1,242** (100%) | **26.33M / 26.33M** (100%) | **1,940 / 1,940** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (24), nonstandard analysis-results metadata (3) | [54 in 12 datasets](findings/define-data.md#mrna-1273-p201-s3-d57) |
| [mRNA-1273-P201 Addendum 1 (BLA 125752 S3)](findings/mrna-1273-p201.md#s3-add1) | **15 / 15** (100%) | **1,327 / 1,327** (100%)<br>31 without input | **29.65M / 29.65M** (100%) | **2,151 / 2,151** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (24), nonstandard analysis-results metadata (3) | [66 in 14 datasets](findings/define-data.md#mrna-1273-p201-s3-add1) |
| [mRNA-1273-P301 BLA interim analysis (BLA 125752 S3)](findings/mrna-1273-p301.md#s3) | **25 / 25** (100%) | **2,882 / 2,882** (100%)<br>35 without input | **2,209.75M / 2,209.75M** (100%) | **3,620 / 3,620** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (50), nonstandard analysis-results metadata (8) | [349 in 25 datasets](findings/define-data.md#mrna-1273-p301-s3) |
| [mRNA-1273-P301 Interim analysis IA1b (27073 S5)](findings/mrna-1273-p301.md#s5) | **15 / 15** (100%)<br>4 outside the analysis set | **1,289 / 1,289** (100%)<br>374 without input | **351.38M / 351.38M** (100%) | **2,111 / 2,111** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (36) | [80 in 14 datasets](findings/define-data.md#mrna-1273-p301-s5) |
| [mRNA-1273-P301 Interim analysis IA1a (19745-83 S80)](findings/mrna-1273-p301.md#s80) | **14 / 14** (100%)<br>4 outside the analysis set | **1,135 / 1,135** (100%)<br>372 without input | **328.91M / 328.91M** (100%) | **1,940 / 1,940** (100%), 0 unexplained | [73 in 14 datasets](findings/define-data.md#mrna-1273-p301-s80) |
| [BNT162-01 EUA 27034 S1 (Oct 2020)](findings/bnt162-01.md#27034) | **7 / 7** (100%) | **708 / 708** (100%) | **9.12M / 9.12M** (100%) | **1,405 / 1,405** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (10) | [2 in 1 dataset](findings/define-data.md#bnt162-01-27034) |
| [BNT162-01 BLA 125742 S1 (Mar 2021)](findings/bnt162-01.md#125742) | **7 / 7** (100%) | **740 / 740** (100%) | **15.75M / 15.75M** (100%) | **1,441 / 1,441** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (8) | 0 |
| [C4591001 Safety and efficacy (BLA 125742 S1)](findings/c4591001.md#s1) | **11 / 11** (100%) | **1,285 / 1,285** (100%)<br>26 without input | **584.29M / 584.29M** (100%) | **2,310 / 2,310** (100%), 0 unexplained<br>submitted-define defects: method OID with a non-breaking space (2) | [16 in 11 datasets](findings/define-data.md#c4591001-s1) |
| [C4591001 1-month cut (BLA 125742 S211)](findings/c4591001.md#s211-1mth) | **11 / 11** (100%) | **1,285 / 1,285** (100%)<br>26 without input | **584.44M / 584.44M** (100%) | **2,259 / 2,259** (100%), 0 unexplained<br>submitted-define defects: method OID with a non-breaking space (2) | [12 in 11 datasets](findings/define-data.md#c4591001-s211-1mth) |
| [C4591001 EUA resubmission (EUA 27034 S135)](findings/c4591001.md#s135) | **11 / 11** (100%) | **1,280 / 1,280** (100%)<br>29 without input | **583.75M / 583.75M** (100%) | **2,259 / 2,259** (100%), 0 unexplained<br>submitted-define defects: method OID with a non-breaking space (2) | [14 in 11 datasets](findings/define-data.md#c4591001-s135) |
| [C4591001 6-month cut, ages 12-15 (BLA 125742 S211)](findings/c4591001.md#s211-6mth) | **9 / 9** (100%) | **949 / 949** (100%)<br>18 without input | **13.07M / 13.07M** (100%) | **1,675 / 1,675** (100%), 0 unexplained<br>submitted-define defects: method OID with a non-breaking space (2) | [9 in 7 datasets](findings/define-data.md#c4591001-s211-6mth) |
| [C4591001 Supplementary datasets (BLA 125742 S1 Supp)](findings/c4591001.md#s1-supp) | **2 / 4** (50.0%)<br>2 still differ | **505 / 645** (78.3%)<br>14 without input | **357.76M / 357.79M** (99.9%)<br>36,846 differ | No define | No define |
| [C4591001 XB datasets (BLA 125742 S6)](findings/c4591001.md#s6) | **2 / 2** (100%) | **261 / 261** (100%)<br>13 without input | **10.25M / 10.25M** (100%) | **569 / 569** (100%), 0 unexplained | [1 in 1 dataset](findings/define-data.md#c4591001-s6) |
| [C4591001 EUA safety and final efficacy (EUA 27034 S1)](findings/c4591001.md#s1-safety-fa-eff) | **8 / 9** (88.9%)<br>1 matches except a submitted-file defect | **834 / 835** (99.9%)<br>26 without input | **321.66M / 321.66M** (99.9%)<br>1 differ | **1,530 / 1,530** (100%), 0 unexplained | [12 in 8 datasets](findings/define-data.md#c4591001-s1-safety-fa-eff) |
| [C4591001 EUA interim efficacy analysis (EUA 27034 S1)](findings/c4591001.md#s1-ia) | **2 / 3** (66.7%)<br>1 matches except a submitted-file defect | **256 / 256** (100%)<br>6 without input | **46.01M / 46.01M** (100%) | No define | No define |

</div>

The columns mean what they mean in the table by study. A define's elements are its OID-bearing parts: datasets, variables, methods, comments, codelists, value lists, where clauses, documents and result displays.
