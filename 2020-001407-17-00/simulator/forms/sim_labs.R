#' =============================================================================
#' Domain: LB (Laboratory) — hematology / chemistry / urinalysis / screens /
#'         pregnancy. One row per analyte with a real (non-blank, non-unit) value.
#' =============================================================================

LB_COLUMNS <- c("STUDYID", "DOMAIN", "USUBJID", "LBSEQ", "LBTESTCD", "LBTEST",
                "LBCAT", "LBORRES", "LBORRESU", "LBSTRESC", "LBSTRESN", "LBSPEC",
                "VISITNUM", "VISIT", "LBTPT", "LBDTC", "LBDY")

# Curated short codes; unknown analytes fall back to an alnum slug.
.LB_TESTCD <- c(
  "hemoglobin" = "HGB", "hematocrit" = "HCT", "platelets" = "PLAT",
  "leukocytes" = "WBC", "erythrocytes" = "RBC",
  "ery. mean corpuscular volume" = "MCV",
  "ery. mean corpuscular hemoglobin" = "MCH",
  "ery. mean corpuscular hgb concentration" = "MCHC",
  "neutrophils percentage" = "NEUTLE", "lymphocytes percentage" = "LYMLE",
  "monocytes percentage" = "MONOLE", "eosinophils percentage" = "EOSLE",
  "basophils percentage" = "BASOLE", "neutrophils absolute" = "NEUT",
  "lymphocytes absolute" = "LYM", "monocytes absolute" = "MONO",
  "eosinophils absolute" = "EOS", "basophils absolute" = "BASO",
  "prothrombin time (pt)" = "PT", "partial prothrombin time (ptt)" = "APTT",
  "international normalized ratio (inr)" = "INR",
  "red cell distribution width (rdw)" = "RDW",
  "blood urea nitrogen" = "BUN", "glucose" = "GLUC", "protein" = "PROT",
  "urobilinogen" = "UROBIL", "occult blood" = "OCCBLD", "ketones" = "KETONES",
  "bilirubin" = "BILI", "nitrite" = "NITRITE",
  "leukocyte esterase" = "LEUKEST", "specific gravity" = "SPGRAV", "ph" = "PH")

.lb_testcd <- function(field) {
  key <- tolower(trimws(field))
  if (!is.na(.LB_TESTCD[key])) return(unname(.LB_TESTCD[key]))
  slug <- gsub("[^A-Z0-9]", "", toupper(field))
  if (nchar(slug) == 0) "LBTEST" else substr(slug, 1, 8)
}

.LB_META_PREFIX <- c("if ", "was ", "were ", "did ", "has ", "any ", "yes,")
.LB_META_EXACT <- c("planned time point", "date of sample collection",
                    "time of sample collection", "specimen type", "result")

.is_lab_meta <- function(field) {
  f <- tolower(trimws(field))
  if (any(startsWith(f, .LB_META_PREFIX))) return(TRUE)
  if (grepl("specify parameters", f) || f %in% .LB_META_EXACT) return(TRUE)
  FALSE
}

build_lb <- function(patient, cases) {
  usubjid <- usubjid_of(patient)
  ref <- patient$baseline_date
  lab_forms <- c("hematology", "chemistry", "urinalysis", "cotinine_test",
                 "alcohol_test", "drugs_of_abuse_screen", "pregnancy_test",
                 "fsh_test")
  rows <- list(); seq <- 0L

  for (e in iter_domain_records(cases, function(f) f %in% lab_forms)) {
    rec <- e$rec; form <- e$form
    if (tolower(rec_get(rec, "Was the sample collected?") %||% "yes") == "no") next
    d <- parse_date(rec_get(rec, "Date of Sample Collection"))
    dtc <- iso_dtc(d, rec_get(rec, "Time of Sample Collection"))
    spec <- toupper(rec_get(rec, "Specimen Type") %||% "")
    tpt <- rec_get(rec, "Planned Time Point") %||% ""

    emit <- function(testcd, test, cat, orres, unit = "") {
      num <- as_number(orres)
      seq <<- seq + 1L
      rows[[seq]] <<- list(
        STUDYID = SIM_CONFIG$study_id, DOMAIN = "LB", USUBJID = usubjid,
        LBSEQ = seq, LBTESTCD = testcd, LBTEST = test, LBCAT = cat,
        LBORRES = orres, LBORRESU = unit, LBSTRESC = as.character(orres),
        LBSTRESN = num %||% "", LBSPEC = spec, VISITNUM = e$vnum,
        VISIT = e$vlabel, LBTPT = tpt, LBDTC = dtc, LBDY = study_day(d, ref))
    }

    if (form == "hematology") {
      cat <- "HEMATOLOGY"
    } else if (form == "chemistry") {
      cat <- "CHEMISTRY"
    } else if (form == "urinalysis") {
      cat <- "URINALYSIS"
    } else if (form == "cotinine_test") {
      v <- real_value(rec_get(rec, "Result"))
      if (!is.null(v)) emit("COTININE", "Cotinine", "SPECIAL CHEMISTRY", v)
      next
    } else if (form == "alcohol_test") {
      v <- real_value(rec_get(rec, "Result"))
      if (!is.null(v)) emit("ALCOHOL", "Alcohol", "SPECIAL CHEMISTRY", v)
      next
    } else if (form == "drugs_of_abuse_screen") {
      v <- real_value(rec_get(rec, "Result"))
      if (!is.null(v)) emit("DRUGSCR", "Drugs of Abuse Screen", "DRUG SCREEN", v)
      next
    } else if (form == "pregnancy_test") {
      if (tolower(rec_get(rec, "Was Pregnancy Test Performed?") %||% "") == "yes") {
        v <- real_value(rec_get(rec, "Result"))
        if (!is.null(v)) emit("HCG", "Pregnancy Test", "PREGNANCY", v)
      }
      next
    } else {
      next  # fsh_test: collection only, no analyte value on the CRF
    }

    for (field in names(rec)) {
      if (.is_lab_meta(field)) next
      v <- real_value(rec[[field]])
      if (is.null(v)) next
      emit(.lb_testcd(field), field, cat, v)
    }
  }
  rows
}
