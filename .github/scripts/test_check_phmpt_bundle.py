"""The PHMPT publication gate, one rule per case, on invented bundles.

Seam: check_bundle.check() over a folder of files; every identifier, program
line and value below is invented. The same file runs in Pilot 7 next to the
vendored gate (.github/scripts/check_phmpt_bundle.py).
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_name = next(n for n in ("check_bundle", "check_phmpt_bundle") if (HERE / f"{n}.py").exists())
_spec = importlib.util.spec_from_file_location(_name, HERE / f"{_name}.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

EVIDENCE = {"schema_version": 1, "meta": {"yamaa_commit": "abc1234", "source_commit": "def5678", "collected": "2026-01-01"},
            "gaps": {}, "studies": {}, "findings": []}
SPEC = "phmpt/bnt162-01/27034/spec/yamaa/adxx.yaml"


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
                                ("index", "coverage", "glossary", "reproduce", "findings/bnt162-01")}, []),
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
            ("a subject identifier pattern", {SPEC: "domain: ADXX\n# subject BNT162-01-999-99-9999\n"},
             [f"{SPEC}:2: a subject identifier pattern"]),
        ]
        for label, files, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(self.errors(files), expected, label)

    def test_source_backed_rules_report_ids_and_copied_text(self):
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest("pyarrow is not installed: the --source checks run only in yamaa_phmpt")
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
