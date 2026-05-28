# =============================================================================
# Program   : adsl.R
# Study     : CART2020 — CAR-T for ALL (Phase IIb)
# Dataset   : ADSL — Subject-Level Analysis Dataset
# Standard  : ADaMIG v1.3
# Purpose   : Derive ADSL from SDTM domains per the ADaM ADSL specification
#
# Inputs    : data/sdtm/dm.rds, data/sdtm/ex.rds, data/sdtm/ds.rds
# Output    : data/adam/adsl.rds
#
# REVIEW: MH (data/sdtm/mh.rds) is available in this study but ADSL-level
#   history flags are not yet in scope. Uncomment the load and Step 10
#   extension block if the SAP requires baseline medical history flags.
#
# REVIEW: VS is not present as a standalone SDTM domain in this project
#   (baseline labs/imaging are in LB/CE). HEIGHTBL, WEIGHTBL, BMIBL are
#   therefore not derived here. Add if VS is introduced in a later data cut.
#
# Notes     : CAR-T therapy context
#   - EX records represent CAR-T cell infusion(s), not daily dosing. Subjects
#     may have one or a small number of infusion records. Treatment dates
#     therefore reflect actual infusion dates, not a dosing window.
#   - REVIEW: Confirm with the statistician whether SAFFL = "Y" requires
#     EXDOSE > 0 or simply a non-missing EXSTDTC (infusion date recorded).
#     For cell therapy, EXDOSE units (e.g. cells/kg) may not follow the
#     conventional > 0 numeric check. Adjust the EX filter accordingly.
# =============================================================================

library(admiral)
library(dplyr)
library(lubridate)

# -----------------------------------------------------------------------------
# Step 1 — Load SDTM domains
# -----------------------------------------------------------------------------

dm <- readRDS("data/sdtm/dm.rds")
ex <- readRDS("data/sdtm/ex.rds")
ds <- readRDS("data/sdtm/ds.rds")
# mh <- readRDS("data/sdtm/mh.rds")  # uncomment if MH flags in scope

# One record per USUBJID in DM is a hard requirement — fail fast if violated
stopifnot(nrow(dm) == n_distinct(dm$USUBJID))

# -----------------------------------------------------------------------------
# Step 2 — Subject spine from DM
# -----------------------------------------------------------------------------

adsl <- dm |>
  select(
    STUDYID, USUBJID, SUBJID, SITEID,
    AGE, AGEU, SEX, RACE, ETHNIC, COUNTRY,
    ARM, ARMCD, ACTARM, ACTARMCD,
    DMDTC, RFSTDTC, RFENDTC,
    DTHFL, DTHDTC
  )

# -----------------------------------------------------------------------------
# Step 3 — Treatment dates (TRTSDTM, TRTSTMF, TRTEDTM, TRTETMF, TRTSDT, TRTEDT)
#
# CAR-T infusion datetimes from EX.EXSTDTC / EX.EXENDTC.
# TRTSDTM = first infusion datetime; TRTEDTM = last infusion datetime.
# For subjects with a single infusion these will be the same record.
# -----------------------------------------------------------------------------

ex_dtm <- ex |>
  select(-DOMAIN) |>
  derive_vars_dtm(
    dtc             = EXSTDTC,
    new_vars_prefix = "EXST",
    date_imputation = "first",
    time_imputation = "first",
    flag_imputation = "auto"
  ) |>
  derive_vars_dtm(
    dtc             = EXENDTC,
    new_vars_prefix = "EXEN",
    date_imputation = "last",
    time_imputation = "last",
    flag_imputation = "auto"
  )

# TRTSDTM / TRTSTMF: first infusion datetime and imputation flag
# REVIEW: The filter condition below uses !is.na(EXSTDTC) only, consistent
#   with CAR-T infusion context where EXDOSE may be expressed as cells/kg
#   rather than a conventional numeric dose. Confirm with the statistician
#   whether EXDOSE > 0 is a reliable inclusion criterion for this study.
adsl <- adsl |>
  derive_vars_merged(
    dataset_add = ex_dtm,
    by_vars     = exprs(STUDYID, USUBJID),
    new_vars    = exprs(TRTSDTM = EXSTDTM, TRTSTMF = EXSTTMF),
    order       = exprs(EXSTDTM),
    mode        = "first",
    filter_add  = !is.na(EXSTDTC)
  ) |>
  # TRTEDTM / TRTETMF: last infusion datetime and imputation flag
  derive_vars_merged(
    dataset_add = ex_dtm,
    by_vars     = exprs(STUDYID, USUBJID),
    new_vars    = exprs(TRTEDTM = EXENDTM, TRTETMF = EXENTMF),
    order       = exprs(EXENDTM),
    mode        = "last",
    filter_add  = !is.na(EXENDTC)
  ) |>
  mutate(
    # TRTSDT / TRTEDT: date-only versions for study day derivations
    TRTSDT = as.Date(TRTSDTM),
    TRTEDT = as.Date(TRTEDTM)
  )

