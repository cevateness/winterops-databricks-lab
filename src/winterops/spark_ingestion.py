"""Isolated V2 Delta adapter. Rendering/importing is offline; writes are opt-in.

No old tables/views are targets. Requires separately approved, serialized Spark
execution against three pre-created development tables. No implicit DDL, jobs,
configuration changes, raw previews, or automatic retries.
"""
from dataclasses import asdict, dataclass
from importlib.resources import files
import json
from pathlib import Path
import re
from string import Template

from winterops.foundation import NUMBER_PATTERN, PIPELINE_VERSION, QualityPolicy, processing_key
from winterops.sources import fingerprint, utc_now

BRONZE_TYPES = {
    'source_version_id':'STRING','source_dataset':'STRING','source_file_name':'STRING','source_url':'STRING',
    'source_file_path':'STRING','source_file_sha256':'STRING','source_week_start':'DATE',
    'source_week_end_exclusive':'DATE','retrieved_at_utc':'TIMESTAMP','ingested_at_utc':'TIMESTAMP',
    'source_record_number':'BIGINT','source_line_end':'BIGINT','csv_parse_issues':'STRING',
    'raw_values_json':'STRING','raw_record_json':'STRING','record_sha256':'STRING',
}
AUDIT_TYPES = {k:v for k,v in BRONZE_TYPES.items() if k not in {'raw_values_json','raw_record_json'}}
SILVER_TYPES = {**AUDIT_TYPES,'processing_key':'STRING','pipeline_version':'STRING','quality_policy_sha256':'STRING',
    'truck_id':'STRING','event_time_unzoned':'TIMESTAMP_NTZ','latitude':'DOUBLE','longitude':'DOUBLE',
    'plow_active':'BOOLEAN','spreader_active':'BOOLEAN','engine_active':'BOOLEAN','payload_occurrences':'BIGINT',
    'has_repeated_payload':'BOOLEAN','is_repeated_header':'BOOLEAN','quality_status':'STRING',
    'quality_issues':'STRING','quality_warnings':'STRING'}
MANIFEST_TYPES = {'processing_key':'STRING','source_version_id':'STRING','source_file_name':'STRING',
    'source_file_sha256':'STRING','metadata_json':'STRING','policy_json':'STRING',
    'status':'STRING','last_successful_stage':'STRING','attempts':'BIGINT',
    'bronze_rows':'BIGINT','silver_rows':'BIGINT','error_code':'STRING','updated_at_utc':'TIMESTAMP'}


@dataclass(frozen=True)
class DevelopmentTargets:
    catalog: str = 'workspace'
    schema: str = 'default'

    def __post_init__(self):
        if any(not re.fullmatch('[a-z][a-z0-9_]*',v) for v in (self.catalog,self.schema)):
            raise ValueError('Unsafe development namespace')

    def table(self, layer):
        if layer not in {'bronze','silver','manifest'}: raise ValueError('Unknown development layer')
        return f'{self.catalog}.{self.schema}.winterops_v2_dev_{layer}'

    @property
    def names(self):
        return tuple(self.table(layer) for layer in ('bronze','silver','manifest'))

    def creation_sql(self):
        # Fail if names exist. Never replace an unrelated/pre-existing object.
        return tuple('CREATE TABLE '+self.table(layer)+' (\n'+',\n'.join(f'  {name} {kind}' for name,kind in types.items())+'\n) USING DELTA'
            for layer,types in [('bronze',BRONZE_TYPES),('silver',SILVER_TYPES),('manifest',MANIFEST_TYPES)])


def silver_sql(targets, version, policy=QualityPolicy()):
    def boolean(key):
        return f"CASE upper(trim(try_element_at(payload, '{key}'))) WHEN 'TRUE' THEN TRUE WHEN 'FALSE' THEN FALSE END"
    def number(key):
        raw=f"try_element_at(payload, '{key}')"
        value=f'try_cast({raw} AS DOUBLE)'
        return f"CASE WHEN trim({raw}) RLIKE '^{NUMBER_PATTERN}$' AND abs({value}) <= 1.7976931348623157E308 THEN {value} END"
    return Template(files('winterops').joinpath('sql','v2_silver.sql').read_text(encoding='utf-8')).substitute(
        bronze_table=targets.table('bronze'),version_id=version.version_id,
        audit_fields=', '.join(AUDIT_TYPES),plow_boolean=boolean('Plow status'),
        spreader_boolean=boolean('Spreader status'),engine_boolean=boolean('Engine status'),
        latitude_number=number('Latitude'),longitude_number=number('Longitude'),
        processing_key=processing_key(version,policy),pipeline_version=PIPELINE_VERSION,policy_hash=policy.policy_sha256,
        lat_min=policy.review_lat_min,lat_max=policy.review_lat_max,lon_min=policy.review_lon_min,lon_max=policy.review_lon_max).strip()


