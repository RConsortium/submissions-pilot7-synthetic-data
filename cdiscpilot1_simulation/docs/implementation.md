# KEYNOTE-868 Clinical Trial Simulation - Implementation Details

## Overview

This project implements a 4-layer simulation framework for generating realistic SDTM/ADaM clinical trial data modeled after KEYNOTE-868 (pembrolizumab + chemotherapy in advanced endometrial carcinoma).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        LAYER 1: TARGETS                         │
│  Published data from KEYNOTE-868 + accuracy tier metadata       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      LAYER 2: SIMULATOR                         │
│  Generates SDTM datasets (DM, SC, EX, AE) calibrated to targets │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        LAYER 3: MAPPER                          │
│  Derives ADaM datasets (ADSL, ADTTE, ADAE, ADRS) from SDTM      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        LAYER 4: SCORER                          │
│  Compares simulated metrics vs targets by accuracy tier         │
└─────────────────────────────────────────────────────────────────┘
```

## Layer 1: Targets

### Files
- `targets/metadata.R` - Defines accuracy tiers and tolerance levels
- `targets/kn868_targets.R` - Published values from KEYNOTE-868

### Accuracy Tiers

| Tier | Tolerance | Categories |
|------|-----------|------------|
| **CRITICAL** | ±5% | Demographics, Primary efficacy (PFS HR) |
| **HIGH** | ±10% | Secondary efficacy (OS, ORR), Exposure, Disposition |
| **MODERATE** | ±20% | Overall safety rates, Common AEs |
| **LOW** | ±30% | Immune-related AEs (rare events) |

### Target Values

Key targets from KEYNOTE-868:
- **N = 810** (dMMR: 222, pMMR: 588)
- **PFS HR dMMR: 0.30** (pembrolizumab vs placebo)
- **PFS HR pMMR: 0.60**
- **ORR dMMR pembro: 77%**, placebo: 53%
- **ORR pMMR pembro: 63%**, placebo: 54%

## Layer 2: Simulator

### Files
- `simulator/sim_config.R` - Simulation parameters (N, dates, randomization)
- `simulator/sim_demographics.R` - DM and SC domain generation
- `simulator/sim_exposure.R` - EX domain generation
- `simulator/sim_efficacy.R` - PFS, OS, tumor response simulation
- `simulator/sim_safety.R` - AE domain generation
- `simulator/run_simulator.R` - Orchestration

### SDTM Domains Generated

| Domain | Description | Records |
|--------|-------------|---------|
| DM | Demographics | 810 subjects |
| SC | Subject Characteristics | 3,240 records |
| SV | Subject Visits | ~16,200 records |
| EX | Exposure | ~8,500 records |
| DS | Disposition | ~3,240 records |
| AE | Adverse Events | ~3,700 records |
| LB | Laboratory | ~115,800 records |
| VS | Vital Signs | ~62,400 records |
| TU | Tumor Identification | ~3,100 records |
| TR | Tumor Results | ~19,500 records |
| RS | Disease Response | ~7,300 records |

### Simulation Methods

#### Demographics (sim_demographics.R)
- Age: Normal distribution (mean=65, SD=9), truncated 18-90
- Sex: 100% female (endometrial carcinoma)
- Race: Multinomial sampling matching trial proportions
- ECOG PS: 50/50 split (0 vs 1)
- MMR Status: ~27% dMMR, ~73% pMMR (stratification factor)
- Histology: Endometrioid (60%), Serous (25%), Other (15%)

#### Efficacy (sim_efficacy.R)
- **PFS**: Weibull distribution calibrated to target medians
  - Shape parameter: 1.1 (slight increasing hazard)
  - Scale derived from target median PFS
  - Cure fraction (20%) applied for dMMR pembrolizumab
  - Administrative censoring at data cutoff
  - Loss to follow-up (~3% annual rate)

- **OS**: Correlated with PFS
  - Post-progression survival: exponential distribution
  - Treatment effect modifier for pembrolizumab

- **Tumor Response**: RECIST 1.1 categories
  - CR, PR, SD, PD probabilities from target ORR
  - Stratified by MMR status and treatment arm

#### Safety (sim_safety.R)
- Common AEs: Anemia, neutropenia, nausea, fatigue, etc.
- Immune-related AEs: Hypothyroidism, pneumonitis, colitis, etc.
- Grade distribution: 1-4 with weighted probabilities
- Serious AE flag based on grade and random selection

#### Subject Visits (sim_visits.R)
- Screening visit at Day -14
- Treatment visits every 3 weeks (Q3W)
- End of Treatment and Follow-up visits
- Visit dates with realistic variability (±2 days)

#### Disposition (sim_disposition.R)
- Protocol milestones: Informed consent, Randomization
- Treatment disposition: Completed, Adverse Event, Progressive Disease, Death, Withdrawal
- Study disposition: Ongoing, Lost to Follow-up, Death

#### Laboratory (sim_labs.R)
- 13 parameters: HGB, WBC, ANC, PLT, LYM, ALT, AST, BILI, CREAT, ALB, SODIUM, POTASSIUM, TSH
- Baseline values with subject-specific variation
- Chemotherapy effect modeling (hematologic toxicity)
- Recovery patterns over treatment cycles
- Reference ranges and abnormality flags

#### Vital Signs (sim_vitals.R)
- 7 parameters: Weight, Height, Temperature, Systolic BP, Diastolic BP, Pulse, Respiratory Rate
- Subject-specific baseline values
- Weight loss trajectory (cancer cachexia modeling)
- Visit-to-visit variability

#### Tumor Assessment (sim_tumor.R)
- **TU (Tumor Identification)**: 1-5 target lesions, 0-3 non-target lesions per subject
- **TR (Tumor Results)**: Longest diameter measurements every 9 weeks
  - Response trajectories: CR (shrinkage to 0), PR (>30% reduction), SD (stable), PD (>20% growth)
- **RS (Disease Response)**: RECIST 1.1 overall response at each assessment
  - Best Overall Response derivation

## Layer 3: Mapper

### Files
- `mapper/map_adsl.R` - Subject-level analysis dataset
- `mapper/map_adtte.R` - Time-to-event analysis dataset
- `mapper/map_adae.R` - Adverse event analysis dataset
- `mapper/run_mapper.R` - Orchestration (includes ADRS inline)

### ADaM Datasets Generated

| Dataset | Description | Key Variables |
|---------|-------------|---------------|
| ADSL | Subject Level | TRT01P, MMRSTAT, SAFFL, ITTFL, EFFFL |
| ADTTE | Time-to-Event | PARAMCD (PFS, OS), AVAL, CNSR |
| ADAE | Adverse Events | AEDECOD, ATOXGRN, AESER |
| ADRS | Response | PARAMCD (BOR), AVALC (CR/PR/SD/PD) |
| ADLB | Laboratory Analysis | PARAMCD, AVAL, BASE, CHG, ATOXGRN |
| ADVS | Vital Signs Analysis | PARAMCD, AVAL, BASE, CHG |

### Key Derivations

- **ADSL**: Merges DM, SC, EX; derives treatment duration, flags
- **ADTTE**: Combines PFS and OS; derives analysis dates, flags
- **ADAE**: Enriches AE with baseline, treatment info
- **ADRS**: Best overall response with treatment stratification

## Layer 4: Scorer

### Files
- `scorer/calculate_metrics.R` - Metric calculation from ADaM
- `scorer/run_scorer.R` - Comparison and reporting

### Metrics Calculated

#### Demographics (CRITICAL tier)
- Age median, age groups (<65, ≥65)
- ECOG PS distribution
- Race distribution
- MMR status proportions
- Histology types
- Disease setting

#### Primary Efficacy (CRITICAL tier)
- PFS hazard ratios by MMR cohort (Cox proportional hazards)
- PFS medians by arm and MMR
- 12-month PFS rates

#### Secondary Efficacy (HIGH tier)
- Overall response rate (ORR) by arm and MMR
- Disease control rate (DCR)
- Treatment duration and cycles

#### Safety (MODERATE/LOW tier)
- Any AE rates
- Grade 3+ AE rates
- Serious AE rates
- Specific AE frequencies
- Immune-related AE rates

### Scoring Logic

For each metric:
1. Calculate simulated value from ADaM
2. Compare to target value
3. Compute percent deviation: `|sim - target| / target * 100`
4. Pass if deviation ≤ tier tolerance

### Data Validation Checks

In addition to target matching, the scorer performs 22 data consistency checks across 5 categories. These checks identify simulation bugs (vs calibration issues) and help the agent-based refinement target specific problems.

#### Temporal Consistency (5 checks)

| Check | Description | Identifies |
|-------|-------------|------------|
| PFS before OS | PFS event time ≤ OS event time | Time simulation bugs |
| AE after treatment | AE start ≥ treatment start (7-day grace) | AE timing bugs |
| Positive treatment duration | Treatment duration > 0 | Exposure calculation bugs |
| Death after randomization | OS event time > 0 | Survival simulation bugs |
| AE end after start | AE end date ≥ AE start date | AE duration bugs |

#### Logical Consistency (5 checks)

| Check | Description | Identifies |
|-------|-------------|------------|
| No duplicate subjects | Each subject appears once in ADSL | Data generation bugs |
| Treatment flags consistent | SAFFL=Y if received treatment | Flag derivation bugs |
| Response requires treatment | BOR only for SAFFL=Y subjects | Response logic bugs |
| Censoring consistency | CNSR=1 has censoring description | Censoring logic bugs |
| Valid AE grades | Grades between 1-5 | AE generation bugs |

#### Value Range (4 checks)

| Check | Description | Identifies |
|-------|-------------|------------|
| Valid age range | Age between 18-100 | Demographics generation |
| Valid ECOG range | ECOG PS between 0-4 | Baseline generation |
| Positive TTE values | Time-to-event ≥ 0 | TTE simulation bugs |
| Valid proportions | Proportions between 0-1 | Calculation bugs |

#### Cross-Dataset Consistency (4 checks)

| Check | Description | Identifies |
|-------|-------------|------------|
| ADTTE subjects in ADSL | All ADTTE subjects exist in ADSL | Merge bugs |
| ADAE subjects in ADSL | All ADAE subjects exist in ADSL | Merge bugs |
| ADRS subjects in ADSL | All ADRS subjects exist in ADSL | Merge bugs |
| Treatment consistency | Same treatment across datasets | Treatment assignment bugs |

#### Clinical Plausibility (4 checks)

| Check | Description | Identifies |
|-------|-------------|------------|
| Death has OS event | DTHFL=Y implies OS CNSR=0 | Death recording bugs |
| Serious AE grade | ≥70% of serious AEs are grade 3+ | SAE logic bugs |
| Plausible response | No extreme response distributions | Response generation bugs |
| PFS ≤ OS | PFS time ≤ OS time for all subjects | Survival correlation bugs |

#### Validation Output Files

- `validation_details.csv`, `validation_details.json` - Per-check results
- `validation_summary.csv`, `validation_summary.json` - Summary by category

## Usage

### Run Full Pipeline
```bash
cd ~/keynote_simulation
Rscript run.R
```

### Run with Custom Seed
```bash
Rscript run.R --seed 42
```

### Output Files

All datasets are saved in both CSV and JSON formats for interoperability:

**SDTM (data/sdtm/)**
- `dm.csv`, `dm.json` - Demographics
- `sc.csv`, `sc.json` - Subject Characteristics
- `ex.csv`, `ex.json` - Exposure
- `ae.csv`, `ae.json` - Adverse Events
- `efficacy_pfs.csv`, `efficacy_pfs.json` - PFS data
- `efficacy_os.csv`, `efficacy_os.json` - OS data
- `efficacy_bor.csv`, `efficacy_bor.json` - Best Overall Response

**ADaM (data/adam/)**
- `adsl.csv`, `adsl.json` - Subject Level Analysis
- `adtte.csv`, `adtte.json` - Time-to-Event Analysis
- `adae.csv`, `adae.json` - Adverse Event Analysis
- `adrs.csv`, `adrs.json` - Response Analysis

**Scoring Results (output/)**
- `score_details.csv`, `score_details.json` - Per-metric scores
- `score_summary.csv`, `score_summary.json` - Summary by tier

## Results (Seed: 20260120)

### Overall Performance
- **Total metrics: 55**
- **Passed: 39 (70.9%)**

### By Tier
| Tier | Passed | Total | Rate |
|------|--------|-------|------|
| CRITICAL | 13 | 24 | 54.2% |
| HIGH | 8 | 10 | 80.0% |
| MODERATE | 11 | 14 | 78.6% |
| LOW | 7 | 7 | 100.0% |

### Areas Meeting Targets
- Demographics: Age, ECOG, histology
- Response rates: All ORR metrics within tolerance
- Safety: Common AEs, immune-related AEs
- Exposure: Treatment duration (placebo), cycles

### Areas Needing Calibration
- PFS hazard ratios (simulation effect size calibration)
- 12-month PFS rates
- Serious AE rates
- Some race/MMR proportions

## Dependencies

- R >= 4.0
- `here` - Project path management
- `survival` - Survival analysis (Cox models, Kaplan-Meier)
- `jsonlite` - JSON serialization for data export

## Technical Notes

### Cox Model for HR Calculation
The scorer uses Cox proportional hazards with treatment as a factor:
```r
# Placebo as reference level
pfs$TRT <- factor(pfs$TRTPN, levels = c(2, 1), labels = c("PLACEBO", "PEMBRO"))
cox_fit <- coxph(Surv(AVAL, 1 - CNSR) ~ TRT, data = pfs)
hr <- exp(coef(cox_fit))  # HR for pembro vs placebo
```

### Weibull PFS Simulation
```r
shape <- 1.1
scale <- median_pfs / (log(2)^(1/shape))
pfs_time <- rweibull(1, shape = shape, scale = scale)
```

### Cure Fraction Model
For dMMR pembrolizumab responders (~20%), additional survival time is added:
```r
if (runif(1) < 0.20) {
  pfs_time <- pfs_time + rexp(1, 0.02)
}
```

## Future Enhancements

1. **Calibration improvements**: Tune Weibull parameters to match target HRs
2. **Correlated endpoints**: Model PFS-OS-Response correlation structure
3. **Subgroup analyses**: Additional stratification factors
4. **Multiple seeds**: Run simulations with different seeds for variability assessment
5. **Visualization**: Add KM curves, forest plots to output

---

## Agent-Based Iterative Refinement (Proposed)

### Overview

An AI agent can iteratively refine simulation parameters until the simulated data meets target matching criteria. This creates a closed-loop calibration system that automatically tunes the simulator.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      CALIBRATION AGENT                          │
│  Analyzes score_details.json and proposes parameter adjustments │
└─────────────────────────────────────────────────────────────────┘
        │                                           ▲
        │ 1. Adjust parameters                      │ 4. Read scores
        ▼                                           │
┌─────────────────┐    2. Run     ┌─────────────────────────────┐
│  sim_config.R   │ ──────────────│      SIMULATION PIPELINE    │
│  sim_efficacy.R │               │  Simulator → Mapper → Scorer│
│  sim_safety.R   │               └─────────────────────────────┘
└─────────────────┘                         │
                                            │ 3. Output
                                            ▼
                                 ┌─────────────────────┐
                                 │  score_details.json │
                                 │  score_summary.json │
                                 └─────────────────────┘
```

