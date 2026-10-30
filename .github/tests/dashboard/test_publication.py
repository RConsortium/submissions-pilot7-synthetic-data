"""A future study must publish without study-specific Python or JavaScript edits."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import pyarrow as pa
import pyarrow.parquet as pq
from build_study_docs import generate
from dashboard_nav import study_navigation, synthetic_navigation
from study_artifacts import artifact_snapshot
from synthetic_evidence import artifact_inventory
from study_dashboard import artifacts, pages, workspace
from study_dashboard.datasets import read_table
from study_dashboard.summaries import review_counts, summary_cards
from build_index_table import build_table

PIN = "a" * 40


class PublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.entries = {
            "future-study": {
                "title": "Future study",
                "description": "New study",
                "source": "https://example.test/study",
                "comparison": "optional",
                "dashboard": {"subject_key": "PARTICIPANT", "default_subject_count": 2},
            },
            "pending-study": {
                "title": "Pending study",
                "description": "Unstarted",
                "source": "https://example.test/pending",
                "comparison": "optional",
                "allow_pending": True,
            },
        }
        self.write(".github/yamaa-studies.json", json.dumps(self.entries))
        self.write(
            "future-study/program/adam/python/requirements.txt",
            f"git+https://github.com/elong0527/yamaa.git@{PIN}",
        )
        self.write(
            "future-study/spec/yamaa/project.yaml", "adam:\n  specs: [custom.yaml]\n"
        )
        self.write(
            "future-study/spec/yamaa/custom.yaml",
            """domain: CUSTOM
input: {SRC: {path: ../../data/sdtm/source.parquet}}
output: {path: ../../data/adam/custom-yamaa.parquet, columns: [PARTICIPANT, VALUE]}
columns:
  - {name: PARTICIPANT, derivation: SRC.PARTICIPANT}
  - {name: VALUE, label: Value, derivation: SRC.VALUE}
