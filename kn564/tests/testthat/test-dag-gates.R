# test-dag-gates.R — Tests for DAG structural consistency gates
# KEYNOTE-564 IPD Causal-DAG Simulator

library(testthat)

# Source modules
source("../../R/dag_state.R")
source("../../R/baseline.R")
source("../../R/longitudinal.R")
source("../../R/recurrence.R")
source("../../R/post_recurrence.R")
source("../../R/outcomes.R")

# Run a small simulation for testing
set.seed(564001)
params <- load_params("../../params/initial_params.json")
params$N <- 200L  # Smaller for speed

bl <- generate_baseline(n = params$N, params = params, seed = 564001)
longitudinal <- simulate_longitudinal(bl, params)
recurrence_dt <- simulate_recurrence(bl, longitudinal$ex_long, params)
death_dt <- simulate_post_recurrence(bl, recurrence_dt, params)
endpoints <- derive_endpoints(bl, recurrence_dt, death_dt)

# ─── Gate Tests ──────────────────────────────────────────────────────────────

test_that("Thyroid labs are consistent with thyroid state", {
  # Patients with hypothyroidism AE should have elevated TSH at nearby visits
  ae_hypo <- longitudinal$ae_long[AETERM == "HYPOTHYROIDISM"]
  if (nrow(ae_hypo) > 0) {
    lb_tsh <- longitudinal$lb_long[LBTEST == "TSH"]
    merged <- merge(ae_hypo[, .(SUBJID, AESTDT)],
                    lb_tsh, by = "SUBJID", allow.cartesian = TRUE)
    merged[, day_diff := abs(AESTDT - VISIT_DAY)]
    closest <- merged[, .SD[which.min(day_diff)], by = .(SUBJID, AESTDT)]
    pct_elevated <- mean(closest$LBORRES > 10, na.rm = TRUE)
    expect_gt(pct_elevated, 0.50)
  }
})

test_that("DFS_DAY correlates with latent recurrence day for events", {
  events <- endpoints[DFS_EVENT == 1L & DFS_EVENT_TYPE == "RECURRENCE"]
  if (nrow(events) > 5) {
    merged <- merge(events[, .(SUBJID, DFS_DAY)],
                    recurrence_dt[, .(SUBJID, LATENT_RECURRENCE_DAY)],
                    by = "SUBJID")
    corr <- cor(merged$DFS_DAY, merged$LATENT_RECURRENCE_DAY, use = "complete.obs")
    expect_gt(corr, 0.90)  # Relaxed for small N
  }
})

test_that("Temporal ordering: death after recurrence for post-recurrence deaths", {
  merged <- merge(
    recurrence_dt[!is.na(OBSERVED_RECURRENCE_DAY), .(SUBJID, OBSERVED_RECURRENCE_DAY)],
    death_dt[DEATH_CAUSE == "POST_RECURRENCE" & !is.na(DEATH_DAY), .(SUBJID, DEATH_DAY)],
    by = "SUBJID"
  )
  if (nrow(merged) > 0) {
    expect_true(all(merged$DEATH_DAY >= merged$OBSERVED_RECURRENCE_DAY))
  }
})

test_that("Risk category direction: M1 NED has worse DFS than M0 int-high", {
  median_dfs <- endpoints[DFS_EVENT == 1L,
                          .(median_dfs = median(DFS_DAY)), by = RISK_CATEGORY]
  m0ih <- median_dfs[RISK_CATEGORY == "M0_INT_HIGH", median_dfs]
  m1ned <- median_dfs[RISK_CATEGORY == "M1_NED", median_dfs]
  if (length(m0ih) > 0 && length(m1ned) > 0) {
    expect_lt(m1ned, m0ih)
  }
})

test_that("AE frailty correlation: immune AE types show within-patient clustering", {
  immune_aes <- longitudinal$ae_long[AECAT %in% c("IMMUNE_MEDIATED", "THYROID")]
  if (nrow(immune_aes) > 50) {
    counts <- dcast(immune_aes, SUBJID ~ AETERM, value.var = "AEGR", fun.aggregate = length)
    ae_cols <- setdiff(names(counts), "SUBJID")
    if (length(ae_cols) >= 2) {
      corr_mat <- cor(counts[, ..ae_cols], use = "pairwise.complete.obs")
      upper_tri <- corr_mat[upper.tri(corr_mat)]
      mean_corr <- mean(upper_tri, na.rm = TRUE)
      expect_gt(mean_corr, 0.0)  # Positive correlation expected
    }
  }
})

test_that("Treatment arm has better DFS than placebo", {
  km_pembro <- km_at_landmark(
    endpoints[ARM == "PEMBROLIZUMAB"]$DFS_DAY,
    endpoints[ARM == "PEMBROLIZUMAB"]$DFS_EVENT,
    48 * 30.44
  )
  km_placebo <- km_at_landmark(
    endpoints[ARM == "PLACEBO"]$DFS_DAY,
    endpoints[ARM == "PLACEBO"]$DFS_EVENT,
    48 * 30.44
  )
  expect_gt(km_pembro, km_placebo)
})

test_that("All DFS_DAY values are positive and bounded", {
  expect_true(all(endpoints$DFS_DAY > 0))
  expect_true(all(endpoints$DFS_DAY <= KN564_CONSTANTS$ADMIN_CENSOR_DAY))
})

test_that("All OS_DAY values are >= DFS_DAY", {
  expect_true(all(endpoints$OS_DAY >= endpoints$DFS_DAY))
})
