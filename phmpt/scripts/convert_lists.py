#!/usr/bin/env python3
"""Convert the C4591001 S1 Appendix V spreadsheets the specs read into Parquet.

The S1 ADSL and ADMH programs read lists the sponsor kept as .xlsx files
(Module 5, S1 Appendix V). They are not SAS transport files, so `fetch` does
not cover them; this script reads them from the same PHMPT Full Productions
zip with HTTP range requests (or from --source-dir) and writes
c4591001/data/lists/.

The conversion copies cells and derives nothing: what the sponsor's programs
compute from a list (the Charlson categories of a code, the upper bound of a
BMI band) is derived in the spec that reads it.

    PHASE1_LIST      SUBJID   column A of the Phase 1 subject list
    DS360_LIST       SUBJID   column B of the first-360 list, sheet SubjID_360
    DS6000_LIST      SUBJID   the subject number (last word) of column A of
                              the 6k list, whose cells read "C4591001 SITE SUBJID"
    IMMUNO1225_LIST  USUBJID  column A of the 12-25 immunogenicity list
    HIV_TERMS        TERM     column B of the HIV preferred-term list
    BMI_SCALE        A, B, C  the 12-15 BMI scale as it stands: sex, age in
                              months, 95th-percentile BMI
    CCI_REPORTS      FILE, ROW, TERM, CODE, LEVEL
                              every term row of the 19 report-cci-*.xlsx
                              files (MedDRA PT lists, one per Charlson
                              category), below their Term/Code header row

Every list but CCI_REPORTS is a set of distinct values in sorted order, as
the earlier conversion wrote it.

    python scripts/convert_lists.py                  # from PHMPT
    python scripts/convert_lists.py --source-dir DIR # from local .xlsx files

Needs openpyxl and zipfile-deflate64.
"""
from __future__ import annotations

import argparse
import io
import sys
import warnings
import zipfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "site"))

ZIP = "https://pdata0916.s3.us-east-2.amazonaws.com/pdocs/multiple/pd-production-030122.zip"
PREFIX = "125742_S1_M5_c4591001-A-"
OUT = ROOT / "c4591001" / "data" / "lists"

PHASE1 = "c4591001-phase-1-subjects-from-dmw.xlsx"
DS360 = "first-c4591001-360-participants-enrolled-v1-13aug20-update.xlsx"
DS6000 = "newlist-c4591001-6k-participants-enrolled-v3-17sep2020.xlsx"
IMMUNO = "c4591001-subject-list-for-12-25-immuno-analysis-27jan2021.xlsx"
HIV = "201114-hiv-preferred-terms.xlsx"
BMI = "bmi-12-15-scale.xlsx"
CCI = "report-cci-"


def members(source_dir: Path | None) -> dict[str, bytes]:
    """The S1 Appendix V .xlsx files, by their name after the Bates prefix."""
    out = {}
    if source_dir:
        for p in source_dir.glob(f"*{PREFIX}*.xlsx"):
            out[p.name.split(PREFIX, 1)[1]] = p.read_bytes()
        return out
    import zipfile_deflate64  # noqa: F401  registers Deflate64 with zipfile
    from httpzip import HTTPRangeFile

    z = zipfile.ZipFile(io.BufferedReader(HTTPRangeFile(ZIP), buffer_size=1 << 20))
    for i in z.infolist():
        name = i.filename.rsplit("/", 1)[-1]
        if name.endswith(".xlsx") and PREFIX in name:
            out[name.split(PREFIX, 1)[1]] = z.read(i)
    return out


def rows(data: bytes, sheet: str | int = 0) -> list[tuple]:
    import openpyxl

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # "Workbook contains no default style"
        wb = openpyxl.load_workbook(io.BytesIO(data))
    ws = wb[sheet] if isinstance(sheet, str) else wb.worksheets[sheet]
    return list(ws.iter_rows(values_only=True))


def text(v) -> str:
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


def column(data: bytes, col: int, sheet: str | int = 0, last_word: bool = False) -> list[str]:
    """Distinct non-empty values of one column below the header row, sorted."""
    vals = {text(r[col]) for r in rows(data, sheet)[1:] if r[col] not in (None, "")}
    return sorted(v.split()[-1] if last_word else v for v in vals)


def write(name: str, table: pa.Table, out: Path) -> None:
    pq.write_table(table, out / f"{name}.parquet")
    print(f"{name}: {table.num_rows:,} rows")


def cci_reports(files: dict[str, bytes]) -> pa.Table:
    names = sorted(n for n in files if n.startswith(CCI))
    if len(names) != 19:
        raise SystemExit(f"expected 19 report-cci files, found {len(names)}")
    cols = {"FILE": [], "ROW": [], "TERM": [], "CODE": [], "LEVEL": []}
    for name in names:
        sheet = rows(files[name])
        head = next(i for i, r in enumerate(sheet) if r[:2] == ("Term", "Code"))
        for i, r in enumerate(sheet[head + 1:], start=head + 2):
            if r[0] in (None, "") and r[1] in (None, ""):
                continue
            cols["FILE"].append(name)
            cols["ROW"].append(i)
            cols["TERM"].append(r[0])
            cols["CODE"].append(text(r[1]))
            cols["LEVEL"].append(r[2])
    return pa.table({k: pa.array(v, pa.int64() if k == "ROW" else pa.large_string()) for k, v in cols.items()})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source-dir", type=Path, help="local folder of the S1 Appendix V .xlsx files")
    ap.add_argument("--out-dir", type=Path, default=OUT, help=f"default: {OUT.relative_to(ROOT)}")
    args = ap.parse_args()
    files = members(args.source_dir)
    missing = [n for n in (PHASE1, DS360, DS6000, IMMUNO, HIV, BMI) if n not in files]
    if missing:
        raise SystemExit(f"not found: {missing}")
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    one = lambda name, vals: pa.table({name: pa.array(vals, pa.large_string())})  # noqa: E731
    write("PHASE1_LIST", one("SUBJID", column(files[PHASE1], 0)), out)
    write("DS360_LIST", one("SUBJID", column(files[DS360], 1, sheet="SubjID_360")), out)
    write("DS6000_LIST", one("SUBJID", column(files[DS6000], 0, last_word=True)), out)
    write("IMMUNO1225_LIST", one("USUBJID", column(files[IMMUNO], 0)), out)
    write("HIV_TERMS", one("TERM", column(files[HIV], 1)), out)
    bmi = [r[:3] for r in rows(files[BMI])[1:] if r[0] not in (None, "")]
    write("BMI_SCALE", pa.table({"A": pa.array([r[0] for r in bmi], pa.large_string()),
                                 "B": pa.array([float(r[1]) for r in bmi], pa.float64()),
                                 "C": pa.array([float(r[2]) for r in bmi], pa.float64())}), out)
    write("CCI_REPORTS", cci_reports(files), out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
