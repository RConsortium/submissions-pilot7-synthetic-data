# Reproduction findings

yamaa `ac826f0` - collected 2026-11-27 - terms: [glossary](../glossary.md)

Two questions, answered separately for every cut that has specs:

- **ADaM datasets.** Does the yamaa spec, run on the submitted SDTM, reproduce the submitted ADaM dataset cell for cell? (`scripts/reproduce.py verify`, with `scripts/verify_compare.py`: rows keyed, numeric tolerance 1e-10, strings compared after removing spaces, and submitted cells FDA redacted to `(b)(6)` under FOIA exemption 6 not compared but counted.)
- **Define-XML.** Does the define yamaa composes from those same specs, with a reproduced-mode metadata layer, match the received define element by element? (`scripts/define/compare_define.py`)

| Study and cut | Datasets reproduced | Columns reproduced | Cells reproduced | Define-XML elements reproduced | Define vs data findings |
| --- | --- | --- | --- | --- | --- |
| [mRNA-1273-P201 Day 57 analysis (BLA 125752 S3)](mrna-1273-p201.md#s3-d57) | **15 / 15** (100%) | **1,242 / 1,242** (100%) | **26.33M / 26.33M** (100%) | **1,940 / 1,940** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (24), nonstandard analysis-results metadata (3) | [54 in 12 datasets](define-data.md#mrna-1273-p201-s3-d57) |
| [mRNA-1273-P201 Addendum 1 (BLA 125752 S3)](mrna-1273-p201.md#s3-add1) | **15 / 15** (100%) | **1,327 / 1,327** (100%)<br>31 without input | **29.65M / 29.65M** (100%) | **2,151 / 2,151** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (24), nonstandard analysis-results metadata (3) | [66 in 14 datasets](define-data.md#mrna-1273-p201-s3-add1) |
| [mRNA-1273-P301 BLA interim analysis (BLA 125752 S3)](mrna-1273-p301.md#s3) | **25 / 25** (100%) | **2,882 / 2,882** (100%)<br>35 without input | **2,209.75M / 2,209.75M** (100%) | **3,620 / 3,620** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (50), nonstandard analysis-results metadata (8) | [349 in 25 datasets](define-data.md#mrna-1273-p301-s3) |
| [mRNA-1273-P301 Interim analysis IA1b (27073 S5)](mrna-1273-p301.md#s5) | **15 / 15** (100%)<br>4 outside the analysis set | **1,289 / 1,289** (100%)<br>374 without input | **351.38M / 351.38M** (100%) | **2,111 / 2,111** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (36) | [80 in 14 datasets](define-data.md#mrna-1273-p301-s5) |
| [mRNA-1273-P301 Interim analysis IA1a (19745-83 S80)](mrna-1273-p301.md#s80) | **14 / 14** (100%)<br>4 outside the analysis set | **1,135 / 1,135** (100%)<br>372 without input | **328.91M / 328.91M** (100%) | **1,940 / 1,940** (100%), 0 unexplained | [73 in 14 datasets](define-data.md#mrna-1273-p301-s80) |
| [BNT162-01 EUA 27034 S1 (Oct 2020)](bnt162-01.md#27034) | **7 / 7** (100%) | **708 / 708** (100%) | **9.12M / 9.12M** (100%) | **1,405 / 1,405** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (10) | [2 in 1 dataset](define-data.md#bnt162-01-27034) |
| [BNT162-01 BLA 125742 S1 (Mar 2021)](bnt162-01.md#125742) | **7 / 7** (100%) | **740 / 740** (100%) | **15.75M / 15.75M** (100%) | **1,441 / 1,441** (100%), 0 unexplained<br>submitted-define defects: repeated codelist `OrderNumber` (8) | 0 |
| [C4591001 Safety and efficacy (BLA 125742 S1)](c4591001.md#s1) | **11 / 11** (100%) | **1,285 / 1,285** (100%)<br>26 without input | **584.29M / 584.29M** (100%) | **2,310 / 2,310** (100%), 0 unexplained<br>submitted-define defects: method OID with a non-breaking space (2) | [16 in 11 datasets](define-data.md#c4591001-s1) |
| [C4591001 1-month cut (BLA 125742 S211)](c4591001.md#s211-1mth) | **11 / 11** (100%) | **1,285 / 1,285** (100%)<br>26 without input | **584.44M / 584.44M** (100%) | **2,259 / 2,259** (100%), 0 unexplained<br>submitted-define defects: method OID with a non-breaking space (2) | [12 in 11 datasets](define-data.md#c4591001-s211-1mth) |
| [C4591001 EUA resubmission (EUA 27034 S135)](c4591001.md#s135) | **11 / 11** (100%) | **1,280 / 1,280** (100%)<br>29 without input | **583.75M / 583.75M** (100%) | **2,259 / 2,259** (100%), 0 unexplained<br>submitted-define defects: method OID with a non-breaking space (2) | [14 in 11 datasets](define-data.md#c4591001-s135) |
| [C4591001 6-month cut, ages 12-15 (BLA 125742 S211)](c4591001.md#s211-6mth) | **9 / 9** (100%) | **949 / 949** (100%)<br>18 without input | **13.07M / 13.07M** (100%) | **1,675 / 1,675** (100%), 0 unexplained<br>submitted-define defects: method OID with a non-breaking space (2) | [9 in 7 datasets](define-data.md#c4591001-s211-6mth) |
| [C4591001 Supplementary datasets (BLA 125742 S1 Supp)](c4591001.md#s1-supp) | **2 / 4** (50.0%)<br>2 still differ | **505 / 645** (78.3%)<br>14 without input | **357.76M / 357.79M** (99.9%)<br>36,846 differ | No define | No define |
| [C4591001 XB datasets (BLA 125742 S6)](c4591001.md#s6) | **2 / 2** (100%) | **261 / 261** (100%)<br>13 without input | **10.25M / 10.25M** (100%) | **569 / 569** (100%), 0 unexplained | [1 in 1 dataset](define-data.md#c4591001-s6) |
| [C4591001 EUA safety and final efficacy (EUA 27034 S1)](c4591001.md#s1-safety-fa-eff) | **8 / 9** (88.9%)<br>1 matches except a submitted-file defect | **834 / 835** (99.9%)<br>26 without input | **321.66M / 321.66M** (99.9%)<br>1 differ | **1,530 / 1,530** (100%), 0 unexplained | [12 in 8 datasets](define-data.md#c4591001-s1-safety-fa-eff) |
| [C4591001 EUA interim efficacy analysis (EUA 27034 S1)](c4591001.md#s1-ia) | **2 / 3** (66.7%)<br>1 matches except a submitted-file defect | **256 / 256** (100%)<br>6 without input | **46.01M / 46.01M** (100%) | No define | No define |

## Where the program and the submitted file disagree

Each released program was ported as written. In these datasets the program's text and the submitted file disagree, which means the file was not produced by the program as released, or the program's code contradicts its own stated intent (the spec follows the intent):

| Study and cut | Dataset | What disagrees |
| --- | --- | --- |
| mRNA-1273-P301 BLA interim analysis (BLA 125752 S3) | ADSLSF | a11adslsf.sas keeps one record per screen-failure date (by usubjid subjid dsstdtc; if last.dsstdtc), so the two subjects who failed screening on two dates get two records each, while the program's own note says the last reason is kept. The submitted ADSLSF has one record for each, the later one; the spec follows the note. |

## How the specs are organised

Each cut's spec is the executable reproduction. A later cut of a study is a **layer** over the earlier cut's spec (`parent:`) holding only what that cut changes; `scripts/specs/inherit_cut.py` writes a layer only when yamaa resolves it to the same specification as the standalone file it replaces.

| Cut | Specs | Layers over another cut | Spec lines |
| --- | ---: | ---: | ---: |
| mRNA-1273-P201 s3-d57 | 15 | 0 | 22,448 |
| mRNA-1273-P201 s3-add1 | 15 | 14 | 8,751 |
| mRNA-1273-P301 s3 | 25 | 0 | 61,338 |
| mRNA-1273-P301 s5 | 19 | 3 | 27,620 |
| mRNA-1273-P301 s80 | 18 | 10 | 14,517 |
| BNT162-01 27034 | 7 | 0 | 15,377 |
| BNT162-01 125742 | 7 | 7 | 9,595 |
| C4591001 s1 | 11 | 0 | 43,290 |
| C4591001 s211-1mth | 11 | 11 | 879 |
| C4591001 s135 | 11 | 11 | 962 |
| C4591001 s211-6mth | 9 | 8 | 3,303 |
| C4591001 s1-supp | 4 | 4 | 1,053 |
| C4591001 s6 | 2 | 1 | 785 |
| C4591001 s1-safety-fa-eff | 9 | 9 | 5,042 |
| C4591001 s1-ia | 3 | 2 | 952 |

Three tiers of inheritance keep each statement in one place:

1. **Study base** (`<study>/spec/yamaa/base/`): the project settings, submission metadata and the columns every dataset of the study carries; every spec's chain starts there.
2. **Earlier cut** (`parent: ../../../<cut>/spec/yamaa/<dataset>.yaml`): a later cut's spec states only what the cut changes.
3. **Define layer** (`<cut>/spec/define/`): reproduced-mode metadata over the cut's spec; a later cut whose wrapper or codelists are identical points to the earlier cut's file.

A yamaa layer can add or replace members but cannot remove a column or intermediate its parent declares, so a later spec that drops one stays standalone over the study base. These are recorded, with the reason, in `studies.yaml` (`standalone`):

| Cut | Dataset | Why it is not a layer over the earlier cut |
| --- | --- | --- |
| mRNA-1273-P201 s3-add1 | ADARP7D | Rebuilt for the addendum from FACE/SUPPFACE and SUPPVS instead of EX: 33 Day-57 columns and 3 intermediates are gone. |
| mRNA-1273-P301 s80 | ADAE | 57 S5 columns (RTPCRBL, the _ADURN helpers) and the six HO_ICU intermediates are not in S80. |
| mRNA-1273-P301 s80 | ADAR1 | ADAR1 keeps the LOCAL rows of this cut's ADAR (helper/adar_all.yaml, a layer over adar.yaml), as in S5. |
| mRNA-1273-P301 s80 | ADAR2 | ADAR2 keeps the SYSTEMIC rows of this cut's ADAR (helper/adar_all.yaml, a layer over adar.yaml), as in S5. |
| mRNA-1273-P301 s80 | ADCM | 36 S5 columns (RTPCRBL, the _AENDT imputation helpers) and the SUPP_P intermediate are not in S80. |
| mRNA-1273-P301 s80 | ADEFF | S5 carries RTPCRBL and the MB_D intermediate; S80 has neither. |
| mRNA-1273-P301 s80 | ADIS | 10 S5 columns (RTPCRBL, the _CRITnFL_RAW helpers) are not in S80. |
| mRNA-1273-P301 s80 | ADMB | 13 S5 columns (RTPCRBL, the _AVISIT helpers) are not in S80. |
| mRNA-1273-P301 s80 | ADRISK | S5 carries RTPCRBL, three helper columns and the SC_LAST and SUPP_P intermediates; S80 has none of them. |
| C4591001 s211-6mth | ADXB | The 6-month program reads MB WGSCLINE records instead of XB and drops four of S6's flags with their intermediates (no 1-month ADXB). |
| C4591001 s1-ia | ADC19EF | adc19ef-ia.sas ends by dropping parameters whose rows the earlier steps read; helper/adc19ef_all.yaml is the layer over the EUA spec, and this spec only applies that final filter |

**Helper specs.** Where the sponsor's program builds an intermediate table in several passes, a helper spec in `spec/yamaa/helper/` builds it and the dataset spec reads its output through a schema link (`<work-dir>/<file>`, `schema:`); `scripts/reproduce.py verify` runs the helper first. C4591001 ADSYMPT reads the visit-collapse walk (`adsympt_visits.yaml`, a calculated-history group over its own rows, and `adsympt_vismap.yaml`), and C4591001 ADSL reads the infection-evidence events behind EV1MD2FL (`adsl_ev1.yaml`). A later cut's spec that inherits the dataset spec inherits its helpers too: they run on that cut's data.


Each cut's `spec/define/` folder holds the define layer: one reproduced-mode wrapper per dataset whose `parent` is the cut's spec, stating only the metadata the received define declares differently or that the spec does not carry (codelists, value-level metadata, received OIDs and orders, define-only columns). `scripts/define/transcribe_define.py` writes it from the received define; `scripts/define/compose_define.py` composes the cut's `define-adam-yamaa.xml`.
