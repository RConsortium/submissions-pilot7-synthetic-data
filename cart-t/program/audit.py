"""Independent source reconciliation, dataset lineage and data-quality queries."""

from collections import Counter, defaultdict
import csv
import json
import math
import xml.etree.ElementTree as ET

import pyarrow.parquet as pq
import pyreadstat

from engine import STUDY, specifications


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def tables():
    result = {}
    for section in ("sdtm", "adam"):
        for path, spec in specifications(section):
            artifact = (path.parent / spec["output"]["path"]).resolve()
            result[spec["domain"]] = {
                "section": section, "spec": spec, "spec_path": path,
                "artifact": artifact, "rows": pq.read_table(artifact).to_pylist(),
            }
    return result


def source_items():
    """Independent XML walk: no native reader or extraction helper is used.

    A full item projection proves that extraction neither lost nor changed a
    clinical value, including blanks, null flags, repeat keys and site IDs.
    """
    ns = "{http://www.cdisc.org/ns/odm/v1.3}"
    document = ET.parse(STUDY / "data/odm/car-t-openclinica.xml")
    def attrs(node):
        return {key.rsplit("}", 1)[-1]: value for key, value in node.attrib.items()}
    records = []
    for clinical in document.getroot().findall(ns + "ClinicalData"):
        for subject in clinical.findall(ns + "SubjectData"):
            for event in subject.findall(ns + "StudyEventData"):
                for form in event.findall(ns + "FormData"):
                    for group in form.findall(ns + "ItemGroupData"):
                        for item in group.findall(ns + "ItemData"):
                            values = {}
                            for node in (clinical, subject, event, form, group, item):
                                values.update(attrs(node))
                            records.append(values)
    return records


def equal_value(left, right):
    if left is None or right is None:
        return left is right
    if isinstance(left, float) and isinstance(right, (float, int)):
        return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)
    return left == right


