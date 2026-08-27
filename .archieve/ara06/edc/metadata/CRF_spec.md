# ARA06 (NCT00837434) — CRF Specification

Derived from the user-provided protocol **ARA06 Version 3.0 (03 Dec 2010)**,
Table 6.5 *Schedule of Evaluations: Clinical Study* (p.69), plus the
ClinicalTrials.gov results record. CDISC-style domains; one CSV per form,
prefixed `ARA06_CRF_`.

## Visit grid (clinical study)

| Key | Visit | Study day | Type | Source |
|---|---|---|---|---|
| SCRN | Screening | −14 | eligibility, labs, clinical | Protocol Table 6.5 |
| V2 | Baseline / Treatment Initiation (Day 0) | 1 | clinical + B/T-cell + labs; first anti-TNF dose | Protocol 6.7.4 |
| V3 | Week 4 | 28 | phone (AE + medication) | Protocol 6.7.6 |
| V4 | Week 8 | 56 | bimonthly safety labs (CBC, chem/LFT) | Protocol 6.7.8 |
| V5 | Week 12 | 84 | **PRIMARY endpoint**; full clinical + B/T-cell + labs | Protocol 6.7.9, 3.2.3 |
| V6 | Week 16 | 112 | bimonthly safety labs | Protocol 6.7.11 |
| V7 | Week 20 | 140 | phone (AE + medication) | Protocol 6.7.12 |
| V8 | Week 24 | 168 | End of Study; full clinical + B/T-cell + labs | Protocol 6.7.13, 3.4.1 |

`ADMIN_CENSOR_DAY = 168` (Week 24, study completion per protocol 3.4.1). The
optional mechanistic sub-studies (tonsil/synovial biopsy, B-cell memory kinetic,
vaccine response) are **not** modeled — only the main clinical-study SoA, whose
endpoints have posted results.

## Forms

| Form (CSV) | Collected at | Variables | Source |
|---|---|---|---|
| **DM** Demographics | Screening | USUBJID, SITEID, ARMCD (ETN/ADA), ARM, AGE, SEX, RACE, ETHNIC, COUNTRY, WEIGHT, RFSTDTC | Protocol 6.7.1; ctgov baseline |
| **MH** Disease history / stratifiers | Screening | MHTERM, RADURYR (RA duration), RFCCPPOS (RF/anti-CCP — randomization stratifier), MTXDOSE/MTXDOSU, DAS28_BL, HAQDI_BL | Protocol 4.1, 3.1.2 |
| **DA** Disease activity (ACR/DAS28 components) | SCRN, V2, V5, V8 | TJC28, SJC28, PTGLOBAL (VAS), PHYSGLOBAL (VAS, blinded), PAINVAS, HAQDI, CRP, DAS28CRP | Protocol 6.2, App. A–G |
| **BC** B-cell flow cytometry | V2, V5, V8 | MEMSWPCT (% CD27+ switched memory B cells) — **PRIMARY mechanistic node** | Protocol 3.2.3, 6.4.2 |
| **LB_HEM** Hematology (CBC) | SCRN, V2, V4, V6, V8 | WBC, ANC, ALC, HGB, PLT | Protocol 6.1, 5.3.4.1 |
| **LB_CHEM** Chemistry / LFT | SCRN, V2, V4, V6, V8 | AST, ALT, CREAT, CRP | Protocol 6.1, 5.3.4.2 |
| **EX** Exposure | every visit | EXTRT (ETANERCEPT/ADALIMUMAB + background METHOTREXATE), EXDOSE, EXDOSU, EXROUTE, EXDOSFRQ (QW/Q2W), EXSTDTC, EXACN | Protocol 5.2 |
| **AE** Adverse events | each visit | AETERM, AEDECOD, AEBODSYS (SOC), AESEV, AETOXGR (NCI-CTCAE), AEREL, AEACN, AESER, AEOUT | Protocol 7 (NCI-CTCAE v3.0) |
| **DS** Disposition | EOT | DSDECOD (COMPLETED/DISCONTINUED), DSTERM (reason), DSSTDY | Protocol 3.4 |
| **RE** Endpoint summary | per patient | MEMSW_WK12, DAS28RESP_WK{12,24}, ACR20_WK{12,24}, ACR50_WK{12,24}, SERIOUS_AE, DISPOSITION | Endpoint definitions |

## Suppression notes (skill false-positive traps)

- **No standalone urinalysis form.** The ARA06 clinical-study SoA (Table 6.5)
  lists no separate urinalysis assessment, so `LB_UA` is not created (unlike the
  renal-focused RAVE build).
- **Seriousness is the `AESER` column on the AE form.** No separate SAE form —
  the protocol records SAEs on the same AE eCRF (protocol 7.3.5).
- **Optional sub-study forms (tonsil/synovial biopsy histology, vaccine titers,
  T-cell panel, glucocorticoid log) are omitted** — they are optional, have no
  posted per-arm results, and are out of scope for the digital twin.
