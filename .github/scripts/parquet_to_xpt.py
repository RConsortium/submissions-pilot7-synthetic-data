#!/usr/bin/env python3
"""Convert a directory of .parquet datasets to SAS Transport (XPT v5).

CORE (cdisc-rules-engine v0.16.0) cannot read parquet -- its
`valid_data_file()` accepts only XPT / Dataset-JSON / NDJSON / XLSX / CSV.
The studies in this repo store parquet, so this step materialises XPT that
CORE can validate. XPT **v5** is chosen deliberately: it is the SAS
Transport flavour CORE reads, and its 8-character name limit is satisfied
by conformant SDTM/ADaM variable names.

Reads with pyarrow (already a repo dependency, see compare_adam.py) and
writes with pyreadstat. Conversion is best-effort and per-file: a dataset
that cannot be written (e.g. a variable name longer than 8 chars) is logged
and skipped, so one bad table never blocks the rest of a domain.

Usage:  python3 .github/scripts/parquet_to_xpt.py --in <src_dir> --out <dst_dir>
Exit code is always 0 (skips are warnings); prints a per-file summary.
"""

from __future__ import annotations

import argparse
import glob
import os
import sys

import pyarrow.parquet as pq
import pyreadstat


def convert_one(src: str, dst_dir: str) -> tuple[bool, str]:
    """Convert one parquet file to <domain>.xpt. Returns (ok, message)."""
    stem = os.path.splitext(os.path.basename(src))[0]
    # SAS dataset (member) name: XPT v5 caps it at 8 chars; CORE keys the
    # domain off the file/member name, so keep the parquet stem.
    table_name = stem.upper()[:8]
    dst = os.path.join(dst_dir, f"{stem}.xpt")
    try:
        df = pq.read_table(src).to_pandas()
        pyreadstat.write_xport(
            df, dst, file_format_version=5, table_name=table_name
        )
        return True, f"{os.path.basename(src)} -> {os.path.basename(dst)} ({len(df)} rows)"
    except Exception as exc:  # noqa: BLE001 - best-effort, report and move on
        # Leave no partial file behind for CORE to trip over.
        if os.path.exists(dst):
            os.remove(dst)
        return False, f"{os.path.basename(src)}: SKIPPED ({type(exc).__name__}: {exc})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="src", required=True, help="source dir of .parquet")
    parser.add_argument("--out", dest="dst", required=True, help="dest dir for .xpt")
    args = parser.parse_args()

    os.makedirs(args.dst, exist_ok=True)
    sources = sorted(glob.glob(os.path.join(args.src, "*.parquet")))
    if not sources:
        print(f"No .parquet files in {args.src} -- nothing to convert.")
        return 0

    ok = 0
    for src in sources:
        success, msg = convert_one(src, args.dst)
        prefix = "  OK  " if success else "  !!  "
        print(prefix + msg)
        if success:
            ok += 1
        elif os.environ.get("GITHUB_ACTIONS") == "true":
            print(f"::warning::parquet_to_xpt: {msg}")

    print(f"\nConverted {ok}/{len(sources)} datasets to XPT in {args.dst}")
    # Zero successes out of a non-empty input is a systemic failure (a missing
    # dependency, an unreadable format) -- fail loudly rather than let the
    # caller carry on and silently produce no reports. Partial failures still
    # succeed: one bad table must not block a whole domain.
    if ok == 0:
        print(
            "::error::parquet_to_xpt: converted 0 datasets -- treating as a "
            "systemic failure (check pandas/pyarrow/pyreadstat install)."
            if os.environ.get("GITHUB_ACTIONS") == "true"
            else "ERROR: converted 0 datasets -- systemic failure.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
