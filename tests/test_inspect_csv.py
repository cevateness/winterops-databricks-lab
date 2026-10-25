import sys
import unittest
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
from inspect_csv import inspect_csv


class CsvInspectionTests(unittest.TestCase):
    def test_synthetic_fixture_has_valid_header_and_no_bad_width(self):
        path = REPO / 'data' / 'synthetic' / 'snowplow_demo_synthetic.csv'
        result = inspect_csv(path, sample_limit=2)
        self.assertEqual(result['malformed_row_count'], 0)
        self.assertEqual(result['duplicate_headers'], [])
        self.assertEqual(result['empty_header_positions_0_based'], [])
        self.assertTrue(result['rows'] >= 5)
        self.assertEqual(len(result['examples']), 2)
        self.assertEqual(len(result['sha256']), 64)

    def test_header_and_bad_column_width_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            f = Path(directory) / 'bad.csv'
            f.write_text('a,a,b\n1,2\n3,4,5\n', encoding='utf-8')
            report = inspect_csv(f, sample_limit=0)
            self.assertEqual(report['rows'], 2)
            self.assertEqual(report['duplicate_headers'], ['a'])
            self.assertEqual(report['malformed_row_count'], 1)
            self.assertEqual(report['examples'], [])

    def test_blank_file_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            f = Path(directory) / 'empty.csv'
            f.write_text('', encoding='utf-8')
            with self.assertRaises(ValueError):
                inspect_csv(f)


if __name__ == '__main__':
    unittest.main()
