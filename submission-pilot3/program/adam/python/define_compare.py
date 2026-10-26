"""Compare Pilot 3 Define-XML metadata after resolving its object references.

Object identifiers, whitespace in prose, and the 2.0/2.1 representation of
classes and implementation guides do not define clinical metadata equality.
Missing fields, unknown content and broken references never count as matches.
"""

from decimal import Decimal
import re
import xml.etree.ElementTree as ET

ODM = "http://www.cdisc.org/ns/odm/v1.3"
XLINK = "http://www.w3.org/1999/xlink"
XML = "http://www.w3.org/XML/1998/namespace"

# Every element and attribute occurring in the reference or generated profile
# is accounted for. New XML content requires an explicit comparator extension.
ATTRIBUTES = {
    "ODM": "CreationDateTime FileOID FileType ODMVersion SourceSystem SourceSystemVersion Context",
    "Study": "OID", "MetaDataVersion": "OID Name Description DefineVersion StandardName StandardVersion",
    "Standard": "OID Name Type Version Status", "ItemGroupDef": "OID Name Repeating IsReferenceData SASDatasetName Purpose Structure ArchiveLocationID Class StandardOID HasNoData CommentOID Domain",
    "ItemRef": "ItemOID OrderNumber Mandatory KeySequence MethodOID Role",
    "ItemDef": "OID Name DataType Length SignificantDigits SASFieldName DisplayFormat CommentOID",
    "CodeList": "OID Name DataType IsNonStandard StandardOID SASFormatName",
    "CodeListItem": "CodedValue OrderNumber Rank ExtendedValue",
    "EnumeratedItem": "CodedValue OrderNumber Rank ExtendedValue",
    "ExternalCodeList": "Dictionary Version href", "Alias": "Name Context",
    "MethodDef": "OID Name Type", "CommentDef": "OID", "ValueListDef": "OID",
    "WhereClauseDef": "OID", "WhereClauseRef": "WhereClauseOID",
    "RangeCheck": "Comparator SoftHard ItemOID", "Origin": "Type Source",
    "DocumentRef": "leafID", "PDFPageRef": "PageRefs Type Title",
    "leaf": "ID href", "Class": "Name", "Subclass": "Name",
    "CodeListRef": "CodeListOID", "ValueListRef": "ValueListOID",
    "FormalExpression": "Context", "TranslatedText": "lang",
    **{name: "" for name in (
        "GlobalVariables", "StudyName", "StudyDescription", "ProtocolName",
        "SupplementalDoc", "AnnotatedCRF", "Standards", "Description", "Decode",
        "CheckValue", "title",
    )},
}


def local(name):
    return name.rsplit("}", 1)[-1]


def prose(text):
    return " ".join((text or "").split())


