# Execution evidence

The full runner generates `run.json`, `audit.json`, `odm.log`, per-dataset
stage logs and yamaa CSV run reports here. A failed run replaces old success
evidence with a failed manifest. A successful run records source coverage,
engine information, dataset dimensions, Define-XML checks and audit status.

`audit.json` separates source/lineage integrity checks from unresolved
clinical-data queries. A passed audit does not resolve those queries or
establish submission readiness. All human review statuses start not reviewed.

Logs are included in the CI `cart-t-review` artifact and are not committed.
