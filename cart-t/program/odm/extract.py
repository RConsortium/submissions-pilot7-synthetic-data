"""Lossless OpenClinica extraction. Clinical mappings belong in spec/yamaa.

The native reader supplies every item and its SourceOrdinal. Wide groups retain
the complete ODM instance key, including event and form repeats. No entry is
interpreted as a correction merely because it occurs later in the document.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import yamaa

STUDY = Path(__file__).resolve().parents[2]
FORM_NAMES = {
    "1. Demographics and History": "demographics",
    "2. Baseline Labs and Imaging": "baseline_labs",
    "3. Randomize": "randomization",
    "4. View Randomization Assignment": "randomization_view",
    "Eligibility": "eligibility",
    "Adverse Event": "adverse_events",
    "ConMed": "medications",
    "Lab Results": "laboratory",
    "RAND SF-12 Survey": "questionnaire",
    "Suspected MI": "clinical_events",
    "Evaluator A": "adjudicator_a",
    "Committee Review": "committee_review",
    "Disposition": "disposition",
    "Kitchen Sink": "demo",
    "Source Document": "source_documents",
    "In-clinic Photo": "photographs",
    "RxNorm Coding": "medication_coding",
}
INSTANCE_KEY = (
    "StudyOID", "MetaDataVersionOID", "SubjectKey", "StudyEventOID",
    "StudyEventRepeatKey", "FormOID", "FormRepeatKey", "FormLayoutOID",
    "ItemGroupOID", "ItemGroupRepeatKey",
)


def write_csv(path, rows, fields=None):
    rows = list(rows)
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def item_column(name):
    return "I_" + re.sub(r"[^A-Za-z0-9_]", "_", name).upper()


def extract(study=STUDY):
    destination = study / "data/odm"
    source = destination / "car-t-openclinica.xml"
    original = source.read_bytes()
    # The original is ASCII bytes with entity references. Changing only this
    # declaration makes the identical characters readable by yamaa ODM-1.
    original.decode("ascii")
    reader_copy = destination / "car-t-utf8.xml"
    reader_copy.write_bytes(original.replace(b'encoding="US-ASCII"',
                                           b'encoding="UTF-8"', 1))
    native = yamaa.read_odm(reader_copy)
    items = native.to_pylist()
    write_csv(destination / "items.csv", items)

    ns = {"o": "http://www.cdisc.org/ns/odm/v1.3"}
    document = ET.fromstring(original)
    sites = {}
    for node in document.findall("o:Study", ns):
        sites[node.get("OID")] = {
            "SITEID": node.findtext("o:GlobalVariables/o:ProtocolName", namespaces=ns),
            "SITENAME": node.findtext("o:GlobalVariables/o:StudyName", namespaces=ns),
        }

    subjects, groups, forms, names, duplicates = {}, {}, {}, {}, []
    for row in items:
        subject_key = (row["StudyOID"], row["SubjectKey"])
        subject = {
            "STUDYOID": row["StudyOID"], "SUBJECTKEY": row["SubjectKey"],
            "SUBJECTID": row["StudySubjectID"], **sites[row["StudyOID"]],
        }
        if subject_key in subjects and subjects[subject_key] != subject:
            raise ValueError(f"Conflicting subject identity: {subject_key}")
        subjects[subject_key] = subject
        instance = tuple(row[k] for k in INSTANCE_KEY)
        if instance not in groups:
            groups[instance] = {
                **subject, "ROWID": row["SourceOrdinal"],
                "EVENTOID": row["StudyEventOID"],
                "EVENTREPEAT": row["StudyEventRepeatKey"] or "1",
                "EVENTNAME": row["EventName"], "STARTDATE": row["StartDate"],
                "FORMOID": row["FormOID"], "FORMREPEAT": row["FormRepeatKey"] or "1",
                "LAYOUT": row["FormLayoutOID"], "FORMNAME": row["FormName"],
                "GROUPOID": row["ItemGroupOID"], "GROUPREPEAT": row["ItemGroupRepeatKey"],
                "IGROUP": row["ItemGroupName"],
            }
        group = groups[instance]
        column = item_column(row["ItemName"] or row["ItemOID"])
        name_key = (row["FormOID"], row["ItemGroupOID"], column)
        identity = (row["ItemOID"], row["ItemName"])
        if name_key in names and names[name_key] != identity:
            raise ValueError(f"Item names collide after identifier conversion: {name_key}")
        names[name_key] = identity
        # Refuse ambiguity within a true group, including two identical items.
        # An explicit data-management decision is needed to resolve such input.
        if column in group:
            duplicates.append({"rowid": group["ROWID"], "item": column})
        group[column] = row["Value"] if row["IsNull"] != "true" else None
        forms.setdefault(row["FormName"], {"items": 0, "subjects": set()})
        forms[row["FormName"]]["items"] += 1
        forms[row["FormName"]]["subjects"].add(subject_key)
    if duplicates:
        raise ValueError(f"Repeated items within an ODM instance: {duplicates[:5]}")
    if len({s["SUBJECTKEY"] for s in subjects.values()}) != len(subjects):
        raise ValueError("SubjectKey is not globally unique; revise study join keys")
    write_csv(destination / "subjects.csv", subjects.values())
    for form, slug in FORM_NAMES.items():
        records = [g for g in groups.values() if g["FORMNAME"] == form]
        if records:
            write_csv(destination / f"{slug}.csv", records)
    unknown = set(forms) - FORM_NAMES.keys()
    if unknown:
        raise ValueError(f"New forms require a documented extraction destination: {unknown}")
    write_csv(destination / "groups.csv", ({k: v for k, v in g.items()
                                          if not k.startswith("I_")}
                                         for g in groups.values()))
    write_csv(destination / "clinical_items.csv", (
        {**{k: v for k, v in groups[tuple(row[k] for k in INSTANCE_KEY)].items()
            if not k.startswith("I_")},
         "ITEMROW": row["SourceOrdinal"], "ITEMOID": row["ItemOID"],
         "ITEMNAME": row["ItemName"], "VALUE": row["Value"]}
        for row in items))
    write_csv(destination / "item_dictionary.csv", (
        {"FORMOID": f, "GROUPOID": g, "COLUMN": c, "ITEMOID": oid, "ITEMNAME": name}
        for (f, g, c), (oid, name) in names.items()))
    inventory = {
        "source": source.name, "odm_version": items[0]["ODMVersion"],
        "file_oid": items[0]["FileOID"], "items": native.num_rows,
        "subjects": len(subjects), "groups": len(groups),
        "native_columns": native.column_names,
        "forms": {form: {"file": FORM_NAMES[form] + ".csv", "items": info["items"],
                         "subjects": len(info["subjects"]),
                         "groups": sum(g["FORMNAME"] == form for g in groups.values())}
                  for form, info in forms.items()},
    }
    (destination / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    return inventory


if __name__ == "__main__":
    print(json.dumps(extract(), indent=2))
