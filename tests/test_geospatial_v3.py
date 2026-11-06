import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from winterops.arcgis_source import ArcGISSource,snapshot,schema_contract,digest,windsor_observation,semantic_fingerprint
from winterops.geospatial import geometry,RoadIndex,observed_fragments,TO_METRES
from winterops.source_overlap import compare
from winterops.geospatial_dashboard import render
from winterops.municipal_status import edmonton_status_sample

ROOT=Path(__file__).resolve().parents[1]
META=dict(fields=[dict(name='OID',type='esriFieldTypeOID'),dict(name='value',type='esriFieldTypeString')],
          geometryType='esriGeometryPoint',sourceSpatialReference=dict(wkid=4326),maxRecordCount=2)


class Fake:
    def __init__(self,mode=None):self.receipts=[];self.mode=mode;self.metadata_calls=0;self.id_calls=0
    def get(self,url,**params):
        self.receipts.append(dict(url=url,params=params))
        if not url.endswith('/query'):
            self.metadata_calls+=1;m=copy.deepcopy(META)
            if self.mode=='schema_drift' and self.metadata_calls>1:m['fields'][1]['type']='esriFieldTypeInteger'
            return m
        if 'returnCountOnly' in params:return dict(count=3)
        if 'returnIdsOnly' in params:
            self.id_calls+=1
            return dict(objectIds=[1,1,3] if self.mode=='duplicate_ids' else [1,2,4] if self.mode=='id_drift' and self.id_calls>1 else [3,1,2])
        ids=list(map(int,params['objectIds'].split(',')))
        features=[dict(attributes=dict(OID=i,value='synthetic'),geometry=dict(x=0,y=0)) for i in ids]
        if self.mode=='missing_page':features.pop()
        if self.mode=='omitted_field':
            for f in features:f['attributes'].pop('value')
        return dict(features=features,spatialReference=dict(wkid=26917 if self.mode=='wrong_crs' else 4326),
                    exceededTransferLimit=self.mode=='transfer_limit')


class AdapterTests(unittest.TestCase):
    def run_snapshot(self,root,mode=None,**kw):
        return snapshot(ArcGISSource('synthetic','synthetic','fixture','https://example.org/a/MapServer/1'),Fake(mode),Path(root),'1=1',4,batch_size=2,**kw)
    def test_complete_exact_batches_and_safe_rerun(self):
        with tempfile.TemporaryDirectory() as root:
            a,r=self.run_snapshot(root);b,s=self.run_snapshot(root)
            self.assertEqual(r['state'],'COMPLETE');self.assertEqual(r['records'],3)
            self.assertEqual(r['snapshot_id'],s['snapshot_id']);self.assertEqual(a,b)
            self.assertEqual(len(list(Path(root).glob('*.snapshot.json'))),1)
    def test_partial_and_drift_never_complete(self):
        for mode in ['missing_page','duplicate_ids','id_drift','schema_drift','omitted_field','wrong_crs','transfer_limit']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as root:
                with self.assertRaises(ValueError):self.run_snapshot(root,mode)
                self.assertFalse(list(Path(root).glob('*.snapshot.json')))
                self.assertEqual(json.loads(next(Path(root).glob('*.attempt.json')).read_text())['state'],'FAILED')
    def test_unknown_schema_pin_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,'SCHEMA_CHANGED'):self.run_snapshot(root,expected_schema='0'*64)
    def test_explicit_projection_is_not_silent_missing_field_coercion(self):
        with tempfile.TemporaryDirectory() as root:
            d,r=self.run_snapshot(root,'omitted_field',fields=('OID',))
            self.assertEqual(d['fields'],('OID',));self.assertEqual(r['records'],3)
            self.assertEqual(len(d['schema']['fields']),2)
    def test_config_rejects_credential_query_and_non_layer(self):
        for u in ['http://example.org/MapServer/1','https://x:y@example.org/MapServer/1','https://example.org/MapServer/1?token=a','https://example.org/a']:
            with self.assertRaises(ValueError):ArcGISSource('a','b','c',u)
    def test_extraction_aliases_do_not_create_an_independent_provider(self):
        a=ArcGISSource('city','place','january','https://example.org/MapServer/1')
        b=ArcGISSource('city','place','february','https://example.org/MapServer/1')
        self.assertEqual(a.canonical_source_id,b.canonical_source_id)
    def test_explicit_envelope_revision_separate_from_record_revision(self):
        old=dict(source=dict(provider='p',city='c',layer_url='https://x/MapServer/1',source='alias'),where='1=1',schema={},features=[])
        new=dict(old,fields=None);self.assertEqual(semantic_fingerprint(old),semantic_fingerprint(new))
        new['features']=[dict(attributes={'OID':1})]
        self.assertNotEqual(semantic_fingerprint(old),semantic_fingerprint(new))
    def test_portal_normalization_preserves_epoch_and_identity(self):
        f=dict(attributes=dict(OBJECTID=9,truck=7,record_date=1767615961000,latitude=42.3,longitude=-83.,plow_status='True',spreader_status='False',engine_status='True'))
        r=windsor_observation(f,'snapshot',4)
        self.assertEqual(r['event_time_unzoned'],'2026-01-05 07:26:01');self.assertEqual(r['snapshot_object_id'],9)
        self.assertTrue(r['plow_active']);self.assertEqual(r['source_record_number'],4)
        f['attributes']['plow_status']='yes'
        with self.assertRaises(ValueError):windsor_observation(f,'s',1)