def _same_rows(left, right):
    # Full multiplicity comparison, never merely COUNT(*) or payload de-duplication.
    columns=left.columns
    if set(columns)!=set(right.columns): return False
    right=right.select(*columns)
    return left.exceptAll(right).limit(1).count()==0 and right.exceptAll(left).limit(1).count()==0


def sql_version_plan(version, artifact_path, artifact_sha256, expected_rows, *,
                     targets=DevelopmentTargets(), policy=QualityPolicy()):
    """Equivalent reviewable SQL-warehouse route; returns text, never executes.

    A caller must inspect manifest/content before choosing writes. Full reruns of
    these DML statements are content-idempotent but still create Delta commits;
    a verified COMPLETE version should skip them. Never use COPY force reruns.
    """
    if (not re.fullmatch(r'/Volumes/[a-z][a-z0-9_]*/[a-z][a-z0-9_]*/[a-z][a-z0-9_]*/[A-Za-z0-9_./-]+/bronze[.]jsonl([.]gz)?',artifact_path)
            or '..' in artifact_path.split('/') or not re.fullmatch('[0-9a-f]{64}',artifact_sha256)
            or type(expected_rows) is not int or not 1<=expected_rows<=500000):
        raise ValueError('Exact bounded immutable Volume artifact required')
    schema=', '.join(k+' '+v for k,v in BRONZE_TYPES.items())
    missing=' OR '.join(name+' IS NULL' for name in BRONZE_TYPES)
    incoming=f"SELECT {', '.join(BRONZE_TYPES)} FROM read_files('{artifact_path}', format => 'json', schema => '{schema}', mode => 'FAILFAST')"
    vp=f"source_version_id = '{version.version_id}'"
    rp=f"processing_key = '{processing_key(version,policy)}'"
    selected=f'SELECT * FROM {targets.table("bronze")} WHERE {vp}'
    candidate=silver_sql(targets,version,policy)
    return {
        'artifact_guard':f"""SELECT assert_true(COUNT(*) = 1 AND MIN(sha2(content,256)) = '{artifact_sha256}'
 AND MAX(length) <= 268435456, 'V2 artifact fingerprint or size mismatch') AS artifact_check
FROM read_files('{artifact_path}', format => 'binaryFile')""",
        'input_guard':f"""WITH incoming AS ({incoming})
SELECT assert_true(COUNT(*) = {expected_rows} AND COUNT(DISTINCT source_record_number) = {expected_rows}
 AND MIN(source_record_number) = 1 AND MAX(source_record_number) = {expected_rows}
 AND COUNT_IF(NOT (source_version_id <=> '{version.version_id}')
  OR NOT (source_file_sha256 <=> '{version.source_file_sha256}')
  OR {missing} OR source_line_end < source_record_number + 1
  OR sha2(raw_record_json,256) <> record_sha256) = 0,
 'V2 input scope, record identity or content mismatch') AS input_check FROM incoming""",
        'bronze_write':f'INSERT INTO {targets.table("bronze")} REPLACE WHERE {vp}\n{incoming}',
        'silver_write':f'INSERT INTO {targets.table("silver")} REPLACE WHERE {rp}\n{candidate}',
        'postflight':f"""WITH _expected_bronze AS ({incoming}), _actual_bronze AS ({selected}),
_expected_silver AS ({candidate}), _actual_silver AS (SELECT * FROM {targets.table('silver')} WHERE {rp}),
_b1 AS (SELECT * FROM _expected_bronze EXCEPT ALL SELECT * FROM _actual_bronze),
_b2 AS (SELECT * FROM _actual_bronze EXCEPT ALL SELECT * FROM _expected_bronze),
_s1 AS (SELECT * FROM _expected_silver EXCEPT ALL SELECT * FROM _actual_silver),
_s2 AS (SELECT * FROM _actual_silver EXCEPT ALL SELECT * FROM _expected_silver)
SELECT assert_true((SELECT COUNT(*) FROM _actual_bronze) = {expected_rows}
 AND (SELECT COUNT(*) FROM _actual_silver) = {expected_rows}
 AND (SELECT COUNT(*) FROM _b1) = 0 AND (SELECT COUNT(*) FROM _b2) = 0
 AND (SELECT COUNT(*) FROM _s1) = 0 AND (SELECT COUNT(*) FROM _s2) = 0,
 'V2 persisted row multiplicity or lineage mismatch') AS persisted_check,
 COUNT(*) AS silver_rows, COUNT_IF(quality_status='HEADER') AS header_rows,
 COUNT_IF(quality_status='VALID') AS valid_rows, COUNT_IF(quality_status='INVALID') AS invalid_rows
FROM _actual_silver""",
    }


