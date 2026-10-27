# SDTM execution

The maintained mappings are `spec/yamaa/sdtm/*.yaml`. Run
`python .github/scripts/validate_yamaa.py kn564` from the repository root
with the pinned dependencies in `program/adam/python/requirements.txt`.
The same runner stages ODM, builds SDTM followed by ADaM, exports submission
files and checks source trace, keys, subjects, XPT and Define-XML.
