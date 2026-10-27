# ODM source and generated extracts

The committed `car-t-openclinica.xml` is the original archived source.
All other XML/CSV/JSON files in this directory are reproducible build products.

Run `python cart-t/program/odm/extract.py` from the repository root with the
pinned environment. It writes the native item table, per-form wide groups,
subjects, structural groups, clinical items, item dictionary and inventory.
Full repeat keys are retained. A repeated item within one complete group is
an error; document order is not interpreted as correction precedence.

Empty fields are not filled with invented clinical values. Original blanks
and native null/value-presence indicators remain in `items.csv`. SDTM reads
the shaped CSVs with empty strings treated as missing.

See `spec/source/README.md` for form coverage and `program/odm/extract.py`
for the complete instance key and normalized item-column naming rule.
