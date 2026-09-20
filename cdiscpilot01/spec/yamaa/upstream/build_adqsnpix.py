#!/usr/bin/env python3
"""Honest preprocessing driver for ADQSNPIX.

YAMAA has no native analysis-window or closest-to-target constructs, so this
driver computes the windowed NPI analysis rows exactly from SDTM QS, following
the official define-adam.xml comments and the observed official ADQSNPIX:

Source: QS where QSTESTCD in NPITM01S..NPITM12S, NPTOT.

Windows (from official AWRANGE/AWTARGET):
  Baseline: ADY <= 1, target 1, AVISITN 0
  Week 2: ADY in [2, 21], target 14, AVISITN 2
  Week N (4,6,...,24): ADY in [7N-6, 7N+7], target 7N, AVISITN N
  Week 26: ADY >= 176, target 182, AVISITN 26.
  AVISIT is the label right-justified to width 16.

Per (USUBJID, PARAMCD, AVISIT) the record closest to the window target gets
ANL01FL='Y'; ties (65 observed) break by earliest ADY then smallest QSSEQ.
ABLFL='Y' iff QSBLFL='Y'. BASE is the ABLFL row's AVAL per (USUBJID, PARAMCD).
CHG = AVAL - BASE (null iff an input is null; baseline rows get 0.0 when BASE
exists). PCHG = (AVAL - BASE) * 100 / BASE (null iff BASE is null/zero or CHG
null). AWTDIFF = |AWTARGET - ADY|.

NPTOTMN (PARAMTYP='DERIVED', DTYPE='AVERAGE'):
  - one Baseline row per subject duplicating the NPTOT baseline record
    (AVAL = NPTOT baseline AVAL);
  - one 'Weeks 4-24' row (AVISITN 98) per subject having >=1 ANL01FL='Y'
    NPTOT record at AVISITN 6/8/10/12, with AVAL = mean of those AVALs,
    BASE = NPTOT baseline AVAL, CHG/PCHG null (official).
    (define-adam.xml: "take the mean of AVAL when PARAMCD=NPTOT from
    week 4 to 24"; empirically the averaged records are exactly the
    ANL01FL='Y' NPTOT rows at AVISITN 6, 8, 10, 12 - verified 214/214).

Official row order: (USUBJID, PARAMN, AVISITN, ANL01FL desc, QSSEQ asc).
"""
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

BASE = str(Path(__file__).resolve().parents[1])

TESTS = [f"NPITM{i:02d}S" for i in range(1, 13)] + ["NPTOT"]

# Exact official PARAM strings (contain intentional double spaces/typos).
PARAMS = {
    "NPITM01S": (1.0, "NPI-X Item A (Delusion) Score"),
    "NPITM02S": (2.0, "NPI-X Item B (Hallucination)  Score"),
    "NPITM03S": (3.0, "NPI-X Item C (Agitation/Agression) Score"),
    "NPITM04S": (4.0, "NPI-X Item D (Depression/Dysphoria) Score"),
    "NPITM05S": (5.0, "NPI-X Item E (Anxiety) Score"),
    "NPITM06S": (6.0, "NPI-X Item F (Eupohoria/Elation) Score"),
    "NPITM07S": (7.0, "NPI-X Item G (Apathy/Indifference) Score"),
    "NPITM08S": (8.0, "NPI-X Item H (Disinhibition) Score"),
    "NPITM09S": (9.0, "NPI-X Item I (Irritability/Lability) Score"),
    "NPITM10S": (10.0, "NPI-X Item J (Aberrant Motor Behavior) Score"),
    "NPITM11S": (11.0, "NPI-X Item K (Night-time Behavior) Score"),
    "NPITM12S": (12.0, "NPI-X Item L (Appetite/Eating Change) Score"),
    "NPTOT": (13.0, "NPI-X (9) Total Score"),
    "NPTOTMN": (14.0, "Mean NPI-X (9) Total (Week 4 to 24)"),
}

# (label, avisitn, target, lo, hi); hi=None -> open ended.
# Official AWRANGE: Baseline '<= 1'; Week 2 '2 - 21'; Week N (4..24)
# '7N-6 - 7N+7'; Week 26 '>175' i.e. [176, inf).
WINDOWS = [("Baseline", 0.0, 1.0, None, 1.0),
           ("Week 2", 2.0, 14.0, 2.0, 21.0)] + [
    (f"Week {n}", float(n), float(7 * n), float(7 * n - 6), float(7 * n + 7))
    for n in range(4, 26, 2)
] + [("Week 26", 26.0, 182.0, 176.0, None)]


