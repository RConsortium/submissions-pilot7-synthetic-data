"""Retained submission documents and exact, escaped reading-copy locations."""

import html
import json
import shutil
import xml.etree.ElementTree as ET

from pypdf import PdfReader

from .document_views import render_xml, workbook_body


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, separators=(",", ":")) + "\n")


def local_name(element):
    return element.tag.rsplit("}", 1)[-1]


def description(element):
    text = " ".join(
        " ".join("".join(x.itertext()).split())
        for x in element
        if local_name(x) == "Description"
    ).strip()
    # Define-XML 1.0 stores the label in def:Label, not Description.
    return text or next(
        (v for k, v in element.attrib.items() if k.rsplit("}", 1)[-1] == "Label"), ""
    )


def attributes(element):
    return {k.rsplit("}", 1)[-1]: v for k, v in element.attrib.items()}


def define_metadata(path):
    """Variable metadata by dataset for Define-XML 1.0 and 2.x.

    Define 2.x states derivations in MethodDef and notes in CommentDef. Define
    1.0 has neither: its derivation text is the ItemDef Comment attribute.
    """
    tree = ET.parse(path)
    items = {x.attrib["OID"]: x for x in tree.iter() if local_name(x) == "ItemDef"}
    methods, comments, codelists = {}, {}, {}
    for x in tree.iter():
        if local_name(x) == "MethodDef":
            methods[x.attrib["OID"]] = description(x)
        elif local_name(x) == "CommentDef":
            comments[x.attrib["OID"]] = description(x)
        elif local_name(x) == "CodeList":
            external = next(
                (attributes(i) for i in x if local_name(i) == "ExternalCodeList"), None
            )
            codelists[x.attrib["OID"]] = {
                "items": [
                    {
                        # Published coded values can carry non-breaking spaces.
                        "value": (i.attrib.get("CodedValue") or "").strip(),
                        "decode": " ".join("".join(i.itertext()).split()),
                    }
                    for i in x
                    if local_name(i) in {"CodeListItem", "EnumeratedItem"}
                ],
                "external": external,
            }
    groups = {}
    for group in tree.iter():
        if local_name(group) != "ItemGroupDef":
            continue
        fields = {}
        for reference in group:
            if local_name(reference) != "ItemRef":
                continue
            item = items.get(reference.attrib.get("ItemOID"))
            if item is None:
                continue
            attrs = attributes(item)
            codelist = next(
                (
                    c.attrib.get("CodeListOID")
                    for c in item
                    if local_name(c) == "CodeListRef"
                ),
                None,
            )
            fields[item.attrib["Name"]] = {
                "label": description(item),
                "type": item.attrib.get("DataType"),
                "oid": item.attrib["OID"],
                "method": methods.get(reference.attrib.get("MethodOID"), ""),
                "comment": (
                    attrs.get("Comment", "").strip()
                    or comments.get(attrs.get("CommentOID"), "")
                ),
                "origin": attrs.get("Origin", ""),
                "significant_digits": attrs.get("SignificantDigits", ""),
                "codelist": (
                    {
                        "oid": codelist,
                        **codelists.get(codelist, {"items": [], "external": None}),
                    }
                    if codelist
                    else None
                ),
            }
        groups[group.attrib.get("Name", "")] = fields
    return groups


def define_section_text(item):
    """The reading-copy text of one Define variable; citations quote this text."""
    lines = [f'Label: {item["label"]}', f'Data type: {item["type"]}']
    for name, key in [
        ("Origin", "origin"),
        ("Significant digits", "significant_digits"),
        ("Method", "method"),
        ("Comment", "comment"),
    ]:
        if item.get(key):
            lines.append(f"{name}: {item[key]}")
    if item.get("codelist"):
        codelist = item["codelist"]
        values = "; ".join(f'{c["value"]} = {c["decode"]}' for c in codelist["items"])
        if codelist.get("external"):
            external = codelist["external"]
            values = " ".join(
                filter(None, [external.get("Dictionary"), external.get("Version")])
            ) + " (external dictionary)"
        lines.append(f'Codelist {codelist["oid"]}: {values}')
    return "\n".join(lines)


def document_sections(path, metadata):
    """Stable, citable sections: PDF pages and Define-XML variables."""
    if path.suffix.lower() == ".pdf":
        return [
            {"id": f"page-{number}", "title": f"Page {number}", "text": page.extract_text() or ""}
            for number, page in enumerate(PdfReader(path).pages, 1)
        ]
    if path.name == "define-adam.xml":
        return [
            {
                "id": f"{domain}.{name}",
                "title": f'{domain}.{name} / {item["oid"]}',
                "text": define_section_text(item),
            }
            for domain, columns in metadata.items()
            for name, item in columns.items()
        ]
    return []


