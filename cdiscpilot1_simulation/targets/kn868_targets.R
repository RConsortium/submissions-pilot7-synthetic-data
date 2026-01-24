#' =============================================================================
#' KEYNOTE-868 Target Values
#' =============================================================================
#' Published data from KEYNOTE-868 (NRG-GY018) trial
#' Source: FDA approval, NEJM, ASCO presentations
#'
#' Trial: Pembrolizumab + carboplatin/paclitaxel vs placebo + carboplatin/paclitaxel
#' Indication: Advanced or recurrent endometrial carcinoma
#' N = 810 (dMMR: 222, pMMR: 588)
#' =============================================================================

KN868_TARGETS <- list(

  # ===========================================================================
  # TRIAL DESIGN
  # ===========================================================================
  trial = list(
    name = "KEYNOTE-868",
    alias = "NRG-GY018",
    indication = "Advanced or Recurrent Endometrial Carcinoma",
    phase = "Phase 3",
    design = "Randomized, Double-blind, Placebo-controlled",
    n_total = 810,
    n_pembro = 405,
    n_placebo = 405,
    n_dmmr = 222,
    n_pmmr = 588,
    randomization_ratio = "1:1",
    stratification = c("MMR status (dMMR vs pMMR)")
  ),

  # ===========================================================================
  # DEMOGRAPHICS (from Table 1)
  # ===========================================================================
  demographics = list(
    # Age
    age_median = 65,
    age_range = c(30, 87),
    age_lt65_pct = 0.48,
    age_gte65_pct = 0.52,

    # ECOG
    ecog_0_pct = 0.50,
    ecog_1_pct = 0.50,

    # Race (approximate)
    race_white_pct = 0.65,
    race_asian_pct = 0.18,
    race_black_pct = 0.08,
    race_other_pct = 0.09,

    # MMR Status (key stratification)
    mmr_dmmr_pct = 0.274,  # 222/810
    mmr_pmmr_pct = 0.726,  # 588/810

    # Histology
    histology_endometrioid_pct = 0.60,
    histology_serous_pct = 0.25,
    histology_clear_cell_pct = 0.05,
    histology_mixed_other_pct = 0.10,

    # Disease setting
    disease_primary_pct = 0.67,
    disease_recurrent_pct = 0.33,

    # Prior therapy
    prior_therapy_yes_pct = 0.10,
    prior_therapy_no_pct = 0.90
  ),

  # ===========================================================================
  # PRIMARY EFFICACY - PFS by MMR status
  # ===========================================================================
  primary_efficacy = list(

    # dMMR cohort (n=222)
    dmmr = list(
      n_pembro = 111,
      n_placebo = 111,

      # PFS
      pfs_hr = 0.30,
      pfs_hr_ci_lower = 0.19,
      pfs_hr_ci_upper = 0.48,
      pfs_p_value = 0.0001,

      pfs_median_pembro = NA,    # Not reached
      pfs_median_placebo = 6.5,  # months

      pfs_rate_6mo_pembro = 0.82,
      pfs_rate_6mo_placebo = 0.50,
      pfs_rate_12mo_pembro = 0.74,
      pfs_rate_12mo_placebo = 0.36,

      pfs_events_pembro = 28,
      pfs_events_placebo = 70
    ),

    # pMMR cohort (n=588)
    pmmr = list(
      n_pembro = 294,
      n_placebo = 294,

      # PFS
      pfs_hr = 0.60,
      pfs_hr_ci_lower = 0.46,
      pfs_hr_ci_upper = 0.78,
      pfs_p_value = 0.0001,

      pfs_median_pembro = 11.1,  # months
      pfs_median_placebo = 8.5,  # months

      pfs_rate_6mo_pembro = 0.72,
      pfs_rate_6mo_placebo = 0.62,
      pfs_rate_12mo_pembro = 0.46,
      pfs_rate_12mo_placebo = 0.34,

      pfs_events_pembro = 156,
      pfs_events_placebo = 198
    )
  ),

  # ===========================================================================
  # SECONDARY EFFICACY - OS, ORR
  # ===========================================================================
  secondary_efficacy = list(

    # OS (interim, not yet mature)
    os_hr_dmmr = 0.45,  # Estimated
    os_hr_pmmr = 0.75,  # Estimated

    # Overall Response Rate
    orr_pembro_dmmr = 0.77,
    orr_placebo_dmmr = 0.53,
    orr_pembro_pmmr = 0.63,
    orr_placebo_pmmr = 0.54,

    # Complete Response Rate
    cr_pembro_dmmr = 0.30,
    cr_placebo_dmmr = 0.15,
    cr_pembro_pmmr = 0.18,
    cr_placebo_pmmr = 0.12,

    # Disease Control Rate
    dcr_pembro = 0.88,
    dcr_placebo = 0.82,

    # Duration of Response (months)
    dor_median_pembro = 18.0,  # Estimated
    dor_median_placebo = 9.0   # Estimated
  ),

  # ===========================================================================
  # SAFETY - Overall
  # ===========================================================================
  safety_overall = list(

    # Any AE
    ae_any_pembro_pct = 0.99,
    ae_any_placebo_pct = 0.98,

    # Grade 3+ AE
    ae_grade3plus_pembro_pct = 0.65,
    ae_grade3plus_placebo_pct = 0.55,

    # Serious AE
    ae_serious_pembro_pct = 0.35,
    ae_serious_placebo_pct = 0.28,

    # AE leading to discontinuation
    ae_discontinuation_pembro_pct = 0.12,
    ae_discontinuation_placebo_pct = 0.08,

    # AE leading to death
    ae_death_pembro_pct = 0.02,
    ae_death_placebo_pct = 0.01
  ),

  # ===========================================================================
  # SAFETY - Specific AEs (All Grades, Pembrolizumab arm)
  # ===========================================================================
  safety_specific = list(

    # Hematologic
    ae_anemia_pct = 0.55,
    ae_neutropenia_pct = 0.42,
    ae_thrombocytopenia_pct = 0.28,
    ae_leukopenia_pct = 0.20,

    # Gastrointestinal
    ae_nausea_pct = 0.50,
    ae_diarrhea_pct = 0.32,
    ae_constipation_pct = 0.28,
    ae_vomiting_pct = 0.25,

    # General
    ae_fatigue_pct = 0.48,
    ae_asthenia_pct = 0.18,

    # Skin
    ae_alopecia_pct = 0.45,
    ae_rash_pct = 0.15,

    # Nervous system
    ae_peripheral_neuropathy_pct = 0.35,

    # Metabolism
    ae_decreased_appetite_pct = 0.22
  ),

  # ===========================================================================
  # SAFETY - Immune-related AEs
  # ===========================================================================
  safety_irae = list(
    irae_any_pct = 0.25,
    irae_any_grade3plus_pct = 0.06,

    # Specific irAEs
    irae_hypothyroidism_pct = 0.12,
    irae_hyperthyroidism_pct = 0.05,
    irae_pneumonitis_pct = 0.03,
    irae_colitis_pct = 0.02,
    irae_hepatitis_pct = 0.02,
    irae_nephritis_pct = 0.01,
    irae_skin_pct = 0.08,
    irae_infusion_reaction_pct = 0.03
  ),

  # ===========================================================================
  # EXPOSURE
  # ===========================================================================
  exposure = list(
    # Treatment duration (months)
    median_treatment_duration_pembro = 9.5,
    median_treatment_duration_placebo = 7.0,

    # Number of cycles
    median_cycles_pembro = 12,
    median_cycles_placebo = 9,

    # Dose intensity
    dose_intensity_pembro_pct = 0.92,
    dose_intensity_placebo_pct = 0.94,

    # Dose modifications
    dose_reduction_pembro_pct = 0.35,
    dose_reduction_placebo_pct = 0.30,
    dose_interruption_pembro_pct = 0.45,
    dose_interruption_placebo_pct = 0.38
  ),

  # ===========================================================================
  # DISPOSITION
  # ===========================================================================
  disposition = list(
    # Completed treatment as planned
    completed_treatment_pembro_pct = 0.55,
    completed_treatment_placebo_pct = 0.45,

    # Discontinuation reasons
    discontinued_ae_pembro_pct = 0.12,
    discontinued_ae_placebo_pct = 0.08,
    discontinued_pd_pembro_pct = 0.28,
    discontinued_pd_placebo_pct = 0.38,
    discontinued_withdrawal_pembro_pct = 0.03,
    discontinued_withdrawal_placebo_pct = 0.04,
    discontinued_death_pembro_pct = 0.02,
    discontinued_death_placebo_pct = 0.03
  )
)