def row(t,ordinal=1,lon=-83.,lat=42.3,plow=True,spread=False,key='scope'):
    return dict(event_time_unzoned='2026-01-05 '+t,source_record_number=ordinal,longitude=lon,latitude=lat,
                truck_id=1,processing_key=key,plow_active=plow,spreader_active=spread,engine_active=True,has_repeated_payload=False)


class GeoTests(unittest.TestCase):
    def test_ring_holes_multipart_and_crs_guard(self):
        g=geometry(dict(rings=[[[0,0],[0,4],[4,4],[4,0],[0,0]],[[1,1],[1,2],[2,2],[2,1],[1,1]]]))
        self.assertEqual(g.area,15)
        with self.assertRaises(ValueError):geometry(dict(x=330000,y=4680000))
    def test_metric_axis_order_and_roundtrip(self):
        x,y=TO_METRES.transform(-83,42.3)
        self.assertTrue(330000<x<340000);self.assertTrue(4680000<y<4690000)
        lon,lat=TO_METRES.transform(x,y,direction='INVERSE')
        self.assertAlmostEqual(lon,-83,places=8);self.assertAlmostEqual(lat,42.3,places=8)
    def test_nearby_parallel_roads_ambiguous_and_off_network(self):
        features=[]
        for i,lat in enumerate([42.3,42.3001]):
            features.append(dict(geometry=dict(paths=[[[-83.01,lat],[-82.99,lat]]]),attributes=dict(street_compkey=i,street_name='Synthetic',functional_classification='Local')))
        idx=RoadIndex(dict(features=features));m=idx.match(-83,42.30005)
        self.assertLess(m['distance_m'],10);self.assertTrue(m['ambiguous'])
        self.assertIsNone(idx.match(-83,42.31)['distance_m'])
        self.assertEqual(idx.match(-120,50)['status'],'OUTSIDE_LOCAL_PROJECTION_SCOPE')
    def test_actual_null_road_attributes_do_not_collapse_geometry_keys(self):
        sample=json.loads((ROOT/'data/fixtures/arcgis_windsor_road_response.json').read_text())
        self.assertIn('created_date',sample['advertised_field_names'])
        self.assertNotIn('created_date',sample['actual_unprojected_query_field_names'])
        f=sample['features'][0];self.assertIsNone(f['attributes']['street_compkey'])
        second=copy.deepcopy(f);second['attributes']['OBJECTID']+=1
        index=RoadIndex(dict(features=[f,second]))
        self.assertEqual(len({r['road_key'] for r in index.records}),2)
    def test_movement_conservative_interval_accounting(self):
        rows=[row('00:00:00'),row('00:00:15',2,lon=-82.9999),row('00:00:30',3,lon=-82.9998,spread=True),row('00:00:45',4,lon=-82.9998,spread=True),row('00:02:00',5,lon=-82.9997,spread=True)]
        m=observed_fragments(rows)
        self.assertEqual(m['intervals'],dict(accepted=1,equipment_state_change=1,stationary=1,recording_gap=1))
        self.assertEqual(m['segments'][0]['source_record_ordinals'],[[1],[2]])
    def test_tied_coordinates_states_and_source_boundaries(self):
        rows=[row('00:00:00'),row('00:00:00',2,lon=-82.9),row('00:00:15',3),row('00:00:30',4,key='other')]
        m=observed_fragments(rows);self.assertEqual(m['coordinate_conflict_groups'],1)
        self.assertEqual(m['intervals'],dict(coordinate_tie_unknown=1));self.assertEqual(m['segments'],[])
    def test_questionable_speed_is_flagged_not_deleted(self):
        rows=[row('00:00:00'),row('00:00:15',2,lon=-82.5)]
        m=observed_fragments(rows);self.assertEqual(m['intervals']['questionable_speed'],1);self.assertEqual(len(rows),2)
    def test_clock_hypotheses_match_winter_and_reject_ambiguous_dst(self):
        rows=[row('23:59:50'),dict(row('00:00:05',2,lon=-82.9999),event_time_unzoned='2026-01-06 00:00:05')]
        self.assertEqual(observed_fragments(rows),observed_fragments(rows,timezone_hypothesis='UTC'))
        dst=[dict(row('01:30:00'),event_time_unzoned='2026-11-01 01:30:00'),dict(row('01:30:15',2),event_time_unzoned='2026-11-01 01:30:15')]
        self.assertEqual(observed_fragments(dst)['intervals'],dict(clock_ambiguous_or_nonexistent=1))
    def test_spring_transition_uses_conditional_elapsed_time(self):
        rows=[dict(row('01:59:50'),event_time_unzoned='2026-03-08 01:59:50'),dict(row('03:00:05',2,lon=-82.9999),event_time_unzoned='2026-03-08 03:00:05')]
        self.assertEqual(observed_fragments(rows)['intervals'],dict(accepted=1))
        self.assertEqual(observed_fragments(rows,timezone_hypothesis='UTC')['intervals'],dict(recording_gap=1))
    def test_overlap_preserves_multiplicity_and_quantized_difference(self):
        a=row('00:00:00');b=dict(a,latitude=a['latitude']+1e-8)
        r=compare([a,a],[a,b]);self.assertEqual(r['exact_matches'],1);self.assertEqual(r['six_decimal_matches'],2)
        self.assertEqual(r['csv_unmatched'],1);self.assertFalse(r['independent_corroboration'])


class ProjectionTests(unittest.TestCase):
    def test_actual_other_city_sample_has_no_completed_outcomes(self):
        sample=json.loads((ROOT/'data/fixtures/edmonton_status_sample.json').read_text())
        rows=edmonton_status_sample(sample['rows'])
        self.assertEqual(len(rows),3);self.assertFalse(any(r['status_available'] for r in rows))
        self.assertEqual(rows[0]['provider'],'city_of_edmonton');self.assertNotIn('observation_count',rows[0])
    def test_public_renderer_rejects_private_payload_and_sparse_cells(self):
        base=dict(schema='winterops-geospatial-v3-public',cells=[])
        with self.assertRaises(ValueError):render(dict(base,segments=[]),{})
        with self.assertRaises(ValueError):render(dict(base,cells=[dict(processing_key='k',spatial_bin='q25:0:0',observation_count=19)]),{})
    def test_browser_contracts_and_privacy_filters_in_node(self):
        p=subprocess.run(['node',str(ROOT/'tests/geospatial_core_test.js')],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)

if __name__=='__main__':unittest.main()
