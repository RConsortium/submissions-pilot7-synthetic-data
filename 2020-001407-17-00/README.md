# EIDD-2801-1001-UK Clinical Trial Simulation (2020-001407-17-00)

A CRF-JSON-driven simulation framework that generates realistic SDTM data for a
Phase 1, single-dose pharmacokinetic study of **molnupiravir (EIDD-2801 /
MK-4482)** in healthy volunteers.

Unlike `cdiscpilot1_simulation` (which calibrates to *published* result tables),
this study has no published efficacy/CSR targets — the simulation is driven by
the **parsed electronic CRF templates** plus clinical reference ranges.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      LAYER 1: CRF TEMPLATES                       │
│   63 parsed eCRF form schemas (simulator/crf_json/*.json)         │
│   field name + controlled-term lists per visit-form               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       LAYER 2: SIMULATOR                          │
│   (a) generic engine fills every CRF form per patient             │
│       -> ground-truth cases  (data/cases/<P###>/*.json)           │
│   (b) per-domain modules map filled cases -> SDTM                 │
│       -> data/sdtm/*.{csv,json}                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
cd 2020-001407-17-00
Rscript run.R                  # 100 patients, seed 0
Rscript run.R --n 250 --seed 42
```

## Project Structure

```
2020-001407-17-00/
├── run.R                       # Pipeline entry point (--n, --seed)
├── README.md
├── docs/
│   └── implementation.md       # Port notes, data flow, fidelity caveats
├── data/
│   ├── cases/<P###>/*.json     # Filled CRF ground truth (intermediate)
│   └── sdtm/                    # SDTM domain tables (.csv + .json)
└── simulator/
    ├── sim_config.R            # Study constants, visit schedule, reference ranges
    ├── sim_core.R              # Shared engine: profiles + generic CRF filler
    │                           #   + value generators + SDTM helpers
    ├── crf_json/               # 63 CRF templates (input spec)
    ├── forms/                  # One module per SDTM domain / form category
    │   ├── sim_demographics.R  #   DM
    │   ├── sim_eligibility.R   #   IE
    │   ├── sim_visits.R        #   SV
    │   ├── sim_exposure.R      #   EX
    │   ├── sim_vitals.R        #   VS
    │   ├── sim_ecg.R           #   EG
    │   ├── sim_labs.R          #   LB
    │   ├── sim_pk.R            #   PC
    │   ├── sim_physical_exam.R #   PE
    │   └── sim_meals.R         #   ML
    └── run_simulator.R         # Driver: profiles -> fill cases -> map domains
```

## Study Design

| Parameter | Value |
|-----------|-------|
| **Compound** | EIDD-2801 / molnupiravir (MK-4482) |
| **Phase / Design** | Phase 1, single ascending dose, healthy volunteers |
| **Population** | Healthy adults 18–55 |
| **Dose levels** | 50 / 100 / 200 / 400 / 800 mg (one level per run) |
| **Formulation** | Capsule or Solution (study-fixed per run) |
| **Route** | Oral |
| **Visits** | Day -1 (admission), Day 1 (dosing), Days 2/3/4/9, Day 15 / EOS |

## SDTM Domains

| Domain | Description | Source CRF forms |
|--------|-------------|------------------|
| DM | Demographics (1/subject) | derived (profile + dosing) |
| SV | Subject Visits | date_of_visit |
| IE | I/E criteria not met | inclusion_exclusion_criteria |
| EX | Exposure | study_drug_placebo_administration |
| VS | Vital Signs | vital_sign(s) |
| EG | ECG Test Results | 12_lead_ecg, continuous_12_lead_ecg |
| LB | Laboratory | hematology, chemistry, urinalysis, cotinine, alcohol, drugs_of_abuse, pregnancy, fsh |
| PC | PK / biospecimen collection | pk_blood_sample, pk_urine_sample, pbmc_collection |
| PE | Physical Examination | physical_examination, symptom_directed_physical_exam |
| ML | Meal Data | meal_detail |

SDTM conventions applied: `USUBJID = <STUDYID>-P###`, per-domain `--SEQ` in
chronological order, `--TESTCD`/`--TEST` pairs, `--ORRES`/`--ORRESU`/`--STRESN`,
ISO-8601 `--DTC`, study day `--DY` relative to dosing (no day 0), `VISITNUM`/`VISIT`.

## Adding a New Form Category

1. Drop `simulator/forms/sim_<domain>.R` exposing `<DOMAIN>_COLUMNS` and
   `build_<domain>(patient, cases)` (returns a list of named-list rows).
2. Add one line to the registry in `simulator/run_simulator.R`.

## Output

Every populated SDTM domain is written in both CSV and JSON to `data/sdtm/`.
Filled-CRF ground truth is written per patient to `data/cases/<P###>/`.

## Dependencies

- R >= 4.0
- `here` — project path management
- `jsonlite` — JSON read/write

## Provenance

Ported to R from the Python reference simulators
`simulate_patient_cases.py` + `cases_to_sdtm.py`
(clinical-data-terminal-dev, study 2020-001407-17-00), reorganized to mirror the
layering of `cdiscpilot1_simulation`.
