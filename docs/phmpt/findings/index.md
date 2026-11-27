# Reproduction findings

yamaa `0b46a21` - collected 2026-11-26

Two questions, answered separately for every cut that has specs:

- **ADaM datasets.** Does the yamaa spec, run on the submitted SDTM, reproduce the submitted ADaM dataset cell for cell? (`scripts/reproduce.py verify`, with `scripts/verify_compare.py`: rows keyed, numeric tolerance 1e-10, strings compared after removing spaces, and submitted cells FDA redacted to `(b)(6)` under FOIA exemption 6 not compared but counted.)
- **Define-XML.** Does the define yamaa composes from those same specs, with a reproduced-mode metadata layer, match the received define element by element? (`scripts/define/compare_define.py`)

| Study and cut | ADaM datasets reproduced | Define-XML elements reproduced | Remaining define differences |
| --- | --- | --- | --- |
| [mRNA-1273-P201 Day 57 analysis (BLA 125752 S3)](mrna-1273-p201.md#s3-d57) | **15 / 15** (100%)<br>Cells: 26.33M / 26.33M | **1,940 / 1,940** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,936 (99.8%) | **0 unexplained**<br>Engine gaps: G1 (24), G6 (3) |
| [mRNA-1273-P201 Addendum 1 (BLA 125752 S3)](mrna-1273-p201.md#s3-add1) | **15 / 15** (100%)<br>Cells: 29.83M / 29.83M | **2,151 / 2,151** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,148 (99.9%) | **0 unexplained**<br>Engine gaps: G1 (24), G6 (3) |
| [mRNA-1273-P301 BLA interim analysis (BLA 125752 S3)](mrna-1273-p301.md#s3) | **21 / 24** (87.5%)<br>3 more match except missing input<br>Cells: 2010.87M / 2192.16M | **3,457 / 3,457** (100%) apart from engine gaps<br>Byte-for-byte identical: 3,452 (99.9%)<br>163 more belong to datasets with no spec | **0 unexplained**<br>Engine gaps: G1 (50), G6 (8), G9 (1)<br>No spec yet: ADCM |
| [mRNA-1273-P301 Interim analysis IA1b (27073 S5)](mrna-1273-p301.md#s5) | **11 / 19** (57.9%)<br>8 more match except missing input<br>Cells: 215.77M / 1294.91M | **2,111 / 2,111** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,109 (99.9%) | **0 unexplained**<br>Engine gaps: G1 (36), G9 (1) |
| [mRNA-1273-P301 Interim analysis IA1a (19745-83 S80)](mrna-1273-p301.md#s80) | **10 / 18** (55.6%)<br>8 more match except missing input<br>Cells: 198.47M / 1239.25M | **1,940 / 1,940** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,939 (99.9%) | **0 unexplained**<br>Engine gaps: G9 (1) |
| [BNT162-01 EUA 27034 S1 (Oct 2020)](bnt162-01.md#27034) | **7 / 7** (100%)<br>Cells: 9.12M / 9.12M | **1,405 / 1,405** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,402 (99.8%) | **0 unexplained**<br>Engine gaps: G1 (10) |
| [BNT162-01 BLA 125742 S1 (Mar 2021)](bnt162-01.md#125742) | **7 / 7** (100%)<br>Cells: 15.75M / 15.75M | **1,441 / 1,441** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,437 (99.7%) | **0 unexplained**<br>Engine gaps: G1 (11) |
| [C4591001 Safety and efficacy (BLA 125742 S1)](c4591001.md#s1) | **8 / 11** (72.7%)<br>3 more match except missing input<br>Cells: 551.34M / 586.83M | **2,310 / 2,310** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,308 (99.9%) | **0 unexplained**<br>Engine gaps: G8 (2) |
| [C4591001 1-month cut (BLA 125742 S211)](c4591001.md#s211-1mth) | **8 / 11** (72.7%)<br>3 more match except missing input<br>Cells: 551.09M / 586.98M | **2,259 / 2,259** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,257 (99.9%) | **0 unexplained**<br>Engine gaps: G8 (2) |
| [C4591001 EUA resubmission (EUA 27034 S135)](c4591001.md#s135) | **8 / 11** (72.7%)<br>3 more match except missing input<br>Cells: 551.09M / 586.58M | **2,259 / 2,259** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,257 (99.9%) | **0 unexplained**<br>Engine gaps: G8 (2) |
| [C4591001 6-month cut, ages 12-15 (BLA 125742 S211)](c4591001.md#s211-6mth) | **5 / 9** (55.6%)<br>4 more match except missing input<br>Cells: 11.88M / 13.12M | **1,675 / 1,675** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,673 (99.9%) | **0 unexplained**<br>Engine gaps: G8 (2) |
| [C4591001 Supplementary datasets (BLA 125742 S1 Supp)](c4591001.md#s1-supp) | **1 / 4** (25.0%)<br>1 more match except missing input<br>Cells: 6.45M / 360.90M | No define in this deliverable | - |
| [C4591001 XB datasets (BLA 125742 S6)](c4591001.md#s6) | **0 / 2** (0%)<br>2 more match except missing input<br>Cells: 0 / 10.83M | **569 / 569** (100%) apart from engine gaps<br>Byte-for-byte identical: 569 (100%) | **0 unexplained**<br>Engine gaps: none |
| [C4591001 EUA safety and final efficacy (EUA 27034 S1)](c4591001.md#s1-safety-fa-eff) | **2 / 8** (25.0%)<br>3 more match except missing input<br>Cells: 74.46M / 324.02M | **1,376 / 1,376** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,376 (100%)<br>154 more belong to datasets with no spec | **0 unexplained**<br>Engine gaps: G8 (1)<br>No spec yet: ADVA |
| [C4591001 EUA interim efficacy analysis (EUA 27034 S1)](c4591001.md#s1-ia) | **0 / 3** (0%)<br>1 more match except missing input<br>Cells: 0 / 46.27M | No define in this deliverable | - |

## How the specs are organised

Each cut's spec is the executable reproduction. A later cut of a study is a **layer** over the earlier cut's spec (`parent:`) holding only what that cut changes; `scripts/specs/inherit_cut.py` writes a layer only when yamaa resolves it to the same specification as the standalone file it replaces.

| Cut | Specs | Layers over another cut | Spec lines |
| --- | ---: | ---: | ---: |
| mRNA-1273-P201 s3-d57 | 15 | 0 | 22,448 |
| mRNA-1273-P201 s3-add1 | 15 | 14 | 8,751 |
| mRNA-1273-P301 s3 | 24 | 0 | 58,103 |
| mRNA-1273-P301 s5 | 19 | 3 | 27,619 |
| mRNA-1273-P301 s80 | 18 | 10 | 14,517 |
| BNT162-01 27034 | 7 | 0 | 15,377 |
| BNT162-01 125742 | 7 | 7 | 9,595 |
| C4591001 s1 | 11 | 0 | 43,290 |
| C4591001 s211-1mth | 11 | 11 | 879 |
| C4591001 s135 | 11 | 11 | 962 |
| C4591001 s211-6mth | 9 | 8 | 3,303 |
| C4591001 s1-supp | 4 | 4 | 1,079 |
| C4591001 s6 | 2 | 1 | 785 |
| C4591001 s1-safety-fa-eff | 8 | 8 | 3,750 |
| C4591001 s1-ia | 3 | 2 | 927 |

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
