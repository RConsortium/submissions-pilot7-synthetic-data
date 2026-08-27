# CRF Schema — KEYNOTE-564

## Overview

This document defines the Case Report Form structure for the KEYNOTE-564 IPD simulator.
Visit schedule: Treatment visits every 3 weeks (17 cycles), imaging per protocol schedule.

---

## Forms x Visits x Variables

### DM — Demographics (Screening Visit)

| Variable | Type | Description |
|----------|------|-------------|
| SUBJID | char | Subject identifier (1–994) |
| AGE | num | Age at randomization (years) |
| SEX | char | M/F |
| RACE | char | WHITE, ASIAN, BLACK, OTHER |
| REGION | char | US, OTHER |
| ARM | char | PEMBROLIZUMAB, PLACEBO |
| RISK_CATEGORY | char | M0_INT_HIGH, M0_HIGH, M1_NED |
| ECOG_BL | int | Baseline ECOG PS (0, 1) |
| SARCOMATOID | int | Sarcomatoid features (0, 1) |
| PDL1_CPS | char | <1, >=1, MISSING |
| RANDDT | date | Randomization date (Day 1) |
| STRATUM | char | Combined stratification factor |

### EX — Exposure (Each Dosing Visit, Cycles 1–17)

| Variable | Type | Description |
|----------|------|-------------|
| SUBJID | char | Subject identifier |
| CYCLE | int | Cycle number (1–17) |
| EXSTDT | date | Dose administration date |
| EXDOSE | num | Dose administered (mg); 0 if held |
| EXDOSU | char | mg |
| EXROUTE | char | IV |
| DOSE_STATUS | char | GIVEN, HELD, DISCONTINUED |
| CUMULATIVE_DOSES | int | Running count of doses received |

### AE — Adverse Events (Any visit)

| Variable | Type | Description |
|----------|------|-------------|
| SUBJID | char | Subject identifier |
| AETERM | char | AE preferred term |
| AESTDT | date | AE start date (study day) |
| AEENDT | date | AE end date (study day) |
| AEGR | int | CTCAE grade (1–4) |
| AESER | int | Serious AE (0, 1) |
| AEREL | char | RELATED, NOT RELATED, POSSIBLY RELATED |
| AEACN | char | Action: NONE, DOSE_HELD, DOSE_REDUCED, DISCONTINUED |
| AECAT | char | Category: IMMUNE_MEDIATED, GENERAL, THYROID |
| AEOUT | char | Outcome: RESOLVED, ONGOING, FATAL |

### LB — Laboratory (Each Dosing Visit + selected follow-up)

| Variable | Type | Description |
|----------|------|-------------|
| SUBJID | char | Subject identifier |
| VISIT_DAY | int | Study day of lab draw |
| LBTEST | char | Test name (TSH, FT4) |
| LBORRES | num | Result in original units |
| LBORRESU | char | Units (mIU/L, ng/dL) |
| LBNRIND | char | Normal range indicator: NORMAL, LOW, HIGH |
| LBBLFL | char | Baseline flag (Y/N) |

### TU — Tumor Assessment (Imaging Visits)

| Variable | Type | Description |
|----------|------|-------------|
| SUBJID | char | Subject identifier |
| VISIT_DAY | int | Study day of imaging |
| TUEVAL | char | Evaluator: INVESTIGATOR |
| TURESP | char | Response: NED, RECURRENCE_LOCAL, RECURRENCE_DISTANT |
| TULOC | char | Location of recurrence (if applicable) |

### RS — Disease Response (Imaging Visits)

| Variable | Type | Description |
|----------|------|-------------|
| SUBJID | char | Subject identifier |
| VISIT_DAY | int | Study day |
| RSEVAL | char | INVESTIGATOR |
| RSSTRESC | char | DFS status: DISEASE_FREE, RECURRED, DEAD |

### DS — Disposition (End of study)

| Variable | Type | Description |
|----------|------|-------------|
| SUBJID | char | Subject identifier |
| DSSTDT | date | Disposition date (study day) |
| DSDECOD | char | COMPLETED, ADVERSE_EVENT, WITHDREW_CONSENT, DEATH, LOST_TO_FU |
| DSCAT | char | TREATMENT, STUDY |
| DSSCAT | char | Subcategory detail |

---

## Visit Schedule

| Visit Type | Timing | Forms Collected |
|------------|--------|-----------------|
| Screening | Day -28 to -1 | DM |
| Cycle 1 Day 1 | Day 1 | EX, LB |
| Cycles 2–17 | q3w | EX, LB, AE |
| Imaging Y1 | q12w | TU, RS |
| Imaging Y2-4 | q16w | TU, RS |
| Imaging Y5+ | q24w | TU, RS |
| End of Treatment | Cycle 17 or early d/c | DS, EX |
| Follow-up | q12w post-treatment | TU, RS, DS |
| Survival follow-up | q12w | DS (vital status) |