def manifest_status_sql(version, status, attempts, *, targets=DevelopmentTargets(), policy=QualityPolicy(),
                        bronze_rows=None, silver_rows=None, last_successful_stage=None, error_code=None):
    """Explicit single-key audit update for an approved SQL execution controller."""
    statuses={'PROCESSING','BRONZE_WRITTEN','SILVER_WRITTEN','COMPLETE','FAILED'}
    if (status not in statuses or type(attempts) is not int or not 1<=attempts<=1000
            or last_successful_stage not in statuses|{None}
            or any(value is not None and (type(value) is not int or not 0<=value<=500000) for value in (bronze_rows,silver_rows))
            or error_code is not None and not re.fullmatch('[A-Z][A-Z0-9_]{0,80}',error_code)):
        raise ValueError('Invalid manifest event')
    def literal(value):
        if value is None: return 'NULL'
        if isinstance(value,int):
            if not 0<=value<=500000: raise ValueError('Unbounded manifest count')
            return str(value)
        # UTF-8 hex avoids SQL backslash/quote interpretation corrupting JSON
        # Windows paths or Unicode provenance. This is escaping, not secrecy.
        return "CAST(unhex('"+str(value).encode('utf-8').hex()+"') AS STRING)"
    key=processing_key(version,policy)
    values=[key,version.version_id,version.source.source_file_name,version.source_file_sha256,
        json.dumps(version.to_dict()),json.dumps(asdict(policy)),status,last_successful_stage,attempts,
        bronze_rows,silver_rows,error_code]
    return f"INSERT INTO {targets.table('manifest')} REPLACE WHERE processing_key = '{key}'\nSELECT "+', '.join(map(literal,values))+', current_timestamp()'


def _write_scoped(frame, target, predicate):
    frame.write.format('delta').mode('overwrite').option('replaceWhere',predicate).saveAsTable(target)


