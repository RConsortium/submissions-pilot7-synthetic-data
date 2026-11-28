#!/bin/sh
# Rerun the PHMPT reproduction from the files FDA released on phmpt.org and
# compare your results with the ones published on the Pilot 7 site.
#
# Needs Python 3.12, git, a Rust toolchain (https://rustup.rs) to build
# yamaa, 15 GB of memory, a few GB of free disk and network access to
# PHMPT's storage. Only the zip members a spec reads are downloaded, and
# files fetched before are kept, so a rerun downloads only what is missing
# (python scripts/reproduce.py fetch --refresh downloads them again).
#
# In a clone of github.com/RConsortium/submissions-pilot7-synthetic-data:
#
#   sh phmpt/reproduce.sh setup      once: build yamaa at yamaa.lock and
#                                    install the kit into .local-run/venv
#   sh phmpt/reproduce.sh <study>    fetch, define, verify, then compare
#                                    with the published results
#   sh phmpt/reproduce.sh all        every study, one after another
#
# <study> is mrna-1273-p201, mrna-1273-p301, bnt162-01 or c4591001. The first
# and third take minutes; the other two take hours. The last step prints ok
# or FAIL for each dataset and define you ran; the script exits 1 if any
# result differs from the published one.
#
# JMP-only inputs. PHMPT released 40 inputs only as JMP tables (format jmp in
# data/sources.csv): files of every mRNA-1273-P301 cut and four C4591001
# files. fetch cannot read them, and a dataset that reads one fails until you
# supply your own conversion:
#   1. python scripts/reproduce.py fetch --study <study> --cut <cut> --jmp
#      saves each original next to where its conversion belongs.
#   2. Convert each to Parquet at its path in data/sources.csv, with the
#      table's columns, values and types (sources.csv gives the counts).
#   3. python scripts/cut_jmp_strings.py cuts every text value at its first
#      NUL byte. What follows a NUL can be text FDA redacted: never publish it.
#
# Keep PHMPT data local. .gitignore keeps the fetched data and .local-run/
# out of git. Never commit them, and never paste rows, subject identifiers or
# program text from them into an issue or a review.
#
# To rerun one dataset or one define, run the commands the review page gives
# for its finding in phmpt/, after . .local-run/venv/bin/activate (see also
# python scripts/reproduce.py --help).

set -eu
export PIP_DISABLE_PIP_VERSION_CHECK=1
self=$(basename "$0")
cd "$(dirname "$0")"
kit=$(pwd)
venv=.local-run/venv
py=$venv/bin/python

usage() {
    sed -n '2,/^$/s/^# \{0,1\}//p' "$kit/$self"
    exit "$1"
}

setup() {
    command -v cargo >/dev/null || { echo "setup needs a Rust toolchain: https://rustup.rs" >&2; exit 1; }
    commit=$(awk '/^commit:/{print $2}' yamaa.lock)
    [ -d .local-run/yamaa ] || git clone https://github.com/elong0527/yamaa .local-run/yamaa
    git -C .local-run/yamaa fetch -q origin
    git -C .local-run/yamaa checkout -q "$commit"
    "${PYTHON:-python3.12}" -m venv "$venv"
    "$py" -m pip install -q maturin==1.9.6
    rm -rf .local-run/yamaa/python/wheels
    (cd .local-run/yamaa/python && "$kit/$venv/bin/maturin" build --release -i "$kit/$py" -o wheels)
    "$py" -m pip install -q .local-run/yamaa/python/wheels/*.whl
    # zipfile-deflate64 0.2.0 does not compile with current Apple clang without this flag.
    [ "$(uname)" != Darwin ] || CFLAGS="-Dfdopen=fdopen" "$py" -m pip install -q zipfile-deflate64
    "$py" -m pip install -q -r requirements.txt
    "$py" -c "import yamaa" && echo "setup done: yamaa $commit in $venv"
}

# Run one step of a study; on failure, say which and go on with the next.
step() {
    name=$1
    shift
    "$@" || { echo "reproduce.sh: $name failed for $s (see above)" >&2; status=1; }
}

study() {
    s=$1
    status=0
    # The cuts with specs; a cut that reads another cut's files reads one of these.
    cuts=$("$py" -c 'import sys, yaml; print(*yaml.safe_load(open("studies.yaml"))[sys.argv[1]]["cuts"])' "$s" \
        2>/dev/null) || { echo "reproduce.sh: no study $s in studies.yaml" >&2; return 1; }
    for c in $cuts; do
        "$py" scripts/reproduce.py fetch --study "$s" --cut "$c" ||
            { echo "reproduce.sh: fetch failed for $s $c; rerun to retry" >&2; return 1; }
    done
    [ "$s" != c4591001 ] || step convert_lists "$py" scripts/convert_lists.py
    "$py" - "$s" <<'EOF'
import csv, os, sys
miss = [r["path"] for r in csv.DictReader(open("data/sources.csv", newline=""))
        if r["study"] == sys.argv[1] and r["format"] == "jmp" and not os.path.exists(r["path"])]
if miss:
    print(f"note: {len(miss)} JMP-only inputs have no conversion; the datasets that read them will fail "
          "(see JMP-only inputs at the top of phmpt/reproduce.sh):", *miss, sep="\n  ")
EOF
    step define "$py" scripts/reproduce.py define --study "$s" --transcribe
    step verify "$py" scripts/reproduce.py verify --study "$s"
    step "the comparison with the published results" \
        "$py" scripts/site/check_verdicts.py --evidence ../docs/phmpt/evidence.json --study "$s"
    return $status
}

[ $# -eq 1 ] || usage 2
case $1 in
    -h|--help) usage 0 ;;
    setup) setup; exit ;;
esac
[ -x "$py" ] || { echo "run 'sh phmpt/reproduce.sh setup' first" >&2; exit 1; }
if [ "$1" = all ]; then
    # shellcheck disable=SC2046  # one argument per study name
    set -- $("$py" -c 'import yaml; print(*yaml.safe_load(open("studies.yaml")))')
fi
rc=0
for s in "$@"; do
    study "$s" || rc=1
done
exit $rc
