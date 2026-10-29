"""Synthetic-only source, transformation, revision and recovery tests."""
from dataclasses import replace
from datetime import date, timedelta
import csv
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from winterops.foundation import (SOURCE_COLUMNS, QualityPolicy, aggregate_quality, processing_key,
                                 read_bronze, silver_rows)
from winterops.ingestion import LocalManifest, export_bronze, process_local, rows_digest
from winterops.sources import LocalStager, WeeklySource, discover_weekly, fingerprint, outside_git
from winterops.spark_ingestion import (DevelopmentTargets, manifest_status_sql, process_spark,
                                      silver_sql, sql_version_plan)


def source(start='2026-01-05'):
    end=(date.fromisoformat(start)+timedelta(days=6)).isoformat()
    return WeeklySource.from_url(f'https://opendata.citywindsor.ca/Uploads/snowplow-{start}_{end}.csv')


def synthetic(start='2026-01-05'):
    tomorrow=(date.fromisoformat(start)+timedelta(days=1)).isoformat()
    return [
        ['42.3','-83.0',start+' 23:59:59.999999','True','False','True','SYN-A'],
        ['42.3','-83.0',start+' 23:59:59.999999','True','False','True','SYN-A'],
        ['42.3','-83.0',tomorrow+' 00:00:00.500000','False','True','False','SYN-A'],
        ['999','-83.0',start+' 10:00:00','True','False','True',' SYN-B '],
        ['42.3','-82.18',start+' 11:00:00','True','True','True','SYN-C'],
        ['NaN','Infinity','2026-02-30 00:00:00','ON','False','UNKNOWN','SYN-D'],
        list(SOURCE_COLUMNS), [],
        ['42.3','-83.0',start+' 12:00:00'],
        ['42.3','-83.0',start+' 13:00:00','True','False','True','SYN\nMULTILINE'],
        ['42.3','-83.0','2026-02-01 00:00:00','True','True','True','SYN-OUTSIDE'],
    ]


