"""Protect the clinical comparison policy and SDTM interchange format."""

import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

import verify_upstream as verify


def table(values, name='VALUE', label='Value', kind=pa.float64()):
    schema = pa.schema([pa.field(name, kind, metadata={b'yamaa:label': label.encode()})])
    return pa.Table.from_arrays([pa.array(values, type=kind)], schema=schema)


class ComparisonTests(unittest.TestCase):
    def test_all_program_libraries_are_locked(self):
        locked = set(json.loads((verify.HERE / 'renv.lock').read_text())['Packages'])
        files = [verify.HERE / 'upstream/code/adam' / filename for _, filename, _ in verify.PROGRAMS]
        files += [verify.HERE / 'run_upstream.R', verify.HERE / 'upstream/code/utils/save_dataset_json.r']
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
        spec = importlib.util.spec_from_file_location('pilot6_import', verify.ROOT / '.github/scripts/import_pilot6_inputs.py')
        importer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(importer)
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
            self.assertIn(payload['columns'][0]['targetDataType'], ('integer', 'decimal'))
            restored = importer.dataset_table(output.read_bytes(), 'dm')
            self.assertTrue(importer.same_dataset(source, restored))


if __name__ == '__main__':
    unittest.main()
