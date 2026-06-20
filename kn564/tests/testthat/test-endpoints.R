# test-endpoints.R — Tests for endpoint derivation logic
# KEYNOTE-564 IPD Causal-DAG Simulator

library(testthat)

source("../../R/dag_state.R")
source("../../R/outcomes.R")

test_that("km_at_landmark computes correct survival for simple case", {
  # 10 patients, 3 events at times 100, 200, 300
  time <- c(100, 200, 300, 400, 500, 600, 700, 800, 900, 1000)
  event <- c(1, 1, 1, 0, 0, 0, 0, 0, 0, 0)

  # At time 100: 1 event out of 10 at risk -> S = 9/10 = 0.9
  km_100 <- km_at_landmark(time, event, 100)
  expect_equal(km_100, 0.9)

  # At time 200: S(100) * (1 - 1/9) = 0.9 * 8/9 = 0.8
 km_200 <- km_at_landmark(time, event, 200)
  expect_equal(km_200, 0.8)

  # At time 50 (before any event): S = 1.0
  km_50 <- km_at_landmark(time, event, 50)
  expect_equal(km_50, 1.0)
})

test_that("km_at_landmark handles all-censored data", {
  time <- c(100, 200, 300)
  event <- c(0, 0, 0)
  expect_equal(km_at_landmark(time, event, 500), 1.0)
})

test_that("weibull_quantile produces valid times", {
  set.seed(42)
  times <- sapply(runif(100), weibull_quantile, shape = 0.85, scale = 2000)
  expect_true(all(times > 0))
  expect_true(all(is.finite(times)))
})

test_that("weibull_surv is monotone decreasing", {
  t_seq <- seq(0, 5000, by = 100)
  surv <- sapply(t_seq, weibull_surv, shape = 0.85, scale = 2000)
  # Should be non-increasing
  expect_true(all(diff(surv) <= 0))
  # S(0) = 1
  expect_equal(surv[1], 1.0)
})

test_that("expit and logit are inverse functions", {
  x <- seq(-5, 5, by = 0.5)
  expect_equal(logit(expit(x)), x, tolerance = 1e-10)

  p <- seq(0.01, 0.99, by = 0.1)
  expect_equal(expit(logit(p)), p, tolerance = 1e-10)
})

test_that("next_imaging_day finds correct next scan", {
  imaging <- c(84, 168, 252, 336, 448, 560, 672)

  # Event on day 100 should be detected at day 168

  expect_equal(next_imaging_day(100, imaging), 168)

  # Event on day 84 should be detected at day 84
  expect_equal(next_imaging_day(84, imaging), 84)

  # Event beyond all scans returns NA
  expect_true(is.na(next_imaging_day(700, imaging)))
})

test_that("day_to_cycle and cycle_to_day are consistent", {
  # Day 1 is cycle 1
  expect_equal(day_to_cycle(1), 1L)
  # Day 21 is cycle 1
  expect_equal(day_to_cycle(21), 1L)
  # Day 22 is cycle 2
  expect_equal(day_to_cycle(22), 2L)
  # Day 357 is cycle 17
  expect_equal(day_to_cycle(357), 17L)

  # Cycle 1 starts at day 1
  expect_equal(cycle_to_day(1), 1L)
  # Cycle 2 starts at day 22
  expect_equal(cycle_to_day(2), 22L)
  # Cycle 17 starts at day 337
  expect_equal(cycle_to_day(17), 337L)
})

test_that("apply_frailty produces valid probabilities", {
  set.seed(42)
  base_probs <- c(0.01, 0.05, 0.10, 0.50, 0.90)
  frailties <- rnorm(100)

  for (bp in base_probs) {
    adjusted <- sapply(frailties, function(f) apply_frailty(bp, f, 0.5))
    expect_true(all(adjusted > 0 & adjusted < 1))
  }
})