""",
        )
        table = pa.table({"PARTICIPANT": ["001", "002", "003"], "VALUE": [1, 2, 3]})
        for relative in ["data/sdtm/source.parquet", "data/adam/custom-yamaa.parquet"]:
            path = self.root / "future-study" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(table, path)
        self.reports = {
            "future-study": {
                "study": "future-study",
                "repository_commit": "commit",
                "status": "succeeded",
                "yamaa_revision": PIN,
                "yamaa_version": "1.0",
                "created_utc": "now",
                "datasets": [
                    {
                        "domain": "CUSTOM",
                        "spec": "future-study/spec/yamaa/custom.yaml",
                        "build": "succeeded",
                        "comparison": "unavailable",
                        "rows": 3,
                        "columns": 2,
                    }
                ],
            },
            "pending-study": {
                "study": "pending-study",
                "repository_commit": "commit",
                "status": "pending",
                "reason": "No project yet.",
                "datasets": [],
            },
        }
        self.refresh()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def refresh(self):
        self.reports["future-study"]["artifacts"] = artifact_snapshot(
            self.root, "future-study"
        )
        for name, report in self.reports.items():
            self.write(f".build/validation/{name}.json", json.dumps(report))

    def generate(self):
        return generate(self.root, self.root / ".build/validation", "commit")

    def test_catalog_discovers_future_and_pending_studies_with_honest_comparison_coverage(
        self,
    ):
        target = self.generate()
        catalog = json.loads((target / "future-study/catalog.json").read_text())
        self.assertEqual(catalog["subjects"], ["001", "002", "003"])
        self.assertEqual(catalog["settings"]["default_subject_count"], 2)
        self.assertEqual(catalog["settings"]["subject_key"], "PARTICIPANT")
        self.assertEqual(catalog["tables"]["t000"]["subject_index"], 0)
        self.assertIsNone(catalog["datasets"][0]["reference"])
        self.assertEqual(catalog["datasets"][0]["comparison"], "unavailable")
        self.assertEqual(catalog["metrics"]["matched"], [0, 0, 0])
        self.assertEqual(
            json.loads((target / "future-study/report.json").read_text())["coverage"][
                "define_xml"
            ],
            "not_available",
        )
        pending = json.loads((target / "pending-study/catalog.json").read_text())
        self.assertEqual(pending["status"], "pending")
        self.assertFalse((target / "pending-study/report.json").exists())
        index = json.loads((target / "index.json").read_text())
        self.assertIsNone(index["studies"][1]["subjects"])
        self.assertIn(
            "No project yet.", (self.root / "docs/studies/pending-study.md").read_text()
        )
        self.assertEqual(
            study_navigation(self.root, [{"Manual": "studies/manual.md"}]),
            [
                {"Pilot study report": "studies/index.md"},
                {"Future study": "studies/future-study.md"},
                {"Pending study": "studies/pending-study.md"},
                {"Manual": "studies/manual.md"},
            ],
        )

    def test_study_report_states_unavailable_comparisons_and_pending_studies(self):
        self.generate()
        page = (self.root / "docs/studies/index.md").read_text()
        for expected in [
            "This report summarizes the findings. 1 study is pending validation.</p>",
            "1 / 2 studies validated",
            "No official reference",
            '<a href="pending-study/">Pending study</a><small>Pending</small></th>',
            '<td class="report-cell"><span class="report-status neutral">No reference</span>'
            '<span class="report-dims">3 &#215; 2</span>'
            '<span class="report-status report-issues neutral" '
            'aria-label="0 issues for Future study / CUSTOM" '
            'aria-describedby="dataset-issues-note">0 issues</span></td><td class="report-cell">-</td>',
            "No reference: no official reference is staged.",
            "<td>New study</td><td>Unstarted<small>Validation pending. No project yet.</small></td>",
            '<tr><th scope="row">ADaM datasets matched</th><td>No official reference</td><td>-</td></tr>',
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, page)
        self.assertNotIn("Study validation records", page)

    def test_study_report_documents_exclude_r_and_sas_programs(self):
        target = self.generate()
        catalog = json.loads((target / "future-study/catalog.json").read_text())
        report = json.loads((target / "future-study/report.json").read_text())
        names = ["sap.pdf", "spec.xlsx", "define.xml", "adsl.R", "adae.r", "adlbc.SAS", "adtte.sas"]
        report["documents"] = [
            {"name": name, "path": f"future-study/spec/source/{name}"} for name in names
        ]
        page = "".join(pages._overview([(catalog, report)]))
        self.assertIn(
            '<tr><th scope="row">Documents</th><td>sap.pdf, spec.xlsx, define.xml</td></tr>',
            page,
        )
        self.assertEqual([d["name"] for d in report["documents"]], names)

    def test_complete_reference_agreement_retains_open_review_and_criticality(self):
        issues = [{"critical": {"status": "yes"}}, {"critical": {"status": "no"}}, {}]
        page = summary_cards([5, 100, 2300000], [5, 100, 2300000], issues)
        self.assertIn("<strong>100%</strong> of reference datasets matched", page)
        self.assertIn("<strong>3</strong> findings awaiting review", page)
        self.assertIn("1 critical; 1 non-critical; 1 needing assessment", page)
        self.assertIn("Cells in matching datasets</dt><dd>2.3M / 2.3M", page)
        self.assertIn("Findings can remain open even when reference agreement is 100%", page)
        self.assertEqual(review_counts(issues), {"yes": 1, "no": 1, "needs_review": 1})

    @patch.dict("os.environ", {"GITHUB_SHA": "commit"})
    def test_home_page_shows_review_counts_separately_and_rejects_stale_summary(self):
        target = self.generate()
        table = "\n".join(build_table(self.root, self.root / ".build/validation"))
        self.assertIn("Published ADaM reference agreement", table)
        self.assertIn("No official reference", table)
        self.assertIn("[0 findings](studies/future-study.md#future-study/overview)", table)
        self.assertIn("0 critical; 0 non-critical; 0 needing assessment", table)
        self.assertIn("Review pending", table)
        with patch.dict("os.environ", {"GITHUB_SHA": "another-commit"}):
            with self.assertRaisesRegex(ValueError, "not from this source commit"):
                build_table(self.root, self.root / ".build/validation")
        path = target / "future-study/report.json"
        report = json.loads(path.read_text())
        report["revision"] = "old-commit"
        path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "not from this publication"):
            build_table(self.root, self.root / ".build/validation")

    def test_study_report_does_not_deny_an_uncompared_configured_reference(self):
        # Validation compares only the default reference path, so a configured
        # reference can be published with an unavailable comparison.
        source = self.root / "future-study/data/adam/custom-yamaa.parquet"
        source.with_name("published-name.parquet").write_bytes(source.read_bytes())
        self.entries["future-study"]["dashboard"]["references"] = {
            "CUSTOM": "data/adam/published-name.parquet"
        }
        self.write(".github/yamaa-studies.json", json.dumps(self.entries))
        self.refresh()
        self.generate()
        page = (self.root / "docs/studies/index.md").read_text()
        for expected in [
            '<span class="report-status attention">Not compared</span>',
            "Not compared: a reference is staged but the comparator did not check it.",
            "<strong>0%</strong> of reference datasets matched",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, page)
        self.assertNotIn("No reference", page)

    def test_dataset_badges_count_grouped_issues_within_the_dataset(self):
        target = self.generate()
        catalog = json.loads((target / "future-study/catalog.json").read_text())
        report = json.loads((target / "future-study/report.json").read_text())
        report["review"]["issues"] = [
            {"id": "a", "dataset": "CUSTOM", "check_ids": ["one", "two", "three"]},
            {"id": "b", "dataset": "CUSTOM", "check_ids": ["four"]},
            {"id": "c", "dataset": "OTHER", "check_ids": ["five"]},
        ]
        page = "".join(pages._matrix([(catalog, report)]))
        self.assertIn('aria-label="2 issues for Future study / CUSTOM"', page)
        self.assertIn('href="future-study/#future-study/overview/CUSTOM?findingSearch=CUSTOM">2 issues</a>', page)
        self.assertNotIn(">3 issues<", page)
        self.assertIn('id="dataset-issues-note"', page)

    def test_study_report_keeps_each_studys_dataset_description(self):
        # Studies may publish different Define-XML labels for one dataset name.
        self.assertEqual(
            pages._descriptions(
                {
                    "Subject-Level Analysis": ["Pilot A"],
                    "Subject-Level Analysis Dataset": ["Pilot B", "Pilot C"],
                }
            ),
            "Subject-Level Analysis<small>Pilot A</small>"
            "Subject-Level Analysis Dataset<small>Pilot B, Pilot C</small>",
        )
        self.assertEqual(
            pages._descriptions({"Adverse Events": ["Pilot A", "Pilot B"]}),
            "Adverse Events",
        )
        self.assertEqual(pages._descriptions({}), "")

    def test_changed_artifacts_during_export_leave_previous_bundle_intact(self):
        current = self.generate()
        before = (current / "index.json").read_bytes()
        export = workspace.export_table

        def tampered(*args, **kwargs):
            result = export(*args, **kwargs)
            self.write(
                "future-study/spec/yamaa/custom.yaml", "changed after validation"
            )
            return result

        with patch.object(workspace, "export_table", side_effect=tampered):
            with self.assertRaisesRegex(ValueError, "artifacts changed"):
                self.generate()
        self.assertEqual((current / "index.json").read_bytes(), before)

    def test_synthetic_category_moves_workspace_out_of_pilot_report(self):
        self.entries['future-study']['category'] = 'synthetic'
        self.write('.github/yamaa-studies.json', json.dumps(self.entries))
        self.refresh()
        current = self.generate()
        self.assertNotIn({'Future study': 'studies/future-study.md'}, study_navigation(self.root, []))
        self.assertIn({'Future study': 'studies/future-study.md'}, synthetic_navigation(self.root))
        self.assertNotIn('Future study', (self.root / 'docs/studies/index.md').read_text())
        index = json.loads((current / 'synthetic/index.json').read_text())
        self.assertEqual([s['id'] for s in index['studies']], ['future-study'])
        self.assertTrue(index['studies'][0]['workspace'])
        self.assertTrue((current / 'future-study/catalog.json').is_file())

    def test_synthetic_build_exports_linked_workspace_without_reference_agreement(self):
        entry = self.entries.pop('future-study')
        self.write('.github/yamaa-studies.json', json.dumps(self.entries))
        self.write('.github/synthetic-studies.json', json.dumps({'future-study': {
            'title': entry['title'], 'description': entry['description'],
            'dashboard': entry['dashboard'], 'build_required': True,
        }}))
        for name in ['synthetic_odm.py', 'synthetic_checks.py', 'synthetic_evidence.py',
                     'validate_synthetic.py', 'resolved_specs.py', 'composed_specs.py', 'study_evidence.py',
                     'study_dashboard/specifications.py']:
            self.write('.github/scripts/' + name, '# execution fixture\n')
        self.write('.github/schemas/synthetic-review.schema.json', '{}')
        self.write('future-study/spec/source/protocol-sap.mmd', 'Retained protocol\n')
        for section in ['sdtm', 'adam']:
            self.write(f'future-study/data/{section}/define.xml', '<ODM/>')
        report = {
            'status': 'succeeded', 'source_revision': 'commit', 'created_utc': 'now',
            'engine': {'version': '1.0'}, 'source_subjects': 3,
            'datasets': [{**d, 'section': 'adam'} for d in self.reports['future-study']['datasets']],
            'define_xml': {}, 'reference_comparison': 'unavailable', 'human_review': 'pending',
            'review': {'findings': [], 'coverage': []}, 'summaries': {},
            'artifacts': artifact_inventory(self.root, 'future-study'),
        }
        self.write('.build/synthetic/future-study/report.json', json.dumps(report))
        self.refresh()
        current = self.generate()
        model = json.loads((current / 'future-study/catalog.json').read_text())
        self.assertEqual(model['subjects'], ['001', '002', '003'])
        self.assertEqual(model['metrics'], {'matched': [0, 0, 0], 'reference': [0, 0, 0]})
        dataset = model['datasets'][0]
        self.assertIsNone(dataset['reference'])
        self.assertEqual(dataset['comparison'], 'unavailable')
        spec = json.loads((current / 'future-study' / dataset['spec']).read_text())
        self.assertIn('SRC.VALUE', spec['lineage']['edges']['spec.VALUE'])
        self.assertEqual(model['development'], 'synthetic/future-study/catalog.json')
        self.assertTrue((current / 'synthetic/future-study/future-study-development.zip').is_file())

    def test_invalid_issue_schema_leaves_previous_bundle_intact(self):
        current = self.generate()
        before = (current / "index.json").read_bytes()
        self.write(
            "future-study/spec/review/custom-issues.json",
            json.dumps(
                {"schema_version": 99, "dataset": "CUSTOM", "checks": {}, "issues": []}
            ),
        )
        self.refresh()
        with self.assertRaisesRegex(ValueError, "review issues"):
            self.generate()
        self.assertEqual((current / "index.json").read_bytes(), before)

    def test_custom_reference_file_is_configured_without_loading_comparator_code(self):
        source = self.root / "future-study/data/adam/custom-yamaa.parquet"
        reference = source.with_name("published-name.parquet")
        reference.write_bytes(source.read_bytes())
        self.entries["future-study"]["dashboard"]["references"] = {
            "CUSTOM": "data/adam/published-name.parquet"
        }
        self.write(".github/yamaa-studies.json", json.dumps(self.entries))
        self.reports["future-study"]["datasets"][0]["comparison"] = "passed"
        self.refresh()
        target = self.generate()
        catalog = json.loads((target / "future-study/catalog.json").read_text())
        self.assertIsNotNone(catalog["datasets"][0]["reference"])
        self.assertEqual(catalog["metrics"]["matched"], [1, 2, 6])

    def test_missing_question_source_is_visible_without_an_invented_citation(self):
        self.write(
            "future-study/spec/review/questions.json",
            json.dumps(
                {
                    "schema_version": 1,
                    "questions": [
                        {
                            "id": "value-rule",
                            "dataset": "CUSTOM",
                            "variable": "VALUE",
                            "document": "spec/source/guide.pdf",
                            "section": "page-2",
                            "excerpt": "Expected source rule.",
                            "title": "Verify value rule",
                            "guidance": "Find the original.",
                        }
                    ],
                }
            ),
        )
        self.refresh()
        target = self.generate()
        finding = json.loads((target / "future-study/report.json").read_text())[
            "findings"
        ][0]
        self.assertEqual(finding["kind"], "missing_evidence")
        self.assertEqual(finding["source"]["url"], "")
        self.assertEqual(finding["spec"]["line"], 6)

    def test_empty_csv_retains_declared_schema(self):
        self.write("empty.csv", "PARTICIPANT,VALUE\n")
        self.assertEqual(
            read_table(self.root / "empty.csv", {"VALUE": "int"}).schema,
            pa.schema([("PARTICIPANT", pa.string()), ("VALUE", pa.int64())]),
        )

    def test_shared_stylesheet_changes_invalidate_the_study_evidence(self):
        self.write(
            "other-study/spec/source/original.xsl", "retained publisher stylesheet"
        )
        self.write(
            "future-study/spec/source/manifest.json",
            json.dumps(
                {
                    "files": [
                        {
                            "path": "future-study/spec/define/define-adam.xml",
                            "stylesheet": "other-study/spec/source/original.xsl",
                        }
                    ]
                }
            ),
        )
        self.refresh()
        self.generate()
        self.write("other-study/spec/source/original.xsl", "changed stylesheet")
        with self.assertRaisesRegex(ValueError, "artifacts changed"):
            self.generate()


if __name__ == "__main__":
    unittest.main()
