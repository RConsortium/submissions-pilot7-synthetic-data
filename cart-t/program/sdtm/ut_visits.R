## Shared SDTM helpers — visit map, USUBJID construction, ARM mapping.
## Source this from every program in program/sdtm/.

visit_map <- c(
  SE_ENROLLMENT             = 1,
  SE_BASELINE               = 2,
  SE_LABS                   = 3,
  SE_ADVERSEEVENTS          = 4,
  SE_CONCOMITANTMEDICATIONS = 5,
  SE_CONMEDCODING           = 6,
  SE_QUALITYOFLIFE          = 7,
  SE_ENDPOINT               = 8,
  SE_ADJUDICATION           = 9,
  SE_DISPOSITION            = 10,
  SE_SOURCEDOCUMENTS        = 11,
  SE_MISCFORMCAPABILITIES   = 99
)

derive_visitnum <- function(studyeventoid) {
  unname(visit_map[studyeventoid])
}

make_usubjid <- function(studysubjectid,
                         studyid = "CART-T-PILOT",
                         siteid  = "01") {
  paste(studyid, siteid, studysubjectid, sep = "-")
}

## Treatment arm derivation.
## This study has no actual treatment differentiation (RECEIVEDINTERVENTION = No
## for every subject). PROFILE is a demographic phenotype used for randomization
## stratification, not a treatment arm. Therefore:
##   - ARMCD = "TREATMENT" for subjects who were randomized (have a PROFILE)
##   - ARMCD = "SCRNFAIL"  for subjects who were not randomized
## Phenotype/cohort is preserved separately via phenotype_code() / phenotype_label().
armcd_map <- function(profile) {
  ifelse(is.na(profile) | !nzchar(trimws(profile)), "SCRNFAIL", "TREATMENT")
}

## Coerce raw date strings to ISO 8601 yyyy-mm-dd. Handles:
##   - yyyy-mm-dd            -> as-is
##   - mm/dd/yyyy            -> yyyy-mm-dd
##   - m/d/yy                -> yyyy-mm-dd (yy<70 -> 20yy, else 19yy)
##   - yyyy                  -> yyyy
## Anything else returns NA so downstream date conversions don't silently bend.
normalize_iso_date <- function(x) {
  out <- rep(NA_character_, length(x))
  ok  <- !is.na(x) & nzchar(x)
  x   <- trimws(x)

  is_iso <- ok & grepl("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", x)
  out[is_iso] <- x[is_iso]

  is_year <- ok & grepl("^[0-9]{4}$", x) & !is_iso
  out[is_year] <- x[is_year]

  is_us <- ok & !is_iso & !is_year & grepl("^[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}$", x)
  if (any(is_us)) {
    parts <- strsplit(x[is_us], "/", fixed = TRUE)
    iso <- vapply(parts, function(p) {
      m <- sprintf("%02d", as.integer(p[1]))
      d <- sprintf("%02d", as.integer(p[2]))
      yy <- as.integer(p[3])
      yy <- if (nchar(p[3]) == 2) ifelse(yy < 70, 2000L + yy, 1900L + yy) else yy
      sprintf("%04d-%s-%s", yy, m, d)
    }, character(1))
    out[is_us] <- iso
  }
  out
}

arm_map <- function(profile) {
  ifelse(is.na(profile) | !nzchar(trimws(profile)),
         "Screen Failure",
         "Study Treatment")
}

## Phenotype / stratification cohort derived from PROFILE.
## Use phenotype_code() for short codes (≤ 8 chars, suitable for STRAT1)
## and phenotype_label() for the descriptive label (STRAT1L).
phenotype_code <- function(profile) {
  p <- toupper(trimws(profile))
  dplyr::case_when(
    is.na(p) | !nzchar(p)             ~ NA_character_,
    grepl("NON-HISPANIC MALE", p)     ~ "NHM",
    grepl("NON-HISPANIC FEMALE", p)   ~ "NHF",
    grepl("HISPANIC MALE", p)         ~ "HM",
    grepl("HISPANIC FEMALE", p)       ~ "HF",
    TRUE                              ~ "OTHER"
  )
}

phenotype_label <- function(profile) {
  p <- toupper(trimws(profile))
  dplyr::case_when(
    is.na(p) | !nzchar(p)             ~ NA_character_,
    grepl("NON-HISPANIC MALE", p)     ~ "Non-Hispanic male",
    grepl("NON-HISPANIC FEMALE", p)   ~ "Non-Hispanic female",
    grepl("HISPANIC MALE", p)         ~ "Hispanic male",
    grepl("HISPANIC FEMALE", p)       ~ "Hispanic female",
    TRUE                              ~ "Other"
  )
}
