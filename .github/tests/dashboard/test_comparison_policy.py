"""Submitted blank, null and numeric values must be compared without repair."""

from contextlib import redirect_stdout
import importlib.util
from io import StringIO
from pathlib import Path
import unittest


@unittest.skipUnless(importlib.util.find_spec('polars'), 'requires study comparison tools')
class ComparisonPolicyTests(unittest.TestCase):
    def test_original_missing_values_and_column_set_are_preserved(self):
        import polars as pl
        root = Path(__file__).resolve().parents[3]
        cases = [('', None, False), ('', '', True), (None, None, True),
                 (float('nan'), None, False), (float('nan'), float('nan'), True),
                 (float('inf'), float('inf'), True), (1.0, 1.0 + 5e-11, True),
                 (1.0, 1.0 + 2e-10, False)]
        for study in ['submission-pilot3', 'submission-pilot5']:
            source = root / study / 'program/adam/python/compare.py'
            spec = importlib.util.spec_from_file_location('study_compare', source)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for expected, observed, matches in cases:
                with self.subTest(study=study, expected=expected, observed=observed):
                    numeric = isinstance(expected, float)
                    dtype = pl.Float64 if numeric else pl.String
                    reference = pl.DataFrame({'STUDYID': ['S'], 'USUBJID': ['S1']}).with_columns(pl.Series('VALUE', [expected], dtype=dtype))
                    output = reference.with_columns(pl.Series('VALUE', [observed], dtype=dtype))
                    with redirect_stdout(StringIO()):
                        self.assertEqual(module.compare(output, reference, 'adsl')['ok'], matches)
            with redirect_stdout(StringIO()):
                self.assertFalse(module.compare(reference.with_columns(pl.lit(1).alias('EXTRA')), reference, 'adsl')['ok'])
