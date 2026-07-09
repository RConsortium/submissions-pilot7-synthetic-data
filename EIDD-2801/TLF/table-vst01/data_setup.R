# Data setup for VST01 — Vital Sign Results and Change from Baseline by Visit.
# Run with the working directory set to this task's output folder (run_all.R does
# this); read_adam() is provided globally by ../tlf_data.R.

library(tern)
library(dplyr)

adsl <- read_adam("adsl")
advs <- read_adam("advs")

# Convert character variables to factors; make empty strings / NAs explicit.
adsl <- df_explicit_na(adsl)
advs <- df_explicit_na(advs)
advs_label <- var_labels(advs)

# Safety population (drop treatment levels with no safety-population subjects,
# e.g. Screen Failure, so they don't surface as empty N=0 columns).
adsl <- adsl %>%
  filter(SAFFL == "Y") %>%
  mutate(TRT01A = droplevels(factor(TRT01A)))

advs <- advs %>%
  filter(SAFFL == "Y", !is.na(AVAL)) %>%
  mutate(TRT01A = droplevels(factor(TRT01A)),
         PARAM  = droplevels(factor(PARAM)))

# Order AVISIT by its numeric companion; baseline = earliest visit.
visit_levels <- advs %>% distinct(AVISIT, AVISITN) %>% arrange(AVISITN) %>% pull(AVISIT)
advs$AVISIT  <- factor(as.character(advs$AVISIT), levels = as.character(visit_levels))
BL_VISIT     <- as.character(visit_levels[1])

advs_f <- advs
var_labels(advs_f) <- advs_label
