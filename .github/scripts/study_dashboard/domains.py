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
