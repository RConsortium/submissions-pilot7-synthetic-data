#!/usr/bin/env python3
"""Import Pilot 6 SDTM and ADaM, verifying DVC hashes before conversion.

Requires pyarrow and PyYAML. Read JSON from the checkout after `dvc pull`,
with optional SDTM inputs from --json-dir or a pinned Pilot 5 --mirror-ref.
ADaM JSON is always read from the DVC-pulled checkout.
Only byte-for-byte matches to the Pilot 6 DVC pointers are accepted.
"""

import argparse
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.request import urlopen
from xml.etree import ElementTree as ET

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / 'submission-pilot6'
SOURCE_URL = 'https://github.com/RConsortium/submissions-pilot6-adams-tlfs'
MIRROR_URL = 'https://raw.githubusercontent.com/RConsortium/submissions-pilot5-datasetjson'
DATA_UTILITIES = (
    'code/utils/compare_data.r',
    'code/utils/dvc_compare.sh',
    'code/utils/save_dataset_json.r',
)


def record_columns(source, domain):
    """Recover metadata for the upstream plain-record ADNPIX export."""
    ns = {'o': 'http://www.cdisc.org/ns/odm/v1.3'}
    root = ET.parse(source / 'data/adam_reference/define.xml').getroot()
    items = {x.attrib['OID']: x for x in root.findall('.//o:ItemDef', ns)}
    group = next(x for x in root.findall('.//o:ItemGroupDef', ns)
                 if x.attrib['Name'] == domain.upper())
    columns = []
    for ref in group.findall('o:ItemRef', ns):
        item = items[ref.attrib['ItemOID']]
        kind = item.attrib['DataType']
        if item.attrib.get('{http://www.cdisc.org/ns/def/v2.1}DisplayFormat') == 'DATE9.':
            kind = 'date'
        columns.append({
            'name': item.attrib['Name'], 'dataType': kind,
            'label': item.findtext('o:Description/o:TranslatedText', namespaces=ns),
        })
    return columns


def dataset_table(raw, domain, source=None):
    """Decode Dataset-JSON or ADNPIX records, preserving order, text and labels."""
    data = json.loads(raw)
    if isinstance(data, list):
        if domain != 'adnpix' or source is None:
            raise ValueError(f'{domain}: plain records require ADNPIX Define-XML metadata')
        columns = record_columns(source, domain)
        names = [column['name'] for column in columns]
        if any(set(row) != set(names) for row in data):
            raise ValueError(f'{domain}: records do not match Define-XML')
        data = {'datasetJSONVersion': '1.1.0', 'name': domain,
                'columns': columns, 'records': len(data),
                'rows': [[row[name] for name in names] for row in data]}
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
        if kind in ('string', 'text', 'datetime'):
            # Retain partial ISO datetime text, including ADSL DTC variables.
            arrow_type = pa.large_string()
        elif kind == 'date':
            values = [date.fromisoformat(v) if v is not None else None for v in values]
            arrow_type = pa.date32()
        elif kind in ('decimal', 'integer', 'float', 'double'):
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


def read_json_input(pointer, entry, args):
    """Return bytes and a retrieval URL only when this call downloads them."""
    stage = pointer.parent.name
    domain = pointer.name.removesuffix('.json.dvc')
    if stage == 'sdtm' and args.mirror_ref:
        url = (f'{MIRROR_URL}/{args.mirror_ref}/pilot5-submission/'
               f'pilot5-input/sdtmdata/datasetjson/{domain}.json')
        with urlopen(url, timeout=60) as response:
            return response.read(), url
    directory = args.json_dir if stage == 'sdtm' and args.json_dir else pointer.parent
    return (directory / entry['path']).read_bytes(), None


