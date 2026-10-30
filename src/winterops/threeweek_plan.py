"""Prepare one local, fingerprinted native plan. No remote execution is provided."""
import hashlib,json,re
from pathlib import Path

from winterops.analytics import AnalyticsConfig,SourceScope,build_plan
from winterops.foundation import PIPELINE_VERSION,QualityPolicy
from winterops.ingestion import LocalManifest,export_bronze
from winterops.landing import OriginalLanding,VOLUME
from winterops.quality import QualitySnapshot
from winterops.sources import outside_git
from winterops.spark_ingestion import BRONZE_TYPES,SILVER_TYPES,sql_version_plan,manifest_status_sql
from winterops.unified_gold import load_selection


def manifest_snapshot_sql(targets, keys):
    if not keys or any(not re.fullmatch('[0-9a-f]{64}',k) for k in keys):
        raise ValueError('Exact processing keys required')
    selected=','.join("'"+k+"'" for k in keys)
    # Raw TIMESTAMP API values lose microseconds; STRING preserves native digits.
    return f"""SELECT processing_key,source_version_id,source_file_sha256,status,last_successful_stage,attempts,
 bronze_rows,silver_rows,error_code,CAST(updated_at_utc AS STRING) AS updated_at_utc,
 sha2(metadata_json,256) AS metadata_sha256,sha2(policy_json,256) AS policy_json_sha256
FROM {targets.table('manifest')} WHERE processing_key IN ({selected}) ORDER BY processing_key"""


def combine_read_results(parts):
    """Combine trusted generated single-row SELECTs, retaining every result field."""
    if not parts or len({p[0] for p in parts})!=len(parts):
        raise ValueError('Unique named read results required')
    for name,sql,columns in parts:
        if (not re.fullmatch('[a-z][a-z0-9_]*',name) or not columns
                or any(not re.fullmatch('[a-z][a-z0-9_]*',c) for c in columns)
                or not sql.lstrip().startswith(('SELECT ','WITH '))):
            raise ValueError('Generated single-row read queries required')
    ctes=',\n'.join(name+' AS ('+sql+')' for name,sql,_ in parts)
    fields=', '.join(name+'.'+c+' AS '+name+'_'+c for name,_,cols in parts for c in cols)
    return 'WITH '+ctes+'\nSELECT '+fields+' FROM '+' CROSS JOIN '.join(name for name,_,_ in parts)


