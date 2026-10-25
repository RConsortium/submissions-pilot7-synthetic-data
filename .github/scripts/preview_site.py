#!/usr/bin/env python3
"""Strict PR layout/link check with explicit placeholders for generated results."""

from pathlib import Path
import shutil
import subprocess
import sys

from study_evidence import catalog

ROOT = Path(__file__).resolve().parents[2]


def prepare_preview(root, work):
    """Use a separate docs tree; never fabricate validation reports or publish it."""
    docs = work / 'docs'
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(root / 'docs', docs)
    shutil.rmtree(docs / 'evidence', ignore_errors=True)
    studies = docs / 'studies'
    studies.mkdir(exist_ok=True)
    # Drop local generated pages so this also works after a full local site build.
    for page in studies.glob('*.md'):
        if page.name not in {'kn189.md', 'kn564.md'}:
            page.unlink()
    note = ('!!! note "PR layout preview"\n\n'
            '    Study results are omitted from this preview. Full validation and\n'
            '    reference comparison run before publication on main.\n')
    entries = catalog(root)
    for name, entry in entries.items():
        (studies / f'{name}.md').write_text(f'# {entry["title"]}\n\n{note}')
    (studies / 'index.md').write_text('# Study verification\n\n' + note + '\n' + '\n'.join(
        f'- [{entry["title"]}]({name}.md)' for name, entry in entries.items()) + '\n')
    config = work / 'mkdocs.yml'
    # INHERIT preserves paths resolved relative to the original configuration.
    config.write_text(f'INHERIT: {root / "mkdocs.yml"}\ndocs_dir: {docs}\nsite_dir: {work / "site"}\n')
    return config


if __name__ == '__main__':
    config = prepare_preview(ROOT, ROOT / '.build/site-preview')
    subprocess.run([sys.executable, str(ROOT / '.github/scripts/check_ascii.py'),
                    '--repo-root', str(config.parent / 'docs')], check=True)
    subprocess.run([sys.executable, '-m', 'mkdocs', 'build', '--strict',
                    '--config-file', str(config)], check=True)