### Stopping Criteria

The agent continues refinement until one of these conditions is met:

| Criterion | Description | Example |
|-----------|-------------|---------|
| **Validation Pass** | All data consistency checks pass | 22/22 validation checks |
| **Tier Pass Rate** | All tiers meet minimum pass rate | CRITICAL ≥ 80%, HIGH ≥ 90% |
| **Overall Pass Rate** | Total metrics passing threshold | ≥ 85% overall |
| **Max Iterations** | Prevent infinite loops | 20 iterations max |
| **Convergence** | No improvement over N iterations | 3 iterations without gain |
| **Specific Metrics** | Key metrics must pass | PFS HR within tolerance |

**Important**: Validation checks must pass before evaluating metric matching. A simulation with validation failures indicates bugs in the simulation code itself, not calibration issues.

### Calibration Parameters

The agent can adjust these parameters in the simulation code:

#### Efficacy Parameters (sim_efficacy.R)
```r
CALIBRATION_PARAMS <- list(
  pfs = list(
    weibull_shape_dmmr = 1.1,      # Adjustable: 0.8 - 1.5
    weibull_shape_pmmr = 1.1,      # Adjustable: 0.8 - 1.5
    cure_fraction_dmmr = 0.20,     # Adjustable: 0.10 - 0.35
    median_multiplier_pembro = 1.0, # Adjustable: 0.8 - 1.2
    median_multiplier_placebo = 1.0 # Adjustable: 0.8 - 1.2
  ),
  response = list(
    cr_adjustment = 0.0,           # Adjustable: -0.10 to +0.10
    orr_adjustment = 0.0           # Adjustable: -0.10 to +0.10
  )
)
```

