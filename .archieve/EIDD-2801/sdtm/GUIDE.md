# SDTM derivation guide — EIDD-2801-1001-UK

Each `derive_<domain>.R` reconstructs one SDTM domain from the raw EDC forms the
generator writes to `../edc/forms/`. This mirrors the cdiscpilot1 environment,
adapted for a forward-simulated study: there is **no canonical SDTM truth**, so
there is no round-trip oracle — the derivations *are* the ground-truth mapping,
and the stage output is the conformant XPT + Define-XML that `export_conformant.py`
produces.

## Where things are
- `../edc/forms/<form>.csv` — raw CRF extract, one row per filled form record,
  columns = collected CRF field names (`read_form("vital_sign")`).
- `../edc/forms/subjects.csv` — subject registration / demographics + the
  per-subject Day-1 reference date (`subjects_tbl()`, `ref_dates()`).
- `../edc/lookups/visit_schedule.csv` — VISITCD → VISIT / VISITNUM / VISITDY.
- `common.R` — shared helpers (source it; do not edit per-domain).
- `sdtm-derived/` — outputs: `<domain>.csv` (+ `xpt/*.xpt` + `define.xml`).

## Contract
Define `derive_<domain>()` returning a data frame: exactly the SDTM columns in
order, one row per record, arranged by `USUBJID, <domain>SEQ`. Do not write files
(run_all.R does). Register the domain in `run_all.R`'s `REG` list.

## common.R API
- `read_form(name)` / `read_look(name)` — read a raw form / lookup as all-character (NA → "").
- `subjects_tbl()` — the subject registration table; `ref_dates()` → USUBJID → Day-1 ISO date.
- `parse_crf_date("15/Oct/2025")` → Date; `iso_dtc(date, "HH:MM")` → ISO-8601 `--DTC`.
- `study_day(dtc, ref_iso)` — SDTM `--DY` (ref day = 1, no day 0).
- `epoch_of(visitnum)` — SCREENING (V1) / TREATMENT / FOLLOW-UP (V7) for the single-dose design.
- `real_value(x)` — drop blanks and bare unit tokens (e.g. ECG "ms"); `as_number_chr(x)` → numeric or "".
- `add_seq(df, "VSSEQ")` — 1..n `--SEQ` within USUBJID (arrange first); `finalize(df, cols)` — stringify, NA→"", select in order.

## Conventions (study 2020-001407-17-00)
- `STUDYID = "2020-001407-17-00"`, `DOMAIN = "<DOM>"`, `USUBJID` from the forms.
- `VISITNUM` / `VISIT` come through on every raw form row.
- Dates collected as `DD/MMM/YYYY` (+ `HH:MM`) → ISO `--DTC` via `parse_crf_date` + `iso_dtc`.
- Standardized results: numeric `--STRESN` = `as_number_chr(--ORRES)`, `--STRESC` = `--ORRES`.
- `EPOCH` added to every observation via `epoch_of(VISITNUM)`.

## Run
```sh
Rscript sdtm/run_all.R            # all domains -> sdtm-derived/*.csv
Rscript sdtm/run_all.R vs lb      # only the named domains
python3 sdtm/export_conformant.py # -> sdtm-derived/xpt/*.xpt + define.xml
```

## Domains
DM, SV, IE, EX, VS, EG, LB, PC, PE, ML. (IE emits rows only for subjects flagged
ineligible, so it may be empty for a given seed. PC is a biospecimen-collection
log — no assayed concentration — so PCORRES is blank.)
