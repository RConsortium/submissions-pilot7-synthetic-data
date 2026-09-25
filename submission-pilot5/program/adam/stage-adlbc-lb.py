"""Input staging for pilot5 ADLBC (mirrors adlbc.r input prep, NOT derivation).

Replicates R's first steps:
  sup <- supplb %>% pivot_wider(names_from = QNAM) %>% mutate(LBSEQ = as.numeric(IDVARVAL))
  adlb00 <- lb %>% left_join(sup, by = c("STUDYID", "USUBJID", "LBSEQ")) %>%
    filter(LBCAT == "CHEMISTRY")

Only the ENDPOINT supplement is carried: LBTMSHI is never referenced by
adlbc.r. IDVARVAL carries leading spaces in the staged parquet, so it is
stripped before the numeric cast. No ADaM variable is derived here; every
derivation lives in the YAML specs.
"""

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

sup = pl.read_parquet("sdtm/supplb.parquet")
endpoint = sup.filter(pl.col("QNAM") == "ENDPOINT").select(
    "STUDYID",
    "USUBJID",
    pl.col("IDVARVAL").str.strip_chars().cast(pl.Float64).alias("LBSEQ"),
    pl.col("QVAL").alias("ENDPOINT"),
)

lb = pl.read_parquet("sdtm/lb.parquet")
out = lb.join(endpoint, on=["STUDYID", "USUBJID", "LBSEQ"], how="left").filter(
    pl.col("LBCAT") == "CHEMISTRY"
)
# Polars writes Arrow large_string; the staged SDTM parquets (and the yamaa
# reader, pre-#736) use plain string. Cast back for compatibility.
table = out.to_arrow()
table = table.cast(
    pa.schema(
        [
            pa.field(
                f.name, pa.string() if pa.types.is_large_string(f.type) else f.type
            )
            for f in table.schema
        ]
    )
)
pq.write_table(table, "adlbc-lb.parquet")
print(
    "WROTE adlbc-lb.parquet:",
    table.num_rows,
    "rows;",
    "ENDPOINT='Y':",
    out.filter(pl.col("ENDPOINT") == "Y").height,
)
