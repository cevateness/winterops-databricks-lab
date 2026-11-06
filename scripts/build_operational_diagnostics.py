"""Offline diagnostics V2. Full private builds need the existing pinned caches.

Public replay regenerates the aggregate diagnostics page without private inputs.
No downloads, native calls, identifiers or episode timelines in public outputs.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from winterops.foundation import read_bronze, silver_rows, processing_key
from winterops.sources import SourceVersion, outside_git, fingerprint
from winterops.unified_gold import load_selection
from winterops.operational_sql import LocalGold
from winterops.operational_analytics import validate_products, match_cached_weather
from winterops.operational_diagnostics import (validated_rows,reporting_buckets,timestamp_events,episodes,transitions,
                                               bucket_summaries,episode_summaries,weather_relationships)
from winterops.diagnostics_dashboard import render_public, render_private
from winterops.weather import canonical,digest,require


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def actual(cache,archive,output):
    cache,archive,output=map(outside_git,(cache,archive,output))
    require(not output.exists(),'DIAG_PRIVATE_OUTPUT_EXISTS')
    plan=load_selection(ROOT/'docs/FOUR_WEEK_SELECTION.json')
    pin=read(ROOT/'docs/WEATHER_ACTIVITY_EXECUTION_RESULTS.json')['private_download_artifact']
    require(archive.stat().st_size==pin['bytes'] and fingerprint(archive)==pin['sha256'],'DIAG_ARCHIVE_PIN')
    with zipfile.ZipFile(archive) as z:
        require(z.getinfo('matched_activity_weather.json').file_size<8*1024*1024,'DIAG_ARCHIVE_SIZE')
        saved=json.loads(z.read('matched_activity_weather.json'))
    local=LocalGold(plan);bucket_rows=[];episode_rows=[];transition_rows=[];quality=[]
    try:
        for s in plan.selected:
            p=cache/'raw'/s.source_file_name/s.source_file_sha256/s.source_file_name
            v=SourceVersion.from_dict(read(p.with_suffix('.version.json')));v.verify()
            require(Path(v.local_path).resolve()==p.resolve() and v.source==s.source and v.source_file_sha256==s.source_file_sha256
                    and processing_key(v,s.policy)==s.processing_key,'DIAG_CSV_PIN')
            bronze=list(read_bronze(v));typed=silver_rows(bronze,v,s.policy);local.add_verified_scope(s,typed)
            valid=validated_rows(typed,s);events=timestamp_events(valid)
            for width in (1,5,15):bucket_rows.extend(reporting_buckets(valid,width))
            for gap in (15,30,60):episode_rows.extend(episodes(events,gap,s))
            for gap in (15,60,300):transition_rows.extend(transitions(events,gap))
            quality.append(dict(processing_key=s.processing_key,valid_observations=len(valid),
                                timestamp_groups=sum(map(len,events.values())),identifier_scopes=len(events),
                                conflicting_timestamp_groups=sum(e['state'].startswith('unknown') for seq in events.values() for e in seq),
                                tied_extra_observations=len(valid)-sum(map(len,events.values())),
                                repeated_payload_observations=sum(r['has_repeated_payload'] for r in valid)))
            del bronze,typed,valid,events
        products=local.products()
    finally:local.close()
    validation=validate_products(products,plan)
    require(validation['totals']['observation_count']==298051 and validation['totals']['plow_active_observations']==239344
            and validation['totals']['spreader_active_observations']==127232,'DIAG_GOLD_TOTALS')
    matches=match_cached_weather(products,saved['weather'],saved['matches'])
    for width in (1,5,15):require(sum(r['observation_count'] for r in bucket_rows if r['bucket_minutes']==width)==298051,'DIAG_BUCKET_RECONCILIATION')
    for gap in (15,30,60):require(sum(r['observation_count'] for r in episode_rows if r['gap_minutes']==gap)==298051,'DIAG_EPISODE_RECONCILIATION')
    relationships=weather_relationships(matches,episode_rows,bucket_rows)
    timing=Counter((r['processing_key'],r['gap_minutes'],r['first_observed'][:10],int(r['first_observed'][11:13])) for r in episode_rows)
    summary=dict(episode_timing=[dict(processing_key=k,gap_minutes=g,source_local_day=d,source_local_hour_of_day=h,observed_onsets=n) for (k,g,d,h),n in sorted(timing.items())],schema='winterops-diagnostics-v2',evidence='EXECUTED_PINNED_REAL_CSV_AND_CACHED_WEATHER',
                 scopes=[s.dimensions() for s in plan.selected],snapshot_id=saved['weather']['weather_snapshot_id'],
                 archive_sha256=pin['sha256'],validation=validation,quality=quality,
                 reporting=bucket_summaries(bucket_rows),episodes=episode_summaries(episode_rows),transitions=transition_rows,
                 relationships=relationships,
                 contracts=dict(reporting='Distinct identifiers within an occupied source-local window, not instantaneous concurrency or capacity.',
                                episodes='Heuristic observed episodes, not dispatch or work duration. All actual onset/completion boundaries are censored.',
                                transitions='Consecutive timestamp groups; conflicting ties/gaps/source starts are unknown.',
                                weather='Conditional Toronto/UTC, retrospective reanalysis; activity-conditioned sample. No deployment probability or causal claim.',
                                onset_weather='Containing-hour start; antecedent [hour_start-2h,hour_start), excluding partial onset hour.',
                                categories={'temperature':['T < -10 C','-10 <= T < 0 C','T >= 0 C'],'precipitation_snowfall':['value = 0','value > 0','missing']},
                                public_privacy='City-level pooled summaries only. No new cell/time/filter cross-tabulation, raw IDs or episode timelines.',
                                quantiles='Linear interpolation; occupied windows only. Missing windows are not imputed zero.',
                                basemap='None: offline Web Mercator coarse cell and returned-grid diagram, not route/coverage geometry.'),
                 requests=dict(weather=0,municipal=0,databricks=0))
    summary['content_sha256']=digest(canonical(summary))
    output.mkdir(parents=True)
    for name,value in [('episodes',episode_rows),('reporting_windows',bucket_rows),('cell_weather',matches)]:
        (output/(name+'.json')).write_bytes(canonical(value)+b'\n')
    private_data=dict(evidence=summary['evidence'],cells=products['cell_hour'],matches=matches,
                      grids=saved['weather']['grids'],scopes=summary['scopes'],snapshot_id=summary['snapshot_id'])
    (output/'private_map.html').write_text(render_private(private_data),encoding='utf-8')
    (output/'public_summary.json').write_bytes(canonical(summary)+b'\n')
    (output/'diagnostics.html').write_text(render_public(summary),encoding='utf-8')
    (output/'index.html').write_bytes((ROOT/'dashboard/index.html').read_bytes())
    receipt=dict(evidence=summary['evidence'],requests=summary['requests'],validation=validation,
                 weather_matches=len(matches),private_files_sha256={p.name:fingerprint(p) for p in output.iterdir() if p.is_file()})
    (output/'execution.json').write_bytes(canonical(receipt)+b'\n')
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--source-cache',type=Path);p.add_argument('--archive',type=Path)
    a=p.parse_args()
    try:
        require(not a.output_root.exists(),'DIAG_OUTPUT_EXISTS')
        require(bool(a.source_cache)==bool(a.archive),'DIAG_BOTH_INPUTS_REQUIRED')
        if a.source_cache:result=actual(a.source_cache,a.archive,a.output_root)
        else:
            summary=read(ROOT/'dashboard/diagnostics.json');expected=summary.pop('content_sha256')
            require(digest(canonical(summary))==expected,'DIAG_PUBLIC_HASH');summary['content_sha256']=expected
            a.output_root.mkdir(parents=True)
            (a.output_root/'diagnostics.html').write_text(render_public(summary),encoding='utf-8')
            (a.output_root/'index.html').write_bytes((ROOT/'dashboard/index.html').read_bytes())
            result=dict(evidence='PUBLIC_SUMMARY_REPLAY_ONLY',private_detail='NOT_RERUN',requests=dict(weather=0,municipal=0,databricks=0))
            (a.output_root/'execution.json').write_bytes(canonical(result)+b'\n')
        print(json.dumps(result));return 0
    except Exception as e:
        print(json.dumps(dict(status='FAILED',code=str(e) if type(e).__module__.startswith('winterops') else type(e).__name__)),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
