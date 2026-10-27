#!/usr/bin/env python3
"""Select PR checks from a complete Git diff, including deleted/renamed paths."""

import argparse
import json
import os
from pathlib import Path
import subprocess

from check_structure import discover_studies
from discover_core_studies import has_validatable_data
from study_evidence import catalog
from study_dashboard.synthetic import synthetic_catalog

CORE_CODE = {'.github/scripts/run_core.py', '.github/scripts/parquet_to_xpt.py',
             '.github/scripts/core_render_block.sh', '.github/scripts/core_block.jq'}
YAMAA_CODE = {'.github/scripts/validate_yamaa.py', '.github/scripts/study_evidence.py',
              '.github/scripts/generate_define.py', '.github/scripts/define_metadata.py',
              '.github/scripts/legacy_define.py', '.github/scripts/compare_legacy_define.py',
              '.github/scripts/define_report.py',
              '.github/scripts/build_study_docs.py', '.github/scripts/build_index_table.py',
              '.github/yamaa-studies.json',
              '.github/workflows/yamaa-site.yml', 'requirements.txt'}
PUBLICATION_CODE = {'.github/scripts/build_study_docs.py', '.github/scripts/build_index_table.py',
                    '.github/scripts/study_define.py', '.github/scripts/define_metadata.py',
                    '.github/scripts/legacy_define.py', '.github/scripts/compare_legacy_define.py',
                    '.github/scripts/study_evidence.py', '.github/scripts/study_artifacts.py',
                    '.github/scripts/study_metrics.py', '.github/scripts/dashboard_nav.py',
                    '.github/scripts/stage_study_artifacts.py', '.github/scripts/check_dashboard.sh',
                    '.github/dashboard.json', '.github/yamaa-studies.json', '.github/synthetic-studies.json',
                    '.github/workflows/yamaa-site.yml', '.github/workflows/study-check.yml',
                    # Validation jobs verify reviewed derivations; the bundle shows the report.
                    '.github/scripts/verify_derivations.py', '.github/scripts/consistency_report.py',
                    '.automation/consistency_review/rules.yaml', 'docs/requirements.txt'}
PUBLICATION_PREFIXES = ('.github/scripts/study_dashboard/', '.github/tests/dashboard/',
                        '.github/schemas/', 'docs/assets/dashboard/', 'docs/stylesheets/dashboard.css')
WORKER = '.github/workflows/study-check.yml'
PLAN = 'submission-pilot3/data/mapping/plan.csv'
PLAN_INPUTS = {PLAN,
               'submission-pilot3/data/sdtm/qs.parquet',
               'submission-pilot3/data/sdtm/ex.parquet'}
PY_PLAN = 'submission-pilot3/program/adam/python/make_plan.py'
R_PLAN = 'submission-pilot3/program/adam/R/make_plan.R'
COMPARE_INPUTS = {'.github/scripts/compare_adam.py',
                  'submission-pilot5/program/adam/adam-compare-keys.json'}


def select_checks(root, changed):
    changed = set(changed)
    entries = catalog(root)
    synthetic = synthetic_catalog(root)
    manifest = json.loads((root / '.github/repo-structure.json').read_text())
    studies = sorted(set(entries) | set(discover_studies(str(root), manifest.get('non_study_dirs', []))))
    publication = bool(changed & PUBLICATION_CODE) or any(
        path.startswith(PUBLICATION_PREFIXES) or
        any(path.startswith((f'{study}/data/', f'{study}/spec/')) and Path(path).suffix != '.md'
            for study in synthetic) or
        any(path.startswith(f'{study}/spec/{part}/') for study in entries
            for part in ('source', 'define', 'review')) for path in changed)
    all_yamaa = publication or bool(changed & (YAMAA_CODE | {WORKER}))
    all_core = bool(changed & (CORE_CODE | {WORKER}))
    selected = []
    for study in studies:
        local = [path[len(study) + 1:] for path in changed if path.startswith(study + '/')]
        inputs = any(path.startswith(('data/sdtm/', 'data/adam/', 'data/mapping/'))
                     and Path(path).suffix.lower() != '.md'
                     and Path(path).name not in {'README.md', '.gitkeep', '.gitignore',
                                                 'dataset_comment.md', 'core-execution.json'}
                     and not Path(path).name.startswith('core-report-') for path in local)
        binary = any(path.startswith(('data/sdtm/', 'data/adam/'))
                     and Path(path).suffix.lower() in {'.parquet', '.xpt'} for path in local)
        python = any(path.startswith('program/adam/python/')
                     and (path.endswith('.py') or path.endswith('/requirements.txt'))
                     and path != 'program/adam/python/make_plan.py' for path in local)
        spec = any(path.startswith('spec/yamaa/') and path.endswith(('.yaml', '.yml')) for path in local)
        r_changed = any(path.startswith('program/adam/R/') and path.lower().endswith('.r')
                        and path != 'program/adam/R/make_plan.R' for path in local)
        pending = entries.get(study, {}).get('allow_pending') and not (root / study / 'spec/yamaa/project.yaml').exists()
        yamaa = study in entries and (inputs or python or spec or (all_yamaa and not pending))
        core = has_validatable_data(str(root), study) and (binary or all_core)
        r = (root / study / 'program/adam/R/run.R').exists() and (
            r_changed or WORKER in changed or f'{study}/program/adam/python/requirements.txt' in changed)
        if yamaa or core or r:
            selected.append({'study': study, 'yamaa': bool(yamaa), 'core': core, 'r': r})
    return {
        'studies': selected,
        'plan_python': bool(changed & (PLAN_INPUTS | {PY_PLAN, '.github/workflows/ci.yml'})),
        'plan_r': bool(changed & (PLAN_INPUTS | {R_PLAN, '.github/workflows/ci.yml'})),
        'compare': bool(changed & (COMPARE_INPUTS | {'.github/workflows/ci.yml'}))
                   or any(path.startswith('submission-pilot5/data/adam/') and path.endswith('.parquet') for path in changed),
        'publication': publication,
        'website': publication or any(path.startswith('docs/') for path in changed)
                   or bool(changed & {'mkdocs.yml', '.github/scripts/build_study_docs.py',
                                      '.github/scripts/build_index_table.py',
                                      '.github/scripts/preview_site.py', '.github/yamaa-studies.json',
                                      '.github/workflows/yamaa-site.yml', '.github/scripts/check_ascii.py'}),
    }


def changed_paths(root, base, head):
    return [path for path in subprocess.check_output(
        ['git', 'diff', '--name-only', '--no-renames', '-z', base, head, '--'],
        cwd=root).decode().split('\0') if path]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--head', default='HEAD')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    # No API pagination or file-count cap; renames expose both the old and new scope.
    scope = select_checks(root, changed_paths(root, args.base, args.head))
    print(json.dumps(scope, indent=2))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            for key, value in scope.items():
                if key == 'studies':
                    value = {'include': value} if value else {}
                output.write(f'{key}={json.dumps(value, separators=(",", ":"))}\n')


if __name__ == '__main__':
    main()
