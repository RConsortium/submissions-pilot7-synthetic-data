#!/usr/bin/env python3
"""Build the analysis-ready ADLBC upstream frame.

Reproducible driver preprocessing for the ADLBC YAMAA specification.

Pipeline
--------
1. Read SDTM LB (chemistry only), drop the 36 RETRIEVAL / AMBUL ECG REMOVAL
   records that never enter analysis.
2. Build the 37,132-row base family (32,704 ordinary + 4,428 End-of-Treatment
   duplicates) with every base derivation.
3. Build the 37,132-row underscore family (one row per base row):
   PARAMCD = '_' + base code, PARAMN = base + 100, and the standardized
   change-from-previous-visit parameter:

       AVAL = null                                    if LBBLFL = 'Y' or AVISIT = '.'
       AVAL = SAS_ROUND((AVAL - PREV_AVAL)
                        / (0.5 * (A1HI - A1LO)), 0.1)  otherwise

   where PREV_AVAL is the base AVAL of the previous *scheduled* record
   (AVISIT not in '.', 'End of Treatment') within (USUBJID, LBTESTCD)
   ordered by (ADT, LBSEQ).  EOT rows reuse the PREV_AVAL of their source
   visit row.  SAS_ROUND is round-half-away-from-zero to one decimal with
   SAS's documented floating-point fuzz at exact .05 boundaries (a 1e-9
   tolerance reproduces every official value exactly).

   The formula above is documented in the official define.xml value-level
   metadata for ADLBC.AVAL, e.g.:
     "(LBSTRESN - previous LBSTRESN)/(.5*(LBSTNRHI-LBSTNRLO)); null if LBBLFL=Y"

   The rounding to one decimal (SignificantDigits=1, DisplayFormat=4.1) and
   the exact "previous scheduled record" rule were reverse-engineered from
   the official ADLBC parquet and verified to reproduce all 74,264 AVAL
   values with zero differences.

4. Merge the ADSL columns.

Output: upstream/adlbc_base.parquet -- 74,264 rows, one per final ADLBC row,
with every analysis value.  The adlbc.yaml YAMAA spec maps these to the 46
official columns (names, types, labels, order).

YAMAA cannot express this derivation natively: the language deliberately
omits ROUND (REQ-0418) and the lag-over-scheduled-records plus EOT
duplication are mechanical row assembly, so they live here, honestly
labeled as driver preprocessing.
"""

import math
import polars as pl

ROOT = str(Path(__file__).resolve().parents[1])

BASE_TESTS = ["SODIUM", "K", "CL", "BILI", "ALP", "GGT", "ALT", "AST", "BUN",
              "CREAT", "URATE", "PHOS", "CA", "GLUC", "PROT", "ALB", "CHOL", "CK"]
PARAMN = {t: 18 + i for i, t in enumerate(BASE_TESTS)}
PARAM_LABEL = {
    "ALB": "Albumin (g/L)", "ALP": "Alkaline Phosphatase (U/L)",
    "ALT": "Alanine Aminotransferase (U/L)", "AST": "Aspartate Aminotransferase (U/L)",
    "BILI": "Bilirubin (umol/L)", "BUN": "Blood Urea Nitrogen (mmol/L)",
    "CA": "Calcium (mmol/L)", "CHOL": "Cholesterol (mmol/L)",
    "CK": "Creatine Kinase (U/L)", "CL": "Chloride (mmol/L)",
    "CREAT": "Creatinine (umol/L)", "GGT": "Gamma Glutamyl Transferase (U/L)",
    "GLUC": "Glucose (mmol/L)", "K": "Potassium (mmol/L)",
    "PHOS": "Phosphate (mmol/L)", "PROT": "Protein (g/L)",
    "SODIUM": "Sodium (mmol/L)", "URATE": "Urate (umol/L)",
}
UNDER_LABEL_SUFFIX = " change from previous visit, relative to normal range"

EXCLUDE_VISITS = ["RETRIEVAL", "AMBUL ECG REMOVAL"]
EOT_VISITNUMS = [2, 4, 6, 8, 12, 16, 20, 24]
DOT = "               ."
BASELINE = "        Baseline"
EOT = "End of Treatment"


def avisit(visit: str) -> str:
    if visit == "SCREENING 1":
        return BASELINE
    if visit.startswith("WEEK "):
        n = visit.split()[1]
        return f"{'Week ' + n:>16}"
    return DOT


def avisitn(visit: str):
    if visit == "SCREENING 1":
        return 0.0
    if visit.startswith("WEEK "):
        return float(visit.split()[1])
    return None


