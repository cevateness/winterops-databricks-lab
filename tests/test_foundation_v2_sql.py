"""Execute V2 SQL logic offline with explicit SQLite dialect adaptations.

This tests classifications/multiplicity against Python, not native Spark types,
Delta writes, privileges, JSON date parsing or Databricks runtime compatibility.
"""
import json
import math
import re
import sqlite3

import test_foundation_v2 as fixtures
from winterops.foundation import QualityPolicy, _number, _timestamp, read_bronze, silver_rows
from winterops.ingestion import process_local
from winterops.spark_ingestion import BRONZE_TYPES, DevelopmentTargets, SILVER_TYPES, silver_sql


def adapt(sql):
    sql=sql.replace('workspace.default.winterops_v2_dev_bronze','bronze')
    sql=sql.replace("from_json(raw_record_json, 'MAP<STRING,STRING>')",'raw_record_json')
    sql=re.sub(r"try_cast\(try_element_at\(payload, '([^']+)'\) AS DOUBLE\)",r"finite_number(map_value(payload, '\1'))",sql)
    sql=sql.replace("try_cast(trim(try_element_at(payload, 'Date time')) AS TIMESTAMP_NTZ)","naive_timestamp(trim(map_value(payload, 'Date time')))")
    sql=re.sub(r"try_element_at\(payload, '([^']+)'\)",r"map_value(payload, '\1')",sql)
    sql=sql.replace('CAST(source_week_start AS TIMESTAMP_NTZ)',"source_week_start || ' 00:00:00'")
    sql=sql.replace('CAST(source_week_end_exclusive AS TIMESTAMP_NTZ)',"source_week_end_exclusive || ' 00:00:00'")
    sql=sql.replace('RLIKE','REGEXP')
    return sql


import unittest
class V2SqlDifferentialTests(unittest.TestCase):
    setUp=fixtures.FoundationV2Tests.setUp
    stage=fixtures.FoundationV2Tests.stage

    def execute(self, version, policy=QualityPolicy()):
        bronze=list(read_bronze(version))
        with sqlite3.connect(':memory:') as db:
            db.create_function('map_value',2,lambda text,key:json.loads(text).get(key))
            db.create_function('finite_number',1,_number)
            db.create_function('naive_timestamp',1,lambda value:(_timestamp(value).isoformat(sep=' ') if _timestamp(value) else None))
            db.create_function('regexp',2,lambda pattern,value:False if value is None else bool(re.search(pattern,value)))
            db.create_function('isnan',1,lambda value:False if value is None else math.isnan(value))
            db.create_function('concat_ws',-1,lambda sep,*values:sep.join(v for v in values if v is not None))
            fields=list(BRONZE_TYPES)
            db.execute('CREATE TABLE bronze ('+', '.join(field+' '+kind for field,kind in BRONZE_TYPES.items())+')')
            db.executemany('INSERT INTO bronze VALUES ('+','.join('?' for _ in fields)+')',[[row[k] for k in fields] for row in bronze])
            cursor=db.execute(adapt(silver_sql(DevelopmentTargets(),version,policy)))
            names=[c[0] for c in cursor.description]
            actual=[dict(zip(names,row)) for row in cursor.fetchall()]
        for row in actual:
            for key in ('plow_active','spreader_active','engine_active','has_repeated_payload','is_repeated_header'):
                if row[key] is not None: row[key]=bool(row[key])
        self.assertEqual(names,list(SILVER_TYPES))
        self.assertEqual(sorted(actual,key=lambda r:r['source_record_number']),silver_rows(bronze,version,policy))
        return actual

    def test_all_classifications_and_subsecond_ties_match_reference(self):
        self.execute(self.stage())

    def test_world_bounds_nonfinite_values_and_status_encodings(self):
        rows=[]
        for lat,lon,status in [('90','180',' TRUE '),('-90','-180','false'),('Infinity','NaN','1'),
                ('-Infinity','-181','on'),('','0',''),('91','0','False'),('4_2.3','-83',' True\t'),('٤٢','-83','True')]:
            row=fixtures.synthetic()[0].copy();row[0]=lat;row[1]=lon;row[3]=status;rows.append(row)
        self.execute(self.stage(rows))

    def test_strict_timestamps_window_and_review_policy(self):
        rows=[]
        for value in ('2026-01-05 00:00:00','2026-01-11 23:59:59.999999','2026-01-12 00:00:00',
                      '2026-01-05T12:00:00','2026-01-05 12:00:00Z','2026-02-30 12:00:00','0000-01-05 12:00:00'):
            row=fixtures.synthetic()[0].copy();row[2]=value;rows.append(row)
        self.execute(self.stage(rows),QualityPolicy(review_lon_max=-82.0))

    def test_payload_frequencies_are_scoped_to_one_source_version(self):
        actual=self.execute(self.stage([fixtures.synthetic()[0],fixtures.synthetic()[0]]))
        self.assertEqual([r['payload_occurrences'] for r in actual],[2,2])
        actual=self.execute(self.stage([fixtures.synthetic()[0]]))
        self.assertEqual(actual[0]['payload_occurrences'],1)

    def test_hard_stop_leaves_observable_attempt_for_explicit_resume(self):
        v=self.stage()
        def interrupt(stage):
            if stage=='bronze':raise SystemExit('synthetic process termination')
        with self.assertRaises(SystemExit):process_local(self.manifest,v,after_stage=interrupt)
        result=process_local(self.manifest,v)
        self.assertEqual(result['report']['reconciliation'],'PASS')
        statuses=[r[0] for r in self.manifest.db.execute('SELECT status FROM attempts ORDER BY attempt_id')]
        self.assertEqual(statuses,['INTERRUPTED','COMPLETE'])
