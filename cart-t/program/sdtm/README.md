# SDTM execution

After extraction, `python cart-t/program/sdtm/run.py` executes the project's
ten SDTM specifications in `spec/yamaa/sdtm/`. Each domain has explicit
row selection, variables, source mappings and metadata. The runner writes
one log and one engine report per dataset under `log/`.

All clinical mapping is in yamaa. Source group ordinals retain complete
repeat identity and expose original items in the statistical review workbook.
The full `program/run.py` also qualifies XPT, generates Define-XML, audits
source preservation and renders the workbook.
