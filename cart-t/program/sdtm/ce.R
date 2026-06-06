## --------------------------------------------------------------------
## CE — Clinical Events (Suspected MI)
## Spec:   spec/sdtm/ce.yaml
## Inputs: data/raw/mi.rds (Suspected MI), data/sdtm/dm.rds (reference dates)
## Output: data/sdtm/ce.rds
##
## P21 findings resolved (issue #15):
##   SD1021 – CETERM canonical mapping (CHEST PAIN / SUSPECTED MYOCARDIAL
##            INFARCTION); junk free-text rows dropped
##   SD1076 – Drop permissible variables that don't belong in CE (VISITNUM /
##            VISIT — Timing-class variables that v3.3 CE table omits)
##   SD1078 – Drop permissible variables that are 100% null (CEDECOD, CESTAT,
##            CESEV)
##   SD1079 – Reorder final select() to match SDTMIG v3.3 CE table
##   SD1077 – Derive EPOCH from DM reference dates (SCREENING / TREATMENT /
##            FOLLOW-UP)
##   SD0022 – CESTDTC null for 1 row remains as a known data limitation
##            (subject CART-T-PILOT-01-DF-035 has no EVENTDATE on the form)
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

raw <- readRDS("data/raw/mi.rds")
dm  <- readRDS("data/sdtm/dm.rds")

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

## SD1021 – canonical CETERM mapping.  CECAT is "SUSPECTED MI" so the only
## protocol-valid event terms are CHEST PAIN (a presenting symptom of MI)
## and SUSPECTED MYOCARDIAL INFARCTION (the protocol event of interest).
## Junk / test-data rows are dropped — they would otherwise mis-represent
## the subject's clinical event log.
map_ceterm <- function(x) {
  u <- toupper(trimws(x))
  dplyr::case_when(
    is.na(u) | !nzchar(u)                       ~ NA_character_,
    ## Chest-pain variants (including the misspelling "cest pain" and the
    ## "Chest pain, with dyspnea, nausea, no diaphoresis." narrative).
    grepl("^C[EH]ST PAIN", u)                   ~ "CHEST PAIN",
    grepl("CHEST PAIN", u)                      ~ "CHEST PAIN",
    ## MI variants
    u == "MI"                                   ~ "SUSPECTED MYOCARDIAL INFARCTION",
    grepl("MYOCARDIAL INFARCTION", u)           ~ "SUSPECTED MYOCARDIAL INFARCTION",
    ## Everything else is junk / test entry — return NA so the row gets dropped.
    TRUE                                        ~ NA_character_
  )
}

ce <- wide |>
  filter(!is.na(DESC) & nzchar(DESC)) |>
  mutate(CETERM = map_ceterm(DESC)) |>
  ## SD1021: drop rows whose DESC doesn't map to a canonical CETERM (junk data)
  filter(!is.na(CETERM)) |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  left_join(dm |> select(USUBJID, RFSTDTC, RFENDTC), by = "USUBJID") |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "CE",
    CECAT    = "SUSPECTED MI",
    CEPRESP  = "Y",
    CEOCCUR  = "Y",
    CESER    = "Y",
    CESTDTC  = normalize_iso_date(EVENTDATE),
    ## SD1088-style derivation: study day of event start relative to RFSTDTC,
    ## skipping day 0.
    CESTDY   = dplyr::if_else(
      !is.na(CESTDTC) & !is.na(RFSTDTC),
      as.integer(as.Date(CESTDTC) - as.Date(RFSTDTC)) +
        ifelse(CESTDTC >= RFSTDTC, 1L, 0L),
      NA_integer_
    ),
    ## SD1077: derive EPOCH from CESTDTC vs DM reference period.
    ##   < RFSTDTC                  -> SCREENING
    ##   RFSTDTC .. RFENDTC         -> TREATMENT
    ##   > RFENDTC                  -> FOLLOW-UP
    ##   anything missing           -> null (no reference period for subject)
    EPOCH    = dplyr::case_when(
      is.na(CESTDTC) | is.na(RFSTDTC)                  ~ NA_character_,
      CESTDTC < RFSTDTC                                ~ "SCREENING",
      !is.na(RFENDTC) & CESTDTC > RFENDTC              ~ "FOLLOW-UP",
      TRUE                                             ~ "TREATMENT"
    )
  ) |>
  arrange(USUBJID, CESTDTC) |>
  mutate(CESEQ = row_number(), .by = USUBJID) |>
  ## SD1076 / SD1078 / SD1079: keep only IG-defined variables that we can
  ## populate, and order per SDTMIG v3.3 CE table.
  ## Dropped (SD1076 — permissible variables not used): VISITNUM, VISIT
  ## Dropped (SD1078 — permissible with 100% null): CEDECOD, CESTAT, CESEV
  select(STUDYID, DOMAIN, USUBJID, CESEQ,
         CETERM, CECAT, CEPRESP, CEOCCUR, CESER,
         EPOCH, CESTDTC, CESTDY)

saveRDS(ce, "data/sdtm/ce.rds")
cat(sprintf("CE written: %d rows x %d cols\n", nrow(ce), ncol(ce)))
cat(sprintf("CETERM non-null: %d / %d\n",
            sum(!is.na(ce$CETERM)), nrow(ce)))
cat(sprintf("CESTDTC non-null: %d / %d\n",
            sum(!is.na(ce$CESTDTC)), nrow(ce)))
cat(sprintf("CESTDY non-null: %d / %d\n",
            sum(!is.na(ce$CESTDY)), nrow(ce)))
cat(sprintf("EPOCH non-null: %d / %d\n",
            sum(!is.na(ce$EPOCH)), nrow(ce)))
cat("CETERM distribution:\n")
print(table(ce$CETERM, useNA = "ifany"))
cat("EPOCH distribution:\n")
print(table(ce$EPOCH, useNA = "ifany"))
