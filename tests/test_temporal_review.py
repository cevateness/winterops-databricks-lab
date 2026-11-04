import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

from winterops.temporal_review import review_clock, summarize_matches
from winterops.weather import WeatherContractError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from weather_activity import demo


class ClockReviewTests(unittest.TestCase):
    def setUp(self):
        self.evidence = json.loads((ROOT / 'data/fixtures/source_time_evidence.json').read_text())

    def test_real_profile_and_features_corroborate_without_promoting_csv(self):
        result = review_clock(self.evidence)
        self.assertEqual(result['status'], 'CORROBORATED_FOR_PINNED_SCOPES')
        self.assertEqual(result['matched_source_hours'], 325)
        self.assertEqual(result['observation_count'], 298051)
        self.assertEqual(result['endpoint_hour_agreements'], {'America/Toronto': 8, 'UTC': 0})
        self.assertFalse(result['original_csv_export_timezone_confirmed'])
        self.assertFalse(result['original_ntz_contract_changed'])

    def test_equal_total_does_not_hide_changed_hour_distribution(self):
        counts = self.evidence['published_profile_response']['features']
        counts[0]['attributes']['observation_count'] += 1
        counts[1]['attributes']['observation_count'] -= 1
        result = review_clock(self.evidence)
        self.assertEqual(result['differing_profile_hours'], 2)
        self.assertIsNone(result['working_hypothesis'])

    def test_truncated_whole_profile_is_rejected(self):
        self.evidence['published_profile_response']['exceededTransferLimit'] = True
        with self.assertRaisesRegex(WeatherContractError, 'INCOMPLETE_PUBLISHED_PROFILE'):
            review_clock(self.evidence)

    def test_duplicate_profile_hour_rejected(self):
        self.evidence['published_profile_response']['features'].append(
            self.evidence['published_profile_response']['features'][0])
        with self.assertRaisesRegex(WeatherContractError, 'DUPLICATE_PUBLISHED_HOUR'):
            review_clock(self.evidence)

    def test_browser_timezone_cannot_replace_field_contract(self):
        self.evidence['layer_metadata_projection']['dateFieldsTimeReference'] = None
        self.evidence['metadata'] = {'timezone': 'America/New_York'}
        self.assertIsNone(review_clock(self.evidence)['working_hypothesis'])

    def test_contradictory_feature_dates_do_not_promote(self):
        self.evidence['datetime_only_samples_projection'][0]['published_utc_epoch_ms'] -= 18000000
        self.assertIsNone(review_clock(self.evidence)['working_hypothesis'])

    def test_missing_or_duplicate_endpoint_is_rejected(self):
        samples = self.evidence['datetime_only_samples_projection']
        samples.pop()
        with self.assertRaisesRegex(WeatherContractError, 'ENDPOINT_SAMPLES_INCOMPLETE'):
            review_clock(self.evidence)
        samples.append(samples[0])
        with self.assertRaisesRegex(WeatherContractError, 'ENDPOINT_SAMPLE_CONTRACT'):
            review_clock(self.evidence)

    def test_minmax_statistics_are_not_clock_proof(self):
        self.evidence['first_week_statistic_diagnostic'] = {'response': 'arbitrary alternative representation'}
        # Feature values still support Toronto, independently of statistic epochs.
        self.assertEqual(review_clock(self.evidence)['working_hypothesis'], 'America/Toronto')


