# emit_source.R — Project trajectory -> source CRF CSVs
# KEYNOTE-564 IPD Causal-DAG Simulator
# No fresh randomness in this layer — deterministic transformation only.

source("R/dag_state.R")

#' Emit all source CRF CSV files from simulation results
#' @param bl data.table, baseline characteristics
#' @param longitudinal list, output from simulate_longitudinal (ae_long, lb_long, ex_long)
#' @param recurrence_dt data.table, recurrence outcomes
#' @param death_dt data.table, death/post-recurrence outcomes
#' @param endpoints data.table, derived endpoints
#' @param output_dir character, directory for output CSVs
emit_source_csvs <- function(bl, longitudinal, recurrence_dt, death_dt,
                              endpoints, output_dir = "output/source") {

  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  # ─── DM (Demographics) ──────────────────────────────────────────────────
  dm <- emit_dm(bl, endpoints)
  fwrite(dm, file.path(output_dir, "DM.csv"))

  # ─── EX (Exposure) ──────────────────────────────────────────────────────
  ex <- emit_ex(longitudinal$ex_long, bl)
  fwrite(ex, file.path(output_dir, "EX.csv"))

  # ─── AE (Adverse Events) ────────────────────────────────────────────────
  ae <- emit_ae(longitudinal$ae_long, longitudinal$ex_long)
  fwrite(ae, file.path(output_dir, "AE.csv"))

  # ─── LB (Laboratory) ────────────────────────────────────────────────────
  lb <- emit_lb(longitudinal$lb_long)
  fwrite(lb, file.path(output_dir, "LB.csv"))

  # ─── TU (Tumor Assessment) ──────────────────────────────────────────────
  tu <- emit_tu(bl, recurrence_dt)
  fwrite(tu, file.path(output_dir, "TU.csv"))

  # ─── RS (Disease Response) ──────────────────────────────────────────────
  rs <- emit_rs(bl, recurrence_dt, death_dt)
  fwrite(rs, file.path(output_dir, "RS.csv"))

  # ─── DS (Disposition) ───────────────────────────────────────────────────
  ds <- emit_ds(bl, longitudinal$ex_long, endpoints)
  fwrite(ds, file.path(output_dir, "DS.csv"))

  message(sprintf("[emit_source] Written %d source CSVs to %s",
                  7L, output_dir))

  invisible(list(dm = dm, ex = ex, ae = ae, lb = lb, tu = tu, rs = rs, ds = ds))
}

# ─── Individual Emitters ─────────────────────────────────────────────────────

emit_dm <- function(bl, endpoints) {
  dm <- bl[, .(SUBJID, AGE, SEX, RACE, REGION, ARM,
               RISK_CATEGORY, ECOG_BL, SARCOMATOID, PDL1_CPS, STRATUM)]

  # Add reference date (Day 1 = randomization)
  dm[, RANDDT := as.Date("2017-06-08") + sample(0:900, nrow(dm), replace = TRUE)]

  # Merge key endpoint flags
  dm <- merge(dm, endpoints[, .(SUBJID, DFS_EVENT, OS_EVENT)], by = "SUBJID", all.x = TRUE)

  dm
}

emit_ex <- function(ex_long, bl) {
  ex <- copy(ex_long)
  ex <- merge(ex, bl[, .(SUBJID, ARM)], by = "SUBJID", all.x = TRUE)

  ex[, `:=`(
    EXDOSU = "mg",
    EXROUTE = "INTRAVENOUS",
    EXTRT = fifelse(ARM == "PEMBROLIZUMAB", "PEMBROLIZUMAB 200MG", "PLACEBO")
  )]

  ex[, .(SUBJID, CYCLE, VISIT_DAY, EXTRT, EXDOSE, EXDOSU, EXROUTE,
         DOSE_STATUS, CUMULATIVE_DOSES)]
}

emit_ae <- function(ae_long, ex_long = NULL) {
  if (nrow(ae_long) == 0) return(data.table())

  ae <- copy(ae_long)

  # Add end date (duration varies by AE type)
  ae[, AEENDT := AESTDT + sample(7:42, .N, replace = TRUE)]

  # Serious AE: probabilistic, based on regulatory criteria (hospitalization,
  # life-threatening, disability) — NOT deterministic from grade.
  # Grade 3 AEs are often managed outpatient (not serious).
  # Some Grade 2 AEs requiring hospitalization are serious.
  ae[, AESER := {
    p_serious <- fcase(
      AEGR == 1L, 0.01,
      AEGR == 2L, 0.05,
      AEGR == 3L, 0.35,
      AEGR == 4L, 0.85,
      default = 0.01
    )
    as.integer(runif(.N) < p_serious)
  }]

  # Default action: NONE for low-grade, DOSE_HELD for grade 3
  ae[, AEACN := fcase(
    AEGR >= 4L, "DISCONTINUED",
    AEGR >= 3L, "DOSE_HELD",
    default = "NONE"
  )]

  # Link ALL discontinuations from EX to AEs: for every patient who discontinued,
  # attribute the discontinuation to their most severe recent AE.
  if (!is.null(ex_long) && nrow(ex_long) > 0) {
    disc_info <- ex_long[DOSE_STATUS == "DISCONTINUED",
                         .(DISC_DAY = min(VISIT_DAY)), by = SUBJID]
    if (nrow(disc_info) > 0) {
      ae <- merge(ae, disc_info, by = "SUBJID", all.x = TRUE)

      # For each discontinued patient, find the single "attributed" AE row index:
      # highest grade AE that started on or before disc day
      ae[, ROW_ID := .I]
      candidates <- ae[!is.na(DISC_DAY) & AESTDT <= DISC_DAY]
      if (nrow(candidates) > 0) {
        # Pick one AE per patient: max grade, then latest start date
        candidates[, SCORE := AEGR * 10000 + AESTDT]
        best <- candidates[, .SD[which.max(SCORE)], by = SUBJID]
        ae[ROW_ID %in% best$ROW_ID, AEACN := "DISCONTINUED"]
      }
      ae[, c("DISC_DAY", "ROW_ID") := NULL]
    }
  }

  # Outcome
  ae[, AEOUT := fcase(
    AECAT == "THYROID" & AETERM == "HYPOTHYROIDISM", "ONGOING",
    AEGR >= 4L, sample(c("RESOLVED", "ONGOING"), .N, replace = TRUE, prob = c(0.7, 0.3)),
    default = "RESOLVED"
  )]

  ae[, .(SUBJID, AETERM, AESTDT, AEENDT, AEGR, AESER, AEREL, AEACN, AECAT, AEOUT)]
}

