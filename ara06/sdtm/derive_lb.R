# derive_lb.R — LB (Laboratory). Pivots the three wide ARA06 lab CRFs into the
# long SDTM findings structure (one row per test per visit): hematology (LB_HEM),
# chemistry (LB_CHEM) and the switched-memory B-cell flow assay (BC).
#
# Result units already match the EDC-collected units, so LBSTRES* == LBORRES.
# LBBLFL = "Y" on the BASELINE record of each subject x test with a result.

# CRF column -> (LBTESTCD, LBTEST, LBORRESU, LBCAT).
.LB_DICT <- tibble::tribble(
  ~col,       ~LBTESTCD,  ~LBTEST,                       ~LBORRESU, ~LBCAT,
  "WBC",      "WBC",      "Leukocytes",                  "10^9/L",  "HEMATOLOGY",
  "ANC",      "NEUT",     "Neutrophils",                 "10^9/L",  "HEMATOLOGY",
  "ALC",      "LYM",      "Lymphocytes",                 "10^9/L",  "HEMATOLOGY",
  "HGB",      "HGB",      "Hemoglobin",                  "g/dL",    "HEMATOLOGY",
  "PLT",      "PLAT",     "Platelets",                   "10^9/L",  "HEMATOLOGY",
  "AST",      "AST",      "Aspartate Aminotransferase",  "U/L",     "CHEMISTRY",
  "ALT",      "ALT",      "Alanine Aminotransferase",    "U/L",     "CHEMISTRY",
  "CREAT",    "CREAT",    "Creatinine",                  "mg/dL",   "CHEMISTRY",
  "CRP",      "CRP",      "C-Reactive Protein",          "mg/L",    "CHEMISTRY",
  "MEMSWPCT", "MEMSWPCT", "Switched Memory B-Cells",     "%",       "FLOW CYTOMETRY"
)

# Pivot one wide lab form (whose result columns are named in `cols`) into long
# rows carrying USUBJID, VISIT(code), LBDTC, LBDY, LBTESTCD/LBORRES/...
# The per-form date/day columns differ (LBDTC/LBDY vs BCDTC/BCDY) so both are
# renamed to the SDTM names.
.lb_long <- function(df, cols, dtc_col, dy_col) {
  df |>
    rename(LBDTC = all_of(dtc_col), LBDY = all_of(dy_col)) |>
    pivot_longer(all_of(cols), names_to = "col", values_to = "LBORRES") |>
    filter(LBORRES != "") |>
    inner_join(.LB_DICT, by = "col")
}

derive_lb <- function() {
  hem <- read_form("LB_HEM")
  chem <- read_form("LB_CHEM")
  bc  <- read_form("BC")

  long <- bind_rows(
    .lb_long(hem,  c("WBC", "ANC", "ALC", "HGB", "PLT"),  "LBDTC", "LBDY"),
    .lb_long(chem, c("AST", "ALT", "CREAT", "CRP"),       "LBDTC", "LBDY"),
    .lb_long(bc,   c("MEMSWPCT"),                         "BCDTC", "BCDY")
  )

  out <- long |>
    select(USUBJID, VISIT_CD = VISIT, LBDTC, LBDY,
           LBTESTCD, LBTEST, LBCAT, LBORRES, LBORRESU) |>
    join_visit("VISIT_CD") |>
    mutate(
      STUDYID  = STUDYID,
      DOMAIN   = "LB",
      LBSTRESC = LBORRES,
      LBSTRESN = LBORRES,
      LBSTRESU = LBORRESU,
      LBBLFL   = ifelse(VISIT == "BASELINE" & LBORRES != "", "Y", ""),
      EPOCH    = epoch_of(VISIT),
    ) |>
    arrange(USUBJID, LBCAT, LBTESTCD, as.integer(VISITNUM)) |>
    add_seq("LBSEQ")

  finalize(out, c(
    "STUDYID", "DOMAIN", "USUBJID", "LBSEQ", "LBTESTCD", "LBTEST", "LBCAT",
    "LBORRES", "LBORRESU", "LBSTRESC", "LBSTRESN", "LBSTRESU", "LBBLFL",
    "EPOCH", "VISITNUM", "VISIT", "LBDTC", "LBDY"))
}
