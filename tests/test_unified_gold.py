"""Synthetic multi-week SQL differential tests. SQLite is not native Databricks."""
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from datetime import datetime,timedelta
from decimal import Decimal
import csv,json,re,sqlite3,tempfile,unittest
from pathlib import Path

from test_gold_products_sql import adapted
from winterops.foundation import SOURCE_COLUMNS,QualityPolicy,read_bronze,silver_rows
from winterops.landing import OriginalLanding,VOLUME
from winterops.sources import LocalStager,WeeklySource
from winterops.spark_ingestion import BRONZE_TYPES,SILVER_TYPES,MANIFEST_TYPES
from winterops.unified_gold import SelectedVersion,UnifiedGold,DIMENSIONS,ADDITIVE,HOUR,validate_schemas


def sqlite_sql(sql):
    sql=sql.replace('workspace.default.','').replace('EXCEPT ALL','EXCEPT')
    sql=sql.replace(HOUR,"(substr(event_time_unzoned,1,13) || ':00:00')")
    sql=re.sub(r"DATE ('[^']*')",r'\1',sql)
    for column in ('w.source_week_start','w.source_week_end_exclusive'):
        sql=sql.replace(f'CAST({column} AS TIMESTAMP_NTZ)',f"({column} || ' 00:00:00')")
    sql=sql.replace('CAST(h.source_local_naive_hour AS DATE)','substr(h.source_local_naive_hour,1,10)')
    return adapted(sql)


def reference(rows,selection):
    """Independent row-based oracle; no SQL output reused for expected metrics."""
    valid=[r for r in rows if r['quality_status']=='VALID']
    freq=Counter(r['record_sha256'] for r in valid)
    def activity(group):
        return dict(observation_count=len(group),plow_active_observations=sum(r['plow_active'] for r in group),
            spreader_active_observations=sum(r['spreader_active'] for r in group),
            plow_only_observations=sum(r['plow_active'] and not r['spreader_active'] for r in group),
            spreader_only_observations=sum(r['spreader_active'] and not r['plow_active'] for r in group),
            both_active_observations=sum(r['spreader_active'] and r['plow_active'] for r in group),
            neither_active_observations=sum(not r['spreader_active'] and not r['plow_active'] for r in group),
            engine_off_observations=sum(not r['engine_active'] for r in group),
            engine_off_with_equipment_flag_observations=sum(not r['engine_active'] and (r['plow_active'] or r['spreader_active']) for r in group),
            repeated_valid_payload_observations=sum(freq[r['record_sha256']]>1 for r in group),
            observed_identifier_count=len({r['truck_id'] for r in group}))
    hours,days,ids=defaultdict(list),defaultdict(list),defaultdict(list)
    for r in valid:
        t=datetime.fromisoformat(r['event_time_unzoned']);h=t.replace(minute=0,second=0,microsecond=0).isoformat(sep=' ')
        hours[h].append(r);days[t.date().isoformat()].append(r);ids[r['truck_id']].append(t)
    hourly=[{**selection.dimensions(),'source_local_naive_hour':h,**activity(group)} for h,group in sorted(hours.items())]
    daily=[{**selection.dimensions(),'source_local_naive_day':d,**activity(group),
            'hours_containing_telemetry':sum(h[:10]==d for h in hours),
            'maximum_hourly_identifiers':max(len({r['truck_id'] for r in g}) for h,g in hours.items() if h[:10]==d)} for d,group in sorted(days.items())]
    gaps=[]
    for times in ids.values():
        times.sort();gaps.extend((b-a).total_seconds() for a,b in zip(times,times[1:]))
    weekly={**selection.dimensions(),**activity(valid),'bronze_rows':len(rows),'silver_rows':len(rows),
        'header_rows':sum(r['quality_status']=='HEADER' for r in rows),'valid_rows':len(valid),
        'invalid_rows':sum(r['quality_status']=='INVALID' for r in rows),'quarantine_rows':len(rows)-len(valid),
        'invalid_coordinate_rows':sum(r['quality_status']=='INVALID' and ('INVALID_LATITUDE' in r['quality_issues'] or 'INVALID_LONGITUDE' in r['quality_issues']) for r in rows),
        'outside_review_envelope_rows':sum('OUTSIDE_REVIEW_ENVELOPE' in r['quality_warnings'] for r in rows),
        'hours_containing_telemetry':len(hours),'days_containing_telemetry':len(days),
        'maximum_hourly_identifiers':max((len({r['truck_id'] for r in group}) for group in hours.values()),default=0),
        'repeated_valid_payload_groups':sum(n>1 for n in freq.values()),'excess_valid_payload_observations':sum(n-1 for n in freq.values()),
        'consecutive_timestamp_pairs':len(gaps),'zero_gap_pairs':sum(g==0 for g in gaps),
        'long_gap_pairs':sum(g>selection.policy.long_gap_seconds for g in gaps),
        'maximum_source_clock_gap_seconds':max(gaps,default=None)}
    return dict(hourly=hourly,daily=daily,weekly=[weekly])


class UnifiedGoldTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.db=sqlite3.connect(':memory:');self.addCleanup(self.db.close)
        def assertion(ok,message):
            if not ok:raise ValueError(message)
            return None
        self.db.create_function('assert_true',2,assertion)
        self.db.create_function('raise_error',1,lambda message:assertion(False,message))
        self.db.create_function('datediff',2,lambda end,start:(datetime.fromisoformat(end)-datetime.fromisoformat(start)).days)
        self.db.create_function('source_seconds_us',1,lambda s:int(Decimal(s)*1000000))
        for name,types in [('bronze',BRONZE_TYPES),('silver',SILVER_TYPES),('manifest',MANIFEST_TYPES)]:
            self.db.execute('CREATE TABLE winterops_v2_dev_'+name+' ('+', '.join(k+' '+v for k,v in types.items())+')')
        self.selections=[];self.typed=[]
        for start in ('2026-01-05','2026-01-12','2026-01-19'):
            day2=(datetime.fromisoformat(start)+timedelta(days=1)).date().isoformat()
            row=['42.3','-83',start+' 00:00:00','True','False','True','SYN-A']
            rows=[row,row,row[:2]+[start+' 00:00:00.500001','True','True','True','SYN-A'],
                row[:2]+[start+' 01:00:00','False','True','False','SYN-B'],
                row[:2]+[day2+' 00:00:00','False','False','True','SYN-C'],
                ['42.3','-82.2',day2+' 03:00:00','True','False','True','SYN-A'],
                row[:2]+[start+' 00:30:00','False','False','True','SYN-C'],list(SOURCE_COLUMNS),
                ['91','-83',start+' 00:00:00','True','False','True','SYN-A']]
            path=self.root/'input.csv'
            with path.open('w',encoding='utf-8',newline='') as out:
                w=csv.writer(out);w.writerow(SOURCE_COLUMNS);w.writerows(rows)
            end=(datetime.fromisoformat(start)+timedelta(days=6)).date().isoformat()
            source=WeeklySource.from_url(f'https://opendata.citywindsor.ca/Uploads/snowplow-{start}_{end}.csv')
            version=LocalStager(self.root/'stage').adopt(source,path)[0]
            bronze=list(read_bronze(version));silver=silver_rows(bronze,version)
            landing=OriginalLanding(source,version.source_file_sha256,version.byte_count)
            selection=SelectedVersion.from_version(version,len(bronze),landing)
            self.selections.append(selection);self.typed.append(silver)
            self.insert('bronze',BRONZE_TYPES,bronze);self.insert('silver',SILVER_TYPES,silver)
            self.insert('manifest',MANIFEST_TYPES,[dict(processing_key=selection.processing_key,source_version_id=version.version_id,
                source_file_name=source.source_file_name,source_file_sha256=version.source_file_sha256,
                metadata_json=json.dumps(version.to_dict()),policy_json=json.dumps(asdict(QualityPolicy())),
                status='COMPLETE',last_successful_stage='COMPLETE',attempts=1,bronze_rows=len(bronze),silver_rows=len(silver),
                error_code=None,updated_at_utc='2026-01-30 00:00:00')])
        self.plan=UnifiedGold(tuple(self.selections))

    def insert(self,layer,types,rows):
        self.db.executemany('INSERT INTO winterops_v2_dev_'+layer+' VALUES ('+','.join('?' for k in types)+')',[[r[k] for k in types] for r in rows])

    def execute(self,sql):
        cursor=self.db.execute(sqlite_sql(sql));return [dict(zip([c[0] for c in cursor.description],r)) for r in cursor.fetchall()]

    def publish(self):
        for p in ('hourly','daily','weekly'):
            name=self.plan.view_name(p).split('.')[-1]
            self.db.execute('CREATE TABLE '+name+' AS '+sqlite_sql(self.plan.query(p)))

    def test_three_weeks_match_independent_oracle_and_reconcile(self):
        self.execute(self.plan.selection_guard());self.execute(self.plan.reconcile())
        before=self.db.total_changes
        for product in ('hourly','daily','weekly'):
            expected=[r for rows,s in zip(self.typed,self.selections) for r in reference(rows,s)[product]]
            self.assertEqual(self.execute(self.plan.query(product)),expected)
        self.assertEqual(self.db.total_changes,before)
        self.publish();self.execute(self.plan.reconcile(published=True))

    def test_weekly_participation_is_not_sum_of_hourly_or_daily_distinct_counts(self):
        week=self.execute(self.plan.query('weekly'))[0]
        hours=[r for r in self.execute(self.plan.query('hourly')) if r['processing_key']==week['processing_key']]
        days=[r for r in self.execute(self.plan.query('daily')) if r['processing_key']==week['processing_key']]
        self.assertEqual(week['observed_identifier_count'],3)
        self.assertGreater(sum(r['observed_identifier_count'] for r in hours),3)
        self.assertGreater(sum(r['observed_identifier_count'] for r in days),3)

    def test_missing_failed_or_duplicate_manifest_is_rejected(self):
        for mutation in ["DELETE FROM winterops_v2_dev_manifest WHERE rowid=1",
            "UPDATE winterops_v2_dev_manifest SET status='PROCESSING' WHERE rowid=1",
            "UPDATE winterops_v2_dev_manifest SET status='FAILED' WHERE rowid=1",
            'INSERT INTO winterops_v2_dev_manifest SELECT * FROM winterops_v2_dev_manifest WHERE rowid=1']:
            with self.subTest(mutation=mutation):
                self.db.execute('SAVEPOINT before_mutation');self.db.execute(mutation)
                with self.assertRaises(sqlite3.OperationalError):self.execute(self.plan.selection_guard())
                self.db.execute('ROLLBACK TO before_mutation');self.db.execute('RELEASE before_mutation')

    def test_wrong_policy_provenance_counts_or_payload_multiplicity_rejected(self):
        for change in ["UPDATE winterops_v2_dev_silver SET quality_policy_sha256='wrong' WHERE rowid=1",
                       "UPDATE winterops_v2_dev_silver SET record_sha256='wrong' WHERE rowid=1",
                       'UPDATE winterops_v2_dev_silver SET payload_occurrences=99 WHERE rowid=1',
                       'DELETE FROM winterops_v2_dev_bronze WHERE rowid=1',
                       "UPDATE winterops_v2_dev_silver SET source_line_end=999 WHERE rowid=1"]:
            with self.subTest(change=change):
                self.db.execute('SAVEPOINT before_mutation');self.db.execute(change)
                with self.assertRaises(sqlite3.OperationalError):self.execute(self.plan.selection_guard())
                self.db.execute('ROLLBACK TO before_mutation');self.db.execute('RELEASE before_mutation')

    def test_unselected_revision_and_policy_are_ignored_without_multiplying_rows(self):
        before=self.execute(self.plan.query('weekly'))
        self.db.execute("INSERT INTO winterops_v2_dev_silver SELECT * FROM winterops_v2_dev_silver WHERE rowid=1")
        self.db.execute("UPDATE winterops_v2_dev_silver SET processing_key='unselected' WHERE rowid=(SELECT MAX(rowid) FROM winterops_v2_dev_silver)")
        self.assertEqual(self.execute(self.plan.query('weekly')),before)

    def test_product_queries_refuse_partial_complete_selection(self):
        self.db.execute("UPDATE winterops_v2_dev_manifest SET status='PROCESSING' WHERE rowid=1")
        for p in ('hourly','daily','weekly'):
            with self.subTest(product=p),self.assertRaises(sqlite3.OperationalError):self.execute(self.plan.query(p))

    def test_source_revisions_require_one_explicit_choice(self):
        import hashlib
        s=self.selections[0];sha='a'*64
        vid=hashlib.sha256('\0'.join(('windsor_snowplow_activity',s.source_file_name,sha)).encode()).hexdigest()
        key=hashlib.sha256('\0'.join((vid,s.pipeline_version,s.policy.policy_sha256)).encode()).hexdigest()
        revised=replace(s,source_file_sha256=sha,source_version_id=vid,processing_key=key,
                        original_csv_volume_path=OriginalLanding(s.source,sha,1).path)
        with self.assertRaises(ValueError):UnifiedGold((s,revised))
        self.assertEqual(UnifiedGold((revised,)).selected[0],revised)

    def test_equal_missing_audit_fields_on_both_layers_are_not_accepted_as_lineage(self):
        self.db.execute('UPDATE winterops_v2_dev_bronze SET ingested_at_utc=NULL WHERE rowid=1')
        self.db.execute('UPDATE winterops_v2_dev_silver SET ingested_at_utc=NULL WHERE rowid=1')
        with self.assertRaises(sqlite3.OperationalError):self.execute(self.plan.selection_guard())

    def test_all_header_week_has_zero_activity_without_disappearing_from_quality(self):
        old=self.selections[0];path=self.root/'headers.csv'
        with path.open('w',encoding='utf-8',newline='') as out:
            w=csv.writer(out);w.writerow(SOURCE_COLUMNS);w.writerows([SOURCE_COLUMNS]*9)
        v=LocalStager(self.root/'stage').adopt(old.source,path)[0]
        b=list(read_bronze(v));s=silver_rows(b,v)
        chosen=SelectedVersion.from_version(v,9,OriginalLanding(v.source,v.source_file_sha256,v.byte_count))
        self.db.execute('DELETE FROM winterops_v2_dev_bronze WHERE source_version_id=?',(old.source_version_id,))
        self.db.execute('DELETE FROM winterops_v2_dev_silver WHERE processing_key=?',(old.processing_key,))
        self.insert('bronze',BRONZE_TYPES,b);self.insert('silver',SILVER_TYPES,s)
        self.db.execute('UPDATE winterops_v2_dev_manifest SET processing_key=?,source_version_id=?,source_file_sha256=?,metadata_json=? WHERE processing_key=?',
                        (chosen.processing_key,v.version_id,v.source_file_sha256,json.dumps(v.to_dict()),old.processing_key))
        plan=UnifiedGold((chosen,*self.selections[1:]));self.execute(plan.reconcile())
        row=self.execute(plan.query('weekly'))[0]
        self.assertEqual((row['header_rows'],row['valid_rows'],row['quarantine_rows']),(9,0,9))
        self.assertEqual(row['observed_identifier_count'],0)
        self.assertFalse(any(r['processing_key']==chosen.processing_key for r in self.execute(plan.query('hourly'))))

    def test_balanced_wrong_hourly_counts_are_not_hidden_by_weekly_totals(self):
        self.publish();name=self.plan.view_name('hourly').split('.')[-1]
        before=self.db.execute('SELECT SUM(observation_count) FROM '+name).fetchone()[0]
        metrics=('observation_count','spreader_active_observations','spreader_only_observations','engine_off_observations','engine_off_with_equipment_flag_observations')
        for rowid,delta in ((1,1),(2,-1)):
            self.db.execute('UPDATE '+name+' SET '+','.join(m+'='+m+'+?' for m in metrics)+' WHERE rowid=?',[delta]*len(metrics)+[rowid])
        self.assertEqual(self.db.execute('SELECT SUM(observation_count) FROM '+name).fetchone()[0],before)
        with self.assertRaises(sqlite3.OperationalError):self.execute(self.plan.reconcile(published=True))

    def test_published_wrong_distinct_count_and_balanced_activity_corruption_detected(self):
        self.publish();self.execute(self.plan.reconcile(published=True))
        hourly=self.plan.view_name('hourly').split('.')[-1]
        self.db.execute('UPDATE '+hourly+' SET observed_identifier_count=observed_identifier_count+1 WHERE rowid=1')
        with self.assertRaises(sqlite3.OperationalError):self.execute(self.plan.reconcile(published=True))

    def test_repeated_observations_and_geographic_diagnostics_are_separate(self):
        week=self.execute(self.plan.query('weekly'))[0]
        self.assertEqual((week['silver_rows'],week['valid_rows'],week['header_rows'],week['invalid_rows']),(9,7,1,1))
        self.assertEqual((week['repeated_valid_payload_observations'],week['excess_valid_payload_observations']),(2,1))
        self.assertEqual((week['outside_review_envelope_rows'],week['invalid_coordinate_rows']),(1,1))
        self.assertEqual(week['engine_off_with_equipment_flag_observations'],1)

    def test_selection_rejects_ambiguity_and_unpinned_keys(self):
        with self.assertRaises(ValueError):UnifiedGold(())
        with self.assertRaises(ValueError):UnifiedGold((self.selections[0],self.selections[0]))
        with self.assertRaises(ValueError):replace(self.selections[0],processing_key='a'*64)
        changed=QualityPolicy(long_gap_seconds=2000)
        s=self.selections[1]
        import hashlib
        key=hashlib.sha256('\0'.join((s.source_version_id,s.pipeline_version,changed.policy_sha256)).encode()).hexdigest()
        s=replace(s,policy=changed,processing_key=key)
        with self.assertRaises(ValueError):UnifiedGold((self.selections[0],s))
        self.assertTrue(UnifiedGold((self.selections[0],s),allow_mixed_policies=True))

    def test_landing_paths_never_use_transport_suffix_and_reuse_requires_exact_path(self):
        s=self.selections[0].source
        landing=OriginalLanding(s,'a'*64,10)
        self.assertIn('/original_csv/',landing.path);self.assertTrue(landing.path.endswith('.csv'))
        self.assertFalse(landing.plan()['overwrite'])
        reuse=OriginalLanding(s,'a'*64,10,VOLUME+'/'+s.source_file_name)
        self.assertEqual(reuse.plan()['action'],'VERIFY_AND_REUSE')
        with self.assertRaises(ValueError):OriginalLanding(s,'a'*64,10,VOLUME+'/bronze.jsonl.gz')

    def test_schema_and_render_contracts_protect_legacy_objects(self):
        validate_schemas(BRONZE_TYPES,SILVER_TYPES,MANIFEST_TYPES)
        with self.assertRaises(ValueError):validate_schemas(BRONZE_TYPES,{**SILVER_TYPES,'event_time_unzoned':'TIMESTAMP'},MANIFEST_TYPES)
        for sql in self.plan.publication():
            self.assertTrue(sql.startswith('CREATE VIEW workspace.default.winterops_v2_gold_'))
            self.assertNotIn('OR REPLACE',sql)
            self.assertNotIn('winterops_gold_windsor_hourly_observations',sql)
        for sql in self.plan.dashboard().values():self.assertTrue(sql.startswith('SELECT '))

    def test_separate_published_comparisons_match_all_products(self):
        self.publish()
        for product,n in (('hourly',12),('daily',6),('weekly',3)):
            self.assertEqual(self.execute(self.plan.published_comparison(product)),
                             [{'published_'+product+'_check':None,'aggregate_rows':n}])

    def test_each_published_comparison_detects_same_rowcount_metric_corruption(self):
        self.publish()
        for product in ('hourly','daily','weekly'):
            self.db.execute('SAVEPOINT before_corruption')
            self.db.execute('UPDATE '+self.plan.view_name(product).split('.')[-1]+' SET observation_count=observation_count+1 WHERE rowid=1')
            with self.assertRaises(sqlite3.OperationalError):self.execute(self.plan.published_comparison(product))
            self.db.execute('ROLLBACK TO before_corruption');self.db.execute('RELEASE before_corruption')

    def test_combined_read_results_retain_both_guards(self):
        from winterops.threeweek_plan import combine_read_results
        sql=combine_read_results((('a',"SELECT assert_true(1=1,'a') AS check_a",('check_a',)),
                                 ('b',"SELECT assert_true(1=1,'b') AS check_b",('check_b',))))
        self.assertEqual(self.execute(sql),[{'a_check_a':None,'b_check_b':None}])
        with self.assertRaises(sqlite3.OperationalError):self.execute(sql.replace("assert_true(1=1,'b')","assert_true(1=0,'b')"))

    def test_manifest_snapshot_string_preserves_microseconds(self):
        from winterops.threeweek_plan import manifest_snapshot_sql
        from winterops.spark_ingestion import DevelopmentTargets
        self.db.create_function('sha2',2,lambda value,bits:__import__('hashlib').sha256(value.encode()).hexdigest())
        stamp='2026-10-29 13:14:58.044428'
        self.db.execute('UPDATE winterops_v2_dev_manifest SET updated_at_utc=?',(stamp,))
        sql=manifest_snapshot_sql(DevelopmentTargets(),[self.selections[0].processing_key]).replace(' AS STRING)',' AS TEXT)')
        self.assertEqual(self.execute(sql)[0]['updated_at_utc'],stamp)

    def test_native_preparer_refuses_unreviewed_source_identity_before_local_writes(self):
        from winterops.threeweek_plan import prepare
        selection=self.root/'selection.json'
        selection.write_text(json.dumps({'selected':[asdict(s) for s in self.selections]}),encoding='utf-8')
        private=self.root/'not_created'
        with self.assertRaises(ValueError):prepare(private,selection,self.root/'absent-native.json',self.root/'absent-summary.json')
        self.assertFalse(private.exists())

if __name__=='__main__':unittest.main()
