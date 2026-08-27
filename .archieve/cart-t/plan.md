# CAR-T ODM Loader — Plan & Findings

## Goal

Translate the Python ODM XML loader at
[`elong0527/demo-cdisc-yaml/src/odm/load.py`](https://github.com/elong0527/demo-cdisc-yaml/blob/main/src/odm/load.py)
into idiomatic R, and stand up a reproducible project environment to run it
against `car-t-openclinica.xml`.

## What was delivered

### 1. `program/sdtm/ut_load_xml.R`

Four functions, mirroring the Python module:

| Function | Purpose |
|---|---|
| `remove_namespaces(xml_content)` | Strips `xmlns="..."` declarations and namespace prefixes from tag/attribute names so XPath stays simple. Regex translated 1:1 from Python. |
| `get_struct_columns(df)`         | Returns names of list-columns whose elements are named lists — the R analogue of a Polars `Struct` column. |
| `odm_xml_to_df_dict(file_path)`  | Walks `ClinicalData > SubjectData > StudyEventData > FormData > ItemGroupData > ItemData`. Returns a tibble with one row per `ItemData` and six list-columns: `study`, `subject`, `event`, `form`, `item_group`, `item`. Attribute names duplicated across levels are prefixed with the level name (e.g. `status` in `subject` becomes `subject_status`); all names are lowercased. |
| `odm_xml_to_df(file_path)`       | Flattens the six list-columns via `tidyr::unnest_wider`. |

### 2. Project environment (renv via pak)

- Bootstrapped `pak` from the r-lib repo (binary install, no curl needed).
- `pak::pak("renv")` to install renv.
- `renv::init(bare = TRUE)` scaffolded `renv/`, `.Rprofile`, `renv.lock`.
- `renv::install(c("xml2", "tibble", "tidyr", "dplyr"))` installed deps and
  their transitive closure (21 packages total).
- `renv::snapshot(prompt = FALSE)` wrote the lockfile.

### 3. New folders

- `data/raw/` — empty; intended landing zone for source XML / extracts.
- `program/raw/` — empty; intended for raw-data ingestion scripts.

> Open question: should `car-t-openclinica.xml` move from the project root
> into `data/raw/`, and should `ut_load_xml.R` move from `program/sdtm/` to
> `program/raw/`? Left in original locations pending confirmation.

## Verification

Ran end-to-end against `car-t-openclinica.xml` (9.3 MB, 16 ClinicalData / 1,620
SubjectData / 4,470 StudyEventData / 6,646 FormData / 17,918 ItemGroupData /
48,557 ItemData):

```
nrow(df_dict) = 48557   ncol = 6
nrow(df)      = 48557   ncol = 34
```

Flat column names include the expected level-prefixed duplicates:
`subject_status`, `event_status`, `form_status`, `event_workflowstatus`,
`form_workflowstatus`, `event_removed`, `item_group_removed`,
`form_sdvstatus`, `item_sdvstatus`.

Runtime: ~2 minutes per call on the full file. Acceptable for a one-shot
load; would need optimization for a hot path.

## Key technical findings

- **`xml2::xml_parent()` on a nodeset deduplicates** rather than returning a
  parallel-by-position nodeset. The first implementation walked five parent
  levels from the `ItemData` nodeset and got mismatched column lengths
  (8 vs. 810 vs. 48,557). Replaced with a top-down nested walk that mirrors
  the Python `findall` structure — also closer to the original by design.
- **Polars `Struct` ↔ R named-list list-column.** Each row's `study` /
  `subject` / etc. is a `list(name = value, ...)`, and `tidyr::unnest_wider`
  expands it. Renaming for duplicate fields happens **before** unnesting, so
  no collision in the flat tibble.
- **Regex parity.** Python raw strings (`r"\s*..."`) map to R double-escaped
  `perl = TRUE` patterns (`"\\s*..."`); single-quoted `xmlns` declarations
  handled separately from double-quoted ones, same as the Python.
- **Batching for performance.** Instead of growing a row-at-a-time records
  list (O(N) appends), the walk emits one mini-tibble per `ItemGroupData`
  (~17,918 chunks, average ~2.7 items each) and `dplyr::bind_rows` at the
  end.

## Files touched / created

```
cart-t/
  .Rprofile                       (new, by renv::init)
  renv/                           (new, by renv::init)
  renv.lock                       (new, by renv::snapshot)
  data/raw/                       (new, empty)
  program/raw/                    (new, empty)
  program/sdtm/ut_load_xml.R      (new — the loader)
  plan.md                         (this file)
```

## How to use

```r
source("program/sdtm/ut_load_xml.R")

# Hierarchical: six list-columns
df_dict <- odm_xml_to_df_dict("car-t-openclinica.xml")

# Flattened: 34 atomic columns
df <- odm_xml_to_df("car-t-openclinica.xml")
```
