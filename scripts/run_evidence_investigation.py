"""Execute V3.1 from exact private V3 replay and public fixed weather snapshots.

No network or Databricks calls. Only explicit allowlisted aggregates are public;
intervals, scope labels, sparse roads and quality-cell/time data stay private.
"""
from collections import Counter,defaultdict
from datetime import datetime
import argparse
import gzip
import json
import math
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from winterops.sources import SourceVersion,outside_git,fingerprint
from winterops.foundation import read_bronze,silver_rows
from winterops.unified_gold import SelectedVersion
from winterops.operational_diagnostics import validated_rows,timestamp_events,state
from winterops.geospatial import RoadIndex,legacy_roads,observation_interval,interval_reason,geometry
from winterops.road_passages import PassageMatcher,legacy_nodes,sensitivity_policies,passage_runs
from winterops.sensor_investigation import conflict_review,february_case,identifier_continuity,scope_patterns
from winterops.weather_exposure import load_references,exposure_calendar,exposure_summary,reference_weekly
from winterops.weather import canonical,digest,require
from shapely.geometry import Point

ROOT=Path(__file__).resolve().parents[1]


def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))


def source_rows(root,public):
    weekly={r['processing_key']:r for r in public['weekly']}
    for number,d in enumerate(public['scopes']):
        file=Path(root)/'csv/raw'/d['source_file_name']/d['source_file_sha256']/d['source_file_name']
        v=SourceVersion.from_dict(read(file.with_suffix('.version.json')));v.verify()
        require(v.source_file_sha256==d['source_file_sha256'],'EVIDENCE_SOURCE_PIN')
        s=SelectedVersion(d['source_file_name'],d['source_file_sha256'],d['source_version_id'],d['processing_key'],
                          weekly[d['processing_key']]['bronze_rows'],d['original_csv_volume_path'])
        rows=validated_rows(silver_rows(list(read_bronze(v)),v),s)
        require(len(rows)==weekly[s.processing_key]['observation_count'],'EVIDENCE_WEEKLY_TOTAL')
        yield number,s,rows


