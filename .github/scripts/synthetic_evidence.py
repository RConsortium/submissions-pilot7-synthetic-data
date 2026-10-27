"""Bind synthetic development evidence to exact inputs, specs, and output bytes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def artifact_inventory(root, study):
    base = root / study
    paths = []
    for folder in ['spec', 'program', 'data/odm', 'data/sdtm', 'data/adam']:
        paths.extend(p for p in (base / folder).rglob('*') if p.is_file() and
                     '__pycache__' not in p.parts and p.name != '.gitkeep')
    for name in ['synthetic_odm.py', 'synthetic_checks.py', 'synthetic_evidence.py', 'validate_synthetic.py']:
        paths.append(root / '.github/scripts' / name)
    paths.extend(p for p in (root / '.github/schemas/cdisc').rglob('*') if p.is_file())
    paths.append(root / '.github/schemas/synthetic-review.schema.json')
    paths.append(root / '.github/scripts/study_dashboard/specifications.py')
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(set(paths))}


def verified_report(root, study, revision=None):
    path = root / '.build/synthetic' / study / 'report.json'
    if not path.exists():
        return None
    report = json.loads(path.read_text())
    if report.get('status') != 'succeeded':
        return report
    if revision and report.get('source_revision') != revision:
        raise ValueError(f'{study}: synthetic report belongs to a different source revision')
    if report.get('artifacts') != artifact_inventory(root, study):
        raise ValueError(f'{study}: synthetic evidence is stale; rerun validate_synthetic.py')
    return report


def stage_artifacts(root, study, destination):
    report = verified_report(root, study)
    if not report or report['status'] != 'succeeded':
        raise ValueError(f'{study}: no successful synthetic build to stage')
    for relative in report['artifacts']:
        if not relative.startswith(study + '/data/'):
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, target)
    relative = Path('.build/synthetic') / study / 'report.json'
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / relative, target)


def package(root, study, target, report):
    """Compress study sources, specs, transports, and the exact build record."""
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for relative in report['artifacts']:
            archive.write(root / relative, relative)
        archive.write(root / '.build/synthetic' / study / 'report.json',
                      f'.build/synthetic/{study}/report.json')
        guide = root / study / 'README.md'
        if guide.exists():
            archive.write(guide, f'{study}/README.md')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--stage', choices=['kn189', 'kn564'])
    args = parser.parse_args()
    if args.list:
        studies = list(json.loads((ROOT / '.github/synthetic-studies.json').read_text()))
        print(json.dumps(studies))
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                output.write('studies=' + json.dumps(studies) + '\n')
    elif args.stage:
        stage_artifacts(ROOT, args.stage, ROOT / '.build/synthetic-artifact')
    else:
        parser.error('Select --list or --stage')


if __name__ == '__main__':
    main()
