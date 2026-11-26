# PHMPT reproduction with yamaa

This section reports how far [yamaa](https://elong0527.github.io/yamaa/) specifications reproduce the ADaM datasets and Define-XML documents that sponsors submitted for COVID-19 vaccine trials and that FDA released on [phmpt.org](https://phmpt.org/) (Module 5, Full Productions). Every result is a draft pending human review.

This section publishes the specifications, the scripts and the results only. No PHMPT file (dataset, define, program or document) and no participant-level value is published; the scripts fetch the inputs from PHMPT, so anyone can rerun a result ([`phmpt/`](https://github.com/RConsortium/submissions-pilot7-synthetic-data/tree/main/phmpt), [review guide](review/index.md)).

## Start here

<div class="grid cards" markdown>

-   **Findings**

    ---

    ADaM and Define-XML agreement for every cut, dataset by dataset and element class by element class.

    [Reproduction findings](findings/index.md)

-   **Review guide**

    ---

    Check one finding's evidence, rerun it from PHMPT, and submit your assessment on GitHub.

    [Review a finding](review/index.md)

-   **Define-XML engine gaps**

    ---

    What yamaa cannot declare yet, with counts per cut and the yamaa issue for each.

    [Engine gaps](findings/define-gaps.md)

-   **Module 5 coverage**

    ---

    All 22 studies: what PHMPT released for each and what is reproduced.

    [Coverage](coverage.md)

</div>

## Results

<div class="pilot-metrics" markdown="1" role="region" aria-label="Reproduction metrics" tabindex="0">

| Study and cut | ADaM datasets reproduced | Define-XML elements reproduced | Remaining define differences |
| --- | --- | --- | --- |
| [mRNA-1273-P201 Day 57 analysis (BLA 125752 S3)](findings/mrna-1273-p201.md#s3-d57) | **15 / 15** (100%)<br>Cells: 26.33M / 26.33M | **1,940 / 1,940** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,936 (99.8%) | **0 unexplained**<br>Engine gaps: G1 (24), G6 (3) |
| [mRNA-1273-P201 Addendum 1 (BLA 125752 S3)](findings/mrna-1273-p201.md#s3-add1) | **15 / 15** (100%)<br>Cells: 29.83M / 29.83M | **2,151 / 2,151** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,148 (99.9%) | **0 unexplained**<br>Engine gaps: G1 (24), G6 (3) |
| [mRNA-1273-P301 BLA interim analysis (BLA 125752 S3)](findings/mrna-1273-p301.md#s3) | **21 / 24** (87.5%)<br>3 more match except missing input<br>Cells: 2010.87M / 2192.16M | **3,457 / 3,457** (100%) apart from engine gaps<br>Byte-for-byte identical: 3,452 (99.9%)<br>163 more belong to datasets with no spec | **0 unexplained**<br>Engine gaps: G1 (50), G6 (8), G9 (1)<br>No spec yet: ADCM |
| [mRNA-1273-P301 Interim analysis IA1b (27073 S5)](findings/mrna-1273-p301.md#s5) | **11 / 19** (57.9%)<br>8 more match except missing input<br>Cells: 215.77M / 1294.91M | **2,111 / 2,111** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,109 (99.9%) | **0 unexplained**<br>Engine gaps: G1 (36), G9 (1) |
| [mRNA-1273-P301 Interim analysis IA1a (19745-83 S80)](findings/mrna-1273-p301.md#s80) | **10 / 18** (55.6%)<br>8 more match except missing input<br>Cells: 198.47M / 1239.25M | **1,940 / 1,940** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,939 (99.9%) | **0 unexplained**<br>Engine gaps: G9 (1) |
| [BNT162-01 EUA 27034 S1 (Oct 2020)](findings/bnt162-01.md#27034) | **7 / 7** (100%)<br>Cells: 9.12M / 9.12M | **1,405 / 1,405** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,402 (99.8%) | **0 unexplained**<br>Engine gaps: G1 (10) |
| [BNT162-01 BLA 125742 S1 (Mar 2021)](findings/bnt162-01.md#125742) | **7 / 7** (100%)<br>Cells: 15.75M / 15.75M | **1,441 / 1,441** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,437 (99.7%) | **0 unexplained**<br>Engine gaps: G1 (11) |
| [C4591001 Safety and efficacy (BLA 125742 S1)](findings/c4591001.md#s1) | **8 / 11** (72.7%)<br>3 more match except missing input<br>Cells: 551.34M / 586.83M | **2,310 / 2,310** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,308 (99.9%) | **0 unexplained**<br>Engine gaps: G8 (2) |
| [C4591001 1-month cut (BLA 125742 S211)](findings/c4591001.md#s211-1mth) | **8 / 11** (72.7%)<br>3 more match except missing input<br>Cells: 551.09M / 586.98M | **2,259 / 2,259** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,257 (99.9%) | **0 unexplained**<br>Engine gaps: G8 (2) |
| [C4591001 EUA resubmission (EUA 27034 S135)](findings/c4591001.md#s135) | **8 / 11** (72.7%)<br>3 more match except missing input<br>Cells: 551.09M / 586.58M | **2,259 / 2,259** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,257 (99.9%) | **0 unexplained**<br>Engine gaps: G8 (2) |
| [C4591001 6-month cut, ages 12-15 (BLA 125742 S211)](findings/c4591001.md#s211-6mth) | **5 / 9** (55.6%)<br>4 more match except missing input<br>Cells: 11.88M / 13.12M | **1,675 / 1,675** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,673 (99.9%) | **0 unexplained**<br>Engine gaps: G8 (2) |
| [C4591001 Supplementary datasets (BLA 125742 S1 Supp)](findings/c4591001.md#s1-supp) | **1 / 4** (25.0%)<br>1 more match except missing input<br>Cells: 6.45M / 360.90M | No define in this deliverable | - |
| [C4591001 XB datasets (BLA 125742 S6)](findings/c4591001.md#s6) | **0 / 2** (0%)<br>2 more match except missing input<br>Cells: 0 / 10.83M | **569 / 569** (100%) apart from engine gaps<br>Byte-for-byte identical: 569 (100%) | **0 unexplained**<br>Engine gaps: none |
| [C4591001 EUA safety and final efficacy (EUA 27034 S1)](findings/c4591001.md#s1-safety-fa-eff) | **2 / 8** (25.0%)<br>3 more match except missing input<br>Cells: 74.46M / 324.02M | **1,376 / 1,376** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,376 (100%)<br>154 more belong to datasets with no spec | **0 unexplained**<br>Engine gaps: G8 (1)<br>No spec yet: ADVA |
| [C4591001 EUA interim efficacy analysis (EUA 27034 S1)](findings/c4591001.md#s1-ia) | **0 / 3** (0%)<br>1 more match except missing input<br>Cells: 0 / 46.27M | No define in this deliverable | - |

</div>

yamaa `0b46a21`, collected 2026-11-26. **ADaM datasets reproduced** counts datasets whose yamaa output equals the submitted dataset under the comparison rules; cells count only those datasets. **Define-XML elements reproduced** counts received OID-bearing elements (datasets, variables, methods, comments, codelists, value lists, where clauses, documents, result displays) of datasets that have a spec, reproduced exactly or except for a [named engine gap](findings/define-gaps.md); any other difference would be *unexplained*.

## Scope

4 of the 22 studies on PHMPT have analysis data in Module 5, and all 4 are reproduced here. The others released documents only ([coverage](coverage.md)).
