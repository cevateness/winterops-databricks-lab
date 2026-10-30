"""Synthetic end-to-end execution of the rendered task model in SQLite.

Control flow uses the same Sql/When graph as native rendering. Explicit dialect,
file and Delta adaptations are test-only; this is not Jobs/Spark compatibility.
Existing SQL differential suites independently verify V2 Silver classifications.
"""
from collections import Counter
from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest

from test_analytics_sql import CountIf
from test_foundation_v2_sql import adapt
import test_unified_gold as gold_fixture
from winterops.batch import BatchRequest, Sql, When, job_definition, prepare_job, synthetic_request
from winterops.batch_sql import BatchSql, tasks
from winterops.foundation import _number, _timestamp
from winterops.landing import VOLUME
from winterops.sources import SourceVersion
from winterops.spark_ingestion import BRONZE_TYPES, MANIFEST_TYPES, SILVER_TYPES


class OfflineJob:
    """Execute the generated graph; substitute files/Delta/SQL dialect only."""
    def __init__(self, db, request, original_bytes, artifact_bytes, incoming):
        self.db, self.r = db, request
        self.p = BatchSql(request)
        self.file_bytes = {request.original_csv_path: original_bytes, request.artifact_path: artifact_bytes}
        db.execute('CREATE TABLE artifact AS SELECT * FROM winterops_v2_dev_bronze WHERE 0')
        db.executemany('INSERT INTO artifact VALUES (' + ','.join('?' for _ in BRONZE_TYPES) + ')', incoming)
        db.create_function('sha2', 2, lambda value, bits: hashlib.sha256(
            value if isinstance(value, bytes) else value.encode()).hexdigest() if value is not None else None)
        db.create_function('unhex', 1, bytes.fromhex)
        db.create_function('map_value', 2, lambda text, key: json.loads(text).get(key))
        db.create_function('finite_number', 1, _number)
        db.create_function('naive_timestamp', 1, lambda value: _timestamp(value).isoformat(sep=' ') if _timestamp(value) else None)
        db.create_function('isnan', 1, lambda value: False)
        db.create_function('regexp', 2, lambda pattern, value: value is not None and bool(re.search(pattern, value)))
        db.create_function('concat_ws', -1, lambda sep, *values: sep.join(v for v in values if v is not None))
        db.create_aggregate('count_if', 1, CountIf)
        db.execute("ATTACH DATABASE ':memory:' AS information_schema")
        db.execute('CREATE TABLE information_schema.columns (table_schema,table_name,column_name,data_type,ordinal_position)')
        for layer, types in (('bronze', BRONZE_TYPES), ('silver', SILVER_TYPES), ('manifest', MANIFEST_TYPES)):
            db.executemany('INSERT INTO information_schema.columns VALUES (?,?,?,?,?)',
                           # Model the documented zero-based Databricks contract.
                           [('default', 'winterops_v2_dev_' + layer, k, v, i) for i, (k, v) in enumerate(types.items())])

    def dialect(self, sql):
        sql = sql.replace(self.p.incoming, 'SELECT * FROM artifact')
        for path, data in self.file_bytes.items():
            sql = sql.replace(f"read_files('{path}', format => 'binaryFile')",
                              f"(SELECT X'{data.hex()}' AS content, {len(data)} AS length)")
        sql = re.sub(r'\bbronze\b', 'winterops_v2_dev_bronze', adapt(sql))
        sql = gold_fixture.sqlite_sql(sql).replace('workspace.information_schema.', 'information_schema.')
        sql = sql.replace('<=>', 'IS').replace(' AS STRING)', ' AS TEXT)')
        sql = sql.replace(' AS TIMESTAMP)', ' AS TEXT)').replace(' AS DATE)', ' AS TEXT)')
        sql = sql.replace('current_timestamp()', 'CURRENT_TIMESTAMP')
        return sql

    def execute(self, sql, params):
        sql = self.dialect(sql)
        write = re.fullmatch(r'INSERT INTO (\w+) REPLACE WHERE ([^\n]+)\n(.*)', sql, re.S)
        if write:
            # One scoped Delta statement is atomic; the entire job is not.
            with self.db:
                self.db.execute('DELETE FROM ' + write[1] + ' WHERE ' + write[2], params)
                self.db.execute('INSERT INTO ' + write[1] + ' ' + write[3], params)
            return []
        cursor = self.db.execute(sql, params)
        if cursor.description:
            return [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]
        self.db.commit()
        return []

    def run(self, *, mode='process', recovery='deny', after_sql=None, overrides=None):
        r = self.r
        params = dict(source_version_id=r.version.version_id, processing_key=r.key,
                      request_sha256=r.sha256, execution_mode=mode, recovery=recovery,
                      batch_preflight_state='upstream_failed')
        params.update(overrides or {})
        states, outputs = {}, {}
        def walk(steps):
            result = []
            for step in steps:
                if isinstance(step, When):
                    condition = self.execute('SELECT (' + step.predicate + ') AS take_branch', params)[0]['take_branch']
                    if condition:
                        result = walk(step.steps)
                else:
                    result = self.execute(step.text, params)
                    if after_sql:
                        after_sql(step.text)
            return result
        error = None
        for task in tasks(r):
            if task.run_if == 'AT_LEAST_ONE_FAILED':
                if error is None:
                    states[task.key] = 'excluded'
                    continue
            elif error is not None:
                states[task.key] = 'upstream_failed'
                continue
            try:
                outputs[task.key] = walk(task.steps)
                states[task.key] = 'success'
            except Exception as exc:
                states[task.key] = 'failed'
                error = exc
            if task.key == 'preflight':
                params['batch_preflight_state'] = states[task.key]
        return states, outputs, error


