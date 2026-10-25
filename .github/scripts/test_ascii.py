"""Check ASCII enforcement and preservation of clinical reference artifacts."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from check_ascii import check_files, source_files


CHECKER = Path(__file__).with_name('check_ascii.py')


class AsciiTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def test_reports_file_line_and_byte_column(self):
        self.write('docs/guide.md', '# Guide\nUse \u2192 here.\n')
        self.assertEqual(
            check_files(self.root, source_files(self.root)),
            ['ERROR: docs/guide.md:2:5: non-ASCII byte 0xE2; '
             'use ASCII punctuation and symbols'],
        )

    def test_checks_new_sources_and_generated_pages(self):
        names = (
            'AGENTS.md', '.github/workflows/check.yml',
            '.automation/bootstrap.R', 'study/spec/yamaa/adsl.yaml',
            'study/program/adam/run.py', 'docs/studies/study.md',
            'docs/stylesheets/extra.css', 'mkdocs.yml',
        )
        for name in names:
            self.write(name, 'ASCII text -> OK\n')
        self.assertEqual(
            sorted(path.as_posix() for path in source_files(self.root)),
            sorted(names),
        )
        self.assertEqual(check_files(self.root, source_files(self.root)), [])

    def test_preserves_reference_data_archives_and_build_output(self):
        names = (
            '.archieve/old/README.md', '.git/hooks/helper.py',
            '.venv/package.py', '.build/validation/study.json',
            'site/index.html', 'docs/evidence/study.json',
            'study/data/sdtm/labels.csv', 'core-report-SDTM.json',
            'cdiscpilot01/spec/define/define-adam.xml',
            'submission-pilot3/spec/define/define-adam.xml',
            'submission-pilot5/spec/define/define-adam.xml',
            'submission-pilot6/program/adam/upstream/code/tables/t_14_1_03.r',
        )
        for name in names:
            self.write(name, 'Original \u00e9 data\n')
        self.assertEqual(list(source_files(self.root)), [])
        for name in names:
            self.assertEqual((self.root / name).read_text(), 'Original \u00e9 data\n')

    def test_reference_exceptions_do_not_cover_other_sources(self):
        names = (
            'cdiscpilot01/spec/define/custom.xml',
            'docs/data/notes.md', 'docs/build/notes.md',
            '.github/data/notes.md',
            'core-report-helper.py',
            'submission-pilot6/program/adam/upstream/code/adam/adsl.r',
        )
        for name in names:
            self.write(name, '\u00e9\n')
        self.assertEqual(
            check_files(self.root, source_files(self.root)),
            [f'ERROR: {name}:1:1: non-ASCII byte 0xC3; '
             'use ASCII punctuation and symbols' for name in sorted(names)],
        )

    def test_cli_fails_on_non_ascii_and_passes_after_correction(self):
        for text, expected_code in (('Use \u2192\n', 1), ('Use ->\n', 0)):
            with self.subTest(text=text):
                self.write('README.md', text)
                result = subprocess.run(
                    [sys.executable, str(CHECKER), '--repo-root', str(self.root)],
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, expected_code, result.stdout)


if __name__ == '__main__':
    unittest.main()
