# Define-XML against the submitted data

Each received define is checked against the ADaM datasets PHMPT released for the same deliverable. Both are the sponsor's files and yamaa is not involved: a finding is a place where the sponsor's define and its datasets disagree. `scripts/define/check_define_data.py` writes the findings (`data/reproduction/define_data.json`, collected 2026-11-27); terms: [glossary](../glossary.md).

**688 findings in 129 of the 159 datasets**, in the 13 deliverables with a define. C4591001 Supplementary datasets (BLA 125742 S1 Supp) and C4591001 EUA interim efficacy analysis (EUA 27034 S1) were released without a define and are not checked. A finding is one variable, or one dataset for the dataset-level checks.

## Findings by check

| Check | What it finds | Findings | Datasets |
| --- | --- | ---: | ---: |
| Datasets in only one of the two | A dataset the define describes that the release lacks, or one the release has that the define does not describe. | 6 | 6 |
| Variables in only one of the two | A variable the define lists that the dataset lacks, or a column of the dataset the define does not list. | 15 | 11 |
| Data type | The define says text and the column is numeric, or the define says integer or float and the column is character. | 0 | 0 |
| Length | A text value longer than the define's Length. | 40 | 22 |
| Codelist | Values outside the variable's enumerated codelist (its coded values and decodes); dictionaries and other external codelists are not checked. | 8 | 5 |
| Mandatory | The define marks the variable Mandatory="Yes" (a value on every record) and some records have none. | 538 | 75 |
| Keys | The define's key variables do not identify one record: some records repeat a key. | 81 | 81 |
| Variable label | The column's label differs from the variable's Description. | 0 | 0 |
| Dataset label | The dataset's label differs from the dataset's Description. | 0 | 0 |
| **All** | | **688** | **129** |

**Set apart as possible release artifacts, not counted: 228.** 133 are column types or labels, or dataset labels, in files FDA redacted (they hold `(b)(6)` values), which FDA's rewrite of the file may have changed (C4591001 ADMH stores its dates as text and has file names as labels), and a redacted variable FDA renamed (`BRTHDT` to `BRTHDT_2`); 95 are types, lengths or labels of files PHMPT released only as JMP tables, which come from the conversion. Whether the sponsor or the release made them cannot be told from the files, so they are listed by deliverable but not counted. The checks on values (variables, lengths, codelists, mandatory values, keys) are counted in every file; redacted values are never counted as codelist or length findings.

## By deliverable

### mRNA-1273-P201 Day 57 analysis (BLA 125752 S3) {#mrna-1273-p201-s3-d57}

15 datasets checked against the define; 54 findings; 1 more set apart as possible release artifacts.

| Dataset | Check | Where |
| --- | --- | --- |
| ADAE | Variables in only one of the two | in the data only: `TRTA` |
| ADAE | Length | `AESPID` 3 < 6, `AETERM` 70 < 81, `AEDECOD` 33 < 36, `AELLT` 31 < 36, `AEHLT` 57 < 70, `AEHLGT` 55 < 86 |
| ADAE | Mandatory | `AESTDY` 1 of 301, `AEACNOTH` 1 of 301 |
| ADAE | Keys | `AEBODSYS, AEDECOD, AESTDTC, AEENDTC`: 2 of 301 records repeat a key |
| ADAR | Length | `FALOC` 34 < 49, `FAEVAL` 12 < 13 |
| ADAR | Keys | `USUBJID, PARCAT1, PARAMCD, ATPTREF, ATPTN, ADT, ATM`: 27 of 110,009 records repeat a key |
| ADARP7D | Mandatory | `ANL01FL` 56 of 150, `ATOXGR` 5 of 150, `ATOXGRN` 5 of 150, `AVAL` 150 of 150, `ASTTM` 41 of 150, `ASTDTM` 41 of 150, `AENTM` 44 of 150, `AENDTM` 44 of 150, `MAAEFL` 136 of 150 |
| ADARP7D | Keys | `USUBJID, PARCAT1, PARAMCD, ATPTREF`: 56 of 150 records repeat a key |
| ADARSUM | Mandatory | `SRCDOM` 4,463 of 22,291, `SRCSEQ` 4,463 of 22,291, `SRCVAR` 4,463 of 22,291 |
| ADCM | Length | `CMINDC` 83 < 108, `CMROUTE` 13 < 17 |
| ADCM | Keys | `USUBJID, CMTRT, CMSTDTC, CMENDTC`: 11 of 1,721 records repeat a key |
| ADCOV | Length | `VISIT` 28 < 32 |
| ADCOV | Mandatory | `AVISIT` 1,511 of 10,388, `AVISITN` 1,511 of 10,388, `AWRANGE` 1,511 of 10,388, `AWTARGET` 1,511 of 10,388 |
| ADDV | Length | `DVSCAT` 28 < 30, `DVTERM1` 129 < 195 |
| ADDV | Mandatory | `DOSE2DT` 18 of 342, `DOS2DTM` 18 of 342 |
| ADDV | Keys | `USUBJID, DVCAT, DVSCAT, DVSTDTC, DVTERM`: 1 of 342 records repeat a key |
| ADIS | Length | `ISSTRESC` 7 < 9 |
| ADLB | Keys | `USUBJID, PARAMCD, AVISITN, LBDTC`: 3 of 36,791 records repeat a key |
| ADMB | Keys | `USUBJID, PARCAT1, PARAMCD, AVISITN, MBDTC`: 20 of 37,626 records repeat a key |
| ADMH | Mandatory | `RACESPY` 2,436 of 2,444, `COMPLFL` 2,406 of 2,444, `COV19BL` 4 of 2,444, `DOSE2DT` 49 of 2,444, `DOS2DTM` 49 of 2,444, `MHSTDTC` 1 of 2,444, `MHENDTC` 1,530 of 2,444, `MHENRTPT` 914 of 2,444, `MHSTDY` 2,254 of 2,444, `MHENDY` 2,343 of 2,444 |
| ADMH | Keys | `USUBJID, MHDECOD`: 98 of 2,444 records repeat a key |
| ADMH | Data type (set apart: FDA redaction) | define integer, data character: `MHSTDY` |
| ADVS | Keys | `USUBJID, PARAMCD, AVISITN, VSDTC`: 5 of 38,439 records repeat a key |

### mRNA-1273-P201 Addendum 1 (BLA 125752 S3) {#mrna-1273-p201-s3-add1}

15 datasets checked against the define; 66 findings; 2 more set apart as possible release artifacts.

