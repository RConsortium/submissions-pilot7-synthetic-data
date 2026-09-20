"""Build ADLBHY upstream base from the generated ADLBC frame.

ADLBHY (Hy's Law, 9,954 x 43) is derived from ADLBC base-family rows for
ALT/AST/BILI at scheduled visits (Baseline, Weeks 2-24; no '.', no EOT).

Row model (all verified empirically against the official ADLBHY parquet):
* base rows (4,977): the ADLBC ALT/AST/BILI rows, PARAMN remapped to 1/2/3,
  plus CRIT1='R2A1HI > 1.5', CRIT1FL=Y/N/'' ('' when R2A1HI null),
  CRIT1FN=1/0/null, SHIFT1='', SHIFT1N=null, PARAMTYP='', PARCAT1='CHEM'.
* derived rows (4,977): one BILIHY/TRANSHY/HYLAW per (USUBJID, AVISIT):
    BILIHY  = 1 if BILI R2A1HI > 1.5 else 0   (null when BILI R2A1HI null)
    TRANSHY = 1 if max(ALT,AST R2A1HI) > 1.5 else 0
              (null when both null; no such case in the data)
    HYLAW   = 1 iff BILIHY=1 and TRANSHY=1 else 0
  BASE = baseline-visit derived AVAL, except null whenever the visit AVAL is
         null, and null when the subject has no baseline visit at all.
  SHIFT1/SHIFT1N compare BASE -> AVAL as Normal(0)/High(1):
    (0,0)->'Normal to Normal'/1, (0,1)->'Normal to High'/2,
    (1,0)->'High to Normal'/0, (1,1)->''/null;
    also ''/null when AVAL or BASE is null.
  Derived rows carry AVISIT/AVISITN and subject columns from ADLBC; ADY, ADT,
  VISIT and VISITNUM are null/empty on derived rows;
  A1LO/A1HI/R2A1LO/R2A1HI/BR2A1LO/BR2A1HI are null; ABLFL='Y' at baseline.

Writes upstream/adlbhy_base.parquet (official Arrow types) and
upstream/adlbhy_input.parquet (plain-string twin for the YAMAA engine,
which rejects large_string input columns).
"""
import polars as pl

ROOT = str(Path(__file__).resolve().parents[1])
BASE_PARAMS = ["ALT", "AST", "BILI"]
VISITNUMS = [0.0, 2.0, 4.0, 6.0, 8.0, 12.0, 16.0, 20.0, 24.0]

VISIT_KEYS = ["USUBJID", "AVISIT", "AVISITN", "VISIT", "VISITNUM", "ADT",
              "STUDYID", "SUBJID", "TRTP", "TRTPN", "TRTA", "TRTAN",
              "TRTSDT", "TRTEDT", "AGE", "AGEGR1", "AGEGR1N", "RACE", "RACEN",
              "SEX", "COMP24FL", "DSRAEFL", "SAFFL"]

DERIVED = [
    ("BILIHY", "Bilirubin 1.5 x ULN", 4.0),
    ("TRANSHY", "Transaminase 1.5 x ULN", 5.0),
    ("HYLAW", "Total Bili 1.5 x ULN and Transaminase 1.5 x ULN", 6.0),
]
BASE_PARAMN = {"ALT": 1.0, "AST": 2.0, "BILI": 3.0}

a = pl.read_parquet(f"{ROOT}/upstream/adlbc_base.parquet")
b = a.filter(pl.col("PARAMCD").is_in(BASE_PARAMS)
             & pl.col("AVISITN").is_in(VISITNUMS))
assert b.height == 4977, b.height

# --- per-visit R2A1HI for the three base params ---------------------------
w = (b.group_by(VISIT_KEYS, maintain_order=True)
      .agg([pl.col("R2A1HI").filter(pl.col("PARAMCD") == p).first().alias(f"{p}_R")
            for p in BASE_PARAMS]))
assert w.height == 1659, w.height

w = w.with_columns([
    pl.when(pl.col("BILI_R").is_null()).then(None)
      .when(pl.col("BILI_R") > 1.5).then(1.0).otherwise(0.0).alias("BILIHY_A"),
    pl.when(pl.col("ALT_R").is_null() & pl.col("AST_R").is_null()).then(None)
      .when(pl.max_horizontal("ALT_R", "AST_R") > 1.5).then(1.0).otherwise(0.0).alias("TRANSHY_A"),
])
w = w.with_columns([
    pl.when((pl.col("BILIHY_A") == 1.0) & (pl.col("TRANSHY_A") == 1.0))
      .then(1.0).otherwise(0.0).alias("HYLAW_A"),
])

# baseline derived values per subject
base_w = (w.filter(pl.col("AVISITN") == 0.0)
           .select(["USUBJID", pl.col("BILIHY_A").alias("BILIHY_B"),
                    pl.col("TRANSHY_A").alias("TRANSHY_B"),
                    pl.col("HYLAW_A").alias("HYLAW_B")]))
w = w.join(base_w, on="USUBJID", how="left")