# -----------------------------------------------------------------------------
# Step 4 — Planned and actual treatment (TRT01P, TRT01PN, TRT01A, TRT01AN)
#
# REVIEW: ARMCD values below are placeholders. Replace with the actual
#   randomisation arm codes from DM before use. Confirm arm labels and
#   numeric codes against the CART2020 randomisation schedule and ADaM spec.
#   Screen failure subjects (if any) should be excluded from the lookup so
#   they receive NA for TRT01P/TRT01A rather than a spurious label.
# -----------------------------------------------------------------------------

arm_lookup <- tibble::tribble(
  ~ARMCD,    ~TRT01P,                              ~TRT01PN,
  # PLACEHOLDER — replace with actual CART2020 ARMCD values from DM
  "CART",    "CAR-T Cell Therapy",                 1L,
  "CTRL",    "Standard of Care",                   2L
)

adsl <- adsl |>
  derive_vars_merged_lookup(
    dataset_add = arm_lookup,
    by_vars     = exprs(ARMCD),
    new_vars    = exprs(TRT01P, TRT01PN)
  ) |>
  derive_vars_merged_lookup(
    dataset_add = arm_lookup |>
      rename(ACTARMCD = ARMCD, TRT01A = TRT01P, TRT01AN = TRT01PN),
    by_vars     = exprs(ACTARMCD),
    new_vars    = exprs(TRT01A, TRT01AN)
  )

# -----------------------------------------------------------------------------
# Step 5 — Randomisation and reference dates
#
# RANDDT : randomisation date from DM.DMDTC
# RFSTDT : study reference start date from DM.RFSTDTC
# RFENDT : study reference end date from DM.RFENDTC
# -----------------------------------------------------------------------------

adsl <- adsl |>
  # RANDDT: date of randomisation
  # REVIEW: Confirm DM.DMDTC is the randomisation date for CART2020. If
  #   randomisation date is captured separately (e.g. on the Randomize CRF),
  #   it may need to be sourced from a dedicated SDTM variable or domain.
  derive_vars_dt(
    dtc             = DMDTC,
    new_vars_prefix = "RAND",
    date_imputation = "first",
    flag_imputation = "auto"
  ) |>
  derive_vars_dt(
    dtc             = RFSTDTC,
    new_vars_prefix = "RFST",
    date_imputation = "first",
    flag_imputation = "auto"
  ) |>
  derive_vars_dt(
    dtc             = RFENDTC,
    new_vars_prefix = "RFEND",
    date_imputation = "last",
    flag_imputation = "auto"
  )

# -----------------------------------------------------------------------------
# Step 6 — Death variables
# -----------------------------------------------------------------------------

adsl <- adsl |>
  derive_vars_dt(
    dtc             = DTHDTC,
    new_vars_prefix = "DTH",
    date_imputation = "first",
    flag_imputation = "auto"
  ) |>
  mutate(
    # CDISC flag convention: "Y" or NA — never "N"
    DTHFL = if_else(DTHFL == "Y", "Y", NA_character_)
  )

# -----------------------------------------------------------------------------
# Step 7 — Study day variables
#
# RANDDY: study day of randomisation relative to first infusion (TRTSDT)
# Use derive_vars_dy() — never manual date subtraction
# -----------------------------------------------------------------------------

adsl <- adsl |>
  derive_vars_dy(
    reference_date = TRTSDT,
    source_vars    = exprs(RANDDT)
  )

# -----------------------------------------------------------------------------
# Step 8 — Treatment duration (TRTDURD)
#
# Requires TRTSDT and TRTEDT. NA for subjects with no recorded infusion.
# For CAR-T with a single infusion, TRTDURD will be 1 for most subjects.
# -----------------------------------------------------------------------------

adsl <- adsl |>
  derive_var_trtdurd()

# -----------------------------------------------------------------------------
# Step 9 — Disposition (EOSSTT, DCSREAS, DCSREASP, EOSDT)
# -----------------------------------------------------------------------------

ds_eos <- ds |>
  select(-DOMAIN) |>
  filter(DSCAT == "DISPOSITION EVENT") |>
  derive_vars_dt(
    dtc             = DSDTC,
    new_vars_prefix = "DS",
    date_imputation = "last",
    flag_imputation = "auto"
  )

# One DISPOSITION EVENT record per subject is required before the merge
stopifnot(n_distinct(ds_eos$USUBJID) == nrow(ds_eos))

# EOSSTT: end of study status — "COMPLETED" or "DISCONTINUED" only
# REVIEW: Verify the mapping below covers all DSDECOD values in this study's
#   DS domain. Confirm with the statistician whether any subjects have a
#   "STUDY TERMINATED BY SPONSOR" or equivalent status requiring a third category.
adsl <- adsl |>
  derive_vars_merged(
    dataset_add = ds_eos |>
      mutate(
        EOSSTT = if_else(DSDECOD == "COMPLETED", "COMPLETED", "DISCONTINUED")
      ),
    by_vars  = exprs(STUDYID, USUBJID),
    new_vars = exprs(EOSSTT, EOSDT = DSDT)
  ) |>
  # DCSREAS / DCSREASP: decoded and verbatim discontinuation reason
  # NA for completers per CDISC convention
  # REVIEW: DCSREAS = decoded value (DSDECOD); DCSREASP = verbatim text (DSTERM)
  derive_vars_merged(
    dataset_add = ds_eos |>
      filter(DSDECOD != "COMPLETED"),
    by_vars  = exprs(STUDYID, USUBJID),
    new_vars = exprs(DCSREAS = DSDECOD, DCSREASP = DSTERM)
  )

