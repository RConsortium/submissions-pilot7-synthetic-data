#!/usr/bin/env python3
"""Run pinned CORE validation locally or in CI; stage reports and coverage."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parent
CORE_VERSION = 'v0.16.0'
CORE_ASSET = 'core-ubuntu-latest.zip'
STANDARDS = {
    'sdtm': ('SDTM', 'sdtmig', '3-3', ['sdtmct-2024-09-27']),
    'adam': ('ADAM', 'adam', 'adamig-1-3', ['adamct-2024-09-27', 'sdtmct-2024-09-27']),
}


def locate_core(directory):
    for path in sorted(directory.rglob('core')):
        if path.is_file():
            with path.open('rb') as binary:
                if binary.read(4) == b'\x7fELF':
                    path.chmod(path.stat().st_mode | 0o111)
                    return path.resolve()
    return None


def ensure_core(directory):
    executable = locate_core(directory)
    if executable:
        return executable
    directory.mkdir(parents=True, exist_ok=True)
    url = f'https://github.com/cdisc-org/cdisc-rules-engine/releases/download/{CORE_VERSION}/{CORE_ASSET}'
    print(f'Downloading CORE from {url}', flush=True)
    with tempfile.TemporaryDirectory(prefix='core-download-') as work:
        archive = Path(work) / 'core.zip'
        subprocess.run(['curl', '-fsSL', '-o', str(archive), url], check=True)
        subprocess.run(['unzip', '-qo', str(archive), '-d', str(directory)], check=True)
    executable = locate_core(directory)
    if not executable:
        raise RuntimeError('CORE Linux executable not found after download')
    return executable


def resolve_ct(core_dir, desired):
    if any(core_dir.rglob(f'{desired}.pkl')):
        return desired
    prefix = desired.split('-', 1)[0]
    available = sorted(path.stem for path in core_dir.rglob(f'{prefix}-*.pkl'))
    if not available:
        raise RuntimeError(f'No {prefix} package in the CORE cache')
    print(f'WARNING: CT package {desired} missing; using {available[-1]}', flush=True)
    return available[-1]


def prepare_datasets(source, destination):
    """Keep the existing parquet-first selection and per-file skip policy."""
    parquets = sorted(source.glob('*.parquet'))
    inputs = parquets or sorted(source.glob('*.xpt'))
    destination.mkdir(parents=True, exist_ok=True)
    skipped = []
    if parquets:
        from parquet_to_xpt import convert_one

        for path in inputs:
            ok, message = convert_one(str(path), str(destination))
            print(message, flush=True)
            if not ok:
                skipped.append(path.name)
    else:
        for path in inputs:
            shutil.copy2(path, destination / path.name)
    return [path.name for path in inputs], skipped


def report_domains(report):
    names = [row.get('filename') for row in report.get('Dataset_Details', [])]
    names += [row.get('dataset') for row in report.get('Issue_Summary', [])]
    return sorted({name.upper().removesuffix('.XPT') for name in names if name})


def render_report(report_file, report, study, label):
    lines = [f'# CDISC CORE validation -- {study} ({label})', '',
             f'- Engine: CORE {CORE_VERSION}',
             f'- Commit: {os.environ.get("GITHUB_SHA", "unknown")[:7]}',
             f'- Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}', '']
    domains = report_domains(report)
    if not domains:
        lines += ['_No datasets found in report._', '']
    for domain in domains:
        block = subprocess.run(
            ['bash', str(SCRIPTS / 'core_render_block.sh'), str(report_file), domain],
            check=True, capture_output=True, text=True,
        ).stdout
        lines += [block.rstrip(), '']
    return '\n'.join(lines)


def run_domain(root, study, domain, executable, work, stage):
    label, standard, version, terminology = STANDARDS[domain]
    output = stage / study / 'data' / domain
    output.mkdir(parents=True, exist_ok=True)
    # A failed attempt must not reuse reports from an earlier invocation.
    for name in (f'core-report-{label}.json', f'core-report-{label}.xlsx',
                 'dataset_comment.md', 'core-execution.json'):
        (output / name).unlink(missing_ok=True)
    record = {'engine': CORE_VERSION, 'study': study,
              'repository_commit': os.environ.get('GITHUB_SHA'),
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'standard': standard, 'version': version, 'inputs': [],
              'prepared': [], 'skipped': [], 'report_datasets': [],
              'covered': [], 'rules': None, 'engine_exit_code': None,
              'status': 'not_run', 'conformance': 'unverified'}
    try:
        data = work / domain
        record['inputs'], record['skipped'] = prepare_datasets(
            root / study / 'data' / domain, data)
        record['prepared'] = sorted(path.name for path in data.glob('*.xpt'))
        if record['inputs']:
            if not record['prepared']:
                raise RuntimeError('No input datasets could be prepared for CORE')
            packages = [resolve_ct(executable.parent, package) for package in terminology]
            record['controlled_terminology'] = packages
            prefix = work / f'core-report-{label}'
            command = [str(executable), 'validate', '--standard', standard,
                       '--version', version]
            for package in packages:
                command += ['--controlled-terminology-package', package]
            command += ['--data', str(data), '--filetype', 'xpt',
                        '--output-format', 'JSON', '--output-format', 'XLSX',
                        '--output', str(prefix)]
            result = subprocess.run(command, cwd=executable.parent, check=False)
            record['engine_exit_code'] = result.returncode
            print(f'CORE {label} exit code: {result.returncode}', flush=True)
            for extension in ('.json', '.xlsx'):
                report_file = prefix.with_suffix(extension)
                if report_file.exists():
                    shutil.copy2(report_file, output / report_file.name)
            report_file = output / f'core-report-{label}.json'
            report = json.loads(report_file.read_text())
            record['report_datasets'] = report_domains(report)
            prepared = {Path(name).stem.upper() for name in record['prepared']}
            record['covered'] = sorted(prepared & set(record['report_datasets']))
            record['rules'] = len(report.get('Rules_Report') or [])
            record['conformance'] = ('unverified' if not record['rules'] else 'findings_reported')
            record['status'] = ('partial' if record['skipped'] or len(record['covered']) < len(prepared)
                                else 'report_generated')
            (output / 'dataset_comment.md').write_text(
                render_report(report_file, report, study, label))
    except Exception as error:
        record.update(status='failed', reason=str(error))
        print(f'ERROR: {study}/{domain}: {error}', flush=True)
    (output / 'core-execution.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def write_summary(study, records):
    lines = [f'## CORE Validation -- `{study}`', '', f'Engine: CORE {CORE_VERSION}', '',
             '| Standard | Prepared / inputs | Covered by report | Rules listed | Engine exit | Status |',
             '|---|---:|---:|---:|---:|---|']
    for domain, record in records.items():
        status = record['status']
        if record['rules'] == 0:
            status += '; 0 rules - conformance UNVERIFIED'
        lines.append(f'| {domain.upper()} | {len(record["prepared"])}/{len(record["inputs"])} '
                     f'| {len(record["covered"])} | {record["rules"]} '
                     f'| {record["engine_exit_code"]} | {status} |')
    lines += ['', 'A generated report is not a conformance pass. Conversion skips and engine '
              'exit codes are recorded in the artifact-only `core-execution.json` files.', '',
              'On main, reports and `dataset_comment.md` are proposed via **core/reports**; '
              'findings are also posted to matching issues.', '']
    summary = '\n'.join(lines)
    print(summary, flush=True)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as output:
            output.write(summary)


def run_study(root, study, executable, stage):
    with tempfile.TemporaryDirectory(prefix=f'core-{study}-') as temporary:
        work = Path(temporary).resolve()
        records = {domain: run_domain(root, study, domain, executable, work, stage)
                   for domain in STANDARDS}
    write_summary(study, records)
    return int(any(record['status'] == 'failed' for record in records.values())
               or not any(record['inputs'] for record in records.values()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study')
    parser.add_argument('--core-dir', type=Path, default=ROOT / '.build/core-bin' / CORE_VERSION)
    parser.add_argument('--output', type=Path, default=ROOT / '.build/core-reports')
    args = parser.parse_args()
    if (Path(args.study).name != args.study or args.study.startswith('.')
            or not (ROOT / args.study / 'data').is_dir()):
        parser.error('study must be a current study folder with data/')
    try:
        executable = ensure_core(args.core_dir.resolve())
        return run_study(ROOT, args.study, executable, args.output.resolve())
    except Exception as error:
        print(f'ERROR: {error}', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
