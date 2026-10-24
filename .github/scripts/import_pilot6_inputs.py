#!/usr/bin/env python3
"""Import Pilot 6 SDTM from a checkout, verifying its DVC hashes before conversion.

Requires pyarrow and PyYAML. Read JSON from the checkout after `dvc pull`,
from --json-dir, or from a pinned Pilot 5 GitHub mirror with --mirror-ref.
Only byte-for-byte matches to the Pilot 6 DVC pointers are accepted.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.request import urlopen

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / 'submission-pilot6'
SOURCE_URL = 'https://github.com/RConsortium/submissions-pilot6-adams-tlfs'
MIRROR_URL = 'https://raw.githubusercontent.com/RConsortium/submissions-pilot5-datasetjson'


def dataset_table(raw, domain):
    """Decode SDTM Dataset-JSON 1.1, retaining order, text, nulls and labels."""
    data = json.loads(raw)
    if data['datasetJSONVersion'] != '1.1.0' or data['name'].lower() != domain:
        raise ValueError(f'{domain}: unexpected Dataset-JSON version or name')
    columns, rows = data['columns'], data['rows']
    names = [c['name'] for c in columns]
    if len(set(names)) != len(names) or len(rows) != data['records']:
        raise ValueError(f'{domain}: duplicate columns or incorrect record count')
    if any(len(row) != len(columns) for row in rows):
        raise ValueError(f'{domain}: row width does not match column metadata')
    arrays, fields = [], []
    for index, column in enumerate(columns):
        values = [row[index] for row in rows]
        kind = column['dataType']
        if kind == 'string':
            arrow_type = pa.large_string()
        elif kind == 'decimal':
            # Upstream serializes numeric values as text, including padded NA.
            values = [None if v is None or str(v).strip() in ('', 'NA', '.')
                      else float(v) for v in values]
            if any(v is not None and not math.isfinite(v) for v in values):
                raise ValueError(f'{domain}.{column["name"]}: nonfinite number')
            arrow_type = pa.float64()
        else:
            raise ValueError(f'{domain}.{column["name"]}: unsupported type {kind}')
        arrays.append(pa.array(values, type=arrow_type))
        fields.append(pa.field(column['name'], arrow_type,
                               metadata={b'yamaa:label': column['label'].encode()}))
    return pa.Table.from_arrays(arrays, schema=pa.schema(fields))


def same_dataset(left, right):
    """Ignore writer-level metadata, but require all values, types and labels."""
    return (left.equals(right) and
            all(a.metadata == b.metadata for a, b in zip(left.schema, right.schema)))


def run(args):
    source = args.source.resolve()
    commit = subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    subprocess.run(['git', '-C', str(source), 'diff', '--exit-code', 'HEAD', '--',
                    'data/sdtm', 'data/adam_reference'], check=True)
    if args.mirror_ref and not re.fullmatch(r'[0-9a-f]{40}', args.mirror_ref):
        raise ValueError('--mirror-ref must be a full Git commit SHA')
    manifest = {'source_repository': SOURCE_URL, 'source_commit': commit,
                'datasets': [], 'specifications': []}
    pointers = sorted((source / 'data/sdtm').glob('*.json.dvc'))
    if len(pointers) != 21:
        raise ValueError(f'Expected 21 SDTM pointers, found {len(pointers)}; review upstream changes')
    # Stage and verify the entire snapshot before replacing any tracked files.
    with tempfile.TemporaryDirectory() as temp:
        staged = Path(temp)
        replacements = []
        for pointer in pointers:
            entry, = yaml.safe_load(pointer.read_text())['outs']
            domain = pointer.name.removesuffix('.json.dvc')
            if entry['path'] != f'{domain}.json' or entry['hash'] != 'md5':
                raise ValueError(f'{domain}: unexpected DVC pointer')
            if args.mirror_ref:
                url = (f'{MIRROR_URL}/{args.mirror_ref}/pilot5-submission/'
                       f'pilot5-input/sdtmdata/datasetjson/{domain}.json')
                with urlopen(url, timeout=60) as response:
                    raw = response.read()
            else:
                raw = ((args.json_dir or source / 'data/sdtm') / entry['path']).read_bytes()
                url = None
            if len(raw) != entry['size'] or hashlib.md5(raw).hexdigest() != entry['md5']:
                raise ValueError(f'{domain}: JSON does not match the Pilot 6 DVC size/MD5')
            table = dataset_table(raw, domain)
            destination = STUDY / 'data/sdtm' / f'{domain}.parquet'
            identical = destination.exists() and same_dataset(pq.read_table(destination), table)
            if args.verify_only and not identical:
                raise ValueError(f'{domain}: staged Parquet differs from the source JSON')
            output = destination if identical else staged / destination.name
            if not identical:
                pq.write_table(table, output, compression='snappy')
                if not same_dataset(pq.read_table(output), table):
                    raise ValueError(f'{domain}: Parquet round-trip failed')
                replacements.append((output, destination))
            record = {
                'path': destination.relative_to(ROOT).as_posix(),
                'dvc_pointer': pointer.relative_to(source).as_posix(),
                'source_md5': entry['md5'], 'source_bytes': entry['size'],
                'rows': table.num_rows, 'columns': table.num_columns,
                'parquet_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            }
            if url:
                record['retrieved_from'] = url
            manifest['datasets'].append(record)
            print(f'{domain.upper()}: verified {table.num_rows:,} rows, {table.num_columns} columns', flush=True)
        for filename, target in [('define.xml', 'define-adam.xml'),
                                 ('pilot6-specs.xlsx', 'pilot6-specs.xlsx')]:
            original = source / 'data/adam_reference' / filename
            destination = STUDY / 'spec' / target
            raw = original.read_bytes()
            if not destination.exists() or destination.read_bytes() != raw:
                if args.verify_only:
                    raise ValueError(f'{target}: differs from upstream')
                output = staged / target
                output.write_bytes(raw)
                replacements.append((output, destination))
            manifest['specifications'].append({
                'path': destination.relative_to(ROOT).as_posix(),
                'source_path': original.relative_to(source).as_posix(),
                'sha256': hashlib.sha256(raw).hexdigest(),
            })
        manifest_path = STUDY / 'spec/source-snapshot.json'
        if args.verify_only:
            recorded = json.loads(manifest_path.read_text())
            # Verification may use a local DVC checkout instead of the mirror
            # used during import; retrieval history is not a content check.
            for snapshot in (recorded, manifest):
                for dataset in snapshot['datasets']:
                    dataset.pop('retrieved_from', None)
            if recorded != manifest:
                raise ValueError('Snapshot manifest differs from the verified source and Parquet files')
        else:
            for output, destination in replacements:
                shutil.copyfile(output, destination)
            manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        print(f'Verified {len(pointers)} SDTM inputs at Pilot 6 commit {commit}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Pilot 6 Git checkout')
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument('--json-dir', type=Path, help='directory of DVC-matching SDTM JSON files')
    inputs.add_argument('--mirror-ref', help='pinned Pilot 5 commit containing the same JSON files')
    parser.add_argument('--verify-only', action='store_true', help='check without changing files')
    run(parser.parse_args())


if __name__ == '__main__':
    main()