| Dataset | Check | Where |
| --- | --- | --- |
| ADAE | Length | `AESPID` 3 < 6, `AETERM` 70 < 95, `AEDECOD` 33 < 46, `AELLT` 31 < 65, `AEHLT` 57 < 70, `AEHLGT` 55 < 86, `AEOUT` 26 < 32 |
| ADAE | Mandatory | `ELECSBL` 563 of 563, `AESTDY` 2 of 563, `AESEV` 1 of 563, `AEACNOTH` 1 of 563 |
| ADAE | Keys | `AEBODSYS, AEDECOD, AESTDTC, AEENDTC`: 5 of 563 records repeat a key |
| ADAR | Length | `FALOC` 34 < 49, `FAEVAL` 12 < 13 |
| ADAR | Mandatory | `ELECSBL` 110,886 of 110,886 |
| ADAR | Keys | `USUBJID, PARCAT1, PARAMCD, ATPTREF, ATPTN, ADT, ATM`: 27 of 110,886 records repeat a key |
| ADARP7D | Mandatory | `ELECSBL` 1,443 of 1,443, `ATM` 336 of 1,443, `ADTM` 336 of 1,443, `MAAEFL` 1,337 of 1,443 |
| ADARP7D | Keys | `USUBJID, PARCAT1, PARAMCD, ATPTREF`: 1,333 of 1,443 records repeat a key |
| ADARSUM | Mandatory | `ELECSBL` 22,290 of 22,290, `SRCDOM` 4,462 of 22,290, `SRCSEQ` 4,462 of 22,290, `SRCVAR` 4,462 of 22,290 |
| ADCM | Length | `CMINDC` 83 < 108, `CMROUTE` 13 < 24 |
| ADCM | Mandatory | `ELECSBL` 2,277 of 2,277 |
| ADCM | Keys | `USUBJID, CMTRT, CMSTDTC, CMENDTC`: 14 of 2,277 records repeat a key |
| ADCOV | Length | `VISIT` 28 < 33 |
| ADCOV | Mandatory | `ELECSBL` 13,284 of 13,284, `AVISIT` 1,511 of 13,284, `AVISITN` 1,511 of 13,284, `AWRANGE` 1,511 of 13,284, `AWTARGET` 1,511 of 13,284 |
| ADDV | Length | `DVSCAT` 28 < 30, `DVTERM1` 129 < 165 |
| ADDV | Mandatory | `ELECSBL` 1,029 of 1,029 |
| ADDV | Keys | `USUBJID, DVCAT, DVSCAT, DVSTDTC, DVTERM`: 4 of 1,029 records repeat a key |
| ADEX | Mandatory | `ELECSBL` 1,196 of 1,196 |
| ADIS | Length | `VISIT` 28 < 33, `ISSTRESC` 7 < 9 |
| ADIS | Mandatory | `ELECSBL` 33,241 of 33,241, `LOD` 1 of 33,241, `ISLLOQ` 1 of 33,241, `ULOQ` 1 of 33,241 |
| ADIS | Keys | `USUBJID, PARCAT1, PARAMCD, AVISITN, ISDTC`: 8 of 33,241 records repeat a key |
| ADLB | Length | `VISIT` 28 < 33 |
| ADLB | Mandatory | `ELECSBL` 37,261 of 37,261 |
| ADLB | Keys | `USUBJID, PARAMCD, AVISITN, LBDTC`: 3 of 37,261 records repeat a key |
| ADMB | Length | `VISIT` 28 < 33 |
| ADMB | Mandatory | `ELECSBL` 41,243 of 41,243 |
| ADMB | Keys | `USUBJID, PARCAT1, PARAMCD, AVISITN, MBDTC`: 20 of 41,243 records repeat a key |
| ADMH | Mandatory | `ELECSBL` 2,449 of 2,449, `MHSTDTC` 1 of 2,449, `MHENDTC` 1,535 of 2,449, `MHENRTPT` 914 of 2,449, `MHSTDY` 2,259 of 2,449, `MHENDY` 2,348 of 2,449 |
| ADMH | Keys | `USUBJID, MHDECOD`: 97 of 2,449 records repeat a key |
| ADMH | Data type (set apart: FDA redaction) | define integer, data character: `MHSTDY` |
| ADMH | Dataset label (set apart: FDA redaction) | differs |
| ADSL | Length | `PPNAB2ER` 174 < 197 |
| ADSL | Mandatory | `ELECSBL` 600 of 600, `UNBLND` 42 of 600 |
| ADVS | Length | `VISIT` 28 < 33 |
| ADVS | Mandatory | `ELECSBL` 41,928 of 41,928 |
| ADVS | Keys | `USUBJID, PARAMCD, AVISITN, VSDTC`: 15 of 41,928 records repeat a key |

### mRNA-1273-P301 BLA interim analysis (BLA 125752 S3) {#mrna-1273-p301-s3}

23 datasets checked against the define, 2 in only one of the two; 349 findings; 80 more set apart as possible release artifacts.

