"""Read the Pilot 01 Define-XML 1.0 reference without hiding its draft extension.

This is a comparison oracle, not an XML generator. Native generation uses the
authored combined YAML specifications. The data guide explicitly identifies
ADaMIG 1.0; the XML header identifies the ADaM 2.1 model.
"""

from collections import Counter, defaultdict
from decimal import Decimal
import xml.etree.ElementTree as ET

from define_metadata import local, prose, XLINK, XML

ODM = "http://www.cdisc.org/ns/odm/v1.2"
DEFINE = "http://www.cdisc.org/ns/def/v1.0"
ARM = "http://www.cdisc.org/ns/ADaMRes/DRAFT"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
CLASSES = {"ADSL": "SUBJECT LEVEL ANALYSIS DATASET",
           "ADAE": "OCCURRENCE DATA STRUCTURE", "BDS": "BASIC DATA STRUCTURE"}
GUIDE = {"Name": "ADaMIG", "Version": "1.0", "Type": "IG", "Status": "Final"}
NAMESPACES = {"o": ODM, "d": DEFINE, "a": ARM}
TYPES = {name: f"{{{ODM}}}{name}" for name in ("ItemDef", "ItemGroupDef", "CodeList")}
TYPES.update({name: f"{{{DEFINE}}}{name}" for name in ("ValueListDef", "leaf")})
ATTRIBUTES = {
    "ODM": {"FileOID", "ODMVersion", "FileType", "CreationDateTime", f"{{{XSI}}}schemaLocation"},
    "Study": {"OID"},
    "MetaDataVersion": {"OID", "Name", "Description", *[f"{{{DEFINE}}}{k}" for k in
                        ("DefineVersion", "StandardName", "StandardVersion")]},
    "ItemGroupDef": {"OID", "Name", "Repeating", "IsReferenceData", "Purpose", "Comment",
                     *[f"{{{DEFINE}}}{k}" for k in ("Label", "Structure", "DomainKeys", "Class", "ArchiveLocationID")]},
    "ItemRef": {"ItemOID", "OrderNumber", "Mandatory"},
    "ItemDef": {"OID", "Name", "DataType", "Length", "Origin", "Comment", "SignificantDigits",
                *[f"{{{DEFINE}}}{k}" for k in ("Label", "DisplayFormat", "SignificantDigits")]},
    "ValueListDef": {"OID"}, "ValueListRef": {"ValueListOID"}, "CodeListRef": {"CodeListOID"},
    "CodeList": {"OID", "Name", "DataType"}, "CodeListItem": {"CodedValue", f"{{{DEFINE}}}Rank"},
    "ExternalCodeList": {"Dictionary", "Version"}, "TranslatedText": {f"{{{XML}}}lang"},
    "DocumentRef": {"leafID"}, "leaf": {"ID", f"{{{XLINK}}}href"},
    **{name: set() for name in ("GlobalVariables", "StudyName", "StudyDescription", "ProtocolName",
                               "SupplementalDoc", "title", "Decode")},
}
DEFINE_TAGS = {"SupplementalDoc", "DocumentRef", "leaf", "title", "ValueListDef", "ValueListRef"}
TAGS = {name: f"{{{DEFINE if name in DEFINE_TAGS else ODM}}}{name}" for name in ATTRIBUTES}
CHILDREN = {
    "ODM": {"Study"}, "Study": {"GlobalVariables", "MetaDataVersion"},
    "GlobalVariables": {"StudyName", "StudyDescription", "ProtocolName"},
    "MetaDataVersion": {"SupplementalDoc", "leaf", "ValueListDef", "ItemGroupDef", "ItemDef", "CodeList"},
    "SupplementalDoc": {"DocumentRef"}, "leaf": {"title"}, "ValueListDef": {"ItemRef"},
    "ItemGroupDef": {"ItemRef", "leaf"}, "ItemDef": {"CodeListRef", "ValueListRef"},
    "CodeList": {"CodeListItem", "ExternalCodeList"}, "CodeListItem": {"Decode"}, "Decode": {"TranslatedText"},
}
TEXT_TAGS = {"StudyName", "StudyDescription", "ProtocolName", "title", "TranslatedText"}


def attr(element, name):
    return element.get(name, element.get(f"{{{DEFINE}}}{name}"))