def execute(inputs,private_path,output,weather_root):
    inputs,private_path,output=map(outside_git,(inputs,private_path,output));require(not output.exists(),'EVIDENCE_OUTPUT_EXISTS');output.mkdir(parents=True)
    public=read(ROOT/'dashboard/geospatial.json')
    # Accept the original V3 payload, even after public UI pins move to V3.1.
    require(fingerprint(private_path)=='4a3a1d76d7ba6e8d339b434dba359f24bf7831edf6a1e55596c8931926f91b45','EVIDENCE_V3_PRIVATE_PIN')
    detail=json.loads(gzip.decompress(private_path.read_bytes()))
    roadpin=read(inputs/'roads_legacy.receipt.json');roads=legacy_roads(inputs/'roads_legacy.zip',roadpin['sha256'])
    def context(name):
        r=read(inputs/(name+'_receipt.json'));return read(inputs/name/(r['snapshot_id']+'.snapshot.json'))
    index=RoadIndex(roads,context('wards'),context('boundary'));matcher=PassageMatcher(index,legacy_nodes(inputs/'roads_legacy.zip'))
    names=sorted({r['road_name'] for r in index.records if r['road_name']});name_id={name:i for i,name in enumerate(names)}
    marks=[];passages=[];uncertain=[];quality_cells=[];source_diagnostics=[];identifier_sets=[];hourly=[];private_case=[]
    scenarios=[];corridor=defaultdict(Counter);corridor_weeks=defaultdict(set);method_corridors=defaultdict(Counter)
    pointer=0;point_tiers=Counter();interval_source_observations=Counter();all_conflicts=0;sample_windows=[]
    methods=['nearest','heading','topology'];policies=sensitivity_policies();began=time.perf_counter()
    for si,scope,rows in source_rows(inputs,public):
        events=timestamp_events(rows);identifier_sets.append({identity[1] for identity in events})
        review,conflicts=conflict_review(events);all_conflicts+=review['conflicting_groups']
        diag=dict(week=scope.source.covered_start,processing_key=scope.processing_key,**review,scope_patterns=scope_patterns(events))
        flags=defaultdict(set)
        for e in conflicts:flags['state_conflict'].update(r['source_record_number'] for r in e['rows'])
        hours=defaultdict(Counter);ten_minutes=Counter();conflict_windows=Counter();quality_buckets=defaultdict(set)
        for e in conflicts:conflict_windows[e['time'].replace(minute=e['time'].minute//10*10,second=0,microsecond=0).isoformat(' ')]+=1
        for r in rows:
            h=r['event_time_unzoned'][:13]+':00:00';hours[h]['observation_count']+=1
            hours[h]['plow_active_observations']+=r['plow_active'];hours[h]['spreader_active_observations']+=r['spreader_active']
            t=datetime.fromisoformat(r['event_time_unzoned']);ten_minutes[t.replace(minute=t.minute//10*10,second=0,microsecond=0).isoformat(' ')]+=1
            candidates=matcher.point(r['longitude'],r['latitude']);n=r['source_record_number']
            inside=any(g.covers(Point(r['longitude'],r['latitude'])) for g in index.boundaries)
            if not inside:flags['outside_city'].add(n)
            if not candidates:flags['no_reference_60m'].add(n)
            if si>=4:flags['missing_activity_matched_weather'].add(n)
            if not candidates or candidates[0][0]>30:point_tiers['reported_coordinate_only']+=1
            elif len(candidates)>1 and candidates[1][0]-candidates[0][0]<=10:
                point_tiers['proximity_ambiguous']+=1;flags['road_alternative'].add(n)
            else:point_tiers['unambiguous_proximity']+=1
            if candidates and candidates[0][0]<=30 and (len(candidates)==1 or candidates[1][0]-candidates[0][0]>10) and n not in flags['state_conflict'] and not r['has_repeated_payload']:
                quality_buckets[(h,t.minute//5)].add(r['truck_id'])
        for h,counts in sorted(hours.items()):
            sizes=[len(ids) for (hour,bucket),ids in quality_buckets.items() if hour==h]
            hourly.append(dict(processing_key=scope.processing_key,source_local_naive_hour=h,**counts,
                               quality_mean_reporting_ids_5m=sum(sizes)/len(sizes) if sizes else None,quality_occupied_5m_buckets=len(sizes)))
        peak=max(ten_minutes,key=lambda t:(ten_minutes[t],t));sample_windows.append(dict(week=scope.source.covered_start,start=peak,kind='HIGH_OBSERVATION_10M',observations=ten_minutes[peak]))
        if scope.source.covered_start=='2026-01-12' and conflict_windows:
            c=max(conflict_windows,key=conflict_windows.get);sample_windows.append(dict(week=scope.source.covered_start,start=c,kind='HIGH_CONFLICT_10M',observations=ten_minutes[c]))
        if scope.source.covered_start=='2026-02-16':
            low=min(ten_minutes,key=lambda t:(ten_minutes[t],t));sample_windows.append(dict(week=scope.source.covered_start,start=low,kind='LOW_OBSERVATION_10M',observations=ten_minutes[low]))
        intervals=[];alternatives=[];legacy_indices={};support3=set()
        for identity,seq in events.items():
            for e in seq:
                if len({(r['longitude'],r['latitude']) for r in e['rows']})>1:flags['coordinate_tie'].update(r['source_record_number'] for r in e['rows'])
            for a,b in zip(seq,seq[1:]):
                e=observation_interval(a,b);e.update(processing_key=identity[0],truck_id=identity[1],start=a['time'].isoformat(' '),end=b['time'].isoformat(' '),
                                                     ordinals=[r['source_record_number'] for event in (a,b) for r in event['rows']])
                i=len(intervals);intervals.append(e);base_reason=interval_reason(e)
                if base_reason=='accepted':
                    old=detail['segments'][pointer]
                    require(old[:9]==[si,old[1],e['start'],e['end'],*e['p'],*e['q'],e['before']], 'EVIDENCE_LEGACY_SEGMENT_ORDER')
                    legacy_indices[i]=pointer;pointer+=1;support3.update(e['ordinals'])
                elif base_reason in ('stationary','questionable_speed'):
                    flags[base_reason].update(e['ordinals'])
                if base_reason!='accepted':
                    uncertain.append([si,e['start'],e['end'],list(e['p']) if e['p'] else None,list(e['q']) if e['q'] else None,base_reason])
                alternatives.append(matcher.alternatives(e) if interval_reason(e,120,150)=='accepted' else dict(overflow=False,paths=[],nearest=None))
        interval_source_observations['movement_supported_records']+=len(support3)
        configs=[(name,policies['reference']) for name in methods]+[(name,p) for name,p in policies.items() if name!='reference']
        for scenario,policy in configs:
            method=scenario if scenario in methods else 'topology'
            matches=[matcher.match(e,a,policy,method) for e,a in zip(intervals,alternatives)]
            runs=passage_runs(intervals,matches,index,matcher.connections if method=='topology' else None)
            support={i for run in runs for i in run['indices']};supported_records={n for i in support for n in intervals[i]['ordinals']}
            row=dict(week=scope.source.covered_start,scenario=scenario,policy=policy.__dict__,consecutive_intervals=len(intervals),
                     temporal_geometry_supported=sum(interval_reason(e,policy.gap_seconds,policy.speed_kph)=='accepted' for e in intervals),
                     pair_supported=sum(m['path'] is not None for m in matches),sequence_supported_intervals=len(support),
                     passage_candidates=len(runs),source_observations_in_sequences=len(supported_records),
                     outcomes=dict(Counter(m['reason'] for m in matches)),topology_pair_support=sum(m['path'] is not None and m['path']['topology'] for m in matches))
            scenarios.append(row)
            for run in runs:method_corridors[scenario][run['road_name']]+=1
            if scenario=='topology':
                interval_source_observations['road_sequence_supported_records']+=len(supported_records)
                run_ids={}
                for run in runs:
                    pid=len(passages);rid=name_id[run['road_name']]
                    passages.append([si,rid,run['start'],run['end'],run['interval_count'],run['observation_count'],run['state'],run['direction']])
                    for i in run['indices']:run_ids[i]=pid
                    corridor[run['road_name']]['passages']+=1;corridor[run['road_name']]['intervals']+=run['interval_count'];corridor[run['road_name']][run['state']]+=1
                    corridor_weeks[run['road_name']].add(si)
                for i,legacy_index in legacy_indices.items():
                    m=matches[i];path=m['path'];path_names={index.records[j]['road_name'] for j in path['indices']} if path else set()
                    name=next(iter(path_names)) if len(path_names)==1 else None
                    require(len(marks)==legacy_index,'EVIDENCE_MARK_ALIGNMENT')
                    marks.append([4 if i in support else 3,'road_sequence_supported' if i in support else m['reason'],name_id.get(name,-1),run_ids.get(i,-1),
                                  round(path['heading'],1) if path else None,round(path['distance'],1) if path else None,m['alternatives']])
        if scope.source.covered_start=='2026-02-09':diag['february_case'],private_case=february_case(rows,events,index)
        source_diagnostics.append(diag)
        positions={r['source_record_number']:r for r in rows};qcounts=Counter()
        for flag,ordinals in flags.items():
            for n in ordinals:
                r=positions[n];qcounts[(r['event_time_unzoned'][:16]+':00',math.floor(r['latitude']*200),math.floor(r['longitude']*200),flag)]+=1
        quality_cells.extend([si,t,y,x,flag,n] for (t,y,x,flag),n in sorted(qcounts.items()))
        print(json.dumps(dict(week=scope.source.covered_start,observations=len(rows),intervals=len(intervals),conflicts=review['conflicting_groups'],elapsed_seconds=round(time.perf_counter()-began,2))),flush=True)
    require(pointer==len(detail['segments'])==235012 and all_conflicts==4147,'EVIDENCE_BASELINE_RECONCILIATION')
    require(sum(r['observation_count'] for r in hourly)==338746,'EVIDENCE_HOURLY_RECONCILIATION')
    facts,refs,receipts=load_references(weather_root);calendar=exposure_calendar(facts,refs,hourly,detail['reporting']);weather=exposure_summary(calendar)
    reporting_means={r['source_local_hour']:r['mean_reporting_ids_5m'] for r in calendar if r['reference_id']=='windsor_centre' and r['timezone_hypothesis']=='America/Toronto'}
    for r in hourly:r['mean_reporting_ids_5m']=reporting_means[r['source_local_naive_hour']]
    pooled=[]
    for name,counts in sorted(corridor.items(),key=lambda x:(-x[1]['passages'],x[0])):
        # No public road/week, road/hour, identifier or sparse state intersection.
        if counts['passages']>=20 and len(corridor_weeks[name])>=4:
            pooled.append(dict(road_name=name,passage_candidates=counts['passages'],supported_intervals=counts['intervals'],source_weeks_present=len(corridor_weeks[name])))
    summary=dict(schema='winterops-evidence-v31-public',evidence='EXECUTED_EXACT_SEVEN_WEEK_REPLAY',observations=338746,
                 point_evidence=dict(point_tiers),observation_support=dict(interval_source_observations),scenarios=scenarios,
                 source_diagnostics=source_diagnostics,identifier_continuity=identifier_continuity(identifier_sets),
                 topology=matcher.topology_audit,pooled_corridors=pooled,
                 corridor_rankings={method:[dict(road_name=n,rank=rank+1) for rank,(n,c) in enumerate(values.most_common(15)) if c>=20 and len(corridor_weeks[n])>=4] for method,values in method_corridors.items()},
                 sample_windows=sample_windows,weather=weather,reference_weekly=reference_weekly(calendar,public['scopes']),weather_provenance=dict(references=refs,receipts=receipts,unique_grid_hours=len(facts),
                 http_requests=4,response_bytes=sum(r['response_bytes'] for r in receipts),model_attestation='REQUEST_PARAMETER_ONLY'),source_hour_activity=hourly,
                 contracts=dict(public_road_grain='FIXED_ALL_SEVEN_WEEK_TOTAL_MIN20_PASSAGES_MIN4_WEEKS_NO_SPARSE_STATE_SUBTABLES',
                                passage='>=3 consecutive timestamp groups, stable equipment, >=20m projected progress, supported geometry/heading and provider-node continuity; not completed service',
                                direction='Observed compass quadrant, not legal one-way validation',independent_service_verification='UNAVAILABLE'))
    (output/'public-results.json').write_bytes(canonical(summary)+b'\n')
    detail['evidence31']=dict(schema='winterops-evidence-v31-private',road_names=names,segment_marks=marks,passages=passages,
                              rejected_intervals=uncertain,quality_cells=quality_cells,reference_weather=calendar,weather_references=refs,private_february_scopes=private_case,
                              method_corridors={method:dict(counts) for method,counts in method_corridors.items()})
    with (output/'winterops-v31-local.json.gz').open('xb') as out:
        with gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0) as compressed:compressed.write(canonical(detail)+b'\n')
    (output/'execution.json').write_bytes(canonical(dict(status='PASS_LOCAL',observations=338746,legacy_segments=pointer,passages=len(passages),
                  conflicting_groups=all_conflicts,private_payload_bytes=(output/'winterops-v31-local.json.gz').stat().st_size,
                  private_payload_sha256=fingerprint(output/'winterops-v31-local.json.gz'),native_calls=0,seconds=round(time.perf_counter()-began,2)))+b'\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',required=True,type=Path);p.add_argument('--v3-private',required=True,type=Path)
    p.add_argument('--weather',type=Path,default=ROOT/'data/weather_reference');p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();execute(a.inputs,a.v3_private,a.output,a.weather)
