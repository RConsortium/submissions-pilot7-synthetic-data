#!/usr/bin/env python3
"""Compare ADSL with the official Pilot 6 reference, failing on missing evidence.

Rows align by unique, nonmissing STUDYID/USUBJID. Columns, logical types and
specification labels must match. Numeric absolute tolerance is 1e-10;
missing character values normalize to the R empty-string convention.
"""

import argparse
import math
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

STUDY = Path(__file__).resolve().parents[3]
KEYS = ('STUDYID', 'USUBJID')
TOLERANCE = 1e-10


def kind(dtype):
    if pa.types.is_integer(dtype) or pa.types.is_floating(dtype):
        return 'numeric'
    if pa.types.is_string(dtype) or pa.types.is_large_string(dtype):
        return 'string'
    if pa.types.is_date(dtype):
        return 'date'
    return str(dtype)


def equal(a, b, dtype):
    if dtype == 'string':
        return (a or '') == (b or '')
    if dtype == 'numeric':
        a = None if isinstance(a, float) and math.isnan(a) else a
        b = None if isinstance(b, float) and math.isnan(b) else b
        if a is None or b is None:
            return a is b
        return a == b or math.isclose(a, b, rel_tol=0, abs_tol=TOLERANCE)
    return a == b


def keyed(table):
    rows = {}
    for row in table.to_pylist():
        key = tuple(row[k] for k in KEYS)
        if any(v is None or v == '' for v in key):
            raise ValueError('ADSL contains a missing subject key')
        if key in rows:
            raise ValueError(f'ADSL contains a duplicate subject key: {key}')
        rows[key] = row
    return rows


def compare(output, reference, spec):
    output, reference = Path(output), Path(reference)
    if not reference.is_file():
        raise FileNotFoundError(f'Official Pilot 6 reference is unavailable: {reference}')
    new, ref = pq.read_table(output), pq.read_table(reference)
    declaration = yaml.safe_load(Path(spec).read_text())
    expected = declaration['output']['columns']
    labels = {c['name']: c.get('label') for c in declaration['columns']}
    errors = []
    if new.column_names != expected or ref.column_names != expected:
        errors.append('Column names/order differ from the ADSL specification')
    if not set(KEYS) <= set(new.column_names) & set(ref.column_names):
        errors.append('Subject key columns are missing')
    if errors:
        return {'ok': False, 'errors': errors}
    for field in ref.schema:
        if kind(new.schema.field(field.name).type) != kind(field.type):
            errors.append(f'{field.name}: logical type mismatch')
        actual = (field.metadata or {}).get(b'yamaa:label')
        expected_label = labels.get(field.name)
        if not expected_label or actual != expected_label.encode():
            errors.append(f'{field.name}: official label differs from specification')
    if errors:
        return {'ok': False, 'errors': errors}
    left, right = keyed(new), keyed(ref)
    if set(left) != set(right):
        errors.append('Subject keys differ from the official reference')
    mismatches = 0
    for key in left.keys() & right.keys():
        for field in ref.schema:
            name = field.name
            if not equal(left[key][name], right[key][name], kind(field.type)):
                mismatches += 1
                if len(errors) < 20:
                    errors.append(f'{key}, {name}: value mismatch')
    return {'ok': not errors, 'rows': ref.num_rows, 'columns': ref.num_columns,
            'mismatched_cells': mismatches, 'errors': errors}


def compare_domain(name='adsl', data_root=None):
    if name.lower() != 'adsl':
        raise ValueError('Only ADSL is implemented for Pilot 6')
    data = Path(data_root) if data_root else STUDY / 'data'
    result = compare(data / 'adam/adsl-yamaa.parquet', data / 'adam/adsl.parquet',
                     STUDY / 'spec/yamaa/adsl.yaml')
    print(f"ADSL reference comparison: {'PASS' if result['ok'] else 'FAIL'} {result}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, help='directory containing adam/ references and outputs')
    args = parser.parse_args()
    try:
        return int(not compare_domain(data_root=args.data_root)['ok'])
    except (FileNotFoundError, ValueError) as error:
        print(f'FAIL: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
