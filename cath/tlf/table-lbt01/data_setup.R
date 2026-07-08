# Data setup for LBT01 — Antimicrobial Peptide (Cathelicidin) expression and
# change from baseline by visit (CATH primary efficacy endpoint).
# read_adam() is provided globally by ../tlf_data.R.

library(tern)
library(dplyr)

adsl <- read_adam("adsl")
adlb <- read_adam("adlb")

adsl <- df_explicit_na(adsl)
adlb <- df_explicit_na(adlb)
adlb_label <- var_labels(adlb)

# ITT population; primary biomarker only (antimicrobial peptide).
adsl <- adsl %>%
  filter(ITTFL == "Y") %>%
  mutate(TRT01A = droplevels(factor(TRT01A)))

adlb <- adlb %>%
  filter(ITTFL == "Y", PARCAT1 == "ANTIMICROBIAL PEPTIDE", !is.na(AVAL)) %>%
  mutate(TRT01A = factor(TRT01A, levels = levels(adsl$TRT01A)),
         PARAM  = droplevels(factor(PARAM)))

# order AVISIT by its numeric companion; baseline = earliest visit.
visit_levels <- adlb %>% distinct(AVISIT, AVISITN) %>% arrange(AVISITN) %>% pull(AVISIT)
adlb$AVISIT  <- factor(as.character(adlb$AVISIT), levels = as.character(visit_levels))
BL_VISIT     <- as.character(visit_levels[1])

adlb_f <- adlb
var_labels(adlb_f) <- adlb_label
