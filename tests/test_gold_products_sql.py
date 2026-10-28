"""SQLite-adapted SQL versus independent Python expectations; not Spark evidence."""
from datetime import datetime
from dataclasses import replace
from decimal import Decimal
import hashlib
import re
import sqlite3
import unittest

from gold_products_fixture import fixture
from test_analytics_sql import CountIf, sqlite_dialect
from winterops.analytics import SILVER_TYPES, build_plan
from winterops.gold_products import DiagnosticSettings, build_products, ntz_clock_index_sql, reference_products


def adapted(sql):
    # Preserve calendar arithmetic; emulate only native DATE/DECIMAL/NTZ casts.
    sql = sqlite_dialect(sql)
    sql = sql.replace(
        'CAST(CAST(substring(CAST(event_time_unzoned AS STRING), 18, 9) AS DECIMAL(8,6)) * 1000000 AS BIGINT)',
        'source_seconds_us(substr(event_time_unzoned, 18, 9))')
    sql = sql.replace('CAST(substring(CAST(event_time_unzoned AS STRING), 1, 10) AS DATE)',
                      'substr(event_time_unzoned, 1, 10)')
    sql = sql.replace("DATE '2000-01-01'", "'2000-01-01'")
    for column in ('event_time_unzoned', 'source_local_naive_hour'):
        sql = sql.replace('CAST(' + column + ' AS DATE)', 'substr(' + column + ', 1, 10)')
    return sql.replace('CAST(event_time_unzoned AS STRING)', 'CAST(event_time_unzoned AS TEXT)')


