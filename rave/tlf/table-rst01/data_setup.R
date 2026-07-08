# Data setup for RST01 — Birmingham Vasculitis Activity Score (BVAS/WG) by visit
# (RAVE disease-activity efficacy summary). read_adam() provided by ../tlf_data.R.
#
# Note: RS is collected from Month 1 onward with no pre-treatment record, so there
# is no baseline flag for the activity scores — this is a value-only (not
# change-from-baseline) descriptive summary of disease activity over time.

library(tern)
library(dplyr)

adsl <- read_adam("adsl")
adrs <- read_adam("adrs")

adsl <- df_explicit_na(adsl)
adrs <- df_explicit_na(adrs)
adrs_label <- var_labels(adrs)

adsl <- adsl %>%
  filter(ITTFL == "Y") %>%
  mutate(TRT01A = droplevels(factor(TRT01A)))

adrs <- adrs %>%
  filter(ITTFL == "Y", PARAMCD == "BVASWG", !is.na(AVAL)) %>%
  mutate(TRT01A = factor(TRT01A, levels = levels(adsl$TRT01A)),
         PARAM  = droplevels(factor(PARAM)))

visit_levels <- adrs %>% distinct(AVISIT, AVISITN) %>% arrange(AVISITN) %>% pull(AVISIT)
adrs$AVISIT  <- factor(as.character(adrs$AVISIT), levels = as.character(visit_levels))

adrs_f <- adrs
var_labels(adrs_f) <- adrs_label
