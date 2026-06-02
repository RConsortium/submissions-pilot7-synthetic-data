#' =============================================================================
#' EIDD-2801-1001-UK Simulator Configuration
#' Single-dose Phase 1 PK study of molnupiravir (EIDD-2801 / MK-4482)
#' Submission package 2020-001407-17-00
#' =============================================================================
#' Study-level constants and clinical reference ranges shared by the engine
#' (sim_core.R) and the per-domain modules (forms/sim_*.R).
#' =============================================================================

SIM_CONFIG <- list(
  study_id   = "2020-001407-17-00",
  drug_trt   = "EIDD-2801",          # molnupiravir (MK-4482)
  site_id    = "01",
  country    = "GBR",

  # Study-fixed dosing options (one pair chosen per simulation run)
  dose_mg_options    = c(50, 100, 200, 400, 800),
  formulation_options = c("Capsule", "Solution"),

  # Demographics not captured on any CRF form — generated deterministically
  age_min = 18, age_max = 55,
  races = c("WHITE", "WHITE", "WHITE", "BLACK OR AFRICAN AMERICAN", "ASIAN",
            "AMERICAN INDIAN OR ALASKA NATIVE", "OTHER"),
  ethnics = c("NOT HISPANIC OR LATINO", "NOT HISPANIC OR LATINO",
              "HISPANIC OR LATINO"),

  # Probability a subject is eligible (ineligible -> I/E criteria ticked)
  eligible_prob = 0.97
)

# Visit slug -> (visitnum, label, day offset from Day 1 dose day = 0)
VISIT_INFO <- list(
  day_minus_1 = list(num = 1, label = "Day -1",     offset = -1),
  day_1       = list(num = 2, label = "Day 1",      offset = 0),
  day_2       = list(num = 3, label = "Day 2",      offset = 1),
  day_3       = list(num = 4, label = "Day 3",      offset = 2),
  day_4       = list(num = 5, label = "Day 4",      offset = 3),
  day_9       = list(num = 6, label = "Day 9",      offset = 8),
  day_15_eos  = list(num = 7, label = "Day 15/EOS", offset = 14)
)

# ----------------------------- Reason pools -----------------------------

REASONS_PERFORMED_NO <- c(
  "Subject withdrew consent", "Equipment malfunction", "Sample lost in transit",
  "Subject refused", "Scheduling conflict", "Insufficient sample volume"
)
REASONS_DRUG_NOT_TAKEN <- c(
  "Subject withdrew before dosing", "Adverse event prior to dosing",
  "Investigator decision"
)
REASONS_DOSE_ADJUSTED <- c(
  "Investigator decision per protocol", "Tolerability assessment",
  "Adverse event prior to administration"
)
SIGNIFICANCE_COMMENTS <- c(
  "Mild finding, resolved without intervention",
  "Reviewed by PI; not clinically actionable",
  "Follow-up assessment scheduled"
)
NA_MALE     <- "Not applicable - male subject"
NA_NOT_FOCP <- "Not applicable - subject not of childbearing potential"

# ----------------------------- Value generators -----------------------------

# Loose keyword ranges for vitals / dosing fields (checked AFTER exact lab names).
# list(keyword, lo, hi, fmt) where fmt is the number of decimals.
NUMERIC_BY_FIELD_NAME <- list(
  list("systolic blood pressure", 105, 135, 0),
  list("diastolic blood pressure", 65, 90, 0),
  list("blood pressure", 70, 130, 0),
  list("pulse rate", 55, 90, 0),
  list("heart rate", 55, 90, 0),
  list("respiratory rate", 12, 20, 0),
  list("temperature", 36.2, 37.4, 1),
  list("planned dose", 50, 800, 0),
  list("planned volume", 100, 700, 0),
  list("weight", 55, 95, 1),
  list("height", 155, 195, 1),
  list("bmi", 18.5, 29.5, 1),
  list("oxygen saturation", 96, 100, 0),
  list("spo2", 96, 100, 0),
  list("volume", 100, 700, 0),
  list("dose", 50, 800, 0)
)

