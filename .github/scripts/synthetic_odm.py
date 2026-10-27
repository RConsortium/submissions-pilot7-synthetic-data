"""Lossless, structural ODM 2.0 staging for synthetic-study yamaa inputs.

This adapter copies collected ItemData values into group-wise CSV files. It
does not impute dates, assign units, derive endpoints, or create subjects.
Source order and exact ItemOID/event/repeat identifiers are retained.
"""

import argparse
import collections
import csv
import json
from pathlib import Path
import tarfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PREFIX = ["STUDYID", "USUBJID", "SRCSEQ", "EVENTOID", "EVENTREP",
          "GROUPOID", "GROUPREP", "VISIT", "VISITNUM"]


def local(element):
    return element.tag.rsplit("}", 1)[-1]


def collected_value(item):
    if "Value" in item.attrib:
        return item.attrib["Value"]
    values = [child.text or "" for child in item if local(child) == "Value"]
    if len(values) > 1:
        raise ValueError(f"Multiple values for {item.get('ItemOID')}")
    return values[0] if values else (item.text or "").strip()


def definitions(element):
    items, groups, events = {}, {}, {}
    for child in element:
        kind, oid = local(child), child.get("OID")
        if kind == "ItemDef":
            items[oid] = {
                "name": oid.rsplit(".", 1)[-1],
                "label": child.get("Name"), "data_type": child.get("DataType"),
                "description": " ".join(
                    x.text or "" for x in child.iter() if local(x) == "TranslatedText"
                ),
            }
        elif kind == "ItemGroupDef" and oid.startswith("IG."):
            groups[oid] = {
                "name": oid.rsplit(".", 1)[-1],
                "items": [x.get("ItemOID") for x in child if local(x) == "ItemRef"],
            }
        elif kind == "StudyEventDef":
            events[oid] = {"name": child.get("Name"), "number": len(events) + 1}
    for group in groups.values():
        names = [items[oid]["name"] for oid in group["items"]]
        if len(names) != len(set(names)) or set(names).intersection(PREFIX):
            raise ValueError(f"Ambiguous group fields: {group['name']}")
    return items, groups, events


def stage(study, root=ROOT):
    base = root / study
    archive_path = base / "data/odm" / f"{study}_odm.tar.gz"
    destination = base / "data/odm/extracted"
    destination.mkdir(parents=True, exist_ok=True)
    handles, writers = {}, {}
    counts, missing = collections.Counter(), collections.Counter()
    subjects = set()
    values = collections.defaultdict(collections.Counter)
    items, groups, events = {}, {}, {}
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            members = [m for m in archive if m.isfile() and
                       Path(m.name).name == "odm.xml"]
            if len(members) != 1:
                raise ValueError("Expected exactly one clinical ODM XML member")
            member = members[0]
            source = archive.extractfile(member)
            studyid = None
            for event, element in ET.iterparse(source, events=("start", "end")):
                kind = local(element)
                if event == "start":
                    if kind == "Study":
                        studyid = element.get("OID").removeprefix("ST.")
                    continue
                if kind == "MetaDataVersion":
                    items, groups, events = definitions(element)
                    for oid, group in groups.items():
                        handle = (destination / f"{group['name'].lower()}.csv").open(
                            "w", encoding="utf-8", newline=""
                        )
                        handles[oid] = handle
                        writers[oid] = csv.DictWriter(
                            handle, fieldnames=PREFIX +
                            [items[item]["name"] for item in group["items"]]
                        )
                        writers[oid].writeheader()
                    element.clear()
                elif kind == "SubjectData":
                    subject = element.get("SubjectKey")
                    if subject in subjects:
                        raise ValueError(f"Duplicate subject snapshot: {subject}")
                    subjects.add(subject)
                    sequences = collections.Counter()
                    for visit in element:
                        if local(visit) != "StudyEventData":
                            continue
                        eventoid = visit.get("StudyEventOID")
                        for group in visit.iter():
                            oid = group.get("ItemGroupOID")
                            if local(group) != "ItemGroupData" or oid not in groups:
                                continue
                            sequences[oid] += 1
                            row = dict(zip(PREFIX, [
                                studyid, subject, sequences[oid], eventoid,
                                visit.get("StudyEventRepeatKey", ""), oid,
                                group.get("ItemGroupRepeatKey", ""),
                                events[eventoid]["name"], events[eventoid]["number"],
                            ]))
                            for item in group:
                                if not local(item).startswith("ItemData"):
                                    continue
                                itemoid = item.get("ItemOID")
                                if itemoid not in groups[oid]["items"]:
                                    raise ValueError(f"Undeclared item {itemoid}")
                                name = items[itemoid]["name"]
                                if name in row:
                                    raise ValueError(f"Duplicate collected item {itemoid}")
                                row[name] = collected_value(item)
                                if len(values[itemoid]) < 30 or row[name] in values[itemoid]:
                                    values[itemoid][row[name]] += 1
                            writers[oid].writerow(row)
                            counts[oid] += 1
                            for itemoid in groups[oid]["items"]:
                                if row.get(items[itemoid]["name"], "") == "":
                                    missing[itemoid] += 1
                    element.clear()
    finally:
        for handle in handles.values():
            handle.close()
    record = {
        "schema_version": 1, "study": study, "studyid": studyid,
        "archive": archive_path.relative_to(root).as_posix(),
        "archive_member": member.name, "subjects": len(subjects),
        "items": items, "groups": groups, "events": events,
        "group_counts": dict(counts), "missing": dict(missing),
        "value_samples": {key: dict(value) for key, value in values.items()},
        "adapter": "Structural copy only; no clinical derivations or imputations.",
    }
    (destination / "inventory.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", choices=("kn189", "kn564"))
    args = parser.parse_args()
    result = stage(args.study)
    print(f"{args.study}: {result['subjects']} subjects; "
          f"{sum(result['group_counts'].values())} collected group records")
