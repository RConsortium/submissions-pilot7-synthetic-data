"""Shared project inventory and publication checks for study evidence."""

import json
import os
import re
from pathlib import Path


def catalog(root):
    return json.loads((root / '.github/yamaa-studies.json').read_text())


def project_specs(root, study):
    import yaml

    project = root / study / 'spec/yamaa/project.yaml'
    declaration = yaml.safe_load(project.read_text())
    specs = declaration['adam']['specs']
    if not specs:
        raise ValueError(f'{study}: project has no active specifications')
    result = []
    for relative in specs:
        path = project.parent / relative
        domain = yaml.safe_load(path.read_text())['domain']
        result.append((domain, path))
    if len({name for name, _ in result}) != len(result):
        raise ValueError(f'{study}: duplicate project domains')
    return result


def engine_revision(root, study):
    path = root / study / 'program/adam/python/requirements.txt'
    matches = re.findall(r'yamaa\.git@([0-9a-f]{40})', path.read_text())
    if len(matches) != 1:
        raise ValueError(f'{study}: requirements must pin one yamaa source revision')
    return matches[0]


def validate_reports(root, entries, reports, expected_commit=None):
    """Refuse incomplete, failed, stale or overstated publication evidence."""
    revisions, commits = set(), set()
    for name, entry in entries.items():
        report = reports[name]
        if report['study'] != name:
            raise ValueError(f'{name}: wrong study in evidence')
        commit = report.get('repository_commit')
        commits.add(commit)
        if expected_commit and commit != expected_commit:
            raise ValueError(f'{name}: evidence is not from this source commit')
        status = report.get('status')
        project = root / name / 'spec/yamaa/project.yaml'
        if status == 'pending':
            if not entry.get('allow_pending') or project.exists() or report['datasets']:
                raise ValueError(f'{name}: unexpected pending project')
            continue
        if status != 'succeeded' or not project.exists():
            raise ValueError(f'{name}: project did not succeed')
        revision = engine_revision(root, name)
        if report['yamaa_revision'] != revision:
            raise ValueError(f'{name}: evidence uses a different engine pin')
        revisions.add(revision)
        expected = {domain: path.relative_to(root).as_posix()
                    for domain, path in project_specs(root, name)}
        datasets = report['datasets']
        if len(datasets) != len(expected) or {d['domain'] for d in datasets} != set(expected):
            raise ValueError(f'{name}: incomplete or duplicate dataset evidence')
        for dataset in datasets:
            if dataset['spec'] != expected[dataset['domain']]:
                raise ValueError(f'{name}: specification path does not match project')
            if dataset['build'] != 'succeeded':
                raise ValueError(f'{name}: dataset build failed')
            comparison = dataset['comparison']
            allowed = {'passed'} if entry['comparison'] == 'official' else {'passed', 'unavailable'}
            if comparison not in allowed:
                raise ValueError(f'{name}: invalid or missing reference comparison')
            if any(type(dataset[k]) is not int or dataset[k] < 0 for k in ('rows', 'columns')):
                raise ValueError(f'{name}: invalid dataset dimensions')
    if len(commits) != 1:
        raise ValueError('Study evidence comes from different source commits')
    if len(revisions) > 1:
        raise ValueError('Study evidence uses different yamaa revisions')


if __name__ == '__main__':
    # Emit the publication catalog as a GitHub Actions matrix.
    studies = json.dumps(list(catalog(Path(__file__).resolve().parents[2])))
    print(studies)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write(f'studies={studies}\n')
