#!/usr/bin/env Rscript
# run_all.R — run every per-domain CRF -> SDTM derivation program and write the
# reconstructed SDTM to sdtm/sdtm-derived/ (one CSV per domain).
#
# ARA06 has no canonical SDTM truth (it is forward-simulated from a causal DAG),
# so there is no round-trip oracle: correctness is checked downstream against the
# CDISC CORE rules engine via validate_sdtm.py.
#
# Run from anywhere:
#   Rscript sdtm/run_all.R            # all registered domains
#   Rscript sdtm/run_all.R dm lb      # only the named domains
#
# Override I/O with env vars (used by the package's generate_sdtm):
#   ARA06_EDC_DIR  (default ../edc)   ARA06_SDTM_OUT (default ./sdtm-derived)

.args <- commandArgs(trailingOnly = FALSE)
.fa <- sub("^--file=", "", .args[grep("^--file=", .args)])
SCRIPT_DIR <- if (length(.fa)) dirname(normalizePath(.fa)) else normalizePath(".")
ENV_DIR <- normalizePath(file.path(SCRIPT_DIR, ".."))
EDC_DIR <- Sys.getenv("ARA06_EDC_DIR", unset = file.path(ENV_DIR, "edc"))
OUT     <- Sys.getenv("ARA06_SDTM_OUT", unset = file.path(SCRIPT_DIR, "sdtm-derived"))

source(file.path(SCRIPT_DIR, "common.R"))

# Registry: domain -> derivation file, function, output stem.
REG <- list(
  dm     = list(file = "derive_dm.R",     fn = "derive_dm"),
  vs     = list(file = "derive_vs.R",     fn = "derive_vs"),
  mh     = list(file = "derive_mh.R",     fn = "derive_mh"),
  suppmh = list(file = "derive_suppmh.R", fn = "derive_suppmh"),
  ex     = list(file = "derive_ex.R",     fn = "derive_ex"),
  ae     = list(file = "derive_ae.R",     fn = "derive_ae"),
  lb     = list(file = "derive_lb.R",     fn = "derive_lb"),
  rs     = list(file = "derive_rs.R",     fn = "derive_rs"),
  ds     = list(file = "derive_ds.R",     fn = "derive_ds")
)

domains <- commandArgs(trailingOnly = TRUE)
if (!length(domains)) domains <- names(REG)

# Source every derivation up front (SUPPMH calls derive_mh()).
for (spec in REG) source(file.path(SCRIPT_DIR, spec$file))

ok <- TRUE
for (d in domains) {
  spec <- REG[[d]]
  if (is.null(spec)) { message("no derivation registered for: ", d); next }
  derived <- tryCatch(get(spec$fn)(), error = function(e) { ok <<- FALSE; message("FAIL ", d, ": ", conditionMessage(e)); NULL })
  if (is.null(derived)) next
  write_csv(derived, file.path(OUT, paste0(d, ".csv")))
  cat(sprintf("%-7s OK  (%d rows, %d cols)\n", d, nrow(derived), ncol(derived)))
}

cat(sprintf("\nSDTM written to %s\n", OUT))
if (!ok) quit(status = 1)