def process_spark(spark, version, artifact_path, artifact_sha256, expected_rows, *,
                  targets=DevelopmentTargets(), policy=QualityPolicy(), approved_targets=(), repair=False):
    """One version/quality-policy attempt on existing isolated dev tables only.

    artifact_path is an immutable Volume NDJSON export made by export_bronze.
    The caller serializes execution. Delta table commits are atomic individually,
    not across Bronze/Silver/manifest. A later explicitly approved invocation can
    reconcile committed stages and resume after a manifest lag/crash.
    """
    if tuple(approved_targets)!=targets.names:
        raise PermissionError('Separate explicit approval of all exact development targets required')
    if (not str(artifact_path).startswith('/Volumes/') or not str(artifact_path).endswith(('/bronze.jsonl','/bronze.jsonl.gz'))
            or not re.fullmatch('[0-9a-f]{64}',artifact_sha256)
            or type(expected_rows) is not int or not 1<=expected_rows<=500000):
        raise ValueError('Bounded immutable Volume artifact required')
    if fingerprint(Path(artifact_path))!=artifact_sha256:
        raise ValueError('ARTIFACT_BYTES_CHANGED')
    for layer,types in [('bronze',BRONZE_TYPES),('silver',SILVER_TYPES),('manifest',MANIFEST_TYPES)]:
        actual={f.name:f.dataType.simpleString().upper() for f in spark.table(targets.table(layer)).schema.fields}
        normalized={k:('BIGINT' if v=='LONG' else v) for k,v in actual.items()}
        if normalized!=types:
            raise ValueError('DEVELOPMENT_TARGET_SCHEMA_MISMATCH')
    # PySpark is loaded only during an explicitly approved runtime invocation.
    from pyspark.sql import functions as F
    key=processing_key(version,policy)
    version_pred=f"source_version_id = '{version.version_id}'"
    run_pred=f"processing_key = '{key}'"
    incoming=spark.read.schema(', '.join(k+' '+v for k,v in BRONZE_TYPES.items())).option('mode','FAILFAST').json(str(artifact_path))
    missing=F.lit(False)
    for column in BRONZE_TYPES:
        missing=missing | F.col(column).isNull()
    if (incoming.count()!=expected_rows or incoming.filter(
        ~F.col('source_version_id').eqNullSafe(version.version_id)
        | ~F.col('source_file_sha256').eqNullSafe(version.source_file_sha256) | missing
        | (F.col('source_line_end') < F.col('source_record_number')+1)
        | ~F.sha2(F.col('raw_record_json'),256).eqNullSafe(F.col('record_sha256'))).limit(1).count()
        or incoming.select('source_record_number').distinct().count()!=expected_rows
        or incoming.filter(F.col('source_record_number').isNull() | ~F.col('source_record_number').between(1,expected_rows)).limit(1).count()):
        raise ValueError('ARTIFACT_SCOPE_OR_MULTIPLICITY_MISMATCH')
    prior=spark.table(targets.table('manifest')).where(run_pred).limit(2).collect()
    if len(prior)>1: raise ValueError('DUPLICATE_MANIFEST_KEY')
    prior=prior[0].asDict() if prior else None
    state=dict(processing_key=key,source_version_id=version.version_id,source_file_name=version.source.source_file_name,
        source_file_sha256=version.source_file_sha256,metadata_json=json.dumps(version.to_dict()),
        policy_json=json.dumps(asdict(policy)),status='PROCESSING',last_successful_stage=None,
        attempts=(prior['attempts'] if prior else 0)+1,bronze_rows=None,silver_rows=None,error_code=None,updated_at_utc=None)
    def mark(status):
        state['status']=status
        if status!='FAILED': state['last_successful_stage']=status
        # Build timestamp explicitly to avoid driver/session timezone assumptions.
        values={**state,'updated_at_utc':utc_now()}
        schema=', '.join(k+' '+('STRING' if k=='updated_at_utc' else v) for k,v in MANIFEST_TYPES.items())
        frame=spark.createDataFrame([values],schema).withColumn('updated_at_utc',F.col('updated_at_utc').cast('timestamp'))
        _write_scoped(frame,targets.table('manifest'),run_pred)
    try:
        existing=spark.table(targets.table('bronze')).where(version_pred)
        same_bronze=_same_rows(incoming,existing)
        if not same_bronze and existing.limit(1).count() and not repair:
            raise ValueError('BRONZE_CONTENT_CONFLICT_REQUIRES_EXPLICIT_REPAIR')
        if prior and prior['status']=='COMPLETE' and same_bronze:
            candidate=spark.sql(silver_sql(targets,version,policy))
            if _same_rows(candidate,spark.table(targets.table('silver')).where(run_pred)):
                return dict(action='SKIP_VERIFIED',source_version_id=version.version_id,processing_key=key,row_count=expected_rows)
            if not repair: raise ValueError('SILVER_CONTENT_CONFLICT_REQUIRES_EXPLICIT_REPAIR')
        mark('PROCESSING')
        if not same_bronze: _write_scoped(incoming,targets.table('bronze'),version_pred)
        if not _same_rows(incoming,spark.table(targets.table('bronze')).where(version_pred)):
            raise ValueError('BRONZE_POSTFLIGHT_FAILED')
        state['bronze_rows']=expected_rows;mark('BRONZE_WRITTEN')
        candidate=spark.sql(silver_sql(targets,version,policy))
        if candidate.count()!=expected_rows: raise ValueError('SILVER_COUNT_MISMATCH')
        existing=spark.table(targets.table('silver')).where(run_pred)
        same_silver=_same_rows(candidate,existing)
        if not same_silver:
            if existing.limit(1).count() and not repair:
                raise ValueError('SILVER_CONTENT_CONFLICT_REQUIRES_EXPLICIT_REPAIR')
            _write_scoped(candidate,targets.table('silver'),run_pred)
        state['silver_rows']=expected_rows;mark('SILVER_WRITTEN')
        if not _same_rows(candidate,spark.table(targets.table('silver')).where(run_pred)):
            raise ValueError('SILVER_POSTFLIGHT_FAILED')
        mark('COMPLETE')
        return dict(action='PROCESSED',source_version_id=version.version_id,processing_key=key,row_count=expected_rows)
    except Exception as error:
        state['error_code']=type(error).__name__
        mark('FAILED')
        raise
