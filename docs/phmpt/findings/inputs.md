# Inputs outside the analysis set

The [analysis set](../results.md#analysis-set) holds the part of the release that has every input its values are derived from. This page lists what it leaves out and why: datasets built from a domain the release lacks, columns and rows that read an absent input, columns carried from the submitted dataset, and submitted cells FDA redacted. It then lists the problems of the submitted files themselves, which stay in the analysis set. Each absent input is recorded, with the owner's decision and the reason, in `data/differences.yaml`; terms: [glossary](../glossary.md).

## Summary

| Outside the analysis set | Datasets | Columns | Rows | Cells |
| --- | ---: | ---: | ---: | ---: |
| [Datasets built from a domain the release lacks](#domain) | 8 | 720 | 20,000,048 | 1,846,688,954 |
| [Columns that read an absent input](#absent) | 36 | 219 | 0 | 27,098,729 |
| [Columns carried from the submitted dataset](#carried) | 2 | 31 | 0 | 181,805 |
| [Rows an absent input decides](#absent) | 7 | 0 | 38,049 | 4,174,070 |
| [Submitted cells FDA redacted](#redacted) | 13 | 0 | 0 | 3,298 |

A dataset can appear in more than one row. Together they leave 970 of 17,089 columns and 1,878.15M of 7,350.32M cells outside the analysis set.

## Datasets built from a domain the release lacks {#domain}

The release lacks the domain these datasets' rows are built from, so the spec reads another release's snapshot of it. The study page reports how far that reproduces; none of it is counted in the analysis set.

| Study and cut | Dataset | Rows x columns | Absent input | Read instead | Subjects reproduced exactly |
| --- | --- | --- | --- | --- | --- |
| [mRNA-1273-P301 Interim analysis IA1b (27073 S5)](mrna-1273-p301.md#s5) | ADAR | 4,975,618 x 93 | this cut's FACE (the release has SUPPFACE but no FACE) | the S3 release's FACE and SUPPFACE, a later snapshot of the same domain | 26,764 of 30,344 (88.2%) |
| [mRNA-1273-P301 Interim analysis IA1b (27073 S5)](mrna-1273-p301.md#s5) | ADAR1 | 1,811,834 x 93 | this cut's FACE (the release has SUPPFACE but no FACE) | the S3 release's FACE and SUPPFACE, a later snapshot of the same domain | - |
| [mRNA-1273-P301 Interim analysis IA1b (27073 S5)](mrna-1273-p301.md#s5) | ADAR2 | 3,163,784 x 93 | this cut's FACE (the release has SUPPFACE but no FACE) | the S3 release's FACE and SUPPFACE, a later snapshot of the same domain | - |
| [mRNA-1273-P301 Interim analysis IA1b (27073 S5)](mrna-1273-p301.md#s5) | ADARP7D | 176,322 x 83 | this cut's FACE (the release has SUPPFACE but no FACE) | the S3 release's FACE and SUPPFACE, a later snapshot of the same domain | 3,536 of 6,306 (56.1%) |
| [mRNA-1273-P301 Interim analysis IA1a (19745-83 S80)](mrna-1273-p301.md#s80) | ADAR | 4,852,255 x 92 | this cut's FACE (the release has SUPPFACE but no FACE) | the S3 release's FACE and SUPPFACE, a later snapshot of the same domain | 25,339 of 30,341 (83.5%) |
| [mRNA-1273-P301 Interim analysis IA1a (19745-83 S80)](mrna-1273-p301.md#s80) | ADAR1 | 1,766,943 x 92 | this cut's FACE (the release has SUPPFACE but no FACE) | the S3 release's FACE and SUPPFACE, a later snapshot of the same domain | - |
| [mRNA-1273-P301 Interim analysis IA1a (19745-83 S80)](mrna-1273-p301.md#s80) | ADAR2 | 3,085,312 x 92 | this cut's FACE (the release has SUPPFACE but no FACE) | the S3 release's FACE and SUPPFACE, a later snapshot of the same domain | - |
| [mRNA-1273-P301 Interim analysis IA1a (19745-83 S80)](mrna-1273-p301.md#s80) | ADARP7D | 167,980 x 82 | this cut's FACE (the release has SUPPFACE but no FACE) | the S3 release's FACE and SUPPFACE, a later snapshot of the same domain | 3,317 of 6,193 (53.6%) |

## Columns and rows without input {#absent}

Each row names the absent input and what of the dataset it leaves out: the columns whose derivation reads it and, where it decides whether a row exists, the submitted rows with no derived counterpart. The rest of the dataset is in the analysis set.

### mRNA-1273-P301

| Cut | Dataset | Absent input | Columns outside | Rows outside |
| --- | --- | --- | --- | --- |
| [BLA interim analysis (BLA 125752 S3)](mrna-1273-p301.md#s3) | ADCM | CM variables the released S3 CM (a JMP conversion with 11 of its 24 variables) drops: CMSEQ, CMCAT, CMDECOD, CMINDC, CMCLAS, CMDOSE, CMDOSU, CMDOSFRQ, CMROUTE; the sponsor file import.pain_drugcode, not submitted; and the CMSTDTC values of 11 rows, redacted to (b)(6) | `ASTDTF`, `ATCLEV1T`, `ATCLEV2T`, `ATCLEV3T`, `ATCLEV4T`, `CMCAT`, `CMDECOD`, `CMDECOD1`, `CMDECOD2`, `CMDECOD3`, `CMDOSE`, `CMDOSFRQ`, `CMDOSU`, `CMFOTHSP`, `CMINDC`, `CMMOI1FL`, `CMMOI2FL`, `CMMOI3FL`, `CMPROTCD`, `CMROTHSP`, `CMROUTE`, `CMSEQ`, `CMSOLFL`, `CMTRTO1`, `CMUOTHSP` | - |
| [BLA interim analysis (BLA 125752 S3)](mrna-1273-p301.md#s3) | ADEX | the unredacted SUPPEC reason text, and the record behind one '.' value | `NDOSRSP` | - |
| [BLA interim analysis (BLA 125752 S3)](mrna-1273-p301.md#s3) | ADSL | the sponsor's files here.ccias_unblinded, here.random_list and here.additional_subcohort_unblinded, not submitted; the unredacted DS DSTERM of nine discontinuation reasons | `CCIASFL`, `DCSREASP`, `DCT01RSP`, `PPSIEREA`, `PPSIFL`, `RANDIGFL` | - |
| [BLA interim analysis (BLA 125752 S3)](mrna-1273-p301.md#s3) | ADVS | the sponsor's file import.vsgrade4, not submitted | `ATOXGRH`, `ATOXGRHN`, `SHIFT2` | - |
| [Interim analysis IA1b (27073 S5)](mrna-1273-p301.md#s5) | ADCM | the CMSTDTC / CMENDTC values of these rows, redacted to (b)(6) | `ASTDTF` | - |
| [Interim analysis IA1b (27073 S5)](mrna-1273-p301.md#s5) | ADRISK | the unredacted free text (SDTM and ADaM redacted differently) | `OTHSPY` | - |
| [Interim analysis IA1b (27073 S5)](mrna-1273-p301.md#s5) | ADSL | this cut's FACE (the release has SUPPFACE but no FACE); the unredacted DS DSTERM of a few discontinuation reasons | `DCSREASP`, `DCTREASP`, `SAR1ERS`, `SAR1FL`, `SAR2ERS`, `SAR2FL`, `SARAFL` | - |
| [Interim analysis IA1b (27073 S5)](mrna-1273-p301.md#s5) | ADVS | the sponsor's file import.vsgrade4, not submitted | `ATOXGRH`, `ATOXGRHN`, `SHIFT2` | - |
| [Interim analysis IA1a (19745-83 S80)](mrna-1273-p301.md#s80) | ADCM | the CMSTDTC / CMENDTC values of these rows, redacted to (b)(6) | `AENDTF`, `ASTDTF`, `FUPFL`, `ONTRTFL` | - |
| [Interim analysis IA1a (19745-83 S80)](mrna-1273-p301.md#s80) | ADRISK | the unredacted free text (SDTM and ADaM redacted differently) | `OTHSPY` | - |
| [Interim analysis IA1a (19745-83 S80)](mrna-1273-p301.md#s80) | ADSL | this cut's FACE (the release has SUPPFACE but no FACE); the unredacted DS DSTERM of a few discontinuation reasons | `DCTREASP`, `SAR1ERS`, `SAR1FL`, `SAR2ERS`, `SAR2FL`, `SARAFL` | - |
| [Interim analysis IA1a (19745-83 S80)](mrna-1273-p301.md#s80) | ADVS | the sponsor's file import.vsgrade4, not submitted | `ATOXGRH`, `ATOXGRHN`, `SHIFT2` | - |

### C4591001

| Cut | Dataset | Absent input | Columns outside | Rows outside |
| --- | --- | --- | --- | --- |
| [Safety and efficacy (BLA 125742 S1)](c4591001.md#s1) | ADCM | WHO Drug dictionary (WHODRUG DDE v202003), licensed, not submitted | `ATC1CD`, `ATC1T`, `ATC2CD`, `ATC2T`, `ATC3CD`, `ATC3T`, `ATC4CD`, `ATC4T`, `ATC5CD`, `ATC5T`, `DRGNAME1`, `DRUGNAME` | 11,940 of 19,925 |
| [Safety and efficacy (BLA 125742 S1)](c4591001.md#s1) | ADMH | the MHSTDTC / MHENDTC values of these rows, redacted to (b)(6) | `AENDTF`, `ASTDTF` | - |
| [Safety and efficacy (BLA 125742 S1)](c4591001.md#s1) | ADSL | DM.BRTHDTC, redacted to (b)(6) for every subject | `AGEGR1`, `AGEGR1N`, `AGEGR3`, `AGEGR3N`, `AGEGR4`, `AGEGR4N`, `AGETGR3`, `AGETGR3N`, `AGETR01`, `AGETR03`, `BRTHDTF`, `OBESEFL` | - |
| [1-month cut (BLA 125742 S211)](c4591001.md#s211-1mth) | ADCM | WHO Drug dictionary (WHODRUG DDE v202003), licensed, not submitted | `ATC1CD`, `ATC1T`, `ATC2CD`, `ATC2T`, `ATC3CD`, `ATC3T`, `ATC4CD`, `ATC4T`, `ATC5CD`, `ATC5T`, `DRGNAME1`, `DRUGNAME` | 11,940 of 19,925 |
| [1-month cut (BLA 125742 S211)](c4591001.md#s211-1mth) | ADMH | the MHSTDTC / MHENDTC values of these rows, redacted to (b)(6) | `AENDTF`, `ASTDTF` | - |
| [1-month cut (BLA 125742 S211)](c4591001.md#s211-1mth) | ADSL | DM.BRTHDTC, redacted to (b)(6) for every subject | `AGEGR1`, `AGEGR1N`, `AGEGR3`, `AGEGR3N`, `AGEGR4`, `AGEGR4N`, `AGETGR3`, `AGETGR3N`, `AGETR01`, `AGETR03`, `BRTHDTF`, `OBESEFL` | - |
| [EUA resubmission (EUA 27034 S135)](c4591001.md#s135) | ADCM | WHO Drug dictionary (WHODRUG DDE v202003), licensed, not submitted | `ATC1CD`, `ATC1T`, `ATC2CD`, `ATC2T`, `ATC3CD`, `ATC3T`, `ATC4CD`, `ATC4T`, `ATC5CD`, `ATC5T`, `DRGNAME1`, `DRUGNAME` | 11,940 of 19,925 |
| [EUA resubmission (EUA 27034 S135)](c4591001.md#s135) | ADMH | the MHSTDTC / MHENDTC values of these rows, redacted to (b)(6) | `ADURN`, `AENDTF`, `ASTDTF` | - |
| [EUA resubmission (EUA 27034 S135)](c4591001.md#s135) | ADSL | DM.BRTHDTC, redacted for every subject; one subject's VS height and BMI, redacted in S135 | `AGEGR1`, `AGEGR1N`, `AGEGR3`, `AGEGR3N`, `AGEGR4`, `AGEGR4N`, `AGETGR3`, `AGETGR3N`, `AGETR01`, `AGETR03`, `BMICAT`, `BMICATN`, `BRTHDTF`, `OBESEFL` | - |
| [6-month cut, ages 12-15 (BLA 125742 S211)](c4591001.md#s211-6mth) | ADAE | the unredacted SUPPAE AERELTXT of one event, redacted to (b)(6) in the 6-month SDTM | `DATACHGC` | - |
| [6-month cut, ages 12-15 (BLA 125742 S211)](c4591001.md#s211-6mth) | ADCM | WHO Drug dictionary (WHODRUG DDE v202003), licensed, not submitted | `ATC1CD`, `ATC1T`, `ATC2CD`, `ATC2T`, `ATC3CD`, `ATC3T`, `ATC4CD`, `ATC4T`, `ATC5CD`, `ATC5T`, `DRUGNAME` | 232 of 412 |
| [6-month cut, ages 12-15 (BLA 125742 S211)](c4591001.md#s211-6mth) | ADMH | the MHSTDTC / MHENDTC values of these rows, redacted to (b)(6) | `AENDTF`, `ASTDTF` | - |
| [6-month cut, ages 12-15 (BLA 125742 S211)](c4591001.md#s211-6mth) | ADSL | DM.BRTHDTC, redacted to (b)(6) for every subject | `AGETGR3`, `AGETGR3N`, `AGETR03`, `OBESEFL` | - |
| [Supplementary datasets (BLA 125742 S1 Supp)](c4591001.md#s1-supp) | ADCEVD | the EX doses the supplement's ADaM read for Phase 1 placebo, which differ from the supplement's released EX | `EXDOSE` | - |
| [Supplementary datasets (BLA 125742 S1 Supp)](c4591001.md#s1-supp) | ADFACEVD | the EX doses the supplement's ADaM read for Phase 1 placebo, which differ from the supplement's released EX | `EXDOSE` | - |
| [Supplementary datasets (BLA 125742 S1 Supp)](c4591001.md#s1-supp) | ADSL | DM.BRTHDTC, redacted to (b)(6) for every subject | `AGEGR1`, `AGEGR1N`, `AGEGR3`, `AGEGR3N`, `AGEGR4`, `AGEGR4N`, `AGETGR3`, `AGETGR3N`, `AGETR01`, `AGETR03`, `BRTHDTF`, `OBESEFL` | - |
| [XB datasets (BLA 125742 S6)](c4591001.md#s6) | ADSL | DM.BRTHDTC, redacted to (b)(6) for every subject | `AGEGR1`, `AGEGR1N`, `AGEGR3`, `AGEGR3N`, `AGEGR4`, `AGEGR4N`, `AGETGR3`, `AGETGR3N`, `AGETR01`, `AGETR03`, `BRTHDTF`, `OBESEFL` | - |
| [XB datasets (BLA 125742 S6)](c4591001.md#s6) | ADXB | the investigator-site state from Pfizer's internal site registry (an Oracle database) | `STATE` | - |
| [EUA safety and final efficacy (EUA 27034 S1)](c4591001.md#s1-safety-fa-eff) | ADCEVD | the CE and EX records the EUA ADaM read, which differ from the released EUA CE and EX | `EXDOSE` | 1,496 of 205,362 |
| [EUA safety and final efficacy (EUA 27034 S1)](c4591001.md#s1-safety-fa-eff) | ADDS | the DS records behind 133 ADDS rows, not in the released EUA DS | - | 133 of 79,147 |
| [EUA safety and final efficacy (EUA 27034 S1)](c4591001.md#s1-safety-fa-eff) | ADFACEVD | the EX doses the EUA ADaM read for Phase 1 placebo, which differ from the released EUA EX | `EXDOSE` | - |
| [EUA safety and final efficacy (EUA 27034 S1)](c4591001.md#s1-safety-fa-eff) | ADMH | MH.MHENRTPT / MHENTPT (not in the released EUA MH) and MHSTDTC / MHENDTC values redacted to (b)(6) | `AENDTF`, `ASTDTF`, `MHENRTPT`, `MHENTPT` | - |
| [EUA safety and final efficacy (EUA 27034 S1)](c4591001.md#s1-safety-fa-eff) | ADSL | DM.BRTHDTC and two subjects' height and BMI (redacted); the Japanese-participants list the program imports; the IS and DS records the EUA ADaM read, which the released EUA SDTM does not carry | `AGETR01`, `BMICAT`, `BMICATN`, `BRTHDTF`, `COVBLST`, `EOSDCDT`, `EOTDCDT`, `EXCL8FL`, `EXCRIT8`, `INCL8FL`, `JPNFL`, `NIGV1FL` | - |
| [EUA safety and final efficacy (EUA 27034 S1)](c4591001.md#s1-safety-fa-eff) | ADSYMPT | the Visit 1 N-binding IS records behind 368 ADSYMPT rows, not in the released EUA IS | - | 368 of 173,585 |
| [EUA safety and final efficacy (EUA 27034 S1)](c4591001.md#s1-safety-fa-eff) | ADVA | the IS records and the ADSL the EUA ADVA read: an IS without the 184 Month-1 N-binding results the released EUA IS carries, and an earlier ADSL than the released one | `ABLPBLFL`, `SRCSEQ`, `TR01EDT`, `TR01EDTM`, `TR01ETM`, `TRTEDT`, `TRTETM`, `VAX102DT` | - |
| [EUA interim efficacy analysis (EUA 27034 S1)](c4591001.md#s1-ia) | ADSL | DM.BRTHDTC and two subjects' height and BMI (redacted); the Japanese-participants list the program imports; one DS record the interim ADaM read, which the released interim DS does not carry | `AGETR01`, `BMICAT`, `BMICATN`, `BRTHDTF`, `EOTDCDT`, `JPNFL` | - |

## Columns carried from the submitted dataset {#carried}

These columns are copied from the submitted dataset, not derived, because the input they are derived from is not in the release. They are outside the analysis set.

| Study and cut | Dataset | Columns |
| --- | --- | --- |
| mRNA-1273-P201 Addendum 1 (BLA 125752 S3) | ADIS | `PPBABRFL`, `PPNABRFL`, `PPBABRER`, `PPNABRER`, `PPNA2RFL` |
| mRNA-1273-P201 Addendum 1 (BLA 125752 S3) | ADSL | `PPBABFL`, `PPNABFL`, `PPNAB2FL`, `PPBD29FL`, `PPBD57FL`, `PPND29FL`, `PPND57FL`, `PN2D29FL`, `PN2D57FL`, `DVBABFL`, `DVNABFL`, `PPBABERS`, `PPNABERS`, `PPBD29ER`, `PPBD57ER`, `PPND29ER`, `PPND57ER`, `PPNAB2ER`, `PN2D29ER`, `PN2D57ER`, `PBD209FL`, `PND209FL`, `PN2209FL`, `PBD209ER`, `PND209ER`, `PN2209ER` |

## Submitted cells FDA redacted {#redacted}

FDA replaced these submitted ADaM values with `(b)(6)` (FOIA exemption 6) before release, so there is no value to compare the derived one with. They are left out of the analysis-set cells. (Redacted SDTM values are absent inputs, above.)

| Study and cut | Dataset | Cells | Columns |
| --- | --- | ---: | --- |
| mRNA-1273-P301 BLA interim analysis (BLA 125752 S3) | ADSL | 651 | `RACESPY` 641, `BMIBL` 10 |
| mRNA-1273-P301 BLA interim analysis (BLA 125752 S3) | ADSLSF | 26 | `RACESPY` 26 |
| mRNA-1273-P301 Interim analysis IA1b (27073 S5) | ADAESMQ | 468 | `RACESPY` 468 |
| mRNA-1273-P301 Interim analysis IA1b (27073 S5) | ADEX | 1 | `NDOSRSP` 1 |
| mRNA-1273-P301 Interim analysis IA1b (27073 S5) | ADSL | 648 | `RACESPY` 638, `BMIBL` 10 |
| mRNA-1273-P301 Interim analysis IA1a (19745-83 S80) | ADAE | 421 | `RACESPY` 421 |
| mRNA-1273-P301 Interim analysis IA1a (19745-83 S80) | ADEX | 1 | `NDOSRSP` 1 |
| mRNA-1273-P301 Interim analysis IA1a (19745-83 S80) | ADSL | 646 | `RACESPY` 636, `BMIBL` 10 |
| BNT162-01 EUA 27034 S1 (Oct 2020) | ADSL | 144 | `AAGE` 144 |
| BNT162-01 BLA 125742 S1 (Mar 2021) | ADSL | 216 | `AAGE` 216 |
| C4591001 Safety and efficacy (BLA 125742 S1) | ADMH | 24 | `ASTDT` 8, `ASTDY` 8, `ADURN` 8 |
| C4591001 1-month cut (BLA 125742 S211) | ADMH | 24 | `ASTDT` 8, `ASTDY` 8, `ADURN` 8 |
| C4591001 EUA safety and final efficacy (EUA 27034 S1) | ADMH | 28 | `ASTDT` 9, `ASTDY` 9, `ADURN` 10 |

## Problems of the submitted files

These stay in the analysis set: the inputs are there, but the submitted files disagree with each other or with themselves.

### Defects of the submitted files

The submitted dataset is malformed or was not produced by its released program; the spec follows the program, and the dataset is counted as differing only where the file is defective.

| Study | Cuts | Dataset | Defect |
| --- | --- | --- | --- |
| C4591001 | s1-safety-fa-eff | ADMH | one AENDY cell holds its value three times, separated by line breaks |
| C4591001 | s1-ia | ADC19EF | the file lacks the PRCDCSAD rows its released program writes |

### Program and submitted file disagree

The released program's text and the submitted dataset disagree. The note does not change the result.

| Study | Cuts | Dataset | What disagrees |
| --- | --- | --- | --- |
| mRNA-1273-P301 | s3 | ADSLSF | a11adslsf.sas keeps one record per screen-failure date (by usubjid subjid dsstdtc; if last.dsstdtc), so the two subjects who failed screening on two dates get two records each, while the program's own note says the last reason is kept. The submitted ADSLSF has one record for each, the later one; the spec follows the note. |

### Define-XML and data disagree

688 findings where a received define and its submitted datasets disagree: see [Define-XML against the data](define-data.md).