#' Get flattened target values for scoring
#' @return Named list of all target values
get_flat_targets <- function() {
  targets <- list()

  # Demographics
  for (name in names(KN868_TARGETS$demographics)) {
    targets[[name]] <- KN868_TARGETS$demographics[[name]]
  }

  # Primary efficacy - dMMR
  targets$pfs_hr_dmmr <- KN868_TARGETS$primary_efficacy$dmmr$pfs_hr
  targets$pfs_median_pembro_dmmr <- KN868_TARGETS$primary_efficacy$dmmr$pfs_median_pembro
  targets$pfs_median_placebo_dmmr <- KN868_TARGETS$primary_efficacy$dmmr$pfs_median_placebo
  targets$pfs_rate_12mo_pembro_dmmr <- KN868_TARGETS$primary_efficacy$dmmr$pfs_rate_12mo_pembro
  targets$pfs_rate_12mo_placebo_dmmr <- KN868_TARGETS$primary_efficacy$dmmr$pfs_rate_12mo_placebo


  # Primary efficacy - pMMR
  targets$pfs_hr_pmmr <- KN868_TARGETS$primary_efficacy$pmmr$pfs_hr
  targets$pfs_median_pembro_pmmr <- KN868_TARGETS$primary_efficacy$pmmr$pfs_median_pembro
  targets$pfs_median_placebo_pmmr <- KN868_TARGETS$primary_efficacy$pmmr$pfs_median_placebo
  targets$pfs_rate_12mo_pembro_pmmr <- KN868_TARGETS$primary_efficacy$pmmr$pfs_rate_12mo_pembro
  targets$pfs_rate_12mo_placebo_pmmr <- KN868_TARGETS$primary_efficacy$pmmr$pfs_rate_12mo_placebo

  # Secondary efficacy
  for (name in names(KN868_TARGETS$secondary_efficacy)) {
    targets[[name]] <- KN868_TARGETS$secondary_efficacy[[name]]
  }

  # Safety
  for (name in names(KN868_TARGETS$safety_overall)) {
    targets[[name]] <- KN868_TARGETS$safety_overall[[name]]
  }
  for (name in names(KN868_TARGETS$safety_specific)) {
    targets[[name]] <- KN868_TARGETS$safety_specific[[name]]
  }
  for (name in names(KN868_TARGETS$safety_irae)) {
    targets[[name]] <- KN868_TARGETS$safety_irae[[name]]
  }

  # Exposure
  for (name in names(KN868_TARGETS$exposure)) {
    targets[[name]] <- KN868_TARGETS$exposure[[name]]
  }

  # Disposition
  for (name in names(KN868_TARGETS$disposition)) {
    targets[[name]] <- KN868_TARGETS$disposition[[name]]
  }

  targets
}
