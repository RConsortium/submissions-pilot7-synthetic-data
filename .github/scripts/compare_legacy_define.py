"""Compare supported Pilot 01 metadata across Define-XML 1.0 and 2.0.

The ordinary 2.0/2.1 comparator is unchanged. Every converted field, known
unsupported block and unresolved declaration remains visible in this report.
"""

from collections import Counter
from pathlib import Path
import re

from define_metadata import Document, local
from legacy_define import LegacyDocument

MISSING = object()


def field_rows(reference, candidate, path=""):
    """Walk equal and unequal leaves, retaining presence separately from null."""
    if isinstance(reference, dict) and isinstance(candidate, dict):
        if not reference and not candidate:
            yield path, reference, candidate
        for key in sorted(reference.keys() | candidate.keys()):
            yield from field_rows(reference.get(key, MISSING), candidate.get(key, MISSING), f"{path}/{key}")
    elif isinstance(reference, list) and isinstance(candidate, list):
        if not reference and not candidate:
            yield path, reference, candidate
        for i in range(max(len(reference), len(candidate))):
            yield from field_rows(reference[i] if i < len(reference) else MISSING,
                                  candidate[i] if i < len(candidate) else MISSING, f"{path}/{i}")
    else:
        yield path, reference, candidate


def target_bindings(document):
    def identity(element):
        return {"element": local(element.tag), "oid": element.get("OID"), "id": element.get("ID"),
                **({"file_oid": element.get("FileOID")} if element is document.root else {})}
    result = {"": identity(document.md), "/file_type": identity(document.root),
              "/study": identity(document.study), "/metadata_name": identity(document.md),
              "/metadata_description": identity(document.md)}
    for group in document.md.findall("o:ItemGroupDef", document.n):
        path = "/datasets/" + group.get("Name")
        result[path] = identity(group)
        for ref in group.findall("o:ItemRef", document.n):
            item = document.object(ref.get("ItemOID"))
            base = path + "/variables/" + item.get("Name")
            result[base] = identity(item)
            value_list = item.find("d:ValueListRef", document.n)
            if value_list is not None:
                entries = document.object(value_list.get("ValueListOID")).findall("o:ItemRef", document.n)
                for i, entry in enumerate(entries):
                    result[f"{base}/value_level/{i}"] = identity(document.object(entry.get("ItemOID")))
    for listing in document.md.findall("o:CodeList", document.n):
        result["/codelists/" + listing.get("Name")] = identity(listing)
    return result


def binding(bindings, path):
    while path:
        if path in bindings:
            return bindings[path]
        path = path.rpartition("/")[0]
    return bindings.get("")


def conversion_rule(path):
    if path.startswith("/standards") or re.fullmatch(r"/datasets/[^/]+/standard/.*", path):
        return "model_and_guide_are_separate_citations"
    if re.fullmatch(r"/datasets/[^/]+/class", path):
        return "legacy_dataset_class"
    if path.endswith("/label"):
        return "inline_label_to_description"
    if "/comment/" in path:
        return "inline_comment_to_comment_def"
    if "/origins/" in path:
        return "inline_origin_to_origin_element"
    if "/value_level/" in path and "/where/" in path:
        return "value_name_to_paramcd_where"
    if path.endswith("/sas_name"):
        return "explicit_transport_name_from_legacy_name"
    if path.endswith("/key_sequence") and "/value_level/" not in path:
        return "domain_keys_to_item_key_sequences"
    if path.endswith("/order") and "/value_level/" in path:
        return "relative_value_list_order"
    return None


def coverage(metadata):
    datasets = metadata["datasets"].values()
    return {"datasets": len(metadata["datasets"]),
            "variables": sum(len(d["variables"]) for d in datasets),
            "value_lists": sum(bool(v["value_level"]) for d in metadata["datasets"].values() for v in d["variables"].values()),
            "value_level_entries": sum(len(v["value_level"]) for d in metadata["datasets"].values() for v in d["variables"].values()),
            "codelists": len(metadata["codelists"])}


def inherited_omission(path, left, right, expected, actual):
    """Explain a difference without treating it as equality or hiding its values.

    DEFINE-30 retains ordinary value-level inheritance. The current language
    cannot clear an optional parent field at one historical value. Only the
    exact, evidenced inheritance pattern qualifies; arbitrary mismatches fail.
    """
    match = re.fullmatch(r"/datasets/([^/]+)/variables/([^/]+)/value_level/\d+/(significant_digits|display_format|codelist|comment|method)", path)
    if not match or left is not None or right is None or right is MISSING:
        return None
    dataset, column, field = match.groups()
    original = expected["datasets"][dataset]["variables"][column][field]
    parent = actual.get("datasets", {}).get(dataset, {}).get("variables", {}).get(column, {}).get(field)
    if original is None or parent != original or right != parent:
        return None
    return {"code": "value_level_optional_metadata_inheritance", "field": field,
            "parent_path": f"/datasets/{dataset}/variables/{column}/{field}",
            "parent_value": parent,
            "reason": "The legacy value omits this field; yamaa inherits the unchanged parent field and has no clear override"}


