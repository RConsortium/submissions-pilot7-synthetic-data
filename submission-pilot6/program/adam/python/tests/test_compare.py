"""Reference comparison must detect structural and value errors."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

MODULE = Path(__file__).resolve().parents[1] / 'compare.py'
loader = importlib.util.spec_from_file_location('pilot6_compare', MODULE)
compare = importlib.util.module_from_spec(loader)
loader.loader.exec_module(compare)


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.spec = self.root / 'adsl.yaml'
        self.names = ['STUDYID', 'USUBJID', 'DOSE', 'FLAG']
        self.spec.write_text(yaml.safe_dump({'output': {'columns': self.names},
            'columns': [{'name': n, 'label': n} for n in self.names]}))
        self.reference = self.root / 'official.parquet'
        self.output = self.root / 'derived.parquet'
        self.rows = [{'STUDYID': 'S', 'USUBJID': s, 'DOSE': dose, 'FLAG': flag}
                     for s, dose, flag in [('1', 10., ''), ('2', 20., 'Y')]]
        self.schema = pa.schema([pa.field(n, pa.float64() if n == 'DOSE' else pa.string(),
                                 metadata={b'yamaa:label': n.encode()}) for n in self.names])
        self.write(self.reference, self.rows)

    def write(self, path, rows, schema=None):
        pq.write_table(pa.Table.from_pylist(rows, schema=schema or self.schema), path)

    def check(self):
        return compare.compare(self.output, self.reference, self.spec)['ok']

    def test_key_alignment_tolerance_and_r_missing_strings(self):
        rows = [dict(r) for r in reversed(self.rows)]
        rows[1].update(DOSE=10. + 5e-11, FLAG=None)
        self.write(self.output, rows)
        self.assertTrue(self.check())

    def test_changed_value_fails(self):
        rows = [dict(r) for r in self.rows]
        rows[0]['DOSE'] = 10. + 1e-5
        self.write(self.output, rows)
        self.assertFalse(self.check())

    def test_duplicate_and_missing_subjects_fail(self):
        self.write(self.output, [self.rows[0], self.rows[0]])
        with self.assertRaises(ValueError):
            self.check()
        self.write(self.output, [self.rows[0]])
        self.assertFalse(self.check())
        self.write(self.output, [dict(self.rows[0], USUBJID=None)])
        with self.assertRaises(ValueError):
            self.check()

    def test_extra_columns_fail(self):
        schema = pa.schema(list(self.schema) + [pa.field('EXTRA', pa.string())])
        self.write(self.output, self.rows, schema)
        self.assertFalse(self.check())

    def test_wrong_types_and_labels_fail(self):
        schema = self.schema.set(2, pa.field('DOSE', pa.string()))
        self.write(self.output, [dict(r, DOSE=str(r['DOSE'])) for r in self.rows], schema)
        self.assertFalse(self.check())
        self.write(self.output, self.rows)
        schema = self.schema.set(2, pa.field('DOSE', pa.float64(), metadata={b'yamaa:label': b'Wrong'}))
        self.write(self.reference, self.rows, schema)
        self.assertFalse(self.check())

    def test_missing_reference_never_passes(self):
        self.reference.unlink()
        with self.assertRaises(FileNotFoundError):
            self.check()


if __name__ == '__main__':
    unittest.main()
