## --------------------------------------------------------------------
## CM — Concomitant Medications
## Spec:   spec/sdtm/cm.yaml
## Inputs: data/raw/cm.rds (ConMed), data/sdtm/dm.rds (RFSTDTC reference)
## Output: data/sdtm/cm.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

raw <- readRDS("data/raw/cm.rds")
dm  <- readRDS("data/sdtm/dm.rds")

key_link <- raw |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

cm_items <- c("CMTRTL", "CMTRTLX", "MEDNAME",
              "CMDOSE", "CMDOSU", "CMDOSUTXT",
              "CMDOSFRM", "CMDOSFRMTEXT", "CMDOSFRQ", "CMROUTE",
              "CMINDC", "CMSTDAT", "CMENDAT", "ONGOING",
              "RXCUI", "RXAUI", "RXSTR", "RXTTY", "RXTYPE")

wide <- raw |>
  filter(itemgroupname == "group1", itemname %in% cm_items) |>
  select(subjectkey, itemgrouprepeatkey,
         eventname, studyeventoid, startdate,
         itemname, value) |>
  pivot_wider(names_from = itemname, values_from = value,
              values_fn = ~ dplyr::first(.x))

## --------------------------------------------------------------------
## CT mappings (raw → CDISC CT)
##   Values without a CT match return NA — raw value remains in the raw
##   RDS for audit; documented as a residual data limitation in the
##   domain knowledge file.
## --------------------------------------------------------------------

# CDISC FRM (C66726). OpenClinica codelist CL_207 ↔ CDISC FRM terms.
map_dosfrm <- function(x) {
  v <- trimws(x)
  dplyr::case_when(
    is.na(v) | !nzchar(v)       ~ NA_character_,
    toupper(v) == "AEROSOL"     ~ "AEROSOL",
    toupper(v) == "CAPSULE"     ~ "CAPSULE",
    toupper(v) == "CREAM"       ~ "CREAM",
    toupper(v) == "GEL"         ~ "GEL",
    toupper(v) == "OINTMENT"    ~ "OINTMENT",
    toupper(v) == "PATCH"       ~ "PATCH",
    toupper(v) == "POWDER"      ~ "POWDER",
    toupper(v) == "SPRAY"       ~ "SPRAY",
    toupper(v) == "SUPPOSITORY" ~ "SUPPOSITORY",
    toupper(v) == "SUSPENSION"  ~ "SUSPENSION",
    toupper(v) == "TABLET"      ~ "TABLET",
    toupper(v) == "LIQUID"      ~ "LIQUID",
    toupper(v) == "GAS"         ~ "GAS",
    toupper(v) == "IMPLANT"     ~ "IMPLANT",
    toupper(v) == "CHEWABLE"    ~ "CHEWABLE TABLET",
    TRUE                        ~ NA_character_      # "Other" and free-text
  )
}

# CDISC FREQ (C71113). OpenClinica codelist CL_209 ↔ CDISC FREQ terms.
map_dosfrq <- function(x) {
  v <- trimws(x)
  dplyr::case_when(
    is.na(v) | !nzchar(v)                         ~ NA_character_,
    v == "QD (once a day)"                        ~ "QD",
    v == "BID (twice a day)"                      ~ "BID",
    v == "TID (three times a day)"                ~ "TID",
    v == "QID (four times a day)"                 ~ "QID",
    v == "QH (every hour)"                        ~ "QH",
    v == "QM (every month)"                       ~ "QM",
    v == "QOM (every other mo)"                   ~ "QOM",
    v == "QOD (every other day)"                  ~ "QOD",
    v == "PC (after meals)"                       ~ "PC",
    v == "AC (before meals)"                      ~ "AC",
    v == "PRN (as needed)"                        ~ "PRN",
    TRUE                                          ~ NA_character_  # numeric codes, "Other"
  )
}

# CDISC UNIT (C71620). Free-text → uppercased CT.
map_dosu <- function(x) {
  v <- trimws(x)
  dplyr::case_when(
    is.na(v) | !nzchar(v) ~ NA_character_,
    toupper(v) == "MG"    ~ "mg",
    toupper(v) == "G"     ~ "g",
    toupper(v) == "L"     ~ "L",
    toupper(v) == "ML"    ~ "mL",
    v == "µg"        ~ "ug",     # micro sign
    toupper(v) == "MCG"   ~ "ug",     # CMDOSUTXT free-text
    toupper(v) == "UG"    ~ "ug",
    TRUE                  ~ NA_character_  # "Other", "mg/m^2"
  )
}

# CDISC ROUTE (C66729). OpenClinica codelist CL_211 ↔ CDISC ROUTE terms.
map_route <- function(x) {
  v <- trimws(x)
  dplyr::case_when(
    is.na(v) | !nzchar(v)        ~ NA_character_,
    toupper(v) == "ORAL"         ~ "ORAL",
    toupper(v) == "TOPICAL"      ~ "TOPICAL",
    toupper(v) == "SUBCUTANEOUS" ~ "SUBCUTANEOUS",
    toupper(v) == "INTRAVANEOUS" ~ "INTRAVENOUS",     # spelling fix
    toupper(v) == "INTRAVENOUS"  ~ "INTRAVENOUS",
    toupper(v) == "INTRAMUSCULAR"~ "INTRAMUSCULAR",
    toupper(v) == "INTRAPERITONEAL" ~ "INTRAPERITONEAL",
    toupper(v) == "INTRADERMAL"  ~ "INTRADERMAL",
    toupper(v) == "INTROACULAR"  ~ "INTRAOCULAR",     # spelling fix
    toupper(v) == "NASAL"        ~ "NASAL",
    toupper(v) == "VAGINAL"      ~ "VAGINAL",
    toupper(v) == "RECTAL"       ~ "RECTAL",
    toupper(v) == "TRANSDERMAL"  ~ "TRANSDERMAL",
    toupper(v) == "INHALATION"   ~ "INHALATION",
    TRUE                         ~ NA_character_      # numeric codes, "Other"
  )
}

