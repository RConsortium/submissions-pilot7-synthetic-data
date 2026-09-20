"""Honest preprocessing driver for ADQSADAS.

YAMAA has no native support for: analysis-window assignment, closest-to-target
record selection within a window, ACTOT within-window LOCF, or empty-window
LOCF row generation. This driver therefore builds the 12,463-row analysis
frame directly from SDTM QS, documenting every rule below. The YAMAA spec
(adqsadas.yaml) then declares each column (mostly passthrough) and merges the
ADSL covariates via a declared intermediate lookup.

Rules (reverse-engineered from the official ADaM parquet; define-adam.xml
carries no derivation text for ADQSADAS):
  Source: QS where QSTESTCD in (ACITM01..ACITM14, ACTOT); every ADaM row joins
  to exactly one QS record on (USUBJID, QSSEQ); PARAMCD == QSTESTCD.
  Windows on ADY (= QSDY): Baseline ADY<=1 (target 1); Week 8 2-84 (target 56);
  Week 16 85-140 (target 112); Week 24 >=141 (target 168).
  Per (subject, param, window) the record closest to the window target gets
  ANL01FL='Y' (ties broken by lowest QSSEQ; no ties observed in the data).
  Items (ACITM01-14): one row per record in its natural window; AVAL = own
  QSSTRESN; DTYPE = '' always; no LOCF rows are generated for items.
  ACTOT: records are processed in (ADY, QSSEQ) order per subject, carrying the
  last selected record's QSSTRESN forward. A selected record's row takes its
  own QSSTRESN (ANL01FL='Y', DTYPE=''); any other record's row takes the
  carried value (ANL01FL=''), with DTYPE='LOCF' iff that carried value differs
  from the record's own QSSTRESN (null-safe). Empty windows at/after the
  subject's first record (every subject has a Baseline record) get one LOCF
  row carrying the latest prior record's VISIT/VISITNUM/ADY/ADT/QSSEQ, with
  AVAL = the carried value, DTYPE='LOCF', ANL01FL='Y'.
  ABLFL='Y' iff QSBLFL='Y' and the row is in the Baseline window.
  BASE = AVAL of the (subject, param) ABLFL='Y' row (null when absent/null).
  CHG = null on Baseline rows, else AVAL - BASE (null if either is null).
  PCHG = null on Baseline rows or when CHG/BASE is null or BASE = 0,
  else CHG / BASE * 100 (exact float arithmetic, no rounding).
  ADT = date part of QSDTC. AWTDIFF = |AWTARGET - ADY|.
Row order: (USUBJID, PARAMN, AVISITN, QSSEQ).
"""

import polars as pl

BASE = str(Path(__file__).resolve().parents[1])

TESTS = [f"ACITM{i:02d}" for i in range(1, 15)] + ["ACTOT"]

PARAM = {
    "ACITM01": ("Word Recall Task", 1.0),
    "ACITM02": ("Naming Objects And Fingers (Refer To 5 C", 2.0),
    "ACITM03": ("Delayed Word Recall", 3.0),
    "ACITM04": ("Commands", 4.0),
    "ACITM05": ("Constructional Praxis", 5.0),
    "ACITM06": ("Ideational Praxis", 6.0),
    "ACITM07": ("Orientation", 7.0),
    "ACITM08": ("Word Recognition", 8.0),
    "ACITM09": ("Attention/Visual Search Task", 9.0),
    "ACITM10": ("Maze Solution", 10.0),
    "ACITM11": ("Spoken Language Ability", 11.0),
    "ACITM12": ("Comprehension Of Spoken Language", 12.0),
    "ACITM13": ("Word Finding Difficulty In Spontaneous S", 13.0),
    "ACITM14": ("Recall Of Test Instructions", 14.0),
    "ACTOT": ("Adas-Cog(11) Subscore", 15.0),
}

# (AVISIT, AVISITN, target, lo, hi, AWRANGE)
WINDOWS = [
    ("Baseline", 0.0, 1.0, None, 1.0, "<=1"),
    ("Week 8", 8.0, 56.0, 2.0, 84.0, "2-84"),
    ("Week 16", 16.0, 112.0, 85.0, 140.0, "85-140"),
    ("Week 24", 24.0, 168.0, 141.0, None, ">140"),
]


def assign_window(ady: float) -> int:
    if ady <= 1:
        return 0
    if ady <= 84:
        return 1
    if ady <= 140:
        return 2
    return 3


