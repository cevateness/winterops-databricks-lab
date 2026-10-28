"""Independent expected metrics on entirely synthetic observations."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
import random
import subprocess
import sys
import unittest

from gold_products_fixture import ROOT, fixture
from winterops.analytics import SILVER_TYPES
from winterops.gold_products import (DiagnosticSettings, GOLD_TYPES, PRODUCT_NAMES, build_products,
                                     reference_products, validate_product_schemas)


class GoldProductsReferenceTests(unittest.TestCase):
    def setUp(self):
        self.config, self.rows = fixture()
        self.settings = DiagnosticSettings(1800, 2)
        self.results = reference_products(self.rows, self.config.scope, self.settings)

    def test_daily_grain_and_peak_are_not_summed_trucks(self):
        self.assertEqual(self.results['daily_activity'], [
            dict(source_local_naive_day='2026-01-12', observation_count=9, plow_active_observations=5,
                 spreader_active_observations=2, hours_containing_telemetry=3, maximum_hourly_distinct_truck_identifiers=2),
            dict(source_local_naive_day='2026-01-13', observation_count=3, plow_active_observations=1,
                 spreader_active_observations=2, hours_containing_telemetry=2, maximum_hourly_distinct_truck_identifiers=2),
            dict(source_local_naive_day='2026-01-14', observation_count=3, plow_active_observations=1,
                 spreader_active_observations=1, hours_containing_telemetry=1, maximum_hourly_distinct_truck_identifiers=2)])
        self.assertEqual(sum(row['observation_count'] for row in self.results['daily_activity']), 15)
        self.assertEqual(sum(row['hours_containing_telemetry'] for row in self.results['daily_activity']), 6)
        self.assertEqual(self.results['fleet_daily_participation'][0]['observed_identifier_count'], 3)
        self.assertEqual(self.results['fleet_overview'][0]['observed_identifier_count'], 6)

    def test_composition_is_exhaustive_and_engine_flags_overlap_only_as_diagnostics(self):
        categories = ('plow_only_observations', 'spreader_only_observations', 'both_active_observations', 'neither_active_observations')
        for product in ('equipment_hourly', 'equipment_daily'):
            rows = self.results[product]
            self.assertEqual([sum(row[name] for row in rows) for name in categories], [4, 2, 3, 6])
            self.assertEqual(sum(row['engine_off_observations'] for row in rows), 4)
            self.assertEqual(sum(row['engine_off_with_equipment_flag_observations'] for row in rows), 2)
            for row in rows:
                self.assertEqual(sum(row[name] for name in categories), row['observation_count'])

    def test_fleet_duplicate_gap_conflict_and_density_diagnostics(self):
        overview = self.results['fleet_overview'][0]
        expected = dict(observed_identifier_count=6, observation_count=15, observed_identifier_day_pairs=8,
            minimum_observations_per_identifier=1, maximum_observations_per_identifier=6,
            mean_observations_per_identifier=2.5, singleton_identifier_count=2,
            constant_timestamp_identifier_count=1, same_timestamp_conflict_identifier_count=2,
            conflicting_identifier_timestamp_groups=2, identifiers_with_long_gaps=1,
            consecutive_timestamp_pairs=9, zero_gap_pairs=4, long_gap_pairs=2,
            minimum_positive_source_clock_gap_seconds=0.5, maximum_source_clock_gap_seconds=54000.0,
            dense_reporting_identifier_count=2, dense_identifier_hour_count=2,
            peak_identifier_hour_observation_count=4, repeated_payload_group_count=2,
            repeated_payload_observations=4, excess_payload_observations=2,
            payload_identity_conflict_groups=0, whitespace_identifier_observations=1)
        self.assertEqual(overview, expected)

    def test_gap_histogram_preserves_ties_and_microseconds_across_midnight(self):
        gaps = self.results['fleet_gap_distribution']
        self.assertEqual([row['consecutive_timestamp_pairs'] for row in gaps], [4, 3, 2])
        self.assertEqual([row['identifiers_in_band'] for row in gaps], [3, 3, 1])
        self.assertEqual(gaps[1]['minimum_source_clock_gap_seconds'], 0.5)
        # The cross-midnight 0.500001-second pair stays positive, not a zero-second tie.
        selected = [row for row in self.rows if row['truck_id'] == 'SYN-D']
        pair = reference_products(selected, self.config.scope)['fleet_gap_distribution'][0]
        self.assertAlmostEqual(pair['minimum_source_clock_gap_seconds'], 0.500001)
        self.assertEqual(pair['consecutive_timestamp_pairs'], 1)

    def test_frequency_and_participation_histograms_reconcile_without_fleet_denominator(self):
        self.assertEqual(self.results['fleet_observation_frequency'], [
            dict(frequency_band='01_single', identifier_count=2, observation_count=2),
            dict(frequency_band='02_2_to_10', identifier_count=4, observation_count=13)])
        self.assertEqual(self.results['fleet_reporting_days'], [
            dict(days_with_observations=1, identifier_count=4, observation_count=7),
            dict(days_with_observations=2, identifier_count=2, observation_count=8)])
        # IDs in gap bands overlap. Summing those counts is not the weekly distinct count.
        self.assertNotEqual(sum(row['identifiers_in_band'] for row in self.results['fleet_gap_distribution']), 6)

    def test_order_independence_and_no_input_mutation(self):
        original = deepcopy(self.rows)
        random.Random(42).shuffle(self.rows)
        self.assertEqual(reference_products(self.rows, self.config.scope, self.settings), self.results)
        self.assertEqual(sorted(self.rows, key=lambda row: json.dumps(row, sort_keys=True)),
                         sorted(original, key=lambda row: json.dumps(row, sort_keys=True)))

    def test_cross_identifier_payload_reuse_is_reported_without_returning_hashes(self):
        rows = deepcopy(self.rows)
        for index in (9, 14):
            rows[index]['record_sha256'] = 'f' * 64
        frequencies = Counter(row['record_sha256'] for row in rows)
        for row in rows:
            row.update(payload_occurrences=frequencies[row['record_sha256']],
                       has_repeated_payload=frequencies[row['record_sha256']] > 1)
        self.assertEqual(reference_products(rows, self.config.scope)['fleet_overview'][0]['payload_identity_conflict_groups'], 1)

    def test_foreign_version_is_filtered_but_selected_bad_time_or_flags_fail(self):
        foreign = dict(self.rows[0], source_file_sha256='b' * 64)
        self.assertEqual(reference_products([*self.rows, foreign], self.config.scope, self.settings), self.results)
        for changes in ({'event_time_unzoned': '2026-01-19 00:00:00'},
                        {'event_time_unzoned': datetime(2026, 1, 12, tzinfo=timezone.utc)},
                        {'engine_active': 0}, {'quality_status': 'HEADER'}, {'payload_occurrences': 99}):
            rows = deepcopy(self.rows)
            rows[0].update(changes)
            with self.subTest(changes=list(changes)), self.assertRaises(ValueError):
                reference_products(rows, self.config.scope)

    def test_public_outputs_have_no_identifier_or_trajectory_fields(self):
        self.assertEqual(tuple(self.results), PRODUCT_NAMES)
        forbidden = {'truck_id', 'record_sha256', 'latitude', 'longitude', 'event_time_unzoned', 'source_file_path'}
        for rows in self.results.values():
            for row in rows:
                self.assertFalse(forbidden.intersection(row))
        serialized = json.dumps(self.results)
        self.assertNotIn('SYN-', serialized)
        self.assertNotIn(self.rows[0]['record_sha256'], serialized)

    def test_empty_reference_has_no_invented_calendar_or_gaps(self):
        result = reference_products([], self.config.scope)
        self.assertEqual(result['daily_activity'], [])
        self.assertEqual(result['fleet_gap_distribution'], [])
        self.assertEqual(result['fleet_overview'][0]['observed_identifier_count'], 0)
        self.assertIsNone(result['fleet_overview'][0]['maximum_source_clock_gap_seconds'])

    def test_thresholds_are_strictly_typed_bounded_review_parameters(self):
        for args in ((True, 2), (0, 2), (604801, 2), (1, False), (1, 0)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                DiagnosticSettings(*args)
        plan = build_products(self.config, self.settings)
        self.assertEqual(tuple(name for name, _ in plan.queries), PRODUCT_NAMES)
        with self.assertRaises(ValueError):
            plan.query('unreviewed')

    def test_offline_cli_renders_one_product_with_guards_and_no_ddl(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/render_gold_products.py'),
            '--source-file-sha256', 'a' * 64, '--expected-summary',
            str(ROOT / 'data/fixtures/windsor_week_2026_01_12_18_summary.json'),
            '--product', 'daily_activity'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('source_version_check', result.stdout)
        self.assertIn('maximum_hourly_distinct_truck_identifiers', result.stdout)
        for token in ('CREATE VIEW', 'CREATE OR REPLACE', 'INSERT INTO', 'to_utc_timestamp', 'unix_timestamp', 'timestampdiff'):
            self.assertNotIn(token, result.stdout)

    def test_runtime_schema_gate_rejects_instant_hours_or_missing_status_types(self):
        validate_product_schemas(dict(SILVER_TYPES), dict(GOLD_TYPES))
        with self.assertRaises(ValueError):
            validate_product_schemas(dict(SILVER_TYPES), dict(GOLD_TYPES, source_local_naive_hour='timestamp'))
        with self.assertRaises(ValueError):
            validate_product_schemas(dict(SILVER_TYPES, engine_active='string'), dict(GOLD_TYPES))


if __name__ == '__main__':
    unittest.main()
