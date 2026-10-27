#!/usr/bin/env python3
"""Reproduce issue #98 findings against archived and standardized datasets."""

from collections import Counter
import json
import math

import pyarrow.parquet as pq
import pyreadstat

from engine import STUDY


FIELDS = {
    "adsl": ("TRTSDT", "TRTEDT", "TRTDURD", "EOSSTT", "DCDECOD", "SAFFL",
             "TRT01P", "TRT01A", "DTHFL", "DTHDT"),
    "adae": ("TRTSDT", "ASTDT", "ASTDY", "TRTEMFL", "AESER", "AEACN",
             "AESDTH", "AEOUT"),
    "adds": ("DSCAT", "DSDECOD"),
    "adlb": ("ABLFL", "BASE", "CHG", "PCHG"),
}


def missing(value):
    return value is None or value == "" or (
        isinstance(value, float) and math.isnan(value))


def distribution(rows, column):
    return dict(sorted(Counter(
        "<missing>" if missing(row.get(column)) else str(row[column])
        for row in rows).items()))


def metrics(datasets):
    result = {}
    for domain, (rows, columns) in datasets.items():
        fields = {}
        for column in FIELDS[domain]:
            count = sum(not missing(row.get(column)) for row in rows)
            fields[column] = {"column_present": column in columns,
                              "nonmissing": count, "missing": len(rows) - count}
            if column in ("EOSSTT", "DCDECOD", "SAFFL", "TRT01P", "TRT01A",
                          "TRTEMFL", "AESER", "AEACN", "AESDTH", "AEOUT",
                          "DSCAT", "DSDECOD", "ABLFL"):
                fields[column]["values"] = distribution(rows, column)
        result[domain] = {"rows": len(rows),
                          "subjects": len({row["USUBJID"] for row in rows}),
                          "fields": fields}
    events = Counter(row["USUBJID"] for row in datasets["adae"][0])
    result["adae"]["subjects_with_multiple_events"] = sum(n > 1 for n in events.values())
    results = Counter((row["USUBJID"], row["PARAMCD"]) for row in datasets["adlb"][0])
    result["adlb"]["subject_parameter_pairs"] = len(results)
    result["adlb"]["pairs_with_multiple_results"] = sum(n > 1 for n in results.values())
    return result


def verify(study=STUDY):
    current, archive = {}, {}
    for domain in FIELDS:
        table = pq.read_table(study / "data/adam" / f"{domain}-yamaa.parquet")
        current[domain] = (table.to_pylist(), table.column_names)
        old = study.parent / ".archieve/cart-t/data/adam" / f"{domain}.xpt"
        if old.is_file():
            frame, _ = pyreadstat.read_xport(old, disable_datetime_conversion=True)
            archive[domain] = (frame.to_dict("records"), frame.columns.tolist())
    now = metrics(current)
    before = metrics(archive) if set(archive) == set(FIELDS) else None
    adsl, adae, adds, adlb = (current[name][0] for name in FIELDS)
    disposition = {}
    for row in adds:
        if row["DSCAT"] == "DISPOSITION EVENT":
            disposition.setdefault(row["USUBJID"], []).append(row)
    checks = []

    def require(name, passed):
        checks.append({"check": name, "passed": bool(passed)})

    require("milestones_excluded_from_adsl_disposition", all(
        (missing(row["DCDECOD"]) and row["EOSSTT"] == "UNKNOWN")
        if row["USUBJID"] not in disposition else
        row["DCDECOD"] in {event["DSDECOD"] for event in disposition[row["USUBJID"]]}
        for row in adsl))
    require("explicit_discontinuations_retained", all(
        row["EOSSTT"] == "DISCONTINUED" for row in adsl
        if row["DCDECOD"] in ("ADVERSE EVENT", "WITHDRAWAL BY SUBJECT")))
    require("multiple_ae_instances_retained", now["adae"]["subjects_with_multiple_events"] > 0)
    ae = pq.read_table(study / "data/sdtm/ae.parquet").to_pylist()
    require("adae_matches_all_ae_keys", Counter(
        (row["USUBJID"], row["AESEQ"]) for row in adae) == Counter(
        (row["USUBJID"], row["AESEQ"]) for row in ae))
    require("ae_presence_does_not_assign_safety_population", all(
        row["SAFFL"] == "N" and missing(row["TRT01A"]) for row in adsl))
    require("no_invented_treatment_timing_or_emergence", all(
        missing(row[column]) for rows, columns in (
            (adsl, ("TRTSDT", "TRTEDT", "TRTDURD")),
            (adae, ("TRTSDT", "ASTDY", "TRTEMFL"))) for row in rows for column in columns))
    require("repeated_laboratory_results_retained", now["adlb"]["pairs_with_multiple_results"] > 0)
    require("no_unsupported_laboratory_baseline", all(
        missing(row[column]) for row in adlb for column in ("ABLFL", "BASE", "CHG", "PCHG")))
    findings = [
        {"finding": "1. Treatment dates", "status": "blocked_by_source",
         "evidence": now["adsl"]["fields"],
         "assessment": "Exposure is absent from ODM. Treatment dates, duration and relative days remain missing."},
        {"finding": "2. Treatment-emergent flag", "status": "blocked_by_source",
         "evidence": now["adae"]["fields"]["TRTEMFL"],
         "assessment": "No approved risk window or documented treatment start supports TRTEMFL."},
        {"finding": "3. Disposition", "status": "corrected_with_source_limits",
         "evidence": {"adsl": {key: now["adsl"]["fields"][key] for key in ("EOSSTT", "DCDECOD")},
                      "adds": now["adds"]},
         "assessment": "Only explicit disposition events feed ADSL. Unsupported archived completion/screen-failure records are removed; missing terminal status is UNKNOWN."},
        {"finding": "4. One AE per safety subject", "status": "corrected",
         "evidence": {key: now["adae"][key] for key in ("rows", "subjects", "subjects_with_multiple_events")},
         "assessment": "Repeated AE instances are retained and AE presence no longer defines SAFFL. An approved safety denominator is still unavailable."},
        {"finding": "5. Safety population", "status": "partially_addressed",
         "evidence": now["adsl"]["fields"]["SAFFL"],
         "assessment": "AE-based safety membership and phenotype-as-treatment are removed. N means documented exposure is unavailable, not that every subject was untreated."},
        {"finding": "6. Safety fields and laboratory baseline", "status": "partially_addressed",
         "evidence": {"safety_fields": {key: now["adae"]["fields"][key] for key in ("AESER", "AEACN", "AESDTH", "AEOUT")},
                      "death_flag": now["adsl"]["fields"]["DTHFL"], "adlb": now["adlb"]},
         "assessment": "Recorded AE actions/death criteria and repeated labs are restored. Missing safety values, contradictory death evidence and baseline definitions still need resolution; DTHFL is not supplied."},
    ]
    report = {"issue": "https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/98",
              "overall": "partially_addressed", "close_issue": False,
              "scope": "Dataset standardization and data-quality verification",
              "checks_status": "passed" if all(item["passed"] for item in checks) else "failed",
              "checks": checks, "archived": before, "standardized": now,
              "findings": findings, "submission_ready": False}
    (study / "log").mkdir(exist_ok=True)
    (study / "log/issue-98.json").write_text(json.dumps(report, indent=2) + "\n")
    if report["checks_status"] != "passed":
        raise ValueError("Issue #98 regression: " + ", ".join(
            item["check"] for item in checks if not item["passed"]))
    return {key: report[key] for key in ("overall", "close_issue", "checks_status")}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