def compare_legacy(reference_path, candidate_path):
    reference_path, candidate_path = Path(reference_path), Path(candidate_path)
    reference, candidate = LegacyDocument(reference_path), Document(candidate_path)
    if candidate.attr(candidate.md, "DefineVersion") != "2.0.0":
        raise ValueError("The legacy migration comparison requires a Define-XML 2.0.0 candidate")
    expected, actual = reference.metadata(), candidate.metadata()
    bindings = target_bindings(candidate)
    rows = []
    for path, left, right in field_rows(expected, actual):
        equal = left is not MISSING and right is not MISSING and left == right
        rule = conversion_rule(path)
        gap = inherited_omission(path, left, right, expected, actual) if not equal else None
        rows.append({"path": path, "status": ("converted" if rule else "matched") if equal else "different",
                     "reference_present": left is not MISSING, "candidate_present": right is not MISSING,
                     "reference": None if left is MISSING else left, "candidate": None if right is MISSING else right,
                     "mapping_rule": rule, "reference_object": binding(reference.bindings, path),
                     "candidate_object": binding(bindings, path), "known_gap": gap})
    for unresolved in reference.unresolved:
        rows.append({"path": unresolved["path"], "status": "unresolved", "reference": unresolved,
                     "candidate": None, "mapping_rule": None, "reference_object": None, "candidate_object": None})
    for i, unsupported in enumerate(reference.unsupported):
        rows.append({"path": f"/legacy_only/{i}", "status": "unsupported", "reference": {k: v for k, v in unsupported.items() if k != "xml"},
                     "candidate": None, "mapping_rule": None, "reference_object": None, "candidate_object": None})
    delta = [{k: row[k] for k in ("path", "reference", "candidate", "reference_present", "candidate_present", "known_gap")}
             for row in rows if row["status"] == "different"]
    unexpected = [d for d in delta if d["known_gap"] is None]
    # A parsed comparison with known gaps is useful evidence, never an assertion
    # that the 1.0 reference or its analysis-results extension was reproduced.
    return {
        "comparison_completed": True, "comparable_metadata_equal": not delta,
        "unexpected_differences": unexpected, "known_gap_difference_count": len(delta) - len(unexpected),
        "full_reference_reproduced": False,
        "byte_identical": reference_path.read_bytes() == candidate_path.read_bytes(),
        "reference_define_version": "1.0.0", "candidate_define_version": "2.0.0",
        "reference_inventory": reference.inventory(), "coverage": {"reference": coverage(expected), "candidate": coverage(actual)},
        "field_counts": dict(Counter(row["status"] for row in rows)), "differences": delta,
        "conversions": reference.conversions, "unsupported": reference.unsupported,
        "unresolved": reference.unresolved, "fields": rows,
        "representation": {"reference_root": reference.root.attrib, "candidate_root": candidate.root.attrib,
                           "reference_metadata_version": reference.md.attrib, "candidate_metadata_version": candidate.md.attrib,
                           "reference_stylesheets": [m.decode("ascii") for m in re.findall(br"<\?xml-stylesheet\s+(.*?)\?>", reference_path.read_bytes())],
                           "candidate_stylesheets": [m.decode("ascii") for m in re.findall(br"<\?xml-stylesheet\s+(.*?)\?>", candidate_path.read_bytes())]},
        "mapping_policy": [
            "Read only the published legacy XML as the comparison oracle; native generation uses authored YAML.",
            "Keep the original ADaM 2.1 model citation visible separately from the data guide's ADaMIG 1.0 citation.",
            "Map ADSL, ADAE and BDS classes explicitly; retain their original values in conversions.",
            "Resolve the legacy labels, origins, comments and domain keys into their 2.0 structures.",
            "Infer PARAMCD equality only when the value's Name occurs in that dataset's linked PARAMCD codelist.",
            "Compare relative value-list order while separately reporting original OrderNumber values.",
            "Unknown source content remains a difference; known unsupported draft results and document leaves remain inventoried.",
            "Missing legacy key variables remain unresolved and are not invented in either the data or XML.",
        ],
    }
