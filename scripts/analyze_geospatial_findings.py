"""Small empirical review from immutable local evidence; no source collection."""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from winterops.sources import SourceVersion,outside_git
from winterops.foundation import read_bronze,silver_rows
from winterops.operational_diagnostics import timestamp_events,state
from winterops.arcgis_source import canonical,digest
from winterops.geospatial import legacy_roads,RoadIndex


def analyze(root,build):
    root,build=map(outside_git,(root,build))
    result=json.loads((build/'summary.json').read_text());products=json.loads((build/'products.json').read_text())
    pin=json.loads((root/'roads_legacy.receipt.json').read_text())
    index=RoadIndex(legacy_roads(root/'roads_legacy.zip',pin['sha256']))
    ties=[];corridor_total=Counter();corridor_weeks=Counter()
    for f in sorted((root/'csv/raw').glob('*/*/*.version.json')):
        v=SourceVersion.from_dict(json.loads(f.read_text()));v.verify()
        rows=[r for r in silver_rows(list(read_bronze(v)),v) if r['quality_status']=='VALID']
        corridors=Counter()
        for row in rows:
            candidate=index.match(row['longitude'],row['latitude'])
            if (candidate['distance_m'] is not None and candidate['distance_m']<=30 and not candidate['ambiguous'] and candidate['road_name']):
                corridors[candidate['road_name']]+=1
        corridor_total.update(corridors);corridor_weeks.update(corridors.keys())
        groups=timestamp_events(rows);combos=Counter();naive_zero_changes=0
        for seq in groups.values():
            for e in seq:
                states=[state(r) for r in e['rows']]
                if len(set(states))>1:combos[' + '.join(sorted(set(states)))]+=1
                naive_zero_changes+=sum(a!=b for a,b in zip(states,states[1:]))
        ties.append(dict(week=v.source.covered_start,timestamp_groups=sum(map(len,groups.values())),
                         contradictory_state_combinations=dict(combos),
                         false_orderable_zero_time_state_changes=naive_zero_changes))
    # Public findings suppress finer geography entirely. Keep class aggregates,
    # source-week diagnostics and city/day requests; no ward/week intersections.
    result['sensors']=[{k:v for k,v in r.items() if k!='current_ward_observations'} for r in result['sensors']]
    result['requests'].pop('ward_counts',None)
    rr=json.loads((root/'requests_receipt.json').read_text())
    request_source=json.loads((root/'requests'/(rr['snapshot_id']+'.snapshot.json')).read_text())
    if digest(request_source)!=rr['snapshot_id']:raise ValueError('V3_REQUEST_SNAPSHOT_CHANGED')
    present=sum(f.get('geometry') is not None for f in request_source['features'])
    result['requests'].update(geometry_present=present,geometry_absent=len(request_source['features'])-present,
                              geometry_evidence='COUNTED_FROM_IMMUTABLE_FEATURE_SNAPSHOT')
    result['tied_state_review']=ties
    result['pooled_corridors']=[dict(road_name=name,candidate_observations=n,source_weeks_present=corridor_weeks[name])
                                for name,n in corridor_total.most_common() if n>=200 and corridor_weeks[name]>=4][:10]
    result['corridor_contract']='POOLED_ALL_SEVEN_WEEKS_NEAREST_WITHIN_30M_SECOND_ROAD_NOT_WITHIN_10M_MIN_200_OBSERVATIONS_MIN_4_WEEKS_NOT_CONFIRMED_PASSAGE'
    result['weekly_metrics']=products['weekly']
    for w in result['weekly_metrics']:
        begin=w['source_week_start'];end=w['source_week_end_exclusive']
        w['created_311_requests']=sum(n for day,n in result['requests']['daily_counts'].items() if begin<=day<end)
    result['scope']='SEVEN_PINNED_CSV_WEEKS_LOCAL_ONLY_FOUR_WEEK_NATIVE_EVIDENCE_UNCHANGED'
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-root',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=analyze(a.input_root,a.build);a.output.write_bytes(canonical(r)+b'\n')
    print(json.dumps(dict(status='PASS_LOCAL',weeks=len(r['weekly_metrics']),tied_review=r['tied_state_review'])))