#### Safety Parameters (sim_safety.R)
```r
SAFETY_CALIBRATION <- list(
  serious_ae_rate = 0.35,          # Adjustable: 0.20 - 0.50
  grade3_rate_multiplier = 1.0,    # Adjustable: 0.7 - 1.3
  irae_rate_multiplier = 1.0       # Adjustable: 0.7 - 1.3
)
```

### Agent Workflow

```
ITERATION 1:
├── Execute: Rscript run.R
├── Read: validation_details.json
├── Check: Did all 22 validation checks pass?
│   ├── If NO → Fix simulation bugs first (targeted fixes)
│   │   ├── TEMPORAL failures → Fix time calculations in sim_efficacy.R
│   │   ├── LOGICAL failures → Fix flag derivations in mapper/
│   │   ├── RANGE failures → Fix value generation bounds
│   │   ├── CROSS_DATASET failures → Fix merge logic in mapper/
│   │   └── CLINICAL failures → Fix clinical logic in simulator/
│   └── If YES → Proceed to metric matching
├── Read: score_details.json
├── Analyze: Which metrics failed? By how much?
├── Diagnose:
│   ├── pfs_hr_dmmr: sim=0.13, target=0.30 → HR too low (too much effect)
│   ├── pfs_hr_pmmr: sim=0.77, target=0.60 → HR too high (not enough effect)
│   └── ae_serious_pct: sim=0.62, target=0.35 → Rate too high
├── Propose calibration adjustments:
│   ├── Decrease cure_fraction_dmmr: 0.20 → 0.12
│   ├── Increase weibull_shape_pmmr: 1.1 → 1.3
│   └── Decrease serious_ae_rate: 0.35 → 0.28
├── Edit: sim_efficacy.R, sim_safety.R
└── Evaluate: Did pass rate improve?

ITERATION 2:
├── Execute: Rscript run.R
├── Read: validation_details.json → All passed ✓
├── Read: score_details.json (updated)
├── Analyze: 45/55 passed (81.8%) vs 39/55 (70.9%) previously
├── Continue: Still below 85% target
└── ... (repeat until criteria met)
```