class GoldProductsSqlTests(unittest.TestCase):
    def setUp(self):
        self.config, self.rows = fixture()
        self.settings = DiagnosticSettings(1800, 2)
        self.plan = build_products(self.config, self.settings)
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.create_aggregate('count_if', 1, CountIf)
        self.db.create_function('regexp', 2, lambda pattern, value: value is not None and bool(re.search(pattern, value)))
        def assertion(value, message):
            if not value:
                raise ValueError(message)
            return None
        self.db.create_function('assert_true', 2, assertion)
        self.db.create_function('datediff', 2, lambda end, start: (datetime.fromisoformat(end).date() - datetime.fromisoformat(start).date()).days)
        self.db.create_function('source_seconds_us', 1, lambda value: int(Decimal(value) * 1000000))
        self.db.execute('CREATE TABLE winterops_silver_windsor_valid (' + ', '.join(name + ' ' + kind for name, kind in SILVER_TYPES.items()) + ')')
        fields = list(SILVER_TYPES)
        self.db.executemany('INSERT INTO winterops_silver_windsor_valid VALUES (' + ','.join('?' for _ in fields) + ')',
                            [[row[name] for name in fields] for row in self.rows])
        self.rebuild_gold()

    def rebuild_gold(self):
        self.db.execute('DROP TABLE IF EXISTS winterops_gold_windsor_hourly_observations')
        # Use the original, already-tested Gold SELECT to seed the local baseline.
        gold = build_plan(self.config).views[2].partition('\nAS ')[2]
        self.db.execute('CREATE TABLE winterops_gold_windsor_hourly_observations AS ' + adapted(gold))

    def execute(self, sql):
        cursor = self.db.execute(adapted(sql))
        names = [item[0] for item in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]

    def preflight(self):
        for sql in self.plan.preflight:
            self.execute(sql)

    def test_all_products_match_python_oracle_and_preserve_sources_on_rerun(self):
        expected = reference_products(self.rows, self.config.scope, self.settings)
        before = self.db.total_changes
        definitions = self.db.execute('SELECT name, sql FROM sqlite_master ORDER BY name').fetchall()
        for _ in range(2):
            self.preflight()
            for name, sql in self.plan.queries:
                with self.subTest(product=name):
                    self.assertEqual(self.execute(sql), expected[name])
        self.assertEqual(self.db.total_changes, before)
        self.assertEqual(self.db.execute('SELECT name, sql FROM sqlite_master ORDER BY name').fetchall(), definitions)

    def test_equal_weekly_totals_do_not_hide_wrong_hourly_gold_counts(self):
        hours = [row[0] for row in self.db.execute('SELECT source_local_naive_hour FROM winterops_gold_windsor_hourly_observations ORDER BY 1 LIMIT 2')]
        self.db.execute('UPDATE winterops_gold_windsor_hourly_observations SET observation_count = observation_count - 1 WHERE source_local_naive_hour=?', (hours[0],))
        self.db.execute('UPDATE winterops_gold_windsor_hourly_observations SET observation_count = observation_count + 1 WHERE source_local_naive_hour=?', (hours[1],))
        self.assertEqual(self.db.execute('SELECT SUM(observation_count) FROM winterops_gold_windsor_hourly_observations').fetchone()[0], 15)
        with self.assertRaises(sqlite3.OperationalError):
            self.preflight()

    def test_per_hour_distinct_truck_mismatch_is_detected(self):
        self.db.execute("UPDATE winterops_gold_windsor_hourly_observations SET distinct_truck_count=3 WHERE source_local_naive_hour='2026-01-12 08:00:00'")
        with self.assertRaises(sqlite3.OperationalError):
            self.preflight()

    def test_wrong_gold_version_and_unrelated_silver_rows_fail_closed(self):
        self.db.execute('UPDATE winterops_gold_windsor_hourly_observations SET source_file_sha256=?', ('b' * 64,))
        with self.assertRaises(sqlite3.OperationalError):
            self.preflight()
        self.rebuild_gold()
        fields = list(SILVER_TYPES)
        row = dict(self.rows[0], source_file_sha256='b' * 64)
        self.db.execute('INSERT INTO winterops_silver_windsor_valid VALUES (' + ','.join('?' for _ in fields) + ')', [row[name] for name in fields])
        with self.assertRaises(sqlite3.OperationalError):
            self.preflight()

    def test_null_status_and_incorrect_multiplicity_are_rejected(self):
        self.db.execute('UPDATE winterops_silver_windsor_valid SET engine_active=NULL WHERE rowid=1')
        with self.assertRaises(sqlite3.OperationalError):
            self.preflight()
        self.db.execute('UPDATE winterops_silver_windsor_valid SET engine_active=1, payload_occurrences=99 WHERE rowid=1')
        with self.assertRaises(sqlite3.OperationalError):
            self.preflight()

    def test_payload_identity_conflicts_remain_diagnostics_not_deduplication(self):
        self.db.execute('UPDATE winterops_silver_windsor_valid SET record_sha256=?, payload_occurrences=2, has_repeated_payload=1 WHERE truck_id IN (?, ?)', ('f' * 64, 'SYN-C', ' SYN-F '))
        self.rebuild_gold()
        self.preflight()
        overview = self.execute(self.plan.query('fleet_overview'))[0]
        self.assertEqual(overview['payload_identity_conflict_groups'], 1)
        self.assertEqual(overview['observation_count'], 15)
        self.assertEqual(overview['observed_identifier_count'], 6)

    def test_threshold_boundary_is_positive_and_does_not_discard_fractional_seconds(self):
        plan = build_products(self.config, DiagnosticSettings(300, 2))
        self.preflight()
        gaps = self.execute(plan.query('fleet_gap_distribution'))
        self.assertEqual(gaps[1]['consecutive_timestamp_pairs'], 3)
        self.assertEqual(gaps[1]['maximum_source_clock_gap_seconds'], 300)
        self.assertEqual(gaps[2]['minimum_source_clock_gap_seconds'], 3600.5)

    def test_result_schemas_do_not_expose_identifiers_hashes_or_locations(self):
        self.preflight()
        forbidden = {'truck_id', 'record_sha256', 'event_time_unzoned', 'latitude', 'longitude', 'source_file_path'}
        for name, sql in self.plan.queries:
            cursor = self.db.execute(adapted(sql))
            self.assertFalse(forbidden.intersection(item[0] for item in cursor.description), name)

    def test_calendar_index_covers_negative_origin_leap_day_and_microseconds(self):
        for value in ('1999-12-31 23:59:59.999999', '2000-01-01 00:00:00',
                      '2000-01-01 00:00:00.000001', '2024-02-29 23:59:59.123456'):
            delta = datetime.fromisoformat(value) - datetime(2000, 1, 1)
            expected = delta.days * 86400000000 + delta.seconds * 1000000 + delta.microseconds
            sql = 'SELECT ' + ntz_clock_index_sql('event_time_unzoned') + " AS clock_index FROM (SELECT '" + value + "' AS event_time_unzoned)"
            with self.subTest(value=value):
                self.assertEqual(self.execute(sql), [dict(clock_index=expected)])

    def test_frequency_boundaries_and_dense_hour_threshold(self):
        self.db.execute('DELETE FROM winterops_silver_windsor_valid')
        fields = list(SILVER_TYPES)
        rows = []
        for index, n in enumerate((1, 2, 10, 11, 100, 101, 1000, 1001)):
            row = dict(self.rows[0], truck_id='SYN-FREQUENCY-' + str(index),
                       record_sha256=hashlib.sha256(('synthetic-' + str(index)).encode()).hexdigest(),
                       payload_occurrences=n, has_repeated_payload=n > 1)
            rows.extend([row] * n)
        self.db.executemany('INSERT INTO winterops_silver_windsor_valid VALUES (' + ','.join('?' for _ in fields) + ')',
                            [[row[name] for name in fields] for row in rows])
        self.rebuild_gold()
        total = len(rows)
        expected = replace(self.config.expected, bronze_rows=total, silver_rows=total, valid_rows=total,
                           distinct_truck_ids=8, plow_active_observations=total, spreader_active_observations=0)
        plan = build_products(replace(self.config, expected=expected))
        for sql in plan.preflight:
            self.execute(sql)
        self.assertEqual(self.execute(plan.query('fleet_observation_frequency')), [
            dict(frequency_band='01_single', identifier_count=1, observation_count=1),
            dict(frequency_band='02_2_to_10', identifier_count=2, observation_count=12),
            dict(frequency_band='03_11_to_100', identifier_count=2, observation_count=111),
            dict(frequency_band='04_101_to_1000', identifier_count=2, observation_count=1101),
            dict(frequency_band='05_1001_plus', identifier_count=1, observation_count=1001)])
        self.assertEqual(self.execute(plan.query('fleet_overview'))[0]['dense_identifier_hour_count'], 1)


if __name__ == '__main__':
    unittest.main()
