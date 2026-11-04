from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

import test_four_week_gold as gold_fixtures
from test_unified_gold import reference
from winterops.operational_analytics import (calendar_hours, match_cached_weather, public_bundle,
                                            validate_products, validate_weather_join, weather_summary)
from winterops.operational_dashboard import pack, unpack, render_dashboard
from winterops.operational_sql import LocalGold, analytical_queries, weather_hourly_query
from winterops.unified_gold import load_selection
from winterops.unified_gold import UnifiedGold
from winterops.weather import WeatherContractError, canonical, digest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from weather_activity import demo, synthetic_inputs


class OperationalGoldTests(unittest.TestCase):
    def setUp(self):
        self.f = gold_fixtures.FourWeekGoldTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.local = LocalGold(self.f.plan)
        self.addCleanup(self.local.close)
        for scope, rows in zip(self.f.selected, self.f.rows):
            self.local.add_verified_scope(scope, rows)
        self.products = self.local.products()

    def test_all_gold_metrics_match_existing_independent_oracle(self):
        for product in ('hourly', 'daily', 'weekly'):
            expected = [r for scope, rows in zip(self.f.selected, self.f.rows) for r in reference(rows, scope)[product]]
            self.assertEqual(Counter(canonical(r) for r in self.products[product]), Counter(canonical(r) for r in expected))
        validate_products(self.products, self.f.plan)

    def test_cell_metrics_preserve_repeats_and_floor_negative_longitude(self):
        cell = next(r for r in self.products['cell_hour'] if r['source_local_naive_hour'] == '2026-01-05 00:00:00')
        self.assertEqual(cell['spatial_bin'], 'q25:169:-332')
        self.assertEqual(cell['repeated_valid_payload_observations'], 2)
        self.assertEqual(cell['both_active_observations'], 1)

    def test_distinct_identifiers_are_not_summed(self):
        week = self.products['weekly'][0]
        rows = [r for r in self.products['hourly'] if r['processing_key'] == week['processing_key']]
        self.assertLess(week['observed_identifier_count'], sum(r['observed_identifier_count'] for r in rows))

    def test_missing_telemetry_stays_null_in_complete_naive_calendar(self):
        calendar = calendar_hours(self.products, self.f.plan)
        self.assertEqual(len(calendar), 4*7*24)
        missing = [r for r in calendar if r['observation_count'] is None]
        self.assertTrue(missing)
        self.assertTrue(all(r['telemetry_status'] == 'MISSING_TELEMETRY_ACTIVITY_UNKNOWN' for r in missing))

    def test_duplicate_product_key_rejected(self):
        self.products['hourly'].append(deepcopy(self.products['hourly'][0]))
        with self.assertRaisesRegex(WeatherContractError, 'DUPLICATE_PRODUCT_KEY'):
            validate_products(self.products, self.f.plan)

    def test_equipment_overlap_corruption_rejected(self):
        self.products['cell_hour'][0]['both_active_observations'] += 1
        with self.assertRaisesRegex(WeatherContractError, 'EQUIPMENT_COMPOSITION'):
            validate_products(self.products, self.f.plan)

    def test_same_total_shifted_hours_rejected(self):
        rows = [r for r in self.products['cell_hour'] if r['plow_only_observations'] >= 2]
        for row, change in ((rows[0], 1), (rows[1], -1)):
            for k in ('observation_count', 'plow_active_observations', 'plow_only_observations'):
                row[k] += change
        with self.assertRaisesRegex(WeatherContractError, 'CELL_HOUR_RECONCILIATION'):
            validate_products(self.products, self.f.plan)

    def test_unselected_processing_or_quality_scope_rejected(self):
        self.products['daily'][0]['quality_policy_sha256'] = 'f'*64
        with self.assertRaisesRegex(WeatherContractError, 'PRODUCT_LINEAGE'):
            validate_products(self.products, self.f.plan)

    def test_partial_local_sources_do_not_pass_as_native_complete(self):
        other = LocalGold(self.f.plan)
        self.addCleanup(other.close)
        other.add_verified_scope(self.f.selected[0], self.f.rows[0])
        with self.assertRaisesRegex(WeatherContractError, 'SCOPE_INCOMPLETE'):
            other.products()

    def test_candidate_queries_reuse_frozen_unified_gold_and_remain_select_only(self):
        queries = analytical_queries(self.f.plan)
        for product in ('hourly', 'daily', 'weekly'):
            self.assertEqual(queries[product], self.f.plan.query(product))
        for sql in queries.values():
            self.assertTrue(sql.startswith('WITH '))
            for forbidden in ('CREATE ', 'INSERT ', 'UPDATE ', 'DELETE ', 'GRANT '):
                self.assertNotIn(forbidden, sql)
        actual = self.f.f.execute(queries['cell_hour'])
        self.assertEqual(Counter(canonical(r) for r in actual),
                         Counter(canonical(r) for r in self.products['cell_hour']))