## --------------------------------------------------------------------
## Build CM
## --------------------------------------------------------------------

dm_ref <- dm |> select(USUBJID, RFSTDTC, RFENDTC)

cm <- wide |>
  filter(!is.na(CMTRTL) & nzchar(CMTRTL)) |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  left_join(dm_ref, by = "USUBJID") |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "CM",
    CMTRT    = CMTRTL,
    CMDECOD  = MEDNAME,
    CMDOSE   = suppressWarnings(as.numeric(CMDOSE)),
    CMDOSU   = map_dosu(dplyr::coalesce(CMDOSU, CMDOSUTXT)),
    CMDOSFRM = map_dosfrm(dplyr::coalesce(CMDOSFRM, CMDOSFRMTEXT)),
    CMDOSFRQ = map_dosfrq(CMDOSFRQ),
    CMROUTE  = map_route(CMROUTE),
    CMINDC   = CMINDC,
    CMSTDTC  = normalize_iso_date(CMSTDAT),
    CMENDTC_raw = normalize_iso_date(CMENDAT),
    # ONGOING values: "Yes" / "No" / "1" — only "Yes" is the affirmative.
    is_ongoing = !is.na(ONGOING) & toupper(trimws(ONGOING)) == "YES",
    CMENDTC  = dplyr::if_else(is_ongoing, NA_character_, CMENDTC_raw),
    # SD0013: drop CMENDTC when it precedes CMSTDTC (data-entry inversion).
    CMENDTC  = dplyr::if_else(
                  !is.na(CMSTDTC) & !is.na(CMENDTC) & CMENDTC < CMSTDTC,
                  NA_character_, CMENDTC),
    # SD0021: relative-timing variables justify missing CMENDTC.
    #   ONGOING=Yes ⇒ "ONGOING" / "DATE OF LAST ASSESSMENT"
    #   Other missing-end rows ⇒ "UNKNOWN" / "DATE OF LAST ASSESSMENT"
    CMENRTPT = dplyr::case_when(
                  is_ongoing                          ~ "ONGOING",
                  is.na(CMENDTC)                      ~ "UNKNOWN",
                  TRUE                                ~ NA_character_),
    CMENTPT  = dplyr::if_else(is.na(CMENDTC),
                              "DATE OF LAST ASSESSMENT",
                              NA_character_),
    # SD0022: justify missing CMSTDTC.
    CMSTRTPT = dplyr::if_else(is.na(CMSTDTC), "UNKNOWN", NA_character_),
    CMSTTPT  = dplyr::if_else(is.na(CMSTDTC), "DATE OF FIRST ASSESSMENT",
                              NA_character_),
    # Study days (SDTMIG: skip day 0; date on/after RFSTDTC ⇒ +1).
    CMSTDY = dplyr::if_else(
        !is.na(CMSTDTC) & !is.na(RFSTDTC),
        as.integer(as.Date(CMSTDTC) - as.Date(RFSTDTC)) +
          ifelse(CMSTDTC >= RFSTDTC, 1L, 0L),
        NA_integer_),
    CMENDY = dplyr::if_else(
        !is.na(CMENDTC) & !is.na(RFSTDTC),
        as.integer(as.Date(CMENDTC) - as.Date(RFSTDTC)) +
          ifelse(CMENDTC >= RFSTDTC, 1L, 0L),
        NA_integer_),
    VISITNUM = derive_visitnum(studyeventoid),
    VISIT    = eventname
  ) |>
  arrange(USUBJID, CMSTDTC, CMTRT) |>
  mutate(CMSEQ = row_number(), .by = USUBJID) |>
  # SD1079: variable order follows SDTMIG v3.3 CM specification.
  # SD1076: CMRXCUI removed (non-standard, not in SDTMIG v3.3).
  # SD1078: CMMODIFY dropped (all-NA in this export — no coding modifications).
  select(STUDYID, DOMAIN, USUBJID, CMSEQ,
         CMTRT, CMDECOD, CMINDC,
         CMDOSE, CMDOSU, CMDOSFRM, CMDOSFRQ, CMROUTE,
         CMSTDTC, CMENDTC, CMSTDY, CMENDY,
         CMSTRTPT, CMSTTPT, CMENRTPT, CMENTPT,
         VISITNUM, VISIT)

saveRDS(cm, "data/sdtm/cm.rds")

cat(sprintf("CM written: %d rows x %d cols\n", nrow(cm), ncol(cm)))
cat(sprintf("Unique subjects: %d\n", length(unique(cm$USUBJID))))
cat(sprintf("CMSTDTC  non-null: %d / %d\n",
            sum(!is.na(cm$CMSTDTC)),  nrow(cm)))
cat(sprintf("CMENDTC  non-null: %d / %d\n",
            sum(!is.na(cm$CMENDTC)),  nrow(cm)))
cat(sprintf("CMENRTPT non-null: %d / %d  (ONGOING justifications)\n",
            sum(!is.na(cm$CMENRTPT)), nrow(cm)))
cat(sprintf("CMSTRTPT non-null: %d / %d  (UNKNOWN start justifications)\n",
            sum(!is.na(cm$CMSTRTPT)), nrow(cm)))
cat(sprintf("CMSTDY   non-null: %d / %d\n",
            sum(!is.na(cm$CMSTDY)),   nrow(cm)))
cat(sprintf("CMENDY   non-null: %d / %d\n",
            sum(!is.na(cm$CMENDY)),   nrow(cm)))