| Dataset | Check | Where |
| --- | --- | --- |
| ADAE | Variables in only one of the two | in the data only: `RSTFRD` |
| ADAE | Mandatory | `AGEGR4` 20,815 of 37,756, `AGEGR4N` 20,815 of 37,756, `RACESPY` 35,495 of 37,756, `TRTSEQA` 2 of 37,756, `TRTSEQAN` 2 of 37,756, `AP01EDT` 230 of 37,756, `AP01SEDT` 230 of 37,756, `RACEGR1` 528 of 37,756, `RACEGR1N` 528 of 37,756, `RETHGR1` 86 of 37,756, `RETHGR1N` 86 of 37,756, `TRTA` 297 of 37,756, `TRTAN` 297 of 37,756, `ASTAGE` 2,849 of 37,756, `ASTAGEN` 2,849 of 37,756, `MDOSREF` 291 of 37,756, `TRTEMFL` 221 of 37,756, `D28FL` 15,281 of 37,756 |
| ADAR | Mandatory | `AGE` 5 of 5,062,955, `AGEU` 5 of 5,062,955, `AGEGR1` 5 of 5,062,955, `AGEGR1N` 5 of 5,062,955, `AGEGR2` 5 of 5,062,955, `AGEGR2N` 5 of 5,062,955, `AGEGR3` 5 of 5,062,955, `AGEGR3N` 5 of 5,062,955, `AGEGR4` 2,734,110 of 5,062,955, `AGEGR4N` 2,734,110 of 5,062,955, `SEX` 5 of 5,062,955, `RACESPY` 4,856,042 of 5,062,955, `ETHNIC` 5 of 5,062,955, `TRTSEQA` 5 of 5,062,955, `TRTSEQAN` 5 of 5,062,955, `AP01EDT` 46,949 of 5,062,955, `AP01SEDT` 46,949 of 5,062,955, `STRATAV` 5 of 5,062,955, `STRATAVN` 5 of 5,062,955, `RACEGR1` 47,498 of 5,062,955, `RACEGR1N` 47,498 of 5,062,955, `RETHGR1` 8,393 of 5,062,955, `RETHGR1N` 8,393 of 5,062,955 |
| ADAR | Keys | `USUBJID, PARCAT1, PARAMCD, ATPTREF, ATPTN, ADT`: 9,768 of 5,062,955 records repeat a key |
| ADAR1 | Datasets in only one of the two | released, not in the define |
| ADAR2 | Datasets in only one of the two | released, not in the define |
| ADARP7D | Mandatory | `AGEGR4` 71,763 of 126,750, `AGEGR4N` 71,763 of 126,750, `RACESPY` 119,974 of 126,750, `AP01EDT` 1,452 of 126,750, `AP01SEDT` 1,452 of 126,750, `RACEGR1` 3,117 of 126,750, `RACEGR1N` 3,117 of 126,750, `RETHGR1` 205 of 126,750, `RETHGR1N` 205 of 126,750, `FAEVAL` 15,949 of 126,750, `MAAEFL` 121,972 of 126,750 |
| ADARP7D | Keys | `USUBJID, PARCAT1, PARAMCD, ATPTREF, ADT`: 36,368 of 126,750 records repeat a key |
| ADARSUM | Mandatory | `AGE` 3 of 1,068,202, `AGEU` 3 of 1,068,202, `AGEGR1` 3 of 1,068,202, `AGEGR1N` 3 of 1,068,202, `AGEGR2` 3 of 1,068,202, `AGEGR2N` 3 of 1,068,202, `AGEGR3` 3 of 1,068,202, `AGEGR3N` 3 of 1,068,202, `AGEGR4` 565,715 of 1,068,202, `AGEGR4N` 565,715 of 1,068,202, `SEX` 3 of 1,068,202, `RACESPY` 1,023,358 of 1,068,202, `ETHNIC` 3 of 1,068,202, `TRTSEQA` 3 of 1,068,202, `TRTSEQAN` 3 of 1,068,202, `AP01EDT` 10,435 of 1,068,202, `AP01SEDT` 10,435 of 1,068,202, `STRATAV` 3 of 1,068,202, `STRATAVN` 3 of 1,068,202, `RACEGR1` 10,362 of 1,068,202, `RACEGR1N` 10,362 of 1,068,202, `RETHGR1` 1,800 of 1,068,202, `RETHGR1N` 1,800 of 1,068,202, `PARCAT1` 163,305 of 1,068,202, `PARCAT1N` 163,305 of 1,068,202, `AVAL` 834,153 of 1,068,202, `AVALC` 412,822 of 1,068,202, `ATOXGR` 234,049 of 1,068,202, `ATOXGRN` 234,049 of 1,068,202 |
| ADCM | Mandatory | `AGEGR4` 128,166 of 195,063, `AGEGR4N` 128,166 of 195,063, `RACESPY` 187,470 of 195,063, `TRTSEQA` 103 of 195,063, `TRTSEQAN` 103 of 195,063, `AP01EDT` 1,071 of 195,063, `AP01SEDT` 1,071 of 195,063, `RACEGR1` 1,774 of 195,063, `RACEGR1N` 1,774 of 195,063, `RETHGR1` 362 of 195,063, `RETHGR1N` 362 of 195,063, `CMTRT` 1 of 195,063, `CMDECOD` 1 of 195,063, `CMPROTCD` 1 of 195,063 |
| ADCM | Keys | `USUBJID, CMTRT, CMSTDTC, CMENDTC`: 924 of 195,063 records repeat a key |
| ADCM | Data type (set apart: JMP) | define integer, data character: `TR01SDT`, `TR01SDTM`, `TRTSDT`, `TRTEDT`, `TR01EDT`, `TR01EDTM`, `DOSE2DT`, `DOS2DTM`, `TR02SDT`, `TR02SDTM`, `TR02EDT`, `TR02EDTM`, `OLDOS2DT`, `OLDO2DTM`, `EUAVACDT`, `AP01EDT`, `AP02SDT`, `AP02EDT`, `AP01SEDT`, `AP02SSDT`, `AP02SEDT`, `CMSTDY`, `ASTDT`, `ASTDY`, `AENDT`, `AENDY` |
| ADDV | Mandatory | `AGE` 1 of 82,039, `AGEU` 1 of 82,039, `AGEGR1` 1 of 82,039, `AGEGR1N` 1 of 82,039, `AGEGR2` 1 of 82,039, `AGEGR2N` 1 of 82,039, `AGEGR3` 1 of 82,039, `AGEGR3N` 1 of 82,039, `AGEGR4` 41,908 of 82,039, `AGEGR4N` 41,908 of 82,039, `SEX` 1 of 82,039, `RACESPY` 78,976 of 82,039, `ETHNIC` 1 of 82,039, `TRTSEQA` 148 of 82,039, `TRTSEQAN` 148 of 82,039, `AP01EDT` 2,363 of 82,039, `AP01SEDT` 2,363 of 82,039, `STRATAV` 1 of 82,039, `STRATAVN` 1 of 82,039, `RACEGR1` 874 of 82,039, `RACEGR1N` 874 of 82,039, `RETHGR1` 210 of 82,039, `RETHGR1N` 210 of 82,039 |
| ADDV | Keys | `USUBJID, DVCAT, DVSCAT, DVSTDTC, DVTERM`: 2,206 of 82,039 records repeat a key |
| ADEFF | Length | `EVIDINF` 15 < 21 |
| ADEFF | Mandatory | `AGEGR4` 7,822 of 18,102, `AGEGR4N` 7,822 of 18,102, `RACESPY` 17,185 of 18,102, `AP01EDT` 150 of 18,102, `AP01SEDT` 150 of 18,102, `RACEGR1` 344 of 18,102, `RACEGR1N` 344 of 18,102, `RETHGR1` 8 of 18,102, `RETHGR1N` 8 of 18,102, `AVISIT` 16,011 of 18,102, `AVISITN` 16,011 of 18,102 |
| ADEFF2 | Mandatory | `AGEGR4` 289,428 of 536,274, `AGEGR4N` 289,428 of 536,274, `RACESPY` 514,560 of 536,274, `TRTSEQA` 1,242 of 536,274, `TRTSEQAN` 1,242 of 536,274, `AP01EDT` 5,592 of 536,274, `AP01SEDT` 5,592 of 536,274, `RACEGR1` 4,994 of 536,274, `RACEGR1N` 4,994 of 536,274, `RETHGR1` 940 of 536,274, `RETHGR1N` 940 of 536,274 |
| ADEFF3 | Length | `SRCVAR` 6 < 8 |
| ADEFF3 | Mandatory | `AGEGR4` 124,075 of 307,100, `AGEGR4N` 124,075 of 307,100, `RACESPY` 293,090 of 307,100, `AP01EDT` 2,682 of 307,100, `AP01SEDT` 2,682 of 307,100, `RACEGR1` 6,295 of 307,100, `RACEGR1N` 6,295 of 307,100, `RETHGR1` 234 of 307,100, `RETHGR1N` 234 of 307,100 |
| ADEFF3 | Keys | `USUBJID, PARAMCD, ARELTPT`: 124 of 307,100 records repeat a key |
| ADEX | Length | `VISIT` 25 < 34 |
| ADEX | Mandatory | `AGE` 1 of 85,233, `AGEU` 1 of 85,233, `AGEGR1` 1 of 85,233, `AGEGR1N` 1 of 85,233, `AGEGR2` 1 of 85,233, `AGEGR2N` 1 of 85,233, `AGEGR3` 1 of 85,233, `AGEGR3N` 1 of 85,233, `AGEGR4` 46,528 of 85,233, `AGEGR4N` 46,528 of 85,233, `SEX` 1 of 85,233, `RACESPY` 81,749 of 85,233, `ETHNIC` 1 of 85,233, `TRTSEQA` 64 of 85,233, `TRTSEQAN` 64 of 85,233, `AP01EDT` 640 of 85,233, `AP01SEDT` 640 of 85,233, `STRATAV` 1 of 85,233, `STRATAVN` 1 of 85,233, `RACEGR1` 789 of 85,233, `RACEGR1N` 789 of 85,233, `RETHGR1` 146 of 85,233, `RETHGR1N` 146 of 85,233 |
| ADEX | Keys | `USUBJID, EXSTDTC`: 37 of 85,233 records repeat a key |
| ADIS | Length | `AWRANGE` 50 < 61 |
| ADIS | Mandatory | `AGEGR4` 137,373 of 261,357, `AGEGR4N` 137,373 of 261,357, `RACESPY` 250,796 of 261,357, `TRTSEQA` 16 of 261,357, `TRTSEQAN` 16 of 261,357, `AP01EDT` 3,013 of 261,357, `AP01SEDT` 3,013 of 261,357, `RACEGR1` 2,748 of 261,357, `RACEGR1N` 2,748 of 261,357, `RETHGR1` 271 of 261,357, `RETHGR1N` 271 of 261,357, `ISSTRESC` 58,268 of 261,357 |
| ADMB | Mandatory | `AGEGR4` 102,634 of 211,582, `AGEGR4N` 102,634 of 211,582, `RACESPY` 201,415 of 211,582, `TRTSEQA` 14 of 211,582, `TRTSEQAN` 14 of 211,582, `AP01EDT` 1,306 of 211,582, `AP01SEDT` 1,306 of 211,582, `RACEGR1` 2,249 of 211,582, `RACEGR1N` 2,249 of 211,582, `RETHGR1` 321 of 211,582, `RETHGR1N` 321 of 211,582, `MBDTC` 1 of 211,582, `ADT` 1 of 211,582, `ADY` 15 of 211,582, `VISIT` 6,149 of 211,582, `VISITNUM` 6,149 of 211,582, `MBTPT` 103,073 of 211,582 |
| ADMH | Mandatory | `AGEGR4` 123,140 of 176,585, `AGEGR4N` 123,140 of 176,585, `RACESPY` 170,914 of 176,585, `TRTSEQA` 180 of 176,585, `TRTSEQAN` 180 of 176,585, `AP01EDT` 1,276 of 176,585, `AP01SEDT` 1,276 of 176,585, `RACEGR1` 1,389 of 176,585, `RACEGR1N` 1,389 of 176,585, `RETHGR1` 356 of 176,585, `RETHGR1N` 356 of 176,585, `MHTERM` 3 of 176,585, `MHBODSYS` 3 of 176,585, `MHDECOD` 3 of 176,585, `MHPTCD` 3 of 176,585 |
| ADMH | Keys | `USUBJID, MHCAT, MHTERM, MHDECOD, MHSTDTC`: 135 of 176,585 records repeat a key |
| ADMH | Data type (set apart: JMP) | define integer, data character: `TR01SDT`, `TR01SDTM`, `TRTSDT`, `TRTEDT`, `TR01EDT`, `TR01EDTM`, `DOSE2DT`, `DOS2DTM`, `TR02SDT`, `TR02SDTM`, `TR02EDT`, `TR02EDTM`, `OLDOS2DT`, `OLDO2DTM`, `EUAVACDT`, `AP01EDT`, `AP02SDT`, `AP02EDT`, `AP01SEDT`, `AP02SSDT`, `AP02SEDT`, `MHPTCD`, `MHSTDY`, `MHENDY` |
| ADRISK | Mandatory | `AGE` 19 of 577,703, `AGEU` 19 of 577,703, `AGEGR1` 19 of 577,703, `AGEGR1N` 19 of 577,703, `AGEGR2` 19 of 577,703, `AGEGR2N` 19 of 577,703, `AGEGR3` 19 of 577,703, `AGEGR3N` 19 of 577,703, `AGEGR4` 310,271 of 577,703, `AGEGR4N` 310,271 of 577,703, `SEX` 19 of 577,703, `RACESPY` 554,276 of 577,703, `ETHNIC` 19 of 577,703, `TRTSEQA` 1,043 of 577,703, `TRTSEQAN` 1,043 of 577,703, `AP01EDT` 6,080 of 577,703, `AP01SEDT` 6,080 of 577,703, `STRATAV` 19 of 577,703, `STRATAVN` 19 of 577,703, `RACEGR1` 5,479 of 577,703, `RACEGR1N` 5,479 of 577,703, `RETHGR1` 995 of 577,703, `RETHGR1N` 995 of 577,703 |
| ADRISK | Data type (set apart: JMP) | define integer, data character: `TR01SDT`, `TR01SDTM`, `TRTSDT`, `TRTEDT`, `TR01EDT`, `TR01EDTM`, `DOSE2DT`, `DOS2DTM`, `TR02SDT`, `TR02SDTM`, `TR02EDT`, `TR02EDTM`, `OLDOS2DT`, `OLDO2DTM`, `EUAVACDT`, `AP01EDT`, `AP02SDT`, `AP02EDT`, `AP01SEDT`, `AP02SSDT`, `AP02SEDT` |
| ADRISK | Length (set apart: JMP) | `OTHSPY` 200 < 202 |
| ADSL | Mandatory | `AGE` 1 of 30,423, `AGEU` 1 of 30,423, `AGEGR1` 1 of 30,423, `AGEGR1N` 1 of 30,423, `AGEGR2` 1 of 30,423, `AGEGR2N` 1 of 30,423, `AGEGR3` 1 of 30,423, `AGEGR3N` 1 of 30,423, `AGEGR4` 16,337 of 30,423, `AGEGR4N` 16,337 of 30,423, `SEX` 1 of 30,423, `ETHNIC` 1 of 30,423, `PROTVER` 1 of 30,423, `RFICDT` 1 of 30,423, `EUAVACDT` 29,670 of 30,423, `AP01EDT` 320 of 30,423, `AP01SEDT` 320 of 30,423, `RACEGR1` 289 of 30,423, `RACEGR1N` 289 of 30,423 |
| ADSL | Data type (set apart: JMP) | define float, data character: `HEIGHTBL`, `BMIBL` |
| ADSL | Length (set apart: JMP) | `PPSIEREA` 100 < 158 |
| ADSLSF | Mandatory | `AGE` 4 of 1,679, `AGEU` 4 of 1,679, `SEX` 5 of 1,679, `RACE` 2 of 1,679, `RACESPY` 1,624 of 1,679, `ETHNIC` 5 of 1,679, `PROTVER` 5 of 1,679, `CHILDBP` 1,675 of 1,679, `RFICDT` 4 of 1,679, `PREVSCR` 3 of 1,679 |
| ADSYMP | Mandatory | `AGEGR4` 473,420 of 1,056,575, `AGEGR4N` 473,420 of 1,056,575, `RACESPY` 1,000,128 of 1,056,575, `AP01EDT` 6,958 of 1,056,575, `AP01SEDT` 6,958 of 1,056,575, `RACEGR1` 14,787 of 1,056,575, `RACEGR1N` 14,787 of 1,056,575, `RETHGR1` 1,091 of 1,056,575, `RETHGR1N` 1,091 of 1,056,575 |
| ADTTE | Mandatory | `AGEGR4` 821,437 of 1,522,428, `AGEGR4N` 821,437 of 1,522,428, `RACESPY` 1,460,689 of 1,522,428, `AP01EDT` 13,760 of 1,522,428, `AP01SEDT` 13,760 of 1,522,428, `RACEGR1` 14,354 of 1,522,428, `RACEGR1N` 14,354 of 1,522,428, `RETHGR1` 2,614 of 1,522,428, `RETHGR1N` 2,614 of 1,522,428 |
| ADTTEA | Mandatory | `AGEGR4` 225,392 of 417,706, `AGEGR4N` 225,392 of 417,706, `RACESPY` 400,768 of 417,706, `AP01EDT` 3,840 of 417,706, `AP01SEDT` 3,840 of 417,706, `RACEGR1` 3,934 of 417,706, `RACEGR1N` 3,934 of 417,706, `RETHGR1` 718 of 417,706, `RETHGR1N` 718 of 417,706 |
| ADTTEA | Dataset label (set apart: FDA redaction) | differs |
| ADTTEB | Mandatory | `AGEGR4` 163,010 of 303,460, `AGEGR4N` 163,010 of 303,460, `RACESPY` 291,150 of 303,460, `AP01EDT` 3,200 of 303,460, `AP01SEDT` 3,200 of 303,460, `RACEGR1` 2,880 of 303,460, `RACEGR1N` 2,880 of 303,460, `RETHGR1` 520 of 303,460, `RETHGR1N` 520 of 303,460 |
| ADTTRE | Mandatory | `AGEGR4` 33,063 of 61,716, `AGEGR4N` 33,063 of 61,716, `RACESPY` 59,215 of 61,716, `AP01EDT` 648 of 61,716, `AP01SEDT` 648 of 61,716, `RACEGR1` 597 of 61,716, `RACEGR1N` 597 of 61,716, `RETHGR1` 105 of 61,716, `RETHGR1N` 105 of 61,716 |
| ADTTRE2 | Mandatory | `AGEGR4` 812 of 1,973, `AGEGR4N` 812 of 1,973, `RACESPY` 1,898 of 1,973, `AP01EDT` 15 of 1,973, `AP01SEDT` 15 of 1,973, `RACEGR1` 38 of 1,973, `RACEGR1N` 38 of 1,973 |
| ADVS | Length | `AWRANGE` 50 < 61 |
| ADVS | Mandatory | `AGEGR4` 653,635 of 1,200,159, `AGEGR4N` 653,635 of 1,200,159, `RACESPY` 1,151,430 of 1,200,159, `TRTSEQA` 366 of 1,200,159, `TRTSEQAN` 366 of 1,200,159, `AP01EDT` 8,626 of 1,200,159, `AP01SEDT` 8,626 of 1,200,159, `RACEGR1` 11,239 of 1,200,159, `RACEGR1N` 11,239 of 1,200,159, `RETHGR1` 2,057 of 1,200,159, `RETHGR1N` 2,057 of 1,200,159, `TRTAN` 256,673 of 1,200,159, `VSDTC` 85 of 1,200,159 |
| ADVS | Keys | `USUBJID, PARAMCD, AVISITN, ADT, VISITNUM, VSTPT`: 170 of 1,200,159 records repeat a key |
| ADVS | Data type (set apart: FDA redaction) | define float, data character: `AVAL`, `BASE`, `CHG`, `PCHG` |

