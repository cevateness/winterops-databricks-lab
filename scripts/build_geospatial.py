"""Offline V3 build: immutable sources → local Silver → diagnostics + file payload.

No HTTP, weather collection or Databricks calls. Raw/local outputs must be outside
Git. Public projection is a separate explicit allowlist, never a private toggle.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import gzip
import json
import math
from pathlib import Path
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from winterops.arcgis_source import canonical,digest,windsor_observation
from winterops.sources import SourceVersion,outside_git,fingerprint
from winterops.foundation import read_bronze,silver_rows,QualityPolicy
from winterops.landing import OriginalLanding
from winterops.unified_gold import SelectedVersion,UnifiedGold,load_selection
from winterops.operational_sql import LocalGold
from winterops.operational_analytics import validate_products,match_cached_weather,weather_summary
from winterops.operational_diagnostics import validated_rows,reporting_buckets,timestamp_events,episodes,transitions,bucket_summaries,episode_summaries,state
from winterops.geospatial import RoadIndex,context_geojson,observed_fragments,sensor_summary,legacy_roads
from winterops.source_overlap import compare

ROOT=Path(__file__).resolve().parents[1]


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def selected_snapshot(root,name):
    receipt=read(root/(name+'_receipt.json'))
    if receipt['state']!='COMPLETE':raise ValueError('V3_SNAPSHOT_NOT_COMPLETE')
    payload=read(root/name/(receipt['snapshot_id']+'.snapshot.json'))
    if digest(payload)!=receipt['snapshot_id']:raise ValueError('V3_SNAPSHOT_CHANGED')
    return payload,receipt


def write(path,value):
    with path.open('xb') as out:out.write(canonical(value)+b'\n')


def build(root,output,archive):
    root,output,archive=map(outside_git,(root,output,archive))
    if output.exists():raise ValueError('V3_OUTPUT_EXISTS')
    output.mkdir(parents=True)
    portal_roads,rr=selected_snapshot(root,'roads');wards,wr=selected_snapshot(root,'wards');boundary,br=selected_snapshot(root,'boundary')
    road_pin=read(root/'roads_legacy.receipt.json')
    roads=legacy_roads(root/'roads_legacy.zip',road_pin['sha256'])
    index=RoadIndex(roads,wards,boundary)
    versions=[];scopes=[];baseline=load_selection(ROOT/'docs/FOUR_WEEK_SELECTION.json')
    for f in sorted((root/'csv/raw').glob('*/*/*.version.json')):
        v=SourceVersion.from_dict(read(f));v.verify();versions.append(v)
        n=sum(1 for _ in read_bronze(v))
        pinned=next((s for s in baseline.selected if s.source_file_name==v.source.source_file_name),None)
        if pinned:
            if pinned.source_file_sha256!=v.source_file_sha256 or pinned.expected_rows!=n:raise ValueError('V3_PINNED_BYTES_CHANGED')
            scopes.append(pinned)
        else:scopes.append(SelectedVersion.from_version(v,n,OriginalLanding(v.source,v.source_file_sha256,v.byte_count)))
    scopes.sort(key=lambda s:s.source.covered_start);versions.sort(key=lambda v:v.source.covered_start)
    if tuple(scopes[:4])!=baseline.selected or len(scopes)!=7:raise ValueError('V3_BASELINE_OR_EXPANSION_SCOPE')
    plan=UnifiedGold(tuple(scopes));gold=LocalGold(plan)
    sensors=[];movements=[];reporting=[];eps=[];transition=[];detail_cells=[];private_segments=[];private_episodes=[];overlaps=[]
    for si,(v,s) in enumerate(zip(versions,scopes)):
        bronze=list(read_bronze(v));typed=silver_rows(bronze,v,s.policy)
        gold.add_verified_scope(s,typed);rows=validated_rows(typed,s)
        if si>=4:
            local=output/'local'/s.source_version_id;local.mkdir(parents=True)
            for name,values in [('bronze',bronze),('silver',typed)]:
                with gzip.GzipFile(filename=str(local/(name+'.jsonl.gz')),mode='xb',mtime=0) as out:
                    for value in values:out.write(canonical(value)+b'\n')
            write(local/'manifest.json',dict(state='LOCAL_COMPLETE_NOT_NATIVE',scope=s.dimensions(),rows=len(typed),
                                           valid=len(rows),files={p.name:fingerprint(p) for p in local.iterdir()}))
        sensor=sensor_summary(rows,index);sensor.update(processing_key=s.processing_key,week=s.source.covered_start)
        sensors.append(sensor)
        move=observed_fragments(rows)
        movements.append(dict(week=s.source.covered_start,processing_key=s.processing_key,**{k:v for k,v in move.items() if k!='segments'}))
        events=timestamp_events(rows)
        for minutes in (1,5,15):reporting.extend(reporting_buckets(rows,minutes))
        for minutes in (15,30,60):eps.extend(episodes(events,minutes,s))
        transition.extend(transitions(events,60))
        reference=[e for e in eps if e['processing_key']==s.processing_key and e['gap_minutes']==30]
        by_truck=defaultdict(list)
        for e in reference:
            seq=events[(s.processing_key,e['truck_id'])]
            ends=[]
            for stamp in (e['first_observed'],e['last_observed']):
                event=next(x for x in seq if x['time'].isoformat(' ')==stamp)
                coordinates={(r['longitude'],r['latitude']) for r in event['rows']}
                ends.append(list(next(iter(coordinates))) if len(coordinates)==1 else None)
            eid=len(private_episodes);private_episodes.append([si,e['first_observed'],e['last_observed'],e['observation_count'],
                                                           e['apparent_span_seconds'],e['conflicting_timestamp_groups'],e['entry_reason'],*ends])
            by_truck[e['truck_id']].append((e['first_observed'],e['last_observed'],eid))
        for seg in move['segments']:
            eid=next(eid for start,end,eid in by_truck[seg['truck_id']] if start<=seg['start']<=end)
            p,q=seg['coordinates'];match=index.match(*q)
            private_segments.append([si,eid,seg['start'],seg['end'],*p,*q,seg['state'],round(seg['apparent_speed_kph'],2),
                                     match['road_class'],round(match['distance_m'],1) if match['distance_m'] is not None else None,match['ambiguous']])
        # Private 0.005-degree cell/minute/state aggregation. IDs are deduplicated
        # here; never sum their counts across cells into a city reporting count.
        cells={}
        for r in rows:
            minute=r['event_time_unzoned'][:16]+':00';lat=math.floor(r['latitude']*200);lon=math.floor(r['longitude']*200)
            k=(minute,lat,lon,state(r));n,ids=cells.setdefault(k,[0,set()]);cells[k][0]+=1;ids.add(r['truck_id'])
        detail_cells.extend([[si,t,y,x,st,n,len(ids)] for (t,y,x,st),(n,ids) in sorted(cells.items())])
        name='overlap' if si==0 else 'overlap_'+s.source.covered_start
        if (root/(name+'_receipt.json')).exists():
            p,r=selected_snapshot(root,name)
            if p['schema']['date_reference']!={'timeZone':'Eastern Standard Time','respectsDaylightSaving':True} or p['schema']['dates_unknown']:
                raise ValueError('V3_PORTAL_CLOCK_CONTRACT')
            normalized=[windsor_observation(f,r['snapshot_id'],i+1) for i,f in enumerate(p['features'])]
            if si==0:old=rows
            else:
                hour=min(x['event_time_unzoned'] for x in rows)[:13]
                old=[x for x in rows if x['event_time_unzoned'][:13]==hour]
            overlaps.append(dict(week=s.source.covered_start,snapshot_id=r['snapshot_id'],scope_where=p['where'],**compare(old,normalized)))
        print(json.dumps(dict(week=s.source.covered_start,valid=len(rows),movement_intervals=move['intervals'])),flush=True)
        del bronze,typed,rows,events,move,cells
    products=gold.products();gold.close();validation=validate_products(products,plan)
    old_products={k:[r for r in values if r['processing_key'] in {s.processing_key for s in baseline.selected}] for k,values in products.items()}
    old_validation=validate_products(old_products,baseline)
    if old_validation['totals']['observation_count']!=298051:raise ValueError('V3_BASELINE_RECONCILIATION')
    pin=read(ROOT/'docs/WEATHER_ACTIVITY_EXECUTION_RESULTS.json')['private_download_artifact']
    if fingerprint(archive)!=pin['sha256'] or archive.stat().st_size!=pin['bytes']:raise ValueError('V3_WEATHER_ARCHIVE_PIN')
    with zipfile.ZipFile(archive) as z:saved=json.loads(z.read('matched_activity_weather.json'))
    matches=match_cached_weather(old_products,saved['weather'],saved['matches'])
    for zone in ('UTC','America/Toronto'):
        if sum(r['observation_count'] for r in matches if r['timezone_hypothesis']==zone)!=298051:raise ValueError('V3_WEATHER_RECONCILIATION')
    requests,qr=selected_snapshot(root,'requests')
    daily_requests=Counter();ward_requests=Counter();request_missing=Counter()
    for f in requests['features']:
        a=f['attributes'];stamp=a['created_date']
        if type(stamp) is not int:raise ValueError('V3_REQUEST_DATE_TYPE')
        from zoneinfo import ZoneInfo
        d=datetime.fromtimestamp(stamp/1000,timezone.utc).astimezone(ZoneInfo('America/Toronto')).date().isoformat()
        daily_requests[d]+=1;ward_requests[a['ward'] or 'missing']+=1
        for field,value in a.items():request_missing[field]+=int(value is None or value=='')
    request_summary=dict(records=len(requests['features']),snapshot_id=qr['snapshot_id'],scope=requests['where'],
                         daily_counts=dict(sorted(daily_requests.items())),ward_counts=dict(ward_requests),
                         missing_fields=dict(request_missing),fulfillment_fields=[],
                         geometry_present=sum(f.get('geometry') is not None for f in requests['features']),
                         geometry_absent=sum(f.get('geometry') is None for f in requests['features']),
                         semantics='CUSTOMER_REPORT_NOT_VERIFIED_UNSERVICED_ROAD_OR_COMPLETION')
    safe_cells=[]
    for s in scopes:
        grouped=Counter()
        for c in products['cell_hour']:
            if c['processing_key']==s.processing_key:grouped[c['spatial_bin']]+=c['observation_count']
        safe_cells.extend(dict(processing_key=s.processing_key,spatial_bin=k,observation_count=n) for k,n in grouped.items() if n>=20)
    receipt=dict(schema='winterops-geospatial-v3-public',evidence='EXECUTED_VERIFIED_CSV_AND_ARCGIS_SNAPSHOTS',
                 scopes=[s.dimensions() for s in scopes],baseline=old_validation,validation=validation,
                 sensors=sensors,movement=movements,overlap=overlaps,reporting=bucket_summaries(reporting),episodes=episode_summaries(eps),
                 transitions=transition,requests=request_summary,
                 roads=dict(records=len(roads['features']),snapshot_id=digest(roads),source_sha256=road_pin['sha256'],source_crs=4326,display_crs=4326,distance_crs=26917,
                            scope='OFFICIAL_LEGACY_LL84_POSTED_2025_01_14_NOT_VERIFIED_JANUARY_2026_ASOF',
                            portal_records=len(portal_roads['features']),portal_snapshot_id=rr['snapshot_id'],
                            portal_null_attributes={k:sum(f['attributes'][k] is None for f in portal_roads['features']) for k in ('street_compkey','street_name','functional_classification')},
                            ambiguous_rule='nearest <=30m and second distinct road within 10m of nearest'),
                 native_calls=0,weather_calls=0,new_weeks=3,weather_covered_scope_count=4,
                 weather=dict(snapshot_id=saved['weather']['weather_snapshot_id'],matches_per_hypothesis=842,observations_per_hypothesis=298051),
                 public_map=dict(grain='FIXED_0.25_DEGREE_CELL_SOURCE_WEEK_TOTAL_ONLY',minimum_observations=20,
                                 displayed_observations=sum(c['observation_count'] for c in safe_cells),
                                 withheld_observations=validation['totals']['observation_count']-sum(c['observation_count'] for c in safe_cells)))
    write(output/'summary.json',receipt)
    write(output/'products.json',products)
    # A local file, never embedded in a public page or read by network request.
    private=dict(schema='winterops-local-geospatial-v3',scopes=receipt['scopes'],baseline=old_validation,
                 cells=detail_cells,segments=private_segments,episodes=private_episodes,
                 reporting=reporting,matches=matches,grids=saved['weather']['grids'],snapshot_id=saved['weather']['weather_snapshot_id'])
    write(output/'winterops-local-detail.json',private)
    with (output/'winterops-local-detail.json').open('rb') as src,(output/'winterops-local-detail.json.gz').open('xb') as dst:
        with gzip.GzipFile(filename='',mode='wb',fileobj=dst,mtime=0) as compressed:
            for block in iter(lambda:src.read(1024*1024),b''):compressed.write(block)
    public=dict(schema=receipt['schema'],scopes=receipt['scopes'],weekly=products['weekly'],daily=products['daily'],
                cells=safe_cells,sensors=[{k:v for k,v in r.items() if k!='current_ward_observations'} for r in sensors],movement=movements,requests={k:v for k,v in request_summary.items() if k!='ward_counts'},
                reporting=receipt['reporting'],episodes=receipt['episodes'],roads=receipt['roads'],weather=receipt['weather'],
                public_map=receipt['public_map'],local_payload_encoding='gzip',
                local_payload_sha256=fingerprint(output/'winterops-local-detail.json.gz'),
                local_payload_bytes=(output/'winterops-local-detail.json.gz').stat().st_size)
    public['weather']=dict(public['weather'],city_hour_summaries=weather_summary(matches))
    write(output/'public.json',public)
    for name,p in [('roads',roads),('wards',wards),('boundary',boundary)]:write(output/(name+'.geojson'),context_geojson(p,name))
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-root',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--archive',required=True,type=Path)
    a=p.parse_args();r=build(a.input_root,a.output,a.archive)
    print(json.dumps(dict(status='PASS_LOCAL',validation=r['validation'],new_weeks=r['new_weeks'])))
