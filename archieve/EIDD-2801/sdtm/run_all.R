#!/usr/bin/env Rscript
# run_all.R — run every per-domain CRF -> SDTM derivation program and write the
# reconstructed SDTM to sdtm/sdtm-derived/ (one CSV per domain).
#
# EIDD-2801 is forward-simulated (no canonical SDTM truth), so there is no
# round-trip oracle: conformance is checked downstream against the CDISC CORE
# rules engine via validate_sdtm.py.
#
# Run from anywhere:
#   Rscript sdtm/run_all.R            # all registered domains
#   Rscript sdtm/run_all.R dm lb      # only the named domains
#
# Override I/O with env vars:
#   EIDD_EDC_DIR   (default ../edc)   EIDD_SDTM_OUT (default ./sdtm-derived)

.args <- commandArgs(trailingOnly = FALSE)
.fa <- sub("^--file=", "", .args[grep("^--file=", .args)])
SCRIPT_DIR <- if (length(.fa)) dirname(normalizePath(.fa)) else normalizePath(".")
ENV_DIR <- normalizePath(file.path(SCRIPT_DIR, ".."))
EDC_DIR <- Sys.getenv("EIDD_EDC_DIR", unset = file.path(ENV_DIR, "edc"))
OUT     <- Sys.getenv("EIDD_SDTM_OUT", unset = file.path(SCRIPT_DIR, "sdtm-derived"))

source(file.path(SCRIPT_DIR, "common.R"))

# Registry: domain -> derivation file, function.
REG <- list(
  dm = list(file = "derive_dm.R", fn = "derive_dm"),
  sv = list(file = "derive_sv.R", fn = "derive_sv"),
  ie = list(file = "derive_ie.R", fn = "derive_ie"),
  ex = list(file = "derive_ex.R", fn = "derive_ex"),
  vs = list(file = "derive_vs.R", fn = "derive_vs"),
  eg = list(file = "derive_eg.R", fn = "derive_eg"),
  lb = list(file = "derive_lb.R", fn = "derive_lb"),
  pc = list(file = "derive_pc.R", fn = "derive_pc"),
  pe = list(file = "derive_pe.R", fn = "derive_pe"),
  ml = list(file = "derive_ml.R", fn = "derive_ml")
)

domains <- commandArgs(trailingOnly = TRUE)
if (!length(domains)) domains <- names(REG)

for (spec in REG) source(file.path(SCRIPT_DIR, spec$file))

ok <- TRUE
for (d in domains) {
  spec <- REG[[d]]
  if (is.null(spec)) { message("no derivation registered for: ", d); next }
  derived <- tryCatch(get(spec$fn)(),
                      error = function(e) { ok <<- FALSE
                        message("FAIL ", d, ": ", conditionMessage(e)); NULL })
  if (is.null(derived)) next
  if (nrow(derived) == 0) { cat(sprintf("%-4s (0 rows — skipped)\n", d)); next }
  write_csv(derived, file.path(OUT, paste0(d, ".csv")))
  cat(sprintf("%-4s OK  (%d rows, %d cols)\n", d, nrow(derived), ncol(derived)))
}

cat(sprintf("\nSDTM written to %s\n", OUT))
if (!ok) quit(status = 1)