### mRNA-1273-P301 Interim analysis IA1b (27073 S5) {#mrna-1273-p301-s5}

17 datasets checked against the define, 2 in only one of the two; 80 findings; 15 more set apart as possible release artifacts.

| Dataset | Check | Where |
| --- | --- | --- |
| ADAE | Mandatory | `COMPLFL` 15,941 of 16,059, `ELECSBL` 133 of 16,059, `TRTA` 199 of 16,059, `TRTAN` 199 of 16,059, `ASTAGE` 196 of 16,059, `ASTAGEN` 196 of 16,059, `MDOSREF` 196 of 16,059, `MRDSTDY` 196 of 16,059, `TRTEMFL` 169 of 16,059, `D28FL` 3,176 of 16,059 |
| ADAESMQ | Mandatory | `COMPLFL` 15,941 of 16,059, `ELECSBL` 133 of 16,059, `TRTA` 199 of 16,059, `TRTAN` 199 of 16,059, `ASTAGE` 196 of 16,059, `ASTAGEN` 196 of 16,059, `MDOSREF` 196 of 16,059, `MRDSTDY` 196 of 16,059, `TRTEMFL` 169 of 16,059, `D28FL` 3,176 of 16,059 |
| ADAR | Mandatory | `AGE` 5 of 4,975,618, `AGEGR1` 5 of 4,975,618, `COMPLFL` 4,944,886 of 4,975,618, `SCOV2BL` 81,694 of 4,975,618, `TRT01A` 5 of 4,975,618 |
| ADAR | Keys | `USUBJID, PARCAT1, PARAMCD, ATPTREF, ATPTN, ADT, ATM`: 180 of 4,975,618 records repeat a key |
| ADAR1 | Datasets in only one of the two | released, not in the define |
| ADAR2 | Datasets in only one of the two | released, not in the define |
| ADARP7D | Mandatory | `FAEVAL` 17,111 of 176,322, `MAAEFL` 172,393 of 176,322 |
| ADARP7D | Keys | `USUBJID, PARCAT1, PARAMCD, ATPTREF, ADT, ATM`: 182 of 176,322 records repeat a key |
| ADARSUM | Mandatory | `TRT01A` 3 of 1,067,282, `TRT01AN` 3 of 1,067,282, `TR01SDT` 3 of 1,067,282, `TR01SDTM` 3 of 1,067,282, `TR01EDT` 3 of 1,067,282, `TR01EDTM` 31 of 1,067,282, `PARCAT1` 163,133 of 1,067,282, `PARCAT1N` 163,133 of 1,067,282, `AVAL` 833,703 of 1,067,282, `AVALC` 412,261 of 1,067,282, `ATOXGR` 233,579 of 1,067,282, `ATOXGRN` 233,579 of 1,067,282 |
| ADCM | Mandatory | `COMPLFL` 156,194 of 157,516, `ELECSBL` 1,528 of 157,516, `CMTRT` 8 of 157,516 |
| ADCM | Keys | `USUBJID, CMTRT, CMSTDTC, CMENDTC`: 655 of 157,516 records repeat a key |
| ADCM | Data type (set apart: JMP) | define integer, data character: `CMSTDY`, `ASTDT`, `ASTDY`, `AENDT`, `AENDY` |
| ADDV | Mandatory | `AGE` 3 of 8,735, `AGEU` 3 of 8,735, `AGEGR1` 3 of 8,735, `AGEGR1N` 3 of 8,735, `AGEGR2` 3 of 8,735, `AGEGR2N` 3 of 8,735, `RACE` 3 of 8,735, `ETHNIC` 3 of 8,735 |
| ADDV | Keys | `USUBJID, DVCAT, DVSCAT, DVSTDTC, DVTERM`: 416 of 8,735 records repeat a key |
| ADEX | Variables in only one of the two | in the define only: `NDOSRSP1`, `NDOSRSP2` |
| ADMB | Variables in only one of the two | in the define only: `MBSTAT` |
| ADMB | Mandatory | `MBDTC` 1 of 108,199, `ADT` 1 of 108,199, `ADY` 16 of 108,199, `VISIT` 2,446 of 108,199, `VISITNUM` 2,446 of 108,199, `MBTPT` 42,627 of 108,199 |
| ADRISK | Variables in only one of the two | in the define only: `OTHSPY2` |
| ADRISK | Length (set apart: JMP) | `OTHSPY` 200 < 202 |
| ADSL | Mandatory | `AGE` 47 of 30,571, `AGEU` 47 of 30,571, `SEX` 48 of 30,571, `RACE` 47 of 30,571, `ARM` 98 of 30,571, `TRT01P` 150 of 30,571 |
| ADSL | Data type (set apart: JMP) | define text, data numeric: `PROTVER`, `RANDNUM`; define float, data character: `HEIGHTBL`, `BMIBL` |
| ADTTEA | Dataset label (set apart: FDA redaction) | differs |
| ADVS | Mandatory | `STRATARN` 266 of 827,208, `COMPLFL` 821,308 of 827,208, `ELECSBL` 7,520 of 827,208, `TRT01P` 266 of 827,208, `TRT01PN` 266 of 827,208, `TRTAN` 259,990 of 827,208, `VSDTC` 204 of 827,208 |
| ADVS | Keys | `USUBJID, PARAMCD, AVISITN, ADT, ATM, VISITNUM, VSTPT`: 29 of 827,208 records repeat a key |
| ADVS | Data type (set apart: FDA redaction) | define float, data character: `AVAL`, `BASE`, `CHG`, `PCHG` |

