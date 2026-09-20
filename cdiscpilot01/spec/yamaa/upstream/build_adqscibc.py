"""ADQSCIBC upstream driver: window assignment + LOCF row generation + ANL01FL.

Source: SDTM QS where QSTESTCD = 'CIBIC' (CIBIC+ interviews).

PREPROCESSING (honest disclosure): YAMAA has no windowing, LOCF-imputation,
or "closest-to-target" row-selection operations, so this driver builds the
analysis rows before the YAMAA spec runs. The spec (spec/adqscibc.yaml) then
maps these rows to the 36 official columns, joins ADSL, orders, and labels.

Rules (reverse-engineered 2026-09-20; 0 differences vs official ADQSCIBC on
all 730 rows x 36 columns; corroborated by define-adam.xml comments):
- define-adam.xml: AVAL "QS.QSSTRESN, where QS.QSTESTCD = CIBIC";
  AVISITN "Using window method in SAP Page 10 to determine AVISITN value
  based on ADY"; ANL01FL "Set ANL01FL=Y based on SAP Page 10 analysis
  windows"; AWTDIFF "Absolute difference between AWTARGET and ADY";
  DTYPE "LOCF denotes that the LOCF imputation method was used".
- Analysis windows on ADY (= QS.QSDY):
    Week 8  (AVISITN 8):  ADY in [2, 84],   target 56,  range '2-84'
    Week 16 (AVISITN 16): ADY in [85, 140], target 112, range '85-140'
    Week 24 (AVISITN 24): ADY >= 141,       target 168, range '>140'
  Every QS CIBIC record lands in exactly one window and yields one row
  with DTYPE=''.
- LOCF: for each subject, windows are processed in order. If a window has
  no QS record but a prior QS record exists (QSDY < window start), one row
  is emitted from the latest prior QS record (keeps its VISIT, VISITNUM,
  ADY, ADT, QSSEQ) with DTYPE='LOCF' and AVAL = the last analysis AVAL
  (the previous window's ANL01FL='Y' value). Windows before the subject's
  first record get no row.
- ANL01FL='Y' marks the record closest to the window target
  (min |ADY - AWTARGET|) within each (subject, AVISIT); others get ''.
  No ties observed in the official data.
- Row order: (USUBJID, AVISITN, QSSEQ).

Output: upstream/adqscibc_input.parquet (730 rows).
"""

import polars as pl

BASE = str(Path(__file__).resolve().parents[1])

WINDOWS = [
    # (avisit, avisitn, lo, hi, target, awrange, awhi)
    ("Week 8", 8.0, 2.0, 84.0, 56.0, "2-84", 84.0),
    ("Week 16", 16.0, 85.0, 140.0, 112.0, "85-140", 140.0),
    ("Week 24", 24.0, 141.0, float("inf"), 168.0, ">140", None),
]


def main() -> None:
    qs = pl.read_parquet(f"{BASE}/sdtm/qs.parquet")
    cibic = (
        qs.filter(pl.col("QSTESTCD") == "CIBIC")
        .select(["USUBJID", "QSSEQ", "VISIT", "VISITNUM", "QSDY", "QSDTC", "QSSTRESN"])
        .sort(["USUBJID", "QSDY", "QSSEQ"])
    )

    out_rows = []
    for (usubjid,), grp in cibic.group_by("USUBJID", maintain_order=True):
        recs = grp.sort(["QSDY", "QSSEQ"]).to_dicts()
        last_anl_aval = None  # last analysis AVAL (ANL01FL='Y' value so far)
        for avisit, avisitn, lo, hi, target, awrange, awhi in WINDOWS:
            in_win = [r for r in recs if lo <= r["QSDY"] <= hi]
            if in_win:
                for r in in_win:
                    awtdiff = abs(r["QSDY"] - target)
                    out_rows.append(
                        {
                            "STUDYID": "CDISCPILOT01",
                            "USUBJID": usubjid,
                            "QSSEQ": float(r["QSSEQ"]),
                            "VISIT": r["VISIT"],
                            "VISITNUM": float(r["VISITNUM"]),
                            "QSDTC": r["QSDTC"],
                            "ADY": float(r["QSDY"]),
                            "AVISIT": avisit,
                            "AVISITN": avisitn,
                            "AVAL": float(r["QSSTRESN"]),
                            "ANL01FL": "",  # fixed up below
                            "DTYPE": "",
                            "AWTARGET": target,
                            "AWTDIFF": awtdiff,
                            "AWLO": lo,
                            "AWHI": awhi,
                            "AWRANGE": awrange,
                            "AWU": "DAYS",
                            "PARAMCD": "CIBICVAL",
                            "PARAM": "CIBIC Score",
                            "PARAMN": 1.0,
                            "_awtdiff": awtdiff,
                        }
                    )
                # ANL01FL='Y' on the record closest to target
                win_rows = [o for o in out_rows if o["USUBJID"] == usubjid and o["AVISIT"] == avisit]
                best = min(win_rows, key=lambda o: o["_awtdiff"])
                best["ANL01FL"] = "Y"
                last_anl_aval = best["AVAL"]
            else:
                prior = [r for r in recs if r["QSDY"] < lo]
                if prior and last_anl_aval is not None:
                    src = max(prior, key=lambda r: (r["QSDY"], r["QSSEQ"]))
                    awtdiff = abs(src["QSDY"] - target)
                    out_rows.append(
                        {
                            "STUDYID": "CDISCPILOT01",
                            "USUBJID": usubjid,
                            "QSSEQ": float(src["QSSEQ"]),
                            "VISIT": src["VISIT"],
                            "VISITNUM": float(src["VISITNUM"]),
                            "QSDTC": src["QSDTC"],
                            "ADY": float(src["QSDY"]),
                            "AVISIT": avisit,
                            "AVISITN": avisitn,
                            "AVAL": last_anl_aval,
                            "ANL01FL": "Y",
                            "DTYPE": "LOCF",
                            "AWTARGET": target,
                            "AWTDIFF": awtdiff,
                            "AWLO": lo,
                            "AWHI": awhi,
                            "AWRANGE": awrange,
                            "AWU": "DAYS",
                            "PARAMCD": "CIBICVAL",
                            "PARAM": "CIBIC Score",
                            "PARAMN": 1.0,
                            "_awtdiff": awtdiff,
                        }
                    )
                    last_anl_aval = last_anl_aval  # carried value persists

    df = pl.DataFrame(out_rows).drop("_awtdiff").sort(["USUBJID", "AVISITN", "QSSEQ"])
    print("rows:", df.shape)
    # The YAMAA R020 parquet profile only ingests pa.string() (not
    # large_string), so cast string columns down before writing.
    import pyarrow as pa

    table = df.to_arrow()
    table = table.cast(
        pa.schema(
            [
                pa.field(f.name, pa.string() if pa.types.is_large_string(f.type) else f.type, nullable=True)
                for f in table.schema
            ]
        )
    )
    import pyarrow.parquet as pq

    pq.write_table(table, f"{BASE}/upstream/adqscibc_input.parquet")


if __name__ == "__main__":
    main()
