# ODM source and native item evidence

The authoritative source is the committed `car-t-openclinica.xml` in this
folder. `program/odm/prepare.py` reads it in place and never rewrites it.
The native yamaa reader accepts its US-ASCII declaration directly.
`items.parquet` and `inventory.json` are reproducible build products.

SDTM specifications read this unchanged XML directly. Native yamaa grouped rows
and exact ItemOID expressions perform clinical reshaping. No per-form staging
tables or CSV inputs are needed.

`items.parquet` contains the complete native item table, including original
names, values, ordinals, repeats and null/value-presence indicators. It is
QC evidence for source review; SDTM does not read it. `inventory.json` records
source hashing and item/group/subject counts.

The download package includes the original XML. See `spec/source/README.md`
for provenance and coverage.
