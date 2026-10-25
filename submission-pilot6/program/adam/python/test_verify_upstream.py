"""Protect the clinical comparison policy and SDTM interchange format."""

import importlib.util
from io import BytesIO
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

import verify_upstream as verify

IMPORT_PATH = verify.ROOT / '.github/scripts/import_pilot6_inputs.py'
spec = importlib.util.spec_from_file_location('pilot6_import', IMPORT_PATH)
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


def table(values, name='VALUE', label='Value', kind=pa.float64()):
    schema = pa.schema([pa.field(name, kind, metadata={b'yamaa:label': label.encode()})])
    return pa.Table.from_arrays([pa.array(values, type=kind)], schema=schema)


class ComparisonTests(unittest.TestCase):
    def test_all_program_libraries_are_locked(self):
        packages = json.loads((verify.ADAM / 'renv.lock').read_text())['Packages']
        locked = set(packages)
        self.assertTrue(all(p['Source'] in ('Repository', 'GitHub') for p in packages.values()))
        files = [verify.ADAM / 'upstream/code/adam' / filename for _, filename, _ in verify.PROGRAMS]
        files += [verify.BOOTSTRAP, verify.ADAM / 'upstream/code/utils/save_dataset_json.r']
        for path in files:
            libraries = set(re.findall(r'\blibrary\(\s*([\w.]+)', path.read_text()))
            self.assertFalse(libraries - locked, f'{path.name}: unlocked packages {libraries - locked}')

    def test_failed_snapshot_check_cannot_reuse_old_success_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / 'report.json'
            report.write_text('{"status": "passed"}')
            with patch('sys.argv', ['verify_upstream.py', '--rscript', 'Rscript', '--report', str(report)]), \
                    patch.object(verify, 'verify_snapshot', side_effect=ValueError('checksum mismatch')):
                with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                    verify.main()
            self.assertFalse(report.exists())

    def test_absolute_tolerance_does_not_hide_large_value_errors(self):
        self.assertTrue(verify.compare_tables(table([1.0]), table([1.0 + 1e-11]))['passed'])
        self.assertFalse(verify.compare_tables(table([1e10]), table([1e10 + 0.1]))['passed'])

    def test_text_blanks_and_nulls_are_distinct(self):
        self.assertFalse(verify.compare_tables(table([''], kind=pa.large_string()),
                                               table([None], kind=pa.large_string()))['passed'])

    def test_labels_types_and_order_are_checked(self):
        reference = table([1.0, 2.0])
        self.assertFalse(verify.compare_tables(table([1.0, 2.0], label='Changed'), reference)['passed'])
        self.assertFalse(verify.compare_tables(table([1, 2], kind=pa.int64()), reference)['passed'])
        self.assertFalse(verify.compare_tables(table([2.0, 1.0]), reference)['passed'])
        self.assertFalse(verify.compare_tables(table([1.0, 2.0], name='RENAMED'), reference)['passed'])

    def test_sdtm_json_interoperates_with_existing_reader(self):
        numeric = table([1.25, None])
        text = table(['', None], name='TEXT', label='Text', kind=pa.large_string())
        source = pa.Table.from_arrays([numeric.column(0), text.column(0)],
                                     schema=pa.schema([numeric.schema[0], text.schema[0]]))
        with tempfile.TemporaryDirectory() as temp:
            path, output = Path(temp) / 'dm.parquet', Path(temp) / 'dm.json'
            pq.write_table(source, path)
            verify.materialize_sdtm(path, output)
            payload = json.loads(output.read_text())
            self.assertEqual(payload['records'], 2)
            # Upstream SDTM numerics are decimal/decimal text; adlbh.r reads them as text.
            self.assertEqual((payload['columns'][0]['dataType'], payload['columns'][0]['targetDataType']),
                             ('decimal', 'decimal'))
            self.assertEqual([row[0] for row in payload['rows']], ['1.25', None])
            restored = importer.dataset_table(output.read_bytes(), 'dm')
            self.assertTrue(importer.same_dataset(source, restored))

    def test_decimal_text_round_trips_and_rejects_nonfinite(self):
        for value in (56.72413793103448, 1.2345678901234567, 5e-07, -7.0):
            self.assertEqual(float(verify.decimal_text(value)), value)
        for value in (float('nan'), float('inf')):
            with self.assertRaisesRegex(ValueError, 'Nonfinite'):
                verify.decimal_text(value)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.study = self.root / 'submission-pilot6'
        self.manifest = json.loads((verify.STUDY / 'spec/source-snapshot.json').read_text())
        for group, key in [('datasets', 'parquet_sha256'), ('specifications', 'sha256'), ('programs', 'sha256')]:
            for entry in self.manifest[group]:
                path = self.root / entry['path']
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'fixture')
                entry[key] = verify.sha256(path)
        self.addCleanup(patch.stopall)
        patch.object(verify, 'ROOT', self.root).start()
        patch.object(verify, 'STUDY', self.study).start()

    def check_snapshot(self):
        (self.study / 'spec/source-snapshot.json').write_text(json.dumps(self.manifest))
        return verify.verify_snapshot()

    def test_complete_snapshot_passes(self):
        _, inputs = self.check_snapshot()
        self.assertEqual(len(inputs), 21)

    def test_deleting_input_and_manifest_entry_still_fails(self):
        for stage, name in [('sdtm', 'cm'), ('adam', 'adsl')]:
            with self.subTest(stage=stage):
                path = f'submission-pilot6/data/{stage}/{name}.parquet'
                entry = next(x for x in self.manifest['datasets'] if x['path'] == path)
                self.manifest['datasets'].remove(entry)
                (self.root / path).unlink()
                with self.assertRaisesRegex(ValueError, 'datasets snapshot inventory'):
                    self.check_snapshot()
                self.manifest['datasets'].append(entry)
                (self.root / path).write_bytes(b'fixture')

    def test_each_specification_is_required(self):
        for entry in list(self.manifest['specifications']):
            with self.subTest(path=entry['path']):
                self.manifest['specifications'].remove(entry)
                with self.assertRaisesRegex(ValueError, 'specifications snapshot inventory'):
                    self.check_snapshot()
                self.manifest['specifications'].append(entry)

    def test_duplicate_or_renamed_entries_fail(self):
        self.manifest['datasets'].append(dict(self.manifest['datasets'][0]))
        with self.assertRaisesRegex(ValueError, 'datasets snapshot inventory'):
            self.check_snapshot()
        self.manifest['datasets'].pop()
        self.manifest['datasets'][0]['path'] = 'submission-pilot6/data/sdtm/replacement.parquet'
        with self.assertRaisesRegex(ValueError, 'datasets snapshot inventory'):
            self.check_snapshot()

    def test_missing_source_utility_fails(self):
        self.manifest['programs'] = [x for x in self.manifest['programs']
                                     if x['source_path'] != 'code/utils/save_dataset_json.r']
        with self.assertRaisesRegex(ValueError, 'programs snapshot inventory'):
            self.check_snapshot()


