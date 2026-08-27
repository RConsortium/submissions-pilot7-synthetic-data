# derive_vs.R — VS (Vital Signs). Long pivot of the VS CRF (BP / pulse / temp /
# weight at BASELINE + DAY 21) plus baseline HEIGHT and BMI from the DM CRF.

.VS_DICT <- tibble::tribble(
  ~col,     ~VSTESTCD, ~VSTEST,                    ~VSORRESU,
  "SYSBP",  "SYSBP",   "Systolic Blood Pressure",  "mmHg",
  "DIABP",  "DIABP",   "Diastolic Blood Pressure", "mmHg",
  "PULSE",  "PULSE",   "Pulse Rate",               "beats/min",
  "TEMP",   "TEMP",    "Temperature",              "C",
  "WEIGHT", "WEIGHT",  "Weight",                   "kg",
  "HEIGHT", "HEIGHT",  "Height",                   "cm",
  "BMI",    "BMI",     "Body Mass Index",          "kg/m2"
)

derive_vs <- function() {
  vs <- read_form("VS")          # SYSBP DIABP PULSE TEMP WEIGHT, per BASE/D21
  dm <- read_form("DM")          # baseline HEIGHT + BMI

  vs_long <- vs |>
    pivot_longer(c(SYSBP, DIABP, PULSE, TEMP, WEIGHT),
                 names_to = "col", values_to = "VSORRES") |>
    filter(VSORRES != "") |>
    transmute(USUBJID, VISIT_CD = VISIT, VSDTC, col, VSORRES)

  dm_long <- dm |>
    pivot_longer(c(HEIGHT, BMI), names_to = "col", values_to = "VSORRES") |>
    filter(VSORRES != "") |>
    transmute(USUBJID, VISIT_CD = "BASE", VSDTC = RFSTDTC, col, VSORRES)

  ref <- ref_dates()

  out <- bind_rows(vs_long, dm_long) |>
    inner_join(.VS_DICT, by = "col") |>
    left_join(ref, by = "USUBJID") |>
    join_visit("VISIT_CD") |>
    mutate(
      STUDYID  = STUDYID,
      DOMAIN   = "VS",
      VSSTRESC = VSORRES,
      VSSTRESN = VSORRES,
      VSSTRESU = VSORRESU,
      VSDY     = study_day(VSDTC, RFSTDTC),
      VSBLFL   = ifelse(VISIT == "BASELINE" & VSORRES != "", "Y", ""),
      EPOCH    = epoch_of(VISIT),
    ) |>
    arrange(USUBJID, VSTESTCD, as.integer(VISITNUM)) |>
    add_seq("VSSEQ")

  finalize(out, c(
    "STUDYID", "DOMAIN", "USUBJID", "VSSEQ", "VSTESTCD", "VSTEST",
    "VSORRES", "VSORRESU", "VSSTRESC", "VSSTRESN", "VSSTRESU", "VSBLFL",
    "EPOCH", "VISITNUM", "VISIT", "VSDTC", "VSDY"))
}
