"""Exercise CORE orchestration with a local engine fixture and no network."""

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from discover_core_studies import discover_studies, has_validatable_data
from run_core import ROOT, resolve_ct, run_study


class CoreRunnerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.stage = self.root / 'staging'
        for domain, dataset in [('sdtm', 'dm'), ('adam', 'adsl')]:
            directory = self.root / 'study/data' / domain
            directory.mkdir(parents=True)
            (directory / f'{dataset}.xpt').write_bytes(b'fixture')
        cache = self.root / 'engine'
        cache.mkdir()
        for package in ('sdtmct-2024-09-27', 'adamct-2024-09-27'):
            (cache / f'{package}.pkl').touch()
        self.engine = cache / 'core'
        self.engine.write_text('''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
args = sys.argv
standard = args[args.index('--standard') + 1]
if os.environ.get('TEST_CORE_MODE') == 'missing-adam' and standard == 'adam':
    raise SystemExit(2)
data = Path(args[args.index('--data') + 1])
output = Path(args[args.index('--output') + 1])
report = {'Dataset_Details': [{'filename': p.name} for p in sorted(data.glob('*.xpt'))],
          'Issue_Summary': [], 'Issue_Details': [],
          'Rules_Report': [] if standard == 'adam' else [{'core_id': 'fixture-rule'}]}
output.with_suffix('.json').write_text(json.dumps(report))
if os.environ.get('TEST_CORE_MODE') == 'invalid-json':
    output.with_suffix('.json').write_text('{invalid')
output.with_suffix('.xlsx').write_bytes(b'fixture workbook')
raise SystemExit(1 if os.environ.get('TEST_CORE_MODE') == 'nonzero' else 0)
''')
        self.engine.chmod(0o755)

    def run_engine(self, mode=''):
        with patch.dict(os.environ, {'TEST_CORE_MODE': mode, 'GITHUB_STEP_SUMMARY': ''}), redirect_stdout(io.StringIO()):
            return run_study(self.root, 'study', self.engine, self.stage)

    def record(self, domain):
        return json.loads((self.stage / f'study/data/{domain}/core-execution.json').read_text())

    def test_stages_both_standards_and_preserves_zero_rules_guard(self):
        self.assertEqual(self.run_engine(), 0)
        record = self.record('sdtm')
        self.assertEqual(record['inputs'], ['dm.xpt'])
        self.assertEqual(record['covered'], ['DM'])
        self.assertEqual(record['engine_exit_code'], 0)
        self.assertEqual(record['status'], 'report_generated')
        adam = self.stage / 'study/data/adam'
        self.assertTrue((adam / 'core-report-ADAM.xlsx').exists())
        markdown = (adam / 'dataset_comment.md').read_text()
        self.assertIn('UNVERIFIED', markdown)
        self.assertNotIn('[PASS]', markdown)
        self.assertEqual(self.record('adam')['conformance'], 'unverified')

    def test_nonzero_engine_exit_is_recorded_separately_from_report_presence(self):
        self.assertEqual(self.run_engine('nonzero'), 0)
        self.assertEqual(self.record('sdtm')['engine_exit_code'], 1)
        self.assertEqual(self.record('sdtm')['status'], 'report_generated')

    def test_invalid_json_fails_and_is_retained_for_diagnosis(self):
        self.assertEqual(self.run_engine('invalid-json'), 1)
        self.assertEqual(self.record('sdtm')['status'], 'failed')
        self.assertTrue((self.stage / 'study/data/sdtm/core-report-SDTM.json').exists())
        self.assertFalse((self.stage / 'study/data/sdtm/dataset_comment.md').exists())

    def test_missing_report_fails_without_reusing_stale_success(self):
        self.assertEqual(self.run_engine(), 0)
        self.assertEqual(self.run_engine('missing-adam'), 1)
        self.assertEqual(self.record('adam')['status'], 'failed')
        self.assertEqual(self.record('adam')['engine_exit_code'], 2)
        self.assertFalse((self.stage / 'study/data/adam/core-report-ADAM.json').exists())
        self.assertFalse((self.stage / 'study/data/adam/dataset_comment.md').exists())
        self.assertEqual(self.record('sdtm')['status'], 'report_generated')

    def test_partial_conversion_reports_skips_and_all_failed_conversion_fails(self):
        source = self.root / 'study/data/sdtm'
        for name in ('dm', 'bad'):
            (source / f'{name}.parquet').touch()

        def convert(path, destination):
            if Path(path).stem == 'bad':
                return False, 'bad.parquet: SKIPPED'
            (Path(destination) / f'{Path(path).stem}.xpt').write_bytes(b'converted')
            return True, 'converted'

        with patch.dict('sys.modules', {'parquet_to_xpt': SimpleNamespace(convert_one=convert)}):
            self.assertEqual(self.run_engine(), 0)
        record = self.record('sdtm')
        self.assertEqual(record['inputs'], ['bad.parquet', 'dm.parquet'])
        self.assertEqual(record['skipped'], ['bad.parquet'])
        self.assertEqual(record['covered'], ['DM'])
        self.assertEqual(record['status'], 'partial')
        converter = SimpleNamespace(convert_one=lambda *args: (False, 'SKIPPED'))
        with patch.dict('sys.modules', {'parquet_to_xpt': converter}):
            self.assertEqual(self.run_engine(), 1)
        self.assertEqual(self.record('sdtm')['status'], 'failed')
        self.assertEqual(self.record('sdtm')['prepared'], [])

    def test_ct_fallback_is_explicit_and_absent_cache_fails(self):
        with redirect_stdout(io.StringIO()) as log:
            self.assertEqual(resolve_ct(self.engine.parent, 'sdtmct-1900-01-01'),
                             'sdtmct-2024-09-27')
        self.assertIn('WARNING', log.getvalue())
        with self.assertRaises(RuntimeError):
            resolve_ct(self.engine.parent, 'missingct-1900-01-01')

    def test_discovery_keeps_scaffolds_separate_from_core_inputs(self):
        for name in ('scaffold', 'docs', '.archieve'):
            (self.root / name).mkdir()
        studies = discover_studies(str(self.root), ['docs', 'engine'])
        self.assertEqual(studies, ['scaffold', 'study'])
        self.assertEqual([name for name in studies if has_validatable_data(str(self.root), name)],
                         ['study'])

    def test_delivery_copies_only_publishable_reports_and_preserves_reference_data(self):
        import yaml

        workflow = yaml.safe_load((ROOT / '.github/workflows/core-validate.yml').read_text())
        step = next(step for step in workflow['jobs']['deliver']['steps']
                    if step.get('name') == 'Copy publishable reports into study folders')
        incoming = self.root / '_dl/study/data/adam'
        incoming.mkdir(parents=True)
        for name in ('core-report-ADAM.json', 'core-report-ADAM.xlsx',
                     'core-execution.json', 'dataset_comment.md', 'adsl.parquet'):
            (incoming / name).write_text('artifact')
        reference = self.root / 'study/data/adam/adsl.parquet'
        reference.write_text('independent reference')
        subprocess.run(['bash', '-c', step['run']], cwd=self.root, check=True)
        published = self.root / 'study/data/adam'
        self.assertTrue((published / 'core-report-ADAM.xlsx').exists())
        self.assertTrue((published / 'dataset_comment.md').exists())
        self.assertFalse((published / 'core-report-ADAM.json').exists())
        self.assertFalse((published / 'core-execution.json').exists())
        self.assertEqual(reference.read_text(), 'independent reference')


if __name__ == '__main__':
    unittest.main()