class BatchWorkflowTests(unittest.TestCase):
    def setUp(self):
        fixture = gold_fixture.UnifiedGoldTests(methodName='runTest')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.db, self.root = fixture.db, fixture.root
        row = self.db.execute('SELECT metadata_json FROM winterops_v2_dev_manifest ORDER BY source_file_name').fetchone()
        version = SourceVersion.from_dict(json.loads(row[0]))
        incoming = self.db.execute('SELECT * FROM winterops_v2_dev_bronze WHERE source_version_id=? ORDER BY source_record_number',
                                   (version.version_id,)).fetchall()
        payload = ''.join(json.dumps(dict(zip(BRONZE_TYPES, row))) + '\n' for row in incoming).encode()
        encoded = gzip.compress(payload, mtime=0)
        sha = hashlib.sha256(encoded).hexdigest()
        selection = fixture.selections[0]
        self.r = BatchRequest(version, f'{VOLUME}/foundation_v2_dev/{version.version_id}/{sha}/bronze.jsonl.gz',
                              sha, len(encoded), 9, 1, 7, 1, selection.original_csv_volume_path, write_policy='append_missing')
        self.job = OfflineJob(self.db, self.r, Path(version.local_path).read_bytes(), encoded, incoming)
        self.outer_before = self.other_scopes()

    def other_scopes(self):
        return {layer: Counter(self.db.execute('SELECT * FROM winterops_v2_dev_' + layer +
                (' WHERE source_version_id<>?' if layer == 'bronze' else ' WHERE processing_key<>?'),
                (self.r.version.version_id if layer == 'bronze' else self.r.key,)).fetchall())
                for layer in ('bronze', 'silver', 'manifest')}

    def empty_selected(self):
        for layer, predicate, key in (('bronze', 'source_version_id', self.r.version.version_id),
                                      ('silver', 'processing_key', self.r.key), ('manifest', 'processing_key', self.r.key)):
            self.db.execute('DELETE FROM winterops_v2_dev_' + layer + ' WHERE ' + predicate + '=?', (key,))
        self.db.commit()

    def manifest(self):
        row = self.db.execute('SELECT * FROM winterops_v2_dev_manifest WHERE processing_key=?', (self.r.key,)).fetchone()
        return dict(zip(MANIFEST_TYPES, row)) if row else None

    def assert_ok(self, result):
        states, outputs, error = result
        self.assertIsNone(error, str(error))
        self.assertEqual([states[k] for k in ('preflight', 'bronze', 'silver', 'quality', 'complete')], ['success'] * 5)
        self.assertEqual(states['failure_audit'], 'excluded')
        self.assertEqual(self.other_scopes(), self.outer_before)
        return outputs

    def test_end_to_end_success_preserves_all_records_and_other_weeks(self):
        self.empty_selected()
        outputs = self.assert_ok(self.job.run())
        self.assertEqual(outputs['complete'], [{'batch_outcome': 'COMPLETE_ELIGIBLE'}])
        self.assertEqual((self.manifest()['status'], self.manifest()['attempts']), ('COMPLETE', 1))
        rows = self.db.execute('SELECT raw_record_json FROM winterops_v2_dev_bronze WHERE source_version_id=?',
                               (self.r.version.version_id,)).fetchall()
        self.assertEqual(len(rows), 9)
        self.assertGreater(max(Counter(rows).values()), 1)

    def test_complete_rerun_performs_no_data_or_manifest_writes(self):
        before = self.db.total_changes
        self.assert_ok(self.job.run())
        self.assertEqual(self.db.total_changes, before)

    def test_new_verify_mode_performs_no_writes_and_does_not_claim_complete(self):
        self.empty_selected()
        before = self.db.total_changes
        out = self.assert_ok(self.job.run(mode='verify'))
        self.assertEqual(out['complete'], [{'batch_outcome': 'VERIFIED_NOT_PROCESSED'}])
        self.assertEqual(self.db.total_changes, before)
        self.assertIsNone(self.manifest())

    def test_invalid_runtime_parameters_stop_without_audit_mutation(self):
        for override in ({'source_version_id': '0' * 64}, {'processing_key': '0' * 64},
                         {'request_sha256': '0' * 64}, {'execution_mode': 'apply'}, {'recovery': 'repair'}):
            before = self.db.total_changes
            states, _, error = self.job.run(overrides=override)
            self.assertIsNotNone(error)
            self.assertEqual(states['preflight'], 'failed')
            self.assertEqual(states['bronze'], 'upstream_failed')
            self.assertEqual(self.db.total_changes, before)

    def test_changed_artifact_stops_before_writes(self):
        self.job.file_bytes[self.r.artifact_path] += b'changed'
        before = self.db.total_changes
        self.assertIsNotNone(self.job.run()[2])
        self.assertEqual(self.db.total_changes, before)

    def test_wrong_acquisition_lineage_stops_even_when_payloads_match(self):
        self.db.execute("UPDATE artifact SET source_file_path='WRONG_PROVENANCE'")
        before = self.db.total_changes
        self.assertIsNotNone(self.job.run()[2])
        self.assertEqual(self.db.total_changes, before)

    def test_complete_corruption_blocks_and_is_never_repaired(self):
        self.db.execute('UPDATE winterops_v2_dev_silver SET payload_occurrences=999 WHERE processing_key=?', (self.r.key,))
        before = self.db.total_changes
        self.assertIsNotNone(self.job.run()[2])
        self.assertEqual(self.db.total_changes, before)
        self.assertEqual(self.manifest()['status'], 'COMPLETE')

    def test_partial_failure_propagates_and_records_sanitized_audit(self):
        self.empty_selected()
        def fail(sql):
            if sql == BatchSql(self.r).plan['silver_write']:
                raise ValueError('DO_NOT_PERSIST_SYNTHETIC_RECORD_OR_EXCEPTION_TEXT')
        states, _, error = self.job.run(after_sql=fail)
        self.assertIsNotNone(error)
        self.assertEqual(states['silver'], 'failed')
        self.assertEqual(states['quality'], 'upstream_failed')
        self.assertEqual(states['failure_audit'], 'failed')
        self.assertEqual(self.manifest()['status'], 'FAILED')
        self.assertEqual(self.manifest()['last_successful_stage'], 'BRONZE_WRITTEN')
        self.assertEqual(self.manifest()['error_code'], 'BATCH_TASK_FAILED')
        # A default rerun cannot silently adopt the interrupted attempt.
        before = self.db.total_changes
        self.assertIsNotNone(self.job.run()[2])
        self.assertEqual(self.db.total_changes, before)
        resumed = replace(self.r, prior_attempts=1)
        self.job.r, self.job.p = resumed, BatchSql(resumed)
        self.assertIsNotNone(self.job.run(recovery='deny')[2])
        data_before = {layer: Counter(self.db.execute('SELECT * FROM winterops_v2_dev_' + layer).fetchall())
                       for layer in ('bronze', 'silver')}
        executed = []
        self.assert_ok(self.job.run(recovery='resume_matching', after_sql=executed.append))
        self.assertNotIn(BatchSql(resumed).plan['bronze_write'], executed)
        self.assertNotIn(BatchSql(resumed).plan['silver_write'], executed)
        self.assertEqual(self.manifest()['attempts'], 2)
        for layer in data_before:
            self.assertEqual(Counter(self.db.execute('SELECT * FROM winterops_v2_dev_' + layer).fetchall()), data_before[layer])

    def test_hard_stop_after_bronze_commit_is_explicitly_recoverable(self):
        self.empty_selected()
        def hard_stop(sql):
            if sql == BatchSql(self.r).plan['bronze_write']:
                raise SystemExit('synthetic crash before audit checkpoint')
        with self.assertRaises(SystemExit):
            self.job.run(after_sql=hard_stop)
        self.assertEqual(self.manifest()['status'], 'PROCESSING')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM winterops_v2_dev_silver WHERE processing_key=?', (self.r.key,)).fetchone()[0], 0)
        resumed = replace(self.r, prior_attempts=1)
        self.job.r, self.job.p = resumed, BatchSql(resumed)
        bronze_before = Counter(self.db.execute('SELECT * FROM winterops_v2_dev_bronze').fetchall())
        self.assert_ok(self.job.run(recovery='resume_matching'))
        self.assertEqual(Counter(self.db.execute('SELECT * FROM winterops_v2_dev_bronze').fetchall()), bronze_before)

    def test_quality_expectation_failure_never_marks_complete(self):
        self.empty_selected()
        wrong = replace(self.r, valid_rows=6, invalid_rows=2)
        self.job.r, self.job.p = wrong, BatchSql(wrong)
        states, _, error = self.job.run()
        self.assertIsNotNone(error)
        self.assertEqual(states['quality'], 'failed')
        self.assertEqual(states['complete'], 'upstream_failed')
        self.assertEqual(self.manifest()['status'], 'FAILED')

    def test_preflight_failure_does_not_claim_someone_elses_partial_attempt(self):
        self.db.execute("UPDATE winterops_v2_dev_manifest SET status='BRONZE_WRITTEN',last_successful_stage='BRONZE_WRITTEN',silver_rows=NULL WHERE processing_key=?", (self.r.key,))
        before = self.db.total_changes
        self.assertIsNotNone(self.job.run()[2])
        self.assertEqual(self.db.total_changes, before)
        self.assertEqual(self.manifest()['status'], 'BRONZE_WRITTEN')

    def test_matching_orphan_requires_explicit_recovery(self):
        self.db.execute('DELETE FROM winterops_v2_dev_manifest WHERE processing_key=?', (self.r.key,))
        before = self.db.total_changes
        self.assertIsNotNone(self.job.run()[2])
        self.assertEqual(self.db.total_changes, before)
        self.assert_ok(self.job.run(recovery='resume_matching'))

    def test_partial_data_conflict_is_blocked_even_with_resume(self):
        self.empty_selected()
        self.db.execute('INSERT INTO winterops_v2_dev_bronze SELECT * FROM artifact LIMIT 1')
        before = self.db.total_changes
        self.assertIsNotNone(self.job.run(recovery='resume_matching')[2])
        self.assertEqual(self.db.total_changes, before)
        self.assertIsNone(self.manifest())

    def test_manifest_policy_and_schema_conflicts_stop_without_writes(self):
        self.db.execute("UPDATE winterops_v2_dev_manifest SET policy_json='{}' WHERE processing_key=?", (self.r.key,))
        before = self.db.total_changes
        self.assertIsNotNone(self.job.run()[2])
        self.assertEqual(self.db.total_changes, before)
        self.db.execute("UPDATE information_schema.columns SET data_type='TIMESTAMP' WHERE column_name='event_time_unzoned'")
        before = self.db.total_changes
        self.assertIsNotNone(self.job.run()[2])
        self.assertEqual(self.db.total_changes, before)

    def test_duplicate_manifest_key_is_never_adopted(self):
        self.db.execute('INSERT INTO winterops_v2_dev_manifest SELECT * FROM winterops_v2_dev_manifest WHERE processing_key=?', (self.r.key,))
        before = self.db.total_changes
        self.assertIsNotNone(self.job.run(recovery='resume_matching')[2])
        self.assertEqual(self.db.total_changes, before)

    def test_column_order_mismatch_stops_before_positional_inserts(self):
        self.empty_selected()
        self.db.execute("UPDATE information_schema.columns SET ordinal_position=999 WHERE column_name='source_file_name'")
        before = self.db.total_changes
        self.assertIsNotNone(self.job.run()[2])
        self.assertEqual(self.db.total_changes, before)

    def test_documented_zero_based_schema_positions_pass(self):
        # Independent fixed anchors from the real V2 schema/API contract.
        anchors = [('bronze', 'source_version_id', 0), ('bronze', 'record_sha256', 15),
                   ('silver', 'event_time_unzoned', 18), ('silver', 'quality_warnings', 29),
                   ('manifest', 'processing_key', 0), ('manifest', 'updated_at_utc', 12)]
        for layer, column, expected in anchors:
            row = self.db.execute('SELECT ordinal_position FROM information_schema.columns '
                                  'WHERE table_name=? AND column_name=?',
                                  ('winterops_v2_dev_' + layer, column)).fetchone()
            self.assertEqual(row[0], expected)
        self.assertEqual(self.job.execute(BatchSql(self.r).schema_guard(), {}), [{'schema_check': None}])

    def test_one_based_positions_are_rejected_without_writes(self):
        self.empty_selected()
        self.db.execute('UPDATE information_schema.columns SET ordinal_position=ordinal_position+1')
        before = self.db.total_changes
        states, _, error = self.job.run()
        self.assertIsNotNone(error)
        self.assertEqual(states['preflight'], 'failed')
        self.assertEqual(self.db.total_changes, before)

    def test_new_explicit_policy_reuses_bronze_and_preserves_existing_processing(self):
        previous = {layer: Counter(self.db.execute('SELECT * FROM winterops_v2_dev_' + layer).fetchall())
                    for layer in ('bronze', 'silver', 'manifest')}
        changed = replace(self.r, policy=replace(self.r.policy, review_lon_max=-82.0))
        self.job.r, self.job.p = changed, BatchSql(changed)
        executed = []
        states, _, error = self.job.run(after_sql=executed.append)
        self.assertIsNone(error, str(error))
        self.assertEqual(states['complete'], 'success')
        self.assertNotIn(BatchSql(changed).plan['bronze_write'], executed)
        self.assertEqual(Counter(self.db.execute('SELECT * FROM winterops_v2_dev_bronze').fetchall()), previous['bronze'])
        for layer in ('silver', 'manifest'):
            unchanged = self.db.execute('SELECT * FROM winterops_v2_dev_' + layer + ' WHERE processing_key<>?', (changed.key,)).fetchall()
            self.assertEqual(Counter(unchanged), previous[layer])

    def test_failure_after_complete_commit_does_not_downgrade_manifest(self):
        self.empty_selected()
        def fail(sql):
            if sql == BatchSql(self.r).mark('COMPLETE'):
                raise ValueError('synthetic late task failure')
        states, _, error = self.job.run(after_sql=fail)
        self.assertIsNotNone(error)
        self.assertEqual(states['complete'], 'failed')
        self.assertEqual(states['failure_audit'], 'failed')
        self.assertEqual(self.manifest()['status'], 'COMPLETE')
        before = self.db.total_changes
        self.assert_ok(self.job.run())
        self.assertEqual(self.db.total_changes, before)

    def test_complete_only_policy_cannot_be_overridden_into_new_writes(self):
        safe_request = replace(self.r, write_policy='complete_only')
        self.job.r, self.job.p = safe_request, BatchSql(safe_request)
        before = self.db.total_changes
        self.assert_ok(self.job.run())
        self.assertEqual(self.db.total_changes, before)
        self.empty_selected()
        before = self.db.total_changes
        self.assertIsNotNone(self.job.run()[2])
        self.assertEqual(self.db.total_changes, before)

    def test_verify_failure_does_not_even_submit_audit_dml(self):
        self.job.file_bytes[self.r.original_csv_path] = b'changed'
        executed = []
        self.assertIsNotNone(self.job.run(mode='verify', after_sql=executed.append)[2])
        self.assertFalse(any(sql.startswith(('INSERT', 'UPDATE', 'DELETE')) for sql in executed))


