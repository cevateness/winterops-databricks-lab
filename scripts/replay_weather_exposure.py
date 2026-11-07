"""Reproduce actual continuous weather findings from public aggregates, offline.

Hour-level mean reporting counts are measured summaries, not synthetic buckets.
Detailed road and sensor reconstruction still requires the private replay.
"""
import argparse
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from winterops.weather_exposure import load_references,exposure_calendar,exposure_summary,reference_weekly,correlation
from winterops.weather import canonical,require

ROOT=Path(__file__).resolve().parents[1]

def equivalent(actual,expected):
    """Exact structure/counts, 1e-12 tolerance for cross-Python float arithmetic."""
    if type(expected) is float:return type(actual) in (int,float) and math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-12)
    if isinstance(expected,dict):return isinstance(actual,dict) and actual.keys()==expected.keys() and all(equivalent(actual[k],v) for k,v in expected.items())
    if isinstance(expected,list):return isinstance(actual,list) and len(actual)==len(expected) and all(equivalent(a,b) for a,b in zip(actual,expected))
    return type(actual) is type(expected) and actual==expected

def replay(public):
    facts,refs,receipts=load_references(ROOT/'data/weather_reference')
    calendar=exposure_calendar(facts,refs,public['source_hour_activity'],[])
    summary=exposure_summary(calendar)
    require(equivalent(summary,public['weather']),'EXPOSURE_PUBLIC_REPLAY_MISMATCH')
    sensitivity=[]
    for dry in (3,6,12):
        events=exposure_summary(calendar,dry)['weather_defined_events']
        for ref in refs:
            for zone in ('America/Toronto','UTC'):
                rows=[r for r in events if r['reference_id']==ref['reference_id'] and r['timezone_hypothesis']==zone]
                supported=[r for r in rows if r['recorded_hours']>=3 and r['mean_reporting_ids_in_recorded_hours'] is not None and r['snowfall_cm'] is not None]
                sensitivity.append(dict(reference_id=ref['reference_id'],timezone_hypothesis=zone,dry_separation_hours=dry,
                                        weather_events=len(rows),events_with_at_least_three_recorded_hours=len(supported),
                                        event_snowfall_reporting_pearson_r=correlation([r['snowfall_cm'] for r in supported],[r['mean_reporting_ids_in_recorded_hours'] for r in supported])))
    return dict(status='PASS_PUBLIC_AGGREGATE_WEATHER_REPLAY',source_observations=sum(r['observation_count'] for r in public['source_hour_activity']),
                calendar_rows=len(calendar),distinct_weather_facts=len(facts),weather_requests=0,event_sensitivity=sensitivity,
                spatial_sensor_details_rerun=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public',type=Path,default=ROOT/'docs/ROAD_EVIDENCE_V31_RESULTS.json');p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();r=replay(json.loads(a.public.read_text()));a.output.write_bytes(canonical(r)+b'\n');print(r['status'])
