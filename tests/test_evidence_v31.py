import copy
import base64
import gzip
import json
import re
from datetime import datetime,timedelta,timezone
from pathlib import Path
import unittest

from winterops.geospatial import RoadIndex,TO_METRES,observation_interval
from winterops.road_passages import PassageMatcher,PassagePolicy,passage_runs,angle_difference,sensitivity_policies
from winterops.operational_diagnostics import timestamp_events
from winterops.sensor_investigation import conflict_review,identifier_continuity
from winterops.weather_exposure import exposure_calendar,exposure_summary,load_references,correlation

ROOT=Path(__file__).resolve().parents[1]

def ll(x,y):
    origin=TO_METRES.transform(-83,42.3)
    return TO_METRES.transform(origin[0]+x,origin[1]+y,direction='INVERSE')

def network(lines,nodes=None):
    features=[dict(attributes=dict(street_compkey=i+1,street_name='A',functional_classification='fixture'),
                   geometry=dict(paths=[[ll(*p) for p in line]])) for i,line in enumerate(lines)]
    idx=RoadIndex(dict(features=features))
    return PassageMatcher(idx,nodes or {})

def interval(x=0,y=0,end=20,ey=0):
    return dict(p=ll(x,y),q=ll(end,ey),distance_m=((end-x)**2+(ey-y)**2)**.5,
                seconds=15,speed_kph=5,before='plow_only',after='plow_only',clock_status='known')

class RoadEvidenceTests(unittest.TestCase):
    def match(self,m,e,policy=None,method='topology'):
        return m.match(e,m.alternatives(e),policy or PassagePolicy(),method)
    def test_heading_rejects_perpendicular_proximity(self):
        m=network([[(-100,0),(100,0)]])
        e=interval(0,-15,0,15)
        self.assertIsNotNone(self.match(m,e,method='nearest')['path'])
        self.assertIsNone(self.match(m,e,method='heading')['path'])
        self.assertEqual(angle_difference(179,1),2)
    def test_parallel_alternatives_remain_ambiguous(self):
        m=network([[(-100,0),(100,0)],[(-100,10),(100,10)]])
        self.assertEqual(self.match(m,interval(y=5,ey=5))['reason'],'road_alternative_ambiguous')
        self.assertIsNotNone(self.match(m,interval(y=0,ey=0),PassagePolicy(alternative_separation_m=0))['path'])
    def test_topology_requires_provider_node_and_endpoint_agreement(self):
        lines=[[(-100,0),(0,0)],[(0,0),(100,0)]]
        m=network(lines,{1:(1,2),2:(2,3)})
        e=interval(-25,0,25)
        self.assertIsNotNone(self.match(m,e)['path'])
        self.assertIsNone(self.match(m,e,method='heading')['path'])
        self.assertIsNone(self.match(network(lines),e)['path'])
        bad=network([[(-100,0),(0,0)],[(10,0),(100,0)]],{1:(1,2),2:(2,3)})
        self.assertEqual(bad.topology_audit['node_geometry_mismatch_pairs'],1)
        self.assertFalse(bad.connections)
    def test_recording_gap_state_tie_speed_and_stationary_rejections(self):
        m=network([[(-100,0),(100,0)]])
        for change,reason in [({'seconds':61},'recording_gap'),({'before':'unknown_conflicting_tie'},'conflicting_state_unknown'),
                              ({'speed_kph':101},'questionable_speed'),({'distance_m':2},'stationary'),({'p':None},'coordinate_tie_unknown')]:
            with self.subTest(reason=reason):self.assertEqual(self.match(m,dict(interval(),**change))['reason'],reason)
        self.assertIsNotNone(self.match(m,dict(interval(),seconds=61),PassagePolicy(gap_seconds=120))['path'])
    def test_three_groups_sequence_preserves_multiplicity_and_boundaries(self):
        m=network([[(-100,0),(100,0)]])
        es=[]
        for i in range(3):
            e=interval(i*20,0,(i+1)*20);e.update(processing_key='p',truck_id='a',start=str(i),end=str(i+1),ordinals=[i+1,i+2]);es.append(e)
        matches=[self.match(m,e) for e in es]
        runs=passage_runs(es,matches,m.index)
        self.assertEqual((len(runs),runs[0]['interval_count'],runs[0]['observation_count']),(1,3,4))
        self.assertEqual(passage_runs(es[:1],matches[:1],m.index),[])
        separate=copy.deepcopy(es);separate[1]['processing_key']='q'
        self.assertEqual(passage_runs(separate,matches,m.index),[])
        rejected=copy.deepcopy(matches);rejected[1]['path']=None
        self.assertEqual(passage_runs(es,rejected,m.index),[])
        reversed_matches=copy.deepcopy(matches);reversed_matches[1]['path']['direction']=2
        self.assertEqual(passage_runs(es,reversed_matches,m.index),[])
    def test_same_name_disconnected_features_do_not_form_sequence(self):
        m=network([[(-100,0),(-10,0)],[(10,0),(100,0)]])
        es=[dict(interval(),processing_key='p',truck_id='a',start='0',end='1',ordinals=[1,2]),
            dict(interval(),processing_key='p',truck_id='a',start='1',end='2',ordinals=[2,3])]
        ms=[dict(path=dict(indices=(i,),progress=20,direction=0,topology=False)) for i in (0,1)]
        self.assertEqual(passage_runs(es,ms,m.index),[])
    def test_invalid_policy_and_short_heading_unknown(self):
        with self.assertRaises(ValueError):PassagePolicy(distance_m=61)
        m=network([[(-100,0),(100,0)]])
        self.assertEqual(self.match(m,interval(end=5))['reason'],'heading_displacement_too_short')
        self.assertEqual(len(sensitivity_policies()),11)

