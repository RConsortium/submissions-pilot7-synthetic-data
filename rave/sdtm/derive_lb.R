# derive_lb.R — LB (Laboratory). Long pivot of the three RAVE lab CRFs:
# hematology (WBC/ANC/HGB/PLT/ESR), chemistry (BUN/CREAT/CRP) and urinalysis
# (hematuria, qualitative). One SDTM record per test per visit.

.LB_DICT <- tibble::tribble(
  ~col,        ~LBTESTCD, ~LBTEST,                          ~LBORRESU, ~LBCAT,       ~LBSPEC,
  "WBC",       "WBC",     "Leukocytes",                     "10^9/L",  "HEMATOLOGY", "WHOLE BLOOD",
  "ANC",       "NEUT",    "Neutrophils",                    "10^9/L",  "HEMATOLOGY", "WHOLE BLOOD",
  "HGB",       "HGB",     "Hemoglobin",                     "g/dL",    "HEMATOLOGY", "WHOLE BLOOD",
  "PLT",       "PLAT",    "Platelets",                      "10^9/L",  "HEMATOLOGY", "WHOLE BLOOD",
  "ESR",       "ESR",     "Erythrocyte Sedimentation Rate", "mm/h",    "HEMATOLOGY", "WHOLE BLOOD",
  "BUN",       "BUN",     "Blood Urea Nitrogen",            "mg/dL",   "CHEMISTRY",  "SERUM",
  "CREAT",     "CREAT",   "Creatinine",                     "mg/dL",   "CHEMISTRY",  "SERUM",
  "CRP",       "CRP",     "C-Reactive Protein",             "mg/L",    "CHEMISTRY",  "SERUM",
  "HEMATURIA", "HEMATUR", "Hematuria",                      "",        "URINALYSIS", "URINE"
)

.lb_long <- function(df, cols) {
  df |>
    pivot_longer(all_of(cols), names_to = "col", values_to = "LBORRES") |>
    filter(LBORRES != "") |>
    inner_join(.LB_DICT, by = "col") |>
    select(USUBJID, VISIT_CD = VISIT, LBDTC, LBTESTCD, LBTEST, LBCAT, LBSPEC,
           LBORRES, LBORRESU)
}

derive_lb <- function() {
  ref <- ref_dates()
  long <- bind_rows(
    .lb_long(read_form("LB_HEM"),  c("WBC", "ANC", "HGB", "PLT", "ESR")),
    .lb_long(read_form("LB_CHEM"), c("BUN", "CREAT", "CRP")),
    .lb_long(read_form("LB_UA"),   c("HEMATURIA"))
  )

  out <- long |>
    left_join(ref, by = "USUBJID") |>
    join_visit("VISIT_CD") |>
    mutate(
      STUDYID  = STUDYID,
      DOMAIN   = "LB",
      LBDY     = study_day(LBDTC, RFSTDTC),
      LBSTRESC = LBORRES,
      LBSTRESN = ifelse(is.na(suppressWarnings(as.numeric(LBORRES))), "", LBORRES),
      LBSTRESU = LBORRESU,
      EPOCH    = epoch_of(VISIT),
    ) |>
    # One baseline flag per subject x test x specimen: the BASELINE (V1) record.
    group_by(USUBJID, LBTESTCD, LBSPEC) |>
    arrange(as.integer(VISITNUM), .by_group = TRUE) |>
    mutate(LBBLFL = {
      cand <- which(VISIT == "BASELINE" & LBORRES != "")
      f <- rep("", n()); if (length(cand)) f[tail(cand, 1)] <- "Y"; f
    }) |>
    ungroup() |>
    arrange(USUBJID, LBCAT, LBTESTCD, as.integer(VISITNUM)) |>
    add_seq("LBSEQ")

  finalize(out, c(
    "STUDYID", "DOMAIN", "USUBJID", "LBSEQ", "LBTESTCD", "LBTEST", "LBCAT",
    "LBORRES", "LBORRESU", "LBSTRESC", "LBSTRESN", "LBSTRESU", "LBSPEC",
    "LBBLFL", "EPOCH", "VISITNUM", "VISIT", "LBDTC", "LBDY"))
}
