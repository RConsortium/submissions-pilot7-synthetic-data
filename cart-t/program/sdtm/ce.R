## --------------------------------------------------------------------
## CE — Clinical Events (Suspected MI)
## Spec:   spec/sdtm/ce.yaml
## Inputs: data/raw/mi.rds (Suspected MI)
## Output: data/sdtm/ce.rds
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

raw <- readRDS("data/raw/mi.rds")

key_link <- raw |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

wide <- raw |>
  filter(itemgroupname == "EVENT", itemname %in% c("DESC", "EVENTDATE")) |>
  select(subjectkey, itemgrouprepeatkey,
         eventname, studyeventoid, startdate,
         itemname, value) |>
  pivot_wider(names_from = itemname, values_from = value,
              values_fn = ~ dplyr::first(.x))

ce <- wide |>
  filter(!is.na(DESC) & nzchar(DESC)) |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "CE",
    CETERM   = DESC,
    CEDECOD  = NA_character_,
    CECAT    = "SUSPECTED MI",
    CEPRESP  = "Y",
    CEOCCUR  = "Y",
    CESTAT   = NA_character_,
    CESEV    = NA_character_,
    CESER    = "Y",
    CESTDTC  = normalize_iso_date(EVENTDATE),
    CESTDY   = NA_integer_,
    VISITNUM = derive_visitnum(studyeventoid),
    VISIT    = eventname
  ) |>
  arrange(USUBJID, CESTDTC) |>
  mutate(CESEQ = row_number(), .by = USUBJID) |>
  select(STUDYID, DOMAIN, USUBJID, CESEQ,
         CETERM, CEDECOD, CECAT, CEPRESP, CEOCCUR, CESTAT, CESEV, CESER,
         CESTDTC, CESTDY, VISITNUM, VISIT)

saveRDS(ce, "data/sdtm/ce.rds")
cat(sprintf("CE written: %d rows x %d cols\n", nrow(ce), ncol(ce)))