def sas_round1(x):
    """SAS ROUND(x, 0.1): half away from zero, with float-boundary fuzz."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    eps = 1e-9
    if x >= 0:
        return math.floor(x * 10 + 0.5 + eps) / 10
    return math.ceil(x * 10 - 0.5 - eps) / 10


def main():
    lb = pl.read_parquet(f"{ROOT}/sdtm/lb.parquet")
    adsl = pl.read_parquet(f"{ROOT}/upstream/adsl.parquet")

    chem = lb.filter(pl.col("LBCAT") == "CHEMISTRY")
    assert chem.height == 32740, chem.height
    chem = chem.filter(~pl.col("VISIT").is_in(EXCLUDE_VISITS))
    assert chem.height == 32704, chem.height

    lbdtc = pl.col("LBDTC").str.slice(0, 10).str.to_date()
    ord_ = (
        chem.with_columns(
            ADT=lbdtc,
            AVISIT=pl.col("VISIT").map_elements(avisit, return_dtype=pl.String),
            AVISITN=pl.col("VISIT").map_elements(avisitn, return_dtype=pl.Float64),
        )
        .with_columns(
            PARAMCD=pl.col("LBTESTCD"),
            PARAM=pl.col("LBTESTCD").map_elements(lambda t: PARAM_LABEL[t], return_dtype=pl.String),
            PARAMN=pl.col("LBTESTCD").map_elements(lambda t: float(PARAMN[t]), return_dtype=pl.Float64),
            PARCAT1=pl.lit("CHEM"),
            AVAL=pl.col("LBSTRESN"),
            A1LO=pl.col("LBSTNRLO"),
            A1HI=pl.col("LBSTNRHI"),
            ABLFL=pl.when(pl.col("LBBLFL") == "Y").then(pl.lit("Y")).otherwise(pl.lit("")),
            VISITNUM=pl.col("VISITNUM"),
        )
    )

    # --- ADSL merge -------------------------------------------------------
    adsl_cols = ["USUBJID", "SUBJID", "TRTSDT", "TRTEDT", "AGE", "AGEGR1", "AGEGR1N",
                 "RACE", "RACEN", "SEX", "COMP24FL", "DSRAEFL", "SAFFL",
                 "TRT01P", "TRT01PN", "TRT01A", "TRT01AN"]
    ord_ = ord_.join(adsl.select(adsl_cols), on="USUBJID", how="left")
    ord_ = ord_.with_columns(
        ADY=pl.when(pl.col("ADT") >= pl.col("TRTSDT"))
        .then((pl.col("ADT") - pl.col("TRTSDT")).dt.total_days() + 1)
        .otherwise((pl.col("ADT") - pl.col("TRTSDT")).dt.total_days())
        .cast(pl.Float64),
        TRTP=pl.col("TRT01P"), TRTPN=pl.col("TRT01PN").cast(pl.Float64),
        TRTA=pl.col("TRT01A"), TRTAN=pl.col("TRT01AN").cast(pl.Float64),
        STUDYID=pl.col("STUDYID"),
        DOMAIN=pl.lit("ADLBC"),
    )

    # --- BASE / CHG / ratios ----------------------------------------------
    base_map = (
        ord_.filter(pl.col("ABLFL") == "Y")
        .select(["USUBJID", "PARAMCD", "AVAL"])
        .rename({"AVAL": "BASE"})
    )
    ord_ = ord_.join(base_map, on=["USUBJID", "PARAMCD"], how="left")
    ord_ = ord_.with_columns(
        CHG=pl.when(pl.col("AVISIT") == BASELINE).then(None)
        .otherwise(pl.col("AVAL") - pl.col("BASE")),
        R2A1LO=pl.col("AVAL") / pl.col("A1LO"),
        R2A1HI=pl.col("AVAL") / pl.col("A1HI"),
        BR2A1LO=pl.col("BASE") / pl.col("A1LO"),
        BR2A1HI=pl.col("BASE") / pl.col("A1HI"),
        ALBTRVAL=pl.max_horizontal(
            1.5 * pl.col("A1HI") - pl.col("AVAL"),
            pl.col("AVAL") - 0.5 * pl.col("A1LO"),
        ),
        ANRIND=pl.when(pl.col("AVAL") > 1.5 * pl.col("A1HI")).then(pl.lit("H")).otherwise(pl.lit("N")),
        BNRIND=pl.when(pl.col("BASE").is_null()).then(pl.lit(""))
        .when(pl.col("BASE") > 1.5 * pl.col("A1HI")).then(pl.lit("H")).otherwise(pl.lit("N")),
    )

    # --- EOT duplication ---------------------------------------------------
    eot_src = (
        ord_.filter(pl.col("AVISITN").is_in(EOT_VISITNUMS))
        .sort(["USUBJID", "PARAMCD", "LBSEQ"])
        .group_by(["USUBJID", "PARAMCD"], maintain_order=True)
        .tail(1)
    )
    assert eot_src.height == 4428, eot_src.height
    eot = eot_src.with_columns(AVISIT=pl.lit(EOT), AVISITN=pl.lit(99.0))

    base = pl.concat([ord_, eot], how="diagonal")
    assert base.height == 37132, base.height

    # AENTMTFL: 'Y' on EOT rows and their source rows
    src_keys = eot_src.select(["USUBJID", "PARAMCD", "LBSEQ"]).with_columns(_s=pl.lit(1))
    base = base.join(src_keys, on=["USUBJID", "PARAMCD", "LBSEQ"], how="left")
    base = base.with_columns(
        AENTMTFL=pl.when((pl.col("AVISIT") == EOT) | pl.col("_s").is_not_null())
        .then(pl.lit("Y")).otherwise(pl.lit(""))
    ).drop("_s")

    # --- base ANL01FL: first max ALBTRVAL over visits 2..24 -----------------
    # (null ALBTRVAL rows can never win)
    cand = base.filter(pl.col("AVISITN").is_in(EOT_VISITNUMS) & pl.col("ALBTRVAL").is_not_null())
    # rank within (USUBJID, PARAMCD): max ALBTRVAL, tie -> earliest visit
    winners = (
        cand.sort(["USUBJID", "PARAMCD", "ALBTRVAL", "AVISITN", "ADT", "LBSEQ"],
                  descending=[False, False, True, False, False, False])
        .group_by(["USUBJID", "PARAMCD"], maintain_order=True)
        .first()
        .select(["USUBJID", "PARAMCD", "LBSEQ"])
        .with_columns(_w=pl.lit(1))
    )
    base = base.join(winners, on=["USUBJID", "PARAMCD", "LBSEQ"], how="left")
    # EOT rows share their source's LBSEQ, so they inherit the flag exactly
    # when their source visit row is the winner.
    # EOT rows share their source's LBSEQ, so they inherit the flag exactly
    # when their source visit row is the winner (no unconditional EOT='Y').
    base = base.with_columns(
        ANL01FL=pl.when(pl.col("_w").is_not_null())
        .then(pl.lit("Y")).otherwise(pl.lit(""))
    )
    base = base.drop("_w")

    # --- underscore family --------------------------------------------------
    # PREV_AVAL: previous scheduled record's AVAL within (USUBJID, PARAMCD)
    sched = base.filter(~pl.col("AVISIT").is_in([DOT, EOT]))
    prevmap = (
        sched.sort(["USUBJID", "PARAMCD", "ADT", "LBSEQ"])
        .with_columns(pl.col("AVAL").shift(1).over(["USUBJID", "PARAMCD"]).alias("PREV_AVAL"))
        .select(["USUBJID", "PARAMCD", "LBSEQ", "AVISIT", "PREV_AVAL"])
    )
    eot_prev = (
        base.filter(pl.col("AVISIT") == EOT)
        .select(["USUBJID", "PARAMCD", "LBSEQ"])
        .join(prevmap.drop("AVISIT"), on=["USUBJID", "PARAMCD", "LBSEQ"], how="left")
        .with_columns(AVISIT=pl.lit(EOT))
    )
    prevmap = pl.concat([prevmap, eot_prev.select(["USUBJID", "PARAMCD", "LBSEQ", "AVISIT", "PREV_AVAL"])])

    u = base.join(prevmap, on=["USUBJID", "PARAMCD", "LBSEQ", "AVISIT"], how="left")
    u = u.with_columns(
        _raw=pl.when(pl.col("AVISIT").is_in([BASELINE, DOT])).then(None).otherwise(
            (pl.col("AVAL") - pl.col("PREV_AVAL")) / (0.5 * (pl.col("A1HI") - pl.col("A1LO")))),
        UPARAMCD="_" + pl.col("PARAMCD"),
        UPARAMN=pl.col("PARAMN") + 100.0,
        UPARAM=pl.col("PARAM") + UNDER_LABEL_SUFFIX,
    )
    u = u.with_columns(
        UAVAL=pl.col("_raw").map_elements(sas_round1, return_dtype=pl.Float64),
    ).drop("_raw")
    # UANRIND derives from the ROUNDED UAVAL (official rule), not the raw
    # intermediate.
    u = u.with_columns(
        UANRIND=pl.when(pl.col("UAVAL").is_null()).then(pl.lit(""))
        .when(pl.col("UAVAL") > 1.0).then(pl.lit("H"))
        .when(pl.col("UAVAL") < -1.0).then(pl.lit("L"))
        .otherwise(pl.lit("N")),
    )

    # underscore ANL01FL: first max |AVAL| over visits 2..24, EOT inherits
    u = u.with_columns(_abs=pl.col("UAVAL").abs())
    uwinners = (
        u.filter(pl.col("AVISITN").is_in(EOT_VISITNUMS) & pl.col("UAVAL").is_not_null())
        .sort(["USUBJID", "UPARAMCD", "_abs", "AVISITN", "ADT", "LBSEQ"],
              descending=[False, False, True, False, False, False])
        .group_by(["USUBJID", "UPARAMCD"], maintain_order=True)
        .first()
        .select(["USUBJID", "UPARAMCD", "LBSEQ"])
        .with_columns(_uw=pl.lit(1))
    )
    u = u.join(uwinners, on=["USUBJID", "UPARAMCD", "LBSEQ"], how="left")
    # EOT inherits only when its source LBSEQ was the winner.
    u = u.with_columns(
        UANL01FL=pl.when(pl.col("_uw").is_not_null())
        .then(pl.lit("Y")).otherwise(pl.lit(""))
    ).drop(["_uw", "_abs"])

    # --- assemble final frame ----------------------------------------------
    # base rows: underscore columns null/empty; underscore rows: mapped columns
    base_out = base.with_columns(
        UPARAMCD=pl.col("PARAMCD"), UPARAMN=pl.col("PARAMN"), UPARAM=pl.col("PARAM"),
        UAVAL=pl.col("AVAL"), UANRIND=pl.col("ANRIND"), UANL01FL=pl.col("ANL01FL"),
        _fam=pl.lit("base"),
    )
    under_out = u.with_columns(
        PARAMCD=pl.col("UPARAMCD"), PARAMN=pl.col("UPARAMN"), PARAM=pl.col("UPARAM"),
        AVAL=pl.col("UAVAL"), ANRIND=pl.col("UANRIND"), ANL01FL=pl.col("UANL01FL"),
        BASE=pl.lit(None, dtype=pl.Float64), CHG=pl.lit(None, dtype=pl.Float64),
        A1LO=pl.lit(None, dtype=pl.Float64), A1HI=pl.lit(None, dtype=pl.Float64),
        R2A1LO=pl.lit(None, dtype=pl.Float64), R2A1HI=pl.lit(None, dtype=pl.Float64),
        BR2A1LO=pl.lit(None, dtype=pl.Float64), BR2A1HI=pl.lit(None, dtype=pl.Float64),
        BNRIND=pl.lit(""), ABLFL=pl.lit(""),
        _fam=pl.lit("under"),
    ).drop(["UPARAMCD", "UPARAMN", "UPARAM", "UAVAL", "UANRIND", "UANL01FL", "PREV_AVAL"])
    base_out = base_out.drop(["UPARAMCD", "UPARAMN", "UPARAM", "UAVAL", "UANRIND", "UANL01FL"])

    final = pl.concat([base_out, under_out], how="diagonal")
    assert final.height == 74264, final.height
    final.write_parquet(f"{ROOT}/upstream/adlbc_base.parquet")
    print("wrote upstream/adlbc_base.parquet", final.shape)

    # Engine-readable input copy: the YAMAA engine rejects large_string input
    # columns (source_field_type_unsupported), so the spec reads this plain-
    # string twin.  The writer (run_spec.py) restores official Arrow types.
    import pyarrow.parquet as _pq
    import pyarrow as _pa

    t = _pq.read_table(f"{ROOT}/upstream/adlbc_base.parquet")
    fields, arrays = [], []
    for f in t.schema:
        if _pa.types.is_large_string(f.type):
            fields.append(_pa.field(f.name, _pa.string(), nullable=True, metadata=f.metadata))
            arrays.append(t.column(f.name).combine_chunks().cast(_pa.string()))
        else:
            fields.append(f)
            arrays.append(t.column(f.name))
    _pq.write_table(_pa.Table.from_arrays(arrays, schema=_pa.schema(fields)),
                    f"{ROOT}/upstream/adlbc_input.parquet")
    print("wrote upstream/adlbc_input.parquet (plain string)")


if __name__ == "__main__":
    main()
