"""Offline checks of Lesson 4 artifact; does NOT test Spark/Databricks execution."""
from pathlib import Path
import ast
import csv
import hashlib
import unittest

ROOT = Path(__file__).resolve().parents[1]

class RealBronzeContractTests(unittest.TestCase):
    def test_notebook_syntax(self):
        code = (ROOT / 'notebooks' / '04_bronze_real_ingestion.py').read_text(encoding='utf-8')
        ast.parse(code)
        self.assertIn('replaceWhere', code)
        self.assertIn('winterops_bronze_windsor_activity', code)
        self.assertIn('raw.select(payload.alias("raw_record_json"))', code)
        self.assertNotIn('.groupBy("raw_record_json").count()', code)

    def test_sample_has_distinct_rows_and_duplicate_multiplicity(self):
        demo = ROOT / 'data' / 'synthetic' / 'snowplow_demo_synthetic.csv'
        with demo.open(newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 13)
        identities = [tuple(sorted(r.items())) for r in rows]
        self.assertEqual(len(set(identities)), 12)
        self.assertEqual(len(rows) - len(set(identities)), 1)
        self.assertEqual(len(hashlib.sha256(demo.read_bytes()).hexdigest()), 64)

if __name__ == '__main__':
    unittest.main()
