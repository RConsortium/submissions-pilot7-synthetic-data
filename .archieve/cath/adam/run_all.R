# Build the CATH ADaM datasets. Each ad_*.R is an admiral derivation reading this
# environment's generated SDTM (../sdtm/sdtm-derived/xpt/, resolved by 00_setup.R)
# and writing <adam>.rds + <adam>.csv to adam-derived/. ADSL runs first.
#
# Run from this directory:
#   cd adam
#   Rscript run_all.R          # then: Rscript export_xpt.R

pipeline <- c(
  "ad_adsl.R",   # must run first
  "ad_adae.R",
  "ad_advs.R",
  "ad_adlb.R",
  "ad_adrs.R"
)

for (f in pipeline) {
  message("\n========== ", f, " ==========")
  t0 <- Sys.time()
  source(f, local = FALSE)
  message(sprintf("  done in %.1fs", as.numeric(difftime(Sys.time(), t0, units = "secs"))))
}
