## --------------------------------------------------------------------
## MH — Medical History
## Spec:   spec/sdtm/mh.yaml
## Inputs: data/raw/dm.rds (group1, group2 item groups), data/sdtm/dm.rds (RFSTDTC)
## Output: data/sdtm/mh.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

raw <- readRDS("data/raw/dm.rds")
dm  <- readRDS("data/sdtm/dm.rds")

key_link <- raw |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

## --- decode maps (from car-t-openclinica.xml) ------------------------

body_decode <- c(
  "1" = "Cardiovascular", "2" = "Respiratory", "3" = "Gastrointestinal",
  "4" = "Genitourinary",  "5" = "Musculoskeletal", "6" = "Neurological",
  "7" = "Endocrinological", "8" = "Dermatologic/Skin",
  "9" = "Hematologic/Lymphatic")

cancer1_decode <- c(
  "1" = "Carcinoma", "2" = "Leukemia", "3" = "Lymphoma",
  "4" = "Sarcoma",  "5" = "Myeloma")

cancer2_decode <- c(
  "1"  = "Adenocarcinoma",
  "2"  = "Small cell carcinoma",
  "3"  = "Squamous cell carcinoma",
  "4"  = "Large cell carcinoma",
  "5"  = "Transitional cell carcinoma",
  "6"  = "Undifferentiated carcinoma",
  "7"  = "Soft tissue sarcoma",
  "8"  = "Bone sarcoma",
  "9"  = "Fibroblastic sarcoma",
  "10" = "Rhabdomyosarcoma",
  "11" = "Gastrointestinal stromal tumor (GIST)",
  "12" = "Leiomyosarcoma",
  "13" = "Liposarcoma",
  "14" = "Osteosarcoma",
  "15" = "Ewing's sarcoma",
  "16" = "Chondrosarcoma",
  "17" = "B-cell lymphoma",
  "18" = "T-cell lymphoma",
  "19" = "Burkitt's lymphoma",
  "20" = "Follicular lymphoma",
  "21" = "Mantle cell lymphoma",
  "22" = "Acute myeloid leukemia (AML)",
  "23" = "Chronic myeloid leukemia (CML)",
  "24" = "Acute lymphocytic leukemia (ALL)",
  "25" = "Chronic lymphocytic leukemia (CLL)",
  "26" = "IgG myeloma",
  "27" = "IgA myeloma",
  "28" = "IgM myeloma",
  "29" = "IgD myeloma",
  "30" = "IgE myeloma")

cancerorg_decode <- c(
  "1" = "Breast", "2" = "Colon", "3" = "Prostate", "4" = "Stomach",
  "5" = "Pancreas", "6" = "Lung", "7" = "Esophageal", "8" = "Colorectal",
  "9" = "Cervix", "10" = "GI Tract")

decode_org <- function(x) {
  ## "1,4,7" -> "Breast, Stomach, Esophageal"
  vapply(x, function(s) {
    if (is.na(s) || !nzchar(s)) return(NA_character_)
    parts <- trimws(strsplit(s, ",", fixed = TRUE)[[1]])
    labs  <- cancerorg_decode[parts]
    keep  <- !is.na(labs)
    if (!any(keep)) return(NA_character_)
    paste(labs[keep], collapse = ", ")
  }, character(1))
}

## --- group1: general medical history --------------------------------
## Items: DIAG (term), BODY (subcategory code), DATE (start),
##        ONG (ongoing flag — "1"=Yes / "0"=No / blank), STOP (end)