class BatchContractTests(unittest.TestCase):
    def test_committed_declarative_example_matches_generator(self):
        path = Path(__file__).resolve().parents[1] / 'jobs/on_demand_batch_v1.job.json'
        self.assertEqual(json.loads(path.read_text(encoding='utf-8')),
                         job_definition(synthetic_request(), '0' * 16, '/Workspace/Shared/winterops_batch_EXAMPLE'))

    def test_invalid_requests_are_rejected_before_rendering(self):
        r = synthetic_request()
        for fields in ({'expected_rows': True}, {'invalid_rows': 2}, {'prior_attempts': -1},
                       {'artifact_sha256': "' OR 1=1"}, {'artifact_path': r.artifact_path + '/..'},
                       {'original_csv_path': '/Volumes/other/file.csv'}, {'artifact_bytes': 0}):
            with self.assertRaises((ValueError, TypeError)):
                replace(r, **fields)
        self.assertEqual(BatchRequest.from_dict(r.to_dict()), r)

    def test_jobs_definition_is_bounded_sequential_and_uses_existing_warehouse(self):
        r = synthetic_request()
        job = job_definition(r, '0' * 16, '/Workspace/Shared/winterops_batch_EXAMPLE')
        self.assertEqual(job['max_concurrent_runs'], 1)
        self.assertFalse(job['queue']['enabled'])
        self.assertEqual(job['timeout_seconds'], 600)
        self.assertNotIn('schedule', job)
        self.assertEqual(len(job['tasks']), 6)
        for task in job['tasks']:
            self.assertEqual(task['max_retries'], 0)
            self.assertFalse(task['retry_on_timeout'])
            self.assertEqual(task['timeout_seconds'], 90)
            self.assertEqual(task['sql_task']['warehouse_id'], '0' * 16)
            self.assertNotIn('new_cluster', task)
        self.assertEqual(job['tasks'][-1]['run_if'], 'AT_LEAST_ONE_FAILED')
        self.assertEqual(job['tasks'][-1]['sql_task']['parameters']['batch_preflight_state'], '{{tasks.preflight.result_state}}')
        self.assertEqual({p['name']: p['default'] for p in job['parameters']}['execution_mode'], 'verify')

    def test_rendering_contains_no_ddl_gold_publication_or_acquisition(self):
        r = synthetic_request()
        rendered = '\n'.join(t.render() for t in tasks(r))
        self.assertNotRegex(rendered, r'(?i)\b(CREATE|ALTER|DROP|GRANT|TRUNCATE|COPY INTO)\b')
        self.assertNotIn('CREATE OR REPLACE', rendered)
        self.assertIn('EXCEPT ALL', rendered)
        self.assertIn('TIMESTAMP_NTZ', rendered)
        self.assertIn('IF :execution_mode=', rendered)

    def test_private_package_is_immutable_and_rejects_git_output(self):
        r = synthetic_request()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review = prepare_job(r, root, '0' * 16, '/Workspace/Shared/winterops_batch_EXAMPLE')
            self.assertEqual(review, prepare_job(r, root, '0' * 16, '/Workspace/Shared/winterops_batch_EXAMPLE'))
            (root / r.sha256 / 'bronze.sql').write_text('modified', encoding='utf-8')
            with self.assertRaises(ValueError):
                prepare_job(r, root, '0' * 16, '/Workspace/Shared/winterops_batch_EXAMPLE')
            with self.assertRaises(ValueError):
                prepare_job(r, Path(__file__).resolve().parents[1], '0' * 16, '/Workspace/Shared/winterops_batch_EXAMPLE')