### Validation-Guided Bug Fixes

When validation checks fail, the agent should apply targeted fixes:

| Validation Category | Failure Indicates | Target Files | Fix Strategy |
|---------------------|-------------------|--------------|--------------|
| TEMPORAL | Time sequence bugs | sim_efficacy.R | Ensure PFS ≤ OS, positive durations |
| LOGICAL | Flag/logic bugs | map_adsl.R, map_adtte.R | Fix flag derivations, ensure consistency |
| RANGE | Value generation bugs | sim_demographics.R | Clamp values to valid ranges |
| CROSS_DATASET | Merge/join bugs | run_mapper.R | Fix merge keys, handle missing subjects |
| CLINICAL | Implausible data | sim_efficacy.R, sim_safety.R | Fix clinical relationships |

Example fix for PFS > OS violation:
```r
# In sim_os.R - ensure OS >= PFS
os_time[i] <- max(os_time[i], pfs_times[i])
```

Example fix for serious AE grade violation:
```r
# In sim_safety.R - bias serious AEs toward higher grades
if (serious) {
  grade <- sample(3:5, 1, prob = c(0.5, 0.35, 0.15))
}
```

### Implementation Approach

#### Option A: External Python Agent

```python
# calibration_agent.py
import json
import subprocess
from pathlib import Path

class CalibrationAgent:
    def __init__(self, project_dir, llm_client):
        self.project_dir = Path(project_dir)
        self.llm = llm_client
        self.history = []

    def run_simulation(self):
        """Execute R simulation pipeline"""
        result = subprocess.run(
            ["Rscript", "run.R"],
            cwd=self.project_dir,
            capture_output=True
        )
        return result.returncode == 0

    def read_scores(self):
        """Load scoring results"""
        with open(self.project_dir / "output/score_details.json") as f:
            return json.load(f)

    def analyze_failures(self, scores):
        """Use LLM to analyze which parameters need adjustment"""
        prompt = f"""
        Analyze these simulation scoring results and suggest parameter adjustments.

        Failed metrics:
        {json.dumps([s for s in scores if not s['pass']], indent=2)}

        Current parameters: {self.get_current_params()}

        Suggest specific numerical adjustments to improve matching.
        """
        return self.llm.generate(prompt)

    def apply_adjustments(self, adjustments):
        """Edit R files with new parameter values"""
        # Parse LLM suggestions and apply via file edits
        pass

    def calibrate(self, max_iterations=20, target_pass_rate=0.85):
        """Main calibration loop"""
        for i in range(max_iterations):
            self.run_simulation()
            scores = self.read_scores()

            pass_rate = sum(s['pass'] for s in scores) / len(scores)
            print(f"Iteration {i+1}: {pass_rate:.1%} pass rate")

            if pass_rate >= target_pass_rate:
                print("Target achieved!")
                return True

            adjustments = self.analyze_failures(scores)
            self.apply_adjustments(adjustments)
            self.history.append({'iteration': i, 'pass_rate': pass_rate})

        return False
```

