"""The two-source review must use actual output bytes and explicit XML scope."""

from pathlib import Path
import hashlib
import json
import sys
from tempfile import TemporaryDirectory
import unittest

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from study_dashboard.dataset_define import build_report, formula, logical_type, selected_rows
from study_evidence import reviewed_datasets
from study_artifacts import artifact_snapshot
from study_dashboard.workspace import build_workspace


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
        self.assertIn('Dangling XML reference', r['findings'][0]['observation'])

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

    def test_scoped_study_does_not_require_multisource_claim_reports(self):
        import json
        (self.base / 'spec/yamaa').mkdir()
        (self.base / 'spec/yamaa/project.yaml').write_text('adam: {specs: [adsl.yaml]}')
        (self.base / 'spec/yamaa/adsl.yaml').write_text('domain: ADSL')
        (self.base / 'spec/review').mkdir()
        (self.base / 'spec/review/adsl-claims.json').write_text('{}')
        (self.root / '.github').mkdir()
        (self.root / '.github/yamaa-studies.json').write_text(json.dumps({'study': {'dashboard': {'review_scope': 'dataset_define'}}}))
        self.assertEqual(reviewed_datasets(self.root, 'study'), [])

    def workspace(self, destination):
        """Full navigation fixture with a separately scoped finding report."""
        from openpyxl import Workbook

        self.report({'USUBJID': ['001', '002', '003'], 'CODE': ['Y', 'X', 'N'], 'AGE': [65., 70., 75.]})
        sdtm = self.base / 'data/sdtm/dm.parquet'
        sdtm.parent.mkdir()
        pq.write_table(pa.table({'USUBJID': ['001', '004'], 'AGE': [65., 80.]}), sdtm)
        source = self.base / 'spec/source'
        source.mkdir()
        workbook = Workbook()
        workbook.active.append(['Variable', 'Description'])
        workbook.active.append(['AGE', 'Age in years'])
        workbook.save(source / 'guide.xlsx')
        (source / 'manifest.json').write_text(json.dumps({'files': [
            {'path': 'study/spec/source/guide.xlsx', 'role': 'specification'}]}))
        specs = self.base / 'spec/yamaa'
        specs.mkdir()
        (specs / 'project.yaml').write_text('adam: {specs: [adsl.yaml], define: ../../data/adam/define.xml}')
        (specs / 'adsl.yaml').write_text('''domain: ADSL
keys: [USUBJID]
input: {DM: {path: ../../data/sdtm/dm.parquet}}
output: {path: ../../data/adam/adsl-yamaa.parquet, columns: [USUBJID, CODE, AGE]}
columns:
  - {name: USUBJID, type: str, label: ID, derivation: DM.USUBJID}
  - {name: CODE, type: str, label: Code, derivation: "'Y'"}
  - {name: AGE, type: float, label: Age, derivation: DM.AGE}
''')
        candidate = self.output.with_name('define.xml')
        candidate.write_bytes(self.define.read_bytes())
        digest = hashlib.sha256(self.define.read_bytes()).hexdigest()
        validation = {'status': 'succeeded', 'datasets': [{'domain': 'ADSL', 'build': 'succeeded',
                       'comparison': 'unavailable', 'rows': 3, 'columns': 3}],
                      'define_xml': {'comparison': 'matched', 'reference_sha256': digest,
                                     'candidate_sha256': digest},
                      'artifacts': artifact_snapshot(self.root, 'study')}
        entry = {'title': 'Two-source browser fixture', 'description': 'Synthetic fixture; no study results.',
                 'source': 'https://example.test', 'dashboard': {'review_scope': 'dataset_define'}}
        return build_workspace(self.root, destination, 'study', entry, validation, 'fixture')

    def test_focused_findings_retain_full_workspace_artifacts(self):
        catalog = self.workspace(self.target)
        target = self.target / 'study'
        report = json.loads((target / 'report.json').read_text())
        self.assertEqual(report['scope'], 'dataset_define')
        self.assertIn('study/spec/source/guide.xlsx', [d['path'] for d in report['documents']])
        define = next(d for d in report['documents'] if d['path'] == 'study/spec/define/define-adam.xml')
        self.assertTrue((target / define['source']).is_file())
        self.assertEqual(json.loads((target / 'documents.json').read_text()), report['documents'])
        self.assertTrue(all(e['path'] == define['path'] for e in report['review']['evidence'] if e['type'] == 'document'))
        self.assertFalse(any(e['type'] == 'specification' for e in report['review']['evidence']))
        self.assertEqual(catalog['subjects'], ['001', '002', '003', '004', '999'])
        dataset = catalog['datasets'][0]
        self.assertTrue(dataset['inputs'])
        self.assertIsNotNone(dataset['reference'])
        output = catalog['tables'][dataset['output']]
        self.assertEqual(output['key_source'], 'study/spec/yamaa/adsl.yaml')
        self.assertEqual(output['columns'][0]['declared_label'], 'ID')
        for side in ('reference', 'candidate'):
            self.assertTrue(catalog['define_comparison'][side]['available'])


if __name__ == '__main__':
    unittest.main()