### mRNA-1273-P301 Interim analysis IA1a (19745-83 S80) {#mrna-1273-p301-s80}

16 datasets checked against the define, 2 in only one of the two; 73 findings; 17 more set apart as possible release artifacts.

| Dataset | Check | Where |
| --- | --- | --- |
| ADAE | Codelist | `ASTAGE` 1 of 2 values, `ARELN` 1 of 3 values, `AETOXGR` 4 of 4 values, `AESEV` 3 of 3 values |
| ADAE | Mandatory | `COMPLFL` 13,263 of 13,359, `ELECSBL` 204 of 13,359, `TRTA` 211 of 13,359, `TRTAN` 211 of 13,359, `ASTAGE` 205 of 13,359, `ASTAGEN` 205 of 13,359, `MDOSREF` 205 of 13,359, `MRDSTDY` 205 of 13,359, `TRTEMFL` 185 of 13,359, `D28FL` 1,854 of 13,359 |
| ADAR | Mandatory | `COMPLFL` 4,827,988 of 4,852,255, `SCOV2BL` 151,783 of 4,852,255, `TRT01A` 143 of 4,852,255 |
| ADAR | Keys | `USUBJID, PARCAT1, PARAMCD, ATPTREF, ATPTN, ADT, ATM`: 162 of 4,852,255 records repeat a key |
| ADAR | Variable label (set apart: FDA redaction) | `MEDTAKP`, `MEDTAK` |
| ADAR1 | Datasets in only one of the two | released, not in the define |
| ADAR2 | Datasets in only one of the two | released, not in the define |
| ADARP7D | Mandatory | `FAEVAL` 16,758 of 167,980, `MAAEFL` 164,267 of 167,980 |
| ADARP7D | Keys | `USUBJID, PARCAT1, PARAMCD, ATPTREF, ADT, ATM`: 140 of 167,980 records repeat a key |
| ADARSUM | Mandatory | `TRT01A` 28 of 1,040,696, `TRT01AN` 28 of 1,040,696, `TR01EDTM` 28 of 1,040,696, `PARCAT1` 159,164 of 1,040,696, `PARCAT1N` 159,164 of 1,040,696, `AVAL` 813,749 of 1,040,696, `AVALC` 401,350 of 1,040,696, `ATOXGR` 226,947 of 1,040,696, `ATOXGRN` 226,947 of 1,040,696 |
| ADCM | Mandatory | `COMPLFL` 149,371 of 150,445, `ELECSBL` 3,312 of 150,445, `CMTRT` 10 of 150,445 |
| ADCM | Keys | `USUBJID, CMTRT, CMSTDTC, CMENDTC`: 603 of 150,445 records repeat a key |
| ADCM | Data type (set apart: JMP) | define integer, data character: `CMSTDY`, `ASTDT`, `ASTDY`, `AENDT`, `AENDY` |
| ADDV | Mandatory | `AGE` 1 of 7,413, `AGEU` 1 of 7,413, `AGEGR1` 1 of 7,413, `AGEGR1N` 1 of 7,413, `AGEGR2` 1 of 7,413, `AGEGR2N` 1 of 7,413, `RACE` 1 of 7,413, `ETHNIC` 1 of 7,413 |
| ADDV | Keys | `USUBJID, DVCAT, DVSCAT, DVSTDTC, DVTERM`: 315 of 7,413 records repeat a key |
| ADMB | Variables in only one of the two | in the define only: `MBSTAT` |
| ADMB | Mandatory | `MBDTC` 2 of 96,077, `ADT` 2 of 96,077, `ADY` 17 of 96,077, `VISIT` 1,829 of 96,077, `VISITNUM` 1,829 of 96,077, `MBTPT` 33,749 of 96,077 |
| ADRISK | Length (set apart: JMP) | `OTHSPY` 200 < 202 |
| ADSL | Mandatory | `AGE` 49 of 30,577, `AGEU` 49 of 30,577, `SEX` 50 of 30,577, `RACE` 49 of 30,577, `ARM` 105 of 30,577, `TRT01P` 158 of 30,577 |
| ADSL | Data type (set apart: JMP) | define text, data numeric: `PROTVER`, `RANDNUM`; define float, data character: `HEIGHTBL`, `BMIBL` |
| ADSYMP | Codelist | `PARAM` 1 of 36 values |
| ADTTE | Mandatory | `TRT01A` 31 of 940,850, `TRT01AN` 31 of 940,850 |
| ADTTEA | Codelist | `PARAM` 1 of 16 values |
| ADTTEA | Mandatory | `TRT01A` 16 of 485,600, `TRT01AN` 16 of 485,600 |
| ADTTEA | Dataset label (set apart: FDA redaction) | differs |
| ADVS | Codelist | `ASTAGE` 1 of 2 values |
| ADVS | Mandatory | `STRATARN` 277 of 795,982, `COMPLFL` 791,302 of 795,982, `ELECSBL` 18,857 of 795,982, `TRT01P` 277 of 795,982, `TRT01PN` 277 of 795,982, `TRTAN` 262,564 of 795,982, `VSDTC` 360 of 795,982 |
| ADVS | Keys | `USUBJID, PARAMCD, AVISITN, ADT, ATM, VISITNUM, VSTPT`: 47 of 795,982 records repeat a key |
| ADVS | Data type (set apart: FDA redaction) | define float, data character: `AVAL`, `BASE`, `CHG`, `PCHG` |

