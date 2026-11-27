# PHMPT reproduction with yamaa

FDA released the submitted SDTM, ADaM and Define-XML of four COVID-19 vaccine trials on [phmpt.org](https://phmpt.org/) (Module 5, Full Productions). AI agents wrote a [yamaa](https://elong0527.github.io/yamaa/) specification for each submitted ADaM dataset, porting the sponsor's programs where they were released; yamaa ran each one on the submitted SDTM; and automated checks compared the output with the submitted dataset cell by cell, and the define composed from the same specifications with the received define element by element. No PHMPT file and no participant-level value is published here: the kit fetches the inputs from PHMPT, so anyone can rerun a result ([Reproduce](reproduce.md)). Every result is a draft pending human review.

## Key findings

yamaa `4ea397f`, results collected 2026-11-27. Terms are defined in the [glossary](glossary.md).

- **119 of 166 ADaM datasets reproduce the submitted dataset**, in 15 cuts of 4 studies: 99 cell for cell and 20 under the comparison rules (numbers within 1e-10, spaces ignored, cells FDA redacted to `(b)(6)` not compared; BNT162-01 is compared strictly apart from redacted cells).
- **33 more match except where the release lacks an input**: a dictionary or sponsor file that was not submitted, or SDTM values FDA redacted. Every other cell of them is reproduced, and each differing cell is counted against its recorded reason.
- **10 are reproduced on a substitute input** (mRNA-1273-P301 S5 and S80): the release lacks this cut's FACE (the release has SUPPFACE but no FACE), so the specs read the S3 release's FACE and SUPPFACE, a later snapshot of the same domain. They differ on the subjects whose data differ between the two snapshots; the study page gives how many subjects reproduce exactly.
- **2 match except a defect of the submitted file** ([C4591001 `s1-safety-fa-eff` ADMH](findings/c4591001.md#s1-safety-fa-eff), [C4591001 `s1-ia` ADC19EF](findings/c4591001.md#s1-ia)): the submitted file is malformed or was not produced by its released program, which the spec follows; the study page names each defect.
- **2 still differ**, each with a diagnosed cause still to fix: [C4591001 `s1-supp` ADCEVD](findings/c4591001.md#s1-supp), [C4591001 `s1-supp` ADFACEVD](findings/c4591001.md#s1-supp).
- **Define-XML: 25,210 of 25,210 received elements reproduced** in the 13 cuts with a define, 25,183 of them byte for byte; the other 27 differ only by named yamaa engine gaps (G1, G6, G8). **0 differences are unexplained.**
- **Still open:** the 2 datasets that still differ; 2 released folders with data but no specs (mRNA-1273-P301 `s27`, C4591001 `s9-safety-fa-eff`); the engine gaps, each tracked as a yamaa issue ([engine gaps](findings/define-gaps.md)); 40 input files PHMPT released only as JMP tables, which the kit cannot fetch ([Reproduce](reproduce.md#jmp)).

## Start here

<div class="grid cards" markdown>

-   **Results by study**

    ---

    Each cut's datasets and define, and every difference with its recorded reason.

    [mRNA-1273-P201](findings/mrna-1273-p201.md) - [mRNA-1273-P301](findings/mrna-1273-p301.md) - [BNT162-01](findings/bnt162-01.md) - [C4591001](findings/c4591001.md)

-   **Reproduce from PHMPT**

    ---

    Set up the kit, fetch the inputs from phmpt.org and rerun any cut on your machine.

    [Reproduce](reproduce.md)

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

-   **Module 5 coverage**

    ---

    All 22 studies: what PHMPT released for each and what is reproduced.

    [Coverage](coverage.md)

</div>

## Results by study

<div class="pilot-metrics" markdown="1" role="region" aria-label="Results by study" tabindex="0">

| Study | Sponsor | Cuts | Datasets with specs | Exact | Match except missing input | On a substitute input | Submitted-file defect | Open | Define-XML |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| [mRNA-1273-P201](findings/mrna-1273-p201.md) | Moderna | 2 | 30 | 30 | 0 | 0 | 0 | 0 | 4,091 / 4,091 elements in 2 defines, 0 unexplained |
| [mRNA-1273-P301](findings/mrna-1273-p301.md) | Moderna | 3 | 62 | 42 | 10 | 10 | 0 | 0 | 7,671 / 7,671 elements in 3 defines, 0 unexplained |
| [BNT162-01](findings/bnt162-01.md) | Pfizer/BioNTech | 2 | 14 | 14 | 0 | 0 | 0 | 0 | 2,846 / 2,846 elements in 2 defines, 0 unexplained |
| [C4591001](findings/c4591001.md) | Pfizer/BioNTech | 8 | 60 | 33 | 23 | 0 | 2 | 2 | 10,602 / 10,602 elements in 6 defines, 0 unexplained (2 cuts have no define) |

</div>

**Exact** counts datasets equal to the submitted dataset, strictly or under the comparison rules. **Open** counts datasets that still differ. **Define-XML** counts the received elements of datasets with a spec that are reproduced, exactly or apart from a [named engine gap](findings/define-gaps.md); *unexplained* would be any other difference.

## Results by cut

<div class="pilot-metrics" markdown="1" role="region" aria-label="Results by cut" tabindex="0">

| Study and cut | ADaM datasets reproduced | Define-XML elements reproduced | Remaining define differences |
| --- | --- | --- | --- |
| [mRNA-1273-P201 Day 57 analysis (BLA 125752 S3)](findings/mrna-1273-p201.md#s3-d57) | **15 / 15** (100%)<br>Cells: 26.33M / 26.33M | **1,940 / 1,940** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,936 (99.8%) | **0 unexplained**<br>Engine gaps: G1 (24), G6 (3) |
| [mRNA-1273-P201 Addendum 1 (BLA 125752 S3)](findings/mrna-1273-p201.md#s3-add1) | **15 / 15** (100%)<br>Cells: 29.83M / 29.83M | **2,151 / 2,151** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,148 (99.9%) | **0 unexplained**<br>Engine gaps: G1 (24), G6 (3) |
| [mRNA-1273-P301 BLA interim analysis (BLA 125752 S3)](findings/mrna-1273-p301.md#s3) | **21 / 25** (84.0%)<br>4 more match except missing input<br>Cells: 2,010.87M / 2,218.49M | **3,620 / 3,620** (100%) apart from engine gaps<br>Byte-for-byte identical: 3,616 (99.9%) | **0 unexplained**<br>Engine gaps: G1 (50), G6 (8) |
| [mRNA-1273-P301 Interim analysis IA1b (27073 S5)](findings/mrna-1273-p301.md#s5) | **11 / 19** (57.9%)<br>3 more match except missing input<br>5 reproduced on a substitute input<br>Cells: 215.77M / 1,294.91M | **2,111 / 2,111** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,110 (99.9%) | **0 unexplained**<br>Engine gaps: G1 (36) |
| [mRNA-1273-P301 Interim analysis IA1a (19745-83 S80)](findings/mrna-1273-p301.md#s80) | **10 / 18** (55.6%)<br>3 more match except missing input<br>5 reproduced on a substitute input<br>Cells: 198.47M / 1,239.25M | **1,940 / 1,940** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,940 (100%) | **0 unexplained**<br>Engine gaps: none |
| [BNT162-01 EUA 27034 S1 (Oct 2020)](findings/bnt162-01.md#27034) | **7 / 7** (100%)<br>Cells: 9.12M / 9.12M | **1,405 / 1,405** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,402 (99.8%) | **0 unexplained**<br>Engine gaps: G1 (10) |
| [BNT162-01 BLA 125742 S1 (Mar 2021)](findings/bnt162-01.md#125742) | **7 / 7** (100%)<br>Cells: 15.75M / 15.75M | **1,441 / 1,441** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,437 (99.7%) | **0 unexplained**<br>Engine gaps: G1 (11) |
| [C4591001 Safety and efficacy (BLA 125742 S1)](findings/c4591001.md#s1) | **8 / 11** (72.7%)<br>3 more match except missing input<br>Cells: 551.34M / 586.83M | **2,310 / 2,310** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,308 (99.9%) | **0 unexplained**<br>Engine gaps: G8 (2) |
| [C4591001 1-month cut (BLA 125742 S211)](findings/c4591001.md#s211-1mth) | **8 / 11** (72.7%)<br>3 more match except missing input<br>Cells: 551.09M / 586.98M | **2,259 / 2,259** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,257 (99.9%) | **0 unexplained**<br>Engine gaps: G8 (2) |
| [C4591001 EUA resubmission (EUA 27034 S135)](findings/c4591001.md#s135) | **8 / 11** (72.7%)<br>3 more match except missing input<br>Cells: 551.09M / 586.58M | **2,259 / 2,259** (100%) apart from engine gaps<br>Byte-for-byte identical: 2,257 (99.9%) | **0 unexplained**<br>Engine gaps: G8 (2) |
| [C4591001 6-month cut, ages 12-15 (BLA 125742 S211)](findings/c4591001.md#s211-6mth) | **5 / 9** (55.6%)<br>4 more match except missing input<br>Cells: 11.88M / 13.12M | **1,675 / 1,675** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,673 (99.9%) | **0 unexplained**<br>Engine gaps: G8 (2) |
| [C4591001 Supplementary datasets (BLA 125742 S1 Supp)](findings/c4591001.md#s1-supp) | **1 / 4** (25.0%)<br>1 more match except missing input<br>Cells: 6.45M / 360.90M | No define in this deliverable | - |
| [C4591001 XB datasets (BLA 125742 S6)](findings/c4591001.md#s6) | **0 / 2** (0%)<br>2 more match except missing input<br>Cells: 0 / 10.83M | **569 / 569** (100%) apart from engine gaps<br>Byte-for-byte identical: 569 (100%) | **0 unexplained**<br>Engine gaps: none |
| [C4591001 EUA safety and final efficacy (EUA 27034 S1)](findings/c4591001.md#s1-safety-fa-eff) | **2 / 9** (22.2%)<br>6 more match except missing input<br>1 more match except a defect of the submitted file<br>Cells: 74.46M / 325.12M | **1,530 / 1,530** (100%) apart from engine gaps<br>Byte-for-byte identical: 1,530 (100%) | **0 unexplained**<br>Engine gaps: G8 (1) |
| [C4591001 EUA interim efficacy analysis (EUA 27034 S1)](findings/c4591001.md#s1-ia) | **1 / 3** (33.3%)<br>1 more match except missing input<br>1 more match except a defect of the submitted file<br>Cells: 7.42M / 46.27M | No define in this deliverable | - |

</div>

**ADaM datasets reproduced** counts datasets whose yamaa output equals the submitted dataset under the comparison rules; cells count only those datasets. **Define-XML elements reproduced** counts received OID-bearing elements (datasets, variables, methods, comments, codelists, value lists, where clauses, documents, result displays) of datasets that have a spec.

## What this shows and what it does not

- **Agreement is not validation.** A verdict compares yamaa's output with the dataset the sponsor submitted. Agreement shows that the specification reproduces the submitted values from the released inputs. It is not regulatory validation, and it does not show that a derivation follows the analysis plan.
- **Not every match is exact.** *Matches except missing input*, *reproduced on a substitute input* and *matches except a defect of the submitted file* are reported apart from exact, with the absent input or the defect named and every differing cell counted.
- **Carried columns are not derived.** In mRNA-1273-P201 Addendum 1 (BLA 125752 S3), 5 ADIS columns and 26 ADSL columns are copied from the submitted datasets, because the input they are derived from is not in the release. Some specs also read another submitted ADaM dataset as input where the program does; the dataset's notes name it.
- **The define text was transcribed, not authored.** The labels, methods, comments and origins in the composed defines come from the received defines through the reproduced-mode layer. Define agreement shows that yamaa can express and write every element of those documents, apart from the named engine gaps; it does not show that yamaa authored that text.
- **Some inputs are not in an open format.** 40 input files are on PHMPT only as JMP tables. The published results used reviewed conversions kept in the development repository; to rerun a dataset that reads one, you supply your own conversion ([Reproduce](reproduce.md#jmp)).
- **A successful run is not a review.** Every result is a draft until a person reviews it.

## Responsibilities

| Role | Responsibility |
| --- | --- |
| Human review | The project owner sets the scope and the comparison rules, decides how each kind of difference is reported (dated owner decisions), reviews and merges changes in the private development repository, and approves each publication to Pilot 7 through a pull request. Reviewers check single findings and record their assessment on the [review page](review/index.md). |
| AI drafting | AI agents (Claude) drafted the specifications, the fetch, verify and define scripts, the recorded reason for each difference and these pages, in the private development repository. Their output is a draft until a person reviews it. |
| Engine execution | yamaa, at the commit pinned in `yamaa.lock` (`4ea397f`), executes each specification on the submitted SDTM and composes each define from the specifications and the reproduced-mode layer. |
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

## Scope

4 of the 22 studies on PHMPT have analysis data in Module 5, and all 4 are reproduced here. The others released documents only ([coverage](coverage.md)).