def _eq(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return a == b


def main() -> None:
    qs = pl.read_parquet(f"{BASE}/sdtm/qs.parquet").filter(
        pl.col("QSTESTCD").is_in(TESTS)
    )
    rows: list[dict] = []
    for (subj,), g in qs.group_by("USUBJID", maintain_order=False):
        recs = g.sort(["QSDY", "QSSEQ"]).to_dicts()
        studyid = recs[0]["STUDYID"]
        # per (param, window): selected record = closest to target
        sel: dict[tuple[str, int], dict] = {}
        sel_key: dict[tuple[str, int], tuple[float, float]] = {}
        for r in recs:
            w = assign_window(r["QSDY"])
            key = (r["QSTESTCD"], w)
            tgt = WINDOWS[w][2]
            cand = (abs(r["QSDY"] - tgt), r["QSSEQ"])
            if key not in sel or cand < sel_key[key]:
                sel[key] = r
                sel_key[key] = cand

        def base_row(r: dict, w: int, aval, anl: str, dtype: str) -> dict:
            avisit, avisitn, target, lo, hi, awrange = WINDOWS[w]
            abl = "Y" if (r["QSBLFL"] == "Y" and w == 0) else ""
            return {
                "STUDYID": studyid,
                "USUBJID": subj,
                "PARAMCD": r["QSTESTCD"],
                "PARAM": PARAM[r["QSTESTCD"]][0],
                "PARAMN": PARAM[r["QSTESTCD"]][1],
                "AVISIT": avisit,
                "AVISITN": avisitn,
                "VISIT": r["VISIT"],
                "VISITNUM": r["VISITNUM"],
                "ADY": r["QSDY"],
                "ADT": r["QSDTC"][:10],
                "QSSEQ": r["QSSEQ"],
                "AVAL": aval,
                "ABLFL": abl,
                "ANL01FL": anl,
                "DTYPE": dtype,
                "AWRANGE": awrange,
                "AWTARGET": target,
                "AWTDIFF": abs(target - r["QSDY"]),
                "AWLO": lo,
                "AWHI": hi,
                "AWU": "DAYS",
            }

        # items: one natural row per record
        for r in recs:
            if r["QSTESTCD"] == "ACTOT":
                continue
            w = assign_window(r["QSDY"])
            s = sel[(r["QSTESTCD"], w)]
            rows.append(base_row(r, w, r["QSSTRESN"],
                                 "Y" if r["QSSEQ"] == s["QSSEQ"] else "", ""))

        # ACTOT: natural rows + empty-window LOCF, with forward-filled analysis
        # value. Records are processed in (ADY, QSSEQ) order; `carried` holds
        # the last selected record's QSSTRESN. A selected record takes its own
        # value; any other record takes the carried value (LOCF). Empty
        # windows (at/after the subject's first record) emit one LOCF row from
        # the latest prior record with the carried value.
        arecs = [r for r in recs if r["QSTESTCD"] == "ACTOT"]
        carried = None
        last_rec = None
        for w in range(4):
            wrecs = sorted(
                (r for r in arecs if assign_window(r["QSDY"]) == w),
                key=lambda r: (r["QSDY"], r["QSSEQ"]),
            )
            if wrecs:
                s = sel[("ACTOT", w)]
                for r in wrecs:
                    is_sel = r["QSSEQ"] == s["QSSEQ"]
                    if is_sel:
                        aval = r["QSSTRESN"]
                        carried = aval
                        dtype = ""
                    else:
                        aval = carried
                        dtype = "LOCF" if not _eq(aval, r["QSSTRESN"]) else ""
                    rows.append(base_row(r, w, aval, "Y" if is_sel else "", dtype))
                last_rec = max(wrecs, key=lambda r: (r["QSDY"], r["QSSEQ"]))
            else:
                assert last_rec is not None and carried is not None, (
                    f"empty leading window for {subj}"
                )
                rows.append(base_row(last_rec, w, carried, "Y", "LOCF"))

    df = pl.DataFrame(rows)
    # BASE / CHG / PCHG
    bl = df.filter(pl.col("ABLFL") == "Y").select(
        ["USUBJID", "PARAMCD", pl.col("AVAL").alias("BASE")]
    )
    df = df.join(bl, on=["USUBJID", "PARAMCD"], how="left")
    df = df.with_columns(
        pl.when(pl.col("AVISIT") == "Baseline")
        .then(None)
        .when(pl.col("AVAL").is_null() | pl.col("BASE").is_null())
        .then(None)
        .otherwise(pl.col("AVAL") - pl.col("BASE"))
        .alias("CHG")
    )
    df = df.with_columns(
        pl.when(pl.col("AVISIT") == "Baseline")
        .then(None)
        .when(
            pl.col("CHG").is_null() | pl.col("BASE").is_null() | (pl.col("BASE") == 0)
        )
        .then(None)
        .otherwise(pl.col("CHG") / pl.col("BASE") * 100)
        .alias("PCHG")
    )
    df = df.with_columns(pl.col("ADT").str.strptime(pl.Date, "%Y-%m-%d"))
    df = df.sort(["USUBJID", "PARAMN", "AVISITN", "QSSEQ"])
    out = f"{BASE}/upstream/adqsadas_input.parquet"
    # YAMAA's input profile rejects large_string: write text as pa.string().
    import pyarrow as pa

    table = df.to_arrow()
    fields = [
        pa.field(f.name, pa.string(), nullable=True)
        if pa.types.is_large_string(f.type)
        else f
        for f in table.schema
    ]
    table = table.cast(pa.schema(fields))
    import pyarrow.parquet as pq

    pq.write_table(table, out)
    print(f"wrote {out}: {df.shape[0]} rows x {df.shape[1]} cols")


if __name__ == "__main__":
    main()