class Document:
    def __init__(self, path):
        self.root = ET.parse(path).getroot()
        if self.root.tag != f"{{{ODM}}}ODM":
            raise ValueError("Pilot 3 requires ODM 1.3 XML")
        self.study = self.root.find(f"{{{ODM}}}Study")
        self.md = self.study.find(f"{{{ODM}}}MetaDataVersion")
        self.defns = next(k[1:].split("}")[0] for k in self.md.attrib if local(k) == "DefineVersion")
        if self.defns not in ("http://www.cdisc.org/ns/def/v2.0", "http://www.cdisc.org/ns/def/v2.1"):
            raise ValueError(f"Unsupported Define namespace: {self.defns}")
        self.n = {"o": ODM, "d": self.defns}
        self.objects = {}
        self.unsupported = []
        allowed_namespaces = {ODM, self.defns, XLINK, XML}
        for element in self.root.iter():
            tag = local(element.tag)
            if element.tag.split("}")[0][1:] not in allowed_namespaces or tag not in ATTRIBUTES:
                self.unsupported.append(ET.tostring(element, encoding="unicode"))
            else:
                for key in element.attrib:
                    namespace = key[1:].split("}")[0] if key.startswith("{") else None
                    if local(key) not in ATTRIBUTES[tag].split() or namespace and namespace not in allowed_namespaces:
                        self.unsupported.append(f"{tag}/@{key}")
            if tag == "TranslatedText" and element.get(f"{{{XML}}}lang", "en") != "en":
                self.unsupported.append("Non-English TranslatedText requires a language-aware comparison")
            if tag in {"Description", "Decode"} and len(element.findall("o:TranslatedText", self.n)) != 1:
                self.unsupported.append(f"{tag} requires exactly one TranslatedText")
            identity = element.get("OID") or element.get("ID")
            if identity:
                if identity in self.objects:
                    raise ValueError(f"Duplicate XML object: {identity}")
                self.objects[identity] = element
        # Resolve every XML reference, even one in an otherwise unused object.
        references = set()
        for element in self.root.iter():
            for key, value in element.attrib.items():
                if local(key) in {"ItemOID", "MethodOID", "CommentOID", "CodeListOID", "ValueListOID", "WhereClauseOID", "leafID", "ArchiveLocationID", "StandardOID"}:
                    self.object(value)
                    references.add(value)
        self.unreferenced = [ET.tostring(e, encoding="unicode") for identity, e in self.objects.items()
                             if local(e.tag) in {"ItemDef", "MethodDef", "CommentDef", "ValueListDef", "WhereClauseDef", "leaf"}
                             and identity not in references]

    def object(self, identity):
        if identity not in self.objects:
            raise ValueError(f"Dangling XML reference: {identity}")
        return self.objects[identity]

    def attr(self, element, name):
        return element.get(name, element.get(f"{{{self.defns}}}{name}"))

    def text(self, element, path="o:Description/o:TranslatedText"):
        return prose(element.findtext(path, namespaces=self.n))

    def documents(self, element):
        documents = []
        for ref in element.findall("d:DocumentRef", self.n):
            leaf = self.object(ref.get("leafID"))
            documents.append({
                "link": leaf.get(f"{{{XLINK}}}href"),
                "title": self.text(leaf, "d:title"),
                "pages": [dict(page.attrib) for page in ref.findall("d:PDFPageRef", self.n)],
            })
        return documents

    def method(self, ref):
        if ref.get("MethodOID") is None:
            return None
        element = self.object(ref.get("MethodOID"))
        return {
            "name": element.get("Name"), "type": element.get("Type"),
            "description": self.text(element), "documents": self.documents(element),
            "expressions": [{"context": e.get("Context"), "code": e.text or ""}
                            for e in element.findall("o:FormalExpression", self.n)],
        }

    def comment(self, element):
        identity = self.attr(element, "CommentOID")
        if identity is None:
            return None
        comment = self.object(identity)
        return {"text": self.text(comment), "documents": self.documents(comment)}

    def variable(self, item, ref):
        codelist = item.find("o:CodeListRef", self.n)
        origins = []
        for origin in item.findall("d:Origin", self.n):
            # ADaM 2.1 makes Sponsor explicit for these origin types.
            source = origin.get("Source")
            if source is None and origin.get("Type") in {"Derived", "Assigned", "Other"}:
                source = "Sponsor"
            origins.append({"type": origin.get("Type"), "source": source,
                            "description": self.text(origin), "documents": self.documents(origin)})
        return {
            "label": self.text(item), "type": item.get("DataType"),
            "length": item.get("Length"), "significant_digits": item.get("SignificantDigits"),
            "display_format": self.attr(item, "DisplayFormat"), "sas_name": item.get("SASFieldName"),
            "mandatory": ref.get("Mandatory"), "role": ref.get("Role"),
            "key_sequence": ref.get("KeySequence"), "order": ref.get("OrderNumber"),
            "codelist": self.object(codelist.get("CodeListOID")).get("Name") if codelist is not None else None,
            "origins": origins, "method": self.method(ref), "comment": self.comment(item),
            "languages": [e.get(f"{{{XML}}}lang", "en") for e in item.findall("o:Description/o:TranslatedText", self.n)],
        }

    def value_list(self, item):
        ref = item.find("d:ValueListRef", self.n)
        if ref is None:
            return []
        values = []
        for item_ref in self.object(ref.get("ValueListOID")).findall("o:ItemRef", self.n):
            where = []
            for clause_ref in item_ref.findall("d:WhereClauseRef", self.n):
                for check in self.object(clause_ref.get("WhereClauseOID")).findall("o:RangeCheck", self.n):
                    where_item = self.object(self.attr(check, "ItemOID"))
                    where.append({"variable": where_item.get("Name"), "comparator": check.get("Comparator"),
                                  "soft_hard": check.get("SoftHard"),
                                  "values": [e.text for e in check.findall("o:CheckValue", self.n)]})
            values.append({"where": where, **self.variable(self.object(item_ref.get("ItemOID")), item_ref)})
        return values

    def codelists(self):
        lists = {}
        for element in self.md.findall("o:CodeList", self.n):
            entries = []
            items = [e for e in element if local(e.tag) in {"CodeListItem", "EnumeratedItem"}]
            numbers = [e.get("OrderNumber") for e in items]
            if any(n is not None for n in numbers):
                if any(n is None for n in numbers) or len(set(numbers)) != len(numbers):
                    raise ValueError("Inconsistent codelist ordering")
                items.sort(key=lambda e: int(e.get("OrderNumber")))
            for item in items:
                value = item.get("CodedValue")
                if element.get("DataType") != "text":
                    value = str(Decimal(value).normalize())
                entries.append({"value": value, "decode": self.text(item, "o:Decode/o:TranslatedText") or None,
                                "rank": self.attr(item, "Rank"), "extended": self.attr(item, "ExtendedValue") or "No",
                                "aliases": [dict(e.attrib) for e in item.findall("o:Alias", self.n)]})
            if element.get("Name") in lists:
                raise ValueError("Duplicate codelist name")
            lists[element.get("Name")] = {
                "type": element.get("DataType"), "format": element.get("SASFormatName"), "items": entries,
                "is_non_standard": self.attr(element, "IsNonStandard"),
                "aliases": [dict(e.attrib) for e in element.findall("o:Alias", self.n)],
                "external": [dict(e.attrib) for e in element.findall("o:ExternalCodeList", self.n)],
            }
        return lists

    def metadata(self):
        groups = self.md.findall("o:ItemGroupDef", self.n)
        datasets = {}
        for group in groups:
            variables = {}
            for ref in group.findall("o:ItemRef", self.n):
                item = self.object(ref.get("ItemOID"))
                if item.get("Name") in variables:
                    raise ValueError("Duplicate dataset variable name")
                variables[item.get("Name")] = {**self.variable(item, ref), "value_level": self.value_list(item)}
            cls = group.find("d:Class", self.n)
            leaf = group.find("d:leaf", self.n)
            if group.get("Name") in datasets:
                raise ValueError("Duplicate dataset name")
            standard = self.attr(group, "StandardOID")
            guide = self.object(standard) if standard else self.md
            datasets[group.get("Name")] = {
                "label": self.text(group), "class": cls.get("Name") if cls is not None else self.attr(group, "Class"),
                "subclass": [e.get("Name") for e in group.findall("d:Class/d:Subclass", self.n)],
                "structure": self.attr(group, "Structure"), "purpose": group.get("Purpose"),
                "domain": group.get("Domain"), "repeating": group.get("Repeating"),
                "reference_data": group.get("IsReferenceData"), "sas_name": group.get("SASDatasetName"),
                "has_no_data": self.attr(group, "HasNoData") or "No", "comment": self.comment(group),
                "standard": {"name": (guide.get("Name") if standard else self.attr(guide, "StandardName")).replace("ADaM-IG", "ADaMIG"),
                             "version": guide.get("Version") if standard else self.attr(guide, "StandardVersion")},
                "artifact": {"link": leaf.get(f"{{{XLINK}}}href"), "title": self.text(leaf, "d:title")} if leaf is not None else None,
                "column_order": list(variables), "variables": variables,
            }
        standards = [dict((local(k), v) for k, v in e.attrib.items() if k != "OID")
                     for e in self.md.findall("d:Standards/d:Standard", self.n)]
        if not standards:
            standards = [{"Name": self.attr(self.md, "StandardName").replace("ADaM-IG", "ADaMIG"),
                          "Version": self.attr(self.md, "StandardVersion"), "Type": "IG", "Status": "Final"}]
        return {
            "file_type": self.root.get("FileType"),
            "study": {local(e.tag): prose(e.text) for e in self.study.find("o:GlobalVariables", self.n)},
            "metadata_name": self.md.get("Name"), "metadata_description": self.md.get("Description"),
            "standards": standards,
            "documents": {kind: [self.documents(e) for e in self.md.findall("d:" + kind, self.n)]
                          for kind in ("AnnotatedCRF", "SupplementalDoc")},
            "dataset_order": [g.get("Name") for g in groups],
            "datasets": datasets, "codelists": self.codelists(), "unsupported_content": self.unsupported,
            "unreferenced_definitions": self.unreferenced,
        }


