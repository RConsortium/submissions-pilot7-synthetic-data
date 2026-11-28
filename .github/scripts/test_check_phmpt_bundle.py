"""The PHMPT gate, one rule per case, on invented files.

Seam: check_phmpt_bundle.check() over a folder of files; every identifier,
program line, define text and value below is invented.
"""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_name = "check_phmpt_bundle"
_spec = importlib.util.spec_from_file_location(_name, HERE / f"{_name}.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

EVIDENCE = {"schema_version": 1, "meta": {"yamaa_commit": "abc1234", "source_commit": "def5678", "collected": "2026-01-01"},
            "gaps": {}, "studies": {}, "findings": []}
COLUMNS = {"schema_version": 1, "fields": gate.COLUMN_FIELDS, "statuses": {"reproduced": "Reproduced"},
           "datasets": {"phmpt/bnt162-01/27034/ADXX": {"layers": ["bnt162-01/27034/spec/yamaa/adxx.yaml"], "notes": [],
                                                       "columns": [["AVAL", "reproduced", 0, 0, 0, 3, None]]}}}
SPEC = "phmpt/bnt162-01/27034/spec/yamaa/adxx.yaml"
WITHHELD = f'"{gate.PLACEHOLDER}"'


def column(origin: str, text_key: str, text: str) -> str:
    """A spec with one column whose submission block holds an origin and a define text."""
    where = "      " if text_key == "description" else "    "
    return ("domain: ADXX\ncolumns:\n- name: AVAL\n  derivation: RAW.X\n  submission:\n    origins:\n"
            f"    - type: {origin}\n{where}{text_key}: {text}\n")


def bundle(root: Path, files: dict) -> None:
    base = {"docs/phmpt/evidence.json": json.dumps(EVIDENCE), "phmpt/README.md": "# Kit\n",
            SPEC: "domain: ADXX\ncolumns:\n- name: AVAL\n  derivation: RAW.X\n"}
    for rel, text in {**base, **files}.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if text is not None:
            p.write_bytes(text if isinstance(text, bytes) else text.encode())
        elif p.exists():
            p.unlink()


class GateRules(unittest.TestCase):
    def errors(self, files: dict, source=None) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle(root, files)
            return gate.check(root, source(root) if source else None)

    def test_each_rule_reports_its_violation(self):
        evidence_extra = {**EVIDENCE, "rows": [{"USUBJID": "X"}]}
        evidence_missing = {k: v for k, v in EVIDENCE.items() if k != "findings"}
        cases = [
            ("a clean bundle", {}, []),
            ("a file outside the allowlist", {"phmpt/notes.md": "x\n"},
             ["phmpt/notes.md: not in the publication allowlist"]),
            ("the site pages", {f"docs/phmpt/{p}.md": "# Page\n" for p in
                                ("index", "coverage", "glossary", "findings/bnt162-01")}, []),
            ("the kit's runner", {"phmpt/reproduce.sh": "#!/bin/sh\n"}, []),
            ("the decisions and the results", {"phmpt/DECISIONS.md": "# Owner decisions\n",
                                               "phmpt/data/reproduction/adam.json": "{}\n"}, []),
            ("a withheld method", {SPEC: column("Derived", "method", WITHHELD)}, []),
            ("a define method in a spec", {SPEC: column("Derived", "method", "Invented text of a received define")},
             [f"{SPEC}:8: 1 submission method or description text(s) where the placeholder belongs"]),
            ("a define description in a spec", {SPEC: column("Assigned", "description", "Invented define text")},
             [f"{SPEC}:8: 1 submission method or description text(s) where the placeholder belongs"]),
            ("a Predecessor's source column", {SPEC: column("Predecessor", "description", "RAW.X")}, []),
            ("a retired page", {"docs/phmpt/reproduce.md": "# Page\n"},
             ["docs/phmpt/reproduce.md: not in the publication allowlist"]),
            ("a site page outside the allowlist", {"docs/phmpt/notes.md": "x\n"},
             ["docs/phmpt/notes.md: not in the publication allowlist"]),
            ("a dataset", {"phmpt/bnt162-01/27034/data/adam/adxx.parquet": b"PAR1"},
             ["phmpt/bnt162-01/27034/data/adam/adxx.parquet: a data or document file; never published"]),
            ("a define", {"phmpt/bnt162-01/27034/spec/define/define-adam.xml": "<ODM/>"},
             ["phmpt/bnt162-01/27034/spec/define/define-adam.xml: a data or document file; never published"]),
            ("a non-ASCII byte", {"phmpt/README.md": "# Kit\nrows \u00d7 columns\n"},
             ["phmpt/README.md:2: non-ASCII byte 0xC3"]),
            ("an evidence key the schema does not name", {"docs/phmpt/evidence.json": json.dumps(evidence_extra)},
             ["evidence.json.rows: not in the published schema"]),
            ("an evidence key missing", {"docs/phmpt/evidence.json": json.dumps(evidence_missing)},
             ["evidence.json.findings: missing"]),
            ("no evidence", {"docs/phmpt/evidence.json": None}, ["docs/phmpt/evidence.json: missing"]),
            ("the column table", {"docs/phmpt/columns.json": json.dumps(COLUMNS)}, []),
            ("a column row of the wrong length", {"docs/phmpt/columns.json": json.dumps(
                {**COLUMNS, "datasets": {"d": {"layers": [], "notes": [], "columns": [["AVAL", "reproduced", 0]]}}})},
             ["columns.json.datasets.d.columns[0]: expected a list of 7"]),
            ("a column value in a row", {"docs/phmpt/columns.json": json.dumps(
                {**COLUMNS, "datasets": {"d": {"layers": [], "notes": [], "columns": [["AVAL", "reproduced", "1.5", 0,
                                                                                        None, None, None]]}}})},
             ["columns.json.datasets.d.columns[0][2]: expected int"]),
            ("a subject identifier pattern", {SPEC: "domain: ADXX\n# subject BNT162-01-999-99-9999\n"},
             [f"{SPEC}:2: a subject identifier pattern"]),
        ]
        for label, files, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(self.errors(files), expected, label)

    def test_a_work_tree_is_checked_as_git_would_commit_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle(root, {"phmpt/.gitignore": "*/*/data/\n",
                          "phmpt/bnt162-01/27034/data/adam/adxx.parquet": b"PAR1"})
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            self.assertEqual(gate.check(root), [], "fetched data in an ignored folder is not checked")
            subprocess.run(["git", "-C", str(root), "add", "-f", "phmpt/bnt162-01/27034/data/adam/adxx.parquet"],
                           check=True)
            self.assertEqual(gate.check(root), ["phmpt/bnt162-01/27034/data/adam/adxx.parquet: "
                                                "a data or document file; never published"])

    def test_source_backed_rules_report_ids_and_copied_text(self):
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest("pyarrow is not installed: the --source checks need it")
        program = ("if the invented flag is yes and the invented visit is the first then set "
                   "the invented analysis flag to yes for every record")

        def source(root: Path) -> Path:
            src = root / "src"
            dm = src / "bnt162-01/27034/data/sdtm/dm.parquet"
            dm.parent.mkdir(parents=True)
            pq.write_table(pa.table({"USUBJID": [f"ZZ-INVENTED-{i:04d}" for i in range(1, 201)],
                                     "SUBJID": [f"INV{i:04d}" for i in range(1, 201)]}), dm)
            prog = src / "bnt162-01/spec/source/program/adam/adxx.txt"
            prog.parent.mkdir(parents=True)
            prog.write_text(program)
            return src

        cases = [
            ("clean", {}, []),
            ("a USUBJID of the data", {SPEC: "domain: ADXX\nfilter: RAW.USUBJID = 'ZZ-INVENTED-0001'\n"},
             [f"{SPEC}: holds 1 subject identifier(s) of the submitted data"]),
            ("a program copied into a comment", {SPEC: f"domain: ADXX\n# {program}\n"},
             # 24 words: 13 runs of 12, the first in sorted order starting at "and".
             [f"{SPEC}: 13 run(s) of 12 words copied from a sponsor program or define, e.g. "
              "'and the invented visit is the first then set the invented analysis'"]),
            ("a program copied into an expression", {SPEC: f"domain: ADXX\nfilter: \"{program}\"\n"}, []),
        ]
        for label, files, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(self.errors(files, source), expected, label)


if __name__ == "__main__":
    unittest.main()