### BNT162-01 EUA 27034 S1 (Oct 2020) {#bnt162-01-27034}

7 datasets checked against the define; 2 findings; 2 more set apart as possible release artifacts.

| Dataset | Check | Where |
| --- | --- | --- |
| ADFACEVD | Mandatory | `SRCVAR` 488 of 31,947, `SRCSEQ` 488 of 31,947 |
| ADSL | Data type (set apart: FDA redaction) | define integer, data character: `AGE_M`; define float, data character: `AAGE` |

### BNT162-01 BLA 125742 S1 (Mar 2021) {#bnt162-01-125742}

7 datasets checked against the define; 0 findings; 2 more set apart as possible release artifacts.

| Dataset | Check | Where |
| --- | --- | --- |
| ADSL | Data type (set apart: FDA redaction) | define integer, data character: `AGE_M`; define float, data character: `AAGE` |

### C4591001 Safety and efficacy (BLA 125742 S1) {#c4591001-s1}

11 datasets checked against the define; 16 findings; 40 more set apart as possible release artifacts.

| Dataset | Check | Where |
| --- | --- | --- |
| ADAE | Mandatory | `AESER` 348 of 37,309 |
| ADAE | Keys | `STUDYID, USUBJID, AEDECOD, AESTDTC`: 133 of 37,309 records repeat a key |
| ADC19EF | Keys | `STUDYID, USUBJID, PARAMCD, ADT`: 8,577 of 2,149,013 records repeat a key |
| ADC19EF | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |
| ADCEVD | Keys | `STUDYID, USUBJID, CETERM`: 133,418 of 270,973 records repeat a key |
| ADCM | Keys | `STUDYID, USUBJID, CMDECOD, CMSTDTC`: 11,947 of 19,925 records repeat a key |
| ADDS | Variables in only one of the two | in the data only: `DSTERM_3`, `DSTERM_2` |
| ADDS | Keys | `STUDYID, USUBJID, DSDECOD`: 73,058 of 123,135 records repeat a key |
| ADDS | Dataset label (set apart: FDA redaction) | differs |
| ADDV | Keys | `STUDYID, USUBJID, DVTERM, DVSTDTC`: 823 of 37,113 records repeat a key |
| ADFACEVD | Keys | `STUDYID, USUBJID, PARAMCD, ATPT`: 1,072,173 of 2,258,681 records repeat a key |
| ADMH | Variables in only one of the two | in the define only: `ADTF`, `VAX20U` |
| ADMH | Keys | `STUDYID, USUBJID, MHTERM`: 2,361 of 197,037 records repeat a key |
| ADMH | Data type (set apart: FDA redaction) | define text, data numeric: `SUBJID`, `SITEID`, `MHSPID`; define integer, data character: `ASTDT`, `ASTDY`, `AENDT`, `AENDY`, `TRTSDT`, `TRTSTM`, `TRTSDTM`, `TRTEDT`, `TRTETM`, `TRTEDTM`, `TR01SDT`, `TR01STM`, `TR01SDTM`, `TR01EDT`, `TR01ETM`, `TR01EDTM`, `TR02SDT`, `TR02STM`, `TR02SDTM`, `TR02EDT`, `TR02ETM`, `TR02EDTM`, `VAX101DT`, `VAX102DT`, `VAX10UDT`, `VAX201DT`, `VAX202DT`, `VAX20UDT`, `UNBLNDDT`, `RANDDT`; define float, data character: `ADURN` |
| ADMH | Dataset label (set apart: FDA redaction) | differs |
| ADSL | Mandatory | `TRT01P` 1,455 of 48,091 |
| ADSL | Variables in only one of the two (set apart: FDA redaction) | in the define only: `BRTHDT`; in the data only: `BRTHDT_2` |
| ADSYMPT | Keys | `STUDYID, USUBJID, PARAMCD, ADT`: 83 of 328,438 records repeat a key |
| ADSYMPT | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |
| ADVA | Keys | `STUDYID, USUBJID, PARAMCD, AVISIT`: 56,031 of 114,365 records repeat a key |

