#!/usr/bin/env python3
"""Check, build and compare a study; record pending projects explicitly."""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from study_evidence import catalog, engine_revision, project_specs
from study_artifacts import artifact_snapshot
from study_define import check_define
from resolved_specs import process_study, specification_packet

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

    process_study(ROOT, study_name, check=True)
    if entry.get('prepare'):
        # End-to-end studies start from their retained ODM, not from an
        # independently published SDTM input. The repository-owned runner
        # must fail before a successful validation record can be produced.
        runner = (study / entry['prepare']).resolve()
        runner.relative_to(study.resolve())
        subprocess.run([sys.executable, str(runner)], cwd=ROOT, check=True)
        report['source_pipeline'] = True
    report.update(yamaa_revision=engine_revision(ROOT, study_name),
                  yamaa_version=yamaa.__version__)
    project = yamaa.project(project_file)
    check = project.check()
    print(check, flush=True)
    if check.status != 'succeeded':
        raise ValueError(str(check.issues.to_pylist()))
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
            'resolved_specification': specification_packet(ROOT, path),
            'rows': output.num_rows, 'columns': len(output.column_names),
            'build': 'succeeded',
            'comparison': ('unavailable' if matched is None else
                           'passed' if matched else 'failed'),
        })
    report['status'] = ('failed' if any(d['comparison'] == 'failed'
                                      for d in report['datasets']) else 'succeeded')
    if report['status'] == 'succeeded':
        report['define_xml'] = check_define(ROOT, study_name, project)
        report['artifacts'] = artifact_snapshot(ROOT, study_name)


def main():
    entries = catalog(ROOT)
    from study_dashboard.synthetic import synthetic_catalog
    synthetic = synthetic_catalog(ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', choices=sorted(set(entries) | set(synthetic)))
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.study in synthetic:
        from validate_synthetic import validate as validate_development
        record = validate_development(args.study, ROOT)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(record, indent=2) + '\n')
        return int(record['status'] != 'succeeded')
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