class ProvenanceTests(unittest.TestCase):
    def test_local_input_modes_do_not_claim_an_s3_download(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pointer = root / 'sdtm/cm.json.dvc'
            pointer.parent.mkdir()
            (pointer.parent / 'cm.json').write_bytes(b'checkout')
            local = root / 'local'
            local.mkdir()
            (local / 'cm.json').write_bytes(b'local')
            for directory, expected in [(local, b'local'), (None, b'checkout')]:
                with self.subTest(directory=directory):
                    args = SimpleNamespace(json_dir=directory, mirror_ref=None)
                    self.assertEqual(importer.read_json_input(pointer, {'path': 'cm.json'}, args),
                                     (expected, None))

    def test_adam_uses_the_dvc_checkout_even_with_local_sdtm(self):
        with tempfile.TemporaryDirectory() as temp:
            pointer = Path(temp) / 'adam/adsl.json.dvc'
            pointer.parent.mkdir()
            (pointer.parent / 'adsl.json').write_bytes(b'adam')
            args = SimpleNamespace(json_dir=Path(temp) / 'unused', mirror_ref='a' * 40)
            self.assertEqual(importer.read_json_input(pointer, {'path': 'adsl.json'}, args), (b'adam', None))

    def test_mirror_records_the_url_actually_requested(self):
        args = SimpleNamespace(json_dir=None, mirror_ref='a' * 40)
        with patch.object(importer, 'urlopen', return_value=BytesIO(b'mirror')) as download:
            raw, url = importer.read_json_input(Path('data/sdtm/cm.json.dvc'), {'path': 'cm.json'}, args)
        self.assertEqual(raw, b'mirror')
        self.assertIn('/' + 'a' * 40 + '/', url)
        self.assertTrue(url.endswith('/cm.json'))
        download.assert_called_once_with(url, timeout=60)


class ExecutionTests(unittest.TestCase):
    def run_fixture(self, root, timeout_domain=None, missing_reference=None):
        study = root / 'submission-pilot6'
        (study / 'spec/define').mkdir(parents=True)
        for relative in ('spec/define/define-adam.xml', 'spec/pilot6-specs.xlsx', 'spec/source-snapshot.json'):
            (study / relative).write_text('{}')
        (study / 'data/adam').mkdir(parents=True)
        for domain in verify.REFERENCE_DOMAINS - {missing_reference}:
            pq.write_table(table([1.0]), study / 'data/adam' / f'{domain}.parquet')
        script = root / '.github/scripts/import_pilot6_inputs.py'
        script.parent.mkdir(parents=True)
        shutil.copyfile(IMPORT_PATH, script)
        report = study / 'log/report.json'
        calls = []

        def rscript(command, **kwargs):
            work = kwargs['cwd']
            if '-e' in command:
                (work / 'runtime-observed.json').write_text('{}')
            else:
                domain = next(d for d, filename, _ in verify.PROGRAMS if filename == command[-1])
                calls.append(domain)
                # Even a partial output from a timed-out process cannot count as success.
                payload = {'datasetJSONVersion': '1.1.0', 'name': domain, 'records': 1,
                           'columns': [{'name': 'VALUE', 'dataType': 'float', 'label': 'Value'}],
                           'rows': [[1.0]]}
                (work / 'data/adam' / f'{domain}.json').write_text(json.dumps(payload))
                if domain == timeout_domain:
                    raise subprocess.TimeoutExpired(command, 600, output=b'partial stdout', stderr=b'partial stderr')
            return subprocess.CompletedProcess(command, 0, stdout='', stderr='')

        with patch.object(verify, 'ROOT', root), patch.object(verify, 'STUDY', study), \
                patch.object(verify, 'verify_snapshot', return_value=({'source_commit': 'fixture', 'programs': []}, [])), \
                patch.object(verify.subprocess, 'run', side_effect=rscript), \
                patch('sys.argv', ['verify_upstream.py', '--report', str(report)]):
            status = verify.main()
        return status, json.loads(report.read_text()), calls

    def test_success_requires_eight_matches_with_only_two_known_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            status, report, _ = self.run_fixture(Path(temp))
        self.assertEqual(status, 0)
        self.assertEqual(report['summary']['matched'], 8)
        self.assertEqual({x['domain'] for x in report['datasets'] if x['comparison'] == 'reference_unavailable'},
                         {'ADLBHY', 'ADCIBC'})

    def test_missing_required_reference_cannot_become_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            status, report, _ = self.run_fixture(Path(temp), missing_reference='adsl')
        self.assertEqual(status, 1)
        self.assertEqual(report['datasets'][0]['comparison'], 'failed')
        self.assertIn('Required reference is missing', report['datasets'][0]['error'])

    def test_timeout_keeps_logs_writes_report_and_blocks_children(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            status, report, calls = self.run_fixture(root, timeout_domain='adlbc')
            log, = (root / '.build/pilot6-upstream').glob('*/logs/adlbc.log')
            self.assertIn('partial stdoutpartial stderr', log.read_text())
            self.assertIn('timed out after 600 seconds', log.read_text())
        self.assertEqual(status, 1)
        records = {x['domain']: x for x in report['datasets']}
        self.assertTrue(records['ADLBC']['timed_out'])
        self.assertEqual(records['ADLBC']['generation'], 'failed')
        self.assertEqual(records['ADLBHY']['generation'], 'blocked')
        self.assertNotIn('adlbhy', calls)
        self.assertIn('adcibc', calls)


if __name__ == '__main__':
    unittest.main()
