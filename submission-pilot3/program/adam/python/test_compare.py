"""Adversarial checks for the optional Python comparator."""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from compare import compare


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.reference = pl.DataFrame({
            "STUDYID": ["SYNTHETIC", "SYNTHETIC"],
            "USUBJID": ["A", "B"], "VALUE": [1.0, 1.0],
        })

    def compare(self, output, reference=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return compare(output, self.reference if reference is None else reference, "adsl")

    def test_identical(self):
        result = self.compare(self.reference)
        self.assertTrue(result["ok"])
        self.assertEqual(result["exact_cells"], 6)

    def test_duplicate_derived_keys(self):
        duplicate = self.reference.with_columns(pl.lit("A").alias("USUBJID"))
        with self.assertRaisesRegex(AssertionError, "duplicate derived keys"):
            self.compare(duplicate)

    def test_duplicate_reference_keys(self):
        duplicate = self.reference.with_columns(pl.lit("A").alias("USUBJID"))
        with self.assertRaisesRegex(AssertionError, "duplicate reference keys"):
            self.compare(self.reference, duplicate)

    def test_missing_column_keeps_reference_denominator(self):
        result = self.compare(self.reference.drop("VALUE"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["cells"], (4, 6))

    def test_extra_column_fails(self):
        self.assertFalse(self.compare(self.reference.with_columns(pl.lit(0).alias("EXTRA")))["ok"])

    def test_column_order_fails(self):
        self.assertFalse(self.compare(self.reference.select("VALUE", "STUDYID", "USUBJID"))["ok"])

    def test_tolerance_is_separate(self):
        output = self.reference.with_columns((pl.col("VALUE") + 1e-12).alias("VALUE"))
        result = self.compare(output)
        self.assertTrue(result["ok"])
        self.assertEqual(result["exact_cells"], 4)
        self.assertEqual(result["tolerance_cells"], 2)

    def test_blank_null_is_separate_and_fails(self):
        reference = self.reference.with_columns(pl.lit("").alias("VALUE"))
        output = reference.with_columns(pl.lit(None, dtype=pl.String).alias("VALUE"))
        result = self.compare(output, reference)
        self.assertFalse(result["ok"])
        self.assertEqual(result["exact_cells"], 4)
        self.assertEqual(result["blank_null_cells"], 2)

    def test_saved_labels_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            reference = Path(directory) / "reference.parquet"
            output = Path(directory) / "output.parquet"
            table = self.reference.to_arrow()
            fields = [field.with_metadata({b"yamaa:label": field.name.encode()}) for field in table.schema]
            pq.write_table(pa.Table.from_arrays(table.columns, schema=pa.schema(fields)), reference)
            pq.write_table(table, output)
            self.assertFalse(self.compare(output, reference)["ok"])


if __name__ == "__main__":
    unittest.main()
