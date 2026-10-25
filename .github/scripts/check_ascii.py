#!/usr/bin/env python3
"""Require ASCII source text while preserving clinical reference artifacts."""

import argparse
import os
from pathlib import Path
import sys


SOURCE_SUFFIXES = {
    '.cfg', '.css', '.csv', '.html', '.ini', '.jq', '.js', '.json', '.md',
    '.py', '.qmd', '.r', '.rd', '.rmd', '.sas', '.sh', '.toml', '.ts',
    '.txt', '.xml', '.yaml', '.yml',
}
SOURCE_NAMES = {
    '.editorconfig', '.gitattributes', '.gitignore', 'DESCRIPTION',
    'LICENSE', 'Makefile', 'NAMESPACE',
}
SKIPPED_ROOTS = {'.archieve', '.build', '.git', '.venv', 'site'}
SKIPPED_DIRECTORY_NAMES = {'__pycache__', 'node_modules'}
REFERENCE_FILES = {
    'cdiscpilot01/spec/define/define-adam.xml',
    'submission-pilot3/spec/define/define-adam.xml',
    'submission-pilot5/spec/define/define-adam.xml',
}


def skip_directory(relative):
    """Exclude archives, build output, and each study's clinical data folder."""
    parts = relative.parts
    return (
        (len(parts) == 1 and parts[0] in SKIPPED_ROOTS)
        or parts[-1] in SKIPPED_DIRECTORY_NAMES
        or relative.as_posix() == 'docs/evidence'
        or (
            len(parts) == 2
            and parts[1] == 'data'
            and not parts[0].startswith('.')
            and parts[0] != 'docs'
        )
    )


def source_files(root):
    """Include new sources and generated study pages without scanning datasets."""
    for directory, subdirectories, files in os.walk(root):
        base = Path(directory).relative_to(root)
        subdirectories[:] = sorted(
            name for name in subdirectories
            if not skip_directory(base / name)
        )
        for name in sorted(files):
            relative = base / name
            if relative.as_posix() in REFERENCE_FILES:
                continue
            # Downloaded CORE reports contain original clinical values.
            if (base == Path('.') and name.startswith('core-report-')
                    and relative.suffix.lower() == '.json'):
                continue
            if relative.suffix.lower() in SOURCE_SUFFIXES or name in SOURCE_NAMES:
                yield relative


def check_files(root, paths):
    """Report the first non-ASCII byte in each source, with its line and column."""
    errors = []
    for relative in sorted(paths):
        try:
            content = (root / relative).read_bytes()
        except OSError as exc:
            errors.append(f'ERROR: {relative}: cannot read source: {exc}')
            continue
        for offset, value in enumerate(content):
            if value <= 0x7f:
                continue
            line = content.count(b'\n', 0, offset) + 1
            column = offset - content.rfind(b'\n', 0, offset)
            errors.append(
                f'ERROR: {relative}:{line}:{column}: non-ASCII byte 0x{value:02X}; '
                'use ASCII punctuation and symbols'
            )
            break
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path,
                        default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.repo_root.resolve()
    if not root.is_dir():
        parser.error(f'repository root is not a directory: {root}')
    paths = list(source_files(root))
    errors = check_files(root, paths)
    for error in errors:
        print(error)
    print(f'ASCII check: {len(paths)} source file(s), {len(errors)} error(s).')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