class FoundationV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.stager=LocalStager(self.root/'staging')
        self.manifest=LocalManifest(self.root/'manifest.sqlite')
        self.addCleanup(self.manifest.close)

    def stage(self, rows=None, start='2026-01-05', columns=SOURCE_COLUMNS):
        src=source(start)
        path=self.root/'input.csv'
        with path.open('w',encoding='utf-8',newline='') as out:
            writer=csv.writer(out);writer.writerow(columns)
            writer.writerows(synthetic(start) if rows is None else rows)
        return self.stager.adopt(src,path)[0]

    def test_discovery_accepts_only_observed_official_links(self):
        url=source().source_url
        html=f'<a href="{url}">week</a><a href="{url}">again</a><a href="https://evil.test/x.csv">no</a>'
        self.assertEqual(discover_weekly(html),(source(),))
        self.assertEqual(discover_weekly('<a href="/Uploads/snowplow-2026-01-05_2026-01-11.csv">x</a>'),(source(),))

    def test_url_period_and_staging_boundaries_fail_closed(self):
        for url in (source().source_url.replace('https:','http:'),source().source_url+'?token=x',
                    source().source_url.replace('citywindsor.ca','citywindsor.ca.evil.test'),
                    source().source_url.replace('2026-01-11','2026-01-12')):
            with self.subTest(url=url),self.assertRaises(ValueError): WeeklySource.from_url(url)
        with self.assertRaises(ValueError): outside_git(ROOT/'.venv/telemetry')
        with self.assertRaises(ValueError): QualityPolicy(review_lon_min=0,review_lon_max=-1)
        with self.assertRaises(ValueError): QualityPolicy(long_gap_seconds=True)
        with self.assertRaises(ValueError): LocalStager(self.root/'bound',max_bytes=True)

    def test_immutable_staging_identical_and_changed_bytes(self):
        first=self.stage();second=self.stage()
        self.assertEqual(first,second)
        newer=self.stage([*synthetic(),synthetic()[0]])
        self.assertNotEqual(first.version_id,newer.version_id)
        first.verify();newer.verify()
        events=[json.loads(line) for line in (self.stager.root/'retrievals.jsonl').read_text().splitlines()]
        self.assertIn('IDENTICAL_BYTES',[row['state'] for row in events])

    def test_failed_staging_is_bounded_and_recorded_without_partial_publication(self):
        limited=LocalStager(self.root/'limited',max_bytes=8)
        path=self.root/'oversize.csv';path.write_bytes(b'x'*9)
        with self.assertRaises(ValueError):limited.adopt(source(),path)
        events=[json.loads(line) for line in (limited.root/'retrievals.jsonl').read_text().splitlines()]
        self.assertEqual(events[-1]['state'],'FAILED')
        self.assertFalse(list(limited.root.glob('*.partial')))
        self.assertFalse((limited.root/'raw').exists())

    def test_sql_warehouse_plan_has_exact_version_predicates_and_safe_audit_events(self):
        v=self.stage()
        plan=sql_version_plan(v,'/Volumes/workspace/default/winterops_raw/v2/hash/bronze.jsonl','a'*64,11)
        self.assertEqual(set(plan),{'artifact_guard','input_guard','bronze_write','silver_write','postflight'})
        self.assertIn('EXCEPT ALL',plan['postflight'])
        self.assertIn("REPLACE WHERE source_version_id = '"+v.version_id+"'",plan['bronze_write'])
        self.assertIn("REPLACE WHERE processing_key = '"+processing_key(v,QualityPolicy())+"'",plan['silver_write'])
        self.assertNotIn('winterops_silver_windsor_week_sample','\n'.join(plan.values()))
        event=manifest_status_sql(v,'COMPLETE',1,bronze_rows=11,silver_rows=11,last_successful_stage='COMPLETE')
        self.assertIn('winterops_v2_dev_manifest',event)
        windows_version=replace(v,local_path='C:\\synthetic\\é\\file.csv')
        event=manifest_status_sql(windows_version,'PROCESSING',1)
        self.assertIn(json.dumps(windows_version.to_dict()).encode('utf-8').hex(),event)
        with self.assertRaises(ValueError):manifest_status_sql(v,'COMPLETE',1,bronze_rows=True)
        with self.assertRaises(ValueError):sql_version_plan(v,'/Volumes/workspace/default/winterops_raw/v2/../bronze.jsonl','a'*64,11)

    def test_bronze_retains_duplicates_headers_blanks_widths_and_line_numbers(self):
        version=self.stage();rows=list(read_bronze(version))
        self.assertEqual(len(rows),11)
        self.assertEqual([row['source_record_number'] for row in rows],list(range(1,12)))
        self.assertEqual(rows[0]['record_sha256'],rows[1]['record_sha256'])
        self.assertEqual(json.loads(rows[6]['raw_record_json'])['Truck'],'Truck')
        self.assertEqual(json.loads(rows[7]['raw_values_json']),[])
        self.assertEqual(rows[8]['csv_parse_issues'],'CSV_WIDTH_MISMATCH')
        self.assertGreater(rows[9]['source_line_end'],rows[9]['source_record_number']+1)
        self.assertEqual(json.loads(rows[9]['raw_record_json'])['Truck'],'SYN\nMULTILINE')

    def test_silver_world_invalid_and_geographic_review_are_distinct(self):
        v=self.stage();b=list(read_bronze(v));s=silver_rows(b,v)
        self.assertEqual(s[3]['quality_status'],'INVALID')
        self.assertIn('INVALID_LATITUDE',s[3]['quality_issues'])
        self.assertEqual(s[4]['quality_status'],'VALID')
        self.assertEqual(s[4]['quality_warnings'],'OUTSIDE_REVIEW_ENVELOPE')
        self.assertIsNone(s[5]['latitude']);self.assertIsNone(s[5]['longitude'])
        self.assertIn('INVALID_PLOW_STATUS',s[5]['quality_issues'])
        self.assertIn('INVALID_ENGINE_STATUS',s[5]['quality_issues'])
        self.assertEqual(s[6]['quality_status'],'HEADER')
        self.assertEqual(s[6]['quality_issues'],'REPEATED_HEADER')
        self.assertEqual(s[7]['quality_status'],'INVALID')
        self.assertIn('TIMESTAMP_OUTSIDE_SOURCE_WEEK',s[10]['quality_issues'])
        self.assertEqual(s[3]['truck_id'],' SYN-B ')
        self.assertIn('ENGINE_OFF_EQUIPMENT_FLAG',s[2]['quality_warnings'])

    def test_aggregate_report_reconciles_without_identifiers_or_coordinates(self):
        v=self.stage();b=list(read_bronze(v));s=silver_rows(b,v);r=aggregate_quality(b,s,v)
        self.assertEqual((r['bronze_rows'],r['silver_rows'],r['header_rows'],r['valid_rows'],r['invalid_rows']),(11,11,1,5,5))
        self.assertEqual(r['distinct_valid_identifiers'],3)
        self.assertEqual(r['repeated_valid_payload_observations'],2)
        self.assertEqual(r['excess_valid_payload_observations'],1)
        self.assertEqual(r['consecutive_valid_timestamp_pairs'],2)
        self.assertEqual(r['zero_gap_pairs'],1)
        self.assertEqual(r['minimum_positive_source_clock_gap_seconds'],0.500001)
        self.assertEqual(r['csv_width_mismatch_rows'],2)
        serialized=json.dumps(r)
        for value in ('SYN-A','SYN-C','-82.18','raw_record_json','raw_values_json'):
            self.assertNotIn(value,serialized)

    def test_initial_and_identical_rerun_preserve_contents_and_attempt_count(self):
        v=self.stage();first=process_local(self.manifest,v)
        b=self.manifest.rows('bronze',v.version_id);key=first['report']['processing_key']
        silver=self.manifest.rows('silver',key)
        run=self.manifest.run(key)
        second=process_local(self.manifest,v)
        self.assertEqual(second['action'],'SKIP_VERIFIED')
        self.assertEqual(self.manifest.run(key),run)
        self.assertEqual(self.manifest.rows('bronze',v.version_id),b)
        self.assertEqual(self.manifest.rows('silver',key),silver)

    def test_second_week_appends_and_keeps_original_week_unchanged(self):
        a=self.stage();r=process_local(self.manifest,a)
        before=rows_digest(self.manifest.rows('bronze',a.version_id)),rows_digest(self.manifest.rows('silver',r['report']['processing_key']))
        b=self.stage(start='2026-01-19');process_local(self.manifest,b)
        self.assertEqual(before,(rows_digest(self.manifest.rows('bronze',a.version_id)),rows_digest(self.manifest.rows('silver',r['report']['processing_key']))))
        self.assertEqual(self.manifest.db.execute('SELECT COUNT(*) FROM bronze').fetchone()[0],22)

    def test_changed_source_is_retained_and_requires_explicit_version_selection(self):
        a=self.stage();process_local(self.manifest,a)
        b=self.stage([*synthetic(),synthetic()[0]])
        r=process_local(self.manifest,b)
        self.assertEqual(r['discovery'],'NEW_REVISION')
        with self.assertRaises(ValueError): self.manifest.select_version(a.source.source_file_name)
        self.assertEqual(self.manifest.select_version(a.source.source_file_name,a.source_file_sha256),a)
        self.assertEqual(len(self.manifest.rows('bronze',a.version_id)),11)
        self.assertEqual(len(self.manifest.rows('bronze',b.version_id)),12)

    def test_changed_policy_preserves_bronze_and_old_silver(self):
        v=self.stage();r=process_local(self.manifest,v);old=r['report']['processing_key']
        before=rows_digest(self.manifest.rows('bronze',v.version_id)),rows_digest(self.manifest.rows('silver',old))
        r2=process_local(self.manifest,v,QualityPolicy(review_lon_max=-82.0))
        self.assertNotEqual(old,r2['report']['processing_key'])
        self.assertEqual(before,(rows_digest(self.manifest.rows('bronze',v.version_id)),rows_digest(self.manifest.rows('silver',old))))
        self.assertNotIn('OUTSIDE_REVIEW_ENVELOPE',r2['report']['warning_counts'])

    def test_interrupted_bronze_and_silver_attempts_resume_without_duplicates(self):
        for stage in ('bronze','silver'):
            v=self.stage([*synthetic(),*([synthetic()[0]] if stage=='silver' else [])])
            def interrupt(current):
                if current==stage: raise RuntimeError('Synthetic interruption')
            with self.assertRaises(RuntimeError): process_local(self.manifest,v,after_stage=interrupt)
            key=processing_key(v,QualityPolicy())
            self.assertEqual(self.manifest.run(key)['status'],'FAILED')
            self.assertEqual(self.manifest.run(key)['last_successful_stage'],stage.upper()+'_WRITTEN')
            r=process_local(self.manifest,v)
            self.assertEqual(r['action'],'PROCESSED')
            self.assertEqual(self.manifest.run(key)['attempts'],2)
            self.assertEqual(len(self.manifest.rows('bronze',v.version_id)),len(self.manifest.rows('silver',key)))

    def test_same_count_corruption_fails_then_explicit_repair_is_scoped(self):
        a=self.stage();result=process_local(self.manifest,a);key=result['report']['processing_key']
        b=self.stage(start='2026-01-19');other=process_local(self.manifest,b)
        before=rows_digest(self.manifest.rows('silver',other['report']['processing_key']))
        with self.manifest.db:
            self.manifest.db.execute("UPDATE silver SET row_json=replace(row_json,'VALID','INVALID') WHERE scope_key=? AND record_number=1",(key,))
        with self.assertRaises(ValueError): process_local(self.manifest,a)
        self.assertEqual(self.manifest.run(key)['error_code'],'COMPLETE_CONTENT_MISMATCH_REQUIRES_EXPLICIT_REPAIR')
        process_local(self.manifest,a,repair=True)
        self.assertEqual(before,rows_digest(self.manifest.rows('silver',other['report']['processing_key'])))
        self.assertEqual(process_local(self.manifest,a)['action'],'SKIP_VERIFIED')

    def test_schema_drift_failure_is_observable_without_partial_rows(self):
        v=self.stage(columns=[*SOURCE_COLUMNS,'Unexpected'])
        with self.assertRaises(ValueError): process_local(self.manifest,v)
        run=self.manifest.run(processing_key(v,QualityPolicy()))
        self.assertEqual(run['status'],'FAILED')
        self.assertEqual(run['error_code'],'SOURCE_SCHEMA_DRIFT')
        self.assertEqual(self.manifest.rows('bronze',v.version_id),[])

    def test_ambiguous_quoting_empty_source_and_record_bounds_fail(self):
        for rows in ([],):
            v=self.stage(rows)
            with self.assertRaises(ValueError): process_local(self.manifest,v)
        v=self.stage()
        with self.assertRaises(ValueError): list(read_bronze(v,max_records=2))
        p=self.root/'broken.csv'
        p.write_text(','.join(SOURCE_COLUMNS)+'\n"unterminated',encoding='utf-8')
        broken=self.stager.adopt(source(),p)[0]
        with self.assertRaises(csv.Error): process_local(self.manifest,broken)
        self.assertEqual(self.manifest.rows('bronze',broken.version_id),[])

    def test_changed_staged_bytes_and_writer_overlap_fail_closed(self):
        v=self.stage();process_local(self.manifest,v)
        with self.manifest.writer_lock(),self.assertRaises(RuntimeError):
            process_local(self.manifest,v)
        Path(v.local_path).write_bytes(b'changed')
        with self.assertRaises(ValueError): process_local(self.manifest,v)

    def test_reordered_schema_is_supported_but_values_are_not_relabelled(self):
        cols=list(reversed(SOURCE_COLUMNS))
        row=dict(zip(SOURCE_COLUMNS,synthetic()[0]))
        v=self.stage([[row[k] for k in cols]],columns=cols)
        s=silver_rows(list(read_bronze(v)),v)
        self.assertEqual(s[0]['truck_id'],'SYN-A')
        self.assertEqual(s[0]['quality_status'],'VALID')

    def test_export_is_content_addressed_and_repeatable(self):
        v=self.stage();process_local(self.manifest,v)
        a=export_bronze(self.manifest,v,self.root/'exports')
        b=export_bronze(self.manifest,v,self.root/'exports')
        self.assertEqual(a,b)
        self.assertEqual(fingerprint(Path(a['local_path'])),a['artifact_sha256'])
        self.assertEqual(len(Path(a['local_path']).read_text().splitlines()),11)

    def test_no_databricks_write_can_run_without_exact_target_approval(self):
        class NoCompute:
            def __getattr__(self,name): raise AssertionError('No Spark call should occur')
        v=self.stage()
        with self.assertRaises(PermissionError): process_spark(NoCompute(),v,'/Volumes/x/bronze.jsonl','a'*64,11)
        targets=DevelopmentTargets()
        ddl=targets.creation_sql()
        self.assertEqual(len(ddl),3)
        self.assertTrue(all('winterops_v2_dev_' in sql and 'OR REPLACE' not in sql and 'IF NOT EXISTS' not in sql for sql in ddl))
        with self.assertRaises(ValueError): DevelopmentTargets(schema='default; DROP TABLE x')

    def test_committed_source_evidence_reconciles_and_has_no_record_fields(self):
        evidence=json.loads((ROOT/'docs/DATA_FOUNDATION_V2_SOURCE_REPORT.json').read_text(encoding='utf-8'))
        self.assertEqual(evidence['status'],'PASS_LOCAL_ONLY')
        self.assertFalse(evidence['databricks_executed'])
        for report in evidence['reports']:
            self.assertEqual(report['bronze_rows'],report['silver_rows'])
            self.assertEqual(report['silver_rows'],report['header_rows']+report['valid_rows']+report['invalid_rows'])
            self.assertEqual(report['consecutive_valid_timestamp_pairs'],report['valid_rows']-report['distinct_valid_identifiers'])
            self.assertEqual(report['consecutive_valid_timestamp_pairs'],sum(report[key] for key in
                ('zero_gap_pairs','positive_below_nominal_pairs','nominal_interval_pairs','above_nominal_within_threshold_pairs','long_gap_pairs')))
        forbidden={'truck_id','latitude','longitude','raw_record_json','raw_values_json','record_sha256','local_path','access_token','warehouse_id'}
        def inspect(value):
            if isinstance(value,dict):
                self.assertFalse(forbidden.intersection(value))
                for child in value.values():inspect(child)
            elif isinstance(value,list):
                for child in value:inspect(child)
        inspect(evidence)

    def test_cli_discovery_and_rendering_are_offline(self):
        html=self.root/'catalogue.html';html.write_text(f'<a href="{source().source_url}">x</a>')
        result=subprocess.run([sys.executable,str(ROOT/'scripts/windsor_history.py'),'discover','--catalogue-file',str(html)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]['source_file_name'],source().source_file_name)
        v=self.stage()
        self.manifest.register(v)
        result=subprocess.run([sys.executable,str(ROOT/'scripts/windsor_history.py'),'--root',str(self.root),'plan','--filename',v.source.source_file_name,'--sha256',v.source_file_sha256],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('TIMESTAMP_NTZ',result.stdout)
        self.assertNotIn('SYN-A',result.stdout)


if __name__=='__main__': unittest.main()