def assign_window(ady):
    for label, avisitn, target, lo, hi in WINDOWS:
        if lo is None:
            if ady <= hi:
                return label, avisitn, target, lo, hi
        elif hi is None:
            if ady >= lo:
                return label, avisitn, target, lo, hi
        elif lo <= ady <= hi:
            return label, avisitn, target, lo, hi
    return None


def awrange(lo, hi):
    if lo is None:
        return f"<= {int(hi)}"
    if hi is None:
        return f">{int(lo) - 1}"
    return f"{int(lo)} - {int(hi)}"


def main():
    qs = pl.read_parquet(f"{BASE}/sdtm/qs.parquet").filter(
        pl.col("QSTESTCD").is_in(TESTS)
    )
    rows: list[dict] = []
    for (subj,), g in qs.group_by("USUBJID", maintain_order=False):
        studyid = g["STUDYID"][0]
        for r in g.iter_rows(named=True):
            ady = r["QSDY"]
            w = assign_window(ady)
            if w is None:
                continue
            label, avisitn, target, lo, hi = w
            paramn, param = PARAMS[r["QSTESTCD"]]
            rows.append({
                "STUDYID": studyid,
                "USUBJID": subj,
                "AVISIT": label.rjust(16),
                "AVISITN": avisitn,
                "VISIT": r["VISIT"],
                "VISITNUM": float(r["VISITNUM"]) if r["VISITNUM"] is not None else None,
                "ADY": float(ady) if ady is not None else None,
                "ADT": r["QSDTC"],
                "PARAM": param,
                "PARAMCD": r["QSTESTCD"],
                "PARAMN": paramn,
                "PARAMTYP": "",
                "AVAL": float(r["QSSTRESN"]) if r["QSSTRESN"] is not None else None,
                "QSBLFL": r["QSBLFL"],
                "AWTARGET": target,
                "AWLO": lo,
                "AWHI": hi,
                "QSSEQ": float(r["QSSEQ"]),
            })

    df = pl.DataFrame(rows)
    # ANL01FL: closest-to-target per (subject, param, visit); ties broken by
    # earliest ADY then smallest QSSEQ (official Y is always the min-ADY
    # record among tied minima - verified across all groups).
    df = df.with_columns(
        (pl.col("AWTARGET") - pl.col("ADY")).abs().alias("_diff")
    )
    df = df.sort(["USUBJID", "PARAMCD", "AVISIT", "_diff", "ADY", "QSSEQ"])
    # first row per group after the sort is the winner
    df = df.with_columns(
        (pl.int_range(pl.len()).over(["USUBJID", "PARAMCD", "AVISIT"]) == 0).alias("_isy")
    )
    df = df.with_columns(
        pl.when(pl.col("_isy")).then(pl.lit("Y")).otherwise(pl.lit("")).alias("ANL01FL")
    )
    df = df.with_columns(
        pl.when(pl.col("QSBLFL") == "Y").then(pl.lit("Y")).otherwise(pl.lit("")).alias("ABLFL")
    )
    # BASE from ABLFL row
    base = (
        df.filter(pl.col("ABLFL") == "Y")
        .group_by(["USUBJID", "PARAMCD"])
        .agg(pl.col("AVAL").first().alias("BASE"))
    )
    df = df.join(base, on=["USUBJID", "PARAMCD"], how="left")
    df = df.with_columns(
        (pl.col("AVAL") - pl.col("BASE")).alias("CHG"),
        pl.when((pl.col("BASE").is_null()) | (pl.col("BASE") == 0))
        .then(None)
        .otherwise((pl.col("AVAL") - pl.col("BASE")) * 100 / pl.col("BASE"))
        .alias("PCHG"),
        (pl.col("AWTARGET") - pl.col("ADY")).abs().alias("AWTDIFF"),
    )
    df = df.drop(["_diff", "_isy", "QSBLFL"])
    df = df.with_columns(
        pl.when(pl.col("AWLO").is_null())
        .then(pl.lit("<= 1"))
        .when(pl.col("AWHI").is_null())
        .then(pl.lit(">") + (pl.col("AWLO").cast(pl.Int64) - 1).cast(pl.String))
        .otherwise(
            pl.col("AWLO").cast(pl.Int64).cast(pl.String)
            + pl.lit(" - ")
            + pl.col("AWHI").cast(pl.Int64).cast(pl.String)
        )
        .alias("AWRANGE"),
        pl.lit("DAYS").alias("AWU"),
        pl.lit("").alias("DTYPE"),
        pl.col("ADT").str.strptime(pl.Date, "%Y-%m-%d"),
    )

    # --- NPTOTMN Baseline rows: duplicate each NPTOT baseline record ---
    dup = df.filter((pl.col("PARAMCD") == "NPTOT") & (pl.col("AVISITN") == 0.0)).with_columns(
        pl.lit(PARAMS["NPTOTMN"][1]).alias("PARAM"),
        pl.lit("NPTOTMN").alias("PARAMCD"),
        pl.lit(14.0).alias("PARAMN"),
        pl.lit("DERIVED").alias("PARAMTYP"),
        pl.lit("AVERAGE").alias("DTYPE"),
    )
    df = pl.concat([df, dup], how="vertical")
    main_rows = df.to_dicts()

    # --- NPTOTMN Weeks 4-24 rows (built as a separate frame with explicit
    # schema, then concatenated, to avoid None/float inference clashes) ---
    wrows: list[dict] = []
    subjects = sorted({r["USUBJID"] for r in main_rows})
    for subj in subjects:
        vals = [
            r["AVAL"]
            for r in main_rows
            if r["USUBJID"] == subj
            and r["PARAMCD"] == "NPTOT"
            and r["ANL01FL"] == "Y"
            and r["AVISITN"] in (6.0, 8.0, 10.0, 12.0)
            and r["AVAL"] is not None
        ]
        if not vals:
            continue
        aval = sum(vals) / len(vals)
        base_row = next(
            r for r in main_rows
            if r["USUBJID"] == subj and r["PARAMCD"] == "NPTOT" and r["ABLFL"] == "Y"
        )
        basev = base_row["AVAL"]
        # CHG/PCHG are null on derived AVERAGE rows (official); BASE is kept.
        first = next(r for r in main_rows if r["USUBJID"] == subj)
        wrows.append({
            "STUDYID": first["STUDYID"],
            "USUBJID": subj,
            "AVISIT": "Weeks 4-24".rjust(16),
            "AVISITN": 98.0,
            "VISIT": "",
            "VISITNUM": None,
            "ADY": None,
            "ADT": None,
            "PARAM": PARAMS["NPTOTMN"][1],
            "PARAMCD": "NPTOTMN",
            "PARAMN": 14.0,
            "PARAMTYP": "DERIVED",
            "AVAL": aval,
            "BASE": basev,
            "CHG": None,
            "PCHG": None,
            "ABLFL": "",
            "ANL01FL": "Y",
            "DTYPE": "AVERAGE",
            "AWRANGE": "22 - 175",
            "AWTARGET": 98.0,
            "AWTDIFF": 0.0,
            "AWLO": 22.0,
            "AWHI": 175.0,
            "AWU": "DAYS",
            "QSSEQ": None,
        })

    schema = df.schema
    wdf = pl.DataFrame(wrows, schema=schema) if wrows else None
    df = pl.concat([df, wdf], how="vertical") if wdf is not None else df
    # official order: (USUBJID, PARAMN, AVISITN, ANL01FL desc, QSSEQ asc nulls last)
    df = df.sort(
        ["USUBJID", "PARAMN", "AVISITN", "ANL01FL", "QSSEQ"],
        descending=[False, False, False, True, False],
        nulls_last=True,
    )
    out = f"{BASE}/upstream/adqsnpix_input.parquet"
    table = df.to_arrow()
    fields = [
        pa.field(f.name, pa.string(), nullable=True)
        if pa.types.is_large_string(f.type)
        else f
        for f in table.schema
    ]
    pq.write_table(table.cast(pa.schema(fields)), out)
    print(f"wrote {out}: {df.shape[0]} rows x {df.shape[1]} cols")


if __name__ == "__main__":
    main()