# Units the FORM-FILLER recognizes (substring match) to generate a measured
# value instead of echoing the unit. Deliberately excludes "ms" so ECG interval
# fields (whose only template value is "ms") are left as the literal token...
UNIT_KEYWORDS <- c(
  "mmhg", "beats/min", "breaths/min", "kg", "cm",
  "celsius", "fahrenheit", "degree celsius", "degree fahrenheit",
  "mg/dl", "mmol/l", "g/dl", "g/l", "%"
)

# ...and the SDTM mapper then suppresses any cell that is ONLY a unit token
# (exact match), e.g. ECG "ms" -> no observation row.
UNIT_TOKENS <- c(
  "ms", "mmhg", "beats/min", "breaths/min", "kg", "cm", "%",
  "mg/dl", "mmol/l", "g/dl", "g/l", "ml", "milligram", "milliliter",
  "degree celsius", "degree fahrenheit"
)

# Clinically-plausible ranges for the standalone numeric lab fields, keyed by
# exact CRF field name (lower-cased). Checked BEFORE NUMERIC_BY_FIELD_NAME so
# "Ery. Mean Corpuscular Volume" is not mistaken for a dosing "volume".
# list(lo, hi, decimals)
LAB_NUMERIC_RANGES <- list(
  "ery. mean corpuscular volume"             = list(80, 100, 0),   # fL
  "ery. mean corpuscular hemoglobin"         = list(27, 33, 1),    # pg
  "ery. mean corpuscular hgb concentration"  = list(32, 36, 1),    # g/dL
  "platelets"                                = list(150, 400, 0),  # 10^9/L
  "neutrophils percentage"                   = list(40, 70, 1),
  "lymphocytes percentage"                   = list(20, 45, 1),
  "monocytes percentage"                     = list(2, 10, 1),
  "eosinophils percentage"                   = list(1, 6, 1),
  "basophils percentage"                     = list(0, 2, 1),
  "neutrophils absolute"                     = list(2.0, 7.0, 2),  # 10^9/L
  "lymphocytes absolute"                     = list(1.0, 3.5, 2),
  "monocytes absolute"                       = list(0.2, 0.8, 2),
  "eosinophils absolute"                     = list(0.0, 0.5, 2),
  "basophils absolute"                       = list(0.0, 0.1, 2),
  "leukocytes"                               = list(4.0, 11.0, 1), # 10^9/L
  "erythrocytes"                             = list(4.2, 5.9, 2),  # 10^12/L
  "prothrombin time (pt)"                    = list(11, 14, 1),    # sec
  "partial prothrombin time (ptt)"           = list(25, 35, 1),    # sec
  "international normalized ratio (inr)"     = list(0.8, 1.2, 2),
  "red cell distribution width (rdw)"        = list(11.5, 14.5, 1),# %
  "blood urea nitrogen"                      = list(7, 20, 0)      # mg/dL
)

# Weighted qualitative dipstick results for standalone urinalysis fields.
# Each entry: list(values = c(...), weights = c(...))
URINALYSIS_VALUES <- list(
  "glucose"            = list(c("Negative", "Trace", "1+"), c(90, 7, 3)),
  "protein"            = list(c("Negative", "Trace", "1+"), c(88, 8, 4)),
  "urobilinogen"       = list(c("Normal", "1+"), c(92, 8)),
  "occult blood"       = list(c("Negative", "Trace", "1+"), c(90, 6, 4)),
  "ketones"            = list(c("Negative", "Trace", "1+"), c(90, 7, 3)),
  "bilirubin"          = list(c("Negative", "1+"), c(97, 3)),
  "nitrite"            = list(c("Negative", "Positive"), c(95, 5)),
  "leukocyte esterase" = list(c("Negative", "Trace", "1+"), c(90, 6, 4)),
  "color and appearance" = list(c("Yellow", "Straw", "Amber", "Dark Yellow"),
                                c(55, 25, 15, 5)),
  "specimen appearance"  = list(c("Clear", "Slightly Cloudy", "Cloudy"),
                                c(80, 15, 5)),
  "microscopic rbcs and wbcs examination" = list(
    c("None seen", "0-2 /hpf", "3-5 /hpf"), c(70, 20, 10))
)
