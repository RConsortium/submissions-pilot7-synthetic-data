#!/usr/bin/env python3
"""Strict PR layout/link check with explicit placeholders for generated results."""

from pathlib import Path
import shutil
import subprocess
import sys

from study_evidence import catalog
from build_index_table import BEGIN, replace_block
from dashboard_nav import populate
from study_dashboard.synthetic import build_synthetic, synthetic_catalog

ROOT = Path(__file__).resolve().parents[2]


def prepare_preview(root, work):
    """Use a separate docs tree; never fabricate validation reports or publish it."""
    docs = work / 'docs'
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(root / 'docs', docs, ignore=shutil.ignore_patterns('evidence'))
    studies = docs / 'studies'
    studies.mkdir(exist_ok=True)
    # Drop local generated pages so this also works after a full local site build.
    for page in studies.glob('*.md'):
        if page.name not in {'kn189.md', 'kn564.md'}:
            page.unlink()
    note = ('!!! note "PR layout preview"\n\n'
            '    Study results are omitted from this preview. Full validation and\n'
            '    reference comparison run before publication on main.\n')
    index = docs / 'index.md'
    if index.exists() and BEGIN in index.read_text():
        index.write_text(replace_block(index.read_text(), note.splitlines()))
    entries = catalog(root)
    for name, entry in entries.items():
        (studies / f'{name}.md').write_text(f'# {entry["title"]}\n\n{note}')
    (studies / 'index.md').write_text('# Pilot study report\n\n' + note + '\n' + '\n'.join(
        f'- [{entry["title"]}]({name}.md)' for name, entry in entries.items()) + '\n')
    config = work / 'mkdocs.yml'
    # The layout preview omits the hook that requires fresh validation reports.
    import yaml
    source_config = yaml.safe_load((root / "mkdocs.yml").read_text())
    nav = populate(source_config.get("nav", []), root)
    config.write_text(f'INHERIT: {root / "mkdocs.yml"}\ndocs_dir: {docs}\n'
                      f'site_dir: {work / "site"}\nhooks: []\n' +
                      (yaml.safe_dump({"nav": nav}, sort_keys=False) if nav else ""))
    if synthetic_catalog(root) or any(e.get('category') == 'synthetic' for e in entries.values()):
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        destination = docs / 'evidence/dashboard'
        records = build_synthetic(root, destination, revision, allow_unbuilt=True)
        from study_dashboard.datasets import write_json
        from study_dashboard.config import comments
        write_json(destination / 'index.json', {
            'schema_version': 1, 'revision': revision, 'studies': [],
            'synthetic_studies': records, 'comments': comments(root),
        })
        for item in records:
            if not item['workspace'] and item['id'] in synthetic_catalog(root):
                (studies / f"{item['id']}.md").write_text(f"# {item['title']}\n\n{note}")
    return config


if __name__ == '__main__':
    config = prepare_preview(ROOT, ROOT / '.build/site-preview')
    subprocess.run([sys.executable, str(ROOT / '.github/scripts/check_ascii.py'),
                    '--repo-root', str(config.parent / 'docs')], check=True)
    subprocess.run([sys.executable, '-m', 'mkdocs', 'build', '--strict',
                    '--config-file', str(config)], check=True)