def ordered(parent, tag):
    """OrderNumber determines relative order, not the XML serialization order."""
    entries = parent.findall("o:" + tag, NAMESPACES)
    numbers = [int(e.get("OrderNumber", "0")) for e in entries]
    if any(n <= 0 for n in numbers) or len(set(numbers)) != len(numbers):
        raise ValueError(f"Invalid or duplicate OrderNumber in {parent.get('OID')}")
    return sorted(entries, key=lambda e: int(e.get("OrderNumber")))


class LegacyDocument:
    def __init__(self, path):
        self.path = path
        self.root = ET.parse(path).getroot()
        if self.root.tag != f"{{{ODM}}}ODM" or self.root.get("ODMVersion") != "1.2":
            raise ValueError("The legacy oracle requires ODM 1.2")
        studies = self.root.findall("o:Study", NAMESPACES)
        if len(studies) != 1 or len(studies[0].findall("o:MetaDataVersion", NAMESPACES)) != 1:
            raise ValueError("Exactly one legacy Study and MetaDataVersion is required")
        self.study = studies[0]
        self.md = self.study.find("o:MetaDataVersion", NAMESPACES)
        if attr(self.md, "DefineVersion") != "1.0.0":
            raise ValueError("The legacy oracle requires Define-XML 1.0.0")
        self.objects = defaultdict(dict)
        self.bindings = {}
        self.conversions = []
        self.unresolved = []
        self.unsupported = []
        self.unknown = []
        self._parents = {child: parent for parent in self.root.iter() for child in parent}
        for kind, tag in TYPES.items():
            for element in self.root.iter(tag):
                identity = element.get("OID") or element.get("ID")
                if not identity or identity in self.objects[kind]:
                    raise ValueError(f"Missing or duplicate {kind} identity: {identity}")
                self.objects[kind][identity] = element
        self._admit_content()
        self._admit_references()

    def object(self, kind, identity):
        if identity not in self.objects[kind]:
            raise ValueError(f"Dangling or wrongly typed legacy {kind} reference: {identity}")
        return self.objects[kind][identity]

    def locator(self, element):
        return {"element": local(element.tag), "oid": element.get("OID"), "id": element.get("ID"),
                **({"file_oid": element.get("FileOID")} if element is self.root else {})}

    def _inside_arm(self, element):
        while element is not None:
            if element.tag.startswith("{" + ARM + "}"):
                return True
            element = self._parents.get(element)
        return False

    def _admit_content(self):
        for element in self.root.iter():
            if self._inside_arm(element):
                continue
            name = local(element.tag)
            namespace = element.tag[1:].split("}")[0] if element.tag.startswith("{") else None
            if namespace not in {ODM, DEFINE} or element.tag != TAGS.get(name):
                self.unknown.append({**self.locator(element), "reason": "unrecognized element",
                                     "xml": ET.tostring(element, encoding="unicode")})
                continue
            allowed = {TAGS[t] for t in CHILDREN.get(name, set())}
            if name == "MetaDataVersion":
                allowed.add(f"{{{ARM}}}AnalysisResultDisplays")
            for child in element:
                if child.tag not in allowed:
                    self.unknown.append({**self.locator(element), "reason": "unexpected child", "child": child.tag})
            if name not in TEXT_TAGS and (element.text or "").strip():
                self.unknown.append({**self.locator(element), "reason": "unexpected text", "text": element.text})
            for child in element:
                if (child.tail or "").strip():
                    self.unknown.append({**self.locator(element), "reason": "unexpected tail text", "text": child.tail})
            required_single = {"Study": ("GlobalVariables",),
                               "GlobalVariables": ("StudyName", "StudyDescription", "ProtocolName"),
                               "leaf": ("title",), "CodeListItem": ("Decode",), "Decode": ("TranslatedText",)}.get(name, ())
            for child_name in required_single:
                if len(element.findall(TAGS[child_name])) != 1:
                    self.unknown.append({**self.locator(element), "reason": "expected exactly one child", "child": child_name})
            if name == "ItemDef":
                for child_name in ("CodeListRef", "ValueListRef"):
                    if len(element.findall(TAGS[child_name])) > 1:
                        self.unknown.append({**self.locator(element), "reason": "multiple references", "child": child_name})
            if name == "CodeList" and element.find(TAGS["ExternalCodeList"]) is not None and element.find(TAGS["CodeListItem"]) is not None:
                self.unknown.append({**self.locator(element), "reason": "mixed external and item codelist"})
            for key, value in element.attrib.items():
                if key not in ATTRIBUTES[name]:
                    self.unknown.append({**self.locator(element), "attribute": key, "value": value})
            if name == "ItemDef" and "SignificantDigits" in element.attrib and f"{{{DEFINE}}}SignificantDigits" in element.attrib:
                if element.get("SignificantDigits") != element.get(f"{{{DEFINE}}}SignificantDigits"):
                    self.unknown.append({**self.locator(element), "reason": "conflicting SignificantDigits attributes"})
            if name == "TranslatedText" and element.get(f"{{{XML}}}lang", "en") != "en":
                self.unknown.append({**self.locator(element), "reason": "non-English text"})

    def _admit_references(self):
        for element in self.root.iter():
            for key, value in element.attrib.items():
                kind = {"ItemOID": "ItemDef", "ItemGroupOID": "ItemGroupDef", "CodeListOID": "CodeList",
                        "ValueListOID": "ValueListDef", "leafID": "leaf", "ArchiveLocationID": "leaf"}.get(local(key))
                if kind:
                    self.object(kind, value)

    def documents(self, parent):
        result = []
        for ref in parent.findall("d:DocumentRef", NAMESPACES):
            leaf = self.object("leaf", ref.get("leafID"))
            result.append({"link": leaf.get(f"{{{XLINK}}}href"),
                           "title": prose(leaf.findtext("d:title", namespaces=NAMESPACES)), "pages": []})
        return result

    @staticmethod
    def comment(element):
        text = prose(element.get("Comment"))
        return {"text": text, "documents": []} if text else None

    def variable(self, item, ref, owner, position, key_sequence=None):
        origin = item.get("Origin")
        codelist = item.find("o:CodeListRef", NAMESPACES)
        return {
            "label": prose(attr(item, "Label")), "type": item.get("DataType"),
            "length": item.get("Length"), "significant_digits": attr(item, "SignificantDigits"),
            "display_format": attr(item, "DisplayFormat"), "sas_name": owner,
            "mandatory": ref.get("Mandatory"), "role": None,
            "key_sequence": str(key_sequence) if key_sequence is not None else None,
            "order": str(position),
            "codelist": self.object("CodeList", codelist.get("CodeListOID")).get("Name") if codelist is not None else None,
            "origins": [{"type": origin, "source": "Sponsor" if origin in {"Derived", "Assigned", "Other"} else None,
                         "description": "", "documents": []}] if origin else [],
            "method": None, "comment": self.comment(item), "languages": ["en"],
        }

    def value_list(self, item, group, owner, path):
        refs = item.findall("d:ValueListRef", NAMESPACES)
        if not refs:
            return []
        if len(refs) != 1:
            raise ValueError(f"Multiple legacy value lists on {item.get('OID')}")
        listing = self.object("ValueListDef", refs[0].get("ValueListOID"))
        self._used_lists.add(listing.get("OID"))
        selector = next((self.object("ItemDef", r.get("ItemOID")) for r in group.findall("o:ItemRef", NAMESPACES)
                         if self.object("ItemDef", r.get("ItemOID")).get("Name") == "PARAMCD"), None)
        cref = selector.find("o:CodeListRef", NAMESPACES) if selector is not None else None
        codes = {c.get("CodedValue") for c in self.object("CodeList", cref.get("CodeListOID"))
                 if local(c.tag) == "CodeListItem"} if cref is not None else set()
        result = []
        entries = ordered(listing, "ItemRef")
        raw_orders = [r.get("OrderNumber") for r in entries]
        canonical_orders = [str(i + 1) for i in range(len(entries))]
        if raw_orders != canonical_orders:
            self.conversions.append({"path": path, "rule": "relative_value_list_order",
                                     "reference": raw_orders, "expected": canonical_orders})
        for index, ref in enumerate(entries):
            entry = self.object("ItemDef", ref.get("ItemOID"))
            entry_path = f"{path}/{index}"
            self.bindings[entry_path] = self.locator(entry)
            value = entry.get("Name")
            if owner == "PARAMCD" or value not in codes:
                self.unresolved.append({"path": entry_path, **self.locator(entry),
                                        "reason": "No evidenced PARAMCD selector", "value": value})
                where = []
            else:
                where = [{"variable": "PARAMCD", "comparator": "EQ", "soft_hard": "Soft", "values": [value]}]
            result.append({"where": where, **self.variable(entry, ref, owner, index + 1)})
        self.conversions.append({"path": path, "rule": "value_name_to_paramcd_where",
                                 "reference": listing.get("OID"), "expected": "PARAMCD equality",
                                 "basis": "Each ItemDef.Name must occur in the dataset's PARAMCD codelist"})
        return result

    def codelists(self):
        result = {}
        for element in self.md.findall("o:CodeList", NAMESPACES):
            name = element.get("Name")
            if name in result:
                raise ValueError(f"Duplicate legacy codelist name: {name}")
            self.bindings[f"/codelists/{name}"] = self.locator(element)
            items = []
            for item in element.findall("o:CodeListItem", NAMESPACES):
                value = item.get("CodedValue")
                if element.get("DataType") != "text":
                    value = str(Decimal(value).normalize())
                items.append({"value": value,
                              "decode": prose(item.findtext("o:Decode/o:TranslatedText", namespaces=NAMESPACES)) or None,
                              "rank": attr(item, "Rank"), "extended": "No", "aliases": []})
            result[name] = {"type": element.get("DataType"), "format": None, "items": items,
                            "is_non_standard": None, "standard": None, "aliases": [],
                            "external": [dict(e.attrib) for e in element.findall("o:ExternalCodeList", NAMESPACES)]}
        return result

    def metadata(self):
        # Repeated inspection is stable; these are inventories, not an event log.
        self.bindings = {"": self.locator(self.md), "/file_type": self.locator(self.root),
                         "/study": self.locator(self.study), "/metadata_name": self.locator(self.md),
                         "/metadata_description": self.locator(self.md)}
        self.conversions, self.unresolved, self.unsupported = [], [], []
        self._used_lists = set()
        standard = {"Name": attr(self.md, "StandardName"), "Version": attr(self.md, "StandardVersion")}
        if standard != {"Name": "CDISC ADaM", "Version": "2.1"}:
            self.unresolved.append({"path": "/standards", "reference": standard, "reason": "Unreviewed legacy standard"})
        self.conversions.append({"path": "/standards", "rule": "model_and_guide_are_separate_citations",
                                 "reference": standard, "expected": [GUIDE],
                                 "basis": "Pilot 01 data guide: current data comply with ADaMIG 1.0"})
        groups = self.md.findall("o:ItemGroupDef", NAMESPACES)
        datasets = {}
        used_leaves = set()
        for group in groups:
            name = group.get("Name")
            if name in datasets:
                raise ValueError(f"Duplicate legacy dataset name: {name}")
            path = f"/datasets/{name}"
            self.bindings[path] = self.locator(group)
            keys = [v.strip() for v in (attr(group, "DomainKeys") or "").split(",") if v.strip()]
            if len(set(keys)) != len(keys):
                raise ValueError(f"Duplicate legacy DomainKeys in {name}")
            variables = {}
            for index, ref in enumerate(ordered(group, "ItemRef")):
                item = self.object("ItemDef", ref.get("ItemOID")); column = item.get("Name")
                if column in variables:
                    raise ValueError(f"Duplicate legacy variable name: {name}.{column}")
                col_path = f"{path}/variables/{column}"
                self.bindings[col_path] = self.locator(item)
                sequence = keys.index(column) + 1 if column in keys else None
                variables[column] = {**self.variable(item, ref, column, index + 1, sequence),
                                     "value_level": self.value_list(item, group, column, col_path + "/value_level")}
            missing_keys = sorted(set(keys) - variables.keys())
            if missing_keys:
                self.unresolved.append({"path": path + "/domain_keys", "reference": keys,
                                        "missing_variables": missing_keys,
                                        "reason": "Legacy DomainKeys names variables absent from its dataset"})
            self.conversions.append({"path": path + "/domain_keys", "rule": "domain_keys_to_item_key_sequences",
                                     "reference": keys, "expected": {k: str(keys.index(k) + 1) for k in keys if k in variables}})
            archive = attr(group, "ArchiveLocationID")
            leaf = self.object("leaf", archive) if archive else None
            if leaf is not None:
                used_leaves.add(archive)
            cls = attr(group, "Class")
            if cls not in CLASSES:
                self.unresolved.append({"path": path + "/class", "reference": cls, "reason": "Unreviewed legacy class"})
            self.conversions.append({"path": path + "/class", "rule": "legacy_dataset_class",
                                     "reference": cls, "expected": CLASSES.get(cls, cls)})
            datasets[name] = {
                "label": prose(attr(group, "Label")), "class": CLASSES.get(cls, cls), "subclass": [],
                "structure": prose(attr(group, "Structure")), "purpose": group.get("Purpose"), "domain": None,
                "repeating": group.get("Repeating"), "reference_data": group.get("IsReferenceData"),
                "sas_name": name, "has_no_data": "No", "comment": self.comment(group), "standard": GUIDE,
                "artifact": {"link": leaf.get(f"{{{XLINK}}}href"), "title": prose(leaf.findtext("d:title", namespaces=NAMESPACES))} if leaf is not None else None,
                "column_order": list(variables), "variables": variables,
            }
        for ref in self.md.findall("d:SupplementalDoc/d:DocumentRef", NAMESPACES):
            used_leaves.add(ref.get("leafID"))
        for display in self.md.findall("a:AnalysisResultDisplays", NAMESPACES):
            self.unsupported.append({"kind": "draft_analysis_results", "reason": "Outside the yamaa metadata profile",
                                     "display_count": len(display.findall("a:ResultDisplay", NAMESPACES)),
                                     "result_count": len(display.findall(".//a:AnalysisResults", NAMESPACES)),
                                     "reference_ids": [e.get("OID") for e in display.iter() if e.get("OID")],
                                     "xml": ET.tostring(display, encoding="unicode")})
        for identity, leaf in self.objects["leaf"].items():
            if identity not in used_leaves:
                self.unsupported.append({"kind": "legacy_document_leaf", **self.locator(leaf),
                                         "link": leaf.get(f"{{{XLINK}}}href"),
                                         "title": prose(leaf.findtext("d:title", namespaces=NAMESPACES)),
                                         "reason": "Not bound to supported dataset/supplemental metadata"})
        used_items = {v["oid"] for v in self.bindings.values() if v["element"] == "ItemDef"}
        for kind, used in (("ItemDef", used_items), ("ValueListDef", self._used_lists)):
            for identity, element in self.objects[kind].items():
                if identity not in used:
                    self.unresolved.append({"path": f"/unbound/{kind}/{identity}", **self.locator(element),
                                            "reason": "Definition is not bound to a represented dataset",
                                            "xml": ET.tostring(element, encoding="unicode")})
        return {
            "file_type": self.root.get("FileType"),
            "study": {local(e.tag): prose(e.text) for e in self.study.find("o:GlobalVariables", NAMESPACES)},
            "metadata_name": self.md.get("Name"), "metadata_description": self.md.get("Description"),
            "standards": [GUIDE],
            "documents": {"AnnotatedCRF": [], "SupplementalDoc": [self.documents(e) for e in self.md.findall("d:SupplementalDoc", NAMESPACES)]},
            "dataset_order": list(datasets), "datasets": datasets, "codelists": self.codelists(),
            "unsupported_content": self.unknown, "unreferenced_definitions": [],
        }

    def inventory(self):
        tags = Counter(local(e.tag) for e in self.root.iter())
        return {"datasets": tags["ItemGroupDef"], "variables": sum(len(e.findall("o:ItemRef", NAMESPACES)) for e in self.md.findall("o:ItemGroupDef", NAMESPACES)),
                "value_lists": tags["ValueListDef"], "value_level_entries": sum(len(e.findall("o:ItemRef", NAMESPACES)) for e in self.md.findall("d:ValueListDef", NAMESPACES)),
                "codelists": tags["CodeList"], "result_displays": tags["ResultDisplay"], "analysis_results": tags["AnalysisResults"],
                "elements": dict(tags)}
