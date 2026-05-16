## --------------------------------------------------------------------
## IE — Inclusion/Exclusion Exceptions
## Spec:   spec/sdtm/ie.yaml
## Inputs: data/raw/ie.rds, data/sdtm/dm.rds (for USUBJID)
## Output: data/sdtm/ie.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

raw <- readRDS("data/raw/ie.rds")

key_link <- raw |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

eval_items <- c("INC1EVAL", "INC2EVAL", "EXCEVAL")
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
    IEORRES  = "Y",
    IESTRESC = "Y",
    VISITNUM = derive_visitnum(studyeventoid),
    VISIT    = "SCREENING",
    IEDTC    = normalize_iso_date(startdate)
  ) |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  arrange(USUBJID, IECAT, IETESTCD) |>
  mutate(
    STUDYID = "CART-T-PILOT",
    DOMAIN  = "IE",
    IESEQ   = row_number(),
    IEDY    = NA_integer_,
    .by = USUBJID
  ) |>
  select(STUDYID, DOMAIN, USUBJID, IESEQ,
         IETESTCD, IETEST, IECAT, IESCAT,
         IEORRES, IESTRESC, VISITNUM, VISIT, IEDTC, IEDY)

saveRDS(ie, "data/sdtm/ie.rds")
cat(sprintf("IE written: %d rows x %d cols\n", nrow(ie), ncol(ie)))