### C4591001 1-month cut (BLA 125742 S211) {#c4591001-s211-1mth}

11 datasets checked against the define; 12 findings; 11 more set apart as possible release artifacts.

| Dataset | Check | Where |
| --- | --- | --- |
| ADAE | Mandatory | `AESER` 348 of 37,309 |
| ADAE | Keys | `STUDYID, USUBJID, AEDECOD, AESTDTC`: 133 of 37,309 records repeat a key |
| ADC19EF | Keys | `STUDYID, USUBJID, PARAMCD, ADT`: 8,577 of 2,149,013 records repeat a key |
| ADC19EF | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |
| ADCEVD | Keys | `STUDYID, USUBJID, CETERM`: 133,418 of 270,973 records repeat a key |
| ADCM | Keys | `STUDYID, USUBJID, CMDECOD, CMSTDTC`: 11,947 of 19,925 records repeat a key |
| ADDS | Keys | `STUDYID, USUBJID, DSDECOD`: 73,058 of 123,135 records repeat a key |
| ADDS | Dataset label (set apart: FDA redaction) | differs |
| ADDV | Keys | `STUDYID, USUBJID, DVTERM, DVSTDTC`: 823 of 37,113 records repeat a key |
| ADFACEVD | Keys | `STUDYID, USUBJID, PARAMCD, ATPT`: 1,072,173 of 2,258,681 records repeat a key |
| ADMH | Keys | `STUDYID, USUBJID, MHTERM`: 2,361 of 197,037 records repeat a key |
| ADMH | Data type (set apart: FDA redaction) | define integer, data character: `ASTDT`, `ASTDY`, `AENDT`, `AENDY`; define float, data character: `ADURN` |
| ADMH | Dataset label (set apart: FDA redaction) | differs |
| ADSL | Mandatory | `TRT01P` 1,455 of 48,091 |
| ADSL | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |
| ADSYMPT | Keys | `STUDYID, USUBJID, PARAMCD, ADT`: 83 of 328,438 records repeat a key |
| ADSYMPT | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |
| ADSYMPT | Dataset label (set apart: FDA redaction) | differs |
| ADVA | Keys | `STUDYID, USUBJID, PARAMCD, AVISIT`: 56,031 of 114,365 records repeat a key |