class SensorTests(unittest.TestCase):
    def test_conflict_order_is_record_order_not_physical_transition(self):
        def row(n,spread):return dict(processing_key='p',truck_id='x',event_time_unzoned='2026-02-09 01:00:00',
                                     longitude=-83,latitude=42.3,source_record_number=n,plow_active=True,spreader_active=spread,has_repeated_payload=False)
        rows=[row(2,False),row(1,True)];events=timestamp_events(rows);r,private=conflict_review(events)
        self.assertEqual(r['conflicting_groups'],1);self.assertEqual(r['same_coordinate_conflicts'],1)
        self.assertEqual(r['source_ordinal_state_sequences'],{'both → plow_only':1})
        self.assertTrue(private[0]['state'].startswith('unknown'))
        self.assertEqual(len(rows),2)
    def test_zero_conflicts_and_identity_scope(self):
        r,_=conflict_review({});self.assertEqual(r['conflicting_groups'],0)
        r=identifier_continuity([{'a','b'},{'a','c'}])
        self.assertEqual(r['distinct_reported_identifier_strings'],3);self.assertEqual(r['source_identifier_scopes'],4)

class ExposureTests(unittest.TestCase):
    def test_actual_public_weather_snapshots_and_complete_calendar(self):
        facts,refs,receipts=load_references(ROOT/'data/weather_reference')
        self.assertEqual(len(facts),2448);self.assertEqual(sum(r['response_bytes'] for r in receipts),64961)
        calendar=exposure_calendar(facts,refs,[],[])
        self.assertEqual(len(calendar),4704);self.assertFalse(any(r['missing_weather'] for r in calendar))
        self.assertTrue(all(r['observation_count'] is None for r in calendar))
        summary=exposure_summary(calendar)
        self.assertTrue(all(r['missing_telemetry_hours']==1176 for r in summary['calendar']))
    def test_current_accumulation_and_antecedent_do_not_overlap(self):
        start=datetime(2026,1,5,tzinfo=timezone.utc);facts={('g',(start+timedelta(hours=i)).isoformat()):dict(temperature_2m_c=i,precipitation_preceding_hour_mm=i+2,snowfall_preceding_hour_cm=0) for i in range(-6,8)}
        r=next(r for r in exposure_calendar(facts,[dict(reference_id='r',grid_id='g')],[],[],end='2026-01-06') if r['timezone_hypothesis']=='UTC')
        self.assertEqual(r['temperature_2m_c'],0);self.assertEqual(r['precipitation_activity_hour_mm'],3)
        self.assertEqual(r['precipitation_antecedent_mm'],3)
        self.assertEqual(r['telemetry_status'],'MISSING_TELEMETRY_ACTIVITY_UNKNOWN')
    def test_duplicate_hour_source_overlap_rejected_and_constant_correlation_unknown(self):
        with self.assertRaisesRegex(ValueError,'EXPOSURE_SOURCE_HOUR_OVERLAP'):
            exposure_calendar({},[],[dict(source_local_naive_hour='x')]*2,[])
        self.assertIsNone(correlation([1,1,1],[1,2,3]));self.assertIsNone(correlation([1,2],[2,3]))
    def test_missing_weather_inside_event_never_becomes_zero_accumulation(self):
        rows=[]
        for i,snow in enumerate([1,None,1]):
            t=f'2026-01-05 0{i}:00:00';rows.append(dict(reference_id='r',timezone_hypothesis='UTC',source_local_hour=t,
               valid_time_utc=t.replace(' ','T')+'+00:00',telemetry_status='MISSING_TELEMETRY_ACTIVITY_UNKNOWN',
               snowfall_activity_hour_cm=snow,missing_weather=snow is None,mean_reporting_ids_5m=None))
        event=exposure_summary(rows)['weather_defined_events'][0]
        self.assertIsNone(event['snowfall_cm']);self.assertEqual(event['missing_weather_hours'],1)
        self.assertTrue(event['boundary_context_incomplete'])

