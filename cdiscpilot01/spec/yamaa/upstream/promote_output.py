#!/usr/bin/env python3
"""Promote a spec output to an upstream input for downstream specs.

Usage: python upstream/promote_output.py <domain>

Copies output/<domain>.parquet to upstream/<domain>.parquet, rewriting
large_string columns as plain `string`: the YAMAA engine rejects
large_string input columns, so downstream specs that look up ADSL/ADAE
(e.g. adtte reads upstream/adsl.parquet + upstream/adae.parquet) need
this plain-string twin. Values, nulls, and column order are unchanged.
"""
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

D = Path(__file__).resolve().parents[1]

domain = sys.argv[1].lower()
src = D / 'output' / f'{domain}.parquet'
dst = D / 'upstream' / f'{domain}.parquet'

t = pq.read_table(src)
fields = [pa.field(f.name, pa.string(), nullable=f.nullable, metadata=f.metadata)
          if pa.types.is_large_string(f.type) else f for f in t.schema]
pq.write_table(t.cast(pa.schema(fields)), dst)
print(f"promoted {src} -> {dst}: {t.num_rows} rows x {t.num_columns} cols")
