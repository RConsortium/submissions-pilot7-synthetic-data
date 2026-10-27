# SDTM execution

After source preparation, `python cart-t/program/sdtm/run.py` executes the project's
ten SDTM specifications in `spec/yamaa/sdtm/`. Each domain has explicit
row selection, variables, source mappings and metadata. The runner writes
one log and one engine report per dataset under `log/`.

All clinical mapping and row reshaping is in yamaa. Inputs point directly to
the ODM XML. Grouped rows and native item reads preserve repeats; exact
ItemOIDs avoid ambiguous normalized source names. The original-item Parquet
provides source ordinal traceability for QC and human review.
The full `program/run.py` also qualifies XPT, generates Define-XML, audits
source preservation and records data-quality queries.
