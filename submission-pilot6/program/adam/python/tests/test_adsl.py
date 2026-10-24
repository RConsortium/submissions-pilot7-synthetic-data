"""Clinical boundary cases from production adsl.r; no official-data claim."""

from datetime import date
from pathlib import Path
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq
import yaml
import yamaa

STUDY = Path(__file__).resolve().parents[4]


class ExposureTests(unittest.TestCase):
    def test_qualifying_doses_and_partial_dates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = yaml.safe_load((STUDY / 'spec/yamaa/adsl.yaml').read_text())
            # Use the actual specification with independently authored source cases.
            for key, value in spec['input'].items():
                if isinstance(value, str):
                    spec['input'][key] = str((STUDY / 'spec/yamaa' / value).resolve())
                else:
                    value['path'] = str((STUDY / 'spec/yamaa' / value['path']).resolve())
            subjects = ['A', 'P', 'D', 'C', 'M']
            dm = [{'STUDYID': 'TEST', 'USUBJID': s, 'ACTARMCD': 'ACTIVE',
                   'RFENDTC': '2025-05'} for s in subjects]
            ds = [{'STUDYID': 'TEST', 'USUBJID': s, 'DSCAT': 'DISPOSITION EVENT',
                   'DSDECOD': 'ADVERSE EVENT' if s in ('D', 'C') else 'COMPLETED',
                   'DSSTDTC': '2025-05-20', 'DSTERM': 'ADVERSE EVENT'} for s in subjects]
            ds[0]['DSTERM'] = 'PROTOCOL ENTRY CRITERIA NOT MET'
            ds[2]['DSTERM'] = 'OTHER'
            sv = [{'STUDYID': 'TEST', 'USUBJID': 'A', 'VISITNUM': 1.,
                   'SVSTDTC': '2025-01'}]
            qs = [{'STUDYID': 'TEST', 'USUBJID': 'A', 'QSCAT': 'MINI-MENTAL STATE',
                   'QSORRES': '2', 'QSSTRESN': 999.}]
            rows = [('A', 1, 0., 'ACTIVE', '2025-01-01', '2025-01-02'),
                    ('A', 2, 10., 'ACTIVE', '2025-05-01', '2025-05-03'),
                    ('A', 3, 0., 'ACTIVE', '2025-12-01', '2025-12-31'),
                    ('P', 1, 0., 'MATCHED PLACEBO', '2025-01-02', '2025'),
                    ('D', 1, 2., 'ACTIVE', '2025-05-01', '2025-05'),
                    ('C', 1, 2., 'ACTIVE', '2025-05-01', '2025-05-25'),
                    ('M', 1, 2., 'ACTIVE', '2025-05', '2025-05-31')]
            ex = [dict(zip(('USUBJID', 'EXSEQ', 'EXDOSE', 'EXTRT', 'EXSTDTC', 'EXENDTC'), row), STUDYID='TEST') for row in rows]
            for name, data in [('DM', dm), ('DS', ds), ('EX', ex), ('SV', sv), ('QS', qs)]:
                path = root / f'{name}.parquet'
                pq.write_table(pa.Table.from_pylist(data), path)
                if isinstance(spec['input'][name], str):
                    spec['input'][name] = str(path)
                else:
                    spec['input'][name]['path'] = str(path)
            spec['output']['columns'] = ['STUDYID', 'USUBJID', 'TRTSDT', 'TRTEDT', 'CUMDOSE',
                                        'DISCONFL', 'DSRAEFL', 'DCSREAS', 'VISIT1DT', 'RFENDT', 'MMSETOT']
            spec['output']['path'] = str(root / 'output.parquet')
            (root / 'adsl.yaml').write_text(yaml.safe_dump(spec, sort_keys=False))
            (root / 'project.yaml').write_text('yamaa: "1.0"\ntype: project\nadam:\n  specs: [adsl.yaml]\n')
            run = yamaa.project(root / 'project.yaml').run('adam')
            self.assertEqual(run.status, 'succeeded', run.issues.to_pylist())
            actual = {r['USUBJID']: (r['TRTSDT'], r['TRTEDT'], r['CUMDOSE']) for r in run['ADSL'].output.to_pylist()}
            self.assertEqual(actual, {
                'A': (date(2025, 5, 1), date(2025, 5, 3), 30.),
                'P': (date(2025, 1, 2), date(2025, 12, 31), 0.),
                'D': (date(2025, 5, 1), date(2025, 5, 20), 40.),
                'C': (date(2025, 5, 1), date(2025, 5, 25), 50.),
                'M': (None, date(2025, 5, 31), None),
            })
            records = {r['USUBJID']: r for r in run['ADSL'].output.to_pylist()}
            self.assertIn(records['A']['DCSREAS'], ('', None))
            self.assertIsNone(records['A']['VISIT1DT'])
            self.assertIsNone(records['A']['RFENDT'])
            self.assertEqual(records['A']['MMSETOT'], 2.)
            self.assertEqual(records['D']['DISCONFL'], 'Y')
            self.assertIsNone(records['D']['DSRAEFL'])
            self.assertEqual(records['C']['DSRAEFL'], 'Y')


if __name__ == '__main__':
    unittest.main()
