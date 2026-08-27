## --------------------------------------------------------------------
## IE — Inclusion/Exclusion Exceptions
## Spec:   spec/sdtm/ie.yaml
## Inputs: data/raw/ie.rds, data/sdtm/dm.rds (for USUBJID + RFSTDTC)
## Output: data/sdtm/ie.rds
##
## P21 findings resolved (issue #18):
##   SD1046 (15) — IESTRESC must be 'N' when IECAT='INCLUSION'. The IE
##                  domain convention is that a row exists *because* the
##                  criterion was failed: for an INCLUSION criterion the
##                  subject did NOT meet it (IEORRES='N'); for an
##                  EXCLUSION criterion the subject DID meet it
##                  (IEORRES='Y'). IESTRESC mirrors IEORRES.
##   SD1077 (1)  — EPOCH not derived. The Eligibility CRF is only
##                  collected at the SE_ENROLLMENT event prior to any
##                  treatment, so EPOCH = "SCREENING" for every row.
##   SD1084 (1)  — IEDY null. Derive from IEDTC and DM.RFSTDTC using the
##                  no-day-0 convention used by CE/DS.
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

raw <- readRDS("data/raw/ie.rds")
dm  <- readRDS("data/sdtm/dm.rds")

key_link <- raw |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

eval_items   <- c("INC1EVAL", "INC2EVAL", "EXCEVAL")
fail_pattern <- "NOT[_ ]?MET|FAIL"

failing <- raw |>
  filter(itemname %in% eval_items) |>
  filter(!is.na(value) & grepl(fail_pattern, toupper(value))) |>
  select(subjectkey, itemgroupname, itemname, value,
         startdate, eventname, studyeventoid)

itemgroup_to_cat <- c(
  INC1 = "INCLUSION", INC2 = "INCLUSION", INCA = "INCLUSION",
  EXCT = "EXCLUSION"
)
itemgroup_to_scat <- c(
  INC1 = "DISEASE HISTORY",
  INC2 = "LABS AND ORGAN FUNCTION",
  INCA = "AGE AND CONSENT",
  EXCT = "SAFETY AND INFECTIONS"
)

testcd_for <- function(itemgroup, itemname) {
  prefix <- substr(itemgroup, 1, 4)
  base   <- substr(itemname, 1, 8)
  cd     <- paste0(prefix, base)
  toupper(substr(cd, 1, 8))
}

ie <- failing |>
  mutate(
    IECAT    = unname(itemgroup_to_cat[itemgroupname]),
    IESCAT   = unname(itemgroup_to_scat[itemgroupname]),
    IETESTCD = mapply(testcd_for, itemgroupname, itemname),
    IETEST   = paste(itemgroupname, itemname, sep = " / "),
    ## SD1046: IEORRES/IESTRESC encode whether the criterion was MET.
    ##   INCLUSION row exists because subject failed the criterion -> 'N'
    ##   EXCLUSION row exists because subject met the criterion     -> 'Y'
    IEORRES  = dplyr::if_else(IECAT == "INCLUSION", "N", "Y"),
    IESTRESC = IEORRES,
    VISITNUM = derive_visitnum(studyeventoid),
    VISIT    = "SCREENING",
    ## SD1077: Eligibility CRF is only collected at screening event.
    EPOCH    = "SCREENING",
    IEDTC    = normalize_iso_date(startdate)
  ) |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  left_join(dm |> select(USUBJID, RFSTDTC), by = "USUBJID") |>
  mutate(
    ## SD1084: derive IEDY as integer days from RFSTDTC to IEDTC, skipping
    ## day 0 (same convention used by CE/DS).
    IEDY = dplyr::if_else(
      !is.na(IEDTC) & !is.na(RFSTDTC),
      as.integer(as.Date(IEDTC) - as.Date(RFSTDTC)) +
        ifelse(IEDTC >= RFSTDTC, 1L, 0L),
      NA_integer_
    )
  ) |>
  arrange(USUBJID, IECAT, IETESTCD) |>
  mutate(
    STUDYID = "CART-T-PILOT",
    DOMAIN  = "IE",
    IESEQ   = row_number(),
    .by = USUBJID
  ) |>
  select(STUDYID, DOMAIN, USUBJID, IESEQ,
         IETESTCD, IETEST, IECAT, IESCAT,
         IEORRES, IESTRESC, VISITNUM, VISIT, EPOCH, IEDTC, IEDY)

saveRDS(ie, "data/sdtm/ie.rds")
cat(sprintf("IE written: %d rows x %d cols\n", nrow(ie), ncol(ie)))
cat(sprintf("IECAT distribution:\n"))
print(table(ie$IECAT))
cat(sprintf("IEORRES by IECAT:\n"))
print(table(ie$IECAT, ie$IEORRES, useNA = "ifany"))
cat(sprintf("EPOCH non-null: %d / %d\n", sum(!is.na(ie$EPOCH)), nrow(ie)))
cat(sprintf("IEDY non-null:  %d / %d\n", sum(!is.na(ie$IEDY)),  nrow(ie)))
cat(sprintf("IETESTCD lengths (must all be <=8):\n"))
print(table(nchar(ie$IETESTCD)))
