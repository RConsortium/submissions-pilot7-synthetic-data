# adam_adae.R — Derive ADAE (Adverse Events Analysis Dataset)
# Following admiral/CDISC ADaM conventions
# ===========================================================================

library(dplyr)

# --- Step 1: Load source data ---
ae <- read.csv("output/source/ae.csv", stringsAsFactors = FALSE)
adsl <- read.csv("output/adam/adsl.csv", stringsAsFactors = FALSE)

stopifnot(nrow(ae) > 0)

# --- Step 2: Start from AE as subject spine ---
adae <- ae |>
  rename(SUBJID = SUBJID)

# --- Step 3: Merge ADSL variables ---
# REVIEW: Only merge required ADSL variables — not all of ADSL
adsl_vars <- adsl |>
  select(STUDYID, USUBJID, SUBJID, SITEID,
         TRT01P, TRT01PN, TRT01A, TRT01AN,
         TRTSDT, TRTEDT, SAFFL, ITTFL, AGE, SEX, RACE)

adae <- adae |>
  left_join(adsl_vars, by = "SUBJID")

# --- Step 4: AE date variables (ASTDT, AENDT, ADY) ---
# Using AESTDTC_WEEK and AEENDTC_WEEK to derive dates
adae <- adae |>
  mutate(
    TRTSDT = as.Date(TRTSDT),
    TRTEDT = as.Date(TRTEDT),
    ASTDT = TRTSDT + as.integer(AESTDTC_WEEK) * 7L,
    AENDT = TRTSDT + as.integer(AEENDTC_WEEK) * 7L,
    # ADY: Study day (Day 1 = TRTSDT, no Day 0)
    ASTDY = as.integer(ASTDT - TRTSDT) + 1L,
    AENDY = as.integer(AENDT - TRTSDT) + 1L
  )

# --- Step 5: Treatment-emergent flag (TRTEMFL) ---
# REVIEW: TEAE defined as onset on or after first dose, up to 30 days post last dose
adae <- adae |>
  mutate(
    TRTEMFL = if_else(
      ASTDT >= TRTSDT & ASTDT <= (TRTEDT + 30L),
      "Y", NA_character_
    )
  )

# --- Step 6: Severity variables ---
adae <- adae |>
  mutate(
    AESEV = AESEV,
    AESEVN = case_when(
      AESEV == "Mild" ~ 1L,
      AESEV == "Moderate" ~ 2L,
      AESEV == "Severe" ~ 3L
    )
  )

# --- Step 7: Seriousness and outcome ---
adae <- adae |>
  mutate(
    # Flag convention: "Y" or NA, never "N"
    AESER = if_else(AESER == "Yes", "Y", NA_character_),
    AEOUT = AEOUT,
    AESDTH = NA_character_  # No deaths in this trial
  )

# --- Step 8: Causality ---
adae <- adae |>
  mutate(
    AEREL = AEREL,
    AERELN = case_when(
      AEREL == "Not Related" ~ 1L,
      AEREL == "Related" ~ 2L
    )
  )

# --- Step 9: Body system and preferred term (MedDRA) ---
adae <- adae |>
  mutate(
    AEBODSYS = AEBODSYS,
    AEDECOD = AEDECOD,
    AEHLT = NA_character_,  # Higher-level term not available in simulated data
    AEHLGT = NA_character_  # Higher-level group term
  )

# --- Step 10: Worst severity flag per subject ---
adae <- adae |>
  group_by(STUDYID, USUBJID) |>
  mutate(
    AMAXSEVFL = if_else(
      TRTEMFL == "Y" & AESEVN == max(AESEVN[TRTEMFL == "Y"], na.rm = TRUE),
      "Y", NA_character_
    )
  ) |>
  ungroup()

# Only keep first occurrence of max severity per subject
adae <- adae |>
  group_by(STUDYID, USUBJID) |>
  mutate(
    AMAXSEVFL = if_else(
      AMAXSEVFL == "Y" & row_number() == which(AMAXSEVFL == "Y")[1],
      "Y", NA_character_
    )
  ) |>
  ungroup()

# --- Step 11: Sequence number ---
adae <- adae |>
  group_by(STUDYID, USUBJID) |>
  mutate(AESEQ = row_number()) |>
  ungroup()

# --- Step 12: Select final variables ---
adae <- adae |>
  select(
    STUDYID, USUBJID, SUBJID, SITEID,
    TRT01P, TRT01PN, TRT01A, TRT01AN, ARM,
    TRTSDT, TRTEDT, SAFFL, ITTFL, AGE, SEX, RACE,
    AESEQ, AETERM = AETERM, AEDECOD, AEBODSYS,
    ASTDT, AENDT, ASTDY, AENDY,
    AESEV, AESEVN, AESER, AEREL, AERELN,
    AEOUT, AESDTH,
    TRTEMFL, AMAXSEVFL
  )

# --- Write output ---
write.csv(adae, "output/adam/adae.csv", row.names = FALSE)
cat("ADAE written:", nrow(adae), "records,", n_distinct(adae$USUBJID), "subjects\n")
