"""Define viewers publish validated bytes, with escaped XML and no stale comparisons."""

import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_dashboard.define_comparison import export_comparison
from study_artifacts import artifact_snapshot, verify_artifacts


class DefineComparisonTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        project = self.root / 'study/spec/yamaa/project.yaml'
        project.parent.mkdir(parents=True)
        project.write_text('adam: {define: ../../data/adam/generated.xml}\n')
        self.paths = {
            'reference': self.root / 'study/spec/define/define-adam.xml',
            'candidate': self.root / 'study/data/adam/generated.xml',
        }
        self.evidence = {'comparison': 'different', 'metadata': {'differences': [
            {'path': '/study/StudyName', 'reference': 'original', 'candidate': 'generated'}]}}
        for side, path in self.paths.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f'<ODM>\n  <script>{side} &amp; source</script>\n</ODM>\n')
            self.evidence[f'{side}_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.target = self.root / 'bundle'
        self.target.mkdir()

    def test_exact_compared_xml_and_evidence_are_exported_with_inert_numbered_source(self):
        result = export_comparison(self.root, 'study', self.target, {'define_xml': self.evidence})
        self.assertEqual(json.loads((self.target / result['evidence']).read_text()), self.evidence)
        for side, path in self.paths.items():
            with self.subTest(side=side):
                doc = result[side]
                self.assertEqual(doc['path'], path.relative_to(self.root).as_posix())
                self.assertEqual((self.target / doc['original']).read_bytes(), path.read_bytes())
                tree = etree.HTML((self.target / doc['source']).read_bytes())
                self.assertEqual(tree.xpath('//li/@id'), ['L1', 'L2', 'L3'])
                self.assertEqual(tree.xpath('//li/code/text()'), path.read_text().splitlines())
                self.assertEqual(tree.xpath('//script'), [])
                self.assertEqual((doc['view'], doc['view_label']), (doc['source'], 'XML source'))

    def test_retained_stylesheets_render_both_versions_without_changing_compared_bytes(self):
        repository = Path(__file__).resolve().parents[3]
        stylesheet = 'submission-pilot3/spec/define/define2-0-0.xsl'
        config = self.root / '.github/dashboard.json'
        config.parent.mkdir()
        config.write_text(json.dumps({'define_stylesheets': {'2.0.0': stylesheet}}))
        retained = self.root / stylesheet
        retained.parent.mkdir(parents=True)
        shutil.copyfile(repository / stylesheet, retained)
        for study in ('cdiscpilot01', 'submission-pilot3'):
            with self.subTest(study=study):
                manifest = json.loads((repository / study / 'spec/source/manifest.json').read_text())
                entry = manifest['files'][0]
                manifest_path = self.root / 'study/spec/source/manifest.json'
                manifest_path.parent.mkdir(exist_ok=True)
                manifest_path.write_text(json.dumps({'files': [{
                    'path': 'study/spec/define/define-adam.xml', 'stylesheet': entry['stylesheet']}]}))
                retained = self.root / entry['stylesheet']
                retained.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(repository / entry['stylesheet'], retained)
                self.paths['reference'].write_bytes((repository / entry['path']).read_bytes())
                self.paths['candidate'].write_bytes(
                    (repository / '.github/tests/fixtures/legacy-define/candidate.xml').read_bytes())
                for side, path in self.paths.items():
                    self.evidence[f'{side}_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
                result = export_comparison(self.root, 'study', self.target, {'define_xml': self.evidence})
                for side, path in self.paths.items():
                    doc = result[side]
                    self.assertEqual((self.target / doc['original']).read_bytes(), path.read_bytes())
                    self.assertEqual(doc['view_label'], 'Rendered Define-XML')
                    tree = etree.HTML((self.target / doc['view']).read_bytes())
                    self.assertTrue(tree.xpath('//table'))
                    self.assertIn('USUBJID', tree.xpath('string(//body)'))
                    source = etree.HTML((self.target / doc['source']).read_bytes())
                    encoding = etree.parse(str(path)).docinfo.encoding
                    self.assertEqual(source.xpath('//li/code/text()'),
                                     [line or ' ' for line in path.read_text(encoding=encoding).splitlines()])
                shutil.rmtree(self.target / 'define')

    def test_shared_generated_stylesheet_changes_invalidate_validation(self):
        self.paths['reference'].write_text('<ODM DefineVersion="1.0.0"/>')
        self.paths['candidate'].write_text('<ODM DefineVersion="2.0.0"/>')
        config = self.root / '.github/dashboard.json'
        config.parent.mkdir()
        config.write_text(json.dumps({'define_stylesheets': {'2.0.0': 'shared/define.xsl'}}))
        stylesheet = self.root / 'shared/define.xsl'
        stylesheet.parent.mkdir()
        stylesheet.write_text('retained stylesheet')
        report = {'artifacts': artifact_snapshot(self.root, 'study')}
        self.assertIn('shared/define.xsl', report['artifacts']['files'])
        verify_artifacts(self.root, 'study', report)
        stylesheet.write_text('changed stylesheet')
        with self.assertRaisesRegex(ValueError, 'artifacts changed.*shared/define.xsl'):
            verify_artifacts(self.root, 'study', report)

    def test_changed_or_missing_compared_files_block_export(self):
        for side, path in self.paths.items():
            original = path.read_bytes()
            for content in (b'changed XML', None):
                with self.subTest(side=side, content=content):
                    if content is None:
                        path.unlink()
                    else:
                        path.write_bytes(content)
                    with self.assertRaisesRegex(ValueError, f'{side} Define-XML changed'):
                        export_comparison(self.root, 'study', self.target, {'define_xml': self.evidence})
                    path.write_bytes(original)
                    shutil.rmtree(self.target / 'define')

    def test_source_view_uses_the_xml_declaration_and_keeps_download_bytes_unchanged(self):
        path = self.paths['reference']
        for encoding in ('ISO-8859-1', 'UTF-8', 'UTF-16'):
            with self.subTest(encoding=encoding):
                text = f'<?xml version="1.0" encoding="{encoding}"?>\n<ODM>caf\u00e9 &amp; source</ODM>'
                original = text.encode(encoding)
                path.write_bytes(original)
                self.evidence['reference_sha256'] = hashlib.sha256(original).hexdigest()
                result = export_comparison(self.root, 'study', self.target, {'define_xml': self.evidence})
                doc = result['reference']
                self.assertEqual((self.target / doc['original']).read_bytes(), original)
                tree = etree.HTML((self.target / doc['view']).read_bytes())
                self.assertEqual(tree.xpath('//li/code/text()'), text.splitlines())
                shutil.rmtree(self.target / 'define')

    def test_uncompared_existing_files_are_not_presented_as_validated_xml(self):
        result = export_comparison(self.root, 'study', self.target, {})
        self.assertEqual([result[s]['available'] for s in self.paths], [False, False])
        self.assertEqual(list((self.target / 'define').glob('*.xml')), [])

    def test_no_define_declaration_omits_the_comparison_bundle(self):
        (self.root / 'study/spec/yamaa/project.yaml').write_text('adam: {specs: []}')
        self.assertIsNone(export_comparison(self.root, 'study', self.target, {}))


if __name__ == '__main__':
    unittest.main()
