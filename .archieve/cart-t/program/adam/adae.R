## --------------------------------------------------------------------
## ADAE — Adverse Events Analysis Dataset (OCCDS)
## Spec:   spec/adam/adae.yaml
## Inputs: data/sdtm/ae.rds, data/adam/adsl.rds
## Output: data/adam/adae.rds, data/adam/adae.xpt
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)
library(admiral)

ae   <- readRDS("data/sdtm/ae.rds")   |> admiral::convert_blanks_to_na()
adsl <- readRDS("data/adam/adsl.rds") |> admiral::convert_blanks_to_na()

## ADSL columns to merge onto every AE record. These cover the OCCDS
## required-variable set (TRTA/TRTAN/TRTP/TRTPN, TRTSDT/TRTEDT, pop
## flags, demographics, and the CART-T phenotype stratum STRAT1/STRAT1L
## per CLAUDE.md).
adsl_vars <- adsl |>
  select(USUBJID, SUBJID, SITEID,
         AGE, AGEGR1, SEX, RACE,
         TRT01P, TRT01PN, TRT01A, TRT01AN,
         TRTSDT, TRTEDT,
         STRAT1, STRAT1L,
         RANDFL, ITTFL, SAFFL)

adae <- ae |>
  admiral::derive_vars_dt(new_vars_prefix = "AST", dtc = AESTDTC) |>
  admiral::derive_vars_dt(new_vars_prefix = "AEN", dtc = AEENDTC) |>
  left_join(adsl_vars, by = "USUBJID") |>
  admiral::derive_vars_dy(reference_date = TRTSDT,
                          source_vars    = exprs(ASTDT, AENDT)) |>
  mutate(
    ## OCCDS Required: per-record planned / actual treatment mirror
    ## ADSL TRT01x for the single-period design.
    TRTP    = TRT01P,
    TRTPN   = TRT01PN,
    TRTA    = TRT01A,
    TRTAN   = TRT01AN,

    ## Analysis-side severity / causality (per OCCDS IG and admiral
    ## ad_adae template). ASEV/AREL are analysis copies of the SDTM
    ## qualifiers; AESEVN is the conventional numeric companion to ASEV.
    ASEV    = AESEV,
    AREL    = AEREL,
    AESEVN  = dplyr::recode(AESEV,
                            MILD = 1L, MODERATE = 2L, SEVERE = 3L,
                            .default = NA_integer_),

    ## Treatment-emergent flag: "Y" / null (ADaMIG cardinal rule for
    ## flags). TRTEMFL is null for non-randomized subjects (no TRTSDT)
    ## — those rows are excluded from safety analyses via SAFFL.
    TRTEMFL = dplyr::case_when(
      is.na(ASTDT) | is.na(TRTSDT)              ~ NA_character_,
      ASTDT >= TRTSDT &
        (is.na(TRTEDT) | ASTDT <= TRTEDT + 30L) ~ "Y",
      TRUE                                      ~ NA_character_
    ),

    ## AE duration in days (inclusive of start day).
    ADURN   = dplyr::if_else(!is.na(ASTDT) & !is.na(AENDT),
                             as.integer(AENDT - ASTDT) + 1L,
                             NA_integer_),
    ADURU   = dplyr::if_else(!is.na(ADURN), "DAYS", NA_character_),

    ## Analysis-record flag 01: safety subjects with TRTEMFL = Y.
    ANL01FL = dplyr::if_else(!is.na(SAFFL) & SAFFL == "Y" &
                             !is.na(TRTEMFL) & TRTEMFL == "Y",
                             "Y", NA_character_)
  )

## First-occurrence flags (admiral helper handles ties via the ordering vars).
adae <- adae |>
  admiral::derive_var_extreme_flag(
    by_vars  = exprs(USUBJID),
    order    = exprs(ASTDT, AESEQ),
    new_var  = AOCCFL,
    mode     = "first"
  ) |>
  admiral::derive_var_extreme_flag(
    by_vars  = exprs(USUBJID, AEDECOD),
    order    = exprs(ASTDT, AESEQ),
    new_var  = AOCCPFL,
    mode     = "first"
  ) |>
  admiral::derive_var_extreme_flag(
    by_vars  = exprs(USUBJID, AEBODSYS),
    order    = exprs(ASTDT, AESEQ),
    new_var  = AOCCSFL,
    mode     = "first"
  ) |>
  arrange(USUBJID, AESEQ) |>
  select(STUDYID, USUBJID, SUBJID, SITEID,
         AGE, AGEGR1, SEX, RACE,
         STRAT1, STRAT1L,
         TRT01P, TRT01PN, TRT01A, TRT01AN,
         TRTP, TRTPN, TRTA, TRTAN,
         TRTSDT, TRTEDT,
         TRTEMFL,
         AESEQ, AESPID,
         AETERM, AEDECOD, AEBODSYS,
         AESEV, AESEVN, ASEV,
         AESER, AEREL, AREL, AEOUT,
         AESTDTC, AEENDTC,
         ASTDT, AENDT, ASTDY, AENDY,
         ADURN, ADURU,
         AOCCFL, AOCCPFL, AOCCSFL,
         RANDFL, ITTFL, SAFFL, ANL01FL)

## --------------------------------------------------------------------
## Attach labels and dataset-level label from spec
## (Family A — resolves AD0018, AD0320, AD0503)
##
## metacore/xportr/labelled are not installed in this renv; fall back to
## yaml + base attr(). Labels carry through to XPT via haven::write_xpt
## using the label attribute on each column. See CLAUDE.md for the spec
## YAML contract.
## --------------------------------------------------------------------
spec_yaml <- yaml::read_yaml("spec/adam/adae.yaml")

# Per-variable label
for (v in names(adae)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(adae[[v]], "label") <- lab
}

# Dataset-level label
attr(adae, "label") <- spec_yaml$label

saveRDS(adae, "data/adam/adae.rds")
cat(sprintf("ADAE written: %d rows x %d cols\n", nrow(adae), ncol(adae)))

## --------------------------------------------------------------------
## Export XPT v5 for P21 validation
## --------------------------------------------------------------------
adae_xpt <- adae
# haven::write_xpt does not support integer XPT columns; coerce to double.
int_cols <- names(adae_xpt)[vapply(adae_xpt, is.integer, logical(1))]
if (length(int_cols) > 0) {
  for (c in int_cols) {
    lab <- attr(adae_xpt[[c]], "label")
    adae_xpt[[c]] <- as.double(adae_xpt[[c]])
    if (!is.null(lab)) attr(adae_xpt[[c]], "label") <- lab
  }
}
haven::write_xpt(adae_xpt, path = "data/adam/adae.xpt", version = 5, name = "ADAE")
cat("ADAE XPT exported to data/adam/adae.xpt\n")