mh_group1 <- raw |>
  filter(itemgroupname == "group1",
         itemname %in% c("DIAG", "BODY", "DATE", "ONG", "STOP")) |>
  select(subjectkey, itemgrouprepeatkey, eventname, studyeventoid,
         startdate, itemname, value) |>
  pivot_wider(names_from = itemname, values_from = value,
              values_fn = ~ dplyr::first(.x)) |>
  filter(!is.na(DIAG) & nzchar(DIAG)) |>
  transmute(
    subjectkey,
    eventname, studyeventoid, startdate,
    MHCAT      = "GENERAL MEDICAL HISTORY",
    MHTERM     = DIAG,
    MHSCAT     = dplyr::coalesce(body_decode[as.character(BODY)], NA_character_),
    MHSTDTC    = normalize_iso_date(DATE),
    MHENDTC    = normalize_iso_date(STOP),
    is_ongoing = !is.na(ONG) & trimws(ONG) == "1",
    MHSPID     = NA_character_
  )

## --- group2: cancer history -----------------------------------------
## Items: CANCER1 (primary type, CL_68), CANCER2 (specific subtype,
##        CL_69), CANCERORG (multi-select organ, MSL_70), DIAGNOSED.

mh_group2 <- raw |>
  filter(itemgroupname == "group2",
         itemname %in% c("CANCER1", "CANCER2", "CANCERORG", "DIAGNOSED")) |>
  select(subjectkey, itemgrouprepeatkey, eventname, studyeventoid,
         startdate, itemname, value) |>
  pivot_wider(names_from = itemname, values_from = value,
              values_fn = ~ dplyr::first(.x)) |>
  mutate(
    term1   = dplyr::coalesce(cancer1_decode[as.character(CANCER1)], CANCER1),
    term2   = dplyr::coalesce(cancer2_decode[as.character(CANCER2)], CANCER2),
    org_lbl = decode_org(CANCERORG))

mh_group2_long <- bind_rows(
  ## CANCER1 row — primary cancer type
  mh_group2 |>
    filter(!is.na(term1) & nzchar(term1)) |>
    transmute(
      subjectkey, eventname, studyeventoid, startdate,
      MHCAT      = "CANCER HISTORY",
      MHTERM     = term1,
      MHSCAT     = NA_character_,
      MHSTDTC    = normalize_iso_date(DIAGNOSED),
      MHENDTC    = NA_character_,
      is_ongoing = FALSE,
      MHSPID     = org_lbl),
  ## CANCER2 row — emit only when distinct from CANCER1 (SD1201 fix:
  ## 46 raw records have CANCER1 == CANCER2, which previously produced
  ## identical duplicate rows).
  mh_group2 |>
    filter(!is.na(term2) & nzchar(term2) & (is.na(term1) | term1 != term2)) |>
    transmute(
      subjectkey, eventname, studyeventoid, startdate,
      MHCAT      = "CANCER HISTORY",
      MHTERM     = term2,
      MHSCAT     = NA_character_,
      MHSTDTC    = normalize_iso_date(DIAGNOSED),
      MHENDTC    = NA_character_,
      is_ongoing = FALSE,
      MHSPID     = org_lbl)
)

