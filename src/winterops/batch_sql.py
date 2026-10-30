"""SQL-file task graph over shared V2 transformations; no SDK or execution.

Only absent scopes may receive data DML. Full existing scopes are compared and
reused; any conflicting/partial content blocks, including for COMPLETE versions.
Serialization across *all* writers of the target tables is a deployment premise.
"""
from dataclasses import asdict
import json

from winterops.batch import Sql, Task, When
from winterops.spark_ingestion import BRONZE_TYPES, SILVER_TYPES, MANIFEST_TYPES, manifest_status_sql, sql_version_plan
from winterops.unified_gold import UnifiedGold


def text_literal(value):
    # Preserve original Windows/Unicode provenance without SQL backslash parsing.
    return "CAST(unhex('" + str(value).encode().hex() + "') AS STRING)"


class BatchSql:
    def __init__(self, request):
        self.r = request
        self.plan = sql_version_plan(request.version, request.artifact_path, request.artifact_sha256,
                                     request.expected_rows, targets=request.targets, policy=request.policy)
        self.b = request.targets.table('bronze')
        self.s = request.targets.table('silver')
        self.m = request.targets.table('manifest')
        self.bp = f"source_version_id='{request.version.version_id}'"
        self.sp = f"processing_key='{request.key}'"
        self.manifest = f'SELECT * FROM {self.m} WHERE {self.sp}'
        self.complete = f"(SELECT COUNT(*) FROM {self.m} WHERE {self.sp} AND status='COMPLETE')=1"
        self.processing = f":execution_mode='process' AND '{request.write_policy}'='append_missing' AND NOT ({self.complete})"
        # The same read_files SELECT and Silver candidate used by approved V2 SQL.
        self.incoming = self.plan['bronze_write'].split('\n', 1)[1]
        self.candidate = self.plan['silver_write'].split('\n', 1)[1]

    def artifact_guard(self):
        return self.plan['artifact_guard'].replace('MAX(length) <= 268435456', f'MAX(length) = {self.r.artifact_bytes}')

    def parameter_guard(self):
        r = self.r
        return f"""SELECT assert_true(:source_version_id='{r.version.version_id}'
 AND :processing_key='{r.key}' AND :request_sha256='{r.sha256}'
 AND :execution_mode IN ('verify','process') AND :recovery IN ('deny','resume_matching'),
 'Pinned batch parameters mismatch') AS parameter_check,
 assert_true(:execution_mode='verify' OR '{r.write_policy}'='append_missing' OR ({self.complete}),
 'This request only permits an existing COMPLETE version') AS write_policy_check"""

    def schema_guard(self):
        targets = self.r.targets
        expected = []
        for layer, types in (('bronze', BRONZE_TYPES), ('silver', SILVER_TYPES), ('manifest', MANIFEST_TYPES)):
            for position, (column, kind) in enumerate(types.items(), 1):
                expected.append(f"SELECT '{targets.table(layer).split('.')[-1]}' AS table_name, '{column}' AS column_name, '{kind}' AS data_type, {position} AS ordinal_position")
        names = ','.join("'" + name.split('.')[-1] + "'" for name in targets.names)
        return f"""WITH expected AS ({' UNION ALL '.join(expected)}), actual AS (
 SELECT table_name,column_name,data_type,ordinal_position FROM {targets.catalog}.information_schema.columns
 WHERE table_schema='{targets.schema}' AND table_name IN ({names}))
SELECT assert_true((SELECT COUNT(*) FROM actual)={len(expected)} AND COUNT(*)={len(expected)}
 AND COUNT(CASE WHEN a.data_type=e.data_type AND a.ordinal_position=e.ordinal_position THEN 1 END)={len(expected)},
 'V2 target schema contract mismatch') AS schema_check
FROM expected e LEFT JOIN actual a ON a.table_name=e.table_name AND a.column_name=e.column_name"""

    def lineage_guard(self):
        v = self.r.version
        values = dict(source_dataset=v.source.source_dataset, source_file_name=v.source.source_file_name,
                      source_url=v.source.source_url, source_file_path=v.local_path,
                      source_week_start=v.source.covered_start, source_week_end_exclusive=v.source.covered_end_exclusive,
                      retrieved_at_utc=v.retrieved_at_utc, ingested_at_utc=v.retrieved_at_utc)
        comparisons = []
        for key, value in values.items():
            expr = text_literal(value)
            if key.endswith('_utc'):
                expr = f'CAST({expr} AS TIMESTAMP)'
            elif key.startswith('source_week_'):
                expr = f'CAST({expr} AS DATE)'
            comparisons.append(f'NOT ({key} <=> {expr})')
        return f"""WITH incoming AS ({self.incoming})
SELECT assert_true(COUNT_IF({' OR '.join(comparisons)})=0,
 'Artifact provenance differs from the selected source') AS lineage_check FROM incoming"""

    def state_ctes(self, owned=False):
        r = self.r
        meta = text_literal(json.dumps(r.version.to_dict()))
        policy = text_literal(json.dumps(asdict(r.policy)))
        return f"""_incoming AS ({self.incoming}), _b AS (SELECT * FROM {self.b} WHERE {self.bp}),
_candidate AS ({self.candidate}), _s AS (SELECT * FROM {self.s} WHERE {self.sp}),
_m AS ({self.manifest}),
_b_missing AS (SELECT * FROM _incoming EXCEPT ALL SELECT * FROM _b),
_b_extra AS (SELECT * FROM _b EXCEPT ALL SELECT * FROM _incoming),
_s_missing AS (SELECT * FROM _candidate EXCEPT ALL SELECT * FROM _s),
_s_extra AS (SELECT * FROM _s EXCEPT ALL SELECT * FROM _candidate),
_snapshot AS (SELECT (SELECT COUNT(*) FROM _m) AS manifest_n,
 (SELECT COUNT(*) FROM _b) AS bronze_n, (SELECT COUNT(*) FROM _s) AS silver_n,
 (SELECT MAX(status) FROM _m) AS status, (SELECT MAX(last_successful_stage) FROM _m) AS last_stage,
 (SELECT MAX(attempts) FROM _m) AS attempts,
 (SELECT COUNT(*) FROM _b_missing)=0 AND (SELECT COUNT(*) FROM _b_extra)=0 AS bronze_equal,
 (SELECT COUNT(*) FROM _s_missing)=0 AND (SELECT COUNT(*) FROM _s_extra)=0 AS silver_equal,
 (SELECT COUNT(*) FROM _m WHERE source_version_id='{r.version.version_id}'
  AND source_file_name='{r.version.source.source_file_name}' AND source_file_sha256='{r.version.source_file_sha256}'
  AND metadata_json={meta} AND policy_json={policy} AND attempts BETWEEN 1 AND 1000
  AND (bronze_rows IS NULL OR bronze_rows={r.expected_rows})
  AND (silver_rows IS NULL OR silver_rows={r.expected_rows})
  AND ((status='PROCESSING' AND (last_successful_stage IS NULL OR last_successful_stage='PROCESSING') AND error_code IS NULL)
   OR (status='BRONZE_WRITTEN' AND last_successful_stage=status AND error_code IS NULL AND bronze_rows={r.expected_rows})
   OR (status='SILVER_WRITTEN' AND last_successful_stage=status AND error_code IS NULL
       AND bronze_rows={r.expected_rows} AND silver_rows={r.expected_rows})
   OR (status='COMPLETE' AND last_successful_stage='COMPLETE' AND error_code IS NULL
       AND bronze_rows={r.expected_rows} AND silver_rows={r.expected_rows})
   OR (status='FAILED' AND (last_successful_stage IS NULL OR last_successful_stage IN ('PROCESSING','BRONZE_WRITTEN','SILVER_WRITTEN'))
       AND error_code IS NOT NULL))) AS good_manifest),
_decision AS (SELECT *, CASE
 WHEN manifest_n>1 OR good_manifest<>manifest_n THEN 'BLOCKED_MANIFEST'
 WHEN bronze_n NOT IN (0,{r.expected_rows}) OR silver_n NOT IN (0,{r.expected_rows})
  OR (bronze_n>0 AND NOT bronze_equal) OR (silver_n>0 AND NOT silver_equal)
  OR (silver_n>0 AND bronze_n=0) THEN 'BLOCKED_CONTENT'
 WHEN status='COMPLETE' AND bronze_n={r.expected_rows} AND silver_n={r.expected_rows} THEN 'SKIP_VERIFIED'
 WHEN status='COMPLETE' THEN 'BLOCKED_COMPLETE'
 WHEN last_stage IN ('BRONZE_WRITTEN','SILVER_WRITTEN') AND bronze_n<>{r.expected_rows}
  OR last_stage='SILVER_WRITTEN' AND silver_n<>{r.expected_rows} THEN 'BLOCKED_STAGE'
 WHEN manifest_n=0 AND silver_n=0 AND {r.prior_attempts}=0 THEN 'NEW_OR_REUSE_BRONZE'
 WHEN COALESCE(attempts,0)={r.prior_attempts + int(owned)} THEN 'RESUME_MATCHING'
 ELSE 'BLOCKED_ATTEMPT' END AS decision FROM _snapshot)"""

    def state_guard(self, owned=False):
        recovery = 'TRUE' if owned else ":recovery='resume_matching'"
        return f"""WITH {self.state_ctes(owned)}
SELECT assert_true(decision IN ('SKIP_VERIFIED','NEW_OR_REUSE_BRONZE','RESUME_MATCHING')
 AND (:execution_mode='verify' OR decision<>'RESUME_MATCHING' OR {recovery}),
 'Conflicting scope, stale attempt or explicit recovery required') AS state_check,
 decision, bronze_n, silver_n FROM _decision"""

    def bronze_guard(self):
        return f"""WITH _incoming AS ({self.incoming}), _actual AS (SELECT * FROM {self.b} WHERE {self.bp}),
 _missing AS (SELECT * FROM _incoming EXCEPT ALL SELECT * FROM _actual),
 _extra AS (SELECT * FROM _actual EXCEPT ALL SELECT * FROM _incoming)
SELECT assert_true((SELECT COUNT(*) FROM _actual)={self.r.expected_rows}
 AND (SELECT COUNT(*) FROM _missing)=0 AND (SELECT COUNT(*) FROM _extra)=0,
 'Bronze lineage or multiplicity mismatch') AS bronze_check"""

    def mark(self, status):
        r = self.r
        return manifest_status_sql(r.version, status, r.prior_attempts + 1, targets=r.targets, policy=r.policy,
                                   bronze_rows=r.expected_rows if status != 'PROCESSING' else None,
                                   silver_rows=r.expected_rows if status in ('SILVER_WRITTEN', 'COMPLETE') else None,
                                   last_successful_stage=status)

    def active_guard(self, stage):
        r = self.r
        return f"""SELECT assert_true(COUNT(*)=1 AND COUNT(CASE WHEN attempts={r.prior_attempts + 1}
 AND status='{stage}' AND last_successful_stage='{stage}' AND error_code IS NULL
 AND metadata_json={text_literal(json.dumps(r.version.to_dict()))}
 AND policy_json={text_literal(json.dumps(asdict(r.policy)))} THEN 1 END)=1,
 'Batch attempt or predecessor stage mismatch') AS predecessor_check FROM {self.m} WHERE {self.sp}"""

    def quality_guard(self):
        r = self.r
        return f"""SELECT assert_true(COUNT(*)={r.expected_rows}
 AND COUNT_IF(quality_status='HEADER')={r.header_rows}
 AND COUNT_IF(quality_status='VALID')={r.valid_rows}
 AND COUNT_IF(quality_status='INVALID')={r.invalid_rows}
 AND COUNT_IF(quality_status IS NULL OR quality_status NOT IN ('HEADER','VALID','INVALID'))=0,
 'Selected quality counts mismatch') AS quality_check,
 COUNT(*) AS silver_rows, COUNT_IF(quality_status='HEADER') AS header_rows,
 COUNT_IF(quality_status='VALID') AS valid_rows, COUNT_IF(quality_status='INVALID') AS invalid_rows
FROM {self.s} WHERE {self.sp}"""

    def eligibility(self, projected=False):
        gold = UnifiedGold((self.r.selection,), targets=self.r.targets)
        if not projected:
            return gold.selection_guard()
        # Check shared Gold contracts before committing COMPLETE. Projection is
        # SELECT-only and never relaxes any data/policy/lineage/count assertion.
        columns = ','.join("'COMPLETE' AS " + k if k in ('status', 'last_successful_stage')
                           else 'CAST(NULL AS STRING) AS error_code' if k == 'error_code' else k
                           for k in MANIFEST_TYPES)
        ctes = gold.source_ctes().replace(self.m, '_batch_complete_candidate')
        return f"""WITH _batch_complete_candidate AS (SELECT {columns} FROM {self.m} WHERE {self.sp}),
{ctes} SELECT assert_true(ok=1,'Gold eligibility contract mismatch') AS gold_eligibility_check FROM _selection_gate"""