def prepare(root,selection_path,prior_native_path,legacy_summary_path):
    """Private JSON may encode local provenance in manifest SQL: keep outside Git."""
    root=outside_git(root);gold=load_selection(selection_path)
    if [s.source.covered_start for s in gold.selected]!=['2026-01-05','2026-01-12','2026-01-19']:
        raise ValueError('This approval matrix is only for the three exact January weeks')
    exact=(('271c9339a42043f441b6c17e82dd309609db4b20e9953b9f368a95ec472d763d',2810),
           ('f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94',110337),
           ('b78d0fb82c8e3c5204ee79eea7a03417cd54bc935ead9b04577a30dc908c7c49',118159))
    if any((s.source_file_sha256,s.expected_rows)!=e or s.policy!=QualityPolicy() or s.pipeline_version!=PIPELINE_VERSION for s,e in zip(gold.selected,exact)):
        raise ValueError('This bounded approval matrix requires the reviewed exact sources and default policy')
    prior=json.loads(Path(prior_native_path).read_text(encoding='utf-8'))
    if prior['status']!='PASS_NATIVE_SQL_WAREHOUSE':raise ValueError('Require prior native V2 evidence')
    m=LocalManifest(root/'manifest.sqlite');versions={};source_plans={};uploads=[];landings=[]
    try:
        for s in gold.selected:
            v=m.select_version(s.source_file_name,s.source_file_sha256);v.verify()
            run=m.run(s.processing_key)
            if not run or run['status']!='COMPLETE' or run['bronze_rows']!=s.expected_rows:
                raise ValueError('Require reconciled local selected version')
            versions[s.source.covered_start]=v
            is_middle=s.source.covered_start=='2026-01-12'
            landing=OriginalLanding(v.source,v.source_file_sha256,v.byte_count,s.original_csv_volume_path if is_middle else None)
            if landing.path!=s.original_csv_volume_path:raise ValueError('Landing identity changed')
            landings.append(landing)
            if is_middle:
                artifact=export_bronze(m,v,root/'artifacts',compression='gzip')
                destination=f"{VOLUME}/foundation_v2_dev/{v.version_id}/{artifact['artifact_sha256']}/bronze.jsonl.gz"
                uploads.append(dict(kind='middle_jsonl_gzip',local_path=artifact['local_path'],volume_path=destination,
                    sha256=artifact['artifact_sha256'],bytes=artifact['artifact_bytes'],overwrite=False))
            else:
                artifact=next(a for a in prior['artifacts'] if a['source_file_sha256']==v.source_file_sha256)
                destination=f"{VOLUME}/foundation_v2_dev/{v.version_id}/{artifact['artifact_sha256']}/bronze.jsonl"+('.gz' if artifact.get('compression')=='gzip' else '')
                uploads.append(dict(kind='original_csv',local_path=v.local_path,volume_path=landing.path,
                    sha256=v.source_file_sha256,bytes=v.byte_count,overwrite=False))
            source_plans[s.source.covered_start]=sql_version_plan(v,destination,artifact['artifact_sha256'],s.expected_rows,policy=s.policy)
    finally:m.close()
    middle=gold.selected[1];version=versions['2026-01-12'];vplan=source_plans['2026-01-12']
    legacy=build_plan(AnalyticsConfig(SourceScope(middle.source_file_sha256),QualitySnapshot.from_mapping(json.loads(Path(legacy_summary_path).read_text()))))
    old_gold="""SELECT COUNT(*) AS hourly_buckets,SUM(observation_count) AS observations,
 SUM(plow_active_observation_count) AS plow_observations,SUM(spreader_active_observation_count) AS spreader_observations
FROM workspace.default.winterops_gold_windsor_hourly_observations"""
    protected=[('legacy-source',legacy.preflight[0]),('legacy-payload',legacy.preflight[1]),('legacy-published',legacy.postflight[0]),('legacy-gold',old_gold),
        ('legacy-bronze-history','DESCRIBE HISTORY workspace.default.winterops_bronze_windsor_activity LIMIT 1'),
        ('legacy-silver-history','DESCRIBE HISTORY workspace.default.winterops_silver_windsor_week_sample LIMIT 1')]
    steps=[]
    def add(label,sql,kind='READ',expected=None):
        steps.append(dict(label=label,kind=kind,sql=sql,query_sha256=hashlib.sha256(sql.encode()).hexdigest(),expected=expected))
    manifest_snapshot=manifest_snapshot_sql(gold.targets,[s.processing_key for s in (gold.selected[0],gold.selected[2])])
    for label,sql in protected:add('before-'+label,sql)
    add('before-outer-manifest-snapshot',manifest_snapshot,expected={'rows':2,'compare_exactly_with_after':True})
    for landing in (landings[0],landings[2]):add('before-original-'+landing.source.covered_start,landing.fingerprint_sql())
    for date in ('2026-01-05','2026-01-19'):add('before-existing-'+date,source_plans[date]['postflight'])
    add('middle-artifact',vplan['artifact_guard']);add('middle-input',vplan['input_guard'])
    targets=gold.targets
    new_scope=f"""SELECT assert_true((SELECT COUNT(*) FROM {targets.table('bronze')} WHERE source_version_id='{version.version_id}')=0
 AND (SELECT COUNT(*) FROM {targets.table('silver')} WHERE source_version_id='{version.version_id}' OR processing_key='{middle.processing_key}')=0
 AND (SELECT COUNT(*) FROM {targets.table('manifest')} WHERE source_version_id='{version.version_id}' OR processing_key='{middle.processing_key}')=0,
 'Middle-week scope already exists; reconcile before a separately approved resume') AS new_scope_check"""
    add('middle-original-and-new-scope',combine_read_results((
        ('original',landings[1].fingerprint_sql(),('original_csv_check',)),
        ('scope',new_scope,('new_scope_check',)))))
    def mark(status,bronze=None,silver=None):
        add('middle-manifest-'+status,manifest_status_sql(version,status,1,policy=middle.policy,bronze_rows=bronze,silver_rows=silver,last_successful_stage=None if status=='PROCESSING' else status),'WRITE')
    mark('PROCESSING')
    for layer,types in [('bronze',BRONZE_TYPES),('silver',SILVER_TYPES)]:
        # Append into an absence-checked new scope; no REPLACE WHERE for data tables.
        incoming=vplan[layer+'_write'].partition('\n')[2]
        add('middle-'+layer+'-append',f"INSERT INTO {targets.table(layer)} ({', '.join(types)})\n"+incoming,'WRITE',{'inserted_rows':middle.expected_rows})
        mark(layer.upper()+'_WRITTEN',middle.expected_rows,middle.expected_rows if layer=='silver' else None)
    add('middle-full-content-postflight',vplan['postflight'])
    mark('COMPLETE',middle.expected_rows,middle.expected_rows)
    add('threeweek-complete-selection',gold.selection_guard())
    add('candidate-gold-reconciliation',gold.reconcile())
    add('candidate-weekly-aggregates',gold.query('weekly'))
    for product,sql in zip(('hourly','daily','weekly'),gold.publication()):add('create-gold-'+product,sql,'CREATE_VIEW',{'target':gold.view_name(product)})
    for product in ('hourly','daily','weekly'):
        add('published-'+product+'-comparison',gold.published_comparison(product))
    add('published-hourly-summary',f"SELECT source_week_start,source_version_id,processing_key,quality_policy_sha256,COUNT(*) AS hourly_buckets,SUM(observation_count) AS observations FROM {gold.view_name('hourly')} GROUP BY source_week_start,source_version_id,processing_key,quality_policy_sha256 ORDER BY source_week_start")
    add('published-daily',gold.dashboard()['daily_equipment']);add('published-weekly',gold.dashboard()['three_week_comparison'])
    fields=('persisted_check','silver_rows','header_rows','valid_rows','invalid_rows')
    add('middle-rerun-and-first-week-preservation',combine_read_results((
        ('middle',vplan['postflight'],fields),('first',source_plans['2026-01-05']['postflight'],fields))))
    add('after-outer-manifest-snapshot',manifest_snapshot,expected={'rows':2,'must_equal_before_snapshot':True})
    add('after-existing-2026-01-19',source_plans['2026-01-19']['postflight'])
    for label,sql in protected:add('after-'+label,sql)
    add('after-original-csv-fingerprints',combine_read_results(tuple(
        ('csv_'+str(i),landing.fingerprint_sql(),('original_csv_check',)) for i,landing in enumerate(landings))))
    if len(steps)>45 or sum(u['bytes'] for u in uploads)>32*1024*1024 or any(u['bytes']>16*1024*1024 for u in uploads):
        raise ValueError('Prepared native scope exceeds bounds')
    return dict(status='PREPARED_NOT_APPROVED_NOT_EXECUTED',sql_statements=len(steps),sql_maximum=45,
        bounds=dict(sql_phase_seconds=600,wait_timeout='30s',on_wait_timeout='CANCEL',client_deadline_seconds=45,
                    row_limit=200,byte_limit=65536,upload_deadline_seconds=180,upload_max_bytes=16*1024*1024,
                    total_upload_max_bytes=32*1024*1024,metadata_deadline_seconds=15,file_verification_get_deadline_seconds=45,automatic_retries=0),
        table_targets=targets.names,new_gold_views=[gold.view_name(p) for p in ('hourly','daily','weekly')],
        original_csvs=[l.plan() for l in landings],uploads=uploads,steps=steps,
        metadata_requirements=['Same approved winterops workspace and existing warehouse; match protected identities and configuration',
            'Exact Bronze/Silver/manifest schemas and existing outer-week COMPLETE metadata; snapshot full contents and manifests before writes',
            'All three new Gold names absent; CREATE VIEW privileges; existing table write and Volume permissions',
            'Immutable upload paths absent or exact bytes identical; skip identical files, never overwrite conflicts',
            'After completion compare outer-week manifest snapshots, all protected metadata/grants/configuration and original Delta versions'],
        stop_and_recovery='Stop on first failure, mismatch, timeout, cancellation or truncation. No automatic retry, cleanup, compensation, replacement or rollback. Preserve immutable uploads and committed stages; inspect full contents/status before proposing a separately approved scoped resume. Never replay append after a partial write or recreate an existing view.',
        expected=dict(bronze_rows=231306,silver_rows=231306,header_rows=79,valid_rows=231227,invalid_rows=0,complete_manifests=3,
                      hourly_buckets=236,plow_observations=175008,spreader_observations=119439,review_envelope_warnings=863))
