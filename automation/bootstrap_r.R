## --------------------------------------------------------------------
## bootstrap_r.R — ensure R + every package in cart-t/renv.lock is
## installed via {pak}. Idempotent: installs only what is missing or
## version-mismatched.
##
## Usage:   Rscript automation/bootstrap_r.R
## Exits:   0 = environment ready;  non-zero = bootstrap failed.
## --------------------------------------------------------------------

LOCKFILE <- "cart-t/renv.lock"

`%||%` <- function(a, b) if (is.null(a) || length(a) == 0L) b else a

log <- function(...) cat(format(Sys.time(), "[%H:%M:%S]"), ..., "\n", sep = " ")
die <- function(...) { log("FATAL:", ...); quit(status = 1L, save = "no") }

## ---- 1. R itself ----------------------------------------------------
if (!file.exists(LOCKFILE)) die("renv.lock not found at", LOCKFILE)

lock <- tryCatch(
  jsonlite::fromJSON(LOCKFILE, simplifyVector = FALSE),
  error = function(e) {
    if (!requireNamespace("jsonlite", quietly = TRUE)) {
      install.packages("jsonlite", repos = "https://cloud.r-project.org")
    }
    jsonlite::fromJSON(LOCKFILE, simplifyVector = FALSE)
  }
)

want_r <- lock$R$Version
have_r <- paste(R.version$major, R.version$minor, sep = ".")
if (!is.null(want_r) && want_r != have_r) {
  log("WARNING: renv.lock wants R", want_r, "— running R", have_r,
      "(continuing; minor mismatches are usually fine)")
}

## ---- 2. Repos (so pak hits the same mirror renv used) ---------------
if (length(lock$R$Repositories)) {
  repos <- setNames(
    vapply(lock$R$Repositories, `[[`, character(1), "URL"),
    vapply(lock$R$Repositories, `[[`, character(1), "Name")
  )
  options(repos = repos)
  log("Repos set:", paste(names(repos), repos, sep = "=", collapse = ", "))
}

## ---- 3. pak --------------------------------------------------------
if (!requireNamespace("pak", quietly = TRUE)) {
  log("Installing {pak} from r-lib universe…")
  install.packages(
    "pak",
    repos = sprintf(
      "https://r-lib.github.io/p/pak/stable/%s/%s/%s",
      .Platform$pkgType, R.Version()$os, R.Version()$arch
    )
  )
  if (!requireNamespace("pak", quietly = TRUE)) {
    install.packages("pak", repos = getOption("repos"))
  }
  if (!requireNamespace("pak", quietly = TRUE)) die("could not install {pak}")
}

## ---- 4. Diff installed vs locked ------------------------------------
pkgs <- lock$Packages %||% list()
if (!length(pkgs)) die("renv.lock contains no Packages section")

inst <- as.data.frame(
  installed.packages()[, c("Package", "Version"), drop = FALSE],
  stringsAsFactors = FALSE
)
have_ver <- as.list(setNames(inst$Version, inst$Package))

make_spec <- function(name, info) {
  src  <- info$Source %||% "Repository"
  vers <- info$Version
  switch(
    src,
    "Repository"    = sprintf("%s@%s", name, vers),
    "CRAN"          = sprintf("%s@%s", name, vers),
    "GitHub"        = sprintf(
      "%s/%s%s",
      info$RemoteUsername, info$RemoteRepo,
      if (!is.null(info$RemoteSha))  paste0("@", info$RemoteSha)
      else if (!is.null(info$RemoteRef)) paste0("@", info$RemoteRef)
      else ""
    ),
    "Bioconductor"  = sprintf("bioc::%s", name),
    "git"           = sprintf("git::%s%s",
                              info$RemoteUrl,
                              if (!is.null(info$RemoteSha)) paste0("@", info$RemoteSha) else ""),
    name
  )
}

missing_pkgs <- character(0)
wrong_ver    <- character(0)
specs        <- character(0)

for (name in names(pkgs)) {
  info <- pkgs[[name]]
  want <- info$Version
  have <- have_ver[[name]]
  if (is.null(have)) {
    missing_pkgs <- c(missing_pkgs, name)
    specs <- c(specs, make_spec(name, info))
  } else if (!is.null(want) && have != want) {
    wrong_ver <- c(wrong_ver, sprintf("%s (have %s, want %s)", name, have, want))
    specs <- c(specs, make_spec(name, info))
  }
}

log(sprintf(
  "Lockfile lists %d package(s): %d already match, %d missing, %d version-mismatched.",
  length(pkgs),
  length(pkgs) - length(missing_pkgs) - length(wrong_ver),
  length(missing_pkgs), length(wrong_ver)
))

if (!length(specs)) {
  log("Environment ready — nothing to install.")
  quit(status = 0L, save = "no")
}

if (length(missing_pkgs)) log("  missing:    ", paste(missing_pkgs, collapse = ", "))
if (length(wrong_ver))    log("  mismatched: ", paste(wrong_ver,    collapse = ", "))

## ---- 5. Install via pak --------------------------------------------
log(sprintf("Installing %d package(s) via {pak}…", length(specs)))
ok <- tryCatch({
  pak::pak(specs, ask = FALSE)
  TRUE
}, error = function(e) { log("pak::pak failed:", conditionMessage(e)); FALSE })

if (!ok) die("package installation failed — see messages above")

## ---- 6. Re-verify ---------------------------------------------------
inst2 <- as.data.frame(
  installed.packages()[, c("Package", "Version"), drop = FALSE],
  stringsAsFactors = FALSE
)
have2 <- as.list(setNames(inst2$Version, inst2$Package))

still_missing <- character(0)
for (name in names(pkgs)) {
  want <- pkgs[[name]]$Version
  have <- have2[[name]]
  if (is.null(have)) {
    still_missing <- c(still_missing, name)
  } else if (!is.null(want) && have != want) {
    still_missing <- c(still_missing, sprintf("%s(%s!=%s)", name, have, want))
  }
}

if (length(still_missing)) {
  die("post-install check failed for: ", paste(still_missing, collapse = ", "))
}

log("Bootstrap complete — all", length(pkgs), "packages match the lockfile.")
quit(status = 0L, save = "no")
