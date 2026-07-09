# EIDD-2801-1001-UK — Synthetic SDTM + ADaM (2020-001407-17-00)

Protocol is available at https://cdn.clinicaltrials.gov/large-docs/19/NCT04392219/Prot_000.pdf.

A three-stage clinical-data environment that generates realistic **SDTM** and
**ADaM** datasets for a Phase 1, single ascending-dose pharmacokinetic study of
**molnupiravir (EIDD-2801 / MK-4482)** in healthy volunteers.

The study is driven by parsed electronic-CRF templates (no published CSR
targets); the pipeline is organized to mirror the reference environment
`clinical-data-terminal-dev/src/cdt/environments/cdiscpilot1` — the same
`edc/ → sdtm/ → adam/` layering used by the `ara06`, `cath`, and `rave`
submissions.

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│ edc/     COLLECTION LAYER                                           │
│   crf_json/*.json           63 parsed eCRF templates (spec)         │
│   generators/build_all.R    fills every form per subject ->         │
│   forms/<form>.csv          raw EDC extract (1 row / filled record) │
│   forms/subjects.csv        subject registration + reference date    │
│   lookups/visit_schedule.csv                                        │
└───────────────────────────────────────────────────────────────────┘
                              ↓  sdtm/derive_<domain>.R
┌───────────────────────────────────────────────────────────────────┐
│ sdtm/    TABULATION LAYER                                           │
│   common.R + derive_*.R     raw forms -> SDTM domains               │
│   run_all.R                 -> sdtm-derived/*.csv                   │
│   export_conformant.py      -> sdtm-derived/xpt/*.xpt + define.xml  │
└───────────────────────────────────────────────────────────────────┘
                              ↓  adam/ad_<dataset>.R (admiral)
┌───────────────────────────────────────────────────────────────────┐
│ adam/    ANALYSIS LAYER                                             │
│   00_setup.R + ad_*.R       SDTM XPT -> ADaM datasets               │
│   run_all.R                 -> adam-derived/*.{rds,csv}             │
│   export_xpt.R              -> adam-derived/_xpt/*.xpt              │
└───────────────────────────────────────────────────────────────────┘
                              ↓  TLF/<task>/{data_setup.R, solve.R} (tern / rtables / ggplot2)
┌───────────────────────────────────────────────────────────────────┐
│ TLF/     REPORTING LAYER                                            │
│   tlf_data.R + <task>/       ADaM -> tables / listings / figures    │
│   run_all.R                 -> tlf-derived/<task>/*.{txt,rds,png}   │
└───────────────────────────────────────────────────────────────────┘
```

## Quick start

```bash
cd EIDD-2801
Rscript run.R                    # 100 subjects, seed 0, through ADaM
Rscript run.R --n 250 --seed 42
Rscript run.R --stage sdtm       # stop after the SDTM stage
Rscript run.R --stage tlf        # also render the TLF outputs
```

Or run each stage directly:

```bash
Rscript edc/generators/build_all.R --n 100 --seed 0   # -> edc/forms/
cd sdtm && Rscript run_all.R && python3 export_conformant.py
cd ../adam && Rscript run_all.R && Rscript export_xpt.R
cd ../TLF && Rscript run_all.R                         # -> tlf-output/
```

## Project structure

```
EIDD-2801/
├── run.R                       # orchestrates edc -> sdtm -> adam
├── README.md
├── docs/implementation.md      # data-flow + porting notes
├── edc/                        # COLLECTION
│   ├── crf_json/               #   63 eCRF templates (input spec)
│   ├── generators/             #   sim_config.R, sim_core.R, build_all.R
│   ├── forms/                  #   raw EDC form CSVs + subjects.csv (generated)
│   └── lookups/visit_schedule.csv
├── sdtm/                       # TABULATION
│   ├── common.R, derive_*.R, run_all.R
│   ├── export_conformant.py, GUIDE.md
│   └── sdtm-derived/           #   *.csv + xpt/*.xpt + define.xml (generated)
├── adam/                       # ANALYSIS
│   ├── 00_setup.R, ad_*.R, run_all.R
│   ├── export_xpt.R, GUIDE.md
│   └── adam-derived/           #   *.{rds,csv} + _xpt/*.xpt (generated)
└── TLF/                        # REPORTING (one folder per output, like cdiscpilot1/tlf)
    ├── tlf_data.R, run_all.R, GUIDE.md
    ├── table-vst01/            #   task.json + data_setup.R + solve.R
    └── tlf-derived/<task>/     #   result1.{txt,rds} or .png (generated)
```

## Study design

| Parameter | Value |
|-----------|-------|
| **Compound** | EIDD-2801 / molnupiravir (MK-4482) |
| **Phase / design** | Phase 1, single ascending dose, healthy volunteers |
| **Population** | Healthy adults 18–55 |
| **Dose levels** | 50 / 100 / 200 / 400 / 800 mg (one level per run) |
| **Formulation** | Capsule or Solution (study-fixed per run) |
| **Route** | Oral |
| **Visits** | Day -1 (admission), Day 1 (dosing), Days 2/3/4/9, Day 15 / EOS |

## SDTM domains

| Domain | Description | Source CRF forms |
|--------|-------------|------------------|
| DM | Demographics (1/subject) | subjects + study-drug + date_of_visit |
| SV | Subject Visits | date_of_visit |
| IE | I/E criteria not met | inclusion_exclusion_criteria |
| EX | Exposure | study_drug_placebo_administration |
| VS | Vital Signs | vital_sign(s) |
| EG | ECG Test Results | 12_lead_ecg |
| LB | Laboratory | hematology, chemistry, urinalysis, cotinine, alcohol, drugs_of_abuse, pregnancy |
| PC | PK / biospecimen collection | pk_blood_sample, pk_urine_sample, pbmc_collection |
| PE | Physical Examination | physical_examination, symptom_directed_physical_exam |
| ML | Meal Data | meal_detail |

## ADaM datasets

| Dataset | Description | Source |
|---------|-------------|--------|
| ADSL | Subject-Level Analysis Dataset | DM + EX |
| ADVS | Vital Signs Analysis Dataset | VS |
| ADEG | ECG Analysis Dataset | EG |
| ADLB | Laboratory Analysis Dataset | LB |

Derived with [admiral](https://pharmaverse.github.io/admiral/). No ADPC (the PC
domain is a biospecimen-collection log with no assayed concentrations); no
ADAE/ADCM/ADMH (no AE/CM/MH source in this single-dose design).

## TLF (tables, listings, figures)

Reporting outputs generated from the ADaM with `tern` / `rtables` (tables &
listings) and `ggplot2` (figures), organized like the `cdiscpilot1/tlf/` catalog:
one folder per output (`<task>/{task.json, data_setup.R, solve.R}`) that
`TLF/run_all.R` discovers and renders to `tlf-derived/<task>/`. A **starter kit**
— one safety table is implemented; see `TLF/GUIDE.md` for the convention to add more.

| Task | Type | Output |
|------|------|--------|
| `table-vst01` | Safety table | Vital Sign Results and Change from Baseline by Visit (Safety Population), from ADVS |

Single-dose Phase 1 PK study with no formal efficacy endpoint, so the catalogue
is safety/PK-oriented.

## Dependencies

- R ≥ 4.0 with `dplyr`, `tidyr`, `readr`, `stringr`, `jsonlite`, `admiral`,
  `haven`, `lubridate`; plus `tern`, `rtables`, `rlistings`, `ggplot2` for the TLF stage
- Python ≥ 3.10 with `pandas`, `pyreadstat` (SDTM XPT/Define-XML export via the
  shared `cdt.environments.sdtm_export`)

## Provenance

Reformulated from the original single-shot R simulator (which mapped CRF cases
straight to SDTM) into the layered `edc/ → sdtm/ → adam/` environment structure
of `cdiscpilot1`. The CRF form-filler (`edc/generators/`) and the domain mappings
(now `sdtm/derive_*.R`) are the same logic, re-split across the collection and
tabulation stages.
