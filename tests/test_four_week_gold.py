"""Four-source differential and isolated-publication tests; synthetic records only."""
from collections import Counter
from dataclasses import asdict, replace
import csv
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest

import test_unified_gold as fixtures
from winterops.foundation import QualityPolicy, SOURCE_COLUMNS, read_bronze, silver_rows
from winterops.landing import OriginalLanding
from winterops.sources import LocalStager, WeeklySource
from winterops.spark_ingestion import BRONZE_TYPES, SILVER_TYPES, MANIFEST_TYPES
from winterops.unified_gold import SelectedVersion, UnifiedGold, load_selection

PREFIX = 'winterops_v2_gold_20260105_20260201_v1'
ROOT = Path(__file__).resolve().parents[1]


def bag(rows):
    return Counter(json.dumps(row, sort_keys=True) for row in rows)


class FourWeekGoldTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.UnifiedGoldTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        day = '2026-01-26'
        base = ['42.3', '-83', day + ' 00:00:00', 'True', 'False', 'True', 'SYN-A']
        rows = [base, base, base[:2] + [day + ' 00:00:00.500001', 'True', 'True', 'True', 'SYN-A'],
                base[:2] + [day + ' 01:00:00', 'False', 'True', 'False', 'SYN-B'],
                base[:2] + ['2026-01-27 00:00:00', 'False', 'False', 'True', 'SYN-C'],
                list(SOURCE_COLUMNS), ['91', '-83', day + ' 00:00:00', 'True', 'False', 'True', 'SYN-A']]
        path = self.f.root / 'fourth.csv'
        with path.open('w', encoding='utf-8', newline='') as out:
            writer = csv.writer(out); writer.writerow(SOURCE_COLUMNS); writer.writerows(rows)
        source = WeeklySource.from_url('https://opendata.citywindsor.ca/Uploads/snowplow-2026-01-26_2026-02-01.csv')
        version = LocalStager(self.f.root / 'stage').adopt(source, path)[0]
        bronze = list(read_bronze(version)); silver = silver_rows(bronze, version)
        self.fourth = SelectedVersion.from_version(version, len(rows), OriginalLanding(source, version.source_file_sha256, version.byte_count))
        self.f.insert('bronze', BRONZE_TYPES, bronze); self.f.insert('silver', SILVER_TYPES, silver)
        self.f.insert('manifest', MANIFEST_TYPES, [dict(processing_key=self.fourth.processing_key,
            source_version_id=version.version_id, source_file_name=source.source_file_name,
            source_file_sha256=version.source_file_sha256, metadata_json=json.dumps(version.to_dict()),
            policy_json=json.dumps(asdict(QualityPolicy())), status='COMPLETE', last_successful_stage='COMPLETE',
            attempts=1, bronze_rows=len(rows), silver_rows=len(rows), error_code=None, updated_at_utc='2026-02-02 00:00:00')])
        self.rows = [*self.f.typed, silver]
        self.selected = (*self.f.selections, self.fourth)
        self.plan = UnifiedGold(self.selected, view_prefix=PREFIX)

    def test_four_candidates_match_full_independent_multisets_and_hierarchy(self):
        before = self.f.db.total_changes
        self.f.execute(self.plan.selection_guard()); self.f.execute(self.plan.reconcile())
        for product in ('hourly', 'daily', 'weekly'):
            expected = [row for typed, selected in zip(self.rows, self.selected)
                        for row in fixtures.reference(typed, selected)[product]]
            self.assertEqual(bag(self.f.execute(self.plan.query(product))), bag(expected))
        self.assertEqual(self.f.db.total_changes, before)

    def test_versioned_publication_preserves_existing_three_week_products(self):
        self.f.publish()
        old = {p: self.f.execute('SELECT * FROM ' + self.f.plan.view_name(p)) for p in ('hourly', 'daily', 'weekly')}
        self.f.plan = self.plan; self.f.publish()
        for product in old:
            self.f.execute(self.plan.published_comparison(product))
            old_name = UnifiedGold(self.selected[:3]).view_name(product)
            self.assertEqual(bag(self.f.execute('SELECT * FROM ' + old_name)), bag(old[product]))
            subset = [r for r in self.f.execute(self.plan.query(product)) if r['processing_key'] != self.fourth.processing_key]
            self.assertEqual(bag(subset), bag(old[product]))

    def test_incomplete_fourth_week_cannot_return_partial_products(self):
        self.f.db.execute('UPDATE winterops_v2_dev_manifest SET status=? WHERE processing_key=?',
                          ('PROCESSING', self.fourth.processing_key))
        for sql in (self.plan.selection_guard(), self.plan.reconcile(),
                    *(self.plan.query(p) for p in ('hourly', 'daily', 'weekly'))):
            with self.assertRaises(sqlite3.OperationalError): self.f.execute(sql)

    def test_fourth_week_multiplicity_corruption_is_rejected(self):
        self.f.db.execute('UPDATE winterops_v2_dev_silver SET payload_occurrences=99 WHERE processing_key=?',
                          (self.fourth.processing_key,))
        with self.assertRaises(sqlite3.OperationalError): self.f.execute(self.plan.selection_guard())

    def test_prefix_changes_only_destination_contract_not_candidate_metrics(self):
        default = UnifiedGold(self.selected)
        for product in ('hourly', 'daily', 'weekly'):
            self.assertEqual(default.query(product), self.plan.query(product))
            self.assertNotEqual(default.view_name(product), self.plan.view_name(product))
            ddl = self.plan.publication()[('hourly', 'daily', 'weekly').index(product)]
            self.assertTrue(ddl.startswith('CREATE VIEW workspace.default.' + PREFIX + '_'))
            self.assertNotIn('OR REPLACE', ddl); self.assertNotIn('IF NOT EXISTS', ddl)
        for prefix in (None, False, '', 'Upper', 'a.b', '../x', 'x;DROP', 'x-' , 'x' * 81):
            with self.subTest(prefix=prefix), self.assertRaises(ValueError): replace(self.plan, view_prefix=prefix)

    def test_full_published_comparison_rejects_same_count_corruption(self):
        self.f.plan = self.plan; self.f.publish()
        for product in ('hourly', 'daily', 'weekly'):
            self.f.db.execute('SAVEPOINT clean')
            self.f.db.execute('UPDATE ' + self.plan.view_name(product).split('.')[-1] + ' SET observation_count=observation_count+1 WHERE rowid=1')
            with self.assertRaises(sqlite3.OperationalError): self.f.execute(self.plan.published_comparison(product))
            self.f.db.execute('ROLLBACK TO clean'); self.f.db.execute('RELEASE clean')

    def test_checked_in_selection_extends_the_verified_three_week_scope_exactly(self):
        old = json.loads((ROOT / 'docs/THREE_WEEK_SELECTION.json').read_text())
        new = json.loads((ROOT / 'docs/FOUR_WEEK_SELECTION.json').read_text())
        self.assertEqual(new['selected'][:3], old['selected'])
        plan = load_selection(ROOT / 'docs/FOUR_WEEK_SELECTION.json')
        native = json.loads((ROOT / 'docs/INCREMENTAL_INGESTION_FILES_ABSENCE_RESULTS.json').read_text())
        scope = native['source_reconciliation']; fourth = plan.selected[-1]
        self.assertEqual((fourth.source_version_id, fourth.processing_key, fourth.source_file_sha256, fourth.expected_rows),
                         (scope['source_version_id'], scope['processing_key'], scope['csv_sha256'], scope['bronze_rows']))
        self.assertEqual(fourth.policy, plan.selected[0].policy)
        self.assertEqual(plan.view_prefix, PREFIX)
        self.assertNotIn('three_week_comparison', plan.dashboard())

    def test_existing_cli_loads_versioned_selection_and_renders_only_new_creates(self):
        selection = self.f.root / 'selection.json'; output = self.f.root / 'publication.sql'
        selection.write_text(json.dumps(dict(selected=[asdict(s) for s in self.selected], view_prefix=PREFIX)))
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/render_unified_gold.py'),
            '--selection', str(selection), '--publication', '--output', str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        sql = output.read_text(encoding='utf-8')
        self.assertEqual(sql.count('CREATE VIEW workspace.default.' + PREFIX + '_'), 3)
        self.assertIn('source_week_comparison', sql)
        self.assertNotIn('CREATE VIEW workspace.default.winterops_v2_gold_hourly_observations', sql)


if __name__ == '__main__': unittest.main()
