# Data setup for AET02 — Adverse Events by System Organ Class and Preferred Term.
# read_adam() is provided globally by ../tlf_data.R.

library(tern)
library(dplyr)

adsl <- read_adam("adsl")
adae <- read_adam("adae")

adsl <- df_explicit_na(adsl)
adae <- df_explicit_na(adae)

# Safety population; treatment-emergent AEs only.
adsl <- adsl %>%
  filter(SAFFL == "Y") %>%
  mutate(TRT01A = droplevels(factor(TRT01A)))

adae <- adae %>%
  filter(SAFFL == "Y", TRTEMFL == "Y") %>%
  mutate(
    TRT01A   = factor(TRT01A, levels = levels(adsl$TRT01A)),
    AEBODSYS = droplevels(factor(AEBODSYS)),
    AEDECOD  = droplevels(factor(AEDECOD))
  )