def run(args):
    source = args.source.resolve()
    commit = subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    subprocess.run(['git', '-C', str(source), 'diff', '--exit-code', 'HEAD', '--',
                    '.dvc/config', '.Rprofile', 'code/adam', *DATA_UTILITIES,
                    'data/sdtm', 'data/adam', 'data/adam_reference'], check=True)
    if args.mirror_ref and not re.fullmatch(r'[0-9a-f]{40}', args.mirror_ref):
        raise ValueError('--mirror-ref must be a full Git commit SHA')
    manifest = {'source_repository': SOURCE_URL, 'source_commit': commit,
                'dvc_remote': 's3://rconsortium-pilots',
                'endpoint': 'https://s3.us-east-1.amazonaws.com',
                'datasets': [], 'specifications': [], 'programs': []}
    tracked = subprocess.check_output(['git', '-C', str(source), 'ls-files'], text=True).splitlines()
    pointers = []
    for stage, expected in (('sdtm', 21), ('adam', 8)):
        paths = sorted(p for p in tracked if p.startswith(f'data/{stage}/') and p.endswith('.json.dvc'))
        if len(paths) != expected:
            raise ValueError(f'Expected {expected} {stage} pointers, found {len(paths)}; review upstream changes')
        pointers.extend(source / p for p in paths)
    # Stage and verify the entire snapshot before replacing any tracked files.
    with tempfile.TemporaryDirectory() as temp:
        staged = Path(temp)
        replacements = []
        for pointer in pointers:
            entry, = yaml.safe_load(pointer.read_text())['outs']
            domain = pointer.name.removesuffix('.json.dvc')
            stage = pointer.parent.name
            if entry['path'] != f'{domain}.json' or entry['hash'] != 'md5':
                raise ValueError(f'{domain}: unexpected DVC pointer')
            raw, url = read_json_input(pointer, entry, args)
            if len(raw) != entry['size'] or hashlib.md5(raw).hexdigest() != entry['md5']:
                raise ValueError(f'{domain}: JSON does not match the Pilot 6 DVC size/MD5')
            table = dataset_table(raw, domain, source)
            destination = STUDY / 'data' / stage / f'{domain}.parquet'
            identical = destination.exists() and same_dataset(pq.read_table(destination), table)
            if args.verify_only and not identical:
                raise ValueError(f'{domain}: staged Parquet differs from the source JSON')
            output = destination if identical else staged / f'{stage}-{destination.name}'
            if not identical:
                pq.write_table(table, output, compression='snappy')
                if not same_dataset(pq.read_table(output), table):
                    raise ValueError(f'{domain}: Parquet round-trip failed')
                replacements.append((output, destination))
            record = {
                'path': destination.relative_to(ROOT).as_posix(),
                'dvc_pointer': pointer.relative_to(source).as_posix(),
                'metadata_source': ('data/adam_reference/define.xml' if domain == 'adnpix'
                                    else pointer.relative_to(source).as_posix().removesuffix('.dvc')),
                'source_md5': entry['md5'], 'source_bytes': entry['size'],
                'rows': table.num_rows, 'columns': table.num_columns,
                'parquet_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            }
            if url:
                record['retrieved_from'] = url
            manifest['datasets'].append(record)
            print(f'{domain.upper()}: verified {table.num_rows:,} rows, {table.num_columns} columns', flush=True)
        for filename, target in [('define.xml', 'define/define-adam.xml'),
                                 ('pilot6-specs.xlsx', 'pilot6-specs.xlsx')]:
            original = source / 'data/adam_reference' / filename
            destination = STUDY / 'spec' / target
            raw = original.read_bytes()
            if not destination.exists() or destination.read_bytes() != raw:
                if args.verify_only:
                    raise ValueError(f'{target}: differs from upstream')
                output = staged / target
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(raw)
                replacements.append((output, destination))
            manifest['specifications'].append({
                'path': destination.relative_to(ROOT).as_posix(),
                'source_path': original.relative_to(source).as_posix(),
                'sha256': hashlib.sha256(raw).hexdigest(),
            })
        for relative in sorted(p for p in tracked
                               if p == '.Rprofile' or p.startswith('code/adam/') or p in DATA_UTILITIES):
            raw = (source / relative).read_bytes()
            destination = STUDY / 'program/adam/upstream' / relative
            if not destination.exists() or destination.read_bytes() != raw:
                if args.verify_only:
                    raise ValueError(f'{relative}: staged source differs from upstream')
                output = staged / 'source' / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(raw)
                replacements.append((output, destination))
            manifest['programs'].append({
                'path': destination.relative_to(ROOT).as_posix(), 'source_path': relative,
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
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(output, destination)
            manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        print(f'Verified {len(pointers)} SDTM/ADaM datasets at Pilot 6 commit {commit}')


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
