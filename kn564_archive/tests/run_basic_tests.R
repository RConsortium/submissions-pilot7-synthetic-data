# Basic verification tests for KEYNOTE-564 simulator
# Run: Rscript tests/run_basic_tests.R

setwd(sub("/tests$", "", getwd()))
if (!file.exists("R/dag_state.R")) setwd("C:/Users/lengnx/Documents/ipd_sim_examples/kn564")

# ─── Test helper functions ────────────────────────────────────────────────────

expit <- function(x) 1 / (1 + exp(-x))
logit <- function(p) log(p / (1 - p))
weibull_quantile <- function(u, shape, scale) scale * (-log(1 - u))^(1 / shape)

# expit/logit tests
stopifnot(abs(expit(0) - 0.5) < 1e-10)
stopifnot(abs(logit(0.5) - 0) < 1e-10)
stopifnot(abs(expit(logit(0.3)) - 0.3) < 1e-10)
cat("[PASS] expit/logit\n")

# weibull_quantile tests
set.seed(42)
t_val <- weibull_quantile(0.5, 0.85, 2000)
stopifnot(t_val > 0 && is.finite(t_val))
cat(sprintf("[PASS] weibull_quantile = %.1f\n", t_val))

# ─── Test JSON loading ────────────────────────────────────────────────────────

library(jsonlite)
params <- fromJSON("params/initial_params.json")
stopifnot(params$N == 994)
stopifnot(params$recurrence$weibull_shape == 0.85)
cat("[PASS] params loading\n")

targets <- fromJSON("data-raw/targets.json")
stopifnot(targets$dfs$hr == 0.72)
stopifnot(targets$os$hr == 0.62)
stopifnot(targets$N$total == 994)
cat("[PASS] targets loading\n")

# ─── Test imaging schedule generation ─────────────────────────────────────────

generate_imaging_schedule <- function(max_day = 1740L) {
  imaging_days <- integer(0)
  current_day <- 1L
  year1_end <- 365L
  while (current_day <= min(year1_end, max_day)) {
    current_day <- current_day + 84L
    if (current_day <= max_day) imaging_days <- c(imaging_days, current_day)
  }
  year4_end <- 4L * 365L
  while (current_day <= min(year4_end, max_day)) {
    current_day <- current_day + 112L
    if (current_day <= max_day) imaging_days <- c(imaging_days, current_day)
  }
  while (current_day <= max_day) {
    current_day <- current_day + 168L
    if (current_day <= max_day) imaging_days <- c(imaging_days, current_day)
  }
  sort(unique(imaging_days))
}

schedule <- generate_imaging_schedule()
stopifnot(length(schedule) > 10)
stopifnot(all(diff(schedule) > 0))
stopifnot(schedule[1] == 85)  # First scan at day 85 (1 + 84)
cat(sprintf("[PASS] imaging schedule: %d visits, first=%d, last=%d\n",
            length(schedule), schedule[1], schedule[length(schedule)]))

# ─── Test apply_frailty ───────────────────────────────────────────────────────

apply_frailty <- function(base_prob, frailty, beta_frailty) {
  log_odds <- logit(pmin(pmax(base_prob, 1e-6), 1 - 1e-6))
  expit(log_odds + beta_frailty * frailty)
}

# Positive frailty should increase probability
p_high <- apply_frailty(0.1, 2.0, 0.5)
p_low <- apply_frailty(0.1, -2.0, 0.5)
stopifnot(p_high > 0.1)
stopifnot(p_low < 0.1)
stopifnot(p_high > p_low)
cat("[PASS] apply_frailty\n")

# ─── Test file structure ──────────────────────────────────────────────────────

required_files <- c(
  "R/dag_state.R", "R/baseline.R", "R/longitudinal.R",
  "R/recurrence.R", "R/post_recurrence.R", "R/outcomes.R",
  "R/emit_source.R", "R/calibrate.R", "R/sdtm.R", "R/adam.R", "R/run.R",
  "params/initial_params.json", "data-raw/targets.json",
  "intake/NCT03142334.json", "DESCRIPTION",
  "crf_schema.md", "dag_spec.md",
  "metadata/crf_schema.csv", "metadata/sdtm_spec.csv", "metadata/adam_spec.csv"
)

for (f in required_files) {
  stopifnot(file.exists(f))
}
cat(sprintf("[PASS] All %d required files exist\n", length(required_files)))

# ─── Test R files parse ───────────────────────────────────────────────────────

r_files <- list.files("R", pattern = "[.]R$", full.names = TRUE)
for (f in r_files) {
  tryCatch(parse(f), error = function(e) stop(sprintf("Parse error in %s: %s", f, e$message)))
}
cat(sprintf("[PASS] All %d R files parse successfully\n", length(r_files)))

cat("\n══════════════════════════════════════════\n")
cat("  All basic tests PASSED\n")
cat("══════════════════════════════════════════\n")