def audit():
    datasets = tables()
    staged_groups = read_csv(STUDY / "data/odm/groups.csv")
    # Form tables hold raw item values as well as complete instance keys.
    raw_records = {}
    for info in json.loads((STUDY / "data/odm/inventory.json").read_text())["forms"].values():
        for row in read_csv(STUDY / "data/odm" / info["file"]):
            raw_records[row["ROWID"]] = row
    issues, checks = [], []
    def require(name, condition, detail):
        checks.append({"check": name, "passed": bool(condition), "details": detail})
    def query(code, domain, variable, count, detail, severity="review", sample=None):
        if count:
            issues.append({"code": code, "dataset": domain, "variable": variable,
                           "count": int(count), "severity": severity, "details": detail,
                           "sample": sample or [], "review_status": "not_reviewed"})

    original = source_items()
    native = read_csv(STUDY / "data/odm/items.csv")
    fields = ["StudyOID", "MetaDataVersionOID", "SubjectKey", "StudyEventOID",
              "StudyEventRepeatKey", "FormOID", "FormRepeatKey", "ItemGroupOID",
              "ItemGroupRepeatKey", "ItemOID", "ItemName", "Value"]
    require("xml_items_preserved", len(original) == len(native) and all(
        all((a.get(k) or "") == (b.get(k) or "") for k in fields) and
        ("Value" in a) == (b["ValuePresent"] == "true") and
        (a.get("IsNull", "false").lower() in ("yes", "true", "1")) == (b["IsNull"] == "true")
        for a, b in zip(original, native)), f"Compared {len(original)} XML items in source order.")
    require("all_subjects_in_dm", len(datasets["DM"]["rows"]) == len(
        {(r["StudyOID"], r["SubjectKey"]) for r in original}), "All XML subjects must be retained.")
    source_ids = {str(i + 1) for i in range(len(original))}
    group_ids = {r["ROWID"] for r in staged_groups}
    for domain, data in datasets.items():
        spec, rows = data["spec"], data["rows"]
        keys = spec["keys"]
        identity = [tuple(r.get(k) for k in keys) for r in rows]
        require(f"{domain}_keys", len(identity) == len(set(identity)) and
                all(all(v is not None for v in k) for k in identity), str(keys))
        if data["section"] == "sdtm" and domain not in ("DM", "SUPPDM"):
            spid = domain + "SPID"
            ids = source_ids if domain in ("LB", "QS") else group_ids
            require(f"{domain}_source_links", all(r[spid] in ids for r in rows),
                    "Every record must point to an original item or complete group instance.")
            for column in spec["columns"]:
                expression = column.get("derivation")
                if isinstance(expression, dict) and "value" in expression:
                    expression = expression["value"]
                if not isinstance(expression, dict) or "mapping" not in expression:
                    continue
                operation = expression["mapping"]
                variable = operation["source"]
                if isinstance(variable, dict):
                    variable = variable["variable"]
                if not isinstance(variable, str) or not variable.startswith("SRC.I_"):
                    continue
                field = variable.split(".", 1)[1]
                unmapped = [r for r in rows if raw_records.get(r[spid], {}).get(field)
                            not in (None, "") and raw_records[r[spid]][field]
                            not in operation["dict"]]
                query("unmapped_source_code", domain, column["name"], len(unmapped),
                      f"A present source value in {field} has no approved mapping. It remains in the raw source and is not silently assigned a clinical code.",
                      sample=[r["USUBJID"] for r in unmapped[:5]])
        # In historical metadata these requirements are declarations, not
        # runtime assertions. Audit every declared mandatory column explicitly.
        for column in spec["columns"]:
            name = column["name"]
            if name not in spec["output"]["columns"]:
                continue
            missing = [r for r in rows if r.get(name) in (None, "")]
            if column.get("submission", {}).get("mandatory"):
                query("missing_required_value", domain, name, len(missing),
                      "Target metadata declares this variable mandatory. Data need resolution before submission.",
                      "blocking", [r["USUBJID"] for r in missing[:5]])
        if domain in ("ADLB", "ADQS"):
            parameters = defaultdict(set)
            for row in rows:
                parameters[row["PARAMCD"]].add((row["PARAM"], row["PARAMN"]))
            require(f"{domain}_parameter_identity", all(len(v) == 1 for v in parameters.values()),
                    "PARAM and PARAMN must be a function of PARAMCD across the entire dataset.")
        if data["section"] == "adam" and domain != "ADSL":
            donor = datasets[rows[0]["SRCDOM"]]["rows"] if rows else []
            seqname = rows[0]["SRCDOM"] + "SEQ" if rows else ""
            lookup = {(r["USUBJID"], r[seqname]): r for r in donor}
            valid = len(rows) == len(donor)
            for row in rows:
                source = lookup.get((row["USUBJID"], row["SRCSEQ"]))
                valid = valid and source is not None
                if source:
                    common = source.keys() & row.keys()
                    valid = valid and all(equal_value(source[n], row[n]) for n in common)
                    if "AVAL" in row:
                        valid = valid and equal_value(row["AVAL"], source[row["SRCVAR"]])
            require(f"{domain}_sdtm_lineage", valid,
                    "One analysis record per SDTM record; copied values and AVAL agree with the linked source.")
        start, end = next(((a, b) for a, b in [
            ("AESTDTC", "AEENDTC"), ("CMSTDTC", "CMENDTC"),
            ("MHSTDTC", "MHENDTC")] if a in spec["output"]["columns"]), (None, None))
        if start and data["section"] == "sdtm":
            inversions = [r for r in rows if r.get(start) and r.get(end) and
                          len(r[start]) == len(r[end]) == 10 and r[end] < r[start]]
            query("inverted_dates_retained", domain, end, len(inversions),
                  "Recorded end is before start. Neither date is overwritten; analysis duration stays missing.",
                  sample=[r["USUBJID"] for r in inversions[:5]])

    # Expected counts are independently enumerated from XML, with item names
    # corresponding to actual clinical content rather than output values.
    nonblank = lambda r: r.get("Value") not in (None, "")
    criteria = {
        "AE": lambda r: r.get("FormName") == "Adverse Event" and r.get("ItemName") == "AETERM",
        "CE": lambda r: r.get("FormName") == "Suspected MI" and r.get("ItemName") == "DESC",
        "LB": lambda r: r.get("FormName") in ("2. Baseline Labs and Imaging", "Lab Results") and
            r.get("ItemName") in ("AMYLASE", "BUN", "CHLORIDE", "HOMOC", "CREAT", "EGFR",
                                  "CHOLES", "TRIG", "HEMA", "HEMO", "RBC", "WBC"),
        "QS": lambda r: r.get("FormName") == "RAND SF-12 Survey" and r.get("ItemName") in
            [f"Q{i}" for i in range(1, 13)] + ["PF-S", "RP-S", "BP", "GH", "VT", "SF", "RE-S", "ME-S"],
        "IE": lambda r: r.get("FormName") == "Eligibility" and r.get("ItemName") in
            ("INC1EVAL", "INC2EVAL", "EXCEVAL") and r.get("Value") == "fail",
    }
    for domain, predicate in criteria.items():
        expected = sum(predicate(r) and nonblank(r) for r in original)
        require(f"{domain}_xml_record_reconciliation", expected == len(datasets[domain]["rows"]),
                f"XML observations {expected}; output records {len(datasets[domain]['rows'])}.")
    for domain in ("LB", "QS"):
        require(f"{domain}_verbatim_values", all(
            original[int(r[domain + "SPID"]) - 1]["Value"] == r[domain + "ORRES"]
            for r in datasets[domain]["rows"]), "Every original result, including nonnumeric text, is preserved.")
    dm = {r["USUBJID"]: r for r in datasets["DM"]["rows"]}
    adsl = {r["USUBJID"]: r for r in datasets["ADSL"]["rows"]}
    recorded_sex = defaultdict(set)
    sex_codes = {"1": "M", "2": "F", "M": "M", "F": "F", "Male": "M", "Female": "F"}
    for raw in raw_records.values():
        if raw["FORMNAME"] not in ("Eligibility", "1. Demographics and History"):
            continue
        for field in ("I_PTSEX", "I_PTSEXEL", "I_PSEX"):
            if raw.get(field) in sex_codes:
                recorded_sex[raw["SUBJECTKEY"]].add(sex_codes[raw[field]])
    conflicts = ["CART-T-PILOT-" + key for key, values in recorded_sex.items() if len(values) > 1]
    query("conflicting_sex_sources", "DM", "SEX", len(conflicts),
          "Recorded sex differs across demographic/eligibility items. The declared precedence is applied, but the source conflict still requires review.",
          sample=conflicts[:5])
    require("adsl_subject_universe", dm.keys() == adsl.keys(), "ADSL and DM have exactly the same subjects.")
    profile_subjects = {r["SubjectKey"] for r in original if r.get("FormName") == "3. Randomize"
                        and r.get("ItemName") == "PROFILE" and nonblank(r)}
    require("randomization_flag_uses_record_not_date", {r["USUBJID"] for r in adsl.values()
            if r["RANDFL"] == "Y"} == {"CART-T-PILOT-" + k for k in profile_subjects},
            "A missing administrative event date must not remove a recorded phenotype from RANDFL.")
    require("no_exposure_from_ae_presence", all(r["SAFFL"] == "N" and r["TRTSDT"] is None
            and r["TRT01A"] is None for r in adsl.values()), "AE presence does not establish treatment.")
    require("no_invented_analysis_baselines", all(
        all(r[n] is None for n in ("ABLFL", "BASE", "CHG", "PCHG"))
        for d in ("ADLB", "ADQS") for r in datasets[d]["rows"]),
        "No analysis baseline or change is manufactured without a reference and approved definition.")
    query("exposure_not_documented", "ADSL", "SAFFL", len(adsl),
          "The export supplies no exposure records. Only two disposition forms answer RECEIVEDINTERVENTION=No; absence elsewhere is not proof of no treatment.", "blocking")
    query("analysis_plan_not_supplied", "ADSL", "ITTCAND", len(profile_subjects),
          "RANDFL is a workflow proxy and ITTCAND is a review candidate. Approve populations, allocation, baseline and endpoints before analyses.", "blocking")
    query("unverified_crf_units", "LB", "LBORRESU", len(datasets["LB"]["rows"]),
          "Fixed units follow the archived form specification. Confirm against a controlled CRF or lab transfer specification.")
    query("source_scores_not_recomputed", "QS", "QSSTRESN",
          sum(r["QSSCAT"] == "SUBSCALE" for r in datasets["QS"]["rows"]),
          "Recorded RAND SF-12 subscales are retained. The scoring algorithm and instrument/CT release were not supplied.")
    # Audit nonnumeric original results without modifying the original text.
    for domain in ("LB", "QS"):
        invalid = [r for r in datasets[domain]["rows"] if r[domain + "STRESN"] is None]
        query("nonnumeric_result", domain, domain + "STRESN", len(invalid),
              "Original text is retained; numeric result is missing. Review before numeric analysis.",
              sample=[r["USUBJID"] for r in invalid[:5]])
        no_date = [r for r in datasets[domain]["rows"] if r[domain + "DTC"] is None]
        query("collection_timing_unavailable", domain, domain + "DTC", len(no_date),
              "Collection date or administrative timing proxy is missing or cannot be parsed under the declared date forms. No replacement date is invented.",
              sample=[r["USUBJID"] for r in no_date[:5]])
    no_randomization_date = [r for r in adsl.values() if r["RANDFL"] == "Y" and r["RANDDT"] is None]
    query("randomization_timestamp_unavailable", "ADSL", "RANDDT", len(no_randomization_date),
          "A phenotype is recorded but its administrative event date is unavailable. RANDFL retains the workflow evidence.",
          sample=[r["USUBJID"] for r in no_randomization_date[:5]])
    disagreements = [r for r in datasets["AE"]["rows"] if
                     (r.get("AEOUT") == "FATAL") != (r.get("AESDTH") == "Y")]
    query("fatal_outcome_disagreement", "AE", "AEOUT", len(disagreements),
          "Outcome and death seriousness criterion disagree. Source values were not forced to agree.",
          sample=[r["USUBJID"] for r in disagreements[:5]])

    # The archive is an independently retained previous implementation, not
    # an official reference. Count differences are evidence, never pass claims.
    legacy = []
    reasons = {
        "DM": "Preserve source site and subject identity; remove proxy consent and allocation.",
        "AE": "Retain complete event instances and original safety qualifiers; no invented MedDRA coding.",
        "CM": "Retain complete event instances and original dates; include CMTRTLX fallback.",
        "LB": "Preserve event repeats; do not interpret separate events as corrections.",
        "QS": "Include actual PF-S/RP-S/RE-S/ME-S item names; no manufactured baseline.",
        "MH": "Preserve all source history instances and distinct cancer type/subtype meanings.",
        "IE": "Use explicit failed evaluations only.",
        "CE": "Retain verbatim reported events and questionable dates for review.",
        "DS": "Remove inferred consent, eligibility, completion and screen failures.",
    }
    for domain, data in datasets.items():
        previous = STUDY.parent / ".archieve/cart-t/data" / data["section"] / (domain.lower() + ".xpt")
        if previous.is_file():
            frame, _ = pyreadstat.read_xport(previous, disable_datetime_conversion=True)
            base = domain[2:] if domain.startswith("AD") and domain != "ADSL" else domain
            legacy.append({"dataset": domain, "archived_rows": len(frame),
                           "new_rows": len(data["rows"]), "agreement": "not_claimed",
                           "reason": reasons.get(base, "Subject-level population and timing rules corrected; see decisions.")})
    summary = {"status": "passed" if all(c["passed"] for c in checks) else "failed",
               "checks": checks, "quality_queries": issues, "legacy_counts": legacy,
               "submission_ready": False, "human_review": "not_reviewed",
               "blocking_queries": sum(i["severity"] == "blocking" for i in issues)}
    (STUDY / "log/audit.json").write_text(json.dumps(summary, indent=2) + "\n")
    if summary["status"] != "passed":
        raise ValueError("Source reconciliation failed: " + ", ".join(
            c["check"] for c in checks if not c["passed"]))
    return {"status": summary["status"], "checks": len(checks), "queries": len(issues),
            "blocking_queries": summary["blocking_queries"]}
