# derive_rs.R — RS (Disease Response and Clin Classification): the RAVE vasculitis
# outcome measures — BVAS/WG activity score + remission / flare / glucocorticoid-free
# status (DA CRF), and the Vasculitis Damage Index (VDI CRF). One record per
# measure per visit.

# DA column -> (RSTESTCD, RSTEST). BVAS/WG is numeric; the rest are categorical.
.RS_DA <- tibble::tribble(
  ~col,        ~RSTESTCD,  ~RSTEST,
  "BVASWG",    "BVASWG",   "BVAS/WG Total Score",
  "REMISSION", "REMSTAT",  "Remission Status",
  "FLARE",     "FLARE",    "Flare Status",
  "GCFREE",    "GCFREE",   "Glucocorticoid-Free Status"
)

derive_rs <- function() {
  ref <- ref_dates()

  da <- read_form("DA") |>
    rename(RSDTC = DADTC) |>
    pivot_longer(all_of(.RS_DA$col), names_to = "col", values_to = "RSORRES") |>
    filter(RSORRES != "") |>
    inner_join(.RS_DA, by = "col") |>
    transmute(USUBJID, VISIT_CD = VISIT, RSDTC, RSTESTCD, RSTEST,
              RSCAT = "DISEASE ACTIVITY", RSORRES)

  vdi <- read_form("VDI") |>
    filter(VDI != "") |>
    left_join(ref, by = "USUBJID") |>
    transmute(USUBJID, VISIT_CD = VISIT,
              RSDTC = add_days(RFSTDTC, as.integer(VDIDY) - 1L),
              RSTESTCD = "VDI", RSTEST = "Vasculitis Damage Index",
              RSCAT = "DAMAGE INDEX", RSORRES = VDI)

  out <- bind_rows(da, vdi) |>
    left_join(ref, by = "USUBJID") |>
    join_visit("VISIT_CD") |>
    mutate(
      STUDYID  = STUDYID,
      DOMAIN   = "RS",
      RSSTRESC = RSORRES,
      RSSTRESN = ifelse(is.na(suppressWarnings(as.numeric(RSORRES))), "", RSORRES),
      RSDY     = study_day(RSDTC, RFSTDTC),
      EPOCH    = epoch_of(VISIT),
    ) |>
    group_by(USUBJID, RSTESTCD) |>
    arrange(as.integer(VISITNUM), .by_group = TRUE) |>
    mutate(RSBLFL = {
      cand <- which(VISIT == "BASELINE" & RSORRES != "")
      f <- rep("", n()); if (length(cand)) f[tail(cand, 1)] <- "Y"; f
    }) |>
    ungroup() |>
    arrange(USUBJID, RSTESTCD, as.integer(VISITNUM)) |>
    add_seq("RSSEQ")

  finalize(out, c(
    "STUDYID", "DOMAIN", "USUBJID", "RSSEQ", "RSTESTCD", "RSTEST", "RSCAT",
    "RSORRES", "RSSTRESC", "RSSTRESN", "RSBLFL", "EPOCH",
    "VISITNUM", "VISIT", "RSDTC", "RSDY"))
}