def tasks(request):
    p = BatchSql(request)
    common = (Sql(p.parameter_guard()), Sql(p.schema_guard()))
    # A full rerun must verify COMPLETE content before all data/audit writes are skipped.
    complete_checks = When(p.complete, (Sql(p.plan['postflight']), Sql(p.quality_guard()), Sql(p.eligibility())))
    preflight = Task('preflight', common + (Sql(request.landing.fingerprint_sql()),
        Sql(p.artifact_guard()),
        Sql(p.plan['input_guard']), Sql(p.lineage_guard()), complete_checks, Sql(p.state_guard())))
    bronze = Task('bronze', common + (When(p.processing, (
        Sql(p.state_guard()), Sql(p.mark('PROCESSING')),
        When(f'(SELECT COUNT(*) FROM {p.b} WHERE {p.bp})=0', (Sql(p.plan['bronze_write']),)),
        Sql(p.bronze_guard()), Sql(p.mark('BRONZE_WRITTEN')))),), ('preflight',))
    silver = Task('silver', common + (When(p.processing, (
        Sql(p.active_guard('BRONZE_WRITTEN')), Sql(p.bronze_guard()),
        # Recheck conflicts after Bronze, before any Silver data DML.
        Sql(p.state_guard(owned=True)),
        When(f'(SELECT COUNT(*) FROM {p.s} WHERE {p.sp})=0', (Sql(p.plan['silver_write']),)),
        Sql(p.plan['postflight']), Sql(p.mark('SILVER_WRITTEN')))),), ('bronze',))
    checks = (Sql(p.active_guard('SILVER_WRITTEN')), Sql(p.plan['postflight']),
              Sql(p.quality_guard()), Sql(request.landing.fingerprint_sql()),
              Sql(p.artifact_guard()), Sql(p.eligibility(projected=True)))
    quality = Task('quality', common + (When(p.processing, checks),), ('silver',))
    complete = Task('complete', common + (When(p.processing, checks + (Sql(p.mark('COMPLETE')),)),
        When(p.complete, (Sql(p.eligibility()),)),
        Sql(f"SELECT CASE WHEN {p.complete} THEN 'COMPLETE_ELIGIBLE' ELSE 'VERIFIED_NOT_PROCESSED' END AS batch_outcome")), ('quality',))
    # Best effort audit only after this attempt actually began; never downgrade
    # an existing COMPLETE manifest or mutate a preflight-conflicting scope.
    owned_failed_scope = f"""{p.sp} AND attempts={request.prior_attempts + 1}
 AND status IN ('PROCESSING','BRONZE_WRITTEN','SILVER_WRITTEN')
 AND metadata_json={text_literal(json.dumps(request.version.to_dict()))}
 AND policy_json={text_literal(json.dumps(asdict(request.policy)))}"""
    failed = Task('failure_audit', (Sql(p.parameter_guard()),
        When(f""":execution_mode='process' AND '{request.write_policy}'='append_missing' AND :batch_preflight_state='success'
 AND (SELECT COUNT(*) FROM {p.m} WHERE {owned_failed_scope})=1""", (
            Sql(f"""UPDATE {p.m} SET status='FAILED', error_code='BATCH_TASK_FAILED', updated_at_utc=current_timestamp()
WHERE {owned_failed_scope}"""),)),
        # Keep this terminal task FAILED even if audit succeeded. Otherwise a
        # successful failure-handler leaf can hide the upstream job failure.
        Sql("SELECT raise_error('WinterOps batch failed; inspect private task states before recovery') AS batch_failure")),
        ('preflight', 'bronze', 'silver', 'quality', 'complete'), 'AT_LEAST_ONE_FAILED')
    return preflight, bronze, silver, quality, complete, failed
