#!/usr/bin/env python3
"""Build ADVS engine input from SDTM VS.

ADVS (32,139 x 34) keeps all 29,643 SDTM VS rows and adds six derived
columns that the YAMAA spec maps directly:

* AVISIT/AVISITN: BASELINE -> ('Baseline', 0); WEEK n -> ('Week n', n);
  SCREENING 1/2, AMBUL ECG PLACEMENT/REMOVAL, RETRIEVAL, UNSCHEDULED 3.1
  -> ('', null) and are excluded from analysis (ANL01FL='').
* ABLFL: 'Y' on BASELINE rows, '' elsewhere.
* BASE: VSSTRESN at the BASELINE visit per (USUBJID, VSTESTCD, VSTPT)
  (timepoint distinguishes the triplicate BP/pulse readings); null when
  the subject/param/timepoint has no baseline row.
* ANL01FL: 'Y' where AVISIT != '', '' elsewhere.
* EOTFL / End-of-Treatment duplicates: per (USUBJID, VSTESTCD, VSTPT),
  when the latest scheduled analysis visit is after Week 2
  (max AVISITN > 2), the rows at that visit are duplicated with
  AVISIT='End of Treatment', AVISITN=99, EOTFL='Y', appended after the
  base rows in source order. Groups whose latest scheduled visit is
  Baseline or Week 2 get no EOT rows -- this reproduces the official
  ADVS exactly (verified: EOT present in all 2,794 groups iff
  max scheduled AVISITN > 2, zero violations in either direction).

Row order: SDTM VS order for base rows, EOT duplicates appended after.
All strings written as plain `string` (the engine rejects large_string).
"""
import polars as pl
from pathlib import Path

D = Path(__file__).resolve().parents[1]
OUT = D / 'upstream' / 'advs_input.parquet'

WEEK_NUM = {'WEEK 2': 2.0, 'WEEK 4': 4.0, 'WEEK 6': 6.0, 'WEEK 8': 8.0,
            'WEEK 12': 12.0, 'WEEK 16': 16.0, 'WEEK 20': 20.0,
            'WEEK 24': 24.0, 'WEEK 26': 26.0}

vs = pl.read_parquet(D / 'sdtm' / 'vs.parquet')
print(f"rows: {vs.shape}")

df = vs.with_columns([
    pl.when(pl.col('VISIT') == 'BASELINE').then(pl.lit('Baseline'))
      .when(pl.col('VISIT').is_in(list(WEEK_NUM)))
      .then(pl.col('VISIT').str.to_titlecase())
      .otherwise(pl.lit('')).alias('AVISIT'),
    pl.when(pl.col('VISIT') == 'BASELINE').then(pl.lit(0.0))
      .when(pl.col('VISIT').is_in(list(WEEK_NUM)))
      .then(pl.col('VISIT').replace(WEEK_NUM).cast(pl.Float64))
      .otherwise(pl.lit(None, dtype=pl.Float64)).alias('AVISITN'),
    pl.when(pl.col('VISIT') == 'BASELINE').then(pl.lit('Y'))
      .otherwise(pl.lit('')).alias('ABLFL'),
    pl.lit('').alias('EOTFL'),
])

base = (df.filter(pl.col('VISIT') == 'BASELINE')
          .select('USUBJID', 'VSTESTCD', 'VSTPT', 'VSSTRESN')
          .unique()
          .rename({'VSSTRESN': 'BASE'}))
df = df.join(base, on=['USUBJID', 'VSTESTCD', 'VSTPT'], how='left')

df = df.with_columns(
    pl.when(pl.col('AVISIT') != '').then(pl.lit('Y'))
      .otherwise(pl.lit('')).alias('ANL01FL')
)

sched = df.filter(pl.col('AVISIT') != '')
mx = (sched.group_by(['USUBJID', 'VSTESTCD', 'VSTPT'])
           .agg(pl.col('AVISITN').max().alias('mx')))
eot_src = (sched.join(mx, on=['USUBJID', 'VSTESTCD', 'VSTPT'])
                .filter((pl.col('AVISITN') == pl.col('mx')) & (pl.col('mx') > 2))
                .drop('mx')
                .with_columns([
                    pl.lit('End of Treatment').alias('AVISIT'),
                    pl.lit(99.0).alias('AVISITN'),
                    pl.lit('Y').alias('EOTFL'),
                    pl.lit('Y').alias('ANL01FL'),
                ]))

out = pl.concat([df, eot_src], how='diagonal')
print(f"EOT duplicates: {eot_src.height}")
order = ['STUDYID', 'DOMAIN', 'USUBJID', 'VSSEQ', 'VSTESTCD', 'VSTEST',
         'VSPOS', 'VSORRES', 'VSORRESU', 'VSSTRESC', 'VSSTRESN', 'VSSTRESU',
         'VSSTAT', 'VSLOC', 'VSBLFL', 'VISITNUM', 'VISIT', 'VISITDY', 'VSDTC',
         'VSDY', 'VSTPT', 'VSTPTNUM', 'VSELTM', 'VSTPTREF', 'EOTFL', 'BASE',
         'AVISIT', 'AVISITN', 'ANL01FL', 'ABLFL']
out = out.select(order)
out.write_parquet(OUT)
# YAMAA does not support large_string; rewrite with plain string
import pyarrow as pa
import pyarrow.parquet as pq
t = pq.read_table(OUT)
fields = [pa.field(f.name, pa.string(), nullable=f.nullable, metadata=f.metadata)
          if pa.types.is_large_string(f.type) else f for f in t.schema]
pq.write_table(t.cast(pa.schema(fields)), OUT)
print(f"wrote {OUT}: {out.shape[0]} rows x {out.shape[1]} cols (string, not large_string)")