class PublicEvidenceTests(unittest.TestCase):
    def test_public_transport_is_lossless_and_contains_no_private_body(self):
        from winterops.geospatial_dashboard import render
        public=json.loads((ROOT/'dashboard/geospatial.json').read_text());context={'roads':{'type':'FeatureCollection','features':[]}}
        html=render(public,context);packed=re.search(r'<script id="data"[^>]*>(.*?)</script>',html,re.S).group(1)
        self.assertEqual(json.loads(gzip.decompress(base64.b64decode(packed))),dict(data=public,context=context))
        self.assertNotIn('local_payloads',public) # original source artifact stays unchanged
    def test_actual_weather_relationships_replay_without_private_records(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('replay',ROOT/'scripts/replay_weather_exposure.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        r=m.replay(json.loads((ROOT/'docs/ROAD_EVIDENCE_V31_RESULTS.json').read_text()))
        self.assertEqual(r['source_observations'],338746);self.assertEqual(r['calendar_rows'],4704)
        self.assertEqual(r['weather_requests'],0);self.assertFalse(r['spatial_sensor_details_rerun'])
        self.assertTrue(m.equivalent({'r':.5,'n':4},{'r':.5+1e-15,'n':4}))
        self.assertFalse(m.equivalent({'r':.5,'n':5},{'r':.5,'n':4}))
        self.assertFalse(m.equivalent({'r':.51},{'r':.5}))
    def test_public_road_suppression_and_nested_private_rejection(self):
        from winterops.geospatial_dashboard import render
        evidence=dict(schema='winterops-evidence-v31-public',pooled_corridors=[dict(road_name='fixture',passage_candidates=19,supported_intervals=40,source_weeks_present=4)])
        public=dict(schema='winterops-geospatial-v3-public',cells=[],investigation=evidence)
        with self.assertRaisesRegex(ValueError,'GEO_PUBLIC_ROAD_GRAIN'):render(public,{})
        evidence['pooled_corridors'][0]['passage_candidates']=20;evidence['pooled_corridors'][0]['source_weeks_present']=3
        with self.assertRaisesRegex(ValueError,'GEO_PUBLIC_ROAD_GRAIN'):render(public,{})
        evidence['pooled_corridors']=[];evidence['source_diagnostics']=[dict(private_scope_label='private')]
        with self.assertRaisesRegex(ValueError,'GEO_PRIVATE_FIELDS'):render(public,{})

if __name__=='__main__':unittest.main()
