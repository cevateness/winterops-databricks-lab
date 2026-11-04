from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import random
import sys
import unittest
import tempfile
import subprocess

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from weather_activity import synthetic_inputs,demo
from winterops.operational_diagnostics import (state,validated_rows,reporting_buckets,timestamp_events,episodes,
                                             transitions,percentile,weather_category,weather_relationships,weather_fact_keys)
from winterops.diagnostics_dashboard import render_public,render_private
from winterops.weather import WeatherContractError,canonical,digest
from winterops.weather_analysis import conditional_instant


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.scope,_=synthetic_inputs()
        self.rows=[]
        for i,(t,p,s,truck) in enumerate([('00:00:00',True,False,'PRIVATE-A'),('00:00:00',True,False,'PRIVATE-A'),
             ('00:00:00',True,True,'PRIVATE-A'),('00:00:15',False,True,'PRIVATE-A'),('00:01:00',True,False,'PRIVATE-A'),
             ('00:16:00',True,False,'PRIVATE-A'),('00:46:01',True,False,'PRIVATE-A'),('23:59:59',True,True,'PRIVATE-B')],1):
            self.rows.append(dict(self.scope.dimensions(),source_record_number=i,event_time_unzoned='2026-01-05 '+t,
                                 quality_status='VALID',truck_id=truck,plow_active=p,spreader_active=s,
                                 latitude=42.3,longitude=-83.01,has_repeated_payload=i<3))

    def test_windows_deduplicate_ids_not_observations(self):
        for width in (1,5,15):
            bs=reporting_buckets(self.rows,width)
            self.assertEqual(sum(r['observation_count'] for r in bs),8)
            self.assertEqual(bs[0]['reporting_ids'],1)
            self.assertGreater(bs[0]['observation_count'],bs[0]['reporting_ids'])

    def test_configurable_thresholds_and_exact_record_partition(self):
        self.assertEqual(sum(r['observation_count'] for r in reporting_buckets(self.rows,10)),8)
        for gap in (10,15,30,60):
            eps=episodes(timestamp_events(self.rows),gap,self.scope)
            self.assertEqual(sorted(n for ep in eps for n in ep['source_record_ordinals']),list(range(1,9)))
        with self.assertRaises(WeatherContractError):reporting_buckets(self.rows,7)

    def test_both_flags_within_window_differ_from_same_ping_both(self):
        rows=[dict(self.rows[0]),dict(self.rows[3])]
        r=reporting_buckets(rows,5)[0]
        self.assertEqual(r['both_any_observations_ids'],1)
        self.assertEqual(r['both_same_observation_ids'],0)
        self.assertEqual(r['plow_exclusive_ids']+r['spreader_exclusive_ids'],0)

    def test_midnight_is_separate_bucket(self):
        rows=[dict(self.rows[-1]),dict(self.rows[-1],event_time_unzoned='2026-01-06 00:00:00')]
        self.assertEqual(len(reporting_buckets(rows,15)),2)

    def test_scope_and_ordinal_validation(self):
        self.assertEqual(len(validated_rows(self.rows,self.scope)),8)
        with self.assertRaisesRegex(WeatherContractError,'ORDINAL'):validated_rows(self.rows+[self.rows[0]],self.scope)
        wrong=deepcopy(self.rows);wrong[0]['quality_policy_sha256']='wrong'
        with self.assertRaisesRegex(WeatherContractError,'SCOPE'):validated_rows(wrong,self.scope)

    def test_ties_and_shuffle_cannot_manufacture_state_order(self):
        expected=timestamp_events(self.rows)
        shuffled=deepcopy(self.rows);random.Random(7).shuffle(shuffled)
        self.assertEqual(timestamp_events(shuffled),expected)
        first=expected[(self.scope.processing_key,'PRIVATE-A')][0]
        self.assertEqual(first['state'],'unknown_conflicting_tie');self.assertEqual(len(first['rows']),3)

    def test_gap_boundary_and_episode_sensitivity_reconcile(self):
        events=timestamp_events(self.rows)
        results=[episodes(events,g,self.scope) for g in (15,30,60)]
        self.assertEqual([len(r) for r in results],[3,3,2])
        for r in results:
            self.assertEqual(sum(e['observation_count'] for e in r),8)
            self.assertTrue(all(e['left_censored'] and e['right_censored'] for e in r))
        self.assertEqual(results[0][0]['apparent_span_seconds'],960)

    def test_unknown_gap_or_tie_never_counts_as_activation(self):
        ts=transitions(timestamp_events(self.rows),60)
        self.assertEqual(sum(r['plow_activation_intervals'] for r in ts),1)
        self.assertEqual(sum(r['spreader_activation_intervals'] for r in ts),0)
        self.assertEqual(sum(r['intervals'] for r in ts if r['status']=='gap_unknown'),2)
        self.assertTrue(all(r['plow_activation_intervals']==r['spreader_activation_intervals']==0 for r in ts if r['status']!='known'))

    def test_activation_only_with_known_prior_off_flag(self):
        rows=[dict(self.rows[0],plow_active=False,spreader_active=False),dict(self.rows[3],plow_active=True,spreader_active=False)]
        self.assertEqual(sum(r['plow_activation_intervals'] for r in transitions(timestamp_events(rows))),1)

    def test_conflicting_first_cells_are_not_arbitrarily_chosen(self):
        rows=[self.rows[0],dict(self.rows[1],longitude=-82.5)]
        ep=episodes(timestamp_events(rows),30,self.scope)[0]
        self.assertIsNone(ep['first_observed_cell'])

    def test_quantiles_and_category_boundaries(self):
        self.assertEqual(percentile([1,2,3,4],.5),2.5)
        self.assertEqual(weather_category(-10,'temperature'),'-10_to_below_0C')
        self.assertEqual(weather_category(0,'temperature'),'0C_or_warmer')
        self.assertEqual(weather_category(0,'snow'),'zero')
        self.assertEqual(weather_category(None,'snow'),'missing')
        with self.assertRaises(WeatherContractError):weather_category(-1,'snow')

    def test_dst_weather_hypotheses_fail_closed(self):
        for t in ('2026-03-08 02:00:00','2026-11-01 01:00:00'):
            with self.assertRaises(WeatherContractError):conditional_instant(datetime.fromisoformat(t),'America/Toronto')
        self.assertEqual(conditional_instant(datetime(2026,1,5,0),'America/Toronto').hour,5)

    def test_antecedent_facts_end_at_containing_hour_start(self):
        r=demo()['matches'][0]
        keys=weather_fact_keys(r,'precipitation_antecedent_mm')
        self.assertEqual(len(keys),2)
        self.assertIn((r['weather_snapshot_id'],r['grid_id'],r['temperature_valid_time_utc']),keys)
        self.assertNotIn((r['weather_snapshot_id'],r['grid_id'],r['accumulation_valid_time_utc']),keys)

    def test_private_renderer_allowlist_drops_identifying_fields(self):
        d=demo();rows=[dict(r,source_local_naive_hour=r['source_local_hour'],plow_only_observations=1,
                            spreader_only_observations=0,both_active_observations=0,truck_id='SECRET_TRUCK_SENTINEL') for r in d['matches']]
        html=render_private(dict(evidence='SYNTHETIC_ONLY',snapshot_id='demo',scopes=[],grids={},cells=rows,matches=rows))
        self.assertNotIn('SECRET_TRUCK_SENTINEL',html)
        self.assertNotIn('createObjectURL',html)

    def test_actual_public_reconciliation_and_privacy(self):
        d=json.loads((ROOT/'dashboard/diagnostics.json').read_text());expected=d.pop('content_sha256')
        self.assertEqual(digest(canonical(d)),expected)
        for width in (1,5,15):self.assertEqual(sum(r['observations'] for r in d['reporting'] if r['grain']=='week' and r['bucket_minutes']==width),298051)
        for gap in (15,30,60):self.assertEqual(sum(r['observations'] for r in d['episodes'] if r['gap_minutes']==gap),298051)
        text=json.dumps(d)
        for key in ('truck_id','source_record_ordinals','first_observed_cell','spatial_bin','grid_id','latitude','longitude'):
            self.assertFalse('"'+key+'":' in text,key)

    def test_public_view_has_no_private_map_filter_data_or_exports(self):
        d=json.loads((ROOT/'dashboard/diagnostics.json').read_text())
        html=render_public(d)
        self.assertNotIn('createObjectURL',html)
        self.assertNotIn('aria-label="Map day"',html)
        d['relationships']['private_injection']={'truck_id':'SENTINEL'}
        with self.assertRaisesRegex(WeatherContractError,'PRIVATE_FIELD'):render_public(d)

    def test_public_replay_is_create_only_and_carries_no_private_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'review';cmd=[sys.executable,str(ROOT/'scripts/build_operational_diagnostics.py'),'--output-root',str(out)]
            r=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual((out/'diagnostics.html').read_text(),(ROOT/'dashboard/diagnostics.html').read_text())
            self.assertFalse((out/'private_map.html').exists())
            self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,2)

    def test_weather_join_duplicates_missingness_and_scenarios(self):
        scope,rows=synthetic_inputs()
        for r in rows:r.update(truck_id='PRIVATE-SYN',plow_active=True,spreader_active=False)
        eps=episodes(timestamp_events(rows),30,scope)
        bs=[r for w in (1,5,15) for r in reporting_buckets(rows,w)]
        matches=[dict(r,plow_active_observations=r['observation_count'],spreader_active_observations=0,both_active_observations=0) for r in demo()['matches']]
        rs=weather_relationships(matches,eps,bs)
        for zone in ('America/Toronto','UTC'):
            self.assertEqual(sum(r['observations'] for r in rs['cell_hour'] if r['timezone_hypothesis']==zone and r['variable']=='temperature_2m_c'),15)
        with self.assertRaisesRegex(WeatherContractError,'DUPLICATE_WEATHER'):
            weather_relationships(matches+[matches[0]],eps,bs)
        for e in eps:e['first_observed_cell']=None
        rs=weather_relationships(matches,eps,bs)
        self.assertTrue(all(r['episodes_with_weather']==0 for r in rs['episode_onsets']))

if __name__=='__main__':unittest.main()