#### Option B: Claude Code Agent Integration

Use Claude Code's agentic capabilities directly:

```bash
# Run calibration via Claude Code
claude "Iteratively refine the KEYNOTE-868 simulation until 85% of metrics pass.

Steps for each iteration:
1. Run: Rscript run.R
2. Read: output/score_details.json
3. Analyze failed metrics and their deviations
4. Edit simulation parameters in sim_efficacy.R or sim_safety.R
5. Repeat until pass rate >= 85% or 10 iterations

Current parameters to adjust:
- sim_efficacy.R: weibull_shape, cure_fraction, median_multiplier
- sim_safety.R: serious_ae_rate, grade3_rate_multiplier

Stop when CRITICAL tier >= 75% AND overall >= 85%"
```

#### Option C: R-Native Agent Loop

```r
# calibration_loop.R
source("run.R")

calibrate_simulation <- function(
  target_pass_rate = 0.85,
  max_iterations = 20,
  param_bounds = list(
    weibull_shape = c(0.8, 1.5),
    cure_fraction = c(0.05, 0.35),
    serious_ae_rate = c(0.20, 0.50)
  )
) {

  history <- list()

  for (iter in 1:max_iterations) {
    # Run simulation
    result <- run_pipeline(seed = 20260120 + iter)

    # Check pass rate
    pass_rate <- result$score$total_passed / result$score$total_metrics
    cat(sprintf("Iteration %d: %.1f%% pass rate\n", iter, pass_rate * 100))

    history[[iter]] <- list(
      iteration = iter,
      pass_rate = pass_rate,
      params = get_current_params()
    )

    if (pass_rate >= target_pass_rate) {
      cat("Target achieved!\n")
      return(list(success = TRUE, history = history))
    }

    # Analyze failures and adjust
    adjustments <- analyze_and_suggest(result$score$results)
    apply_parameter_adjustments(adjustments, param_bounds)
  }

  list(success = FALSE, history = history)
}
```

