# CDISC CORE validation -- submission-pilot6 (SDTM)

- Engine: CORE v0.16.0
- Commit: 5e21a17
- Generated: 2026-09-24T21:29Z

### AE

Report: `core-report-SDTM.json`

- **Total issues**: 2674
- **Unique rules**: 10

**Issues by rule:**

- **CORE-000024** (1191): AEBODSYS is not empty and AEBDSYCD is empty
- **CORE-000701** (1191): EPOCH is missing for clinical subject-level observation.
- **CORE-000657** (250): AEENDTC is populated, when AEOUT = NOT RECOVERED/NOT RESOLVED.
- **CORE-000022** (36): At least one of the Seriousness criteria (AESCAN, AESCONG, AESDISAB, AESDTH, AESHOSP, AESLIFE, AESOD or AESMIE)  = 'Y', but AESER = 'N' or empty.
- **CORE-000321** (1): Study Day of Visit/Collection/Exam (AEDY) variable is missing when Date/Time of Collection (AEDTC) is present.
- **CORE-000552** (1): AESTDY is not properly calculated per study day algorithm
- **CORE-000793** (1): Collection study day (AEDY) is missing when date/time of collection (AEDTC) is populated.
- **CORE-000841** (1): AEENDTC in AE dataset of AE where AEOUT = 'FATAL' is not equal to DTHDTC in the DM dataset.
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
| 108 | AETERM;AESTDTC;AESER;AESCAN;AE | PNEUMONIA;2012-09-07 | CORE-000022 | At least one of the Seriousness criteria (AESCAN, AESCONG, AESDISAB, A |
| 109 | AETERM;AESTDTC;AESER;AESCAN;AE | PNEUMONIA;2012-09-07 | CORE-000022 | At least one of the Seriousness criteria (AESCAN, AESCONG, AESDISAB, A |
| 121 | AETERM;AESTDTC;AESER;AESCAN;AE | SUDDEN DEATH;2013-01 | CORE-000022 | At least one of the Seriousness criteria (AESCAN, AESCONG, AESDISAB, A |
| 312 | AETERM;AESTDTC;AESER;AESCAN;AE | TRANSIENT ISCHAEMIC  | CORE-000022 | At least one of the Seriousness criteria (AESCAN, AESCONG, AESDISAB, A |
| 409 | AETERM;AESTDTC;AESER;AESCAN;AE | COMPLETED SUICIDE;20 | CORE-000022 | At least one of the Seriousness criteria (AESCAN, AESCONG, AESDISAB, A |

</details>


### CM

Report: `core-report-SDTM.json`

- **Total issues**: 7594
- **Unique rules**: 6

**Issues by rule:**

- **CORE-000701** (7510): EPOCH is missing for clinical subject-level observation.
- **CORE-000093** (80): Missing value for CMDOSU, when CMDOSE, CMDOSTXT or CMDOSTOT is provided
- **CORE-000321** (1): Study Day of Visit/Collection/Exam (CMDY) variable is missing when Date/Time of Collection (CMDTC) is present.
- **CORE-000793** (1): Collection study day (CMDY) is missing when date/time of collection (CMDTC) is populated.
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
| 2391 | CMDOSE;CMDOSTXT;CMDOSTOT;CMDOS | 1.0;Not in dataset;N | CORE-000093 | Missing value for CMDOSU, when CMDOSE, CMDOSTXT or CMDOSTOT is provide |
| 2392 | CMDOSE;CMDOSTXT;CMDOSTOT;CMDOS | 1.0;Not in dataset;N | CORE-000093 | Missing value for CMDOSU, when CMDOSE, CMDOSTXT or CMDOSTOT is provide |
| 2393 | CMDOSE;CMDOSTXT;CMDOSTOT;CMDOS | 1.0;Not in dataset;N | CORE-000093 | Missing value for CMDOSU, when CMDOSE, CMDOSTXT or CMDOSTOT is provide |
| 2394 | CMDOSE;CMDOSTXT;CMDOSTOT;CMDOS | 1.0;Not in dataset;N | CORE-000093 | Missing value for CMDOSU, when CMDOSE, CMDOSTXT or CMDOSTOT is provide |
| 2395 | CMDOSE;CMDOSTXT;CMDOSTOT;CMDOS | 1.0;Not in dataset;N | CORE-000093 | Missing value for CMDOSU, when CMDOSE, CMDOSTXT or CMDOSTOT is provide |

</details>


### DM

Report: `core-report-SDTM.json`

- **Total issues**: 339
- **Unique rules**: 11

**Issues by rule:**

- **CORE-000047** (52): ARM value in DM dataset is not among the values of ARM variable in TA dataset. This is allowed only in a multistage study with incomplete ARM assignment. Please confirm if your study is a multistage assignment study
- **CORE-000115** (52): ARM cannot be equal to 'Screen Failure', 'Not Assigned', 'Unplanned Treatment' or 'Not Treated'.
- **CORE-000191** (52): RFENDTC is missing when ARM is provided.
- **CORE-000208** (52): ACTARMCD is not in TA.ARMCD
- **CORE-000209** (52): ACTARM value in DM dataset is not among the values of ARM variable in the TA dataset. This is allowed only in a multistage study with incomplete ARM assignment. Please confirm if your study is a multistage assignment study.
- **CORE-000210** (52): ARMCD is not present in TA.ARMCD
- **CORE-000655** (12): Values between ARMCD and ACTARMCD are not matching
- **CORE-000656** (12): Values between ARM and ACTARM are not matching
- **CORE-000334** (1): At least one expected variable is missing from dataset
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
| 7 | ARM | Screen Failure | CORE-000047 | ARM value in DM dataset is not among the values of ARM variable in TA  |
| 14 | ARM | Screen Failure | CORE-000047 | ARM value in DM dataset is not among the values of ARM variable in TA  |
| 18 | ARM | Screen Failure | CORE-000047 | ARM value in DM dataset is not among the values of ARM variable in TA  |
| 19 | ARM | Screen Failure | CORE-000047 | ARM value in DM dataset is not among the values of ARM variable in TA  |
| 28 | ARM | Screen Failure | CORE-000047 | ARM value in DM dataset is not among the values of ARM variable in TA  |

</details>


### DS

Report: `core-report-SDTM.json`

- **Total issues**: 659
- **Unique rules**: 7

**Issues by rule:**

- **CORE-000701** (596): EPOCH is missing for clinical subject-level observation.
- **CORE-000867** (58): Text variable contains leading spaces.
- **CORE-000321** (1): Study Day of Visit/Collection/Exam (DSDY) variable is missing when Date/Time of Collection (DSDTC) is present.
- **CORE-000334** (1): At least one expected variable is missing from dataset
- **CORE-000793** (1): Collection study day (DSDY) is missing when date/time of collection (DSDTC) is populated.
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
|  | DSDTC | 2014-07-02 | CORE-000321 | Study Day of Visit/Collection/Exam (DSDY) variable is missing when Dat |
|  | $dataset_variables;$expected_v | ['STUDYID', 'DOMAIN' | CORE-000334 | At least one expected variable is missing from dataset |
| 1 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |
| 2 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |
| 3 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |

</details>


### EX

Report: `core-report-SDTM.json`

- **Total issues**: 593
- **Unique rules**: 3

**Issues by rule:**

- **CORE-000701** (591): EPOCH is missing for clinical subject-level observation.
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
| 1 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |
| 2 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |
| 3 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |
| 4 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |
| 5 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |

</details>


### LB

Report: `core-report-SDTM.json`

- **Total issues**: 65195
- **Unique rules**: 10

**Issues by rule:**

- **CORE-000701** (59580): EPOCH is missing for clinical subject-level observation.
- **CORE-000542** (5568): LBSTRESC is numeric but LBSTRESN is not populated or not equal to LBSTRESC.
- **CORE-000168** (20): VISITNUM is not among VISITNUM in SV domain.
- **CORE-000289** (6): LBORRES is not a continuous measurement but LBORNRHI is not empty.
- **CORE-000290** (6): LBORRES is not a continuous measurement but LBORNRLO is not empty.
- **CORE-000298** (6): LBORRES is not a continuous measurment but LBSTNRLO is not empty.
- **CORE-000299** (6): LBORRES is not a continuous measurement but LBSTNRHI is not empty.
- **CORE-000334** (1): At least one expected variable is missing from dataset
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
| 3434 | VISITNUM | 9.299999999999999 | CORE-000168 | VISITNUM is not among VISITNUM in SV domain. |
| 3511 | VISITNUM | 9.299999999999999 | CORE-000168 | VISITNUM is not among VISITNUM in SV domain. |
| 3578 | VISITNUM | 9.299999999999999 | CORE-000168 | VISITNUM is not among VISITNUM in SV domain. |
| 3625 | VISITNUM | 9.299999999999999 | CORE-000168 | VISITNUM is not among VISITNUM in SV domain. |
| 3643 | VISITNUM | 9.299999999999999 | CORE-000168 | VISITNUM is not among VISITNUM in SV domain. |

</details>


### MH

Report: `core-report-SDTM.json`

- **Total issues**: 1823
- **Unique rules**: 5

**Issues by rule:**

- **CORE-000264** (1818): Primary analysis used but MHBODSYS and MHSOC are not equal
- **CORE-000236** (2): MHSTDTC ^= null and MHSTDTC is on or after the DM.RFSTDTC. The medical history dataset should include the subject's prior history at the start of the trial.
- **CORE-000328** (1): The Study Day of Start of Observation (MHSTDY) is not present in the dataset when Start Date/Time of Observation (MHSTDTC) is present.
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
| 110 | MHSTDTC;RFSTDTC | 2012;2012-09-07 | CORE-000236 | MHSTDTC ^= null and MHSTDTC is on or after the DM.RFSTDTC. The medical |
| 1554 | MHSTDTC;RFSTDTC | 2013-06;2013-06-08 | CORE-000236 | MHSTDTC ^= null and MHSTDTC is on or after the DM.RFSTDTC. The medical |
| 1 | MHTERM;MHBODSYS;MHSOC | ALZHEIMER'S DISEASE; | CORE-000264 | Primary analysis used but MHBODSYS and MHSOC are not equal |
| 2 | MHTERM;MHBODSYS;MHSOC | VERBATIM_0135;CARDIA | CORE-000264 | Primary analysis used but MHBODSYS and MHSOC are not equal |
| 3 | MHTERM;MHBODSYS;MHSOC | VERBATIM_0140;SURGIC | CORE-000264 | Primary analysis used but MHBODSYS and MHSOC are not equal |

</details>


### QS

Report: `core-report-SDTM.json`

- **Total issues**: 121807
- **Unique rules**: 6

**Issues by rule:**

- **CORE-000701** (121749): EPOCH is missing for clinical subject-level observation.
- **CORE-000200** (25): QSORRES cannot be null when QSSTAT is null or QSDRVFL not equal to 'Y'
- **CORE-000542** (24): QSSTRESC is numeric but QSSTRESN is not populated or not equal to QSSTRESC.
- **CORE-000643** (7): BLFL is set to "Y", but no value for STRESC is provided
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
| 2715 | QSSTAT;QSDRVFL;QSORRES | Not in dataset;null; | CORE-000200 | QSORRES cannot be null when QSSTAT is null or QSDRVFL not equal to 'Y' |
| 23380 | QSSTAT;QSDRVFL;QSORRES | Not in dataset;null; | CORE-000200 | QSORRES cannot be null when QSSTAT is null or QSDRVFL not equal to 'Y' |
| 32064 | QSSTAT;QSDRVFL;QSORRES | Not in dataset;null; | CORE-000200 | QSORRES cannot be null when QSSTAT is null or QSDRVFL not equal to 'Y' |
| 40438 | QSSTAT;QSDRVFL;QSORRES | Not in dataset;null; | CORE-000200 | QSORRES cannot be null when QSSTAT is null or QSDRVFL not equal to 'Y' |
| 46336 | QSSTAT;QSDRVFL;QSORRES | Not in dataset;null; | CORE-000200 | QSORRES cannot be null when QSSTAT is null or QSDRVFL not equal to 'Y' |

</details>


### RELREC

Report: `core-report-SDTM.json`

- **Total issues**: 236
- **Unique rules**: 3

**Issues by rule:**

- **CORE-000867** (234): Text variable contains leading spaces.
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
| 1 | variable_value;variable_name | 2;IDVARVAL | CORE-000867 | Text variable contains leading spaces. |
| 2 | variable_value;variable_name | 4;IDVARVAL | CORE-000867 | Text variable contains leading spaces. |
| 3 | variable_value;variable_name | 7;IDVARVAL | CORE-000867 | Text variable contains leading spaces. |
| 4 | variable_value;variable_name | 7;IDVARVAL | CORE-000867 | Text variable contains leading spaces. |
| 5 | variable_value;variable_name | 6;IDVARVAL | CORE-000867 | Text variable contains leading spaces. |

</details>


### SC

Report: `core-report-SDTM.json`

- **Total issues**: 259
- **Unique rules**: 4

**Issues by rule:**

- **CORE-000701** (254): EPOCH is missing for clinical subject-level observation.
- **CORE-000732** (3): SCSTRESC is not numeric but SCSTRESN is not empty
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
| 1 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |
| 2 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |
| 3 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |
| 4 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |
| 5 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |

</details>


### SE

Report: `core-report-SDTM.json`

- **Total issues**: 4
- **Unique rules**: 4

**Issues by rule:**

- **CORE-000328** (1): The Study Day of Start of Observation (SESTDY) is not present in the dataset when Start Date/Time of Observation (SESTDTC) is present.
- **CORE-000776** (1): Study Day of End of Observation (SEENDY) variable is missing when End Date/Time of Observation (SEENDTC) is present.
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
|  | SESTDTC | 2013-12-26 | CORE-000328 | The Study Day of Start of Observation (SESTDY) is not present in the d |
|  | SEENDTC | 2014-01-02 | CORE-000776 | Study Day of End of Observation (SEENDY) variable is missing when End  |
|  |  | Failed to build data | CORE-000929 | rule evaluation error - evaluation dataset failed to build - Error occ |
|  |  | Failed to build data | CORE-001081 | rule evaluation error - evaluation dataset failed to build - Error occ |

</details>


### SUPPAE

Report: `core-report-SDTM.json`

- **Total issues**: 3
- **Unique rules**: 3

**Issues by rule:**

- **CORE-000712** (1): rule evaluation error - operation failed
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
|  |  | Failed to execute ru | CORE-000712 | rule evaluation error - operation failed - Error occurred during opera |
|  |  | Failed to build data | CORE-000929 | rule evaluation error - evaluation dataset failed to build - Error occ |
|  |  | Failed to build data | CORE-001081 | rule evaluation error - evaluation dataset failed to build - Error occ |

</details>


### SUPPDM

Report: `core-report-SDTM.json`

- **Total issues**: 966
- **Unique rules**: 4

**Issues by rule:**

- **CORE-000211** (963): Population flag is present in SUPPDM
- **CORE-000712** (1): rule evaluation error - operation failed
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
| 1 | QNAM | COMPLT16 | CORE-000211 | Population flag is present in SUPPDM |
| 2 | QNAM | COMPLT24 | CORE-000211 | Population flag is present in SUPPDM |
| 3 | QNAM | COMPLT8 | CORE-000211 | Population flag is present in SUPPDM |
| 5 | QNAM | ITT | CORE-000211 | Population flag is present in SUPPDM |
| 6 | QNAM | SAFETY | CORE-000211 | Population flag is present in SUPPDM |

</details>


### SUPPDS

Report: `core-report-SDTM.json`

- **Total issues**: 3
- **Unique rules**: 3

**Issues by rule:**

- **CORE-000712** (1): rule evaluation error - operation failed
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
|  |  | Failed to execute ru | CORE-000712 | rule evaluation error - operation failed - Error occurred during opera |
|  |  | Failed to build data | CORE-000929 | rule evaluation error - evaluation dataset failed to build - Error occ |
|  |  | Failed to build data | CORE-001081 | rule evaluation error - evaluation dataset failed to build - Error occ |

</details>


### SUPPLB

Report: `core-report-SDTM.json`

- **Total issues**: 64406
- **Unique rules**: 4

**Issues by rule:**

- **CORE-000867** (64403): Text variable contains leading spaces.
- **CORE-000712** (1): rule evaluation error - operation failed
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
|  |  | Failed to execute ru | CORE-000712 | rule evaluation error - operation failed - Error occurred during opera |
| 1 | variable_value;variable_name | 1;IDVARVAL | CORE-000867 | Text variable contains leading spaces. |
| 2 | variable_value;variable_name | 2;IDVARVAL | CORE-000867 | Text variable contains leading spaces. |
| 3 | variable_value;variable_name | 3;IDVARVAL | CORE-000867 | Text variable contains leading spaces. |
| 4 | variable_value;variable_name | 5;IDVARVAL | CORE-000867 | Text variable contains leading spaces. |

</details>


### SV

Report: `core-report-SDTM.json`

- **Total issues**: 248
- **Unique rules**: 6

**Issues by rule:**

- **CORE-000333** (122): SVUPDES is not populated or does not exist, but the VISIT does not equal a VISIT present in TV
- **CORE-000842** (122): SVUPDES is not populated or does not exist, but the VISITNUM does not equal a VISITNUM present in TV
- **CORE-000328** (1): The Study Day of Start of Observation (SVSTDY) is not present in the dataset when Start Date/Time of Observation (SVSTDTC) is present.
- **CORE-000776** (1): Study Day of End of Observation (SVENDY) variable is missing when End Date/Time of Observation (SVENDTC) is present.
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
|  | SVSTDTC | 2013-12-26 | CORE-000328 | The Study Day of Start of Observation (SVSTDY) is not present in the d |
| 23 | SVUPDES;VISIT | Not in dataset;UNSCH | CORE-000333 | SVUPDES is not populated or does not exist, but the VISIT does not equ |
| 75 | SVUPDES;VISIT | Not in dataset;UNSCH | CORE-000333 | SVUPDES is not populated or does not exist, but the VISIT does not equ |
| 107 | SVUPDES;VISIT | Not in dataset;UNSCH | CORE-000333 | SVUPDES is not populated or does not exist, but the VISIT does not equ |
| 201 | SVUPDES;VISIT | Not in dataset;UNSCH | CORE-000333 | SVUPDES is not populated or does not exist, but the VISIT does not equ |

</details>


### TA

Report: `core-report-SDTM.json`

- **Total issues**: 2
- **Unique rules**: 2

**Issues by rule:**

- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
|  |  | Failed to build data | CORE-000929 | rule evaluation error - evaluation dataset failed to build - Error occ |
|  |  | Failed to build data | CORE-001081 | rule evaluation error - evaluation dataset failed to build - Error occ |

</details>


### TE

Report: `core-report-SDTM.json`

- **Total issues**: 2
- **Unique rules**: 2

**Issues by rule:**

- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
|  |  | Failed to build data | CORE-000929 | rule evaluation error - evaluation dataset failed to build - Error occ |
|  |  | Failed to build data | CORE-001081 | rule evaluation error - evaluation dataset failed to build - Error occ |

</details>


### TI

Report: `core-report-SDTM.json`

- **Total issues**: 2
- **Unique rules**: 2

**Issues by rule:**

- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
|  |  | Failed to build data | CORE-000929 | rule evaluation error - evaluation dataset failed to build - Error occ |
|  |  | Failed to build data | CORE-001081 | rule evaluation error - evaluation dataset failed to build - Error occ |

</details>


### TV

Report: `core-report-SDTM.json`

- **Total issues**: 2
- **Unique rules**: 2

**Issues by rule:**

- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
|  |  | Failed to build data | CORE-000929 | rule evaluation error - evaluation dataset failed to build - Error occ |
|  |  | Failed to build data | CORE-001081 | rule evaluation error - evaluation dataset failed to build - Error occ |

</details>


### VS

Report: `core-report-SDTM.json`

- **Total issues**: 31931
- **Unique rules**: 6

**Issues by rule:**

- **CORE-000701** (29643): EPOCH is missing for clinical subject-level observation.
- **CORE-000914** (2277): There are multiple records per assigned baseline flag (VSBLFL).
- **CORE-000774** (8): VSSTAT = NOT DONE, but VSREASND is missing.
- **CORE-000334** (1): At least one expected variable is missing from dataset
- **CORE-000929** (1): rule evaluation error - evaluation dataset failed to build
- **CORE-001081** (1): rule evaluation error - evaluation dataset failed to build

<details><summary>Sample records</summary>

| Record | Variables | Values | Rule | Message |
|--------|-----------|--------|------|---------|
|  | $dataset_variables;$expected_v | ['STUDYID', 'DOMAIN' | CORE-000334 | At least one expected variable is missing from dataset |
| 1 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |
| 2 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |
| 3 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |
| 4 | EPOCH | Not in dataset | CORE-000701 | EPOCH is missing for clinical subject-level observation. |

</details>


