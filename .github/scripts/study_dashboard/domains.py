"""Display domain descriptions from the retained Define-XML metadata."""

import xml.etree.ElementTree as ET


def domain_labels(path):
    if not path.exists():
        return {}
    labels = {}
    for element in ET.parse(path).iter():
        if element.tag.rsplit("}", 1)[-1] != "ItemGroupDef":
            continue
        label = next(
            (
                value
                for key, value in element.attrib.items()
                if key.rsplit("}", 1)[-1] == "Label"
            ),
            "",
        )
        if not label:
            label = " ".join(
                " ".join("".join(child.itertext()).split())
                for child in element
                if child.tag.rsplit("}", 1)[-1] == "Description"
            )
        labels[element.attrib.get("Name", "")] = label
    return labels


def domain_keys(path):
    """Read Define 1 DomainKeys or Define 2 ItemRef KeySequence declarations."""
    if not path.exists():
        return {}
    root = ET.parse(path).getroot()
    names = {
        item.attrib["OID"]: item.attrib["Name"]
        for item in root.iter()
        if item.tag.rsplit("}", 1)[-1] == "ItemDef"
        and "OID" in item.attrib
        and "Name" in item.attrib
    }
    keys = {}
    for group in root.iter():
        if group.tag.rsplit("}", 1)[-1] != "ItemGroupDef":
            continue
        declared = next(
            (
                value for key, value in group.attrib.items()
                if key.rsplit("}", 1)[-1] == "DomainKeys"
            ),
            "",
        )
        if declared:
            columns = [name.strip() for name in declared.split(",") if name.strip()]
        else:
            refs = [
                ref
                for ref in group
                if ref.tag.rsplit("}", 1)[-1] == "ItemRef"
                and ref.attrib.get("KeySequence", "").isdigit()
            ]
            columns = [
                names.get(ref.attrib["ItemOID"], ref.attrib["ItemOID"].rsplit(".", 1)[-1])
                for ref in sorted(refs, key=lambda ref: int(ref.attrib["KeySequence"]))
            ]
        keys[group.attrib.get("Name", "")] = columns
    return keys
