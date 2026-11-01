"""Bind baseline reads to actual generated legacy/V2 definitions, offline only."""
from pathlib import Path
import re
import sqlite3
import unittest

import test_analytics_sql as legacy_fixture
import test_unified_gold as v2_fixture
from test_batch import OfflineJob
from winterops.batch import synthetic_request
from winterops.spark_ingestion import BRONZE_TYPES, SILVER_TYPES, MANIFEST_TYPES

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'src/winterops/sql/batch_gold_baselines.sql'
LEGACY = 'winterops_gold_windsor_hourly_observations'
WEEKLY = 'winterops_v2_gold_weekly_quality'


class BaselineContractFixture:
    """Small entrypoints around existing synthetic fixtures; no native client.

    The views are generated from their real definitions, not a mock schema that
    copies the baseline query's expectations. EXPLAIN binds names without running
    source-specific assertions; it is not Spark syntax/runtime verification.
    """
    def __init__(self, owner, request=None):
        v2 = v2_fixture.UnifiedGoldTests(methodName='runTest')
        v2.setUp()
        owner.addCleanup(v2.doCleanups)
        legacy = legacy_fixture.SqlLogicTests(methodName='runTest')
        legacy.setUp()
        owner.addCleanup(legacy.doCleanups)
        self.db, self.v2 = v2.db, v2
        self.job = OfflineJob(self.db, request or synthetic_request(), b'', b'', [])
        for name, ddl in legacy.db.execute("SELECT name,sql FROM sqlite_master WHERE type='table'"):
            self.db.execute(ddl)
            rows = legacy.db.execute('SELECT * FROM ' + name).fetchall()
            width = len(legacy.db.execute('PRAGMA table_info(' + name + ')').fetchall())
            self.db.executemany('INSERT INTO ' + name + ' VALUES (' + ','.join('?' for _ in range(width)) + ')', rows)
        for statement in legacy.plan.views:
            self.db.execute(legacy_fixture.sqlite_dialect(statement))
        for product in ('hourly', 'daily', 'weekly'):
            name = v2.plan.view_name(product).split('.')[-1]
            self.db.execute('CREATE VIEW ' + name + ' AS ' + v2_fixture.sqlite_sql(v2.plan.query(product)))

    def columns(self, name):
        return [r[1] for r in self.db.execute('PRAGMA table_info(' + name + ')')]

    def baseline(self, sql=None):
        cursor = self.db.execute((sql or BASELINE.read_text()).replace('workspace.default.', ''))
        return [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]

    def audit(self, sql):
        """Return source column reads resolved by SQLite's binder/authorizer."""
        history = re.fullmatch(r'DESCRIBE HISTORY workspace\.default\.(winterops_v2_dev_(bronze|silver|manifest)) LIMIT 1', sql)
        if history:
            expected = {'bronze': BRONZE_TYPES, 'silver': SILVER_TYPES, 'manifest': MANIFEST_TYPES}[history[2]]
            if self.columns(history[1]) != list(expected):
                raise ValueError('History target differs from V2 table contract')
            return dict(kind='DELTA_HISTORY_METADATA', table=history[1], referenced_source_columns=[],
                        result_field='version', native_history_runtime='NOT_EMULATED')
        reads = {}
        def authorize(action, table, column, database, trigger):
            if action == sqlite3.SQLITE_READ and column:
                reads.setdefault(database + '.' + table, set()).add(column)
            return sqlite3.SQLITE_OK
        self.db.set_authorizer(authorize)
        try:
            self.db.execute('EXPLAIN ' + self.job.dialect(sql), {
                'source_version_id': self.job.r.version.version_id, 'processing_key': self.job.r.key,
                'request_sha256': self.job.r.sha256, 'execution_mode': 'verify', 'recovery': 'deny'})
        finally:
            self.db.set_authorizer(None)
        return dict(kind='SQLITE_COLUMN_BINDING', reads={k: sorted(v) for k, v in sorted(reads.items())})


class BatchBaselineContractTests(unittest.TestCase):
    def setUp(self):
        self.f = BaselineContractFixture(self)

    def test_legacy_and_v2_columns_remain_distinct(self):
        legacy, v2 = self.f.columns(LEGACY), self.f.columns(WEEKLY)
        for equipment in ('plow', 'spreader'):
            self.assertIn(equipment + '_active_observation_count', legacy)
            self.assertNotIn(equipment + '_active_observations', legacy)
            self.assertIn(equipment + '_active_observations', v2)
            self.assertNotIn(equipment + '_active_observation_count', v2)

    def test_baseline_query_reconciles_both_real_definitions_without_writes(self):
        before = self.f.db.total_changes
        rows = self.f.baseline()
        self.assertEqual(len(rows), 3)
        self.assertEqual([r['source_week_start'] for r in rows], ['2026-01-05', '2026-01-12', '2026-01-19'])
        for r in rows:
            self.assertEqual((r['legacy_hourly_rows'], r['legacy_observations'], r['legacy_plow_observations'],
                              r['legacy_spreader_observations']), (1, 3, 2, 1))
            self.assertEqual((r['bronze_rows'], r['silver_rows'], r['header_rows'], r['valid_rows'], r['invalid_rows']), (9, 9, 1, 7, 1))
            self.assertEqual((r['observation_count'], r['plow_active_observations'], r['spreader_active_observations']), (7, 4, 2))
        self.assertEqual(self.f.db.total_changes, before)
        audit = self.f.audit(BASELINE.read_text())
        self.assertIn('plow_active_observation_count', audit['reads']['main.' + LEGACY])
        self.assertIn('plow_active_observations', audit['reads']['main.' + WEEKLY])

    def test_using_v2_names_in_legacy_cte_fails_binding(self):
        sql = BASELINE.read_text()
        for equipment in ('plow', 'spreader'):
            with self.subTest(equipment=equipment), self.assertRaises(sqlite3.OperationalError):
                self.f.audit(sql.replace(equipment + '_active_observation_count', equipment + '_active_observations'))

    def test_using_legacy_names_in_v2_cte_fails_binding(self):
        sql = BASELINE.read_text()
        for equipment in ('plow', 'spreader'):
            with self.subTest(equipment=equipment), self.assertRaises(sqlite3.OperationalError):
                self.f.audit(sql.replace(equipment + '_active_observations,', equipment + '_active_observation_count,'))