def document_html(title, body):
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title><style>"
        "body{font:16px/1.7 system-ui;margin:30px auto;padding:0 24px;max-width:1000px;color:#24344a}"
        "section{border-bottom:1px solid #ddd;padding:24px 0;scroll-margin-top:20px}"
        "pre{white-space:pre-wrap;font:inherit}td,th{padding:8px;border:1px solid #ddd;vertical-align:top}"
        "table{border-collapse:collapse}a{color:#2d5f8a}:target{background:#fff5d6}"
        "</style><body>" + f"<h1>{html.escape(title)}</h1>" + body + "</body></html>"
    )


def materials(root, study, target, metadata):
    folder = target / "documents"
    folder.mkdir(exist_ok=True)
    manifest_path = root / study / "spec/source/manifest.json"
    manifest = (
        json.loads(manifest_path.read_text())
        if manifest_path.exists()
        else {"files": []}
    )
    documents = []
    entries = list(manifest.get("files", []))
    known = {e["path"] for e in entries}
    for path in sorted((root / study / "spec/define").glob("*.xml")):
        relative = path.relative_to(root).as_posix()
        if relative not in known:
            entries.append({"path": relative, "role": "published_metadata"})
    for section in ('sdtm', 'adam'):
        path = root / study / f'data/{section}/define.xml'
        relative = path.relative_to(root).as_posix()
        if path.is_file() and relative not in known:
            entries.append({'path': relative, 'role': 'generated_draft_metadata'})
    for entry in entries:
        path = root / entry["path"]
        path.resolve().relative_to(root.resolve())
        relative = path.relative_to(root)
        original = folder / relative
        if not path.is_file():
            documents.append(
                {
                    "name": path.name,
                    "path": entry["path"],
                    "available": False,
                    "role": entry.get("role"),
                    "upstream": entry.get("upstream", {}),
                    "sections": [],
                }
            )
            continue
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, original)
        record = {
            "name": path.name,
            "path": entry["path"],
            "role": entry.get("role"),
            "upstream": entry.get("upstream", {}),
            "original": f"documents/{relative.as_posix()}",
            "available": True,
            "sections": [],
        }
        if path.suffix.lower() == ".pdf":
            record.update(view=record["original"], view_label="Original PDF")
        elif path.suffix.lower() == '.mmd':
            view = original.with_name(original.name + '.html')
            view.write_text(document_html(path.name,
                '<p>Retained protocol/SAP conversion. Verify against the publisher PDF.</p><pre>'
                + html.escape(path.read_text()) + '</pre>'), encoding='ascii', errors='xmlcharrefreplace')
            record.update(view=view.relative_to(target).as_posix(), view_label='Retained protocol/SAP')
        elif path.suffix.lower() == ".xlsx":
            body, record["sections"] = workbook_body(path)
            view = original.with_name(original.name + ".table.html")
            view.write_text(
                document_html(
                    path.name,
                    "<p>Workbook cells in their original sheet, row and column positions. Formulas are shown as entered. The original Excel file is retained.</p>"
                    + body,
                ),
                encoding="utf-8",
            )
            record.update(
                view=view.relative_to(target).as_posix(), view_label="Excel tables"
            )
        elif path.suffix.lower() == ".xml":
            view = render_xml(root, path, original, entry)
            record.update(
                view=(
                    view.relative_to(target).as_posix() if view else record["original"]
                ),
                view_label="Original XML HTML" if view else "XML source",
            )
        record["sections"].extend(document_sections(path, metadata))
        if record["sections"]:
            body = "<p>Extracted reading copy. Verify against the linked original submission document.</p>"
            body += f'<p><a href="{html.escape(path.name)}">Open original {html.escape(path.name)}</a></p>'
            for section in record["sections"]:
                body += (
                    f'<section id="{html.escape(section["id"])}"><h2>{html.escape(section["title"])}</h2>'
                    f'<pre>{html.escape(section["text"])}</pre></section>'
                )
            reading = str(relative) + ".html"
            (folder / reading).write_text(
                document_html(path.name, body), encoding="utf-8"
            )
            record["reading"] = f"documents/{reading}"
        documents.append(record)
    save_json(target / "documents.json", documents)
    return manifest, documents
