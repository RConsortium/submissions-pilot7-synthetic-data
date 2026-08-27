# sdtm.R — SDTM domain construction from source CSVs
# KEYNOTE-564 IPD Causal-DAG Simulator

source("R/dag_state.R")

#' Build SDTM domains from source CSVs
#' @param source_dir character, path to source CSV directory
#' @param output_dir character, path for SDTM output
#' @return list of SDTM domain data.tables
build_sdtm <- function(source_dir = "output/source", output_dir = "output/sdtm") {

  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  # Read source CSVs
  dm_src <- fread(file.path(source_dir, "DM.csv"))
  ex_src <- fread(file.path(source_dir, "EX.csv"))
  ae_src <- fread(file.path(source_dir, "AE.csv"))
  lb_src <- fread(file.path(source_dir, "LB.csv"))
  tu_src <- fread(file.path(source_dir, "TU.csv"))
  ds_src <- fread(file.path(source_dir, "DS.csv"))

  # ─── DM Domain ──────────────────────────────────────────────────────────
  dm <- data.table(
    STUDYID  = "KN564",
    DOMAIN   = "DM",
    USUBJID  = dm_src$SUBJID,
    SUBJID   = dm_src$SUBJID,
    RFSTDTC  = format(dm_src$RANDDT, "%Y-%m-%d"),
    AGE      = dm_src$AGE,
    AGEU     = "YEARS",
    SEX      = dm_src$SEX,
    RACE     = dm_src$RACE,
    COUNTRY  = fifelse(dm_src$REGION == "US", "USA", "OTH"),
    ARM      = dm_src$ARM,
    ARMCD    = fifelse(dm_src$ARM == "PEMBROLIZUMAB", "PEMBRO", "PBO"),
    ACTARM   = dm_src$ARM,
    ACTARMCD = fifelse(dm_src$ARM == "PEMBROLIZUMAB", "PEMBRO", "PBO")
  )

  # ─── EX Domain ──────────────────────────────────────────────────────────
  ex <- data.table(
    STUDYID  = "KN564",
    DOMAIN   = "EX",
    USUBJID  = ex_src$SUBJID,
    EXSEQ    = seq_len(nrow(ex_src)),
    EXTRT    = ex_src$EXTRT,
    EXDOSE   = ex_src$EXDOSE,
    EXDOSU   = ex_src$EXDOSU,
    EXROUTE  = ex_src$EXROUTE,
    VISITNUM = ex_src$CYCLE,
    EXSTDY   = ex_src$VISIT_DAY,
    EXENDY   = ex_src$VISIT_DAY
  )

  # ─── AE Domain ──────────────────────────────────────────────────────────
  ae <- data.table(
    STUDYID  = "KN564",
    DOMAIN   = "AE",
    USUBJID  = ae_src$SUBJID,
    AESEQ    = seq_len(nrow(ae_src)),
    AETERM   = ae_src$AETERM,
    AEDECOD  = ae_src$AETERM,
    AESTDY   = ae_src$AESTDT,
    AEENDY   = ae_src$AEENDT,
    AESEV    = fcase(
      ae_src$AEGR == 1L, "MILD",
      ae_src$AEGR == 2L, "MODERATE",
      ae_src$AEGR >= 3L, "SEVERE"
    ),
    AESER    = fifelse(ae_src$AESER == 1L, "Y", "N"),
    AEREL    = ae_src$AEREL,
    AEACN    = ae_src$AEACN,
    AEOUT    = ae_src$AEOUT,
    AETOXGR  = as.character(ae_src$AEGR)
  )

  # ─── LB Domain ──────────────────────────────────────────────────────────
  lb <- data.table(
    STUDYID  = "KN564",
    DOMAIN   = "LB",
    USUBJID  = lb_src$SUBJID,
    LBSEQ    = seq_len(nrow(lb_src)),
    LBTESTCD = lb_src$LBTEST,
    LBTEST   = fifelse(lb_src$LBTEST == "TSH",
                       "Thyroid Stimulating Hormone",
                       "Free Thyroxine"),
    LBORRES  = as.character(lb_src$LBORRES),
    LBORRESU = lb_src$LBORRESU,
    LBSTRESN = lb_src$LBORRES,
    LBNRIND  = lb_src$LBNRIND,
    LBBLFL   = lb_src$LBBLFL,
    LBDY     = lb_src$VISIT_DAY
  )

  # ─── TU Domain ──────────────────────────────────────────────────────────
  tu <- data.table(
    STUDYID  = "KN564",
    DOMAIN   = "TU",
    USUBJID  = tu_src$SUBJID,
    TUSEQ    = seq_len(nrow(tu_src)),
    TUEVAL   = tu_src$TUEVAL,
    TURESP   = tu_src$TURESP,
    TUDY     = tu_src$VISIT_DAY
  )

  # ─── DS Domain ──────────────────────────────────────────────────────────
  ds <- data.table(
    STUDYID  = "KN564",
    DOMAIN   = "DS",
    USUBJID  = ds_src$SUBJID,
    DSSEQ    = seq_len(nrow(ds_src)),
    DSDECOD  = ds_src$DSDECOD,
    DSCAT    = ds_src$DSCAT,
    DSSTDY   = ds_src$DSSTDT
  )

  # Write SDTM datasets
  domains <- list(dm = dm, ex = ex, ae = ae, lb = lb, tu = tu, ds = ds)
  for (nm in names(domains)) {
    fwrite(domains[[nm]], file.path(output_dir, paste0(toupper(nm), ".csv")))
  }

  message(sprintf("[sdtm] Written %d SDTM domains to %s", length(domains), output_dir))
  invisible(domains)
}