class OperationalWeatherTests(unittest.TestCase):
    def setUp(self):
        self.demo = demo()
        self.matches = self.demo['matches']

    def test_weather_grid_hours_are_not_repeated_for_two_activity_bins(self):
        rows = weather_summary(self.matches)
        first = next(r for r in rows if r['source_local_hour'] == '2026-01-05 00:00:00' and r['timezone_hypothesis'] == 'America/Toronto')
        self.assertEqual(first['sampled_grid_hours'], 1)
        self.assertEqual(first['observation_count'], 10)
        self.assertEqual(first['precipitation_activity_hour_mm_mean'], self.matches[0]['precipitation_activity_hour_mm'])

    def test_independent_sql_weather_summary_matches_portable_python(self):
        db = sqlite3.connect(':memory:');self.addCleanup(db.close)
        cols = list(self.matches[0])
        db.execute('CREATE TABLE cell_weather (' + ','.join(cols) + ')')
        db.executemany('INSERT INTO cell_weather VALUES (' + ','.join('?' for _ in cols) + ')',
                       [[r[c] for c in cols] for r in self.matches])
        db.row_factory = sqlite3.Row
        actual = [dict(r) for r in db.execute(weather_hourly_query())]
        expected = {(r['processing_key'],r['source_local_hour'],r['timezone_hypothesis']): r for r in weather_summary(self.matches)}
        for row in actual:
            reference_row = expected[(row['processing_key'],row['source_local_hour'],row['timezone_hypothesis'])]
            for k,v in row.items():self.assertEqual(v,reference_row[k])

    def test_mixed_snapshots_and_conflicting_grid_facts_rejected(self):
        self.matches[0]['weather_snapshot_id'] = 'other'
        with self.assertRaisesRegex(WeatherContractError, 'SINGLE_WEATHER_SNAPSHOT'):
            weather_summary(self.matches)
        self.matches[0]['weather_snapshot_id'] = self.matches[1]['weather_snapshot_id']
        self.matches[0]['temperature_2m_c'] += 1
        with self.assertRaisesRegex(WeatherContractError, 'WEATHER_FACT_CONFLICT'):
            weather_summary(self.matches)

    def test_all_null_weather_has_no_invented_zero_mean(self):
        for row in self.matches:row['precipitation_antecedent_mm'] = None
        for row in weather_summary(self.matches):
            self.assertIsNone(row['precipitation_antecedent_mm_mean'])
            self.assertEqual(row['precipitation_antecedent_mm_present_samples'],0)

    def test_join_rejects_duplicate_missing_or_wrong_scope_matches(self):
        scope, _ = synthetic_inputs()
        plan = UnifiedGold((scope,))
        cells = [dict(r, source_local_naive_hour=r['source_local_hour']) for r in self.matches
                 if r['timezone_hypothesis']=='America/Toronto']
        products = dict(cell_hour=cells)
        snapshot = self.matches[0]['weather_snapshot_id']
        validate_weather_join(products,self.matches,plan,snapshot)
        for invalid in (self.matches+[self.matches[0]], self.matches[1:]):
            with self.assertRaises(WeatherContractError):validate_weather_join(products,invalid,plan,snapshot)
        self.matches[0]['source_version_id'] = 'f'*64
        with self.assertRaisesRegex(WeatherContractError,'JOIN_LINEAGE_OR_COUNT'):
            validate_weather_join(products,self.matches,plan,snapshot)


class PublicDashboardTests(unittest.TestCase):
    def setUp(self):
        self.bundle = unpack(json.loads((ROOT / 'dashboard/analytics.json').read_text()))

    def test_actual_snapshot_hash_and_expected_grains(self):
        expected = self.bundle.pop('content_sha256')
        self.assertEqual(digest(canonical(self.bundle)), expected)
        self.assertEqual(self.bundle['validation']['rows'],dict(hourly=325,daily=25,weekly=4,cell_hour=842))
        self.assertFalse(self.bundle['native_execution'])

    def test_public_snapshot_has_no_vehicle_or_cell_hour_detail(self):
        text = json.dumps(self.bundle)
        for key in ('truck_id','record_sha256','source_record_number','latitude','longitude','raw_record_json'):
            self.assertFalse('"'+key+'":' in text, 'Private field found: ' + key)
        self.assertNotIn('cell_weather',self.bundle)
        self.assertTrue(all('source_local_hour' not in r and 'source_local_naive_hour' not in r for r in self.bundle['cells']))
        self.assertEqual(sum(r['observation_count'] for r in self.bundle['cells']) +
                         sum(self.bundle['suppressed_map_observations'].values()),298051)

    def test_timezone_totals_reconcile_independently(self):
        for zone in ('America/Toronto','UTC'):
            self.assertEqual(sum(r['observation_count'] for r in self.bundle['weather_hourly'] if r['timezone_hypothesis']==zone),298051)
        self.assertEqual(sum(r['observation_count'] is None for r in self.bundle['calendar']),347)

    def test_renderer_is_self_contained_and_escapes_script_terminators(self):
        self.bundle['evidence'] = '</script><script>PRIVATE_SENTINEL</script>'
        html = render_dashboard(self.bundle)
        self.assertIn('\\u003c/script>',html)
        self.assertNotIn('<script>PRIVATE_SENTINEL',html)
        self.assertNotIn('https://cdn',html)
        self.assertEqual(unpack(pack(self.bundle)),self.bundle)

    def test_cli_public_replay_and_create_only_directory(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root)/'dashboard'
            command = [sys.executable,str(ROOT/'scripts/build_operational_dashboard.py'),'--output-root',str(out)]
            result = subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads((out/'execution.json').read_text())['detailed_spatial_validation'],'NOT_RERUN_WITHOUT_PRIVATE_INPUTS')
            self.assertEqual(json.loads((out/'analytics.json').read_text()),pack(self.bundle))
            self.assertEqual((out/'index.html').read_text(encoding='utf-8'),
                             (ROOT/'dashboard/index.html').read_text(encoding='utf-8'))
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,2)


if __name__ == '__main__':unittest.main()
