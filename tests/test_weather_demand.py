"""Synthetic private-Silver spatial/time contract; no native data or network."""
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from email.message import Message
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from weather_activity import demo, synthetic_inputs, synthetic_snapshots
from winterops.weather import WeatherContractError, WeatherRequest, acquire_snapshot, canonical, digest
from winterops.weather_demand import (DemandPlan, acquire_demand, aggregate_activity,
                                     matched_projection, weather_catalog)


class ActivityDemandTests(unittest.TestCase):
    def setUp(self):
        self.scope, self.raw = synthetic_inputs()
        self.hours, self.audit = aggregate_activity(self.raw, [self.scope])
        self.plan = DemandPlan(self.hours)

    def test_valid_private_silver_becomes_coarse_hour_counts_preserving_observations(self):
        self.assertEqual(len(self.hours), 3)
        self.assertEqual(sum(a.observation_count for a in self.hours), 15)
        self.assertEqual(self.audit['retained_observations'], 15)
        self.assertEqual(len({a.spatial_bin for a in self.hours}), 2)
        self.assertEqual({a.representative_longitude for a in self.hours}, {-83.125})

    def test_quality_and_broad_geometric_exclusions_are_audited_not_weather_demand(self):
        rows = deepcopy(self.raw)
        rows.extend([dict(rows[0], source_record_number=16, quality_status='HEADER', latitude=None),
                     dict(rows[0], source_record_number=17, quality_status='INVALID', latitude=None),
                     dict(rows[0], source_record_number=18, latitude=41.0)])
        hours, audit = aggregate_activity(rows, [self.scope])
        self.assertEqual(hours, self.hours)
        self.assertEqual((audit['excluded_quality_rows'], audit['outside_review_rows']), (2, 1))
        self.assertEqual(audit['input_rows'], 18)

    def test_sparse_buckets_suppressed_before_demand(self):
        hours, audit = aggregate_activity(self.raw[:-1], [self.scope])
        self.assertEqual(len(hours), 2)
        self.assertEqual((audit['suppressed_observations'], audit['retained_observations']), (4, 10))

    def test_changed_policy_source_record_or_timezone_fails_before_requests(self):
        for change in (dict(quality_policy_sha256='other'), dict(processing_key='other'),
                       dict(source_file_sha256='other'), dict(source_record_number=True),
                       dict(latitude=True), dict(latitude=999), dict(event_time_unzoned='2026-01-05T00:00:00Z'),
                       dict(event_time_unzoned='2026-02-01 00:00:00')):
            rows = deepcopy(self.raw)
            rows[0].update(change)
            with self.subTest(change=change), self.assertRaises(WeatherContractError):
                aggregate_activity(rows, [self.scope])
        with self.assertRaisesRegex(WeatherContractError, 'DUPLICATE_SOURCE'):
            aggregate_activity(self.raw + [self.raw[0]], [self.scope])

    def test_same_payload_different_source_observations_are_preserved(self):
        rows = [dict(self.raw[0], source_record_number=i + 1) for i in range(5)]
        hours, _ = aggregate_activity(rows, [self.scope])
        self.assertEqual(hours[0].observation_count, 5)

    def test_demand_contract_never_exports_raw_positions_ids_or_subhour_times(self):
        text = json.dumps(dict(contract=self.plan.public_contract(), hours=[asdict(a) for a in self.hours]))
        for sentinel in ('42.301234', '42.241234', '-83.021234', 'SYNTHETIC_POSITION_SENTINEL',
                         'truck_id', 'source_record_number', '00:00:01'):
            self.assertNotIn(sentinel, text)
        for r in self.plan.requests:
            self.assertIn(r.latitude, (42.375, 42.125))
            self.assertEqual(r.longitude, -83.125)

    def test_request_windows_come_from_demand_with_buffer_and_no_gap_days(self):
        windows = [(r.latitude, r.start_date, r.end_date) for r in self.plan.requests]
        self.assertEqual(windows, [(42.125, '2026-01-04', '2026-01-05'),
                                   (42.375, '2026-01-04', '2026-01-05'),
                                   (42.375, '2026-01-08', '2026-01-08')])
        self.assertEqual(self.plan.public_contract()['requested_api_hours'], 120)
        self.assertEqual(self.plan.public_contract()['required_bin_hours'], 18)
        self.assertTrue(all(r.grid_only for r in self.plan.requests))
        self.assertTrue(all(r.parameters['elevation'] == 'nan' and r.parameters['cell_selection'] == 'nearest'
                            for r in self.plan.requests))

    def test_two_timezone_hypotheses_require_different_weather_instants(self):
        a = self.hours[0]
        from winterops.weather_demand import required_epochs
        t, _, lag = required_epochs(a, 'America/Toronto', 2)
        u, _, _ = required_epochs(a, 'UTC', 2)
        self.assertEqual(t - u, 5 * 3600)
        self.assertEqual(lag, (t, t - 3600))

    def test_contiguous_dates_merge_but_lookback_boundary_is_not_dropped(self):
        plan = DemandPlan((self.hours[0], replace(self.hours[0], source_local_hour='2026-01-06 00:00:00')))
        self.assertEqual([(r.start_date, r.end_date) for r in plan.requests], [('2026-01-04', '2026-01-06')])
        no_lag = DemandPlan((self.hours[0],), 0)
        self.assertEqual([(r.start_date, r.end_date) for r in no_lag.requests], [('2026-01-05', '2026-01-05')])

    def test_empty_activity_makes_zero_requests_and_zero_matches(self):
        plan = DemandPlan(())
        acquire = Mock()
        self.assertEqual(acquire_demand(plan, '/not-used', acquire=acquire), ())
        acquire.assert_not_called()
        self.assertEqual(matched_projection(plan, weather_catalog(plan, []))['matches'], [])

    def test_duplicate_bins_bad_representatives_dst_and_unbounded_lag_reject(self):
        for hours in ((self.hours[0], self.hours[0]),
                      (replace(self.hours[0], representative_latitude=42.301234),),
                      (replace(self.hours[0], source_local_hour='2026-03-08 02:00:00'),),
                      (replace(self.hours[0], source_local_hour='2026-11-01 01:00:00'),)):
            with self.assertRaises(WeatherContractError):
                DemandPlan(hours)
        for value in (-1, 7, True):
            with self.assertRaises(WeatherContractError):
                DemandPlan(self.hours, value)

    def test_request_ceiling_prevents_a_large_sparse_calendar_fetch(self):
        hours = tuple(replace(self.hours[0], source_local_hour=(datetime(2026, 1, 5)
                      + timedelta(days=i * 4)).isoformat(sep=' ')) for i in range(17))
        with self.assertRaisesRegex(WeatherContractError, 'REQUEST_BUDGET'):
            DemandPlan(hours)


