#!/usr/bin/env bash
# Usage: dvc-compare.sh [--rev <rev>] [--vde-path <path/to/vde>] [--text] <path/to/file>
set -euo pipefail

# Defaults
vde_path="vde-dataset-viewer"
r_path="Rscript"
text_mode=0
rev=HEAD

usage() {
  echo "Usage: $0 [--rev <rev>] [--vde-path <path/to/vde>] [--text] <path/to/file>" >&2
  echo "  --rev <rev>           Git revision to compare against (default: HEAD)" >&2
  echo "  --vde-path <path>     Path to vde-dataset-viewer executable (default: vde-dataset-viewer in PATH)" >&2
  echo "  --r-path <path>       Path to Rscript executable (default: Rscript in PATH)" >&2
  echo "  --text, -t            Use text-based comparison mode" >&2
  echo "  --visual, -v          Use visual comparison mode (default)" >&2
  echo "  --help, -h            Show this help message and exit" >&2
}

# Parse parameters (supports both `--opt value` and `--opt=value` forms)
while [ $# -gt 0 ]; do
  case "$1" in
    --rev)
      shift
      if [ $# -eq 0 ]; then
        usage
        exit 2
      fi
      rev="$1"
      shift
      ;;
    --rev=*)
      rev="${1#*=}"
      shift
      ;;
    --vde-path)
      shift
      if [ $# -eq 0 ]; then
        usage
        exit 2
      fi
      vde_path="$1"
      shift
      ;;
    --vde-path=*)
      vde_path="${1#*=}"
      shift
      ;;
    --r-path)
      shift
      if [ $# -eq 0 ]; then
        usage
        exit 2
      fi
      r_path="$1"
      shift
      ;;
    --r-path=*)
      r_path="${1#*=}"
      shift
      ;;
    --text|-t)
      text_mode=1
      shift
      ;;
    --visual|-v)
      text_mode=0
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --*)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
    *)
      file="$1"
      shift
      ;;
  esac
done

if [ -z "${file:-}" ]; then
  usage
  exit 2
fi

if [ ! -f "${file}.dvc" ]; then
  echo "not in dvc: $file" >&2
  exit 1
fi

dir=$(dirname -- "$file")
base=$(basename -- "$file")
tmp="$dir/~compare.$base"

# Set up cleanup function to remove temporary file on exit

cleanup() {
  if [ -f "$tmp" ]; then
    rm -f -- "$tmp"
  fi
}

trap cleanup EXIT HUP INT TERM

# Determine git root and path relative to it
git_root=$(git rev-parse --show-toplevel)
file_abs=$(realpath -- "$file")
file_relative_path="${file_abs#$git_root/}"

# Use `dvc status --json` to check for modifications
status_json=$(dvc status "$file_abs" --json 2>&1) || {
  echo "dvc status failed for $file_relative_path: $status_json" >&2
  exit 3
}

# Check JSON respose, empty object means there are no changes (possible need to check if the file is modified instead).
if [ "$status_json" = '{}' ]; then
  echo "File not modified relative to committed DVC version: $file"
  # If no revision specified, we exit
  if [ "$rev" = "HEAD" ]; then
    exit 0
  fi
else
  echo "Workspace file modified; fetching committed DVC version to: $tmp"
fi


if ! dvc get . "$file_relative_path" -o "$tmp" --rev "$rev" >/dev/null 2>&1; then
  echo "Failed to retrieve committed DVC version for $file (rev=$rev)" >&2
  exit 5
fi

if [ "${text_mode:-0}" = "1" ]; then
  if ! command -v "$r_path" >/dev/null 2>&1; then
    echo "Rscript not found in PATH" >&2
    exit 6
  fi
  echo "Running Rscript ./compare_data.r \"$file\" \"$tmp\""
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  "$r_path" "$script_dir/compare_data.r" "$file" "$tmp"
else
  echo "Launching $vde_path --compare $file $tmp"
  "$vde_path" --compare "$file" "$tmp" >/dev/null 2>&1
fi

# cleanup will be run by trap on exit
exit 0
