"""Weather source-contract, temporal-integrity and batch recovery regressions."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from email.message import Message
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

from winterops.unified_gold import load_selection
from winterops.weather import (MAX_BYTES, WeatherContractError, WeatherRequest, acquire_snapshot,
                               canonical, load_snapshot, stage_response)
from winterops.weather_analysis import conditional_instant, daily_weather, join_daily_activity

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'data/weather/windsor_era5_20260104_20260202'


def payload(request):
    n = len(request.epochs)
    return dict(latitude=42.25, longitude=-83.0, elevation=189.0, timezone='GMT', utc_offset_seconds=0,
                hourly_units=dict(time='unixtime', temperature_2m='°C', precipitation='mm', snowfall='cm'),
                hourly=dict(time=list(request.epochs), temperature_2m=[-2.0] * n,
                            precipitation=[1.0] * n, snowfall=[0.7] * n))


class WeatherContractTests(unittest.TestCase):
    def setUp(self):
        self.request = WeatherRequest('2026-01-25', '2026-02-02')
        self.body = payload(self.request)

    def stage(self, body=None):
        return stage_response(canonical(self.body if body is None else body), self.request)[0]

    def test_request_is_bounded_and_explicitly_pins_model_time_and_units(self):
        self.assertEqual(len(WeatherRequest().epochs), 720)
        self.assertIn('models=era5', self.request.url)
        self.assertIn('timezone=GMT&timeformat=unixtime', self.request.url)
        self.assertEqual(self.request, replace(self.request))
        for change in (dict(start_date='2026-02-03'), dict(end_date='2026-03-01'),
                       dict(start_date='20260125'), dict(latitude=True), dict(latitude=float('nan')),
                       dict(longitude=-70), dict(start_date=None)):
            with self.subTest(change=change), self.assertRaises(WeatherContractError):
                replace(self.request, **change)

    def test_exact_utc_hourly_grain_and_accumulation_intervals(self):
        rows = self.stage()
        self.assertEqual(len({(r['snapshot_id'], r['valid_time_utc']) for r in rows}), len(rows))
        self.assertEqual(rows[0]['accumulation_start_utc'], '2026-01-24T23:00:00+00:00')
        self.assertEqual(rows[0]['valid_time_utc'], '2026-01-25T00:00:00+00:00')
        self.assertEqual(rows[0]['weather_kind'], 'historical_reanalysis')

    def test_nulls_are_retained_with_quality_flags_and_never_zero_filled(self):
        self.body['hourly']['snowfall'][5] = None
        rows = self.stage()
        self.assertIsNone(rows[5]['snowfall_preceding_hour_cm'])
        self.assertEqual(rows[5]['missing_variables'], ['snowfall'])

    def test_negative_temperature_is_valid_and_negative_accumulation_is_rejected(self):
        self.stage()
        for variable in ('precipitation', 'snowfall'):
            body = deepcopy(self.body)
            body['hourly'][variable][0] = -0.1
            with self.assertRaises(WeatherContractError):
                self.stage(body)

    def test_numeric_strings_booleans_objects_and_nonfinite_values_reject(self):
        for value in ('0', True, {}, [], float('inf')):
            body = deepcopy(self.body)
            body['hourly']['temperature_2m'][0] = value
            with self.subTest(value=str(value)), self.assertRaises(ValueError):
                self.stage(body)
        with self.assertRaisesRegex(WeatherContractError, 'NONFINITE'):
            stage_response(b'{"value":NaN}', self.request)

    def test_wrong_units_timezone_and_grid_metadata_reject(self):
        for change in (dict(utc_offset_seconds=-18000), dict(utc_offset_seconds=False),
                       dict(timezone='America/Toronto'), dict(latitude=0), dict(elevation=None)):
            with self.subTest(change=change), self.assertRaises(WeatherContractError):
                self.stage(dict(self.body, **change))
        for key in ('time', 'temperature_2m', 'precipitation', 'snowfall'):
            body = deepcopy(self.body)
            body['hourly_units'][key] = 'wrong'
            with self.assertRaises(WeatherContractError):
                self.stage(body)

    def test_unrelated_optional_response_fields_do_not_break_valid_contract(self):
        body = dict(self.body, generationtime_ms=1.2, future_metadata={'extension': True})
        self.assertEqual(len(self.stage(body)), len(self.request.epochs))

    def test_missing_duplicate_unordered_wrong_type_or_off_hour_times_reject(self):
        epochs = self.body['hourly']['time']
        for times in (epochs[:-1], [epochs[0]] + epochs[:-1], list(reversed(epochs)),
                      [float(epochs[0])] + epochs[1:], [epochs[0] + 1] + epochs[1:]):
            body = deepcopy(self.body)
            body['hourly']['time'] = times
            with self.assertRaises(WeatherContractError):
                self.stage(body)

    def test_mismatched_arrays_error_objects_and_malformed_json_reject(self):
        body = deepcopy(self.body)
        body['hourly']['precipitation'].pop()
        with self.assertRaises(WeatherContractError):
            self.stage(body)
        for raw in (b'[]', b'null', b'\xff', b'{', b'{"error":false}',
                    b'{"time":1,"time":2}', b'x' * (MAX_BYTES + 1)):
            with self.subTest(raw=raw[:20]), self.assertRaises(WeatherContractError):
                stage_response(raw, self.request)

    def test_snapshot_changes_with_request_or_exact_response_bytes(self):
        rows = self.stage()
        raw = canonical(self.body) + b'\n'
        other = stage_response(raw, self.request)[0]
        self.assertNotEqual(rows[0]['snapshot_id'], other[0]['snapshot_id'])
        self.assertNotEqual(self.request.request_id, replace(self.request, latitude=42.4).request_id)

    def response(self, body=None, status=200, content_type='application/json'):
        response = Mock()
        response.status = status
        response.geturl.return_value = self.request.url
        response.headers = Message()
        response.headers['Content-Type'] = content_type
        response.read.return_value = canonical(self.body if body is None else body)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        return response

    def test_fetch_is_one_call_then_rerun_is_verified_without_network(self):
        opener = Mock(return_value=self.response())
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / 'snapshot'
            first, rows = acquire_snapshot(target, self.request, opener=opener)
            second, reused = acquire_snapshot(target, self.request, opener=opener)
            self.assertEqual(first, second)
            self.assertEqual(rows, reused)
            self.assertEqual(opener.call_count, 1)
            self.assertEqual(opener.call_args.kwargs['timeout'], 30)
            self.assertEqual(sorted(p.name for p in target.iterdir()), ['response.json', 'retrieval.json'])

    def test_fetch_failure_leaves_no_partial_final_bundle_and_no_retry(self):
        for response in (self.response(status=429), self.response(content_type='text/html'),
                         self.response(dict(error=True, reason='failure'))):
            opener = Mock(return_value=response)
            with tempfile.TemporaryDirectory() as root:
                target = Path(root) / 'snapshot'
                with self.assertRaises(WeatherContractError):
                    acquire_snapshot(target, self.request, opener=opener)
                self.assertFalse(target.exists())
                self.assertEqual(opener.call_count, 1)

    def test_existing_corrupt_or_conflicting_bundle_never_triggers_download(self):
        opener = Mock(return_value=self.response())
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / 'snapshot'
            acquire_snapshot(target, self.request, opener=opener)
            with self.assertRaises(WeatherContractError):
                acquire_snapshot(target, replace(self.request, latitude=42.4), opener=opener)
            path = target / 'response.json'
            path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaises(WeatherContractError):
                acquire_snapshot(target, self.request, opener=opener)
            self.assertEqual(opener.call_count, 1)


class WeatherAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.request = WeatherRequest('2026-01-25', '2026-02-02')
        self.body = payload(self.request)
        self.rows = stage_response(canonical(self.body), self.request)[0]
        self.scope = load_selection(ROOT / 'docs/FOUR_WEEK_SELECTION.json').selected[-1]
        evidence = json.loads((ROOT / 'docs/FOUR_WEEK_LOCAL_EVIDENCE.json').read_text())
        self.activity = evidence['fourth_week_daily']

    def test_accumulations_use_end_of_preceding_hour_temperature_uses_instant(self):
        start = int(datetime(2026, 1, 26, tzinfo=timezone.utc).timestamp())
        n = self.body['hourly']['time'].index(start)
        self.body['hourly']['precipitation'] = [0.0] * len(self.rows)
        self.body['hourly']['precipitation'][n] = 100.0  # belongs to previous day
        self.body['hourly']['precipitation'][n + 24] = 2.0  # belongs to Jan 26
        rows = stage_response(canonical(self.body), self.request)[0]
        day = daily_weather(rows, '2026-01-26', 'UTC')
        self.assertEqual(day['precipitation_sum_mm'], 2.0)
        self.assertEqual(day['temperature_mean_c'], -2.0)

    def test_sensitivity_has_same_activity_and_five_hour_different_weather_window(self):
        a = join_daily_activity(self.activity, self.rows, [self.scope], timezone_assumption='America/Toronto')
        b = join_daily_activity(self.activity, self.rows, [self.scope], timezone_assumption='UTC')
        self.assertEqual([r['observation_count'] for r in a], [r['observation_count'] for r in b])
        self.assertEqual(a[0]['window_start_utc'], '2026-01-26T05:00:00+00:00')
        self.assertEqual(b[0]['window_start_utc'], '2026-01-26T00:00:00+00:00')
        self.assertTrue(a[0]['retrospective_only'])
        self.assertIn('CONDITIONAL', a[0]['alignment_status'])

    def test_missing_activity_calendar_days_are_null_and_totals_reconcile(self):
        joined = join_daily_activity(self.activity, self.rows, [self.scope], timezone_assumption='UTC')
        self.assertEqual(len(joined), 7)
        self.assertEqual(sum(r['activity_present'] for r in joined), 5)
        self.assertEqual(sum(r['observation_count'] or 0 for r in joined), 66824)
        self.assertEqual([r['observation_count'] for r in joined[-2:]], [None, None])

    def test_null_weather_and_missing_boundary_hours_produce_null_daily_totals(self):
        rows = deepcopy(self.rows)
        next(r for r in rows if r['valid_time_utc'] == '2026-01-26T12:00:00+00:00')['snowfall_preceding_hour_cm'] = None
        day = daily_weather(rows, '2026-01-26', 'UTC')
        self.assertIsNone(day['snowfall_sum_cm'])
        self.assertEqual(day['snowfall_preceding_hour_cm_present_hours'], 23)
        self.assertEqual(day['precipitation_sum_mm'], 24.0)
        boundary = daily_weather(self.rows, '2026-02-02', 'UTC')
        self.assertIsNone(boundary['precipitation_sum_mm'])
        self.assertEqual(boundary['temperature_mean_c'], -2.0)

    def test_ambiguous_and_nonexistent_dst_hours_reject_without_guessing(self):
        for stamp in (datetime(2026, 3, 8, 2, 30), datetime(2026, 11, 1, 1, 30)):
            with self.assertRaisesRegex(WeatherContractError, 'AMBIGUOUS_OR_NONEXISTENT'):
                conditional_instant(stamp, 'America/Toronto')

    def test_dst_days_have_23_and_25_weather_hours(self):
        for start, end, day, hours in (('2026-03-07', '2026-03-10', '2026-03-08', 23),
                                      ('2026-10-31', '2026-11-03', '2026-11-01', 25)):
            request = WeatherRequest(start, end)
            rows = stage_response(canonical(payload(request)), request)[0]
            daily = daily_weather(rows, day, 'America/Toronto')
            self.assertEqual(daily['expected_hours'], hours)
            self.assertEqual(daily['precipitation_sum_mm'], float(hours))

    def test_duplicate_weather_keys_and_mixed_snapshots_block_many_to_many_joins(self):
        for rows in (self.rows + [self.rows[0]], self.rows + [dict(self.rows[0], snapshot_id='other')]):
            with self.assertRaises(WeatherContractError):
                daily_weather(rows, '2026-01-26', 'UTC')

    def test_duplicate_activity_or_wrong_version_policy_and_counts_reject(self):
        bad = (self.activity + [self.activity[0]],
               [dict(self.activity[0], processing_key='other')],
               [dict(self.activity[0], quality_policy_sha256='other')],
               [dict(self.activity[0], plow_active_observations=999999)],
               [dict(self.activity[0], observation_count=True)])
        for rows in bad:
            with self.assertRaises(WeatherContractError):
                join_daily_activity(rows, self.rows, [self.scope], timezone_assumption='UTC')
        with self.assertRaises(WeatherContractError):
            join_daily_activity(self.activity, self.rows, [self.scope, self.scope], timezone_assumption='UTC')

    def test_naive_source_time_is_never_mutated_and_aware_input_rejects(self):
        original = deepcopy(self.activity)
        join_daily_activity(self.activity, self.rows, [self.scope], timezone_assumption='UTC')
        self.assertEqual(original, self.activity)
        with self.assertRaises(WeatherContractError):
            conditional_instant(datetime.now(timezone.utc), 'UTC')


class CommittedWeatherSampleTests(unittest.TestCase):
    def test_actual_sample_integrity_types_units_missingness_and_grid(self):
        metadata, rows = load_snapshot(SAMPLE)
        self.assertEqual(len(rows), 720)
        self.assertEqual(sum(len(r['missing_variables']) for r in rows), 0)
        self.assertEqual((metadata['grid']['latitude'], metadata['grid']['longitude']), (42.25, -83.0))
        self.assertEqual(metadata['model_attestation'], 'REQUEST_PARAMETER_ONLY')

    def test_offline_cli_reproduces_real_join_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'example.json'
            cmd = [sys.executable, str(ROOT / 'scripts/weather_batch.py'), 'example', '--output', str(output)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            evidence = json.loads(output.read_text())
            self.assertFalse(evidence['activity_timezone_verified'])
            self.assertFalse(evidence['predictive_features_allowed'])
            self.assertEqual(len(evidence['scenarios']['UTC']), 7)
            before = output.read_bytes()
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
