# test-calibration.R — Tests for calibration logic
# KEYNOTE-564 IPD Causal-DAG Simulator

library(testthat)

source("../../R/dag_state.R")
source("../../R/calibrate.R")

test_that("load_targets returns expected structure", {
  targets <- load_targets("../../data-raw/targets.json")

  expect_true("dfs" %in% names(targets))
  expect_true("os" %in% names(targets))
  expect_true("ae" %in% names(targets))
  expect_true("baseline" %in% names(targets))
  expect_true("tolerances" %in% names(targets))

  expect_equal(targets$N$total, 994)
  expect_equal(targets$dfs$hr, 0.72)
  expect_equal(targets$os$hr, 0.62)
})

test_that("load_params returns expected structure", {
  params <- load_params("../../params/initial_params.json")

  expect_true("recurrence" %in% names(params))
  expect_true("thyroid" %in% names(params))
  expect_true("ae_per_cycle" %in% names(params))
  expect_true("dose_modification" %in% names(params))
  expect_true("imaging" %in% names(params))

  expect_equal(params$N, 994)
  expect_equal(params$recurrence$weibull_shape, 0.85)
})

test_that("all_gates_pass works correctly", {
  gates_all_pass <- list(
    g1 = list(pass = TRUE),
    g2 = list(pass = TRUE),
    g3 = list(pass = TRUE)
  )
  expect_true(all_gates_pass(gates_all_pass))

  gates_one_fail <- list(
    g1 = list(pass = TRUE),
    g2 = list(pass = FALSE),
    g3 = list(pass = TRUE)
  )
  expect_false(all_gates_pass(gates_one_fail))
})

test_that("compute_calibration_score returns non-negative value", {
  gate_results <- list(
    dfs = list(
      metrics = list(hr = 0.75, km48_pembro = 0.65, km48_placebo = 0.55),
      targets = list(hr = 0.72, km48_pembro = 0.649, km48_placebo = 0.566)
    ),
    os = list(
      metrics = list(hr = 0.65, km48_pembro = 0.90, km48_placebo = 0.85),
      targets = list(hr = 0.62, km48_pembro = 0.912, km48_placebo = 0.860)
    ),
    ae_rates = list(
      metrics = list(trae_pembro = 0.78),
      targets = list(trae_pembro = 0.791)
    )
  )

  score <- compute_calibration_score(gate_results)
  expect_true(score >= 0)
  expect_true(is.finite(score))
})

test_that("adjust_parameters modifies params when gates fail", {
  params <- load_params("../../params/initial_params.json")
  targets <- load_targets("../../data-raw/targets.json")

  gate_results <- list(
    dfs = list(
      pass = FALSE,
      metrics = list(hr = 0.85, km48_pembro = 0.70, km48_placebo = 0.50),
      targets = list(hr = 0.72, km48_pembro = 0.649, km48_placebo = 0.566)
    ),
    ae_rates = list(
      pass = FALSE,
      metrics = list(trae_pembro = 0.60),
      targets = list(trae_pembro = 0.791)
    ),
    discontinuation = list(
      pass = TRUE,
      metrics = list(disc_pembro = 0.21),
      targets = list(disc_pembro = 0.211)
    )
  )

  adjusted <- adjust_parameters(params, gate_results, targets, iter = 1)

  # Treatment effect should have been strengthened (more negative)
  expect_lt(adjusted$recurrence$treatment_effect_on_treatment,
            params$recurrence$treatment_effect_on_treatment)
})

test_that("imaging schedule generates valid days", {
  schedule <- generate_imaging_schedule()
  expect_true(length(schedule) > 0)
  expect_true(all(schedule > 0))
  expect_true(all(diff(schedule) > 0))  # Strictly increasing
  expect_true(max(schedule) <= KN564_CONSTANTS$ADMIN_CENSOR_DAY)
})

test_that("dosing visits are correctly generated", {
  visits <- generate_dosing_visits()
  expect_equal(nrow(visits), 17)
  expect_equal(visits$visit_day[1], 1L)
  expect_equal(visits$visit_day[2], 22L)
  expect_equal(visits$visit_day[17], 337L)
})
