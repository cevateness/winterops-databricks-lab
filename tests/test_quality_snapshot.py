"""Portable unit tests: do not contact Databricks."""
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from winterops.quality import QualitySnapshot, validate_snapshot


class AggregateSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = json.loads(
            (ROOT / "data" / "fixtures" / "windsor_week_2026_01_12_18_summary.json")
            .read_text(encoding="utf-8")
        )
        cls.snapshot = QualitySnapshot.from_mapping(data)

    def test_reconciles_user_reported_counts(self):
        self.assertEqual(validate_snapshot(self.snapshot), [])

    def test_detects_missing_classification(self):
        self.assertTrue(validate_snapshot(replace(self.snapshot, header_rows=25)))

    def test_detects_bronze_silver_mismatch(self):
        self.assertTrue(validate_snapshot(replace(self.snapshot, bronze_rows=110338)))

    def test_rejects_nonsense_activity_counts(self):
        self.assertTrue(validate_snapshot(replace(self.snapshot, plow_active_observations=120000)))

    def test_rejects_boolean_number(self):
        with self.assertRaises(TypeError):
            QualitySnapshot.from_mapping(dict(
                source_file="demo.csv", bronze_rows=True, silver_rows=0,
                header_rows=0, valid_rows=0, other_invalid_rows=0,
                distinct_truck_ids=0, plow_active_observations=0,
                spreader_active_observations=0
            ))


if __name__ == "__main__":
    unittest.main()
