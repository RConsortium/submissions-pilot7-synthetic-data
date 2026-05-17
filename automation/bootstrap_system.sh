#!/usr/bin/env bash
## --------------------------------------------------------------------
## bootstrap_system.sh — make sure Rscript is available before
## automation/bootstrap_r.R runs.
##
## Idempotent: exits 0 immediately when Rscript is already on PATH
## (does NOT try to "fix" or upgrade an existing R install — that is a
## container-image concern, not a per-run concern).
##
## On a fresh Debian/Ubuntu container with no R, installs R 4.x from
## the CRAN apt repository (cran40), so that the installed R matches
## cart-t/renv.lock's R$Version (currently 4.6.0). Also installs
## r-base-dev and the system libraries {renv} needs to compile packages
## from source.
##
## Usage:   bash automation/bootstrap_system.sh
## Exits:   0 = Rscript is present (already or after install).
##          non-zero = could not install (no apt, no root, unknown OS,
##                     CRAN repo unreachable, or apt failed).
## --------------------------------------------------------------------

set -euo pipefail

log() { printf '[bootstrap_system] %s\n' "$*"; }
die() { printf '[bootstrap_system] FATAL: %s\n' "$*" >&2; exit 1; }

if command -v Rscript >/dev/null 2>&1; then
  log "Rscript already present at: $(command -v Rscript)"
  log "$(Rscript --version 2>&1 | head -1)"
  log "Skipping install. (If you need a different R version, rebuild the container image — this script does not upgrade in place.)"
  exit 0
fi

log "Rscript not found — installing R 4.x from the CRAN apt repository."

if ! command -v apt-get >/dev/null 2>&1; then
  die "apt-get not found. This bootstrap only handles Debian/Ubuntu containers. Bake R into the routine's container image (e.g. rocker/r-ver:4.6.0) instead."
fi

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    die "Not running as root and sudo is unavailable. Bake R into the routine's container image, or run this script as root."
  fi
fi

if [ ! -r /etc/os-release ]; then
  die "/etc/os-release not readable — cannot detect distribution."
fi
# shellcheck disable=SC1091
. /etc/os-release
: "${ID:?cannot detect distribution ID from /etc/os-release}"
: "${VERSION_CODENAME:?cannot detect distribution codename from /etc/os-release}"

case "$ID" in
  ubuntu) CRAN_PATH="ubuntu" ;;
  debian) CRAN_PATH="debian" ;;
  *)      die "Unsupported distribution: $ID (this bootstrap handles ubuntu and debian)" ;;
esac

CRAN_URL="https://cloud.r-project.org/bin/linux/${CRAN_PATH}"
CRAN_DIST="${VERSION_CODENAME}-cran40"

export DEBIAN_FRONTEND=noninteractive

log "Installing prerequisites (curl, gnupg, ca-certificates)…"
$SUDO apt-get update -qq
$SUDO apt-get install -y --no-install-recommends \
  curl gnupg ca-certificates

log "Adding the CRAN signing key to /usr/share/keyrings…"
curl -fsSL "${CRAN_URL}/marutter_pubkey.asc" \
  | $SUDO gpg --dearmor --yes -o /usr/share/keyrings/cran-archive-keyring.gpg

log "Adding CRAN apt source: deb ${CRAN_URL} ${CRAN_DIST}/"
echo "deb [signed-by=/usr/share/keyrings/cran-archive-keyring.gpg] ${CRAN_URL} ${CRAN_DIST}/" \
  | $SUDO tee /etc/apt/sources.list.d/cran-r.list >/dev/null

$SUDO apt-get update -qq

log "Installing r-base, r-base-dev, and the system libs {renv} needs to compile from source…"
$SUDO apt-get install -y --no-install-recommends \
  r-base r-base-dev \
  libxml2-dev \
  libcurl4-openssl-dev \
  libssl-dev \
  libgit2-dev \
  libuv1-dev

if ! command -v Rscript >/dev/null 2>&1; then
  die "apt install reported success but Rscript is still missing. Inspect /var/log/apt/term.log."
fi

INSTALLED_VER="$(Rscript -e 'cat(paste(R.version$major, R.version$minor, sep="."))' 2>/dev/null || true)"
log "Rscript installed: $(Rscript --version 2>&1 | head -1)"

# Warn (but don't fail) if the CRAN-shipped R doesn't match the lockfile's expectation.
# bootstrap_r.R will print its own warning; this one is just to surface it early.
if [ -r cart-t/renv.lock ] && command -v python3 >/dev/null 2>&1; then
  WANT_VER="$(python3 -c 'import json; print(json.load(open("cart-t/renv.lock"))["R"]["Version"])' 2>/dev/null || true)"
  if [ -n "${WANT_VER:-}" ] && [ -n "${INSTALLED_VER:-}" ] && [ "$WANT_VER" != "$INSTALLED_VER" ]; then
    log "WARNING: installed R is ${INSTALLED_VER}, but cart-t/renv.lock wants ${WANT_VER}. Minor mismatches are usually fine; bootstrap_r.R will warn and continue."
  fi
fi
