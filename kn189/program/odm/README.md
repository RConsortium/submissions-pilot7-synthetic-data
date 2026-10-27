# Structural ODM staging

Run `.github/scripts/synthetic_odm.py kn189` from the repository root.
The common adapter writes lossless group-wise CSVs and an inventory under
`data/odm/extracted/`. It preserves numeric text and event/repeat identifiers;
it performs no clinical derivations. The original archive is not changed.

The complete runner stages these files before executing yamaa.
