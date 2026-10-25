"""Original document views retain structure, escape text and confine XSLT reads."""

from pathlib import Path
import sys
import tempfile
import unittest

from lxml import etree
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_dashboard.document_views import render_xml, workbook_body


class DocumentViewTests(unittest.TestCase):
    def test_workbook_keeps_coordinates_merges_formulas_and_escaped_cell_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spec.xlsx"
            book = Workbook()
            sheet = book.active
            sheet.title = "Rules & inputs"
            sheet["A1"] = "<script>source text</script>"
            sheet.merge_cells("A1:B1")
            sheet["B3"] = "=1+2"
            book.create_sheet("Output")["A1"] = "ADAE"
            book.save(path)
            body, sections = workbook_body(path)
            tree = etree.HTML(body)
            self.assertEqual(
                tree.xpath('string(//tr[@id="sheet-1-row-1"]/td)'),
                "<script>source text</script>",
            )
            self.assertEqual(tree.xpath('//tr[@id="sheet-1-row-1"]/td/@colspan'), ["2"])
            self.assertEqual(
                tree.xpath('//tr[@id="sheet-1-row-3"]/td/text()'), ["=1+2"]
            )
            self.assertEqual(tree.xpath("//script"), [])
            self.assertEqual(
                [s["id"] for s in sections],
                ["sheet-1-row-1", "sheet-1-row-3", "sheet-2-row-1"],
            )
            self.assertEqual(
                tree.xpath("//caption/text()"), ["Rules & inputs", "Output"]
            )

    def test_xml_uses_retained_publisher_html_and_denies_external_document_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "define.xml"
            source.write_text('<ODM><ItemDef Name="ASTDT"/></ODM>')
            stylesheet = root / "original.xsl"
            template = '<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"><xsl:output method="html"/><xsl:template match="/"><html><body><table id="published"><tr><td><xsl:value-of select="ODM/ItemDef/@Name"/></td></tr></table>EXTERNAL</body></html></xsl:template></xsl:stylesheet>'
            stylesheet.write_text(template.replace("EXTERNAL", ""))
            view = render_xml(root, source, source, {"stylesheet": "original.xsl"})
            self.assertEqual(
                etree.HTML(view.read_bytes()).xpath(
                    '//table[@id="published"]//td/text()'
                ),
                ["ASTDT"],
            )
            self.assertEqual(source.read_text(), '<ODM><ItemDef Name="ASTDT"/></ODM>')
            stylesheet.write_text(
                template.replace(
                    "EXTERNAL", "<xsl:value-of select=\"document('define.xml')\"/>"
                )
            )
            with self.assertRaises(etree.XSLTApplyError):
                render_xml(root, source, source, {"stylesheet": "original.xsl"})
            with self.assertRaises(ValueError):
                render_xml(root, source, source, {"stylesheet": "../outside.xsl"})


if __name__ == "__main__":
    unittest.main()