### Adjustment Heuristics

The agent uses these rules to adjust parameters:

| Metric Issue | Parameter | Adjustment |
|--------------|-----------|------------|
| HR too low (too much effect) | cure_fraction | Decrease by 20% |
| HR too low | weibull_shape | Increase by 0.1 |
| HR too high (not enough effect) | median_multiplier_pembro | Increase by 10% |
| HR too high | cure_fraction | Increase by 20% |
| 12-mo rate too high | weibull_shape | Decrease by 0.1 |
| 12-mo rate too low | weibull_shape | Increase by 0.1 |
| Serious AE too high | serious_ae_rate | Decrease by 15% |
| Grade 3+ AE off | grade3_rate_multiplier | Adjust proportionally |

### Expected Convergence

Based on the parameter sensitivity:

| Iteration | Expected Pass Rate | Key Adjustments |
|-----------|-------------------|-----------------|
| 1 (baseline) | 70.9% | - |
| 2 | ~75% | Cure fraction, serious AE rate |
| 3 | ~80% | Weibull shapes fine-tuned |
| 4-5 | ~85% | Minor calibration |
| 6+ | 85%+ | Converged |

### Benefits

1. **Automated calibration**: No manual parameter tuning
2. **Reproducible**: Agent logs all adjustments
3. **Adaptive**: Handles multiple failing metrics simultaneously
4. **Extensible**: Easy to add new parameters or metrics
5. **Interpretable**: JSON output enables analysis of calibration path

### Limitations

1. **Local optima**: May converge to suboptimal solutions
2. **Parameter interactions**: Some parameters have complex interdependencies
3. **Stochastic variation**: Different seeds produce different results
4. **Computation cost**: Each iteration runs full pipeline
