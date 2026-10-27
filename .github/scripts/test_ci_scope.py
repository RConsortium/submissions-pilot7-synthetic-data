"""Regression tests for selecting sufficient checks without unrelated studies."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from ci_scope import PLAN, PY_PLAN, R_PLAN, WORKER, changed_paths, select_checks
from run_core import ROOT
from preview_site import prepare_preview


class ScopeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / '.github').mkdir()
        (self.root / '.github/repo-structure.json').write_text(json.dumps({'non_study_dirs': ['docs']}))
        entries = {name: {'title': name} for name in ('cdiscpilot01', 'submission-pilot3', 'submission-pilot5')}
        entries['submission-pilot6'] = {'title': 'Pilot 6', 'allow_pending': True}
        (self.root / '.github/yamaa-studies.json').write_text(json.dumps(entries))
        for name in entries:
            source = self.root / name / 'data/sdtm'
            source.mkdir(parents=True)
            (source / 'dm.parquet').touch()
            if name != 'submission-pilot6':
                project = self.root / name / 'spec/yamaa'
                project.mkdir(parents=True)
                (project / 'project.yaml').touch()
        runner = self.root / 'submission-pilot3/program/adam/R'
        runner.mkdir(parents=True)
        (runner / 'run.R').touch()

    def scope(self, *paths):
        return select_checks(self.root, paths)

    def test_prompts_guides_and_generated_reports_need_no_study_jobs(self):
        for path in ('.automation/triage_issues.md', '.automation/consistency_review/workflow.md',
                     'AGENTS.md', 'README.md',
                     '.github/AUTOMATION.md', 'submission-pilot3/program/adam/README.md',
                     'submission-pilot3/spec/yamaa/README.md',
                     'submission-pilot3/data/adam/dataset_comment.md',
                     'submission-pilot3/data/adam/core-report-ADAM.xlsx'):
            with self.subTest(path=path):
                scope = self.scope(path)
                self.assertEqual(scope['studies'], [])
                self.assertFalse(any(scope[key] for key in ('website', 'plan_python', 'plan_r', 'compare')))

    def test_website_only_needs_layout_preview(self):
        scope = self.scope('docs/index.md', 'mkdocs.yml')
        self.assertTrue(scope['website'])
        self.assertEqual(scope['studies'], [])
        self.assertFalse(scope['publication'])

    def test_study_spec_and_python_changes_select_only_that_study(self):
        for path in ('submission-pilot3/spec/yamaa/adsl.yaml',
                     'submission-pilot3/program/adam/python/compare.py'):
            self.assertEqual(self.scope(path)['studies'], [
                {'study': 'submission-pilot3', 'yamaa': True, 'core': False, 'r': False}])

    def test_a_shared_layer_selects_exactly_the_studies_that_inherit_it(self):
        layers = {'spec/yamaa/pilot-program/adsl_v1.yaml': 'yamaa: "1.0"\n',
                  'spec/yamaa/pilot-program/adsl_v2.yaml': 'parent: adsl_v1.yaml\n',
                  'cdiscpilot01/spec/yamaa/adsl.yaml':
                      'parent: ../../../spec/yamaa/pilot-program/adsl_v1.yaml\n'}
        for study in ('submission-pilot3', 'submission-pilot5'):
            layers[f'{study}/spec/yamaa/adsl.yaml'] = \
                'parent: ../../../spec/yamaa/pilot-program/adsl_v2.yaml\n'
        for name, text in layers.items():
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            (self.root / name).write_text(text)
        cases = [
            ('version 1', 'spec/yamaa/pilot-program/adsl_v1.yaml',
             ['cdiscpilot01', 'submission-pilot3', 'submission-pilot5']),
            ('version 2', 'spec/yamaa/pilot-program/adsl_v2.yaml',
             ['submission-pilot3', 'submission-pilot5']),
            ('guide', 'spec/yamaa/README.md', []),
        ]
        for label, path, studies in cases:
            with self.subTest(case=label):
                self.assertEqual(self.scope(path)['studies'], [
                    {'study': name, 'yamaa': True, 'core': False, 'r': False} for name in studies])

    def test_source_pipeline_changes_select_its_study_before_sdtm_exists(self):
        manifest = self.root / '.github/yamaa-studies.json'
        entries = json.loads(manifest.read_text())
        entries['cdiscpilot01']['prepare'] = 'program/run.py'
        manifest.write_text(json.dumps(entries))
        for path in ('cdiscpilot01/program/odm/extract.py',
                     'cdiscpilot01/program/engine.py',
                     'cdiscpilot01/data/odm/source.xml'):
            with self.subTest(path=path):
                self.assertEqual(self.scope(path)['studies'], [
                    {'study': 'cdiscpilot01', 'yamaa': True, 'core': False, 'r': False}])

    def test_data_change_combines_yamaa_and_core_in_one_job(self):
        self.assertEqual(self.scope('submission-pilot5/data/sdtm/ae.parquet')['studies'], [
            {'study': 'submission-pilot5', 'yamaa': True, 'core': True, 'r': False}])

    def test_generators_and_mapping_select_their_actual_dependencies(self):
        self.assertEqual(self.scope(PY_PLAN)['studies'], [])
        self.assertTrue(self.scope(PY_PLAN)['plan_python'])
        self.assertFalse(self.scope(PY_PLAN)['plan_r'])
        self.assertTrue(self.scope(R_PLAN)['plan_r'])
        self.assertFalse(self.scope(R_PLAN)['plan_python'])
        scope = self.scope(PLAN)
        self.assertTrue(scope['plan_python'] and scope['plan_r'])
        self.assertEqual(scope['studies'], [
            {'study': 'submission-pilot3', 'yamaa': True, 'core': False, 'r': False}])
        scope = self.scope('submission-pilot3/data/sdtm/qs.parquet')
        self.assertTrue(scope['plan_python'] and scope['plan_r'])

    def test_analysis_window_lookup_is_separate_from_planning_relation(self):
        scope = self.scope('submission-pilot3/data/mapping/analysis_window.csv')
        self.assertFalse(scope['plan_python'] or scope['plan_r'])
        self.assertEqual(scope['studies'], [
            {'study': 'submission-pilot3', 'yamaa': True, 'core': False, 'r': False}])

    def test_r_program_change_checks_r_without_unrelated_python_execution(self):
        self.assertEqual(self.scope('submission-pilot3/program/adam/R/run.R')['studies'], [
            {'study': 'submission-pilot3', 'yamaa': False, 'core': False, 'r': True}])

    def test_engine_pin_change_rechecks_publication_and_r_for_that_study(self):
        scope = self.scope('submission-pilot3/program/adam/python/requirements.txt')
        self.assertTrue(scope['publication'])
        self.assertEqual(scope['studies'], [
            {'study': 'cdiscpilot01', 'yamaa': True, 'core': False, 'r': False},
            {'study': 'submission-pilot3', 'yamaa': True, 'core': False, 'r': True},
            {'study': 'submission-pilot5', 'yamaa': True, 'core': False, 'r': False}])

    def test_shared_engine_and_worker_changes_cover_all_affected_studies(self):
        scope = self.scope('.github/scripts/validate_yamaa.py')
        self.assertEqual({row['study'] for row in scope['studies']},
                         {'cdiscpilot01', 'submission-pilot3', 'submission-pilot5'})
        self.assertTrue(all(row['yamaa'] and not row['core'] for row in scope['studies']))
        scope = self.scope('.github/scripts/run_core.py')
        self.assertEqual(len(scope['studies']), 4)
        self.assertTrue(all(row['core'] and not row['yamaa'] for row in scope['studies']))
        scope = self.scope(WORKER)
        self.assertEqual(len(scope['studies']), 4)
        self.assertTrue(next(row['r'] for row in scope['studies'] if row['study'] == 'submission-pilot3'))

    def test_publication_code_requires_fresh_full_publication_check(self):
        for path in ('.github/scripts/build_study_docs.py', '.github/scripts/build_index_table.py',
                     '.github/yamaa-studies.json', WORKER,
                     '.github/scripts/study_dashboard/artifacts.py', '.github/scripts/study_artifacts.py',
                     '.github/dashboard.json', '.github/synthetic-studies.json', 'docs/assets/dashboard/app.js',
                     'docs/stylesheets/dashboard.css', '.github/tests/dashboard/modules.test.js',
                     'submission-pilot3/spec/review/questions.json',
                     'submission-pilot3/spec/source/adrg.pdf',
                     '.github/scripts/verify_derivations.py', '.github/scripts/consistency_report.py',
                     '.automation/consistency_review/rules.yaml',
                     '.github/schemas/review-issues.schema.json', 'docs/requirements.txt',
                     'cdiscpilot01/spec/review/adsl-issues.json',
                     'cdiscpilot01/spec/review/adsl-claims.json'):
            scope = self.scope(path)
            self.assertTrue(scope['publication'])
            self.assertEqual(sum(row['yamaa'] for row in scope['studies']), 3)

    def test_synthetic_source_changes_check_the_source_dashboard_publication(self):
        (self.root / '.github/synthetic-studies.json').write_text(json.dumps({'kn189': {'title': 'KN189'}}))
        for path in ('kn189/data/odm/kn189_odm.tar.gz', 'kn189/spec/define/define.xml'):
            scope = self.scope(path)
            self.assertTrue(scope['publication'])
            self.assertEqual(sum(row['yamaa'] for row in scope['studies']), 3)

    def test_missing_official_project_cannot_silently_skip_validation(self):
        import shutil
        shutil.rmtree(self.root / 'submission-pilot3')
        scope = self.scope('.github/scripts/validate_yamaa.py')
        self.assertIn('submission-pilot3', [row['study'] for row in scope['studies']])

    def test_comparator_only_change_needs_self_check_without_derivation(self):
        scope = self.scope('.github/scripts/compare_adam.py')
        self.assertTrue(scope['compare'])
        self.assertEqual(scope['studies'], [])

    def test_ci_workflow_changes_exercise_conditional_steps_in_one_job(self):
        scope = self.scope('.github/workflows/ci.yml')
        self.assertTrue(scope['plan_python'] and scope['plan_r'] and scope['compare'])
        self.assertEqual(scope['studies'], [])

    def test_git_rename_covers_source_and_destination_studies(self):
        def git(*args):
            return subprocess.check_output(['git', *args], cwd=self.root, text=True)
        git('init', '--quiet')
        source = self.root / 'cdiscpilot01/data/sdtm/ae.parquet'
        source.write_bytes(b'dataset')
        git('add', str(source))
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'initial')
        git('mv', str(source), str(self.root / 'submission-pilot3/data/sdtm/ae.parquet'))
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'move')
        paths = changed_paths(self.root, 'HEAD^', 'HEAD')
        scope = self.scope(*paths)
        self.assertEqual({row['study'] for row in scope['studies']}, {'cdiscpilot01', 'submission-pilot3'})
        self.assertTrue(all(row['core'] and row['yamaa'] for row in scope['studies']))

    def test_no_file_count_cap_and_deleted_inputs_still_select_the_study(self):
        paths = [f'.automation/note-{number}.md' for number in range(3500)]
        paths.append('submission-pilot3/data/sdtm/deleted.parquet')
        self.assertEqual(len(self.scope(*paths)['studies']), 1)

    def test_core_checks_precede_any_generated_adam_outputs(self):
        import yaml
        workflow = yaml.safe_load((ROOT / WORKER).read_text())
        names = [step.get('name') for step in workflow['jobs']['validate']['steps']]
        self.assertLess(names.index('Validate and stage CORE reports'),
                        names.index('Check, build, compare, and record evidence'))
        self.assertLess(names.index('Validate and stage CORE reports'),
                        names.index('Run the R program and compare with official references'))

    def test_preview_omits_results_and_keeps_canonical_docs_untouched(self):
        docs = self.root / 'docs/studies'
        docs.mkdir(parents=True)
        (docs / 'kn189.md').write_text('# Synthetic study\n')
        (docs / 'submission-pilot3.md').write_text('old generated result')
        (self.root / 'docs/evidence').mkdir()
        (self.root / 'docs/evidence/study.json').write_text('{"status":"succeeded"}')
        source_index = ('# Home\n\n<!-- pilot-metrics:begin -->\n'
                        'old numeric snapshot\n<!-- pilot-metrics:end -->\n')
        (self.root / 'docs/index.md').write_text(source_index)
        (self.root / 'mkdocs.yml').write_text('site_name: Preview\n')
        config = prepare_preview(self.root, self.root / '.build/site-preview')
        page = config.parent / 'docs/studies/submission-pilot3.md'
        self.assertIn('PR layout preview', page.read_text())
        self.assertNotIn('old generated result', page.read_text())
        self.assertFalse((config.parent / 'docs/evidence').exists())
        self.assertEqual((docs / 'submission-pilot3.md').read_text(), 'old generated result')
        self.assertEqual((config.parent / 'docs/studies/kn189.md').read_text(), '# Synthetic study\n')
        preview_index = (config.parent / 'docs/index.md').read_text()
        self.assertIn('PR layout preview', preview_index)
        self.assertNotIn('old numeric snapshot', preview_index)
        self.assertNotIn('<!-- pilot-metrics:begin -->', preview_index)
        self.assertEqual((self.root / 'docs/index.md').read_text(), source_index)
        self.assertIn('hooks: []', config.read_text())


if __name__ == '__main__':
    unittest.main()