# --- base rows ------------------------------------------------------------
base_rows = b.with_columns([
    pl.col("PARAMCD").replace_strict(BASE_PARAMN).alias("PARAMN"),
    pl.lit("").alias("PARAMTYP"),
    pl.lit("CHEM").alias("PARCAT1"),
    pl.lit("R2A1HI > 1.5").alias("CRIT1"),
    pl.when(pl.col("R2A1HI").is_null()).then(pl.lit(""))
      .when(pl.col("R2A1HI") > 1.5).then(pl.lit("Y")).otherwise(pl.lit("N")).alias("CRIT1FL"),
    pl.when(pl.col("R2A1HI").is_null()).then(None)
      .when(pl.col("R2A1HI") > 1.5).then(1.0).otherwise(0.0).alias("CRIT1FN"),
    pl.lit("").alias("SHIFT1"),
    pl.lit(None).cast(pl.Float64).alias("SHIFT1N"),
])

# --- derived rows ----------------------------------------------------------
def shift1(base, aval):
    return (pl.when(base.is_null() | aval.is_null()).then(pl.lit(""))
            .when((base == 0.0) & (aval == 0.0)).then(pl.lit("Normal to Normal"))
            .when((base == 0.0) & (aval == 1.0)).then(pl.lit("Normal to High"))
            .when((base == 1.0) & (aval == 0.0)).then(pl.lit("High to Normal"))
            .otherwise(pl.lit("")))

def shift1n(base, aval):
    return (pl.when(base.is_null() | aval.is_null()).then(None)
            .when((base == 0.0) & (aval == 0.0)).then(1.0)
            .when((base == 0.0) & (aval == 1.0)).then(2.0)
            .when((base == 1.0) & (aval == 0.0)).then(0.0)
            .otherwise(None).cast(pl.Float64))

derived_frames = []
for pcd, param, paramn in DERIVED:
    aval = pl.col(f"{pcd}_A")
    blo = pl.col(f"{pcd}_B")
    dbase = pl.when(aval.is_null()).then(None).otherwise(blo)
    null_f = [pl.lit(None).cast(pl.Float64).alias(a) for a in
              ["A1LO", "A1HI", "R2A1LO", "R2A1HI", "BR2A1LO", "BR2A1HI"]]
    d = (w.with_columns([
            aval.alias("AVAL"),
            dbase.alias("BASE"),
            shift1(dbase, aval).alias("SHIFT1"),
            shift1n(dbase, aval).alias("SHIFT1N"),
            pl.lit(None).cast(pl.Float64).alias("ADY"),
            pl.lit(None).cast(pl.Date).alias("ADT"),
        ] + null_f + [
            pl.when(pl.col("AVISITN") == 0.0).then(pl.lit("Y")).otherwise(pl.lit("")).alias("ABLFL"),
            pl.lit(param).alias("PARAM"),
            pl.lit(pcd).alias("PARAMCD"),
            pl.lit(paramn).alias("PARAMN"),
            pl.lit("DERIVED").alias("PARAMTYP"),
            pl.lit("HYLAW").alias("PARCAT1"),
            pl.lit("").alias("CRIT1"),
            pl.lit("").alias("CRIT1FL"),
            pl.lit(None).cast(pl.Float64).alias("CRIT1FN"),
            # derived rows carry no SDTM visit name/number
            pl.lit("").alias("VISIT"),
            pl.lit(None).cast(pl.Float64).alias("VISITNUM"),
        ]))
    derived_frames.append(d)

COLS = ["STUDYID", "SUBJID", "USUBJID", "TRTP", "TRTPN", "TRTA", "TRTAN",
        "TRTSDT", "TRTEDT", "AGE", "AGEGR1", "AGEGR1N", "RACE", "RACEN", "SEX",
        "COMP24FL", "DSRAEFL", "SAFFL", "AVISIT", "AVISITN", "ADY", "ADT",
        "VISIT", "VISITNUM", "PARAMTYP", "PARAM", "PARAMCD", "PARAMN", "PARCAT1",
        "AVAL", "BASE", "A1LO", "A1HI", "R2A1LO", "R2A1HI", "BR2A1LO", "BR2A1HI",
        "ABLFL", "SHIFT1", "SHIFT1N", "CRIT1", "CRIT1FL", "CRIT1FN"]

final = pl.concat([base_rows.select(COLS)] +
                  [d.select(COLS) for d in derived_frames],
                  how="diagonal")
assert final.height == 9954, final.height
final.write_parquet(f"{ROOT}/upstream/adlbhy_base.parquet")
print("wrote upstream/adlbhy_base.parquet", final.shape)

# plain-string twin for the YAMAA engine (rejects large_string inputs)
import pyarrow.parquet as _pq
import pyarrow as _pa

t = _pq.read_table(f"{ROOT}/upstream/adlbhy_base.parquet")
fields, arrays = [], []
for f in t.schema:
    if _pa.types.is_large_string(f.type):
        fields.append(_pa.field(f.name, _pa.string(), nullable=True, metadata=f.metadata))
        arrays.append(t.column(f.name).combine_chunks().cast(_pa.string()))
    else:
        fields.append(f)
        arrays.append(t.column(f.name))
_pq.write_table(_pa.Table.from_arrays(arrays, schema=_pa.schema(fields)),
                f"{ROOT}/upstream/adlbhy_input.parquet")
print("wrote upstream/adlbhy_input.parquet (plain string)")
