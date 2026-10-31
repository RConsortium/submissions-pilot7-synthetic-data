"""The two-source review must use actual output bytes and explicit XML scope."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from study_dashboard.dataset_define import build_report, formula, logical_type, selected_rows


XML = '''<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3" xmlns:def="http://www.cdisc.org/ns/def/v2.0">
<Study OID="S"><GlobalVariables><StudyName>S</StudyName><StudyDescription>S</StudyDescription><ProtocolName>S</ProtocolName></GlobalVariables>
<MetaDataVersion OID="M" Name="M" def:DefineVersion="2.0.0" def:StandardName="ADaM-IG" def:StandardVersion="1.1">
<ItemGroupDef OID="IG.ADSL" Name="ADSL" Repeating="No" IsReferenceData="No" Purpose="Analysis">
<ItemRef ItemOID="IT.ID" OrderNumber="1" Mandatory="No" KeySequence="1"/>
<ItemRef ItemOID="IT.CODE" OrderNumber="2" Mandatory="No"/>
<ItemRef ItemOID="IT.AGE" OrderNumber="3" Mandatory="No"/>
</ItemGroupDef>
<ItemDef OID="IT.ID" Name="USUBJID" DataType="text" Length="3"><Description><TranslatedText>ID</TranslatedText></Description><def:Origin Type="Predecessor"/></ItemDef>
<ItemDef OID="IT.CODE" Name="CODE" DataType="text" Length="1"><Description><TranslatedText>Code</TranslatedText></Description><CodeListRef CodeListOID="CL.CODE"/></ItemDef>
<ItemDef OID="IT.AGE" Name="AGE" DataType="integer" Length="8"><Description><TranslatedText>Age</TranslatedText></Description></ItemDef>
<CodeList OID="CL.CODE" Name="Codes" DataType="text"><EnumeratedItem CodedValue="Y"/><EnumeratedItem CodedValue="N"/></CodeList>
</MetaDataVersion></Study></ODM>'''


class DatasetDefineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / 'study'
        self.define = self.base / 'spec/define/define-adam.xml'
        self.define.parent.mkdir(parents=True)
        self.define.write_text(XML)
        self.output = self.base / 'data/adam/adsl-yamaa.parquet'
        self.output.parent.mkdir(parents=True)
        self.target = self.root / 'export'
        self.target.mkdir()

    def report(self, values=None, xml=None):
        if xml is not None:
            self.define.write_text(xml)
        table = pa.table(values or {'USUBJID': ['001', '002'], 'CODE': ['Y', 'N'], 'AGE': [65., 70.]})
        schema = pa.schema([f.with_metadata({b'yamaa:label': {'USUBJID': b'ID', 'CODE': b'Code', 'AGE': b'Age'}.get(f.name, b'Extra')}) for f in table.schema])
        pq.write_table(table.cast(schema), self.output)
        # An independent reference intentionally disagrees. It is outside this review.
        pq.write_table(pa.table({'USUBJID': ['999'], 'CODE': ['X']}), self.output.with_name('adsl.parquet'))
        return build_report(self.root, 'study', {'ADSL': self.output}, self.target, 'revision')

    def test_reads_actual_output_and_only_retained_define(self):
        r = self.report()
        self.assertEqual(r['sources']['datasets'][0]['path'], 'study/data/adam/adsl-yamaa.parquet')
        self.assertEqual(r['sources']['datasets'][0]['rows'], 2)
        self.assertEqual([d['path'] for d in r['documents']], ['study/spec/define/define-adam.xml'])
        self.assertEqual(r['documents'][0]['view'], r['documents'][0]['source'])
        self.assertIn('id="ADSL.USUBJID"', (self.target / r['documents'][0]['view']).read_text())
        self.assertNotIn('different', r['check_counts'])
        self.assertTrue(all(c['comparison'] == 'dataset_define' for c in r['review']['checks']))
        self.assertFalse(any(e['type'] == 'specification' for e in r['review']['evidence']))

    def test_measures_complete_bad_values_and_keys(self):
        r = self.report({'USUBJID': ['001', '001', None], 'CODE': ['XX', 'Y', 'XX'], 'AGE': [65.5, 70., 80.]})
        checks = {c['check']: c for c in r['checks'] if c['status'] == 'different'}
        self.assertTrue({'keys', 'text_length', 'codelist', 'logical_type'}.issubset(checks))
        issue = next(i for i in r['review']['issues'] if i['variable'] == 'CODE' and 'codelist' in i['title'].lower())
        evidence = [e for e in r['review']['evidence'] if e['id'] in {t['evidence_id'] for t in issue['trace']} and e['type'] == 'comparison'][0]
        self.assertEqual((evidence['compared'], evidence['differ']), (3, 2))
        self.assertEqual(evidence['subjects'], ['001'])

    def test_reverse_inventory_and_missing_variable_are_visible(self):
        r = self.report({'USUBJID': ['001'], 'CODE': ['Y'], 'EXTRA': [1]})
        inventory = {(c['variable'], c['status']) for c in r['checks'] if c['check'] == 'variable_inventory'}
        self.assertEqual(inventory, {('AGE', 'different'), ('EXTRA', 'gap')})

    def test_broken_xml_references_are_unassessed(self):
        r = self.report(xml=XML.replace('CodeListOID="CL.CODE"', 'CodeListOID="MISSING"'))
        self.assertEqual(r['check_counts'], {'not_assessed': 1})
        self.assertEqual(r['findings'], [])
        self.assertIn('Dangling XML reference', r['coverage_items'][0]['reason'])

    def test_value_level_scope_requires_present_columns_and_supported_predicates(self):
        variables = {'CODE': {'type': 'text'}}
        clause = {'variable': 'CODE', 'comparator': 'EQ', 'values': ['Y']}
        self.assertEqual(selected_rows([{'CODE': 'Y'}, {'CODE': 'N'}], [clause], variables), [{'CODE': 'Y'}])
        self.assertIsNone(selected_rows([{'OTHER': 'Y'}], [clause], variables))
        self.assertIsNone(selected_rows([{'CODE': 'Y'}], [{**clause, 'comparator': 'NE'}], variables))

    def test_integer_storage_checks_values_not_arrow_width(self):
        item = {'type': 'integer', 'display_format': None}
        self.assertTrue(logical_type(pa.field('N', pa.float64()), item, [1., None]))
        self.assertFalse(logical_type(pa.field('N', pa.float64()), item, [1.5]))
        self.assertTrue(logical_type(pa.field('N', pa.float64()), item, [1.000000000000001]))

    def test_numeric_codelists_tolerate_binary_representation_only(self):
        from study_dashboard.dataset_define import member
        self.assertTrue(member(4.199999999999999, {'4.2'}, 'float'))
        self.assertFalse(member(4.21, {'4.2'}, 'float'))

    def test_predecessor_origin_names_missing_source_variable(self):
        source = self.base / 'data/sdtm/dm.parquet'
        source.parent.mkdir(parents=True)
        pq.write_table(pa.table({'USUBJID': ['001', '002']}), source)
        xml = XML.replace('<def:Origin Type="Predecessor"/>', '<def:Origin Type="Predecessor"><Description><TranslatedText>DM.MISSING</TranslatedText></Description></def:Origin>')
        result = self.report(xml=xml)
        issue = next(f for f in result['findings'] if f['check'] == 'predecessor_source')
        self.assertIn('DM has no variable MISSING', issue['observation'])

    def test_assigned_origin_alone_is_not_a_documentation_defect(self):
        result = self.report(xml=XML.replace('Type="Predecessor"', 'Type="Assigned"'))
        self.assertFalse(any(f['variable'] == 'USUBJID' and f['check'] == 'origin_method' for f in result['findings']))

    def test_significant_digits_does_not_hide_gross_formula_error(self):
        xml = XML.replace('OrderNumber="3" Mandatory="No"', 'OrderNumber="3" Mandatory="No" MethodOID="MT.AGE"')
        xml = xml.replace('DataType="integer" Length="8"', 'DataType="integer" Length="8" SignificantDigits="1"')
        xml = xml.replace('</MetaDataVersion>', '<MethodDef OID="MT.AGE" Name="Age" Type="Computation"><Description><TranslatedText>AGE + 10</TranslatedText></Description></MethodDef></MetaDataVersion>')
        result = self.report(xml=xml)
        self.assertTrue(any(f['check'] == 'arithmetic_method' for f in result['findings']))

    def test_precision_compatible_difference_is_coverage_not_a_pass(self):
        xml = XML.replace('OrderNumber="3" Mandatory="No"', 'OrderNumber="3" Mandatory="No" MethodOID="MT.AGE"')
        xml = xml.replace('DataType="integer" Length="8"', 'DataType="integer" Length="8" SignificantDigits="1"')
        xml = xml.replace('</MetaDataVersion>', '<MethodDef OID="MT.AGE" Name="Age" Type="Computation"><Description><TranslatedText>AGE + 0.01</TranslatedText></Description></MethodDef></MetaDataVersion>')
        result = self.report(xml=xml)
        self.assertTrue(any(c['check'] == 'numeric_precision' and c['status'] == 'not_assessed' for c in result['checks']))
        self.assertTrue(any('numeric_precision' in c['id'] for c in result['coverage_items']))
        self.assertFalse(any(c['check'] == 'arithmetic_method' and c['status'] == 'passed' for c in result['checks']))

    def test_native_legacy_value_level_type_overrides_parent_type(self):
        xml = XML.replace('odm/v1.3', 'odm/v1.2').replace('def/v2.0', 'def/v1.0').replace('CODE', 'PARAMCD')
        xml = xml.replace('DataType="integer" Length="8"', 'DataType="float" Length="8"')
        xml = xml.replace('<Description><TranslatedText>Age</TranslatedText></Description></ItemDef>', '<Description><TranslatedText>Age</TranslatedText></Description><def:ValueListRef ValueListOID="VL.AGE"/></ItemDef>')
        xml = xml.replace('</MetaDataVersion>', '<def:ValueListDef OID="VL.AGE"><ItemRef ItemOID="IT.AGE.Y" OrderNumber="1" Mandatory="No"/></def:ValueListDef><ItemDef OID="IT.AGE.Y" Name="Y" DataType="integer" Length="8" def:Label="Age"/></MetaDataVersion>')
        result = self.report({'USUBJID': ['001', '002'], 'PARAMCD': ['Y', 'N'], 'AGE': [1.5, 2.5]}, xml=xml)
        finding = next(f for f in result['findings'] if f['check'] == 'logical_type_value_level_1')
        self.assertEqual(finding['evidence']['dataset_check']['compared'], 1)
        self.assertEqual(finding['evidence']['dataset_check']['differ'], 1)
        self.assertFalse(any(f['variable'] == 'AGE' and f['check'] == 'logical_type' for f in result['findings']))

    def test_postbaseline_scope_excludes_unflagged_prebaseline_records(self):
        from datetime import date
        xml = XML.replace('OrderNumber="3" Mandatory="No"', 'OrderNumber="3" Mandatory="No" MethodOID="MT.AGE"')
        xml = xml.replace('</MetaDataVersion>', '<MethodDef OID="MT.AGE" Name="Age" Type="Computation"><Description><TranslatedText>AGE + 1, for post baseline records</TranslatedText></Description></MethodDef></MetaDataVersion>')
        result = self.report({'USUBJID': ['001'] * 3, 'CODE': ['Y'] * 3, 'AGE': [65.] * 3,
                              'ABLFL': ['', 'Y', ''], 'ADT': [date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 3)]}, xml=xml)
        finding = next(f for f in result['findings'] if f['variable'] == 'AGE' and f['check'] == 'arithmetic_method')
        self.assertEqual(finding['evidence']['dataset_check']['compared'], 1)

    def test_value_level_predecessor_overrides_parent_source_scope(self):
        source = self.base / 'data/sdtm/dm.parquet'
        source.parent.mkdir(parents=True)
        pq.write_table(pa.table({'USUBJID': ['001', '002'], 'CODE': ['N', 'N'], 'VLCODE': ['N', 'N']}), source)
        xml = XML.replace('<CodeListRef CodeListOID="CL.CODE"/>', '<CodeListRef CodeListOID="CL.CODE"/><def:Origin Type="Predecessor"><Description><TranslatedText>DM.CODE</TranslatedText></Description></def:Origin><def:ValueListRef ValueListOID="VL.CODE"/>')
        xml = xml.replace('</MetaDataVersion>', '''<def:ValueListDef OID="VL.CODE"><ItemRef ItemOID="IT.CODE.Y" OrderNumber="1" Mandatory="No"><def:WhereClauseRef WhereClauseOID="WC.Y"/></ItemRef></def:ValueListDef>
<ItemDef OID="IT.CODE.Y" Name="CODE" DataType="text" Length="1"><Description><TranslatedText>Code</TranslatedText></Description><def:Origin Type="Predecessor"><Description><TranslatedText>DM.VLCODE</TranslatedText></Description></def:Origin></ItemDef>
<def:WhereClauseDef OID="WC.Y"><RangeCheck Comparator="EQ" SoftHard="Soft" def:ItemOID="IT.CODE"><CheckValue>Y</CheckValue></RangeCheck></def:WhereClauseDef></MetaDataVersion>''')
        result = self.report(xml=xml)
        copied = [f for f in result['findings'] if f['check'].startswith('predecessor_copy')]
        self.assertEqual(len(copied), 1)
        self.assertEqual(copied[0]['check'], 'predecessor_copy_value_level_1')
        self.assertEqual(copied[0]['evidence']['dataset_check']['compared'], 1)

    def test_key_sequence_does_not_invent_a_nonmissing_requirement(self):
        r = self.report({'USUBJID': ['001', None], 'CODE': ['Y', 'N'], 'AGE': [65., 70.]})
        self.assertEqual(next(c['status'] for c in r['checks'] if c['check'] == 'keys'), 'passed')
        self.assertEqual(next(c['status'] for c in r['checks'] if c['check'] == 'missing_key_values'), 'not_assessed')

    def test_literal_arithmetic_uses_only_this_dataset_and_preserves_missing(self):
        calculate = formula('ADSL.END - START + 1', 'ADSL', {'START', 'END'})
        from datetime import date
        self.assertEqual(calculate({'START': date(2026, 1, 1), 'END': date(2026, 1, 3)}), 3)
        self.assertIsNone(calculate({'START': None, 'END': 3}))
        self.assertIsNone(formula('DM.AGE', 'ADSL', {'AGE'}))
        self.assertIsNone(formula('__import__("os").system("bad")', 'ADSL', {'AGE'}))
        self.assertIsNone(formula('AGE ** 999999', 'ADSL', {'AGE'}))

    def test_arithmetic_conflict_contains_actual_and_expected_values(self):
        xml = XML.replace('OrderNumber="3" Mandatory="No"', 'OrderNumber="3" Mandatory="No" MethodOID="MT.AGE"')
        xml = xml.replace('</MetaDataVersion>', '<MethodDef OID="MT.AGE" Name="Age" Type="Computation"><Description><TranslatedText>AGE + 1</TranslatedText></Description></MethodDef></MetaDataVersion>')
        r = self.report(xml=xml)
        evidence = next(e for e in r['review']['evidence'] if e['type'] == 'comparison' and e['column'] == 'AGE')
        self.assertEqual((evidence['compared'], evidence['differ']), (2, 2))
        self.assertEqual(evidence['patterns'][0]['observed'], 66.)
        quotes = [e for e in r['review']['evidence'] if e['type'] == 'document']
        for e in quotes:
            first, last = e['lines']
            self.assertEqual(e['quote'], '\n'.join(xml.splitlines()[first-1:last]))

    def test_value_level_membership_uses_selected_population(self):
        xml = XML.replace('</ItemDef>\n<ItemDef OID="IT.AGE"', '<def:ValueListRef ValueListOID="VL.CODE"/></ItemDef>\n<ItemDef OID="IT.AGE"')
        xml = xml.replace('</MetaDataVersion>', '''<def:ValueListDef OID="VL.CODE"><ItemRef ItemOID="IT.CODE.Y" OrderNumber="1" Mandatory="No"><def:WhereClauseRef WhereClauseOID="WC.Y"/></ItemRef></def:ValueListDef>
<ItemDef OID="IT.CODE.Y" Name="CODE" DataType="text" Length="1"><Description><TranslatedText>Code</TranslatedText></Description><CodeListRef CodeListOID="CL.ONLYN"/></ItemDef>
<CodeList OID="CL.ONLYN" Name="Only N" DataType="text"><EnumeratedItem CodedValue="N"/></CodeList>
<def:WhereClauseDef OID="WC.Y"><RangeCheck Comparator="EQ" SoftHard="Soft" def:ItemOID="IT.CODE"><CheckValue>Y</CheckValue></RangeCheck></def:WhereClauseDef></MetaDataVersion>''')
        r = self.report(xml=xml)
        finding = next(f for f in r['findings'] if f['check'] == 'codelist_value_level_1')
        self.assertEqual((finding['evidence']['dataset_check']['compared'], finding['evidence']['dataset_check']['differ']), (1, 1))



if __name__ == '__main__':
    unittest.main()
