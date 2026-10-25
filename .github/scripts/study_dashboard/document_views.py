"""Browser views of retained workbooks and original Define-XML stylesheets."""

import html
import shutil

from lxml import etree
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter


def workbook_body(path):
    """Keep sheet, row and column coordinates, merged cells and literal cell text."""
    book = load_workbook(path, data_only=False)
    sections, tables = [], []
    try:
        navigation = (
            "<nav>"
            + " | ".join(
                f'<a href="#sheet-{n}">{html.escape(sheet.title)}</a>'
                for n, sheet in enumerate(book, 1)
            )
            + "</nav>"
        )
        for n, sheet in enumerate(book, 1):
            merged, covered = {}, set()
            for region in sheet.merged_cells.ranges:
                merged[region.min_row, region.min_col] = (
                    region.max_row - region.min_row + 1,
                    region.max_col - region.min_col + 1,
                )
                covered.update(
                    (r, c)
                    for r in range(region.min_row, region.max_row + 1)
                    for c in range(region.min_col, region.max_col + 1)
                    if (r, c) != (region.min_row, region.min_col)
                )
            rows = []
            for number, row in enumerate(sheet.iter_rows(), 1):
                values = [str(c.value) if c.value is not None else "" for c in row]
                anchor = f"sheet-{n}-row-{number}"
                if any(values):
                    sections.append(
                        {
                            "id": anchor,
                            "title": f"{sheet.title} / row {number}",
                            "text": " | ".join(values),
                        }
                    )
                cells = []
                for column, cell in enumerate(row, 1):
                    if (number, column) in covered:
                        continue
                    rowspan, colspan = merged.get((number, column), (1, 1))
                    style = "white-space:pre-wrap;min-width:100px;max-width:600px;"
                    if cell.font.bold:
                        style += "font-weight:bold;"
                    cells.append(
                        f'<td rowspan="{rowspan}" colspan="{colspan}" style="{style}">{html.escape(values[column - 1])}</td>'
                    )
                rows.append(
                    f'<tr id="{anchor}"><th scope="row">{number}</th>{"".join(cells)}</tr>'
                )
            headings = "".join(
                f'<th scope="col">{get_column_letter(c)}</th>'
                for c in range(1, sheet.max_column + 1)
            )
            tables.append(
                f'<section id="sheet-{n}"><h2>{html.escape(sheet.title)}</h2><div style="overflow:auto"><table><caption>{html.escape(sheet.title)}</caption><thead><tr><th scope="col">Row</th>{headings}</tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>'
            )
        return navigation + "".join(tables), sections
    finally:
        book.close()


def render_xml(root, path, original, entry):
    """Apply the retained publisher stylesheet without restyling its HTML."""
    stylesheet = entry.get("stylesheet")
    if not stylesheet:
        return None
    source = (root / stylesheet).resolve()
    source.relative_to(root.resolve())
    retained = original.parent / source.name
    if source != retained.resolve():
        shutil.copyfile(source, retained)
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    transform = etree.XSLT(
        etree.parse(str(source), parser),
        access_control=etree.XSLTAccessControl.DENY_ALL,
    )
    view = original.with_name(original.name + ".original.html")
    view.write_bytes(bytes(transform(etree.parse(str(path), parser))))
    return view