emit_lb <- function(lb_long) {
  lb <- copy(lb_long)

  # Mark baseline (first visit)
  lb[, LBBLFL := fifelse(VISIT_DAY == min(VISIT_DAY), "Y", "N"), by = .(SUBJID, LBTEST)]

  lb[, .(SUBJID, VISIT_DAY, LBTEST, LBORRES, LBORRESU, LBNRIND, LBBLFL)]
}

emit_tu <- function(bl, recurrence_dt) {
  imaging_days <- IMAGING_SCHEDULE

  # Create one TU record per patient per imaging visit (up to event or censor)
  tu_list <- lapply(seq_len(nrow(bl)), function(i) {
    subjid <- bl$SUBJID[i]
    rec_day <- recurrence_dt[SUBJID == subjid, OBSERVED_RECURRENCE_DAY]
    rec_type <- recurrence_dt[SUBJID == subjid, RECURRENCE_TYPE]

    # Patient has imaging visits until recurrence or admin censor
    max_img_day <- if (!is.na(rec_day)) rec_day else KN564_CONSTANTS$ADMIN_CENSOR_DAY
    visit_days <- imaging_days[imaging_days <= max_img_day]

    if (length(visit_days) == 0) return(data.table())

    dt <- data.table(
      SUBJID = subjid,
      VISIT_DAY = visit_days,
      TUEVAL = "INVESTIGATOR"
    )

    # Response at each visit
    dt[, TURESP := fifelse(
      !is.na(rec_day) & VISIT_DAY == rec_day,
      fifelse(!is.na(rec_type) & rec_type == "DISTANT",
              "RECURRENCE_DISTANT", "RECURRENCE_LOCAL"),
      "NED"
    )]

    dt
  })

  rbindlist(tu_list, fill = TRUE)
}

emit_rs <- function(bl, recurrence_dt, death_dt) {
  imaging_days <- IMAGING_SCHEDULE

  rs_list <- lapply(seq_len(nrow(bl)), function(i) {
    subjid <- bl$SUBJID[i]
    rec_day <- recurrence_dt[SUBJID == subjid, OBSERVED_RECURRENCE_DAY]
    death_day <- death_dt[SUBJID == subjid, DEATH_DAY]

    max_day <- KN564_CONSTANTS$ADMIN_CENSOR_DAY
    visit_days <- imaging_days[imaging_days <= max_day]

    if (length(visit_days) == 0) return(data.table())

    dt <- data.table(
      SUBJID = subjid,
      VISIT_DAY = visit_days,
      RSEVAL = "INVESTIGATOR"
    )

    dt[, RSSTRESC := fcase(
      !is.na(rec_day) & VISIT_DAY >= rec_day, "RECURRED",
      !is.na(death_day) & VISIT_DAY >= death_day, "DEAD",
      default = "DISEASE_FREE"
    )]

    dt
  })

  rbindlist(rs_list, fill = TRUE)
}

emit_ds <- function(bl, ex_long, endpoints) {
  # Determine disposition for each patient
  # Treatment disposition
  treat_disp <- ex_long[, .(
    LAST_CYCLE = max(CYCLE),
    LAST_STATUS = DOSE_STATUS[.N]
  ), by = SUBJID]

  ds <- merge(bl[, .(SUBJID, ARM)], treat_disp, by = "SUBJID", all.x = TRUE)
  ds <- merge(ds, endpoints[, .(SUBJID, DFS_DAY, DFS_EVENT, OS_EVENT)],
              by = "SUBJID", all.x = TRUE)

  # Treatment disposition
  ds[, `:=`(
    DSCAT = "TREATMENT",
    DSSTDT = fifelse(is.na(LAST_CYCLE), 1L,
                     as.integer(LAST_CYCLE * KN564_CONSTANTS$CYCLE_LENGTH)),
    DSDECOD = fcase(
      LAST_STATUS == "DISCONTINUED" | is.na(LAST_STATUS), "ADVERSE_EVENT",
      LAST_CYCLE >= KN564_CONSTANTS$MAX_CYCLES, "COMPLETED",
      OS_EVENT == 1L, "DEATH",
      default = "COMPLETED"
    )
  )]

  # Override: patients who completed all cycles
  ds[LAST_CYCLE >= KN564_CONSTANTS$MAX_CYCLES & LAST_STATUS == "GIVEN",
     DSDECOD := "COMPLETED"]

  ds[, .(SUBJID, ARM, DSSTDT, DSDECOD, DSCAT)]
}
