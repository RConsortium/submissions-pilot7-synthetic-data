# derive_rs.R — RS (Disease Response and Clin Classification): the RA
# disease-activity assessment (DA CRF) — DAS28-CRP composite plus its component
# measures, one SDTM record per measure per clinical visit. (CRP itself lives in
# LB chemistry and is not duplicated here.)

# CRF column -> (RSTESTCD, RSTEST, RSORRESU).
.RS_DICT <- tibble::tribble(
  ~col,         ~RSTESTCD,    ~RSTEST,                          ~RSORRESU,
  "TJC28",      "TJC28",      "Tender Joint Count (28)",        "joints",
  "SJC28",      "SJC28",      "Swollen Joint Count (28)",       "joints",
  "PTGLOBAL",   "PTGLOBAL",   "Patient Global Assessment VAS",  "mm",
  "PHYSGLOBAL", "PHYSGBL",    "Physician Global Assessment VAS","mm",
  "PAINVAS",    "PAINVAS",    "Pain VAS",                       "mm",
  "HAQDI",      "HAQDI",      "HAQ Disability Index",           "",
  "DAS28CRP",   "DAS28CRP",   "DAS28-CRP Score",                ""
)

derive_rs <- function() {
  da <- read_form("DA")

  long <- da |>
    rename(RSDTC = DADTC, RSDY = DADY) |>
    pivot_longer(all_of(.RS_DICT$col), names_to = "col", values_to = "RSORRES") |>
    filter(RSORRES != "") |>
    inner_join(.RS_DICT, by = "col")

  out <- long |>
    select(USUBJID, VISIT_CD = VISIT, RSDTC, RSDY,
           RSTESTCD, RSTEST, RSORRES, RSORRESU) |>
    join_visit("VISIT_CD") |>
    mutate(
      STUDYID  = STUDYID,
      DOMAIN   = "RS",
      RSCAT    = "DISEASE ACTIVITY",
      RSSTRESC = RSORRES,
      RSSTRESN = RSORRES,
      RSSTRESU = RSORRESU,
      RSBLFL   = ifelse(VISIT == "BASELINE" & RSORRES != "", "Y", ""),
      EPOCH    = epoch_of(VISIT),
    ) |>
    arrange(USUBJID, RSTESTCD, as.integer(VISITNUM)) |>
    add_seq("RSSEQ")

  finalize(out, c(
    "STUDYID", "DOMAIN", "USUBJID", "RSSEQ", "RSTESTCD", "RSTEST", "RSCAT",
    "RSORRES", "RSORRESU", "RSSTRESC", "RSSTRESN", "RSSTRESU", "RSBLFL",
    "EPOCH", "VISITNUM", "VISIT", "RSDTC", "RSDY"))
}
