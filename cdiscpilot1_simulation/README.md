# CDISC Pilot 01 Clinical Trial Simulation

A 4-layer simulation framework for generating realistic SDTM/ADaM clinical trial data modeled after CDISC Pilot 01 (Xanomeline Transdermal Therapeutic System in Alzheimer's Disease).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        LAYER 1: TARGETS                         │
│  Published data from CDISC Pilot 01 + accuracy tier metadata    │
│  (CRITICAL ±5%, HIGH ±10%, MODERATE ±20%, LOW ±30%)            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      LAYER 2: SIMULATOR                         │
│  Generates SDTM datasets calibrated to targets                  │
│  (DM, SC, SV, EX, DS, AE, QS, LB, VS)                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        LAYER 3: MAPPER                          │
│  Derives ADaM datasets from SDTM                                │
│  (ADSL, ADQS, ADAE, ADLB, ADVS)                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        LAYER 4: SCORER                          │
│  Validates data consistency + compares metrics vs targets       │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
cd ~/keynote_simulation
Rscript run.R
```

Or with custom seed:
```bash
Rscript run.R --seed 42
```

## Project Structure

```
keynote_simulation/
├── targets/                    # Layer 1: Target outputs
│   ├── metadata.R             # Accuracy tier definitions
│   └── cdiscpilot01_targets.R # Published CDISC Pilot 01 values
├── simulator/                  # Layer 2: SDTM generation
│   ├── sim_config.R           # Simulation parameters
│   ├── sim_demographics.R     # DM, SC domains
│   ├── sim_visits.R           # SV domain
│   ├── sim_exposure.R         # EX domain (transdermal patches)
│   ├── sim_disposition.R      # DS domain
│   ├── sim_efficacy.R         # QS domain (ADAS-Cog, CIBIC+)
│   ├── sim_safety.R           # AE domain
│   ├── sim_labs.R             # LB domain
│   ├── sim_vitals.R           # VS domain
│   └── run_simulator.R        # Simulator entry point
├── mapper/                     # Layer 3: ADaM derivation
│   ├── map_adsl.R             # ADSL mapping
│   ├── map_adqs.R             # ADQS mapping (efficacy)
│   ├── map_adae.R             # ADAE mapping
│   ├── map_adlb.R             # ADLB mapping
│   ├── map_advs.R             # ADVS mapping
│   └── run_mapper.R           # Mapper entry point
├── scorer/                     # Layer 4: Validation & Scoring
│   ├── validate_data.R        # Data consistency checks
│   ├── calculate_metrics.R    # Metric calculation
│   └── run_scorer.R           # Scorer entry point
├── reference/
│   └── cdiscpilot01_TLFs/     # Reference TLF PDFs and index
├── docs/
│   └── implementation.md      # Detailed implementation docs
├── data/
│   ├── sdtm/                  # Generated SDTM datasets
│   └── adam/                  # Generated ADaM datasets
├── output/                    # Scoring results
└── run.R                      # Main pipeline script
```

## Study Design

**CDISC Pilot 01** - Xanomeline Transdermal Therapeutic System in Patients with Mild to Moderate Alzheimer's Disease

| Parameter | Value |
|-----------|-------|
| **Indication** | Mild to Moderate Alzheimer's Disease |
| **Population** | Elderly (≥50 years), MMSE 10-24 |
| **Sample Size** | N = 254 (randomized 1:1:1) |
| **Treatment Arms** | Placebo (N=86), Xanomeline Low 54mg (N=84), Xanomeline High 81mg (N=84) |
| **Administration** | Transdermal patch, once daily |
| **Duration** | 24 weeks treatment + 2 weeks follow-up |
| **Primary Endpoint** | ADAS-Cog(11) change from baseline at Week 24 |
| **Secondary Endpoint** | CIBIC+ at Week 24 |

## SDTM Domains

| Domain | Description | Records |
|--------|-------------|---------|
| DM | Demographics | 254 |
| SC | Subject Characteristics | ~1,300 |
| SV | Subject Visits | ~2,000 |
| EX | Exposure (Transdermal Patches) | ~2,500 |
| DS | Disposition | ~760 |
| AE | Adverse Events | ~1,200 |
| QS | Questionnaires (ADAS-Cog, CIBIC+) | ~3,000 |
| LB | Laboratory | ~7,600 |
| VS | Vital Signs | ~12,700 |

## ADaM Datasets

| Dataset | Description | Records |
|---------|-------------|---------|
| ADSL | Subject Level Analysis | 254 |
| ADQS | Questionnaire Analysis (Efficacy) | ~3,000 |
| ADAE | Adverse Event Analysis | ~1,200 |
| ADLB | Laboratory Analysis | ~7,600 |
| ADVS | Vital Signs Analysis | ~12,700 |

## Accuracy Tiers

| Tier | Tolerance | Categories |
|------|-----------|------------|
| **CRITICAL** | ±5% | Demographics, Primary efficacy (ADAS-Cog), Disposition, Application site AEs |
| **HIGH** | ±10% | Secondary efficacy (CIBIC+), Skin AEs, Exposure |
| **MODERATE** | ±20% | Overall safety rates, Other AEs |
| **LOW** | ±30% | Rare events, Subgroups |

## Key Metrics Scored

### Demographics (CRITICAL - ±5%)
- Age (mean, SD, age groups)
- Sex distribution
- Race distribution
- Baseline MMSE

### Primary Efficacy - ADAS-Cog(11) (CRITICAL - ±5%)
- Baseline scores by arm
- Week 24 scores by arm
- Change from baseline by arm

### Secondary Efficacy - CIBIC+ (HIGH - ±10%)
- Week 24 scores by arm

### Disposition (CRITICAL - ±5%)
- Completion rates by arm
- Discontinuation due to AE by arm

### Safety (MODERATE-CRITICAL)
- Any AE rates by arm
- Application site pruritus/erythema (CRITICAL)
- Dermatological AEs: Pruritus, Erythema, Rash (HIGH)
- Other AEs: Dizziness, Nausea, Syncope, Bradycardia (MODERATE)

## Data Validation

The scorer performs data consistency checks across 5 categories:

| Category | Examples |
|----------|----------|
| LOGICAL | Sample size ~254, Treatment arm balance (~84-86 per arm) |
| RANGE | Age 50-95, MMSE 10-24, CIBIC+ 1-7 |
| CLINICAL | Placebo completion > Active completion, ADAS-Cog worsening over time |
| CROSS_DATASET | All ADQS/ADAE subjects exist in ADSL |

## Output Files

All data is saved in both CSV and JSON formats:

**SDTM** (`data/sdtm/`)
```
dm.csv, dm.json, sc.csv, sc.json, sv.csv, sv.json,
ex.csv, ex.json, ds.csv, ds.json, ae.csv, ae.json,
qs.csv, qs.json, lb.csv, lb.json, vs.csv, vs.json
```

**ADaM** (`data/adam/`)
```
adsl.csv, adsl.json, adqs.csv, adqs.json,
adae.csv, adae.json, adlb.csv, adlb.json, advs.csv, advs.json
```

**Scoring Results** (`output/`)
```
score_details.csv, score_details.json    # Per-metric scores
score_summary.csv, score_summary.json    # Summary by tier
validation_details.csv, validation_details.json  # Validation checks
```

## Sample Results

```
======================================================================
OVERALL SUMMARY
======================================================================
Total metrics scored: 60
Total passed: 48 (80.0%)
  CRITICAL: 20/26 (76.9%)
  HIGH: 10/12 (83.3%)
  MODERATE: 12/15 (80.0%)
  LOW: 6/7 (85.7%)

DATA VALIDATION: 18/20 passed (90.0%)
======================================================================
```

## Key Clinical Patterns Simulated

### Efficacy
- **ADAS-Cog(11)**: Higher scores = worse cognition (0-70 range)
  - Baseline ~24 (mild-moderate AD)
  - Placebo shows worsening (+3-4 points at Week 24)
  - Active arms show stabilization or improvement (-2 to +1 points)

- **CIBIC+**: 1-7 scale (4 = no change, lower = improvement)
  - Placebo ~4.5 (slight worsening)
  - Active arms ~3.5-4.0 (improvement to stable)

### Disposition
- **High dropout in active arms** (~67% early termination)
- **Better completion in placebo** (~70%)
- Primary discontinuation reason: Adverse events (application site reactions)

### Safety
- **Application site reactions** dominant in active arms
  - Pruritus: Placebo ~5%, Active ~22%
  - Erythema: Placebo ~3%, Active ~15%
- **Cholinergic effects**: Nausea, dizziness, bradycardia in active arms
- Lower AE rates in placebo vs active arms

## Dependencies

- R >= 4.0
- `here` - Project path management
- `jsonlite` - JSON serialization

## Reference

**CDISC Pilot 01 Study**
- Indication: Mild to Moderate Alzheimer's Disease
- Drug: Xanomeline Transdermal Therapeutic System
- N = 254 (randomized 1:1:1)
- Treatment: Placebo vs Xanomeline Low (54mg/day) vs Xanomeline High (81mg/day)
- Primary endpoint: ADAS-Cog(11) change from baseline at Week 24
- Reference TLFs: Tables 14-1.01 through 14-7.04

## Future Directions

1. **Agent-Based Calibration**: Use AI agents to iteratively refine simulation parameters until target metrics are met
2. **Additional Endpoints**: Add NPI, ADCS-ADL, DAD assessments
3. **Visualizations**: Add efficacy plots, AE incidence charts
4. **Correlation Modeling**: Improve ADAS-Cog baseline/change correlation
