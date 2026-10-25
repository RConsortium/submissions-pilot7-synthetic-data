"""Authored window and LOCF cases for the complete questionnaire specs."""

from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq
import yaml
import yamaa

STUDY = Path(__file__).resolve().parents[3]
START = date(2020, 1, 1)


def observation(day, score, sequence, test="ACTOT", baseline=False):
    return {
        "STUDYID": "TEST", "USUBJID": "S1", "QSSEQ": float(sequence),
        "QSTESTCD": test, "QSSTRESN": float(score),
        "QSBLFL": "Y" if baseline else "",
        "QSDTC": (START + timedelta(days=day - 1)).isoformat(),
        "VISIT": f"Day {day}", "VISITNUM": float(sequence),
    }


class QuestionnaireTests(unittest.TestCase):
    def derive(self, domain, observations, columns):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            subject = {
                "STUDYID": "TEST", "USUBJID": "S1", "SITEID": "001",
                "SITEGR1": "001", "TRTSDT": START, "TRTEDT": date(2020, 12, 31),
                "TRT01P": "Placebo", "TRT01PN": 0.0, "AGE": 70.0,
                "AGEGR1": "65-80", "AGEGR1N": 2.0, "RACE": "WHITE",
                "RACEN": 1.0, "SEX": "F", "ITTFL": "Y", "EFFFL": "Y",
                "COMP24FL": "Y",
            }
            pq.write_table(pa.Table.from_pylist([subject]), work / "adsl.parquet")
            pq.write_table(pa.Table.from_pylist(observations), work / "qs.parquet")
            spec = yaml.safe_load((STUDY / "spec/yamaa" / f"{domain}.yaml").read_text())
            spec["input"]["QS"]["path"] = str(work / "qs.parquet")
            spec["input"]["ADSL"]["path"] = str(work / "adsl.parquet")
            spec["input"]["ADSL"].pop("schema")
            spec["output"]["path"] = str(work / "output.parquet")
            path = work / "spec.yaml"
            path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="ascii")
            run = yamaa.spec(path).run()
            self.assertEqual(run.status, "succeeded", run.issues.to_pylist())
            run.save()
            records = pq.read_table(work / "output.parquet", columns=columns).to_pylist()
            return [tuple(record[c] for c in columns) for record in records]

    def test_adas_carries_selected_score_and_marks_only_changed_observations(self):
        rows = [observation(1, 9, 1, baseline=True), observation(50, 10, 2),
                observation(83, 99, 3), observation(84, 10, 4)]
        columns = ["AVISITN", "QSSEQ", "AVAL", "ANL01FL", "DTYPE", "ADY", "BASE", "CHG"]
        self.assertEqual(self.derive("adqsadas", rows, columns), [
            (0, 1, 9, "Y", "", 1, 9, None),
            (8, 2, 10, "Y", "", 50, 9, 1),
            (8, 3, 10, "", "LOCF", 83, 9, 1),
            (8, 4, 10, "", "", 84, 9, 1),
            (16, 4, 10, "Y", "LOCF", 84, 9, 1),
            (24, 4, 10, "Y", "LOCF", 84, 9, 1),
        ])

    def test_adas_window_boundaries_keep_item_observations(self):
        rows = [observation(day, i, i, test="ACITM01", baseline=i == 1)
                for i, day in enumerate([1, 2, 84, 85, 140, 141], start=1)]
        columns = ["AVISITN", "AVAL", "ANL01FL", "DTYPE", "BASE", "CHG"]
        self.assertEqual(self.derive("adqsadas", rows, columns), [
            (0, 1, "Y", "", 1, None), (8, 2, "", "", 1, 1),
            (8, 3, "Y", "", 1, 2), (16, 4, "Y", "", 1, 3),
            (16, 5, "", "", 1, 4), (24, 6, "Y", "", 1, 5),
        ])

    def test_adas_zero_baseline_has_no_percent_change(self):
        rows = [observation(1, 0, 1, baseline=True), observation(56, 5, 2)]
        self.assertEqual(self.derive("adqsadas", rows, ["AVISITN", "CHG", "PCHG"]), [
            (0, None, None), (8, 5, None), (16, 5, None), (24, 5, None),
        ])

    def test_cibic_locf_combines_selected_score_with_latest_record_metadata(self):
        rows = [observation(50, 3, 1, test="CIBIC"), observation(83, 7, 2, test="CIBIC")]
        columns = ["AVISITN", "QSSEQ", "AVAL", "ANL01FL", "DTYPE", "ADY"]
        self.assertEqual(self.derive("adqscibc", rows, columns), [
            (8, 1, 3, "Y", "", 50), (8, 2, 7, "", "", 83),
            (16, 2, 3, "Y", "LOCF", 83), (24, 2, 3, "Y", "LOCF", 83),
        ])

    def test_cibic_tie_selects_later_day_and_leaves_earlier_visit_unfilled(self):
        rows = [observation(100, 3, 1, test="CIBIC"), observation(124, 4, 2, test="CIBIC")]
        columns = ["AVISITN", "QSSEQ", "AVAL", "ANL01FL", "DTYPE", "ADY"]
        self.assertEqual(self.derive("adqscibc", rows, columns), [
            (16, 1, 3, "", "", 100), (16, 2, 4, "Y", "", 124),
            (24, 2, 4, "Y", "LOCF", 124),
        ])

    def test_cibic_window_boundaries_keep_all_observations(self):
        rows = [observation(day, i, i, test="CIBIC")
                for i, day in enumerate([2, 84, 85, 140, 141], start=1)]
        columns = ["AVISITN", "AVAL", "ANL01FL", "DTYPE"]
        self.assertEqual(self.derive("adqscibc", rows, columns), [
            (8, 1, "", ""), (8, 2, "Y", ""), (16, 3, "Y", ""),
            (16, 4, "", ""), (24, 5, "Y", ""),
        ])


if __name__ == "__main__":
    unittest.main()