## --- combine, join DM, fix inversion, derive timing -----------------
mh <- bind_rows(mh_group1, mh_group2_long) |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  left_join(dm |> select(USUBJID, RFSTDTC), by = "USUBJID") |>
  ## SD0013 — null out demonstrably inverted end dates (data-entry error).
  mutate(MHENDTC = dplyr::if_else(
    !is.na(MHSTDTC) & !is.na(MHENDTC) & MHENDTC < MHSTDTC,
    NA_character_, MHENDTC)) |>
  arrange(USUBJID, MHCAT, MHTERM, MHSTDTC, MHENDTC) |>
  ## Safety net: drop any residual true duplicates on the natural key.
  distinct(USUBJID, MHCAT, MHTERM, MHSTDTC, MHENDTC, MHSCAT, .keep_all = TRUE) |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "MH",
    MHDECOD  = NA_character_,   # MedDRA coding gap — see domain notes
    MHBODSYS = NA_character_,   # MedDRA coding gap — see domain notes
    ## SD0021 — End Time-Point justification when MHENDTC is missing.
    ##   ongoing condition: MHENRF="ONGOING" + MHENRTPT="ONGOING"
    ##                                       + MHENTPT="DATE OF LAST ASSESSMENT"
    ##   missing end date: MHENRTPT="UNKNOWN" + MHENTPT="DATE OF LAST ASSESSMENT"
    MHENRF   = dplyr::if_else(is_ongoing, "ONGOING", NA_character_),
    MHENRTPT = dplyr::case_when(
      is_ongoing     ~ "ONGOING",
      is.na(MHENDTC) ~ "UNKNOWN",
      TRUE           ~ NA_character_),
    MHENTPT  = dplyr::if_else(is.na(MHENDTC),
                              "DATE OF LAST ASSESSMENT", NA_character_),
    ## SD0022 — Start Time-Point justification when MHSTDTC is missing.
    MHSTRTPT = dplyr::if_else(is.na(MHSTDTC), "UNKNOWN", NA_character_),
    MHSTTPT  = dplyr::if_else(is.na(MHSTDTC),
                              "DATE OF FIRST ASSESSMENT", NA_character_),
    ## SD1088 — MHSTDY relative to DM.RFSTDTC (skip day 0).
    .d_st = suppressWarnings(as.Date(MHSTDTC)),
    .d_rf = suppressWarnings(as.Date(RFSTDTC)),
    MHSTDY = dplyr::if_else(
      !is.na(.d_st) & !is.na(.d_rf),
      as.integer(.d_st - .d_rf) + dplyr::if_else(.d_st >= .d_rf, 1L, 0L),
      NA_integer_),
    VISITNUM = derive_visitnum(studyeventoid),
    VISIT    = eventname
  ) |>
  mutate(MHSEQ = row_number(), .by = USUBJID) |>
  ## SD1079 — variable order per SDTMIG v3.3 MH specification.
  ## SD1078 / SD1076 — dropped MHPRESP, MHOCCUR, MHSTAT (always-null
  ## permissibles in this study; CRF carries no pre-specified questions
  ## and form-completion status is not surfaced).
  select(STUDYID, DOMAIN, USUBJID, MHSEQ, MHSPID,
         MHTERM, MHDECOD, MHCAT, MHSCAT, MHBODSYS,
         MHSTDTC, MHENDTC, MHSTDY,
         MHSTRTPT, MHSTTPT, MHENRF, MHENRTPT, MHENTPT,
         VISITNUM, VISIT)

saveRDS(mh, "data/sdtm/mh.rds")

cat(sprintf("MH written: %d rows x %d cols\n", nrow(mh), ncol(mh)))
cat(sprintf("Unique subjects: %d\n", length(unique(mh$USUBJID))))
cat(sprintf("MHSTDTC  non-null: %d / %d\n",
            sum(!is.na(mh$MHSTDTC)), nrow(mh)))
cat(sprintf("MHENDTC  non-null: %d / %d\n",
            sum(!is.na(mh$MHENDTC)), nrow(mh)))
cat(sprintf("MHENRF   non-null: %d  (ONGOING)\n",      sum(!is.na(mh$MHENRF))))
cat(sprintf("MHENRTPT non-null: %d  (end justified)\n",  sum(!is.na(mh$MHENRTPT))))
cat(sprintf("MHSTRTPT non-null: %d  (start justified)\n",sum(!is.na(mh$MHSTRTPT))))
cat(sprintf("MHSTDY   non-null: %d / %d\n",
            sum(!is.na(mh$MHSTDY)), nrow(mh)))
cat(sprintf("Date inversions remaining: %d\n",
            sum(!is.na(mh$MHSTDTC) & !is.na(mh$MHENDTC) &
                  mh$MHENDTC < mh$MHSTDTC)))
cat(sprintf("Dup-key (USUBJID,MHCAT,MHTERM,MHSTDTC,MHENDTC) duplicates: %d\n",
            sum(duplicated(mh[, c("USUBJID","MHCAT","MHTERM","MHSTDTC","MHENDTC")]))))
