#' =============================================================================
#' Domain: PC (PK / biospecimen collection log)
#' =============================================================================
#' The CRF captures collection only (date/time/timepoint/specimen), no assayed
#' concentration, so PCORRES is left blank — each row documents a collection.
#' =============================================================================

PC_COLUMNS <- c("STUDYID", "DOMAIN", "USUBJID", "PCSEQ", "PCTESTCD", "PCTEST",
                "PCSPEC", "PCORRES", "PCORRESU", "VISITNUM", "VISIT", "PCTPT",
                "PCDTC", "PCDY")

.PC_SPEC <- c("pk_blood_sample" = "BLOOD", "pk_urine_sample" = "URINE",
              "pbmc_collection" = "PBMC")

build_pc <- function(patient, cases) {
  usubjid <- usubjid_of(patient)
  ref <- patient$baseline_date
  rows <- list(); seq <- 0L
  for (e in iter_domain_records(cases, function(f) f %in% names(.PC_SPEC))) {
    rec <- e$rec
    if (tolower(rec_get(rec, "Was the sample collected?") %||% "yes") == "no") next
    d <- parse_date(rec_get(rec, "Date of Sample Collection"))
    dtc <- iso_dtc(d, rec_get(rec, "Time of Sample Collection"))
    seq <- seq + 1L
    rows[[seq]] <- list(
      STUDYID = SIM_CONFIG$study_id, DOMAIN = "PC", USUBJID = usubjid,
      PCSEQ = seq, PCTESTCD = "EIDD2801", PCTEST = SIM_CONFIG$drug_trt,
      PCSPEC = .PC_SPEC[[e$form]], PCORRES = "", PCORRESU = "",
      VISITNUM = e$vnum, VISIT = e$vlabel,
      PCTPT = rec_get(rec, "Planned Time Point") %||% "", PCDTC = dtc,
      PCDY = study_day(d, ref))
  }
  rows
}