### C4591001 EUA resubmission (EUA 27034 S135) {#c4591001-s135}

11 datasets checked against the define; 14 findings; 39 more set apart as possible release artifacts.

| Dataset | Check | Where |
| --- | --- | --- |
| ADAE | Mandatory | `AESER` 348 of 37,309 |
| ADAE | Keys | `STUDYID, USUBJID, AEDECOD, AESTDTC`: 133 of 37,309 records repeat a key |
| ADAE | Dataset label (set apart: FDA redaction) | differs |
| ADC19EF | Keys | `STUDYID, USUBJID, PARAMCD, ADT`: 8,577 of 2,149,013 records repeat a key |
| ADC19EF | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |
| ADCEVD | Keys | `STUDYID, USUBJID, CETERM`: 133,418 of 270,973 records repeat a key |
| ADCM | Keys | `STUDYID, USUBJID, CMDECOD, CMSTDTC`: 11,947 of 19,925 records repeat a key |
| ADDS | Keys | `STUDYID, USUBJID, DSDECOD`: 73,058 of 123,135 records repeat a key |
| ADDV | Keys | `STUDYID, USUBJID, DVTERM, DVSTDTC`: 823 of 37,113 records repeat a key |
| ADFACEVD | Keys | `STUDYID, USUBJID, PARAMCD, ATPT`: 1,072,173 of 2,258,681 records repeat a key |
| ADMH | Variables in only one of the two | in the define only: `ADTF`, `VAX20U` |
| ADMH | Keys | `STUDYID, USUBJID, MHTERM`: 2,361 of 197,037 records repeat a key |
| ADMH | Data type (set apart: FDA redaction) | define text, data numeric: `SUBJID`, `SITEID`, `MHSPID`; define integer, data character: `ASTDT`, `ASTDY`, `AENDT`, `AENDY`, `TRTSDT`, `TRTSTM`, `TRTSDTM`, `TRTEDT`, `TRTETM`, `TRTEDTM`, `TR01SDT`, `TR01STM`, `TR01SDTM`, `TR01EDT`, `TR01ETM`, `TR01EDTM`, `TR02SDT`, `TR02STM`, `TR02SDTM`, `TR02EDT`, `TR02ETM`, `TR02EDTM`, `VAX101DT`, `VAX102DT`, `VAX10UDT`, `VAX201DT`, `VAX202DT`, `VAX20UDT`, `UNBLNDDT`, `RANDDT`; define float, data character: `ADURN` |
| ADMH | Dataset label (set apart: FDA redaction) | differs |
| ADSL | Mandatory | `TRT01P` 1,455 of 48,091 |
| ADSL | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |
| ADSYMPT | Keys | `STUDYID, USUBJID, PARAMCD, ADT`: 83 of 328,438 records repeat a key |
| ADSYMPT | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |
| ADVA | Keys | `STUDYID, USUBJID, PARAMCD, AVISIT`: 56,031 of 114,365 records repeat a key |

### C4591001 6-month cut, ages 12-15 (BLA 125742 S211) {#c4591001-s211-6mth}

9 datasets checked against the define; 9 findings; 10 more set apart as possible release artifacts.

| Dataset | Check | Where |
| --- | --- | --- |
| ADAE | Length | `AERELTXT` 80 < 83 |
| ADAE | Mandatory | `AESER` 1 of 1,077 |
| ADAE | Keys | `STUDYID, USUBJID, AEDECOD, AESTDTC`: 2 of 1,077 records repeat a key |
| ADAE | Dataset label (set apart: FDA redaction) | differs |
| ADC19EF | Keys | `STUDYID, USUBJID, PARAMCD, ADT`: 7,268 of 121,603 records repeat a key |
| ADC19EF | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |
| ADCM | Keys | `STUDYID, USUBJID, CMDECOD, CMSTDTC`: 232 of 412 records repeat a key |
| ADDS | Keys | `STUDYID, USUBJID, DSDECOD`: 4,186 of 6,594 records repeat a key |
| ADDV | Keys | `STUDYID, USUBJID, DVTERM, DVSTDTC`: 321 of 3,327 records repeat a key |
| ADMH | Keys | `STUDYID, USUBJID, MHTERM`: 18 of 4,381 records repeat a key |
| ADMH | Data type (set apart: FDA redaction) | define integer, data character: `ASTDT`, `ASTDY`, `AENDT`, `AENDY`; define float, data character: `ADURN` |
| ADMH | Dataset label (set apart: FDA redaction) | differs |
| ADSL | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |
| ADSYMPT | Keys | `STUDYID, USUBJID, PARAMCD, ADT`: 101 of 34,798 records repeat a key |
| ADSYMPT | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |

### C4591001 XB datasets (BLA 125742 S6) {#c4591001-s6}

2 datasets checked against the define; 1 findings; 1 more set apart as possible release artifacts.

| Dataset | Check | Where |
| --- | --- | --- |
| ADSL | Mandatory | `TRT01P` 1,455 of 48,091 |
| ADSL | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |

### C4591001 EUA safety and final efficacy (EUA 27034 S1) {#c4591001-s1-safety-fa-eff}

9 datasets checked against the define; 12 findings; 8 more set apart as possible release artifacts.

| Dataset | Check | Where |
| --- | --- | --- |
| ADAE | Codelist | `ASTDTF` 1 of 3 values |
| ADAE | Mandatory | `AESER` 328 of 18,953 |
| ADAE | Keys | `STUDYID, USUBJID, AETERM, AESTDTC`: 1 of 18,953 records repeat a key |
| ADC19EF | Keys | `STUDYID, USUBJID, PARAMCD, ADT`: 537 of 998,891 records repeat a key |
| ADC19EF | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |
| ADCEVD | Keys | `STUDYID, USUBJID, CETERM`: 97,078 of 205,362 records repeat a key |
| ADDS | Keys | `STUDYID, USUBJID, DSDECOD`: 34,338 of 79,147 records repeat a key |
| ADFACEVD | Keys | `STUDYID, USUBJID, PARAMCD, ATPT`: 772,483 of 1,698,532 records repeat a key |
| ADMH | Variables in only one of the two | in the define only: `ADTF` |
| ADMH | Keys | `STUDYID, USUBJID, MHTERM`: 2,299 of 188,762 records repeat a key |
| ADMH | Data type (set apart: FDA redaction) | define integer, data character: `ASTDT`, `ASTDY`, `AENDT`, `AENDY`; define float, data character: `ADURN` |
| ADSL | Mandatory | `TRT01P` 2 of 43,850 |
| ADSL | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |
| ADSYMPT | Variables in only one of the two | in the define only: `C19ILHFL` |
| ADSYMPT | Keys | `STUDYID, USUBJID, PARAMCD, ADT`: 84 of 173,585 records repeat a key |
| ADSYMPT | Data type (set apart: FDA redaction) | define integer, data character: `BRTHDT` |
