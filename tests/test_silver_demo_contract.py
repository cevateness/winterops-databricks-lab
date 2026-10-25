import csv
from collections import Counter
from datetime import datetime
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
SAMPLE = REPO / "data" / "synthetic" / "snowplow_demo_synthetic.csv"
NOTEBOOK = REPO / "notebooks" / "02_silver_typing.py"


class SilverDemoContractTests(unittest.TestCase):
    """Source-level expectations only; these tests do NOT execute Spark."""

    @classmethod
    def setUpClass(cls):
        with SAMPLE.open(newline="", encoding="utf-8-sig") as stream:
            cls.rows = list(csv.DictReader(stream))

    def test_row_and_vehicle_counts(self):
        self.assertEqual(len(self.rows), 13)
        self.assertEqual(len({tuple(sorted(r.items())) for r in self.rows}), 12)
        self.assertEqual(Counter(r["Vehicle_ID"] for r in self.rows), {
            "SYN-001": 5, "SYN-002": 4, "SYN-003": 4,
        })

    def test_source_fields_are_convertible(self):
        for row in self.rows:
            self.assertLessEqual(abs(float(row["Latitude"])), 90)
            self.assertLessEqual(abs(float(row["Longitude"])), 180)
            datetime.strptime(row["Date_Time"], "%Y-%m-%d %H:%M:%S")
            for key in ("Is_Plow_Status", "Is_Spreader_Status", "Is_Engine_Status"):
                self.assertIn(row[key], {"TRUE", "FALSE"})
            self.assertTrue(row["Vehicle_ID"].strip())

    def test_notebook_is_synthetic_only_and_compiles(self):
        source = NOTEBOOK.read_text(encoding="utf-8")
        compile(source, str(NOTEBOOK), "exec")
        self.assertIn('SOURCE_DATASET = "winterops_demo_synthetic"', source)
        self.assertIn('winterops_silver_demo_snowplow', source)
        self.assertIn('TIMESTAMP_NTZ', source)
        self.assertIn('len(file_versions) != 1', source)


if __name__ == "__main__":
    unittest.main()