class AnalyticalReviewTests(unittest.TestCase):
    def setUp(self):
        self.matches = demo()['matches']

    def test_alternative_hypotheses_not_added_and_missing_days_not_zero(self):
        result = summarize_matches(self.matches)
        self.assertEqual(result['hypothesis_totals'], {'America/Toronto': 15, 'UTC': 15})
        self.assertEqual(len(result['days']), 4)
        self.assertNotIn('2026-01-06', {r['source_local_day'] for r in result['days']})
        self.assertTrue(result['retrospective_only'])

    def test_same_grid_hour_deduplicated_across_activity_bins(self):
        day = next(r for r in summarize_matches(self.matches)['days']
                   if r['source_local_day'] == '2026-01-05' and r['timezone_hypothesis'] == 'America/Toronto')
        self.assertEqual(day['matched_cell_hours'], 2)
        self.assertEqual(day['sampled_grid_hours'], 1)

    def test_duplicate_grain_and_count_disagreement_rejected(self):
        with self.assertRaisesRegex(WeatherContractError, 'DUPLICATE_MATCH_GRAIN'):
            summarize_matches(self.matches + [self.matches[0]])
        self.matches[0]['observation_count'] += 1
        with self.assertRaisesRegex(WeatherContractError, 'PAIRED_COUNTS_DIFFER'):
            summarize_matches(self.matches)

    def test_unpaired_hypothesis_rejected(self):
        with self.assertRaisesRegex(WeatherContractError, 'PAIRED_HYPOTHESES_REQUIRED'):
            summarize_matches(self.matches[1:])

    def test_weather_conflict_for_shared_grid_hour_rejected(self):
        self.matches[0]['temperature_2m_c'] += 1
        with self.assertRaisesRegex(WeatherContractError, 'CONFLICTING_WEATHER_FACT'):
            summarize_matches(self.matches)

    def test_missing_weather_is_counted_without_zero_imputation(self):
        for row in self.matches:
            row['temperature_2m_c'] = None
        result = summarize_matches(self.matches)
        self.assertTrue(all(row['sampled_temperature_min_c'] is None for row in result['days']))
        self.assertTrue(all(row['missing_measurements'] > 0 for row in result['days']))

    def test_summary_excludes_detailed_join_identifiers(self):
        text = json.dumps(summarize_matches(self.matches))
        for private in ('spatial_bin', 'processing_key', 'source_version_id', 'grid_id', 'latitude', 'longitude'):
            self.assertNotIn('"' + private + '"', text)

    def test_recorded_daily_summary_reconciles_to_independent_source_profile(self):
        result = json.loads((ROOT / 'docs/TEMPORAL_REVIEW_RESULTS.json').read_text())['analytical_review']
        profile = json.loads((ROOT / 'data/fixtures/source_time_evidence.json').read_text())['local_source_hour_profile']
        expected = {}
        for hour, count in profile.items():
            expected[hour[:10]] = expected.get(hour[:10], 0) + count
        self.assertEqual(len(result['days']), 50)
        for zone in ('America/Toronto', 'UTC'):
            rows = [r for r in result['days'] if r['timezone_hypothesis'] == zone]
            self.assertEqual({r['source_local_day']: r['observation_count'] for r in rows}, expected)
            self.assertEqual(sum(r['matched_cell_hours'] for r in rows), 842)
            self.assertEqual(sum(r['outside_source_review_observations'] for r in rows), 863)
            self.assertEqual(sum(r['observed_source_hours'] for r in rows), 325)


class ReviewCliTests(unittest.TestCase):
    def test_offline_cli_and_create_only_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'review.json'
            command = [sys.executable, str(ROOT / 'scripts/review_temporal_alignment.py'), '--output', str(output)]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            recorded = output.read_bytes()
            self.assertEqual(json.loads(recorded)['weather_http_requests'], 0)
            again = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(again.returncode, 2)
            self.assertIn('OUTPUT_ALREADY_EXISTS', again.stderr)
            self.assertEqual(output.read_bytes(), recorded)

    def test_wrong_archive_hash_rejected_before_reading_members(self):
        pin = json.loads((ROOT / 'docs/WEATHER_ACTIVITY_EXECUTION_RESULTS.json').read_text())['private_download_artifact']
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'wrong.zip'
            archive.write_bytes(b'0' * pin['bytes'])
            output = Path(directory) / 'review.json'
            run = subprocess.run([sys.executable, str(ROOT / 'scripts/review_temporal_alignment.py'),
                                  '--output', str(output), '--archive', str(archive)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertIn('ARCHIVE_HASH_MISMATCH', run.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