# -----------------------------------------------------------------------------
# Step 10 — Baseline demographics
#
# AGEGR1 / AGEGR1N: age group per ADaM spec
# REVIEW: Age cut-points below are PLACEHOLDERS for a CAR-T ALL adult study
#   (protocol specifies adults; confirm the actual grouping in the ADaM spec).
#   Replace before use. ALL studies often use <40 / 40–59 / >=60 or similar
#   oncology-specific groupings — do not assume the defaults below are correct.
# -----------------------------------------------------------------------------

adsl <- adsl |>
  mutate(
    AGEGR1 = case_when(
      AGE < 40              ~ "<40",    # PLACEHOLDER — confirm from ADaM spec
      AGE >= 40 & AGE < 60  ~ "40-59",  # PLACEHOLDER — confirm from ADaM spec
      AGE >= 60             ~ ">=60"    # PLACEHOLDER — confirm from ADaM spec
    ),
    AGEGR1N = case_when(
      AGEGR1 == "<40"   ~ 1L,
      AGEGR1 == "40-59" ~ 2L,
      AGEGR1 == ">=60"  ~ 3L
    )
  )

# -----------------------------------------------------------------------------
# Step 11 — Population flags (SAFFL, ITTFL)
#
# REVIEW: Population flag definitions are protocol-specific. Review and confirm
#   each flag definition against the CART2020 protocol and SAP before use.
#   Flags are "Y" or NA only — never "N" per CDISC ADaM convention.
# -----------------------------------------------------------------------------

# SAFFL: received at least one CAR-T infusion (exposure recorded)
# REVIEW: For CAR-T, "received treatment" = infusion date recorded in EX.
#   EXDOSE > 0 may not be the right condition if dose is expressed as cells/kg
#   or as a categorical variable. Confirm the exact SAFFL definition with the
#   statistician. Using !is.na(EXSTDTC) as the trigger here — adjust if needed.
adsl <- adsl |>
  derive_var_merged_exist_flag(
    dataset_add   = ex |> select(-DOMAIN),
    by_vars       = exprs(STUDYID, USUBJID),
    new_var       = SAFFL,
    condition     = !is.na(EXSTDTC),
    true_value    = "Y",
    false_value   = NA_character_,
    missing_value = NA_character_
  ) |>
  # ITTFL: randomised subjects (ARMCD is not a screen failure value)
  # REVIEW: Confirm ITTFL exclusion criteria with the statistician.
  #   Adjust the ARMCD exclusion values if the study uses different codes for
  #   screen failures or pre-randomisation withdrawals.
  mutate(
    ITTFL = if_else(
      !ARMCD %in% c("Scrnfail", "NOTASSGN") & !is.na(ARMCD),
      "Y",
      NA_character_
    )
  )
  # PPROTFL: per protocol — derive per SAP with protocol deviation exclusions
  # REVIEW: Highly protocol-specific; uncomment and complete per SAP definition.
  # |> mutate(
  #   PPROTFL = if_else(ITTFL == "Y" & <no_major_deviations_condition>, "Y", NA_character_)
  # )

# -----------------------------------------------------------------------------
# Step 12 — Dataset attributes and final checks
# -----------------------------------------------------------------------------

# Non-negotiable per ADaMIG — one record per USUBJID
stopifnot(nrow(adsl) == n_distinct(adsl$USUBJID))

# Confirm all required variables are present
required_vars <- c(
  "STUDYID", "USUBJID",
  "TRTSDT", "TRTEDT",
  "TRT01P", "TRT01PN", "TRT01A", "TRT01AN",
  "TRTSDTM", "TRTSTMF", "TRTEDTM", "TRTETMF",
  "EOSSTT", "SAFFL", "ITTFL"
)
missing_vars <- setdiff(required_vars, names(adsl))
if (length(missing_vars) > 0) {
  stop("Missing required ADSL variables: ", paste(missing_vars, collapse = ", "))
}

# Save to ADaM output location
saveRDS(adsl, "data/adam/adsl.rds")
message("adsl.rds written: ", nrow(adsl), " subjects")

# -----------------------------------------------------------------------------
# Submission output (xportr) — uncomment for XPT generation
# -----------------------------------------------------------------------------
# library(xportr)
# library(metacore)
# metacore_obj <- spec_to_metacore("spec/adam/adsl.yaml", where_sep_sheet = FALSE)
# adsl <- adsl |>
#   xportr_label(metacore_obj,  domain = "ADSL") |>
#   xportr_type(metacore_obj,   domain = "ADSL") |>
#   xportr_length(metacore_obj, domain = "ADSL") |>
#   xportr_order(metacore_obj,  domain = "ADSL")
# xportr_write(adsl, "adsl.xpt", label = "Subject-Level Analysis Dataset")
