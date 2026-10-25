#!/usr/bin/env python3
"""Build the review prototype separately from published study documentation."""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

import yaml


ROOT = Path(__file__).resolve().parents[3]
PROTOTYPE = Path(__file__).resolve().parent
STUDIES = (
    ('cdiscpilot01', 'CDISC Pilot 01'),
    ('submission-pilot3', 'Submission Pilot 3'),
    ('submission-pilot5', 'Submission Pilot 5'),
    ('submission-pilot6', 'Submission Pilot 6'),
    ('kn189', 'KN189'),
    ('kn564', 'KN564'),
)


def build(destination):
    """Stage demo pages and use the repository's actual MkDocs configuration."""
    destination = destination.resolve()
    docs = destination / 'docs'
    (docs / 'assets').mkdir(parents=True, exist_ok=True)
    (docs / 'stylesheets').mkdir(parents=True, exist_ok=True)
    (docs / 'studies').mkdir(parents=True, exist_ok=True)

    # The existing stylesheet retains its attribution and licence in the copy.
    shutil.copytree(ROOT / 'docs/stylesheets', docs / 'stylesheets',
                    dirs_exist_ok=True)
    shutil.copyfile(PROTOTYPE / 'dashboard.css',
                    docs / 'stylesheets/dashboard.css')
    shutil.copyfile(PROTOTYPE / 'dashboard.js', docs / 'assets/dashboard.js')
    for name in ('index.md', 'verification.md'):
        source = (ROOT / 'docs' / name).read_text(encoding='utf-8')
        note = ('!!! note "Design prototype"\n\n'
                '    Dashboard metrics, documentation findings, and data rows '
                'are illustrative.\n\n')
        (docs / name).write_text(note + source, encoding='utf-8')

    for study, title in (('gallery', 'Study verification'), *STUDIES):
        filename = 'index' if study == 'gallery' else study
        page = (
            f'---\ntitle: {title}\nhide:\n  - toc\n---\n\n'
            f'<div id="study-dashboard" class="study-dashboard" '
            f'data-study="{study}"><h1>{title}</h1>'
            '<noscript>Enable JavaScript to explore this review prototype.'
            '</noscript></div>\n'
        )
        (docs / 'studies' / f'{filename}.md').write_text(page, encoding='utf-8')

    config = yaml.safe_load((ROOT / 'mkdocs.yml').read_text(encoding='utf-8'))
    config['docs_dir'] = str(docs)
    config['site_dir'] = str(destination / 'site')
    config.pop('site_url', None)
    # Demo values cannot enter the production evidence/publication hooks.
    config.pop('hooks', None)
    config['extra_css'] = [*config.get('extra_css', []),
                           'stylesheets/dashboard.css']
    config['extra_javascript'] = [*config.get('extra_javascript', []),
                                  'assets/dashboard.js']
    config['nav'] = [
        {'Home': 'index.md'},
        {'Studies': [{'Study verification': 'studies/index.md'},
                     *({title: f'studies/{study}.md'}
                       for study, title in STUDIES)]},
        {'Verification policy': 'verification.md'},
    ]
    config_path = destination / 'mkdocs.yml'
    config_path.write_text(yaml.safe_dump(config, sort_keys=False),
                           encoding='utf-8')
    subprocess.run([sys.executable, '-m', 'mkdocs', 'build', '--strict',
                    '--config-file', str(config_path)], check=True, cwd=ROOT)
    print(f'Prototype output: {destination / "site"}')
    print('Open /studies/cdiscpilot01/ after serving this directory.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path,
                        default=ROOT / '.build/study-dashboard-preview')
    args = parser.parse_args()
    build(args.output_dir)


if __name__ == '__main__':
    main()