class GridMatchingTests(unittest.TestCase):
    def setUp(self):
        self.scope, self.raw = synthetic_inputs()
        self.hours, _ = aggregate_activity(self.raw, [self.scope])
        self.plan = DemandPlan(self.hours)
        self.snapshots = synthetic_snapshots(self.plan)
        self.catalog = weather_catalog(self.plan, self.snapshots)

    def test_different_requested_representatives_share_one_returned_grid(self):
        self.assertEqual(len(self.catalog['bin_to_grid']), 2)
        self.assertEqual(len(self.catalog['grids']), 1)
        grid = next(iter(self.catalog['grids'].values()))
        self.assertEqual((grid['latitude'], grid['longitude']), (42.25, -83.0))
        self.assertNotIn(grid['longitude'], {r.longitude for r in self.plan.requests})

    def test_facts_deduplicate_grid_hours_and_keep_each_response_location_provenance(self):
        facts = self.catalog['facts']
        self.assertEqual(len(facts), 12)
        self.assertEqual(len({(r['weather_snapshot_id'], r['grid_id'], r['valid_time_utc']) for r in facts}), 12)
        self.assertTrue(any(len(r['sources']) == 2 for r in facts))
        self.assertTrue(all(s['response_location_index'] == 0 for r in facts for s in r['sources']))
        self.assertEqual({s['request_id'] for r in facts for s in r['sources']},
                         {r.request_id for r in self.plan.requests})

    def test_many_to_one_weather_matching_has_exact_activity_grain_not_calendar_rows(self):
        projection = matched_projection(self.plan, self.catalog)
        rows = projection['matches']
        self.assertEqual(len(rows), 6)
        self.assertEqual(len({(r['processing_key'], r['spatial_bin'], r['source_local_hour'],
                               r['timezone_hypothesis']) for r in rows}), 6)
        self.assertEqual(len(projection['matched_weather_keys']), 12)
        for hypothesis in ('America/Toronto', 'UTC'):
            self.assertEqual(sum(r['observation_count'] for r in rows if r['timezone_hypothesis'] == hypothesis), 15)
        self.assertTrue(all(r['weather_coverage'] == 'COMPLETE' for r in rows))
        self.assertFalse(any('2026-01-06' in r['source_local_hour'] for r in rows))

    def test_temperature_instant_and_current_hour_accumulation_use_distinct_endpoints(self):
        rows = matched_projection(self.plan, self.catalog)['matches']
        row = next(r for r in rows if r['timezone_hypothesis'] == 'UTC' and r['source_local_hour'].startswith('2026-01-05'))
        self.assertEqual(row['temperature_2m_c'], 0.0)
        self.assertEqual(row['precipitation_activity_hour_mm'], 1.0)  # ending 01:00, not 00:00
        self.assertEqual(row['precipitation_antecedent_mm'], 2.0)  # ending 00:00 and prior 23:00
        self.assertEqual(row['antecedent_present_hours'], 2)
        self.assertEqual(row['temperature_valid_time_utc'], '2026-01-05T00:00:00+00:00')
        self.assertEqual(row['accumulation_valid_time_utc'], '2026-01-05T01:00:00+00:00')

    def test_missing_fact_or_null_is_visible_and_never_interpolated_or_zero_filled(self):
        catalog = deepcopy(self.catalog)
        catalog['facts'] = [r for r in catalog['facts'] if r['valid_time_utc'] != '2026-01-05T01:00:00+00:00']
        row = next(r for r in matched_projection(self.plan, catalog)['matches'] if r['timezone_hypothesis'] == 'UTC')
        self.assertIsNone(row['precipitation_activity_hour_mm'])
        self.assertEqual(row['weather_coverage'], 'MISSING_GRID_OR_HOUR')
        catalog = deepcopy(self.catalog)
        next(r for r in catalog['facts'] if r['valid_time_utc'] == '2026-01-05T01:00:00+00:00')['snowfall_preceding_hour_cm'] = None
        row = next(r for r in matched_projection(self.plan, catalog)['matches'] if r['timezone_hypothesis'] == 'UTC')
        self.assertIsNone(row['snowfall_activity_hour_cm'])
        self.assertEqual(row['weather_coverage'], 'NULL_MEASUREMENT')

    def test_missing_antecedent_hour_is_separate_from_current_hour_coverage(self):
        catalog = deepcopy(self.catalog)
        catalog['facts'] = [r for r in catalog['facts'] if r['valid_time_utc'] != '2026-01-04T23:00:00+00:00']
        row = next(r for r in matched_projection(self.plan, catalog)['matches'] if r['timezone_hypothesis'] == 'UTC')
        self.assertEqual(row['weather_coverage'], 'COMPLETE')
        self.assertIsNone(row['precipitation_antecedent_mm'])
        self.assertEqual(row['antecedent_present_hours'], 1)
        self.assertEqual(row['antecedent_coverage'], 'MISSING_OR_NULL')

    def test_conflicting_overlapping_grid_values_stop_instead_of_choosing_latest(self):
        snapshots = deepcopy(self.snapshots)
        snapshots[1][1][0]['temperature_2m_c'] = 100.0  # outside needed hours, not used
        next(r for r in snapshots[1][1] if r['valid_time_utc'] == '2026-01-05T00:00:00+00:00')['temperature_2m_c'] = 100.0
        with self.assertRaisesRegex(WeatherContractError, 'GRID_HOUR_CONFLICT'):
            weather_catalog(self.plan, snapshots)

    def test_changed_returned_grid_for_same_bin_or_unplanned_response_reject(self):
        snapshots = deepcopy(self.snapshots)
        snapshots[2][0]['grid']['longitude'] = -82.75
        with self.assertRaisesRegex(WeatherContractError, 'GRID_ASSIGNMENT_CHANGED'):
            weather_catalog(self.plan, snapshots)
        with self.assertRaisesRegex(WeatherContractError, 'UNEXPECTED_OR_DUPLICATE_RESPONSE'):
            weather_catalog(self.plan, self.snapshots + self.snapshots[:1])

    def test_different_elevation_is_not_collapsed_into_same_grid_measurement_identity(self):
        snapshots = deepcopy(self.snapshots[:2])
        snapshots[1][0]['grid']['elevation'] += 1
        catalog = weather_catalog(self.plan, snapshots)
        self.assertEqual(len(catalog['grids']), 2)

    def test_missing_response_keeps_unresolved_activity_rows_and_coverage_status(self):
        catalog = weather_catalog(self.plan, [])
        rows = matched_projection(self.plan, catalog)['matches']
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(r['grid_id'] is None and r['weather_coverage'] == 'MISSING_GRID_OR_HOUR' for r in rows))

    def test_duplicate_fact_or_mixed_snapshot_rejects_join_cardinality_ambiguity(self):
        bad = deepcopy(self.catalog)
        bad['facts'].append(bad['facts'][0])
        with self.assertRaisesRegex(WeatherContractError, 'DUPLICATE_WEATHER_FACT'):
            matched_projection(self.plan, bad)
        bad = deepcopy(self.catalog)
        bad['facts'][0]['weather_snapshot_id'] = 'other'
        with self.assertRaisesRegex(WeatherContractError, 'MIXED_WEATHER_SNAPSHOTS'):
            matched_projection(self.plan, bad)

    def test_acquisition_is_per_demand_request_and_reruns_can_reuse_exact_cache(self):
        by_url = {r.url: (r, pair) for r, pair in zip(self.plan.requests, self.snapshots)}
        def response(request, timeout):
            r, (metadata, rows) = by_url[request.full_url]
            body = dict(metadata['grid'], hourly_units=dict(time='unixtime', temperature_2m='°C',
                        precipitation='mm', snowfall='cm'), hourly=dict(time=list(r.epochs),
                        temperature_2m=[v['temperature_2m_c'] for v in rows],
                        precipitation=[v['precipitation_preceding_hour_mm'] for v in rows],
                        snowfall=[v['snowfall_preceding_hour_cm'] for v in rows]))
            obj = Mock(status=200)
            obj.headers = Message()
            obj.headers['Content-Type'] = 'application/json'
            obj.geturl.return_value = request.full_url
            obj.read.return_value = canonical(body)
            obj.__enter__ = Mock(return_value=obj)
            obj.__exit__ = Mock(return_value=False)
            return obj
        opener = Mock(side_effect=response)
        def acquire(path, request):
            return acquire_snapshot(path, request, opener=opener)
        with tempfile.TemporaryDirectory() as root:
            first = acquire_demand(self.plan, root, acquire=acquire)
            second = acquire_demand(self.plan, root, acquire=acquire)
            self.assertEqual(first, second)
            self.assertEqual(opener.call_count, 3)  # zero additional GETs on rerun
            self.assertEqual(len(list(Path(root).iterdir())), 3)

    def test_synthetic_cli_proof_is_labelled_blocked_and_contains_no_raw_positions(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'proof.json'
            command = [sys.executable, str(ROOT / 'scripts/weather_activity.py'), 'demo', '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            proof = json.loads(output.read_text())
            self.assertEqual(proof['evidence'], 'SYNTHETIC_OFFLINE_ONLY')
            self.assertEqual(proof['weather_http_requests'], 0)
            self.assertIn('BLOCKED', proof['live_spatial_matching'])
            for text in ('42.301234', '-83.021234', 'truck_id', 'SYNTHETIC_POSITION_SENTINEL'):
                self.assertNotIn(text, output.read_text())
            before = output.read_bytes()
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertEqual(output.read_bytes(), before)

    def test_private_plan_cli_reads_silver_locally_and_only_writes_coarse_demand(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            silver, selection, output = root / 'silver.jsonl', root / 'selection.json', root / 'plan.json'
            silver.write_text(''.join(json.dumps(row) + '\n' for row in self.raw))
            selection.write_text(json.dumps(dict(selected=[asdict(self.scope)])))
            command = [sys.executable, str(ROOT / 'scripts/weather_activity.py'), 'plan',
                       '--private-silver', str(silver), '--selection', str(selection), '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(output.read_text())
            self.assertEqual(plan['demand']['request_count'], 3)
            self.assertEqual(plan['audit']['retained_observations'], 15)
            self.assertNotIn('SYNTHETIC_POSITION_SENTINEL', output.read_text())
            self.assertNotIn('42.301234', result.stdout + result.stderr + output.read_text())
            command[command.index('--private-silver') + 1] = str(ROOT / 'README.md')
            command[-1] = str(root / 'second.json')
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('PRIVATE_FILES_MUST_STAY_OUTSIDE_REPOSITORY', result.stderr)


if __name__ == '__main__':
    unittest.main()
