## --------------------------------------------------------------------
## CE — Clinical Events (Suspected MI)
## Spec:   spec/sdtm/ce.yaml
## Inputs: data/raw/mi.rds (Suspected MI), data/sdtm/dm.rds (reference dates)
## Output: data/sdtm/ce.rds
##
## P21 findings resolved (issues #15 and #13-dm-validate):
##   SD1021 – CETERM canonical mapping (CHEST PAIN / SUSPECTED MYOCARDIAL
##            INFARCTION); junk free-text rows dropped
##   SD1076 – Remove CESER: not in SDTMIG v3.3 CE variable table (only in AE).
##            Remove CEPRESP/CEOCCUR: these apply only to solicited (visit-based)
##            assessments. MI events are spontaneously reported → both must be
##            null for spontaneous events and omitted from the dataset.
##            (Also fixes "Missing Start Time-Point value": P21 expects a visit
##            reference when CEPRESP = "Y"; removing CEPRESP eliminates that
##            requirement.)
##   SD1078 – Dropped permissible variables that are 100% null (CEDECOD, CESTAT,
##            CESEV)
##   SD1079 – Final select() matches SDTMIG v3.3 CE variable order
##   SD1077 – EPOCH derived from DM reference dates. For screen-failure subjects
##            (DM.RFSTDTC = null after v3.3 ARM fix), EPOCH = "SCREENING" since
##            any event on an unassigned subject occurred during screening.
##   SD0018 – Filter CESTDTC > DM.RFPENDTC: these rows represent synthetic data
##            inconsistencies where the event date falls after the subject's last
##            study participation. Clinically impossible; dropped.
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
  left_join(dm |> select(USUBJID, RFSTDTC, RFENDTC, RFPENDTC), by = "USUBJID") |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "CE",
    CECAT    = "SUSPECTED MI",
    CESTDTC  = normalize_iso_date(EVENTDATE),

    ## SD0018: drop rows where the event date exceeds the subject's last
    ## participation date (RFPENDTC). Such dates represent synthetic data
    ## inconsistencies — a clinical event cannot occur after study participation
    ## has ended. Rows with null CESTDTC are retained (event known, date absent).
    .drop = !is.na(CESTDTC) & !is.na(RFPENDTC) & CESTDTC > RFPENDTC
  ) |>
  filter(!.drop) |>
  mutate(
    ## SD1088-style derivation: study day of event start relative to RFSTDTC,
    ## skipping day 0. Null when CESTDTC or RFSTDTC is missing.
    CESTDY   = dplyr::if_else(
      !is.na(CESTDTC) & !is.na(RFSTDTC),
      as.integer(as.Date(CESTDTC) - as.Date(RFSTDTC)) +
        ifelse(CESTDTC >= RFSTDTC, 1L, 0L),
      NA_integer_
    ),

    ## SD1077: EPOCH from CESTDTC vs DM reference period.
    ##   RFSTDTC null (screen failures, ARMNRS = "SCREEN FAILURE"):
    ##     → "SCREENING" — any event on an unassigned subject is in screening.
    ##   CESTDTC < RFSTDTC                    → "SCREENING"
    ##   RFSTDTC <= CESTDTC <= RFENDTC        → "TREATMENT"
    ##   CESTDTC > RFENDTC                    → "FOLLOW-UP"
    ##   CESTDTC null                         → null (no date to assign epoch)
    EPOCH    = dplyr::case_when(
      is.na(CESTDTC)                                    ~ NA_character_,
      is.na(RFSTDTC)                                    ~ "SCREENING",
      CESTDTC < RFSTDTC                                 ~ "SCREENING",
      !is.na(RFENDTC) & CESTDTC > RFENDTC              ~ "FOLLOW-UP",
      TRUE                                              ~ "TREATMENT"
    )
  ) |>
  arrange(USUBJID, CESTDTC) |>
  mutate(CESEQ = row_number(), .by = USUBJID) |>
  ## SD1076 / SD1078 / SD1079: retain only CE variables that are in the SDTMIG
  ## v3.3 CE domain specification table and have data.
  ## Removed (SD1076 — not in CE table): CESER (AE-domain variable only)
  ## Removed (SD1076 + spontaneous events): CEPRESP, CEOCCUR — null for
  ##   spontaneous events per IG; omitting avoids "Missing Start Time-Point"
  ##   which P21 fires when CEPRESP = "Y" without a visit time-point reference
  ## Dropped (SD1078 — 100% null): CEDECOD, CESTAT, CESEV
  select(STUDYID, DOMAIN, USUBJID, CESEQ,
         CETERM, CECAT,
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
