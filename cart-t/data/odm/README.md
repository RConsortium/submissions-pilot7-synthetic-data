# ODM source and native item evidence

The authoritative source is `.archieve/cart-t/car-t-openclinica.xml`.
`program/odm/prepare.py` stages a byte-identical `car-t-openclinica.xml` here.
The native yamaa reader accepts its US-ASCII declaration directly.
All data files here are reproducible build products.

SDTM specifications read this unchanged XML directly. Native yamaa grouped rows
and exact ItemOID expressions perform clinical reshaping. No per-form staging
tables or CSV inputs are needed.

`items.parquet` contains the complete native item table, including original
names, values, ordinals, repeats and null/value-presence indicators. It is
QC evidence for source review; SDTM does not read it. `inventory.json` records
source hashing and item/group/subject counts.

The download package includes the staged original XML, so it can be reviewed
without the archive. See `spec/source/README.md` for provenance and coverage.
