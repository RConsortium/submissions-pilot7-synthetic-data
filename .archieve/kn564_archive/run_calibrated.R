## Run KEYNOTE-564 simulation with calibration enabled
setwd("C:/Users/lengnx/Documents/ipd_sim_examples/kn564")
source("R/run.R")
results <- run_simulation(calibrate = TRUE, verbose = TRUE)
