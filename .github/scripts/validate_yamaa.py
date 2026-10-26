#!/usr/bin/env python3
"""Check, build and compare a study; record pending projects explicitly."""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path

from study_evidence import catalog, engine_revision, project_specs, validate_derivation_inputs
from study_artifacts import artifact_snapshot
from study_dashboard.specifications import capture_specification

ROOT = Path(__file__).resolve().parents[2]


def validate(study_name, entry, report):
    study = ROOT / study_name
    project_file = study / 'spec/yamaa/project.yaml'
    if not project_file.exists():
        if not entry.get('allow_pending'):
            raise ValueError(f'{study_name}: required project is missing')
        report.update(status='pending', reason='The study project is not yet merged.')
        return

    import yamaa

    report.update(yamaa_revision=engine_revision(ROOT, study_name),
                  yamaa_version=yamaa.__version__)
    for directory in [project_file.parent, ROOT / 'spec/yamaa']:
        if not directory.is_dir():
            continue
        findings = yamaa.lint(directory).to_pylist()
        print(f'yamaa lint of {directory}: {len(findings)} findings', flush=True)
        if findings:
            raise ValueError(f'Authoring checks failed: {findings}')
    project = yamaa.project(project_file)
    check = project.check()
    print(check, flush=True)
    if check.status != 'succeeded':
        raise ValueError(str(check.issues.to_pylist()))
    resolved = {
        domain: capture_specification(ROOT, path, project.spec(domain).resolve())
        for domain, path in project_specs(ROOT, study_name)
    }
    validate_derivation_inputs(ROOT, study_name, resolved)
    runs = project.run('adam')
    print(runs, flush=True)
    if runs.status != 'succeeded':
        raise ValueError(str(runs.issues.to_pylist()))
    runs.save()

    compare_file = study / 'program/adam/python/compare.py'
    comparator = None
    if compare_file.exists():
        spec = importlib.util.spec_from_file_location('study_compare', compare_file)
        comparator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(comparator)
    if entry['comparison'] == 'official' and comparator is None:
        raise ValueError(f'{study_name}: official comparator is missing')

    for domain, path in project_specs(ROOT, study_name):
        output = runs[domain].output
        required = entry['comparison'] == 'official'
        reference = study / 'data/adam' / f'{domain.lower()}.parquet'
        matched = None
        if required or reference.exists():
            if comparator is None:
                raise ValueError(f'{study_name}: reference exists but no comparator is available')
            if hasattr(comparator, 'compare_domain'):
                matched = comparator.compare_domain(path.stem)['ok']
            else:
                matched = comparator.compare(path.stem)
        report['datasets'].append({
            'domain': domain, 'spec': path.relative_to(ROOT).as_posix(),
            'resolved_specification': resolved[domain],
            'rows': output.num_rows, 'columns': len(output.column_names),
            'build': 'succeeded',
            'comparison': ('unavailable' if matched is None else
                           'passed' if matched else 'failed'),
        })
    report['status'] = ('failed' if any(d['comparison'] == 'failed'
                                      for d in report['datasets']) else 'succeeded')
    if report['status'] == 'succeeded':
        report['artifacts'] = artifact_snapshot(ROOT, study_name)


def main():
    entries = catalog(ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', choices=entries)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    destination = args.report or ROOT / '.build/validation' / f'{args.study}.json'
    # A failed attempt must never leave an earlier successful record behind.
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    report = {
        'study': args.study, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'repository_commit': os.environ.get('GITHUB_SHA'), 'status': 'failed',
        'yamaa_revision': None, 'yamaa_version': None, 'datasets': [],
    }
    try:
        validate(args.study, entries[args.study], report)
    except Exception as error:
        report.update(status='failed', reason=str(error))
        print(f'FAILED: {error}', flush=True)
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(f"{report['status']}: {destination}", flush=True)
    return int(report['status'] == 'failed')


if __name__ == '__main__':
    raise SystemExit(main())