def differences(reference, candidate, path=""):
    """Return every unequal leaf, including missing and extra keys/list entries."""
    if isinstance(reference, dict) and isinstance(candidate, dict):
        result = []
        for key in sorted(reference.keys() | candidate.keys()):
            location = f"{path}/{key}"
            if key not in reference or key not in candidate:
                result.append({"path": location, "reference": reference.get(key), "candidate": candidate.get(key)})
            else:
                result.extend(differences(reference[key], candidate[key], location))
        return result
    if isinstance(reference, list) and isinstance(candidate, list):
        result = []
        for i in range(max(len(reference), len(candidate))):
            if i >= len(reference) or i >= len(candidate):
                result.append({"path": f"{path}/{i}", "reference": reference[i] if i < len(reference) else None,
                               "candidate": candidate[i] if i < len(candidate) else None})
            else:
                result.extend(differences(reference[i], candidate[i], f"{path}/{i}"))
        return result
    return [] if reference == candidate else [{"path": path, "reference": reference, "candidate": candidate}]


def compare(reference_path, candidate_path):
    reference, candidate = Document(reference_path), Document(candidate_path)
    expected, actual = reference.metadata(), candidate.metadata()
    delta = differences(expected, actual)
    return {
        "metadata_equivalent": not delta and not reference.unsupported and not candidate.unsupported,
        "byte_identical": reference_path.read_bytes() == candidate_path.read_bytes(),
        "reference_define_version": reference.attr(reference.md, "DefineVersion"),
        "candidate_define_version": candidate.attr(candidate.md, "DefineVersion"),
        "coverage": {"datasets": len(actual["datasets"]),
                     "variables": sum(len(d["variables"]) for d in actual["datasets"].values()),
                     "value_level_entries": sum(len(v["value_level"]) for d in actual["datasets"].values() for v in d["variables"].values()),
                     "codelists": len(actual["codelists"])},
        "differences": delta,
        "representation": {
            "reference_root": reference.root.attrib, "candidate_root": candidate.root.attrib,
            "reference_study": reference.study.attrib, "candidate_study": candidate.study.attrib,
            "reference_metadata_version": reference.md.attrib, "candidate_metadata_version": candidate.md.attrib,
            "reference_stylesheets": re.findall(r"<\?xml-stylesheet\s+(.*?)\?>", reference_path.read_text()),
            "candidate_stylesheets": re.findall(r"<\?xml-stylesheet\s+(.*?)\?>", candidate_path.read_text()),
        },
        "normalizations": [
            "Resolve XML object references by their metadata content, not generated OIDs.",
            "Collapse whitespace in prose; preserve coded values and formal expression code.",
            "Use ordered items when CodeList OrderNumber is omitted in 2.1.",
            "Read a 2.0 Class attribute and a 2.1 Class child as the same field.",
            "Read ADaM-IG 1.1 as ADaMIG 1.1, Final; 2.0 does not encode IG status.",
            "Treat omitted English language and ADaM Sponsor source as their 2.1 defaults.",
            "Compare methods/comments at every binding, including shared value-level methods.",
            "Identify value-level definitions by their owner, where clause and SASFieldName, not generated Name/OID.",
        ],
    }
