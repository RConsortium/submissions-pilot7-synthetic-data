# Execution evidence

The full runner generates `run.json`, `audit.json`, `odm.log` and per-dataset
stage logs here. Native yamaa run reports are also Parquet files here,
named `<domain>-report.parquet`. A failed run replaces old success
evidence with a failed manifest. A successful run records source coverage,
engine information, dataset dimensions, Define-XML checks and audit status.

`audit.json` separates source/lineage integrity checks from unresolved
clinical-data queries. A passed audit does not resolve those queries or
establish submission readiness. All human review statuses start not reviewed.

`issue-98.json` records a reproducible assessment of every finding in
[issue #98](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/98).
It distinguishes corrected standardization defects from source-data blockers.
See `spec/review/issue-98.md` for interpretation and remaining work.

Logs are included in the CI `cart-t-standardization` artifact and are not committed.
