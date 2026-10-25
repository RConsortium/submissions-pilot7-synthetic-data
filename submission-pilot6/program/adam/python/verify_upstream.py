#!/usr/bin/env python3
"""Regenerate Pilot 6 ADaM from staged SDTM and compare with imported references.

Runs the unchanged upstream R programs with Rscript and the renv lockfile. Each attempt
uses a new sandbox with no ADaM files; children read freshly generated parents.
Requires pyarrow and PyYAML in Python and the R packages listed in the README.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[4]
STUDY = ROOT / 'submission-pilot6'
HERE = Path(__file__).resolve().parent
ADAM = HERE.parent
BOOTSTRAP = ADAM / 'R/run_upstream.R'
SDTM_DOMAINS = {
    'ae', 'cm', 'dm', 'ds', 'ex', 'lb', 'mh', 'qs', 'relrec', 'sc', 'se',
    'suppae', 'suppdm', 'suppds', 'supplb', 'sv', 'ta', 'te', 'ti', 'tv', 'vs',
}
REFERENCE_DOMAINS = {'adsl', 'adae', 'adadas', 'adlbc', 'adlbh', 'adnpix', 'advs', 'adtte'}
UNREFERENCED_DOMAINS = {'adlbhy', 'adcibc'}
PROGRAMS = [
    ('adsl', 'adsl.r', []),
    ('adae', 'adae.r', ['adsl']),
    ('adadas', 'adadas.r', ['adsl']),
    ('adlbc', 'adlbc.r', ['adsl']),
    ('adlbh', 'adlbh.r', ['adsl']),
    ('adnpix', 'adqsnpix.r', ['adsl']),
    ('advs', 'advs.r', ['adsl']),
    ('adtte', 'adtte.r', ['adsl', 'adae']),
    ('adlbhy', 'adlbhy.r', ['adlbc']),
    ('adcibc', 'adqscibc.r', ['adsl']),
]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_snapshot():
    manifest = json.loads((STUDY / 'spec/source-snapshot.json').read_text())
    expected_datasets = {
        f'submission-pilot6/data/{stage}/{domain}.parquet'
        for stage, domains in [('sdtm', SDTM_DOMAINS), ('adam', REFERENCE_DOMAINS)]
        for domain in domains
    }
    expected_specs = {
        'submission-pilot6/spec/define/define-adam.xml',
        'submission-pilot6/spec/pilot6-specs.xlsx',
    }
    expected_sources = {'.Rprofile', 'code/utils/compare_data.r',
                        'code/utils/dvc_compare.sh', 'code/utils/save_dataset_json.r'}
    expected_sources.update(f'code/adam/{filename}' for _, filename, _ in PROGRAMS)
    expected_programs = {f'submission-pilot6/program/adam/upstream/{path}' for path in expected_sources}
    for group, expected in [('datasets', expected_datasets), ('specifications', expected_specs),
                            ('programs', expected_programs)]:
        paths = [entry['path'] for entry in manifest.get(group, [])]
        if set(paths) != expected or len(paths) != len(expected):
            raise ValueError(f'Incomplete or unexpected {group} snapshot inventory')
    for group, hash_key in [('datasets', 'parquet_sha256'), ('specifications', 'sha256'), ('programs', 'sha256')]:
        for entry in manifest[group]:
            if sha256(ROOT / entry['path']) != entry[hash_key]:
                raise ValueError(f'Snapshot checksum mismatch: {entry["path"]}')
    declared = [p['source_path'] for p in manifest['programs']]
    if set(declared) != expected_sources or len(declared) != len(expected_sources):
        raise ValueError('Program inventory differs from the execution plan')
    sdtm = [x for x in manifest['datasets'] if '/data/sdtm/' in x['path']]
    if {f'{domain}.parquet' for domain in SDTM_DOMAINS} != {p.name for p in (STUDY / 'data/sdtm').glob('*.parquet')}:
        raise ValueError('SDTM inventory differs from the source snapshot')
    return manifest, sdtm


def run_program(command, environment, work, domain):
    """Keep partial output and mark timeouts as failures, even if a file exists."""
    try:
        result = subprocess.run(command, env=environment, cwd=work,
                                capture_output=True, text=True, timeout=600)
        log = result.stdout + result.stderr
        failure = {'returncode': result.returncode} if result.returncode else None
    except subprocess.TimeoutExpired as exc:
        def output_text(value):
            return value.decode(errors='replace') if isinstance(value, bytes) else (value or '')
        # TimeoutExpired may hold bytes even when text=True.
        log = output_text(exc.stdout) + output_text(exc.stderr)
        log += f'\nProgram timed out after {exc.timeout} seconds.\n'
        failure = {'returncode': None, 'timed_out': True, 'timeout_seconds': exc.timeout}
    (work / 'logs' / f'{domain}.log').write_text(log)
    return failure, log


def materialize_sdtm(path, destination):
    """Convert staged Parquet to Dataset-JSON for the upstream reader."""
    table = pq.read_table(path)
    columns, values = [], []
    for field, column in zip(table.schema, table.columns):
        if pa.types.is_large_string(field.type) or pa.types.is_string(field.type):
            kind = 'string'
        elif pa.types.is_floating(field.type) or pa.types.is_integer(field.type):
            kind = 'float'
        else:
            raise ValueError(f'Unsupported SDTM column type: {field}')
        metadata = {'name': field.name, 'itemOID': field.name, 'dataType': kind,
                    'label': field.metadata[b'yamaa:label'].decode()}
        columns.append(metadata)
        values.append(column.to_pylist())
    data = {'datasetJSONVersion': '1.1.0', 'datasetJSONCreationDateTime': '2026-10-24T00:00:00',
            'itemGroupOID': path.stem, 'name': path.stem.upper(), 'label': path.stem.upper(),
            'records': table.num_rows, 'columns': columns, 'rows': list(map(list, zip(*values)))}
    destination.write_text(json.dumps(data, allow_nan=False, separators=(',', ':')))


def compare_tables(actual, reference, tolerance=1e-10):
    """Compare original order, exact text/nulls/dates/labels and numeric tolerance."""
    result = {'actual_rows': actual.num_rows, 'reference_rows': reference.num_rows,
              'actual_columns': actual.num_columns, 'reference_columns': reference.num_columns,
              'column_order_matches': actual.column_names == reference.column_names,
              'type_differences': [], 'label_differences': [], 'value_differences': []}
    for name in actual.column_names:
        if name not in reference.column_names:
            continue
        a, b = actual.schema.field(name), reference.schema.field(name)
        if a.type != b.type:
            result['type_differences'].append(name)
        if (a.metadata or {}).get(b'yamaa:label') != (b.metadata or {}).get(b'yamaa:label'):
            result['label_differences'].append(name)
        if actual.num_rows != reference.num_rows:
            continue
        differences, max_difference, examples = 0, 0.0, []
        for row, (left, right) in enumerate(zip(actual[name].to_pylist(), reference[name].to_pylist()), 1):
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                matched = math.isclose(left, right, rel_tol=0, abs_tol=tolerance)
                max_difference = max(max_difference, abs(left - right))
            else:
                matched = left == right
            differences += not matched
            if not matched and len(examples) < 3:
                examples.append({'row': row, 'actual': left, 'reference': right})
        if differences:
            result['value_differences'].append({'column': name, 'cells': differences,
                                                 'max_numeric_difference': max_difference, 'examples': examples})
    result['passed'] = (result['actual_rows'] == result['reference_rows']
                        and result['column_order_matches']
                        and not any(result[k] for k in ('type_differences', 'label_differences', 'value_differences')))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rscript', default='Rscript', help='Rscript executable in the current environment')
    parser.add_argument('--report', type=Path, default=STUDY / 'log/upstream-verification.json')
    args = parser.parse_args()
    # A failed attempt must not publish an earlier run's evidence.
    args.report.unlink(missing_ok=True)
    manifest, inputs = verify_snapshot()
    build = ROOT / '.build/pilot6-upstream'
    build.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='run-', dir=build))
    for entry in manifest['programs']:
        relative = Path(entry['source_path'])
        if relative.is_absolute() or '..' in relative.parts or not (relative == Path('.Rprofile') or relative.parts[0] == 'code'):
            raise ValueError(f'Unexpected upstream source path: {relative}')
        destination = work / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / entry['path'], destination)
    shutil.copyfile(BOOTSTRAP, work / 'run_upstream.R')
    for directory in ('data/sdtm', 'data/adam', 'data/adam_reference', 'logs'):
        (work / directory).mkdir(parents=True, exist_ok=True)
    for entry in inputs:
        source = ROOT / entry['path']
        materialize_sdtm(source, work / 'data/sdtm' / f'{source.stem}.json')
    shutil.copyfile(STUDY / 'spec/pilot6-specs.xlsx', work / 'data/adam_reference/pilot6-specs.xlsx')
    shutil.copyfile(STUDY / 'spec/define/define-adam.xml', work / 'data/adam_reference/define.xml')
    initial_adam_files = list((work / 'data/adam').iterdir())
    if initial_adam_files:
        raise ValueError('ADaM sandbox must be empty before execution')
    probe = pa.Table.from_arrays([pa.array([56.72413793103448, 1.2345678901234567])],
                                 schema=pa.schema([pa.field('NUMBER', pa.float64(),
                                                            metadata={b'yamaa:label': b'Precision probe'})]))
    pq.write_table(probe, work / 'probe.parquet')
    materialize_sdtm(work / 'probe.parquet', work / 'probe.json')
    environment = dict(os.environ, PILOT6_RENV_PROJECT=str(ADAM))
    command = [args.rscript, '--vanilla']
    runtime = subprocess.run(command + ['-e', 'renv::load(project=Sys.getenv("PILOT6_RENV_PROJECT"), quiet=TRUE); '
                             'probe <- datasetjson::read_dataset_json("probe.json"); '
                             'stopifnot(identical(as.numeric(probe$NUMBER), c(56.72413793103448, 1.2345678901234567))); '
                             'jsonlite::write_json(list(R=R.version.string, '
                             'packages=as.list(setNames(installed.packages()[,"Version"], '
                             'installed.packages()[,"Package"]))), "runtime-observed.json", auto_unbox=TRUE)'],
                             env=environment, cwd=work, capture_output=True, text=True, timeout=120)
    if runtime.returncode:
        raise RuntimeError(runtime.stderr)
    spec = importlib.util.spec_from_file_location('pilot6_import', ROOT / '.github/scripts/import_pilot6_inputs.py')
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_commit': manifest['source_commit'],
              'workflow_run_id': os.environ.get('GITHUB_RUN_ID'), 'execution_commit': os.environ.get('GITHUB_SHA'),
              'snapshot_sha256': sha256(STUDY / 'spec/source-snapshot.json'),
              'runner_sha256': sha256(Path(__file__)), 'bootstrap_sha256': sha256(BOOTSTRAP),
              'renv_lock_sha256': sha256(ADAM / 'renv.lock'),
              'runtime': json.loads((work / 'runtime-observed.json').read_text()),
              'input_datasets': len(inputs), 'initial_adam_files': len(initial_adam_files),
              'input_precision_probe': 'passed',
              'input_adapter': 'Staged Parquet to Dataset-JSON 1.1; numeric columns use float.',
              'comparison_policy': 'Original row/column order; exact text, nulls, dates, types and labels; absolute numeric tolerance 1e-10.',
              'datasets': []}
    generated = set()
    for domain, filename, dependencies in PROGRAMS:
        record = {'domain': domain.upper(), 'program': f'code/adam/{filename}', 'dependencies': dependencies}
        blocked = [parent for parent in dependencies if parent not in generated]
        if blocked:
            record.update(generation='blocked', blocked_by=blocked, comparison='not_run')
        else:
            failure, log = run_program(command + ['run_upstream.R', filename], environment, work, domain)
            output = work / 'data/adam' / f'{domain}.json'
            if failure or not output.exists():
                record.update(generation='failed', **(failure or {'returncode': 0}), comparison='not_run',
                              error=log[-3000:] if log else 'Expected output was not created.')
            else:
                generated.add(domain)
                record.update(generation='succeeded', output_sha256=sha256(output))
                table = importer.dataset_table(output.read_bytes(), domain)
                record.update(rows=table.num_rows, columns=table.num_columns)
                reference = STUDY / 'data/adam' / f'{domain}.parquet'
                if domain in UNREFERENCED_DOMAINS:
                    record['comparison'] = 'reference_unavailable'
                elif reference.exists():
                    comparison = compare_tables(table, pq.read_table(reference))
                    record.update(comparison='passed' if comparison['passed'] else 'failed', details=comparison)
                else:
                    record.update(comparison='failed', error=f'Required reference is missing: {reference}')
        report['datasets'].append(record)
        print(f'{domain.upper()}: generation={record["generation"]}, comparison={record["comparison"]}', flush=True)
    report['summary'] = {key: sum(x[field] == value for x in report['datasets']) for key, field, value in (
        ('generated', 'generation', 'succeeded'), ('failed', 'generation', 'failed'),
        ('blocked', 'generation', 'blocked'), ('matched', 'comparison', 'passed'),
        ('mismatched', 'comparison', 'failed'), ('reference_unavailable', 'comparison', 'reference_unavailable'))}
    report['status'] = 'passed' if (report['summary']['generated'] == len(PROGRAMS)
                                    and report['summary']['matched'] == len(REFERENCE_DOMAINS)
                                    and not report['summary']['mismatched']) else 'failed'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, default=str) + '\n')
    print(f'Evidence: {args.report}\nFull logs and outputs: {work}', flush=True)
    return int(report['status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
